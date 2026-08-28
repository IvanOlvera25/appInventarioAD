# models.py
from datetime import datetime, timedelta

from utils import now_mx

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Crea una instancia global de SQLAlchemy para inicializarla en app.py
db = SQLAlchemy()

# ===== Modelos de Base de Datos =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='requisitador')
    department = db.Column(db.String(100), nullable=True)
    is_leader = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now_mx)
    # Asociación con empleado de AD17_RH
    employee_id   = db.Column(db.Integer, nullable=True)   # id en AD17_RH.empleados_activos
    employee_name = db.Column(db.String(200), nullable=True)  # caché del nombre del empleado

    @property
    def full_name(self):
        """Returns the employee name if linked, otherwise the username"""
        return self.employee_name or self.username

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)              # opcional (p.ej. PROD, MANT)
    name = db.Column(db.String(120), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_mx)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fp_code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    production_start = db.Column(db.Date, nullable=False)
    assembly_date = db.Column(db.Date, nullable=False)
    analysis_date = db.Column(db.Date) # Fecha analisis
    client = db.Column(db.String(150)) # Cliente del proyecto
    status = db.Column(db.String(50), default='activo')
    created_at = db.Column(db.DateTime, default=now_mx)


# ===== Modelos sincronizados con BD Remota =====
class Category(db.Model):
    """Categorías de materiales - sincronizadas desde AD17_Materiales.Categoria"""
    id = db.Column(db.Integer, primary_key=True)
    remote_id = db.Column(db.Integer, unique=True)  # regID de la BD remota
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_fabric = db.Column(db.Boolean, default=False)  # True si es categoría de telas
    is_active = db.Column(db.Boolean, default=True)
    synced_at = db.Column(db.DateTime, default=now_mx)


class Unit(db.Model):
    """Unidades de medida - sincronizadas desde AD17_General.Unidades"""
    id = db.Column(db.Integer, primary_key=True)
    remote_id = db.Column(db.Integer, unique=True)  # regID de la BD remota
    name = db.Column(db.String(50), nullable=False)
    abbreviation = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    synced_at = db.Column(db.DateTime, default=now_mx)


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    # Referencias a tablas sincronizadas (opcionales para compatibilidad)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)
    current_stock = db.Column(db.Float, default=0)
    min_stock = db.Column(db.Float, default=0)
    max_stock = db.Column(db.Float, default=0)
    unit_cost = db.Column(db.Float, default=0)
    # Opciones de telas
    is_fabric_roll = db.Column(db.Boolean, default=False)
    fabric_width = db.Column(db.Float)  # Ancho de tela en cm
    # Opciones de reciclaje
    can_recycle = db.Column(db.Boolean, default=False)
    can_reuse = db.Column(db.Boolean, default=True)
    is_recycled = db.Column(db.Boolean, default=False)  # Es material reciclado
    is_pre_recycled = db.Column(db.Boolean, default=False)  # Es material pre-reciclado
    recycled_from_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=True)  # Material origen
    # Timestamps
    created_at = db.Column(db.DateTime, default=now_mx)
    last_movement = db.Column(db.DateTime)
    is_consumible = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)   # False = deshabilitado (baja lógica)
    disabled_at = db.Column(db.DateTime, nullable=True)  # Fecha de deshabilitación

    # Relaciones
    category_ref = db.relationship('Category', backref='materials', foreign_keys=[category_id])
    unit_ref = db.relationship('Unit', backref='materials', foreign_keys=[unit_id])
    recycled_from = db.relationship('Material', remote_side=[id], backref='recycled_materials')


