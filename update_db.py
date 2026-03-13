import sqlite3
from app import app, db
from sqlalchemy import text

def run_migrations():
    """
    Script seguro para agregar columnas faltantes en PythonAnywhere.
    Verifica si las columnas existen antes de intentar agregarlas.
    """
    with app.app_context():
        print("Iniciando verificación de base de datos...")
        
        # 1. Verificar tabla PROJECT
        print("\n--- Verificando tabla PROJECT ---")
        try:
            # Usamos db.engine.begin() para manejar la transacción automáticamente
            with db.engine.begin() as conn:
                # Para SQLite/MySQL la sintaxis puede variar, pero esto es genérico
                try:
                    # Inspeccionar columnas
                    result = conn.execute(text("SELECT * FROM project LIMIT 1"))
                    columns = result.keys()
                except Exception:
                    # Si falla, intentamos otra forma o asumimos vacío
                    columns = []

                # Lista de columnas requeridas y su tipo
                required_columns = {
                    'client': 'VARCHAR(150)',
                    'production_start': 'DATE',
                    'assembly_date': 'DATE',
                    'analysis_date': 'DATE'
                }

                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        print(f"Agregando columna faltante: {col_name}...")
                        conn.execute(text(f"ALTER TABLE project ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ Columna {col_name} agregada.")
                    else:
                        print(f"ℹ️ Columna {col_name} ya existe.")

        except Exception as e:
            print(f"❌ Error verificando tabla project: {e}")

        # 2. Verificar tabla REQUEST
        print("\n--- Verificando tabla REQUEST ---")
        try:
            with db.engine.begin() as conn:
                try:
                    result = conn.execute(text("SELECT * FROM request LIMIT 1"))
                    columns = result.keys()
                except:
                    columns = []

                # Lista de columnas requeridas
                required_columns = {
                    'is_incident': 'BOOLEAN DEFAULT 0',
                    'incident_id': 'VARCHAR(100)',
                    'acquisition_deadline': 'DATE',
                    'production_start_date': 'DATE',
                    'assembly_start_date': 'DATE',
                    'assembly_end_date': 'DATE',
                    'has_returns': 'BOOLEAN DEFAULT 0',
                    'cancellation_requested': 'BOOLEAN DEFAULT 0',
                    'cancellation_requested_by': 'INTEGER REFERENCES user(id)',
                    'cancellation_requested_at': 'DATETIME'
                }

                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        print(f"Agregando columna faltante: {col_name}...")
                        conn.execute(text(f"ALTER TABLE request ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ Columna {col_name} agregada.")
                    else:
                        print(f"ℹ️ Columna {col_name} ya existe.")

        except Exception as e:
            print(f"❌ Error verificando tabla request: {e}")

        # 3. Verificar tabla REQUEST_ITEM
        print("\n--- Verificando tabla REQUEST_ITEM ---")
        try:
            with db.engine.begin() as conn:
                try:
                    result = conn.execute(text("SELECT * FROM request_item LIMIT 1"))
                    columns = result.keys()
                except:
                    columns = []

                required_columns = {
                    'return_expected_date': 'DATE',
                    'will_recycle': 'BOOLEAN DEFAULT 0',
                    'item_status': "VARCHAR(50) DEFAULT 'pendiente'",
                    'quantity_to_purchase': 'FLOAT DEFAULT 0',
                    'quantity_supplied': 'FLOAT DEFAULT 0'
                }

                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        print(f"Agregando columna faltante: {col_name}...")
                        conn.execute(text(f"ALTER TABLE request_item ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ Columna {col_name} agregada.")
                    else:
                        print(f"ℹ️ Columna {col_name} ya existe.")
                        
        except Exception as e:
            print(f"❌ Error verificando tabla request_item: {e}")

        print("\n✅ Verificación y migración completada.")

if __name__ == "__main__":
    run_migrations()
