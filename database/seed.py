from datetime import datetime, timedelta, timezone
import random
import sys
from pathlib import Path

# Ensure project root is on sys.path so `config` can be imported
# even when this script is run from the `database/` folder.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from bson import ObjectId
from pymongo import MongoClient
from config.database import MONGO_URI, MONGO_DB


random.seed(42)

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]


marcas = ["Toyota", "Honda", "Ford", "Chevrolet", "Nissan", "BMW", "Mercedes", "Volkswagen", "Mazda", "Hyundai"]
modelos_por_marca = {
    "Toyota": ["Corolla", "Hilux", "Yaris", "RAV4"],
    "Honda": ["Civic", "CR-V", "Accord", "Fit"],
    "Ford": ["Focus", "Explorer", "Mustang", "Escape"],
    "Chevrolet": ["Aveo", "Cruze", "Silverado", "Tracker"],
    "Nissan": ["Sentra", "Versa", "X-Trail", "Frontier"],
    "BMW": ["Serie 3", "X5", "Serie 1", "M4"],
    "Mercedes": ["Clase C", "GLE", "Clase A", "GLA"],
    "Volkswagen": ["Jetta", "Tiguan", "Golf", "Passat"],
    "Mazda": ["Mazda3", "CX-5", "Mazda6", "CX-30"],
    "Hyundai": ["Elantra", "Tucson", "Accent", "Santa Fe"],
}

tipos_vehiculo = ["Sedan", "SUV", "Pickup", "Hatchback", "Coupe"]
sucursales = [
    {"nombre": "Centro", "ciudad": "Monterrey", "estado": "Nuevo León"},
    {"nombre": "Sur", "ciudad": "Guadalajara", "estado": "Jalisco"},
    {"nombre": "Norte", "ciudad": "Mexico City", "estado": "CDMX"},
    {"nombre": "Poniente", "ciudad": "Puebla", "estado": "Puebla"},
]

tipos_cliente = ["Nuevo", "Frecuente", "VIP", "Empresarial"]

def limpiar_db():
    for nombre in [
        "clientes", "vehiculos", "vendedores", "cotizaciones", "ventas",
        "financiamientos", "pagos", "servicios", "refacciones", "inventario",
        "sucursales"
    ]:
        db[nombre].delete_many({})


def generar_sucursales():
    sucursal_docs = []
    for idx, sucursal in enumerate(sucursales, start=1):
        sucursal_docs.append({
            "_id": ObjectId(),
            "nombre": sucursal["nombre"],
            "ciudad": sucursal["ciudad"],
            "estado": sucursal["estado"],
            "direccion": f"{idx} Avenida {sucursal['nombre']}",
            "telefono": f"81{random.randint(10000000, 99999999)}",
            "activo": True,
            "created_at": datetime.now(timezone.utc),
        })
    db.sucursales.insert_many(sucursal_docs)
    return list(db.sucursales.find())


def generar_clientes():
    clientes = []
    for i in range(1, 201):
        edad = random.randint(22, 72)
        ingreso = random.randint(18000, 95000)
        historial = random.randint(0, 12)
        presupuesto = random.randint(250000, 1200000)
        clientes.append({
            "_id": ObjectId(),
            "nombre": f"Cliente {i}",
            "apellido_paterno": f"Apellido{chr(65 + (i % 26))}",
            "apellido_materno": f"Mat{chr(65 + ((i + 3) % 26))}",
            "email": f"cliente{i}@mail.com",
            "telefono": f"55{random.randint(10000000, 99999999)}",
            "edad": edad,
            "ingreso_mensual": ingreso,
            "historial_compras": historial,
            "tipo_cliente": random.choice(tipos_cliente),
            "presupuesto": presupuesto,
            "marca_interes": random.choice(marcas),
            "antiguedad_cliente": random.randint(0, 12),
            "visitas_agencia": random.randint(0, 20),
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "activo": True,
            "created_at": datetime.now(timezone.utc),
        })
    db.clientes.insert_many(clientes)
    return list(db.clientes.find())


