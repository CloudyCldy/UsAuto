import os
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from config.database import get_db


def obtener_datos_cluster():
    db = get_db()
    clientes = list(db.clientes.find())
    if not clientes:
        return pd.DataFrame()
    df = pd.DataFrame(clientes)
    df['gasto_promedio'] = np.random.uniform(5000, 120000, len(df))
    df['numero_compras'] = np.random.randint(0, 10, len(df))
    df['numero_cotizaciones'] = np.random.randint(0, 8, len(df))
    cols = ['edad', 'ingreso_mensual', 'gasto_promedio', 'numero_compras', 'numero_cotizaciones', 'visitas_agencia']
    return df[cols].copy()


def seleccionar_k(datos, max_k=10):
    if datos.empty:
        return 3
    scaler = StandardScaler()
    X = scaler.fit_transform(datos)
    inertias = []
    for k in range(1, max_k + 1):
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
    return inertias


def entrenar_kmeans():
    datos = obtener_datos_cluster()
    if datos.empty:
        return None
    scaler = StandardScaler()
    X = scaler.fit_transform(datos)
    inertias = seleccionar_k(datos)
    k = 3 if len(inertias) >= 3 else len(inertias)
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    clusters = model.fit_predict(X)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'), exist_ok=True)
    joblib.dump(model, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'kmeans.pkl'))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(range(1, len(inertias) + 1), inertias, marker='o')
    ax.set_title('Método del codo')
    ax.set_xlabel('K')
    ax.set_ylabel('Inertia')
    fig.tight_layout()
    return {'model': model, 'clusters': clusters, 'k': k, 'inertia': model.inertia_, 'figure': fig}
