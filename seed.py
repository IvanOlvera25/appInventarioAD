# seed_dummy.py (actualizado)
# Limpieza completa de datos dummy y rehidratación desde el maestro remoto.
# Uso:
#   python3 seed_dummy.py load          -> Inserta datos dummy (igual que antes)
#   python3 seed_dummy.py purge         -> Elimina datos dummy (igual que antes)
#   python3 seed_dummy.py reload        -> purge + load (igual que antes)
#   python3 seed_dummy.py purge_remote  -> Deja el sistema "solo real":
#                                          1) purge dummy
#                                          2) purga ejemplos init_db/consumibles
#                                          3) elimina materiales fuera del maestro remoto (sin deps/stock)
#                                          4) sincroniza catálogo desde remoto

import os
import sys
from datetime import datetime, timedelta, date
import random

# Importa tu app y modelos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db, remote_db, sync_materials_from_remote
from models import (
    User, Project, Material, FabricRoll, Request, RequestItem,
    ProjectSummary, StockMovement, PurchaseRequest, VerificationCode
)

from werkzeug.security import generate_password_hash
from sqlalchemy import inspect, text

# ===== Config del seed =====
DUMMY_PREFIX = "DUMMY-"
DUMMY_NOTE = "DUMMY SEED"
NOW = datetime.utcnow()
DEPARTAMENTOS = [
    "Producción", "Mantenimiento", "Calidad",
    "Ingeniería", "Logística", "Administración"
]
AREAS = [
    "Línea A", "Línea B", "Soldadura", "Oficina Proyectos",
    "Almacén", "Confección"
]
USERS_DEF = [
    # username, email, role, is_leader, department, password
    (f"{DUMMY_PREFIX}admin",        "dummy.admin@empresa.com",        "admin",        True,  "Administración", "admin123"),
    (f"{DUMMY_PREFIX}almacenista",  "dummy.almacen@empresa.com",      "almacenista",  False, "Logística",       "almacen123"),
    (f"{DUMMY_PREFIX}requisitador", "dummy.requis@empresa.com",       "requisitador", False, "Producción",      "requis123"),
    (f"{DUMMY_PREFIX}lider",        "dummy.lider@empresa.com",        "requisitador", True,  "Producción",      "lider123"),
]

MATERIALS_DEF = [
    # (code, name, unit, category, is_fabric_roll, is_consumible, min, max, unit_cost)
    (f"{DUMMY_PREFIX}MAT-001", "Acero Inox 304",     "kg",      "Metales",      False, False, 100, 1000, 15.5),
    (f"{DUMMY_PREFIX}MAT-002", "Tela Algodón 100%",  "metros",  "Textiles",     True,  False, 500, 2000,  8.75),
    (f"{DUMMY_PREFIX}MAT-003", "Tornillo M6x20",     "piezas",  "Ferretería",   False, False, 1000, 5000, 0.25),
    (f"{DUMMY_PREFIX}MAT-004", "Pintura Acrílica",   "litros",  "Químicos",     False, False, 50,  200,  25.0),
    (f"{DUMMY_PREFIX}MAT-005", "Lámina Aluminio 2mm","m2",      "Metales",      False, False, 20,  100,  45.0),
    (f"{DUMMY_PREFIX}CON-001", "Pilas AA Alcalinas", "piezas",  "Electrónicos", False, True,  10,  100,  1.50),
    (f"{DUMMY_PREFIX}CON-002", "Papel Hig. Ind.",    "rollos",  "Limpieza",     False, True,  15,   50,  2.25),
    (f"{DUMMY_PREFIX}CON-003", "Cinta Aislante",     "rollos",  "Mantenimiento",False, True,  10,   30,  3.50),
]

PROJECTS_DEF = [
    (f"{DUMMY_PREFIX}FP-2025-001", "Proyecto Demo Alpha"),
    (f"{DUMMY_PREFIX}FP-2025-002", "Proyecto Demo Beta"),
    (f"{DUMMY_PREFIX}FP-2025-003", "Proyecto Demo Gamma"),
]