def generar_vehiculos():
    vehiculos = []
    for i in range(1, 151):
        marca = random.choice(marcas)
        modelo = random.choice(modelos_por_marca[marca])
        precio = random.randint(180000, 1800000)
        vehiculos.append({
            "_id": ObjectId(),
            "marca": marca,
            "modelo": modelo,
            "anio": random.randint(2018, 2025),
            "tipo": random.choice(tipos_vehiculo),
            "precio": precio,
            "kilometraje": random.randint(5000, 150000),
            "color": random.choice(["Blanco", "Negro", "Rojo", "Azul", "Gris", "Plateado"]),
            "transmision": random.choice(["Automática", "Manual"]),
            "combustible": random.choice(["Gasolina", "Diésel", "Híbrido", "Eléctrico"]),
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "stock": random.randint(1, 20),
            "estado": random.choice(["Disponible", "Reservado", "Vendido"]),
            "tiempo_inventario_dias": random.randint(5, 220),
            "created_at": datetime.now(timezone.utc),
        })
    db.vehiculos.insert_many(vehiculos)
    return list(db.vehiculos.find())


def generar_vendedores():
    vendedores = []
    for i in range(1, 31):
        vendedores.append({
            "_id": ObjectId(),
            "nombre": f"Vendedor {i}",
            "apellido": f"ApellidoV{i}",
            "email": f"vendedor{i}@mail.com",
            "telefono": f"81{random.randint(10000000, 99999999)}",
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "comision": round(random.uniform(0.02, 0.08), 4),
            "activo": True,
            "created_at": datetime.now(timezone.utc),
        })
    db.vendedores.insert_many(vendedores)
    return list(db.vendedores.find())


def generar_cotizaciones(clientes, vendedores, sucursales):
    cotizaciones = []
    for i in range(1, 301):
        cliente = random.choice(clientes)
        vehiculo = random.choice(list(db.vehiculos.find()))
        vendedor = random.choice(vendedores)
        fecha = datetime.now(timezone.utc) - timedelta(days=random.randint(10, 700))
        precio = float(vehiculo["precio"])
        descuento = round(random.uniform(0, 0.12), 4)
        total = round(precio * (1 - descuento), 2)
        cotizaciones.append({
            "_id": ObjectId(),
            "cliente_id": cliente['_id'],
            "vehiculo_id": vehiculo['_id'],
            "vendedor_id": vendedor['_id'],
            "sucursal_id": vendedor['sucursal_id'],
            "fecha": fecha,
            "precio_base": precio,
            "descuento": descuento,
            "total": total,
            "estado": random.choice(["Pendiente", "Aprobada", "Rechazada", "Convertida"]),
            "created_at": datetime.now(timezone.utc),
        })
    db.cotizaciones.insert_many(cotizaciones)
    return list(db.cotizaciones.find())


def generar_ventas(clientes, vendedores, vehiculos, cotizaciones):
    ventas = []
    for i in range(1, 201):
        cliente = random.choice(clientes)
        vendedor = random.choice(vendedores)
        vehiculo = random.choice(vehiculos)
        venta_date = datetime.now(timezone.utc) - timedelta(days=random.randint(20, 500))
        subtotal = float(vehiculo["precio"])
        iva = round(subtotal * 0.16, 2)
        total = round(subtotal + iva, 2)
        ventas.append({
            "_id": ObjectId(),
            "cliente_id": cliente['_id'],
            "vehiculo_id": vehiculo['_id'],
            "vendedor_id": vendedor['_id'],
            "sucursal_id": vendedor['sucursal_id'],
            "fecha_venta": venta_date,
            "precio_venta": subtotal,
            "iva": iva,
            "total": total,
            "metodo_pago": random.choice(["Efectivo", "Tarjeta", "Transferencia", "Crédito"]),
            "estado": "Completada",
            "created_at": datetime.now(timezone.utc),
        })
    db.ventas.insert_many(ventas)
    return list(db.ventas.find())


def generar_financiamientos(ventas):
    financiamientos = []
    for venta in ventas[:150]:
        monto = float(venta['total'])
        plazo = random.choice([12, 18, 24, 36, 48, 60])
        tasa = round(random.uniform(0.08, 0.18), 4)
        financiamientos.append({
            "_id": ObjectId(),
            "venta_id": venta['_id'],
            "cliente_id": venta['cliente_id'],
            "sucursal_id": venta['sucursal_id'],
            "monto_financiado": round(monto * random.uniform(0.4, 0.8), 2),
            "plazo_meses": plazo,
            "tasa_interes": tasa,
            "enganche": round(monto * random.uniform(0.1, 0.35), 2),
            "cuota_mensual": round((monto * (1 + tasa)) / plazo, 2),
            "estatus": random.choice(["Aprobado", "En proceso", "Pagado"]),
            "created_at": datetime.now(timezone.utc),
        })
    db.financiamientos.insert_many(financiamientos)
    return list(db.financiamientos.find())