class FabricRoll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    total_length = db.Column(db.Float, nullable=False)
    remaining_length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float)
    status = db.Column(db.String(50), default='disponible')
    location = db.Column(db.String(100), default='Almacén de Telas')
    provisioned_by_client = db.Column(db.String(200))
    # Historial del rollo
    created_at = db.Column(db.DateTime, default=now_mx)  # Cuándo se registró
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Quién lo registró
    finished_at = db.Column(db.DateTime, nullable=True)  # Cuándo se terminó (agotó)
    material = db.relationship('Material', backref='fabric_rolls')
    creator = db.relationship('User', foreign_keys=[created_by])


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(100), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    # Campos mantenidos para compatibilidad con BD existente (tienen NOT NULL)
    area = db.Column(db.String(100))
    request_type = db.Column(db.String(50))  # venta/renta - ya no se usa en UI
    is_incident = db.Column(db.Boolean, default=False)  # Si es por incidencia
    incident_id = db.Column(db.String(100))  # ID de incidencia si aplica
    # Nuevos campos de fecha
    acquisition_deadline = db.Column(db.Date)  # Fecha límite de adquisición
    production_start_date = db.Column(db.Date)  # Fecha inicio producción
    assembly_start_date = db.Column(db.Date)  # Fecha inicio montaje
    assembly_end_date = db.Column(db.Date)  # Fecha fin montaje
    # Estados: pendiente, abastecido, pendiente_compra, en_entrega, completada, cancelada, pendiente_retorno
    status = db.Column(db.String(50), default='pendiente')
    has_returns = db.Column(db.Boolean, default=False)  # Si tiene devoluciones
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_mx)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Campos para solicitud de cancelación
    cancellation_requested = db.Column(db.Boolean, default=False)
    cancellation_requested_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    cancellation_requested_at = db.Column(db.DateTime)

    project = db.relationship('Project', backref='requests')
    user = db.relationship('User', backref='requests', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    cancellation_requester = db.relationship('User', foreign_keys=[cancellation_requested_by])


class RequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=True)  # Nullable para nuevos materiales

    # Campos para materiales nuevos
    new_material_code = db.Column(db.String(100))
    new_material_name = db.Column(db.String(200))
    new_material_unit = db.Column(db.String(50))
    new_material_category = db.Column(db.String(100))
    is_new_material = db.Column(db.Boolean, default=False)

    quantity_requested = db.Column(db.Float, nullable=False)
    quantity_delivered = db.Column(db.Float, default=0)
    item_type = db.Column(db.String(50), default='nuevo')  # nuevo, reutilizado, reciclado
    will_return = db.Column(db.Boolean, default=False)  # Si va a regresar
    return_expected_date = db.Column(db.Date)  # Fecha esperada de retorno
    unit_cost = db.Column(db.Float)
    will_recycle = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    # Nuevos campos para flujo de estados
    item_status = db.Column(db.String(50), default='pendiente')  # pendiente, abastecido, pendiente_compra, pendiente_retorno, cancelado
    quantity_to_purchase = db.Column(db.Float, default=0)  # Cantidad a comprar
    quantity_supplied = db.Column(db.Float, default=0)  # Cantidad abastecida del stock
    item_notes = db.Column(db.Text)  # Notas específicas del item
    actual_return_date = db.Column(db.Date)  # Fecha real de retorno

    request = db.relationship('Request', backref='items')
    material = db.relationship('Material', backref='request_items')


class ProjectSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    total_requests = db.Column(db.Integer, default=0)
    total_materials = db.Column(db.Integer, default=0)
    total_cost = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=now_mx)

    project = db.relationship('Project', backref='summary')


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    idm = db.Column(db.String(50))  # Nueva columna IDM
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    movement_type = db.Column(db.String(50), nullable=False)  # entrada, salida, retorno, ajuste
    quantity = db.Column(db.Float, nullable=False)  # en ajustes = diferencia aplicada (+/-)
    previous_stock = db.Column(db.Float)  # stock antes del movimiento (se llena en ajustes manuales)
    rollos = db.Column(db.Integer, default=0)  # Rollos
    fp_code = db.Column(db.String(100))  # Código de proyecto
    fecha = db.Column(db.Date)  # Fecha específica
    hora = db.Column(db.Time)  # Hora específica
    personal = db.Column(db.String(100))  # Personal
    area = db.Column(db.String(100))  # Área
    unit_cost = db.Column(db.Float)
    reference_id = db.Column(db.Integer)  # ID de la requisición o compra
    reference_type = db.Column(db.String(50))  # requisicion, compra, ajuste
    # Rollo de tela de origen (solo salidas por corte de tela)
    fabric_roll_id = db.Column(db.Integer, db.ForeignKey('fabric_roll.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_mx)  # Fecha creación
    updated_at = db.Column(db.DateTime, default=now_mx, onupdate=now_mx)  # Fecha modificación
    returned = db.Column(db.Boolean, default=False)
    return_date = db.Column(db.DateTime)
    return_quantity = db.Column(db.Float, default=0)
    condition_on_return = db.Column(db.String(50))  # bueno, reutilizable, reciclable, desecho

    material = db.relationship('Material', backref='movements')
    user = db.relationship('User', backref='movements')
    fabric_roll = db.relationship('FabricRoll', foreign_keys=[fabric_roll_id], backref='movements')


class PurchaseRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(100), unique=True, nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pendiente')
    purchase_cost = db.Column(db.Float)
    supplier = db.Column(db.String(200))
    purchase_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_mx)

    material = db.relationship('Material', backref='purchase_requests')
    requester = db.relationship('User', backref='purchase_requests')

# --- NUEVO: Alertas del sistema persistentes ---
class SystemAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # requisicion_alta, material_abastecido, requisicion_abastecida, retorno_pendiente, cancelacion_solicitada
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # warning, info, success, danger
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # NULL = para todos
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now_mx)

    target_user = db.relationship('User', foreign_keys=[target_user_id])
    request = db.relationship('Request', foreign_keys=[request_id])


# --- NUEVO: Códigos de verificación por tipo de usuario ---
class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)     # p.ej. REQ-AB12CD
    role = db.Column(db.String(50), nullable=False)                  # requisitador/almacenista/admin
    expires_at = db.Column(db.DateTime)                              # opcional
    used_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_mx)

    user = db.relationship('User', foreign_keys=[used_by])


# --- Auditoría de cambios (append-only, nunca se modifica) ---
class AuditLog(db.Model):
    """Registro inmutable de cambios en la base de datos.
    Cada UPDATE genera una fila por campo modificado.
    CREATE y DELETE generan una fila sin field_name.
    """
    __tablename__ = 'audit_log'

    id          = db.Column(db.Integer, primary_key=True)
    table_name  = db.Column(db.String(100), nullable=False)   # 'request', 'material', etc.
    record_id   = db.Column(db.Integer, nullable=False)        # ID del registro afectado
    action      = db.Column(db.String(20), nullable=False)     # CREATE | UPDATE | DELETE
    field_name  = db.Column(db.String(100))                    # Campo modificado (solo UPDATE)
    old_value   = db.Column(db.Text)                           # Valor anterior (str)
    new_value   = db.Column(db.Text)                           # Valor nuevo (str)
    changed_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    changed_at  = db.Column(db.DateTime, default=now_mx, nullable=False)
    ip_address  = db.Column(db.String(45))                     # IPv4 / IPv6
    notes       = db.Column(db.Text)                           # Contexto adicional (número req, etc.)

    author = db.relationship('User', foreign_keys=[changed_by])


# --- Configuración global del sistema (toggles y ajustes de admin) ---
class SystemConfig(db.Model):
    """Almacena configuraciones globales de la app que los admins pueden cambiar.
    Cada fila es un par clave-valor. Claves conocidas:
      - stock_check_enabled: '1' = validar stock antes de salida, '0' = permitir negativos
    """
    __tablename__ = 'system_config'

    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(100), unique=True, nullable=False)
    value      = db.Column(db.String(255), nullable=False, default='0')
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=now_mx, onupdate=now_mx)

    author = db.relationship('User', foreign_keys=[updated_by])


