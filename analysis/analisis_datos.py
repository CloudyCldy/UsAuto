import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from config.database import get_db


def obtener_ventas_dataframe():
    try:
        db = get_db()
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return pd.DataFrame()

    pipeline = [
        {
            '$lookup': {
                'from': 'vehiculos',
                'localField': 'vehiculo_id',
                'foreignField': '_id',
                'as': 'vehiculo'
            }
        },
        {
            '$lookup': {
                'from': 'clientes',
                'localField': 'cliente_id',
                'foreignField': '_id',
                'as': 'cliente'
            }
        },
        {
            '$lookup': {
                'from': 'vendedores',
                'localField': 'vendedor_id',
                'foreignField': '_id',
                'as': 'vendedor'
            }
        },
        {
            '$lookup': {
                'from': 'sucursales',
                'localField': 'sucursal_id',
                'foreignField': '_id',
                'as': 'sucursal'
            }
        },
        {'$unwind': {'path': '$vehiculo', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$cliente', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$vendedor', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$sucursal', 'preserveNullAndEmptyArrays': True}},
        {'$project': {
            '_id': 1,
            'fecha_venta': 1,
            'precio_venta': 1,
            'total': 1,
            'marca': '$vehiculo.marca',
            'modelo': '$vehiculo.modelo',
            'tipo': '$vehiculo.tipo',
            'anio': '$vehiculo.anio',
            'cliente': '$cliente.nombre',
            'vendedor': '$vendedor.nombre',
            'sucursal': '$sucursal.nombre',
            'ciudad': '$sucursal.ciudad',
            'year': {'$year': '$fecha_venta'}
        }}
    ]
    try:
        datos = list(db.ventas.aggregate(pipeline))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return pd.DataFrame()

    df = pd.DataFrame(datos)
    if df.empty:
        return df
    df['fecha_venta'] = pd.to_datetime(df['fecha_venta'])
    return df


def analisis_ventas():
    df = obtener_ventas_dataframe()
    if df.empty:
        return {
            'ventas_por_marca': pd.DataFrame(),
            'ventas_por_modelo': pd.DataFrame(),
            'ventas_por_vendedor': pd.DataFrame(),
            'ventas_por_sucursal': pd.DataFrame(),
            'ventas_por_anio': pd.DataFrame(),
            'precio_promedio': 0,
            'ticket_promedio': 0,
        }
    ventas_por_marca = df.groupby('marca', as_index=False)['total'].sum().sort_values('total', ascending=False)
    ventas_por_modelo = df.groupby('modelo', as_index=False)['total'].sum().sort_values('total', ascending=False)
    ventas_por_vendedor = df.groupby('vendedor', as_index=False)['total'].sum().sort_values('total', ascending=False)
    ventas_por_sucursal = df.groupby('sucursal', as_index=False)['total'].sum().sort_values('total', ascending=False)
    ventas_por_anio = df.groupby('year', as_index=False)['total'].sum().sort_values('year', ascending=True)
    precio_promedio = float(df['precio_venta'].mean())
    ticket_promedio = float(df['total'].mean())
    return {
        'ventas_por_marca': ventas_por_marca,
        'ventas_por_modelo': ventas_por_modelo,
        'ventas_por_vendedor': ventas_por_vendedor,
        'ventas_por_sucursal': ventas_por_sucursal,
        'ventas_por_anio': ventas_por_anio,
        'precio_promedio': precio_promedio,
        'ticket_promedio': ticket_promedio,
    }


def obtener_metricas_dashboard():
    try:
        db = get_db()
        clientes = db.clientes.count_documents({})
        vehiculos = db.vehiculos.count_documents({})
        vendedores = db.vendedores.count_documents({})
        ventas = db.ventas.count_documents({})
        total_ingresos = float(sum(v['total'] for v in db.ventas.find({}, {'total': 1, '_id': 0})))
        ticket_promedio = total_ingresos / ventas if ventas else 0
        modelo_mas_vendido = db.ventas.aggregate([
            {'$lookup': {'from': 'vehiculos', 'localField': 'vehiculo_id', 'foreignField': '_id', 'as': 'vehiculo'}},
            {'$unwind': '$vehiculo'},
            {'$group': {'_id': '$vehiculo.modelo', 'total': {'$sum': 1}}},
            {'$sort': {'total': -1}},
            {'$limit': 1}
        ])
        mejor_vendedor = db.ventas.aggregate([
            {'$group': {'_id': '$vendedor_id', 'total': {'$sum': '$total'}}},
            {'$sort': {'total': -1}},
            {'$limit': 1}
        ])
        sucursal_mas_ventas = db.ventas.aggregate([
            {'$group': {'_id': '$sucursal_id', 'total': {'$sum': '$total'}}},
            {'$sort': {'total': -1}},
            {'$limit': 1}
        ])
        vendedor = next(db.vendedores.find({'_id': next(mejor_vendedor, {}).get('_id')}), None)
        sucursal = next(db.sucursales.find({'_id': next(sucursal_mas_ventas, {}).get('_id')}), None)

        return {
            'total_clientes': clientes,
            'total_vehiculos': vehiculos,
            'total_vendedores': vendedores,
            'total_ventas': ventas,
            'ingresos_totales': round(total_ingresos, 2),
            'ticket_promedio': round(ticket_promedio, 2),
            'modelo_mas_vendido': next(modelo_mas_vendido, {}).get('_id', 'N/A'),
            'mejor_vendedor': vendedor['nombre'] if vendedor else 'N/A',
            'sucursal_con_mas_ventas': sucursal['nombre'] if sucursal else 'N/A',
        }
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return {
            'total_clientes': 0,
            'total_vehiculos': 0,
            'total_vendedores': 0,
            'total_ventas': 0,
            'ingresos_totales': 0,
            'ticket_promedio': 0,
            'modelo_mas_vendido': 'N/A',
            'mejor_vendedor': 'N/A',
            'sucursal_con_mas_ventas': 'N/A',
        }