REQUEST_TIPOS = ["venta", "renta"]

# Conjunto de materiales demo creados por init_db()/init_consumibles_data()
_INIT_DB_DEMO_MATS = {
    # init_db() materiales
    "MAT-001","MAT-002","MAT-003","MAT-004","MAT-005",
    # init_consumibles_data()
    "CON-ELE-001","CON-LIM-001","CON-OFI-001","CON-MAN-001","CON-SEG-001",
}

# ===== Utilidades =====

def _exists_user(username):
    return User.query.filter_by(username=username).first()

def _exists_material(code):
    return Material.query.filter_by(code=code).first()

def _exists_project(fp):
    return Project.query.filter_by(fp_code=fp).first()

def _idm(prefix: str, n: int) -> str:
    # IDM tipo ENT-250908-0001
    return f"{prefix}-{NOW.strftime('%y%m%d')}-{n:04d}"

# ===== Utilidades remoto / limpieza segura =====

def _remote_material_codes_set():
    """Devuelve un set con todos los códigos válidos desde el maestro remoto."""
    try:
        rows = remote_db.get_materiales_habilitados() or []
        return { str(r['id']).strip() for r in rows if r.get('id') is not None }
    except Exception as e:
        print(f"⚠️  No se pudo leer el maestro remoto de materiales: {e}")
        return set()

def _material_has_dependencies(mat_id: int) -> bool:
    """True si el material tiene movimientos, items o stock > 0."""
    deps = 0
    deps += db.session.query(StockMovement.id).filter_by(material_id=mat_id).limit(1).count()
    deps += db.session.query(RequestItem.id).filter_by(material_id=mat_id).limit(1).count()
    mat = db.session.get(Material, mat_id)
    has_stock = (mat.current_stock or 0) > 0 if mat else False
    return (deps > 0) or has_stock

def _safe_delete_material(mat: Material) -> bool:
    """
    Elimina un material SIN dependencias. Si tiene dependencias/stock, no lo toca.
    Devuelve True si se borró, False si se saltó.
    """
    if _material_has_dependencies(mat.id):
        return False
    # borrar rollos asociados si existen
    db.session.query(FabricRoll).filter_by(material_id=mat.id).delete(synchronize_session=False)
    db.session.delete(mat)
    return True

# ===== Carga de datos dummy (igual que antes) =====

def seed_users():
    print("👤 Creando usuarios dummy…")
    created = 0
    for username, email, role, is_leader, dept, pwd in USERS_DEF:
        if _exists_user(username):
            continue
        u = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(pwd),
            role=role,
            department=dept,
            is_leader=is_leader,
        )
        db.session.add(u)
        created += 1
    db.session.commit()
    print(f"   ✓ Usuarios creados: {created}")
    # Opcional: marcar verificados si existen columnas
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('user')]
    if "is_verified" in cols and "verified_at" in cols:
        User.query.filter(User.username.like(f"{DUMMY_PREFIX}%")).update(
            {"is_verified": True, "verified_at": datetime.utcnow()},
            synchronize_session=False
        )
        db.session.commit()

def seed_projects():
    print("📁 Creando proyectos dummy…")
    created = 0
    for fp, name in PROJECTS_DEF:
        if _exists_project(fp):
            continue
        p = Project(
            fp_code=fp,
            name=name,
            delivery_date=(date.today() + timedelta(days=90)),
            production_start=(date.today() - timedelta(days=7)),
            assembly_date=(date.today() + timedelta(days=60)),
            status="activo"
        )
        db.session.add(p)
        created += 1
    db.session.commit()
    print(f"   ✓ Proyectos creados: {created}")

