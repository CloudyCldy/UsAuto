import csv
import io
import os
from datetime import datetime

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

import joblib
import pandas as pd
from bson import ObjectId
from flask import Flask, render_template, request, jsonify, Response, redirect
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from config.database import get_db
from analysis.analisis_datos import obtener_metricas_dashboard, analisis_ventas
from analysis.visualizacion import generar_graficas_base64, obtener_df_visualizacion, obtener_datos_reportes_negocio
from analysis.clasificacion import entrenar_random_forest, entrenar_decision_tree
from analysis.kmeans import entrenar_kmeans
from analysis.pca import entrenar_pca

app = Flask(__name__)
app.config['SECRET_KEY'] = 'usagi_autos_secret'

# Agregar funciones globales para Jinja2
app.jinja_env.globals.update(max=max, min=min)


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def paginate_collection(collection_name, filtro=None, page=1, per_page=10):
    """
    Paginates a MongoDB collection.
    Returns: (items, total_items, total_pages, current_page)
    """
    try:
        db = get_db()
        total = db[collection_name].count_documents(filtro or {})
        total_pages = (total + per_page - 1) // per_page  # Ceiling division
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        skip = (page - 1) * per_page
        items = list(db[collection_name].find(filtro or {}).skip(skip).limit(per_page))
        return items, total, total_pages, page
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return [], 0, 0, 1


def safe_db_collection(collection_name, filtro=None):
    try:
        db = get_db()
        return list(db[collection_name].find(filtro or {}))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return []


def safe_db_count(collection_name, filtro=None):
    try:
        db = get_db()
        return db[collection_name].count_documents(filtro or {})
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return 0


def get_db_stats():
    return {
        'clientes': safe_db_count('clientes'),
        'vehiculos': safe_db_count('vehiculos'),
        'vendedores': safe_db_count('vendedores'),
        'ventas': safe_db_count('ventas'),
        'financiamientos': safe_db_count('financiamientos'),
        'servicios': safe_db_count('servicios'),
    }


def cargar_dashboard_context():
    metricas = obtener_metricas_dashboard()
    analy = analisis_ventas()
    graficas = generar_graficas_base64()

    df = obtener_df_visualizacion()
    dashboard_data = {
        'ventas_por_marca': [],
        'ventas_por_tipo': [],
        'precios': [],
        'ingreso_vs_presupuesto': [],
        'precio_por_marca': [],
        'evolucion_mensual': [],
    }

    if not df.empty:
        ventas_marca = df.groupby('marca', as_index=False)['total'].sum().sort_values('total', ascending=False)
        dashboard_data['ventas_por_marca'] = [
            {'marca': row['marca'], 'ventas': float(row['total'])}
            for _, row in ventas_marca.iterrows()
        ]
        dashboard_data['evolucion_mensual'] = [
            {'mes': row['mes'], 'ventas': float(row['total'])}
            for _, row in df.groupby('mes', as_index=False)['total'].sum().sort_values('mes').iterrows()
        ]
        dashboard_data['precio_por_marca'] = [
            {'marca': row['marca'], 'precio': float(row['precio'])}
            for _, row in df.groupby('marca', as_index=False)['precio'].mean().sort_values('precio', ascending=False).iterrows()
        ]
        dashboard_data['precios'] = [float(value) for value in df['precio'].dropna().tolist()]
        dashboard_data['ventas_por_tipo'] = [
            {'tipo': key, 'cantidad': int(value)}
            for key, value in df['tipo'].value_counts().items()
        ]

    clientes = pd.DataFrame(list(get_db().clientes.find()))
    if not clientes.empty:
        clientes = clientes[['ingreso_mensual', 'presupuesto']].dropna()
        dashboard_data['ingreso_vs_presupuesto'] = [
            {'ingreso': float(row['ingreso_mensual']), 'presupuesto': float(row['presupuesto'])}
            for _, row in clientes.iterrows()
        ]

    return {
        'metricas': metricas,
        'analisis': analy,
        'graficas': graficas,
        'dashboard_data': dashboard_data,
        'stats': get_db_stats(),
    }


@app.route('/')
def index():
    context = cargar_dashboard_context()
    return render_template('index.html', **context)


