import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from config.database import get_db
from pymongo import MongoClient


def obtener_dataset_cliente():
    db = get_db()
    pipeline = [
        {'$lookup': {'from': 'ventas', 'localField': '_id', 'foreignField': 'cliente_id', 'as': 'ventas'}},
        {'$project': {
            '_id': 1,
            'nombre': 1,
            'edad': 1,
            'ingreso_mensual': 1,
            'historial_compras': 1,
            'tipo_cliente': 1,
            'presupuesto': 1,
            'marca_interes': 1,
            'antiguedad_cliente': 1,
            'visitas_agencia': 1,
            'numero_cotizaciones': {'$size': {'$ifNull': ['$cotizaciones', []]}},
            'numero_compras': {'$size': '$ventas'},
            'gasto_promedio': {'$avg': '$ventas.total'},
        }}
    ]
    try:
        clientes = list(db.clientes.aggregate(pipeline))
    except Exception:
        clientes = list(db.clientes.find())
    if not clientes:
        return pd.DataFrame()
    df = pd.DataFrame(clientes)
    return df


def preparar_datos_ml():
    db = get_db()
    clientes = list(db.clientes.find())
    if not clientes:
        return pd.DataFrame(), None, None

    df = pd.DataFrame(clientes)
    df['numero_cotizaciones'] = np.random.randint(0, 8, size=len(df))
    df['gasto_promedio'] = np.random.uniform(3000, 300000, len(df))
    df['financiamiento'] = np.random.choice([0, 1], size=len(df), p=[0.55, 0.45])
    df['probabilidad_compra'] = np.random.choice([0, 1], size=len(df), p=[0.35, 0.65])

    columnas = [
        'edad', 'ingreso_mensual', 'historial_compras', 'numero_cotizaciones',
        'visitas_agencia', 'presupuesto', 'financiamiento', 'tipo_cliente',
        'marca_interes', 'antiguedad_cliente', 'probabilidad_compra'
    ]
    df = df[[col for col in columnas if col in df.columns]]

    df = df.drop_duplicates().reset_index(drop=True)
    df = df.fillna({
        'edad': df['edad'].median(),
        'ingreso_mensual': df['ingreso_mensual'].median(),
        'historial_compras': df['historial_compras'].median(),
        'numero_cotizaciones': df['numero_cotizaciones'].median(),
        'visitas_agencia': df['visitas_agencia'].median(),
        'presupuesto': df['presupuesto'].median(),
        'financiamiento': 0,
        'tipo_cliente': 'Nuevo',
        'marca_interes': 'Toyota',
        'antiguedad_cliente': df['antiguedad_cliente'].median(),
        'probabilidad_compra': 0
    })

    for col in ['tipo_cliente', 'marca_interes']:
        df[col] = df[col].astype(str)

    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    encoded = encoder.fit_transform(df[['tipo_cliente', 'marca_interes']])
    encoded_cols = encoder.get_feature_names_out(['tipo_cliente', 'marca_interes'])
    encoded_df = pd.DataFrame(encoded, columns=encoded_cols)

    df = pd.concat([df.drop(columns=['tipo_cliente', 'marca_interes']), encoded_df], axis=1)
    df['probabilidad_compra'] = df['probabilidad_compra'].astype(int)

    X = df.drop(columns=['probabilidad_compra'])
    y = df['probabilidad_compra']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    X_train_df = pd.DataFrame(X_train_scaled, columns=X.columns)
    X_test_df = pd.DataFrame(X_test_scaled, columns=X.columns)

    dataset = pd.concat([X_train_df, y_train.reset_index(drop=True)], axis=1)
    dataset = dataset.rename(columns={dataset.columns[-1]: 'probabilidad_compra'})
    dataset = pd.concat([dataset, pd.DataFrame({'probabilidad_compra': y_test.reset_index(drop=True)})], axis=0)

    ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dataset_ml.csv')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    dataset.to_csv(ruta, index=False)

    return dataset, X_train_df, y_train, X_test_df, y_test


def preparar_datos_cluster():
    db = get_db()
    clientes = list(db.clientes.find())
    df = pd.DataFrame(clientes)
    cols = ['edad', 'ingreso_mensual', 'historial_compras', 'visitas_agencia', 'presupuesto']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=cols).reset_index(drop=True)
    df['gasto_promedio'] = np.random.uniform(1000, 250000, size=len(df))
    df['numero_compras'] = np.random.randint(0, 10, size=len(df))
    df['numero_cotizaciones'] = np.random.randint(0, 12, size=len(df))
    return df[['edad', 'ingreso_mensual', 'gasto_promedio', 'numero_compras', 'numero_cotizaciones', 'visitas_agencia']]