def seed_materials_and_rolls():
    print("📦 Creando materiales y rollos dummy…")
    created_mat = 0
    created_rolls = 0
    for code, name, unit, cat, is_roll, is_cons, min_s, max_s, cost in MATERIALS_DEF:
        if _exists_material(code):
            continue
        m = Material(
            code=code,
            name=name,
            unit=unit,
            category=cat,
            description=f"{DUMMY_NOTE} - {name}",
            min_stock=min_s,
            max_stock=max_s,
            unit_cost=cost,
            is_fabric_roll=is_roll,
            is_consumible=is_cons,
            current_stock=0,  # stock se sube con entradas
        )
        db.session.add(m)
        db.session.flush()
        created_mat += 1

        if is_roll:
            # Crea 2-3 rollos por material tipo tela
            for i in range(1, 3+1):
                fr = FabricRoll(
                    material_id=m.id,
                    roll_number=f"{DUMMY_PREFIX}ROL-{i:03d}",
                    total_length=100.0,
                    remaining_length=random.choice([85.0, 50.0, 20.0]),
                    width=150.0,
                    status=random.choice(["disponible", "critico", "agotado"])
                )
                db.session.add(fr)
                created_rolls += 1

    db.session.commit()
    print(f"   ✓ Materiales creados: {created_mat}")
    print(f"   ✓ Rollos creados: {created_rolls}")

def seed_stock_entries():
    print("📥 Generando ENTRADAS de stock para materiales dummy…")
    admin = User.query.filter_by(role="admin").first() or User.query.first()
    mats = Material.query.filter(Material.code.like(f"{DUMMY_PREFIX}%")).all()
    count = 0
    for idx, m in enumerate(mats, start=1):
        qty = round(m.max_stock * 0.5, 2) if m.max_stock else 100
        mv = StockMovement(
            idm=_idm("ENT", idx),
            material_id=m.id,
            movement_type="entrada",
            quantity=qty,
            rollos=1 if m.is_fabric_roll else 0,
            fp_code=random.choice([fp for fp, _ in PROJECTS_DEF]) if PROJECTS_DEF else None,
            fecha=date.today(),
            hora=datetime.utcnow().time(),
            personal=admin.username if admin else "system",
            area="Almacén",
            unit_cost=m.unit_cost,
            user_id=admin.id if admin else None,
            notes=DUMMY_NOTE,
            reference_type="inventario_inicial"
        )
        m.current_stock = (m.current_stock or 0) + qty
        m.last_movement = datetime.utcnow()
        db.session.add(mv)
        count += 1
    db.session.commit()
    print(f"   ✓ Entradas creadas: {count}")