@app.route('/clientes', methods=['GET'])
def clientes():
    query = request.args.get('q', '').strip()
    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))  # Limitar entre 5 y 100
    filtro = {}
    if query:
        filtro = {
            '$or': [
                {'nombre': {'$regex': query, '$options': 'i'}},
                {'apellido_paterno': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}},
            ]
        }
    clientes, total, total_pages, current_page = paginate_collection('clientes', filtro, page, per_page=per_page)
    return render_template('clientes.html', clientes=clientes, query=query, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/vehiculos', methods=['GET', 'POST'])
def vehiculos():
    db = get_db()
    if request.method == 'POST':
        payload = {
            'marca': request.form.get('marca', '').strip(),
            'modelo': request.form.get('modelo', '').strip(),
            'anio': to_int(request.form.get('anio'), 0),
            'tipo': request.form.get('tipo', '').strip(),
            'precio': to_float(request.form.get('precio'), 0.0),
            'stock': to_int(request.form.get('stock'), 0),
            'estado': request.form.get('estado', 'Disponible').strip() or 'Disponible',
            'created_at': datetime.utcnow(),
        }
        if payload['marca'] and payload['modelo']:
            try:
                db.vehiculos.insert_one(payload)
            except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
                pass

    query = request.args.get('q', '').strip()
    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    filtro = {}
    if query:
        filtro = {
            '$or': [
                {'marca': {'$regex': query, '$options': 'i'}},
                {'modelo': {'$regex': query, '$options': 'i'}},
                {'tipo': {'$regex': query, '$options': 'i'}},
            ]
        }
    vehiculos, total, total_pages, current_page = paginate_collection('vehiculos', filtro, page, per_page=per_page)
    return render_template('vehiculos.html', vehiculos=vehiculos, query=query, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/vehiculos/<vehiculo_id>/editar', methods=['POST'])
def editar_vehiculo(vehiculo_id):
    db = get_db()
    payload = {
        'marca': request.form.get('marca', '').strip(),
        'modelo': request.form.get('modelo', '').strip(),
        'anio': to_int(request.form.get('anio'), 0),
        'tipo': request.form.get('tipo', '').strip(),
        'precio': to_float(request.form.get('precio'), 0.0),
        'stock': to_int(request.form.get('stock'), 0),
        'estado': request.form.get('estado', 'Disponible').strip() or 'Disponible',
    }
    if payload['marca'] and payload['modelo']:
        db.vehiculos.update_one({'_id': ObjectId(vehiculo_id)}, {'$set': payload})
    return redirect('/vehiculos')


@app.route('/vendedores', methods=['GET', 'POST'])
def vendedores():
    db = get_db()
    if request.method == 'POST':
        payload = {
            'nombre': request.form.get('nombre', '').strip(),
            'apellido': request.form.get('apellido', '').strip(),
            'email': request.form.get('email', '').strip(),
            'telefono': request.form.get('telefono', '').strip(),
            'comision': to_float(request.form.get('comision'), 0.0),
            'activo': True,
            'created_at': datetime.utcnow(),
        }
        if payload['nombre'] and payload['email']:
            try:
                db.vendedores.insert_one(payload)
            except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
                pass

    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    vendedores, total, total_pages, current_page = paginate_collection('vendedores', {}, page, per_page=per_page)
    return render_template('vendedores.html', vendedores=vendedores, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/cotizaciones', methods=['GET', 'POST'])
def cotizaciones():
    db = get_db()
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        payload = {
            'cliente_id': request.form.get('cliente_id', '').strip() or 'cliente_demo',
            'vehiculo_id': request.form.get('vehiculo_id', '').strip() or 'vehiculo_demo',
            'vendedor_id': request.form.get('vendedor_id', '').strip() or 'vendedor_demo',
            'fecha': datetime.strptime(fecha, '%Y-%m-%d') if fecha else datetime.utcnow(),
            'precio_base': to_float(request.form.get('precio_base'), 0.0),
            'descuento': to_float(request.form.get('descuento'), 0.0),
            'total': to_float(request.form.get('total'), 0.0),
            'estado': request.form.get('estado', 'Pendiente').strip(),
            'created_at': datetime.utcnow(),
        }
        try:
            db.cotizaciones.insert_one(payload)
        except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
            pass

    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    cotizaciones, total, total_pages, current_page = paginate_collection('cotizaciones', {}, page, per_page=per_page)
    return render_template('cotizaciones.html', cotizaciones=cotizaciones, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/ventas')
def ventas():
    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    ventas, total, total_pages, current_page = paginate_collection('ventas', {}, page, per_page=per_page)
    return render_template('ventas.html', ventas=ventas, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/ventas/exportar')
def exportar_ventas():
    db = get_db()
    ventas = list(db.ventas.find({}))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['fecha_venta', 'precio_venta', 'iva', 'total', 'metodo_pago'])
    writer.writeheader()
    for venta in ventas:
        writer.writerow({
            'fecha_venta': venta.get('fecha_venta').strftime('%Y-%m-%d') if venta.get('fecha_venta') else '',
            'precio_venta': venta.get('precio_venta', 0),
            'iva': venta.get('iva', 0),
            'total': venta.get('total', 0),
            'metodo_pago': venta.get('metodo_pago', ''),
        })
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=ventas.csv'
    return response


@app.route('/financiamientos')
def financiamientos():
    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    financiamientos_list, total, total_pages, current_page = paginate_collection('financiamientos', {}, page, per_page=per_page)
    resumen = None
    if request.args.get('resumen') == '1':
        # Get all for summary calculation
        all_financiamientos = safe_db_collection('financiamientos')
        resumen = {
            'total_monto': sum(float(f.get('monto_financiado', 0) or 0) for f in all_financiamientos),
            'promedio_cuota': round(sum(float(f.get('cuota_mensual', 0) or 0) for f in all_financiamientos) / len(all_financiamientos), 2) if all_financiamientos else 0,
            'aprobados': sum(1 for f in all_financiamientos if str(f.get('estatus', '')).lower() == 'aprobado'),
            'en_proceso': sum(1 for f in all_financiamientos if str(f.get('estatus', '')).lower() == 'en proceso'),
        }
    return render_template('financiamientos.html', financiamientos=financiamientos_list, resumen=resumen, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/servicios', methods=['GET', 'POST'])
def servicios():
    db = get_db()
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        payload = {
            'tipo_servicio': request.form.get('tipo_servicio', '').strip(),
            'cliente_id': request.form.get('cliente_id', '').strip(),
            'costo': to_float(request.form.get('costo'), 0.0),
            'fecha': datetime.strptime(fecha, '%Y-%m-%d') if fecha else datetime.utcnow(),
            'status': request.form.get('status', 'Programado').strip(),
            'created_at': datetime.utcnow(),
        }
        if payload['tipo_servicio'] and payload['cliente_id']:
            try:
                db.servicios.insert_one(payload)
            except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
                pass

    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    servicios, total, total_pages, current_page = paginate_collection('servicios', {}, page, per_page=per_page)
    return render_template('servicios.html', servicios=servicios, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


@app.route('/reportes')
def reportes():
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')

    filtro_pagos = {}
    filtro_ventas = {}
    if desde or hasta:
        fecha_pagos = {}
        fecha_ventas = {}
        if desde:
            fecha_pagos['$gte'] = datetime.strptime(desde, '%Y-%m-%d')
            fecha_ventas['$gte'] = datetime.strptime(desde, '%Y-%m-%d')
        if hasta:
            fecha_pagos['$lte'] = datetime.strptime(hasta, '%Y-%m-%d')
            fecha_ventas['$lte'] = datetime.strptime(hasta, '%Y-%m-%d')
        filtro_pagos['fecha_pago'] = fecha_pagos
        filtro_ventas['fecha_venta'] = fecha_ventas

    try:
        db = get_db()
        pagos = list(db.pagos.find(filtro_pagos))
        ventas = list(db.ventas.find(filtro_ventas))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        pagos = []
        ventas = []
    venta_total = sum(float(v['total']) for v in ventas if 'total' in v)

    df = obtener_df_visualizacion()
    if desde or hasta:
        mask = pd.Series(True, index=df.index)
        if desde:
            mask &= df['fecha_venta'] >= pd.Timestamp(desde)
        if hasta:
            mask &= df['fecha_venta'] <= pd.Timestamp(hasta)
        df = df[mask]
    report_data = obtener_datos_reportes_negocio(df)
    return render_template(
        'reportes.html',
        pagos=pagos,
        venta_total=venta_total,
        ventas_por_marca=report_data['ventas_por_marca'],
        evolucion_mensual=report_data['evolucion_mensual'],
        ventas_por_mes=report_data['ventas_por_mes'],
        tickets_por_mes=report_data['tickets_por_mes'],
        desde=desde,
        hasta=hasta,
    )


@app.route('/reportes/exportar-pdf')
@app.route('/reportes/exportar-pdf/')
@app.route('/reportes/exportar')
def exportar_reportes_pdf():
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')

    filtro_pagos = {}
    filtro_ventas = {}
    if desde or hasta:
        fecha_pagos = {}
        fecha_ventas = {}
        if desde:
            fecha_pagos['$gte'] = datetime.strptime(desde, '%Y-%m-%d')
            fecha_ventas['$gte'] = datetime.strptime(desde, '%Y-%m-%d')
        if hasta:
            fecha_pagos['$lte'] = datetime.strptime(hasta, '%Y-%m-%d')
            fecha_ventas['$lte'] = datetime.strptime(hasta, '%Y-%m-%d')
        filtro_pagos['fecha_pago'] = fecha_pagos
        filtro_ventas['fecha_venta'] = fecha_ventas

    try:
        db = get_db()
        pagos = list(db.pagos.find(filtro_pagos))
        ventas = list(db.ventas.find(filtro_ventas))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        pagos = []
        ventas = []
    venta_total = sum(float(v['total']) for v in ventas if 'total' in v)

    df = obtener_df_visualizacion()
    if desde or hasta:
        mask = pd.Series(True, index=df.index)
        if desde:
            mask &= df['fecha_venta'] >= pd.Timestamp(desde)
        if hasta:
            mask &= df['fecha_venta'] <= pd.Timestamp(hasta)
        df = df[mask]
    report_data = obtener_datos_reportes_negocio(df)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    pdf.setTitle('Reporte Usagi Autos')
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(50, y, 'Reporte Usagi Autos')
    y -= 28

    pdf.setFont('Helvetica', 11)
    periodo = f"Periodo: {desde or 'Inicio'} - {hasta or 'Actual'}"
    pdf.drawString(50, y, periodo)
    y -= 24
    pdf.drawString(50, y, f"Ventas totales: ${venta_total:,.2f}")
    y -= 20
    pdf.drawString(50, y, f"Pagos registrados: {len(pagos)}")
    y -= 20
    pdf.drawString(50, y, f"Estado de pagos: {'Activos' if pagos else 'Sin pagos'}")
    y -= 30

    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(50, y, 'Ventas por marca')
    y -= 20
    pdf.setFont('Helvetica', 10)
    for item in report_data.get('ventas_por_marca', [])[:8]:
        if y < 80:
            pdf.showPage()
            y = height - 60
            pdf.setFont('Helvetica', 10)
        pdf.drawString(60, y, f"- {item.get('marca', 'Sin marca')}: {item.get('ventas', 0)} ventas")
        y -= 16

    pdf.save()
    pdf_data = buffer.getvalue()
    buffer.close()

    response = Response(pdf_data, mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_agencia.pdf'
    return response


@app.route('/machine-learning')
def machine_learning():
    return render_template('machine_learning.html')


@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.form
    required = ['edad', 'ingreso_mensual', 'historial_compras', 'numero_cotizaciones', 'visitas_agencia', 'presupuesto', 'financiamiento', 'tipo_cliente', 'marca_interes', 'antiguedad_cliente']
    if any(data.get(field) in (None, '') for field in required):
        return jsonify({'error': 'Faltan datos requeridos para la predicción.'}), 400

    try:
        artifact = joblib.load(os.path.join('models', 'random_forest.pkl'))
        model = artifact['model']
        preprocessor = artifact['preprocessor']
        sample = pd.DataFrame([{
            'edad': to_float(data.get('edad'), 0.0),
            'ingreso_mensual': to_float(data.get('ingreso_mensual'), 0.0),
            'historial_compras': to_int(data.get('historial_compras'), 0),
            'numero_cotizaciones': to_int(data.get('numero_cotizaciones'), 0),
            'visitas_agencia': to_int(data.get('visitas_agencia'), 0),
            'presupuesto': to_float(data.get('presupuesto'), 0.0),
            'financiamiento': to_int(data.get('financiamiento'), 0),
            'tipo_cliente': str(data.get('tipo_cliente', '')),
            'marca_interes': str(data.get('marca_interes', '')),
            'antiguedad_cliente': to_int(data.get('antiguedad_cliente'), 0),
        }])
        transformed = preprocessor.transform(sample)
        transformed_df = pd.DataFrame(transformed, columns=preprocessor.get_feature_names_out())
        pred = model.predict(transformed_df)[0]
        proba = model.predict_proba(transformed_df)[0].max()
        result = 'Alta probabilidad de compra' if pred == 1 else 'Baja probabilidad de compra'
        return jsonify({'resultado': result, 'probabilidad': round(float(proba), 4), 'prediccion': int(pred)})
    except (TypeError, ValueError):
        return jsonify({'error': 'Datos numéricos inválidos.'}), 400


if __name__ == '__main__':
    if not os.path.exists('models/random_forest.pkl'):
        entrenar_random_forest()
    if not os.path.exists('models/decision_tree.pkl'):
        entrenar_decision_tree()
    if not os.path.exists('models/kmeans.pkl'):
        entrenar_kmeans()
    if not os.path.exists('models/pca.pkl'):
        entrenar_pca()
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)
