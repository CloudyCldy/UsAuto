"""Paquete de análisis.

Se mantiene ligero para evitar efectos secundarios al importar un submódulo,
como la apertura de conexiones a MongoDB o carga de modelos pesados.
"""

__all__ = [
    'analisis_datos',
    'preparacion_datos',
    'clasificacion',
    'metricas',
    'matriz_confusion',
    'kmeans',
    'pca',
    'visualizacion',
]