def generar_pagos(ventas):
    pagos = []
    for i in range(1, 301):
        venta = random.choice(ventas)
        financiamiento = random.choice(list(db.financiamientos.find())) if db.financiamientos.count_documents({}) > 0 else None
        fecha = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 300))
        pagos.append({
            "_id": ObjectId(),
            "venta_id": venta['_id'],
            "cliente_id": venta['cliente_id'],
            "financiamiento_id": financiamiento['_id'] if financiamiento else None,
            "fecha_pago": fecha,
            "monto": round(float(venta['total']) * random.uniform(0.1, 0.4), 2),
            "metodo": random.choice(["Efectivo", "Tarjeta", "Transferencia"]),
            "estado": random.choice(["Pagado", "Pendiente"]),
            "created_at": datetime.now(timezone.utc),
        })
    db.pagos.insert_many(pagos)
    return list(db.pagos.find())


def generar_servicios():
    servicios = []
    for i in range(1, 151):
        servicios.append({
            "_id": ObjectId(),
            "cliente_id": random.choice(list(db.clientes.find()))['_id'],
            "vehiculo_id": random.choice(list(db.vehiculos.find()))['_id'],
            "tipo_servicio": random.choice(["Mantenimiento", "Revisión", "Llantas", "Frenos", "Alineación"]),
            "descripcion": f"Servicio {i} de mantenimiento",
            "costo": round(random.uniform(900, 7500), 2),
            "fecha": datetime.now(timezone.utc) - timedelta(days=random.randint(2, 400)),
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "status": random.choice(["Completado", "En proceso"]),
            "created_at": datetime.now(timezone.utc),
        })
    db.servicios.insert_many(servicios)
    return list(db.servicios.find())


def generar_refacciones():
    refacciones = []
    for i in range(1, 201):
        refacciones.append({
            "_id": ObjectId(),
            "nombre": f"Refaccion {i}",
            "categoria": random.choice(["Motor", "Suspensión", "Frenos", "Aire", "Eléctrico"]),
            "marca": random.choice(marcas),
            "precio": round(random.uniform(180, 3500), 2),
            "stock": random.randint(5, 60),
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "created_at": datetime.now(timezone.utc),
        })
    db.refacciones.insert_many(refacciones)
    return list(db.refacciones.find())


def generar_inventario():
    inventario = []
    for i in range(1, 301):
        inventario.append({
            "_id": ObjectId(),
            "vehiculo_id": random.choice(list(db.vehiculos.find()))['_id'],
            "sucursal_id": random.choice(list(db.sucursales.find()))['_id'],
            "cantidad": random.randint(0, 15),
            "stock_minimo": random.randint(1, 5),
            "stock_maximo": random.randint(10, 25),
            "ubicacion": f"Pasillo {random.randint(1, 12)}",
            "ultimo_reabastecimiento": datetime.now(timezone.utc) - timedelta(days=random.randint(3, 120)),
            "created_at": datetime.now(timezone.utc),
        })
    db.inventario.insert_many(inventario)
    return list(db.inventario.find())


def seed_database():
    limpiar_db()
    sucursales = generar_sucursales()
    clientes = generar_clientes()
    vehiculos = generar_vehiculos()
    vendedores = generar_vendedores()
    cotizaciones = generar_cotizaciones(clientes, vendedores, sucursales)
    ventas = generar_ventas(clientes, vendedores, vehiculos, cotizaciones)
    financiamientos = generar_financiamientos(ventas)
    pagos = generar_pagos(ventas)
    servicios = generar_servicios()
    refacciones = generar_refacciones()
    inventario = generar_inventario()

    print(f"SUCURSALES: {len(sucursales)}")
    print(f"CLIENTES: {len(clientes)}")
    print(f"VEHICULOS: {len(vehiculos)}")
    print(f"VENDEDORES: {len(vendedores)}")
    print(f"COTIZACIONES: {len(cotizaciones)}")
    print(f"VENTAS: {len(ventas)}")
    print(f"FINANCIAMIENTOS: {len(financiamientos)}")
    print(f"PAGOS: {len(pagos)}")
    print(f"SERVICIOS: {len(servicios)}")
    print(f"REFACCIONES: {len(refacciones)}")
    print(f"INVENTARIO: {len(inventario)}")


if __name__ == "__main__":
    seed_database()