def seed_requests_and_movements():
    print("🧾 Creando requisiciones dummy…")
    users = {u.role: u for u in User.query.filter(User.username.like(f"{DUMMY_PREFIX}%")).all()}
    admin = users.get("admin") or User.query.filter_by(role="admin").first()
    almacenista = users.get("almacenista")
    requisitador = users.get("requisitador") or User.query.filter_by(role="usuario").first()
    lider = User.query.filter(User.username.like(f"{DUMMY_PREFIX}lider%")).first()

    projects = Project.query.filter(Project.fp_code.like(f"{DUMMY_PREFIX}%")).all()
    mats = Material.query.filter(Material.code.like(f"{DUMMY_PREFIX}%"), Material.is_consumible == False).all()
    consumibles = Material.query.filter(Material.code.like(f"{DUMMY_PREFIX}%"), Material.is_consumible == True).all()

    if not projects or not mats:
        print("   ⚠️  No hay proyectos o materiales dummy. Omite requisiciones.")
        return

    req_defs = [
        # (status, is_incident, department, area, request_type)
        ("pendiente",   False, "Producción",    "Línea A",           "venta"),
        ("aprobada",    False, "Mantenimiento", "Taller de Sold.",   "renta"),
        ("en_proceso",  True,  "Producción",    "Línea B",           "venta"),
        ("completada",  False, "Ingeniería",    "Oficina Proyectos", "venta"),
        ("cancelada",   True,  "Calidad",       "Inspección",        "renta"),
    ]
    created_reqs = 0
    created_items = 0
    created_movs = 0

    for i, (status, is_inc, dept, area, rtype) in enumerate(req_defs, start=1):
        project = random.choice(projects)
        user = requisitador or admin
        req_num = f"{DUMMY_PREFIX}REQ-{NOW.strftime('%Y%m%d')}-{i:03d}"

        req = Request(
            request_number=req_num,
            project_id=project.id,
            user_id=user.id if user else None,
            department=dept,
            area=area,
            request_type=rtype,
            is_incident=is_inc,
            incident_id=(f"{DUMMY_PREFIX}INC-{i:03d}" if is_inc else None),
            assembly_start_date=date.today() + timedelta(days=7),
            assembly_end_date=date.today() + timedelta(days=15),
            status=status,
            notes=DUMMY_NOTE,
            approved_at=(datetime.utcnow() - timedelta(days=1)) if status in ("aprobada", "en_proceso", "completada") else None,
            approved_by=(lider.id if (lider and status in ("aprobada", "en_proceso", "completada")) else None)
        )
        db.session.add(req)
        db.session.flush()
        created_reqs += 1

        # 2–3 materiales por requisición
        for j in range(1, random.choice([2, 3]) + 1):
            mat = random.choice(mats)
            qty = round(random.uniform(5, 50), 2)
            will_return = random.choice([True, False])
            item_type = random.choice(["nuevo", "reutilizado", "reciclado"])

            it = RequestItem(
                request_id=req.id,
                material_id=mat.id,
                quantity_requested=qty,
                quantity_delivered=0,
                item_type=item_type,
                will_return=will_return,
                return_expected_date=(date.today() + timedelta(days=30)) if will_return else None,
                notes=DUMMY_NOTE
            )
            db.session.add(it)
            created_items += 1

            # Generar una salida parcial (entrega) para simular flujo
            deliver = round(qty * random.uniform(0.3, 0.9), 2)
            it.quantity_delivered = deliver

            # Mov. de salida
            mv_out = StockMovement(
                idm=_idm("SAL", i*10 + j),
                material_id=mat.id,
                movement_type="salida",
                quantity=deliver,
                rollos=0,
                fp_code=project.fp_code,
                fecha=date.today(),
                hora=datetime.utcnow().time(),
                personal=almacenista.username if almacenista else (admin.username if admin else "system"),
                area=area,
                unit_cost=mat.unit_cost,
                user_id=(almacenista.id if almacenista else (admin.id if admin else None)),
                notes=f"{DUMMY_NOTE} - {req_num}",
                reference_type="requisicion",
            )
            db.session.add(mv_out)
            mat.current_stock = max(0, (mat.current_stock or 0) - deliver)
            mat.last_movement = datetime.utcnow()
            created_movs += 1

            # En algunos casos, crear retorno
            if will_return and random.choice([True, False]):
                ret_qty = round(deliver * random.uniform(0.2, 0.6), 2)
                mv_ret = StockMovement(
                    idm=f"RET-{mv_out.idm}",
                    material_id=mat.id,
                    movement_type="retorno",
                    quantity=ret_qty,
                    rollos=0,
                    fp_code=project.fp_code,
                    fecha=date.today(),
                    hora=datetime.utcnow().time(),
                    personal=mv_out.personal,
                    area=mv_out.area,
                    unit_cost=mat.unit_cost,
                    user_id=mv_out.user_id,
                    notes=f"{DUMMY_NOTE} - Retorno {req_num}",
                    reference_type="devolucion",
                    reference_id=None
                )
                db.session.add(mv_ret)
                mat.current_stock = (mat.current_stock or 0) + ret_qty
                mat.last_movement = datetime.utcnow()
                created_movs += 1

        db.session.commit()

    print(f"   ✓ Requisiciones creadas: {created_reqs}")
    print(f"   ✓ Items creados: {created_items}")
    print(f"   ✓ Movimientos creados: {created_movs}")

    # Consumibles: crear consumos y órdenes urgentes
    print("🧯 Movimientos para consumibles y órdenes de compra…")
    cons_user = almacenista or admin
    for k, con in enumerate(consumibles, start=1):
        # Consumo
        qty_cons = min(5, max(1, int((con.current_stock or 20) * 0.2)))
        mv_cons = StockMovement(
            idm=_idm("SAL", 900 + k),
            material_id=con.id,
            movement_type="salida",
            quantity=qty_cons,
            rollos=0,
            fp_code=random.choice([fp for fp, _ in PROJECTS_DEF]) if PROJECTS_DEF else None,
            fecha=date.today(),
            hora=datetime.utcnow().time(),
            personal=cons_user.username if cons_user else "system",
            area="Oficina",
            unit_cost=con.unit_cost,
            user_id=cons_user.id if cons_user else None,
            notes=DUMMY_NOTE,
            reference_type="consumo"
        )
        con.current_stock = max(0, (con.current_stock or 0) - qty_cons)
        con.last_movement = datetime.utcnow()
        db.session.add(mv_cons)

        # Si queda crítico, genera PurchaseRequest
        if con.current_stock <= con.min_stock:
            qty_need = max(0, (con.max_stock or 50) - (con.current_stock or 0))
            if qty_need > 0:
                pr = PurchaseRequest(
                    request_number=f"{DUMMY_PREFIX}PO-{NOW.strftime('%Y%m%d')}-{k:03d}",
                    material_id=con.id,
                    quantity=qty_need,
                    requested_by=cons_user.id if cons_user else None,
                    status=random.choice(["pendiente", "urgente"]),
                    purchase_cost=round(qty_need * (con.unit_cost or 0), 2),
                    supplier=None,
                    notes=DUMMY_NOTE
                )
                db.session.add(pr)
    db.session.commit()
    print("   ✓ Movimientos de consumibles y órdenes creados")

