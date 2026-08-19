"""Create the initial application user without touching the business seed data."""

import sys
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.database import get_db


SEED_USER = {
    'nombre': 'Administrador',
    'username': 'admin',
    'email': 'admin@usagimotors.com',
    'password': 'Usagi123!',
    'role': 'admin',
}


def seed_users():
    db = get_db()
    db.usuarios.update_one(
        {'username': SEED_USER['username']},
        {
            '$set': {
                'nombre': SEED_USER['nombre'],
                'email': SEED_USER['email'],
                'password_hash': generate_password_hash(SEED_USER['password']),
                'role': SEED_USER['role'],
                'activo': True,
            },
            '$setOnInsert': {'created_at': datetime.utcnow()},
        },
        upsert=True,
    )
    print(f"Usuario creado/actualizado: {SEED_USER['email']}")
    print(f"Contraseña inicial: {SEED_USER['password']}")


if __name__ == '__main__':
    seed_users()