# --- Ubicaciones / Áreas del almacén (administrables desde el panel) ---
class WarehouseLocation(db.Model):
    """Catálogo de ubicaciones (almacenes) y áreas destino configurables por el admin.

    location_type:
      'almacen' → aparece en el dropdown de Ubicación/Área al registrar una entrada.
      'area'    → aparece en el dropdown de Área destino en salidas libres y corte libre de tela.
    """
    __tablename__ = 'warehouse_location'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    location_type = db.Column(db.String(20), nullable=False, default='almacen')  # 'almacen' | 'area'
    is_active     = db.Column(db.Boolean, default=True)
    sort_order    = db.Column(db.Integer, default=0)   # para ordenar en el dropdown
    created_at    = db.Column(db.DateTime, default=now_mx)

    __table_args__ = (
        db.UniqueConstraint('name', 'location_type', name='uq_location_name_type'),
    )

# ===================================================================
# ===== INVENTARIO DE HERRAMIENTAS =====
# ===================================================================

class Tool(db.Model):
    """Herramienta del inventario (control individual por número de serie)."""
    __tablename__ = 'tool'

    id               = db.Column(db.Integer, primary_key=True)
    code             = db.Column(db.String(50), unique=True, nullable=False)   # HERR-0001
    name             = db.Column(db.String(200), nullable=False)
    serial_number    = db.Column(db.String(120))                               # número de serie
    brand            = db.Column(db.String(120))                               # marca
    model            = db.Column(db.String(120))                               # modelo
    tool_type        = db.Column(db.String(100))                               # tipo (eléctrica, manual, medición...)

    # 'estado' se maneja en dos ejes:
    #   status    → disponibilidad operativa (se actualiza sola con préstamos/reparaciones)
    #   condition → estado físico declarado por el almacenista
    status           = db.Column(db.String(30), default='disponible')  # disponible|prestada|en_reparacion|baja
    condition        = db.Column(db.String(30), default='bueno')       # nuevo|bueno|regular|malo

    cost             = db.Column(db.Float, default=0)
    acquisition_date = db.Column(db.Date)
    photo            = db.Column(db.String(255))                               # nombre de archivo en uploads/herramientas
    location         = db.Column(db.String(120))                               # dónde se resguarda
    notes            = db.Column(db.Text)

    is_active        = db.Column(db.Boolean, default=True)                     # baja lógica
    created_at       = db.Column(db.DateTime, default=now_mx)
    created_by       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    creator = db.relationship('User', foreign_keys=[created_by])

    @property
    def active_loan(self):
        """Préstamo abierto (sin fecha de devolución), si existe."""
        return next((l for l in self.loans if l.actual_return_date is None), None)

    @property
    def open_repair(self):
        """Reparación en proceso, si existe."""
        return next((r for r in self.repairs if r.status == 'en_proceso'), None)

    @property
    def total_repair_cost(self):
        return sum((r.cost or 0) for r in self.repairs)

    @property
    def status_label(self):
        return {
            'disponible':    'Disponible',
            'prestada':      'Prestada',
            'en_reparacion': 'En reparación',
            'baja':          'Dada de baja',
        }.get(self.status, self.status or '—')

    @property
    def condition_label(self):
        return {
            'nuevo':   'Nuevo',
            'bueno':   'Bueno',
            'regular': 'Regular',
            'malo':    'Malo',
        }.get(self.condition, self.condition or '—')


