import csv
import io
import os
from datetime import datetime

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

import joblib
import pandas as pd
from bson import ObjectId
from flask import Flask, render_template, request, jsonify, Response, redirect, session, url_for, flash
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas as pdfcanvas
from werkzeug.security import check_password_hash, generate_password_hash
from config.database import get_db
from analysis.analisis_datos import obtener_metricas_dashboard, analisis_ventas
from analysis.visualizacion import generar_graficas_base64, obtener_df_visualizacion, obtener_datos_reportes_negocio
from analysis.clasificacion import entrenar_random_forest, entrenar_decision_tree
from analysis.kmeans import entrenar_kmeans
from analysis.pca import entrenar_pca

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'usagi_autos_secret')

PUBLIC_ENDPOINTS = {'login', 'register', 'logout', 'static'}


@app.before_request
def require_login():
    if request.endpoint not in PUBLIC_ENDPOINTS and 'user_id' not in session:
        return redirect(url_for('login', next=request.path))


@app.context_processor
def inject_current_user():
    return {'current_user': session.get('user_name')}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip().lower()
        password = request.form.get('password', '')
        user = get_db().usuarios.find_one({
            '$or': [{'email': identifier}, {'username': identifier}]
        })
        if user and user.get('activo', True) and check_password_hash(user.get('password_hash', ''), password):
            session.clear()
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('nombre') or user.get('username')
            next_url = request.args.get('next') or request.form.get('next')
            return redirect(next_url if next_url and next_url.startswith('/') else url_for('index'))
        flash('Correo, usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html', next_url=request.args.get('next', ''))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirmation = request.form.get('password_confirmation', '')

        if not nombre or not username or not email or not password:
            flash('Completa todos los campos.', 'danger')
        elif len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
        elif password != password_confirmation:
            flash('Las contraseñas no coinciden.', 'danger')
        elif get_db().usuarios.find_one({'$or': [{'email': email}, {'username': username}]}):
            flash('El correo o usuario ya está registrado.', 'danger')
        else:
            try:
                user = {
                    'nombre': nombre,
                    'username': username,
                    'email': email,
                    'password_hash': generate_password_hash(password),
                    'role': 'user',
                    'activo': True,
                    'created_at': datetime.utcnow(),
                }
                result = get_db().usuarios.insert_one(user)
                session['user_id'] = str(result.inserted_id)
                session['user_name'] = nombre
                return redirect(url_for('index'))
            except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
                flash('No fue posible crear la cuenta. Intenta nuevamente.', 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Agregar funciones globales para Jinja2
app.jinja_env.globals.update(max=max, min=min)


# --------------------------------------------------------------------------
# Paleta de colores para el reporte PDF (coherente con la UI de la app)
# --------------------------------------------------------------------------
PURPLE_DARK = colors.HexColor('#3A1F52')
PURPLE = colors.HexColor('#6C3FA8')
PURPLE_LIGHT = colors.HexColor('#F1E8F8')
PINK = colors.HexColor('#E85AAE')
TEXT_DARK = colors.HexColor('#292230')
GREEN = colors.HexColor('#16a34a')
ORANGE = colors.HexColor('#d97706')
GRAY = colors.HexColor('#6b7280')
ROW_ALT = colors.HexColor('#FBF7FD')
GRID_LINE = colors.HexColor('#E5E0EA')


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


def format_currency(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


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


@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    db = get_db()
    if request.method == 'POST':
        payload = {
            'nombre': request.form.get('nombre', '').strip(),
            'apellido_paterno': request.form.get('apellido_paterno', '').strip(),
            'apellido_materno': request.form.get('apellido_materno', '').strip(),
            'email': request.form.get('email', '').strip(),
            'telefono': request.form.get('telefono', '').strip(),
            'edad': to_int(request.form.get('edad'), 0),
            'ingreso_mensual': to_float(request.form.get('ingreso_mensual'), 0.0),
            'tipo_cliente': request.form.get('tipo_cliente', 'Nuevo').strip() or 'Nuevo',
            'presupuesto': to_float(request.form.get('presupuesto'), 0.0),
            'activo': True,
            'created_at': datetime.utcnow(),
        }
        if payload['nombre'] and payload['email']:
            try:
                db.clientes.insert_one(payload)
            except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
                pass

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


@app.route('/clientes/<cliente_id>/editar', methods=['POST'])
def editar_cliente(cliente_id):
    payload = {
        'nombre': request.form.get('nombre', '').strip(),
        'apellido_paterno': request.form.get('apellido_paterno', '').strip(),
        'apellido_materno': request.form.get('apellido_materno', '').strip(),
        'email': request.form.get('email', '').strip(),
        'telefono': request.form.get('telefono', '').strip(),
        'edad': to_int(request.form.get('edad'), 0),
        'ingreso_mensual': to_float(request.form.get('ingreso_mensual'), 0.0),
        'tipo_cliente': request.form.get('tipo_cliente', 'Nuevo').strip() or 'Nuevo',
        'presupuesto': to_float(request.form.get('presupuesto'), 0.0),
    }
    if payload['nombre'] and payload['email']:
        try:
            get_db().clientes.update_one({'_id': ObjectId(cliente_id)}, {'$set': payload})
        except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
            pass
    return redirect('/clientes')


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

    query = request.args.get('q', '').strip()
    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))
    filtro = {}
    if query:
        filtro = {
            '$or': [
                {'nombre': {'$regex': query, '$options': 'i'}},
                {'apellido': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}},
                {'telefono': {'$regex': query, '$options': 'i'}},
            ]
        }
    vendedores, total, total_pages, current_page = paginate_collection('vendedores', filtro, page, per_page=per_page)
    return render_template('vendedores.html', vendedores=vendedores, query=query, page=current_page, total_pages=total_pages, total=total, per_page=per_page)


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

    page = to_int(request.args.get('page', 1), 1)
    per_page = to_int(request.args.get('per_page', 10), 10)
    per_page = max(5, min(per_page, 100))

    try:
        db = get_db()
        pagos, pagos_total, total_pages, current_page = paginate_collection(
            'pagos', filtro_pagos, page, per_page=per_page
        )
        ventas = list(db.ventas.find(filtro_ventas))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        pagos = []
        pagos_total = 0
        total_pages = 0
        current_page = 1
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
        pagos_total=pagos_total,
        page=current_page,
        total_pages=total_pages,
        total=pagos_total,
        per_page=per_page,
        venta_total=venta_total,
        ventas_por_marca=report_data['ventas_por_marca'],
        evolucion_mensual=report_data['evolucion_mensual'],
        ventas_por_mes=report_data['ventas_por_mes'],
        tickets_por_mes=report_data['tickets_por_mes'],
        desde=desde,
        hasta=hasta,
    )


