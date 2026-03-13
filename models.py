# models.py
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Crea una instancia global de SQLAlchemy para inicializarla en app.py
db = SQLAlchemy()

# ===== Modelos de Base de Datos =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='requisitador')
    department = db.Column(db.String(100), nullable=True)
    is_leader = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_name(self):
        """Returns the username as the full name display"""
        return self.username

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)              # opcional (p.ej. PROD, MANT)
    name = db.Column(db.String(120), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===== Modelos sincronizados con BD Remota =====
class Category(db.Model):
    """Categorías de materiales - sincronizadas desde AD17_Materiales.Categoria"""
    id = db.Column(db.Integer, primary_key=True)
    remote_id = db.Column(db.Integer, unique=True)  # regID de la BD remota
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_fabric = db.Column(db.Boolean, default=False)  # True si es categoría de telas
    is_active = db.Column(db.Boolean, default=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class Unit(db.Model):
    """Unidades de medida - sincronizadas desde AD17_General.Unidades"""
    id = db.Column(db.Integer, primary_key=True)
    remote_id = db.Column(db.Integer, unique=True)  # regID de la BD remota
    name = db.Column(db.String(50), nullable=False)
    abbreviation = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_movement = db.Column(db.DateTime)
    is_consumible = db.Column(db.Boolean, default=False)

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
    material = db.relationship('Material', backref='fabric_rolls')


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref='summary')


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    idm = db.Column(db.String(50))  # Nueva columna IDM
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    movement_type = db.Column(db.String(50), nullable=False)  # entrada, salida, retorno
    quantity = db.Column(db.Float, nullable=False)
    rollos = db.Column(db.Integer, default=0)  # Rollos
    fp_code = db.Column(db.String(100))  # Código de proyecto
    fecha = db.Column(db.Date)  # Fecha específica
    hora = db.Column(db.Time)  # Hora específica
    personal = db.Column(db.String(100))  # Personal
    area = db.Column(db.String(100))  # Área
    unit_cost = db.Column(db.Float)
    reference_id = db.Column(db.Integer)  # ID de la requisición o compra
    reference_type = db.Column(db.String(50))  # requisicion, compra, ajuste
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha creación
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Fecha modificación
    returned = db.Column(db.Boolean, default=False)
    return_date = db.Column(db.DateTime)
    return_quantity = db.Column(db.Float, default=0)
    condition_on_return = db.Column(db.String(50))  # bueno, reutilizable, reciclable, desecho

    material = db.relationship('Material', backref='movements')
    user = db.relationship('User', backref='movements')


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    material = db.relationship('Material', backref='purchase_requests')
    requester = db.relationship('User', backref='purchase_requests')

# --- NUEVO: Códigos de verificación por tipo de usuario ---
class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)     # p.ej. REQ-AB12CD
    role = db.Column(db.String(50), nullable=False)                  # requisitador/almacenista/admin
    expires_at = db.Column(db.DateTime)                              # opcional
    used_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[used_by])