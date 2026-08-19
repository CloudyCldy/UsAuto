import base64
import io

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from config.database import get_db


def obtener_datos_reportes_negocio(df=None):
    """Devuelve datos listos para gráficos interactivos de negocio."""
    if df is None:
        df = obtener_df_visualizacion()

    if df.empty:
        return {
            'ventas_por_marca': [],
            'ventas_por_vendedor': [],
            'evolucion_mensual': [],
            'ventas_por_mes': [],
            'tickets_por_mes': [],
        }

    ventas_marca = (
        df.groupby('marca', as_index=False)['total']
        .sum()
        .sort_values('total', ascending=False)
        .rename(columns={'total': 'ventas'})
    )

    evolucion = (
        df.groupby('mes', as_index=False)['total']
        .sum()
        .sort_values('mes')
        .rename(columns={'total': 'ventas'})
    )

    ventas_vendedor = pd.DataFrame(columns=['vendedor', 'ventas'])
    if 'vendedor' in df.columns:
        ventas_vendedor = (
            df.assign(vendedor=df['vendedor'].fillna('Sin vendedor'))
            .groupby('vendedor', as_index=False)['total']
            .sum()
            .sort_values('total', ascending=False)
            .rename(columns={'total': 'ventas'})
        )

    datos = {
        'ventas_por_marca': [
            {'marca': row['marca'], 'ventas': float(row['ventas'])}
            for _, row in ventas_marca.iterrows()
        ],
        'ventas_por_vendedor': [
            {'vendedor': row['vendedor'], 'ventas': float(row['ventas'])}
            for _, row in ventas_vendedor.iterrows()
        ],
        'evolucion_mensual': [
            {'mes': row['mes'], 'ventas': float(row['ventas'])}
            for _, row in evolucion.iterrows()
        ],
        'ventas_por_mes': [
            {'x': row['mes'], 'y': float(row['ventas'])}
            for _, row in evolucion.iterrows()
        ],
        'tickets_por_mes': [
            {'x': row['mes'], 'y': int((df[df['mes'] == row['mes']].shape[0]))}
            for _, row in evolucion.iterrows()
        ],
    }
    return datos


def obtener_df_visualizacion():
    try:
        db = get_db()
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        return pd.DataFrame()

    pipeline = [
        {'$lookup': {'from': 'vehiculos', 'localField': 'vehiculo_id', 'foreignField': '_id', 'as': 'vehiculo'}},
        {'$lookup': {'from': 'vendedores', 'localField': 'vendedor_id', 'foreignField': '_id', 'as': 'vendedor'}},
        {'$lookup': {'from': 'sucursales', 'localField': 'sucursal_id', 'foreignField': '_id', 'as': 'sucursal'}},
        {'$unwind': '$vehiculo'},
        {'$unwind': {'path': '$vendedor', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': '$sucursal'},
        {'$project': {
            '_id': 1,
            'fecha_venta': 1,
            'total': 1,
            'marca': '$vehiculo.marca',
            'modelo': '$vehiculo.modelo',
            'tipo': '$vehiculo.tipo',
            'precio': '$vehiculo.precio',
            'vendedor': '$vendedor.nombre',
            'sucursal': '$sucursal.nombre',
            'ciudad': '$sucursal.ciudad'
        }}
    ]
    try:
        docs = list(db.ventas.aggregate(pipeline))
    except Exception:
        return pd.DataFrame()

    df = pd.DataFrame(docs)
    if not df.empty:
        df['fecha_venta'] = pd.to_datetime(df['fecha_venta'])
        df['mes'] = df['fecha_venta'].dt.to_period('M').astype(str)
    return df


def _figura_a_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return 'data:image/png;base64,' + encoded


def generar_graficas_base64(df=None):
    df = obtener_df_visualizacion() if df is None else df
    if df.empty:
        return {}

    graficas = {}

    if 'vendedor' in df.columns:
        ventas_vendedor = (
            df.assign(vendedor=df['vendedor'].fillna('Sin vendedor'))
            .groupby('vendedor', as_index=False)['total']
            .sum()
            .sort_values('total', ascending=False)
            .head(10)
        )
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=ventas_vendedor, x='total', y='vendedor', ax=ax, color='#6C3FA8')
        ax.set_title('Vendedores con mas ventas')
        ax.set_xlabel('Ventas')
        ax.set_ylabel('Vendedor')
        fig.tight_layout()
        graficas['ventas_por_vendedor'] = _figura_a_base64(fig)

    ventas_marca = df.groupby('marca', as_index=False)['total'].sum().sort_values('total', ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=ventas_marca, x='marca', y='total', ax=ax, palette='viridis', hue='marca', dodge=False, legend=False)
    ax.set_title('Ventas por marca')
    ax.set_xlabel('Marca')
    ax.set_ylabel('Ventas')
    fig.tight_layout()
    graficas['ventas_por_marca'] = _figura_a_base64(fig)

    tipos = df['tipo'].value_counts()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(tipos.values, labels=tipos.index, autopct='%1.1f%%', startangle=90)
    ax.set_title('Distribución de ventas por tipo de vehículo')
    fig.tight_layout()
    graficas['ventas_por_tipo'] = _figura_a_base64(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df['precio'], bins=20, kde=True, ax=ax)
    ax.set_title('Distribución de precios de vehículos')
    ax.set_xlabel('Precio')
    ax.set_ylabel('Frecuencia')
    fig.tight_layout()
    graficas['hist_precio_vehiculos'] = _figura_a_base64(fig)

    try:
        clientes = pd.DataFrame(list(get_db().clientes.find()))
    except (PyMongoError, ServerSelectionTimeoutError, OSError, ValueError):
        clientes = pd.DataFrame()
    if not clientes.empty:
        clientes['ingreso_mensual'] = pd.to_numeric(clientes['ingreso_mensual'], errors='coerce')
        clientes = clientes[['ingreso_mensual', 'presupuesto']].dropna()
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(data=clientes, x='ingreso_mensual', y='presupuesto', ax=ax)
        ax.set_title('Ingreso mensual vs presupuesto')
        ax.set_xlabel('Ingreso mensual')
        ax.set_ylabel('Presupuesto')
        fig.tight_layout()
        graficas['ingreso_vs_presupuesto'] = _figura_a_base64(fig)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=df, x='marca', y='precio', ax=ax, orient='v')
    ax.set_title('Precio de vehículos por marca')
    ax.set_xlabel('Marca')
    ax.set_ylabel('Precio')
    fig.tight_layout()
    graficas['precio_por_marca'] = _figura_a_base64(fig)

    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        corr = numeric_df.corr()
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, annot=True, cmap='coolwarm', ax=ax)
        ax.set_title('Mapa de calor de correlaciones')
        fig.tight_layout()
        graficas['mapa_calor'] = _figura_a_base64(fig)

    if 'mes' in df.columns:
        monthly = df.groupby('mes', as_index=False)['total'].sum()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.fill_between(monthly['mes'], monthly['total'], alpha=0.5)
        ax.plot(monthly['mes'], monthly['total'])
        ax.set_title('Evolución mensual de ventas')
        ax.set_xlabel('Mes')
        ax.set_ylabel('Ventas')
        plt.xticks(rotation=45)
        fig.tight_layout()
        graficas['evolucion_mensual_ventas'] = _figura_a_base64(fig)

    return graficas


def guardar_graficas():
    return generar_graficas_base64()