# --------------------------------------------------------------------------
# Generación del PDF de reportes
# --------------------------------------------------------------------------
def _tabla_estilo(num_rows, right_cols=None):
    """Construye un TableStyle reutilizable: encabezado morado, texto oscuro,
    filas alternadas (zebra) y alineación derecha opcional para columnas
    numéricas."""
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_DARK),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, PURPLE_DARK),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, GRID_LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for row in range(1, num_rows):
        if row % 2 == 0:
            cmds.append(('BACKGROUND', (0, row), (-1, row), ROW_ALT))
    for col in right_cols or []:
        cmds.append(('ALIGN', (col, 0), (col, -1), 'RIGHT'))
    return TableStyle(cmds)


def _make_canvas_factory(desde, hasta, logo_path):
    """Crea una subclase de Canvas que dibuja encabezado (logo + título) y
    pie de página (fecha de generación + "Página X de Y") en cada página,
    usando el truco de doble pasada de reportlab para conocer el total de
    páginas antes de escribir el pie."""

    class ReportCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdfcanvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_header_footer(num_pages)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def _draw_header_footer(self, page_count):
            width, height = A4
            self.saveState()
            if logo_path and os.path.exists(logo_path):
                self.drawImage(
                    ImageReader(logo_path), 40, height - 75, width=85, height=38,
                    preserveAspectRatio=True, mask='auto'
                )
            self.setFillColor(PURPLE_DARK)
            self.setFont('Helvetica-Bold', 16)
            self.drawString(140, height - 48, 'Reporte de operaciones')
            self.setFont('Helvetica', 9)
            self.setFillColor(PURPLE)
            self.drawString(140, height - 62, 'Usagi Motors | Resumen comercial')
            self.setStrokeColor(PINK)
            self.setLineWidth(1.5)
            self.line(40, height - 85, width - 40, height - 85)

            self.setFont('Helvetica', 8)
            self.setFillColor(GRAY)
            periodo = f"Periodo: {desde or 'Inicio'} - {hasta or 'Actual'}"
            generado = f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  {periodo}"
            self.drawString(40, 25, generado)
            self.drawRightString(width - 40, 25, f"Página {self._pageNumber} de {page_count}")
            self.restoreState()

    return ReportCanvas


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
        pagos = list(db.pagos.find(filtro_pagos).sort('fecha_pago', -1))
        ventas = list(db.ventas.find(filtro_ventas))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        pagos = []
        ventas = []

    venta_total = sum(float(v['total']) for v in ventas if 'total' in v)
    ticket_promedio = (venta_total / len(ventas)) if ventas else 0.0

    df = obtener_df_visualizacion()
    if desde or hasta:
        mask = pd.Series(True, index=df.index)
        if desde:
            mask &= df['fecha_venta'] >= pd.Timestamp(desde)
        if hasta:
            mask &= df['fecha_venta'] <= pd.Timestamp(hasta)
        df = df[mask]
    report_data = obtener_datos_reportes_negocio(df)

    # --- Estilos de texto ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='SeccionTitulo', fontName='Helvetica-Bold', fontSize=13,
        textColor=PURPLE_DARK, spaceBefore=14, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='TextoNormalOscuro', fontName='Helvetica', fontSize=9.5,
        textColor=TEXT_DARK, leading=13,
    ))
    styles.add(ParagraphStyle(
        name='KpiLabel', fontName='Helvetica', fontSize=7.5,
        textColor=PURPLE, leading=10,
    ))
    styles.add(ParagraphStyle(
        name='KpiValue', fontName='Helvetica-Bold', fontSize=14,
        textColor=TEXT_DARK, leading=18, spaceBefore=2,
    ))

    story = []
    story.append(Paragraph(
        f"Periodo evaluado: {desde or 'Inicio'} &ndash; {hasta or 'Actual'}",
        styles['TextoNormalOscuro']
    ))
    story.append(Spacer(1, 12))

    # --- Tarjetas KPI ---
    kpis = [
        ('VENTAS TOTALES', format_currency(venta_total)),
        ('PAGOS REGISTRADOS', str(len(pagos))),
        ('TICKET PROMEDIO', format_currency(ticket_promedio)),
        ('ESTADO DE PAGOS', 'Activos' if pagos else 'Sin pagos'),
    ]
    kpi_row = [[Paragraph(label, styles['KpiLabel']), ] for label, _ in kpis]
    kpi_cells = [
        [Paragraph(label, styles['KpiLabel']), Paragraph(value, styles['KpiValue'])]
        for label, value in kpis
    ]
    kpi_table = Table([[c for c in kpi_cells]], colWidths=[123] * 4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PURPLE_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 6, colors.white),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 18))

    # --- Ventas por marca ---
    story.append(Paragraph('Ventas por marca', styles['SeccionTitulo']))
    marca_rows = report_data.get('ventas_por_marca', [])
    if marca_rows:
        data = [['Marca', 'Ventas']]
        for item in marca_rows:
            data.append([item.get('marca', 'Sin marca'), format_currency(item.get('ventas', 0))])
        marca_table = Table(data, colWidths=[300, 192], repeatRows=1)
        marca_table.setStyle(_tabla_estilo(len(data), right_cols=[1]))
        story.append(marca_table)
    else:
        story.append(Paragraph('Sin datos disponibles para el periodo seleccionado.', styles['TextoNormalOscuro']))
    story.append(Spacer(1, 18))

    # --- Evolución mensual ---
    story.append(Paragraph('Evolución mensual', styles['SeccionTitulo']))
    mes_rows = report_data.get('evolucion_mensual', [])
    if mes_rows:
        data = [['Mes', 'Ventas']]
        for item in mes_rows:
            data.append([item.get('mes', ''), format_currency(item.get('ventas', 0))])
        mes_table = Table(data, colWidths=[300, 192], repeatRows=1)
        mes_table.setStyle(_tabla_estilo(len(data), right_cols=[1]))
        story.append(mes_table)
    else:
        story.append(Paragraph('Sin datos disponibles para el periodo seleccionado.', styles['TextoNormalOscuro']))
    story.append(Spacer(1, 18))

    # --- Detalle de pagos (tabla completa, con encabezado repetido en cada página) ---
    story.append(Paragraph(f'Detalle de pagos ({len(pagos)})', styles['SeccionTitulo']))
    if pagos:
        data = [['Cliente', 'Monto', 'Estado', 'Fecha']]
        estado_por_fila = []
        for idx, p in enumerate(pagos, start=1):
            fecha = p.get('fecha_pago')
            fecha_str = fecha.strftime('%Y-%m-%d') if fecha else ''
            estado = p.get('estado', '')
            data.append([str(p.get('cliente_id', '')), format_currency(p.get('monto', 0)), estado, fecha_str])
            estado_por_fila.append((idx, str(estado).lower()))

        pagos_table = Table(data, colWidths=[190, 110, 110, 82], repeatRows=1)
        estilo = _tabla_estilo(len(data), right_cols=[1])
        for idx, estado in estado_por_fila:
            color = GREEN if estado == 'pagado' else (ORANGE if estado == 'pendiente' else TEXT_DARK)
            estilo.add('TEXTCOLOR', (2, idx), (2, idx), color)
            estilo.add('FONTNAME', (2, idx), (2, idx), 'Helvetica-Bold')
        pagos_table.setStyle(estilo)
        story.append(pagos_table)
    else:
        story.append(Paragraph('No hay pagos registrados en el periodo seleccionado.', styles['TextoNormalOscuro']))

    buffer = io.BytesIO()
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'usagi_motors.png')

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=100, bottomMargin=50, leftMargin=40, rightMargin=40,
        title='Reporte Usagi Motors',
    )
    doc.build(story, canvasmaker=_make_canvas_factory(desde, hasta, logo_path))

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