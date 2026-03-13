"""
Script para verificar estructura de tabla Datos
"""
import pymysql
import pymysql.cursors

connection_params = {
    "host": "ad17solutions.dscloud.me",
    "port": 3307,
    "user": "IvanUriel",
    "password": "iuOp20!!25",
    "database": "AD17_Materiales",
    "charset": 'utf8mb4',
    "cursorclass": pymysql.cursors.DictCursor
}

try:
    conn = pymysql.connect(**connection_params)
    with conn.cursor() as cursor:
        print("="*70)
        print("📋 ESTRUCTURA DE LA TABLA Datos")
        print("="*70)
        cursor.execute("DESCRIBE Datos;")
        for col in cursor.fetchall():
            print(f"  {col['Field']:20} | {col['Type']:20} | {col['Null']:5}")
        
        print("\n" + "="*70)
        print("📦 MUESTRA DE DATOS (3 registros)")
        print("="*70)
        cursor.execute("SELECT * FROM Datos LIMIT 3;")
        for row in cursor.fetchall():
            print(row)
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
