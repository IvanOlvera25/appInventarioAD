from app import app, db
from sqlalchemy import text, inspect

def run_migration():
    """Ejecutar migración manual de tablas para agregar columnas faltantes"""
    print("🚀 Iniciando migración manual de base de datos...")

    with app.app_context():
        inspector = inspect(db.engine)

        # 1. Migrar tabla REQUEST
        if 'request' in inspector.get_table_names():
            print("Verificando tabla 'request'...")
            columns = [col['name'] for col in inspector.get_columns('request')]
            # Usar conexión cruda para evitar problemas de transacción con DDL
            with db.engine.connect() as conn:
                try:
                    trans = conn.begin()
                    if 'acquisition_deadline' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN acquisition_deadline DATE'))
                        print("  ✅ Columna 'acquisition_deadline' agregada")
                    if 'production_start_date' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN production_start_date DATE'))
                        print("  ✅ Columna 'production_start_date' agregada")
                    if 'has_returns' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN has_returns BOOLEAN DEFAULT 0'))
                        print("  ✅ Columna 'has_returns' agregada")
                    # Nuevos campos de cancelación
                    if 'cancellation_requested' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN cancellation_requested BOOLEAN DEFAULT 0'))
                        print("  ✅ Columna 'cancellation_requested' agregada")
                    if 'cancellation_requested_by' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN cancellation_requested_by INTEGER'))
                        print("  ✅ Columna 'cancellation_requested_by' agregada")
                    if 'cancellation_requested_at' not in columns:
                        conn.execute(text('ALTER TABLE request ADD COLUMN cancellation_requested_at DATETIME'))
                        print("  ✅ Columna 'cancellation_requested_at' agregada")
                    trans.commit()
                except AttributeError:
                    pass
                except Exception as e:
                    print(f"  ℹ️ Nota sobre request: {e}")

        # 2. Migrar tabla MATERIAL
        if 'material' in inspector.get_table_names():
            print("Verificando tabla 'material'...")
            columns = [col['name'] for col in inspector.get_columns('material')]
            with db.engine.connect() as conn:
                try:
                    if 'fabric_width' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN fabric_width FLOAT'))
                        print("  ✅ Columna 'fabric_width' agregada")
                    if 'is_recycled' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN is_recycled BOOLEAN DEFAULT 0'))
                        print("  ✅ Columna 'is_recycled' agregada")
                    if 'is_pre_recycled' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN is_pre_recycled BOOLEAN DEFAULT 0'))
                        print("  ✅ Columna 'is_pre_recycled' agregada")
                    if 'recycled_from_id' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN recycled_from_id INTEGER'))
                        print("  ✅ Columna 'recycled_from_id' agregada")
                    if 'category_id' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN category_id INTEGER'))
                        print("  ✅ Columna 'category_id' agregada")
                    if 'unit_id' not in columns:
                        conn.execute(text('ALTER TABLE material ADD COLUMN unit_id INTEGER'))
                        print("  ✅ Columna 'unit_id' agregada")
                    if hasattr(conn, 'commit'):
                        conn.commit()
                except Exception as e:
                    print(f"❌ Error durante migración de material: {e}")

        # 3. Migrar tabla REQUEST_ITEM
        if 'request_item' in inspector.get_table_names():
            print("Verificando tabla 'request_item'...")
            columns = [col['name'] for col in inspector.get_columns('request_item')]
            with db.engine.connect() as conn:
                try:
                    if 'item_status' not in columns:
                        conn.execute(text("ALTER TABLE request_item ADD COLUMN item_status VARCHAR(50) DEFAULT 'pendiente'"))
                        print("  ✅ Columna 'item_status' agregada")
                    if 'quantity_to_purchase' not in columns:
                        conn.execute(text('ALTER TABLE request_item ADD COLUMN quantity_to_purchase FLOAT DEFAULT 0'))
                        print("  ✅ Columna 'quantity_to_purchase' agregada")
                    if 'quantity_supplied' not in columns:
                        conn.execute(text('ALTER TABLE request_item ADD COLUMN quantity_supplied FLOAT DEFAULT 0'))
                        print("  ✅ Columna 'quantity_supplied' agregada")
                    if 'item_notes' not in columns:
                        conn.execute(text('ALTER TABLE request_item ADD COLUMN item_notes TEXT'))
                        print("  ✅ Columna 'item_notes' agregada")
                    if 'actual_return_date' not in columns:
                        conn.execute(text('ALTER TABLE request_item ADD COLUMN actual_return_date DATE'))
                        print("  ✅ Columna 'actual_return_date' agregada")
                    if hasattr(conn, 'commit'):
                        conn.commit()
                except Exception as e:
                    print(f"❌ Error durante migración de request_item: {e}")

        # 4. Crear tablas nuevas
        try:
            db.create_all()
            print("✅ Tablas Category y Unit verificadas")
        except Exception as e:
            print(f"⚠️ Alerta verificando tablas nuevas: {e}")

    print("\n✨ Migración completada.")

if __name__ == "__main__":
    run_migration()