def seed_project_summaries():
    print("📊 Generando ProjectSummary dummy…")
    projects = Project.query.filter(Project.fp_code.like(f"{DUMMY_PREFIX}%")).all()
    created = 0
    for p in projects:
        # Calcula totales
        reqs = Request.query.filter_by(project_id=p.id).all()
        total_requests = len(reqs)
        total_materials = sum(len(r.items) for r in reqs)
        total_cost = 0.0
        for r in reqs:
            for it in r.items:
                mat_cost = 0.0
                if it.material and it.material.unit_cost:
                    mat_cost = it.quantity_requested * it.material.unit_cost
                total_cost += mat_cost

        summary = ProjectSummary.query.filter_by(project_id=p.id).first()
        if not summary:
            summary = ProjectSummary(project_id=p.id)
            db.session.add(summary)
        summary.total_requests = total_requests
        summary.total_materials = total_materials
        summary.total_cost = round(total_cost, 2)
        summary.last_updated = datetime.utcnow()
        created += 1
    db.session.commit()
    print(f"   ✓ Summaries actualizados: {created}")

def seed_verification_codes_if_table():
    """Crea códigos de verificación dummy por rol, sólo si existe la tabla."""
    insp = inspect(db.engine)
    if "verification_code" not in insp.get_table_names():
        return

    print("🔐 Insertando códigos de verificación dummy…")
    # Evita duplicados por código
    for code, role in [
        (f"{DUMMY_PREFIX}VC-REQ-1234", "requisitador"),
        (f"{DUMMY_PREFIX}VC-ALM-1234", "almacenista"),
        (f"{DUMMY_PREFIX}VC-ADM-1234", "admin"),
    ]:
        exists = db.session.execute(
            text("SELECT 1 FROM verification_code WHERE code = :c"),
            {"c": code}
        ).first()
        if exists:
            continue
        db.session.execute(
            text("""
                INSERT INTO verification_code (code, role, expires_at, used_by, is_active, created_at)
                VALUES (:code, :role, :exp, NULL, 1, :created)
            """),
            {
                "code": code,
                "role": role,
                "exp": datetime.utcnow() + timedelta(days=30),
                "created": datetime.utcnow()
            }
        )
    db.session.commit()
    print("   ✓ Códigos insertados")

def load_all():
    seed_users()
    seed_projects()
    seed_materials_and_rolls()
    seed_stock_entries()
    seed_requests_and_movements()
    seed_project_summaries()
    seed_verification_codes_if_table()
    print("✅ Seed dummy COMPLETO")

