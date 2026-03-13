#!/usr/bin/env python
# run_migration.py - Ejecutar UNA VEZ
import sqlite3

DB_PATH = '/home/IvanOlvera25/appInventario/almacen.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Ver columnas actuales
cursor.execute("PRAGMA table_info(request)")
existing = [col[1] for col in cursor.fetchall()]
print(f"Columnas actuales: {existing}")

# Agregar columnas faltantes
for col, dtype in [('acquisition_deadline', 'DATE'), ('production_start_date', 'DATE'), ('has_returns', 'BOOLEAN DEFAULT 0')]:
    if col not in existing:
        cursor.execute(f"ALTER TABLE request ADD COLUMN {col} {dtype}")
        print(f"✅ Agregada: {col}")
    else:
        print(f"ℹ️ Ya existe: {col}")

conn.commit()
conn.close()
print("✅ Migración completada")