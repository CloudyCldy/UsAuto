import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from analysis.metricas import calcular_metricas
from analysis.matriz_confusion import crear_matriz_confusion
from config.database import get_db


def preparar_dataset_clasificacion():
    db = get_db()
    data = list(db.clientes.find())
    if not data:
        return None
    df = pd.DataFrame(data)
    df['numero_cotizaciones'] = np.random.randint(0, 10, size=len(df))
    df['financiamiento'] = np.random.choice([0, 1], size=len(df))
    df['probabilidad_compra'] = np.random.choice([0, 1], size=len(df), p=[0.4, 0.6])

    df = df[['edad', 'ingreso_mensual', 'historial_compras', 'numero_cotizaciones', 'visitas_agencia',
             'presupuesto', 'financiamiento', 'tipo_cliente', 'marca_interes', 'antiguedad_cliente', 'probabilidad_compra']].copy()

    for col in ['tipo_cliente', 'marca_interes']:
        df[col] = df[col].astype(str)

    categorical = ['tipo_cliente', 'marca_interes']
    numeric = [c for c in df.columns if c not in categorical + ['probabilidad_compra']]

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical),
        ]
    )

    X = df.drop(columns=['probabilidad_compra'])
    y = df['probabilidad_compra'].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    X_train_pre = preprocessor.fit_transform(X_train)
    X_test_pre = preprocessor.transform(X_test)

    return {
        'X_train': pd.DataFrame(X_train_pre, columns=preprocessor.get_feature_names_out()),
        'X_test': pd.DataFrame(X_test_pre, columns=preprocessor.get_feature_names_out()),
        'y_train': y_train,
        'y_test': y_test,
        'preprocessor': preprocessor,
        'modelos_dir': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    }


def entrenar_decision_tree():
    datos = preparar_dataset_clasificacion()
    if not datos:
        return None
    model = DecisionTreeClassifier(random_state=42, max_depth=5)
    model.fit(datos['X_train'], datos['y_train'])
    pred = model.predict(datos['X_test'])
    metrics = calcular_metricas(datos['y_test'], pred)
    os.makedirs(datos['modelos_dir'], exist_ok=True)
    artifact = {'model': model, 'preprocessor': datos['preprocessor'], 'feature_names': list(datos['X_train'].columns)}
    joblib.dump(artifact, os.path.join(datos['modelos_dir'], 'decision_tree.pkl'))
    cm = crear_matriz_confusion(datos['y_test'], pred, title='Decision Tree', filename=os.path.join(datos['modelos_dir'], 'decision_tree_confusion.png'))
    return {'model': model, 'pred': pred, 'metrics': metrics, 'cm': cm}


def entrenar_random_forest():
    datos = preparar_dataset_clasificacion()
    if not datos:
        return None
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(datos['X_train'], datos['y_train'])
    pred = model.predict(datos['X_test'])
    metrics = calcular_metricas(datos['y_test'], pred)
    os.makedirs(datos['modelos_dir'], exist_ok=True)
    artifact = {'model': model, 'preprocessor': datos['preprocessor'], 'feature_names': list(datos['X_train'].columns)}
    joblib.dump(artifact, os.path.join(datos['modelos_dir'], 'random_forest.pkl'))
    cm = crear_matriz_confusion(datos['y_test'], pred, title='Random Forest', filename=os.path.join(datos['modelos_dir'], 'random_forest_confusion.png'))
    return {'model': model, 'pred': pred, 'metrics': metrics, 'cm': cm}


def evaluar_modelos():
    dt = entrenar_decision_tree()
    rf = entrenar_random_forest()
    if dt is None or rf is None:
        return {'decision_tree': {}, 'random_forest': {}}
    return {
        'decision_tree': dt['metrics'],
        'random_forest': rf['metrics'],
    }
