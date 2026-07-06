#!/usr/bin/env python3
"""Prueba de conexión a la base de datos MySQL remota."""

import socket
import time
import sys

HOST = "ad17solutions.dscloud.me"
PORT = 3307
USER = "IvanUriel"
PASSWORD = "iuOp20!!25"

SCHEMAS = [
    "AD17_Almacen",
    "AD17_Materiales",
    "AD17_General",
    "AD17_Proyectos",
    "AD17_Clientes",
    "AD17_RH",
]

def test_dns():
    """1. Resolver DNS"""
    print("=" * 60)
    print("1. TEST DNS — Resolviendo", HOST)
    print("=" * 60)
    try:
        ip = socket.gethostbyname(HOST)
        print(f"   ✅ DNS OK → {HOST} → {ip}")
        return ip
    except socket.gaierror as e:
        print(f"   ❌ DNS FALLÓ: {e}")
        return None

def test_tcp(ip):
    """2. Conectividad TCP al puerto"""
    print()
    print("=" * 60)
    print(f"2. TEST TCP — Conectando a {HOST}:{PORT}")
    print("=" * 60)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    start = time.time()
    try:
        sock.connect((ip or HOST, PORT))
        elapsed = time.time() - start
        print(f"   ✅ TCP OK — Puerto {PORT} abierto (latencia: {elapsed*1000:.0f}ms)")
        sock.close()
        return True
    except socket.timeout:
        print(f"   ❌ TCP TIMEOUT — No se pudo conectar en 10s")
        return False
    except ConnectionRefusedError:
        print(f"   ❌ TCP RECHAZADO — Puerto {PORT} cerrado")
        return False
    except OSError as e:
        print(f"   ❌ TCP ERROR: {e}")
        return False

def test_pymysql():
    """3. Conexión MySQL con pymysql"""
    print()
    print("=" * 60)
    print("3. TEST MySQL — Autenticación con pymysql")
    print("=" * 60)
    try:
        import pymysql
    except ImportError:
        print("   ⚠️  pymysql no instalado, intentando con pip...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "-q"])
        import pymysql

    try:
        start = time.time()
        conn = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            connect_timeout=15,
            read_timeout=10,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        elapsed = time.time() - start
        print(f"   ✅ MySQL AUTH OK (conectó en {elapsed*1000:.0f}ms)")

        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS ver, CURRENT_USER() AS usr")
            row = cur.fetchone()
            print(f"   📌 Versión MySQL: {row['ver']}")
            print(f"   📌 Usuario: {row['usr']}")

        conn.close()
        return True
    except pymysql.err.OperationalError as e:
        print(f"   ❌ MySQL ERROR: {e}")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_schemas():
    """4. Probar acceso a cada esquema"""
    print()
    print("=" * 60)
    print("4. TEST SCHEMAS — Verificando acceso a bases de datos")
    print("=" * 60)
    try:
        import pymysql
    except ImportError:
        print("   ❌ pymysql no disponible")
        return

    for schema in SCHEMAS:
        try:
            conn = pymysql.connect(
                host=HOST,
                port=PORT,
                user=USER,
                password=PASSWORD,
                database=schema,
                connect_timeout=15,
                read_timeout=10,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                tables = cur.fetchall()
                table_names = [list(t.values())[0] for t in tables]
                print(f"   ✅ {schema:20s} — {len(tables)} tablas: {', '.join(table_names[:5])}{'...' if len(tables) > 5 else ''}")
            conn.close()
        except pymysql.err.OperationalError as e:
            code = e.args[0] if e.args else "?"
            print(f"   ❌ {schema:20s} — Error {code}: {e.args[1] if len(e.args) > 1 else e}")
        except Exception as e:
            print(f"   ❌ {schema:20s} — {e}")

def test_sqlalchemy():
    """5. Probar con SQLAlchemy (como lo usa la app)"""
    print()
    print("=" * 60)
    print("5. TEST SQLAlchemy — Conexión como la usa Flask")
    print("=" * 60)
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("   ⚠️  SQLAlchemy no instalado")
        return

    uri = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/AD17_Almacen?charset=utf8mb4"
    try:
        engine = create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 15})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS ok"))
            row = result.fetchone()
            print(f"   ✅ SQLAlchemy OK — SELECT 1 = {row[0]}")

            # Contar tablas de la app
            result = conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            print(f"   📌 Tablas en AD17_Almacen: {len(tables)}")
            for t in tables:
                print(f"       • {t[0]}")
        engine.dispose()
    except Exception as e:
        print(f"   ❌ SQLAlchemy ERROR: {e}")


if __name__ == "__main__":
    print()
    print("🔍 PRUEBA DE CONEXIÓN A BASE DE DATOS")
    print(f"   Host: {HOST}:{PORT}")
    print(f"   User: {USER}")
    print()

    ip = test_dns()
    if not ip:
        print("\n⛔ No se puede resolver el host. Verifica tu DNS/Internet.")
        sys.exit(1)

    tcp_ok = test_tcp(ip)
    if not tcp_ok:
        print("\n⛔ No hay conectividad TCP al servidor MySQL.")
        print("   Posibles causas:")
        print("   • El servidor está apagado")
        print("   • El firewall bloquea el puerto 3307")
        print("   • El DDNS no apunta a la IP correcta")
        sys.exit(1)

    mysql_ok = test_pymysql()
    if not mysql_ok:
        print("\n⛔ La autenticación MySQL falló.")
        print("   Verifica usuario y contraseña.")
        sys.exit(1)

    test_schemas()
    test_sqlalchemy()

    print()
    print("=" * 60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("=" * 60)
