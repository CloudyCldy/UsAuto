import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from config.database import get_db


def obtener_datos_pca():
    db = get_db()
    clientes = list(db.clientes.find())
    if not clientes:
        return pd.DataFrame()
    df = pd.DataFrame(clientes)
    df['gasto_promedio'] = np.random.uniform(5000, 90000, len(df))
    df['numero_compras'] = np.random.randint(0, 10, len(df))
    df['numero_cotizaciones'] = np.random.randint(0, 8, len(df))
    return df[['edad', 'ingreso_mensual', 'gasto_promedio', 'numero_compras', 'numero_cotizaciones', 'visitas_agencia']].copy()


def entrenar_pca():
    datos = obtener_datos_pca()
    if datos.empty:
        return None
    scaler = StandardScaler()
    X = scaler.fit_transform(datos)
    pca = PCA(n_components=2)
    componentes = pca.fit_transform(X)
    varianza = pca.explained_variance_ratio_
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'), exist_ok=True)
    joblib.dump(pca, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'pca.pkl'))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(range(1, len(varianza) + 1), np.cumsum(varianza), marker='o')
    ax.set_title('Varianza explicada por componente')
    ax.set_xlabel('Componente principal')
    ax.set_ylabel('Varianza acumulada')
    fig.tight_layout()
    return {'model': pca, 'componentes': componentes, 'varianza': varianza, 'figure': fig}