class ToolLoan(db.Model):
    """Historial de préstamos: a quién salió, cuándo salió y cuándo regresó."""
    __tablename__ = 'tool_loan'

    id                   = db.Column(db.Integer, primary_key=True)
    tool_id              = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)

    # A quién se le prestó (empleado de AD17_RH o nombre libre)
    employee_id          = db.Column(db.Integer, nullable=True)
    employee_name        = db.Column(db.String(200), nullable=False)
    area                 = db.Column(db.String(120))
    fp_code              = db.Column(db.String(100))          # opcional

    checkout_date        = db.Column(db.DateTime, default=now_mx, nullable=False)  # cuándo salió
    expected_return_date = db.Column(db.Date)                 # cuándo debería regresar
    actual_return_date   = db.Column(db.DateTime)             # cuándo regresó (NULL = sigue afuera)
    condition_on_return  = db.Column(db.String(30))           # bueno|regular|malo|dañada

    delivered_by         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # quién la entregó
    received_by          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # quién la recibió
    reservation_id       = db.Column(db.Integer, db.ForeignKey('tool_reservation.id'), nullable=True)

    notes                = db.Column(db.Text)
    return_notes         = db.Column(db.Text)
    created_at           = db.Column(db.DateTime, default=now_mx)

    tool      = db.relationship('Tool', backref=db.backref('loans', order_by='ToolLoan.checkout_date.desc()'))
    deliverer = db.relationship('User', foreign_keys=[delivered_by])
    receiver  = db.relationship('User', foreign_keys=[received_by])

    @property
    def is_open(self):
        return self.actual_return_date is None

    @property
    def is_overdue(self):
        if self.actual_return_date or not self.expected_return_date:
            return False
        return self.expected_return_date < now_mx().date()

    @property
    def days_out(self):
        end = self.actual_return_date or now_mx()
        return max((end - self.checkout_date).days, 0)


class ToolRepair(db.Model):
    """Historial de reparaciones con su costo."""
    __tablename__ = 'tool_repair'

    id          = db.Column(db.Integer, primary_key=True)
    tool_id     = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)

    description = db.Column(db.Text, nullable=False)          # falla / trabajo realizado
    provider    = db.Column(db.String(200))                   # taller o proveedor
    cost        = db.Column(db.Float, default=0)
    start_date  = db.Column(db.Date, nullable=False)
    end_date    = db.Column(db.Date)                          # NULL mientras siga en proceso
    status      = db.Column(db.String(30), default='en_proceso')  # en_proceso|completada|cancelada
    notes       = db.Column(db.Text)

    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=now_mx)

    tool    = db.relationship('Tool', backref=db.backref('repairs', order_by='ToolRepair.start_date.desc()'))
    creator = db.relationship('User', foreign_keys=[created_by])


class ToolReservation(db.Model):
    """Apartado de una herramienta: debe estar lista cierto día para cierta área,
    con la fecha comprometida de regreso para saber cuándo vuelve a estar libre.
    No requiere FP."""
    __tablename__ = 'tool_reservation'

    id            = db.Column(db.Integer, primary_key=True)
    tool_id       = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)

    area          = db.Column(db.String(120), nullable=False)   # área que la aparta
    responsible   = db.Column(db.String(200))                   # persona responsable (opcional)
    employee_id   = db.Column(db.Integer, nullable=True)

    start_date    = db.Column(db.Date, nullable=False)          # día en que debe estar lista
    end_date      = db.Column(db.Date, nullable=False)          # día comprometido de regreso
    purpose       = db.Column(db.Text)                          # para qué se necesita
    status        = db.Column(db.String(30), default='pendiente')  # pendiente|en_uso|completada|cancelada
    notes         = db.Column(db.Text)

    requested_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at    = db.Column(db.DateTime, default=now_mx)
    cancelled_at  = db.Column(db.DateTime)
    cancel_reason = db.Column(db.String(255))

    tool      = db.relationship('Tool', backref=db.backref('reservations', order_by='ToolReservation.start_date'))
    requester = db.relationship('User', foreign_keys=[requested_by])
    loans     = db.relationship('ToolLoan', backref='reservation', foreign_keys='ToolLoan.reservation_id')

    @property
    def is_blocking(self):
        """Ocupa la herramienta en su rango de fechas."""
        return self.status in ('pendiente', 'en_uso')

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def status_label(self):
        return {
            'pendiente':  'Apartada',
            'en_uso':     'En uso',
            'completada': 'Completada',
            'cancelada':  'Cancelada',
        }.get(self.status, self.status or '—')