# ===== Borrado de datos dummy (cubre Dashboard/Reportes/Panel Líder) =====

def purge_all():
    """
    Elimina datos dummy en orden seguro por dependencias.
    Esto limpia lo que usan:
      - Dashboard (StockMovement, Materiales, Requisiciones…)
      - Reportes/Análisis (mismos datos, más ProjectSummary)
      - Panel Líder (Requisiciones/Usuarios/Proyectos)
    """
    print("🧨 Eliminando datos dummy… (orden seguro por dependencias)")

    # 1) Movimientos de stock
    mv_del = StockMovement.query.filter(
        (StockMovement.notes.contains(DUMMY_NOTE)) |
        (StockMovement.idm.like(f"{DUMMY_PREFIX}%")) |
        (StockMovement.fp_code.like(f"{DUMMY_PREFIX}%"))
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Movimientos borrados: {mv_del}")

    # 2) Items de requisición
    it_del = RequestItem.query.filter(
        (RequestItem.notes.contains(DUMMY_NOTE)) |
        (RequestItem.material_id.in_(
            db.session.query(Material.id).filter(Material.code.like(f"{DUMMY_PREFIX}%"))
        )) |
        (RequestItem.request_id.in_(
            db.session.query(Request.id).filter(Request.request_number.like(f"{DUMMY_PREFIX}%"))
        ))
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Items de requisición borrados: {it_del}")

    # 3) Ordenes de compra dummy
    pr_del = PurchaseRequest.query.filter(
        (PurchaseRequest.request_number.like(f"{DUMMY_PREFIX}%")) |
        (PurchaseRequest.notes.contains(DUMMY_NOTE)) |
        (PurchaseRequest.material_id.in_(
            db.session.query(Material.id).filter(Material.code.like(f"{DUMMY_PREFIX}%"))
        ))
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ PurchaseRequests borrados: {pr_del}")

    # 4) Requisiciones dummy
    req_del = Request.query.filter(
        (Request.request_number.like(f"{DUMMY_PREFIX}%")) |
        (Request.notes.contains(DUMMY_NOTE)) |
        (Request.project_id.in_(
            db.session.query(Project.id).filter(Project.fp_code.like(f"{DUMMY_PREFIX}%"))
        )) |
        (Request.user_id.in_(
            db.session.query(User.id).filter(User.username.like(f"{DUMMY_PREFIX}%"))
        ))
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Requisiciones borradas: {req_del}")

    # 5) Rollos de tela de materiales dummy
    fr_del = FabricRoll.query.filter(
        FabricRoll.material_id.in_(
            db.session.query(Material.id).filter(Material.code.like(f"{DUMMY_PREFIX}%"))
        )
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ FabricRolls borrados: {fr_del}")

    # 6) ProjectSummary de proyectos dummy
    ps_del = ProjectSummary.query.filter(
        ProjectSummary.project_id.in_(
            db.session.query(Project.id).filter(Project.fp_code.like(f"{DUMMY_PREFIX}%"))
        )
    ).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ ProjectSummaries borrados: {ps_del}")

    # 7) Materiales dummy
    mat_del = Material.query.filter(Material.code.like(f"{DUMMY_PREFIX}%")).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Materiales borrados: {mat_del}")

    # 8) Proyectos dummy
    proj_del = Project.query.filter(Project.fp_code.like(f"{DUMMY_PREFIX}%")).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Proyectos borrados: {proj_del}")

    # 9) Códigos de verificación dummy (si existe tabla)
    insp = inspect(db.engine)
    if "verification_code" in insp.get_table_names():
        vc_del = db.session.execute(
            text("DELETE FROM verification_code WHERE code LIKE :pfx"),
            {"pfx": f"{DUMMY_PREFIX}%"}
        ).rowcount
        db.session.commit()
        print(f"   ✓ VerificationCodes borrados: {vc_del}")

    # 10) Usuarios dummy
    usr_del = User.query.filter(User.username.like(f"{DUMMY_PREFIX}%")).delete(synchronize_session=False)
    db.session.commit()
    print(f"   ✓ Usuarios borrados: {usr_del}")

    print("✅ Purge dummy COMPLETO")

# ===== Purga de ejemplos locales de init_db() / consumibles =====

def purge_initdb_examples():
    print("🧽 Eliminando materiales de ejemplo creados por init_db()/init_consumibles_data()…")
    removed, skipped = 0, []
    mats = Material.query.filter(Material.code.in_(_INIT_DB_DEMO_MATS)).all()
    for m in mats:
        if _safe_delete_material(m):
            removed += 1
        else:
            skipped.append(m.code)
    db.session.commit()
    print(f"   ✓ Eliminados: {removed}")
    if skipped:
        print("   ⚠️ Saltados (dependencias/stock):", ", ".join(skipped))

# ===== Purga de materiales no existentes en el maestro remoto =====

def purge_non_remote_materials():
    """
    Elimina todo material local cuyo código NO exista en el maestro remoto,
    siempre que no tenga dependencias ni stock.
    """
    print("🧹 Eliminando materiales locales que NO existen en el maestro remoto…")
    remote_codes = _remote_material_codes_set()
    if not remote_codes:
        print("   ⚠️ No se pudo obtener lista remota. Omite esta etapa.")
        return

    locals_not_in_remote = Material.query.filter(~Material.code.in_(remote_codes)).all()

    removed, skipped = 0, []
    for m in locals_not_in_remote:
        if _safe_delete_material(m):
            removed += 1
        else:
            skipped.append(m.code)
    db.session.commit()

    print(f"   ✓ Eliminados (sin dependencias): {removed}")
    if skipped:
        print("   ⚠️ Saltados (dependencias/stock):", ", ".join(skipped))
        print("      Si quieres forzar limpieza total, elimina primero movimientos/items o ajusta stock a 0.")

# ===== Sincronización desde el maestro remoto =====

def sync_from_remote_and_report():
    print("🔄 Sincronizando catálogo local desde remoto…")
    res = sync_materials_from_remote()
    if res.get('success'):
        print(f"   ✓ Sincronización: {res.get('synced',0)} nuevos, {res.get('updated',0)} actualizados (total remoto: {res.get('total','?')})")
    else:
        print(f"   ❌ Error de sync: {res.get('error')}")

# ===== Flujo maestro: dejar "solo real" =====

def purge_remote_only():
    """
    Deja el sistema 'solo real':
      1) Borra DUMMY (todas las secciones que alimentan dashboard/reportes/panel líder)
      2) Borra ejemplos de init_db()/consumibles de ejemplo
      3) Elimina materiales que no existen en el maestro remoto (si no tienen dependencias/stock)
      4) Sincroniza desde remoto
    """
    print("🧨 Paso 1/4: Purga DUMMY…")
    purge_all()

    print("\n🧽 Paso 2/4: Purga ejemplos locales (init_db)…")
    purge_initdb_examples()

    print("\n🧹 Paso 3/4: Quita materiales fuera del maestro remoto…")
    purge_non_remote_materials()

    print("\n🔄 Paso 4/4: Rehidratar catálogo desde remoto…")
    sync_from_remote_and_report()

    print("\n✅ Listo. El sistema quedó sin dummy en Dashboard/Reportes/Panel Líder y alineado al maestro remoto (salvo materiales con dependencias/stock, que se reportaron).")

# ===== CLI =====

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 seed_dummy.py [load|purge|reload|purge_remote]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd not in {"load", "purge", "reload", "purge_remote"}:
        print("Comando no reconocido. Usa: load | purge | reload | purge_remote")
        sys.exit(1)

    if cmd == "load":
        load_all()
    elif cmd == "purge":
        purge_all()
    elif cmd == "reload":
        purge_all()
        load_all()
    elif cmd == "purge_remote":
        purge_remote_only()

if __name__ == "__main__":
    with app.app_context():
        main()