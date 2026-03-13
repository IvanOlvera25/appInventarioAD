# seed_verification_real.py
# Crea códigos de verificación reales (no dummy) para usuarios del sistema
# Uso:
#   python3 seed_verification_real.py

from datetime import datetime, timedelta
from sqlalchemy import text
from app import app, db

# === CONFIGURACIÓN ===
VERIFICATION_CODES = [
    # (código, rol, descripción)
    ("AD17-REQ-2025-KEY", "requisitador", "Código para creación de usuarios Requisitadores"),
    ("AD17-ALM-2025-KEY", "almacenista", "Código para creación de usuarios Almacenistas"),
    ("AD17-ADM-2025-KEY", "admin", "Código para creación de Administradores del sistema"),
]

EXP_DAYS = 365  # 1 año de vigencia


def seed_verification_codes():
    print("🔐 Insertando códigos de verificación REALES…")
    created = 0

    # Crear tabla si no existe (por compatibilidad)
    with db.engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS verification_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                used_by INTEGER NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME NOT NULL,
                notes TEXT NULL
            )
        """))
        conn.commit()

    for code, role, note in VERIFICATION_CODES:
        exists = db.session.execute(
            text("SELECT 1 FROM verification_code WHERE code = :code"),
            {"code": code}
        ).first()
        if exists:
            print(f"   ⚠️  Ya existe el código {code}, se omite.")
            continue

        db.session.execute(
            text("""
                INSERT INTO verification_code (code, role, expires_at, used_by, is_active, created_at, notes)
                VALUES (:code, :role, :exp, NULL, 1, :created, :note)
            """),
            {
                "code": code,
                "role": role,
                "exp": datetime.utcnow() + timedelta(days=EXP_DAYS),
                "created": datetime.utcnow(),
                "note": note
            }
        )
        created += 1

    db.session.commit()
    print(f"✅ Códigos creados: {created}")
    print("Finalizado correctamente.")


if __name__ == "__main__":
    with app.app_context():
        seed_verification_codes()