"""Muestra la definición de sp_resumen_fp y la forma de sus 3 resultsets."""
import sys
import pymysql
from config import Config as C

FP = sys.argv[1] if len(sys.argv) > 1 else None
if not FP:
    print('Uso: python3 inspeccionar_sp.py FP-2026-XXX   (un FP que tenga requisiciones)')
    sys.exit(1)

conn = pymysql.connect(host=C.REMOTE_DB_HOST, port=C.REMOTE_DB_PORT,
                       user=C.REMOTE_DB_USER, password=C.REMOTE_DB_PASSWORD,
                       database=C.MAIN_SCHEMA, charset='utf8mb4')
cur = conn.cursor()

print('=' * 100)
print('DEFINICIÓN DE sp_resumen_fp')
print('=' * 100)
try:
    cur.execute('SHOW CREATE PROCEDURE sp_resumen_fp')
    print(cur.fetchone()[2])
except Exception as e:
    print(f'No se pudo leer la definición: {e}')
while cur.nextset():
    pass

print()
print('=' * 100)
print(f'RESULTSETS DE CALL sp_resumen_fp("{FP}")')
print('=' * 100)
cur.callproc('sp_resumen_fp', (FP,))
n = 1
while True:
    cols = [d[0] for d in cur.description] if cur.description else []
    if cols:
        filas = cur.fetchall()
        print(f'\n--- RESULTSET {n} · {len(filas)} fila(s) ---')
        print('COLUMNAS:', cols)
        for f in filas[:6]:
            print('  ', f)
        if len(filas) > 6:
            print(f'   ... y {len(filas) - 6} más')
        n += 1
    if not cur.nextset():
        break
conn.close()
