import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

from app import app

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from analysis.matriz_confusion import crear_matriz_confusion
from analysis.visualizacion import generar_graficas_base64, obtener_datos_reportes_negocio


class TestVisualizacion(unittest.TestCase):
    @patch('analysis.visualizacion.obtener_df_visualizacion')
    @patch('analysis.visualizacion.get_db')
    def test_generar_graficas_base64_no_crea_archivos(self, mock_get_db, mock_obtener_df_visualizacion):
        mock_obtener_df_visualizacion.return_value = pd.DataFrame([
            {
                'marca': 'Toyota',
                'total': 150000,
                'tipo': 'Sedán',
                'precio': 22000,
                'fecha_venta': '2024-01-15',
                'mes': '2024-01',
            },
            {
                'marca': 'Ford',
                'total': 200000,
                'tipo': 'Hatchback',
                'precio': 25000,
                'fecha_venta': '2024-02-15',
                'mes': '2024-02',
            },
        ])

        mock_db = type('FakeDB', (), {})()
        mock_db.clientes = type('FakeClientes', (), {'find': lambda self: [
            {'ingreso_mensual': 3500000, 'presupuesto': 30000000},
            {'ingreso_mensual': 4000000, 'presupuesto': 32000000},
        ]})()
        mock_get_db.return_value = mock_db

        graficas = generar_graficas_base64()

        self.assertIsInstance(graficas, dict)
        self.assertTrue(graficas)
        self.assertTrue(all(value.startswith('data:image/png;base64,') for value in graficas.values()))

    def test_obtener_datos_reportes_negocio(self):
        df = pd.DataFrame([
            {
                'marca': 'Toyota',
                'total': 150000,
                'fecha_venta': '2024-01-15',
                'mes': '2024-01',
            },
            {
                'marca': 'Toyota',
                'total': 220000,
                'fecha_venta': '2024-02-15',
                'mes': '2024-02',
            },
            {
                'marca': 'Ford',
                'total': 180000,
                'fecha_venta': '2024-02-20',
                'mes': '2024-02',
            },
        ])
        datos = obtener_datos_reportes_negocio(df)

        self.assertIn('ventas_por_marca', datos)
        self.assertIn('evolucion_mensual', datos)
        self.assertEqual(datos['ventas_por_marca'][0]['marca'], 'Toyota')
        self.assertEqual(datos['evolucion_mensual'][0]['mes'], '2024-01')

    @patch('app.get_db')
    @patch('app.obtener_df_visualizacion')
    def test_reportes_renderiza_graficos_interactivos(self, mock_obtener_df_visualizacion, mock_get_db):
        mock_db = type('FakeDB', (), {
            'pagos': type('FakeCollection', (), {'find': lambda self, *args, **kwargs: []})(),
            'ventas': type('FakeCollection', (), {'find': lambda self, *args, **kwargs: []})(),
        })()
        mock_get_db.return_value = mock_db
        mock_obtener_df_visualizacion.return_value = pd.DataFrame([
            {'marca': 'Toyota', 'total': 150000, 'fecha_venta': '2024-01-15', 'mes': '2024-01'},
            {'marca': 'Ford', 'total': 200000, 'fecha_venta': '2024-02-15', 'mes': '2024-02'},
        ])

        with app.test_client() as client:
            response = client.get('/reportes')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('chart.js', html.lower())
        self.assertNotIn('events: []', html)
        self.assertIn('tooltip', html)

    def test_crear_matriz_confusion_no_guarda_archivo(self):
        cm = crear_matriz_confusion([0, 1], [0, 1], title='Test')
        self.assertEqual(cm.shape, (2, 2))
        self.assertFalse(os.path.exists('confusion_matrix.png'))


if __name__ == '__main__':
    unittest.main()
