import os

class Config:
    # ===== Conexión base al servidor MySQL =====
    REMOTE_DB_HOST = os.environ.get("REMOTE_DB_HOST", "ad17solutions.dscloud.me")
    REMOTE_DB_PORT = int(os.environ.get("REMOTE_DB_PORT", "3307"))
    REMOTE_DB_USER = os.environ.get("REMOTE_DB_USER", "IvanUriel")
    REMOTE_DB_PASSWORD = os.environ.get("REMOTE_DB_PASSWORD", "iuOp20!!25")

    # ===== Esquemas de SOLO LECTURA (catálogos/externos) =====
    SCHEMA_MAT = os.environ.get("SCHEMA_MAT", "AD17_Materiales")
    SCHEMA_GEN = os.environ.get("SCHEMA_GEN", "AD17_General")
    SCHEMA_PRO = os.environ.get("SCHEMA_PRO", "AD17_Proyectos")
    SCHEMA_CLI = os.environ.get("SCHEMA_CLI", "AD17_Clientes")
    SCHEMA_RH  = os.environ.get("SCHEMA_RH",  "AD17_RH")

    # Alias de compatibilidad para mysql_conn() (tu app.py lo usa por defecto)
    # Si no te pasan REMOTE_DB_NAME por entorno, cae al esquema de materiales.
    REMOTE_DB_NAME = os.environ.get("REMOTE_DB_NAME", SCHEMA_MAT)

    # ===== Esquema PRINCIPAL donde ESCRIBE la app (tablas propias) =====
    MAIN_SCHEMA = os.environ.get("MAIN_SCHEMA", "AD17_Almacen")
    # Alias opcional por si en algún punto se usa SCHEMA_ALM en código
    SCHEMA_ALM = os.environ.get("SCHEMA_ALM", MAIN_SCHEMA)

    # ===== Flask / SQLAlchemy =====
    SECRET_KEY = os.environ.get("SECRET_KEY", "tu-clave-secreta-aqui")

    # Conexión principal: apunta al esquema donde se escriben las tablas propias
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
        f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{MAIN_SCHEMA}?charset=utf8mb4"
    )

    # Binds de solo lectura a otros esquemas del mismo servidor
    SQLALCHEMY_BINDS = {
        "mat": f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
               f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{SCHEMA_MAT}?charset=utf8mb4",
        "gen": f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
               f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{SCHEMA_GEN}?charset=utf8mb4",
        "pro": f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
               f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{SCHEMA_PRO}?charset=utf8mb4",
        "cli": f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
               f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{SCHEMA_CLI}?charset=utf8mb4",
        "rh":  f"mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}"
               f"@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{SCHEMA_RH}?charset=utf8mb4",
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ===== Archivos =====
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
