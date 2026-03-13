# utils.py - Funciones auxiliares para el sistema de almacén

from datetime import datetime, timedelta
from flask import flash
import re
import os

def validate_material_code(code):
    """
    Valida que el código del material sea válido
    - No debe contener espacios
    - Debe tener al menos 3 caracteres
    - Solo letras, números y guiones
    """
    if not code:
        return False, "El código es requerido"
    
    if len(code) < 3:
        return False, "El código debe tener al menos 3 caracteres"
    
    if ' ' in code:
        return False, "El código no puede contener espacios"
    
    if not re.match(r'^[A-Za-z0-9\-_]+$', code):
        return False, "El código solo puede contener letras, números y guiones"
    
    return True, "Código válido"

def calculate_recycled_price(original_price):
    """
    Calcula el precio de un material reciclado (50% del precio original)
    """
    return original_price * 0.5

def calculate_reused_price(original_price):
    """
    Calcula el precio de un material reutilizado (mismo precio)
    """
    return original_price

def get_stock_status(current_stock, min_stock, max_stock):
    """
    Determina el estado del stock basado en los límites
    """
    if current_stock <= min_stock:
        return "bajo", "danger"
    elif current_stock >= max_stock:
        return "alto", "warning"
    else:
        return "normal", "success"

def generate_request_number():
    """
    Genera un número único de requisición
    """
    today = datetime.utcnow()
    # Importar aquí para evitar circular imports
    from app import Request
    
    count = Request.query.filter(
        Request.created_at >= today.replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    return f"REQ-{today.strftime('%Y%m%d')}-{count + 1:04d}"

def generate_purchase_request_number():
    """
    Genera un número único de solicitud de compra
    """
    today = datetime.utcnow()
    # Importar aquí para evitar circular imports
    from app import PurchaseRequest
    
    count = PurchaseRequest.query.filter(
        PurchaseRequest.created_at >= today.replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    return f"COMP-{today.strftime('%Y%m%d')}-{count + 1:04d}"

def check_materials_without_movement(months=6):
    """
    Encuentra materiales sin movimiento en los últimos X meses
    """
    cutoff_date = datetime.utcnow() - timedelta(days=months * 30)
    # Importar aquí para evitar circular imports
    from app import Material
    
    materials = Material.query.filter(
        (Material.last_movement < cutoff_date) | 
        (Material.last_movement.is_(None))
    ).all()
    
    return materials

def get_low_stock_materials():
    """
    Obtiene materiales con stock bajo
    """
    # Importar aquí para evitar circular imports
    from app import Material
    
    return Material.query.filter(
        Material.current_stock <= Material.min_stock
    ).all()

def update_material_stock(material_id, quantity, movement_type):
    """
    Actualiza el stock de un material según el tipo de movimiento
    """
    # Importar aquí para evitar circular imports
    from app import Material, db
    
    material = Material.query.get(material_id)
    if not material:
        return False, "Material no encontrado"
    
    if movement_type == 'entrada' or movement_type == 'retorno':
        material.current_stock += quantity
    elif movement_type == 'salida':
        if material.current_stock < quantity:
            return False, f"Stock insuficiente. Disponible: {material.current_stock}"
        material.current_stock -= quantity
    else:
        return False, "Tipo de movimiento inválido"
    
    material.last_movement = datetime.utcnow()
    db.session.commit()
    
    return True, "Stock actualizado correctamente"

def calculate_fabric_usage_percentage(total_length, remaining_length):
    """
    Calcula el porcentaje de uso de un rollo de tela
    """
    if total_length <= 0:
        return 0
    
    used_length = total_length - remaining_length
    return (used_length / total_length) * 100

def validate_fabric_cut(roll_id, cut_length):
    """
    Valida que un corte de tela sea válido
    """
    # Importar aquí para evitar circular imports
    from app import FabricRoll
    
    roll = FabricRoll.query.get(roll_id)
    if not roll:
        return False, "Rollo no encontrado"
    
    if cut_length <= 0:
        return False, "La longitud de corte debe ser mayor a 0"
    
    if cut_length > roll.remaining_length:
        return False, f"Longitud insuficiente. Disponible: {roll.remaining_length}m"
    
    return True, "Corte válido"

def process_fabric_cut(roll_id, cut_length, reason, notes=""):
    """
    Procesa un corte de tela y actualiza el rollo
    """
    # Importar aquí para evitar circular imports
    from app import FabricRoll, StockMovement, db, current_user
    
    # Validar el corte
    is_valid, message = validate_fabric_cut(roll_id, cut_length)
    if not is_valid:
        return False, message
    
    roll = FabricRoll.query.get(roll_id)
    
    # Actualizar el rollo
    roll.remaining_length -= cut_length
    
    # Crear movimiento de stock
    movement = StockMovement(
        material_id=roll.material_id,
        movement_type='salida',
        quantity=cut_length,
        reference_type='corte_tela',
        reference_id=roll_id,
        user_id=current_user.id,
        notes=f"Corte de tela - {reason}: {notes}"
    )
    
    db.session.add(movement)
    
    # Actualizar estado del rollo
    if roll.remaining_length <= 0:
        roll.status = 'agotado'
    elif roll.remaining_length < (roll.total_length * 0.1):  # Menos del 10%
        roll.status = 'critico'
    else:
        roll.status = 'disponible'
    
    db.session.commit()
    
    return True, "Corte procesado correctamente"

def export_inventory_report():
    """
    Genera datos para exportar reporte de inventario
    """
    # Importar aquí para evitar circular imports
    from app import Material
    
    materials = Material.query.all()
    
    report_data = []
    for material in materials:
        status, _ = get_stock_status(material.current_stock, material.min_stock, material.max_stock)
        
        report_data.append({
            'Código': material.code,
            'Nombre': material.name,
            'Categoría': material.category,
            'Stock Actual': material.current_stock,
            'Unidad': material.unit,
            'Stock Mínimo': material.min_stock,
            'Stock Máximo': material.max_stock,
            'Estado': status,
            'Costo Unitario': material.unit_cost,
            'Valor Total': material.current_stock * material.unit_cost,
            'Último Movimiento': material.last_movement.strftime('%d/%m/%Y') if material.last_movement else 'Nunca'
        })
    
    return report_data

def export_movements_report(start_date=None, end_date=None):
    """
    Genera datos para exportar reporte de movimientos
    """
    # Importar aquí para evitar circular imports
    from app import StockMovement
    
    query = StockMovement.query
    
    if start_date:
        query = query.filter(StockMovement.created_at >= start_date)
    if end_date:
        query = query.filter(StockMovement.created_at <= end_date)
    
    movements = query.order_by(StockMovement.created_at.desc()).all()
    
    report_data = []
    for movement in movements:
        report_data.append({
            'Fecha': movement.created_at.strftime('%d/%m/%Y %H:%M'),
            'Material': f"{movement.material.code} - {movement.material.name}",
            'Tipo': movement.movement_type,
            'Cantidad': movement.quantity,
            'Unidad': movement.material.unit,
            'Costo Unitario': movement.unit_cost or 0,
            'Costo Total': (movement.unit_cost or 0) * movement.quantity,
            'Usuario': movement.user.username,
            'Referencia': movement.reference_type or '',
            'Notas': movement.notes or ''
        })
    
    return report_data

def create_purchase_alert(material):
    """
    Crea una alerta de compra para un material con stock bajo
    """
    # Importar aquí para evitar circular imports
    from app import PurchaseRequest, db, current_user
    
    # Verificar si ya existe una solicitud pendiente
    existing_request = PurchaseRequest.query.filter_by(
        material_id=material.id,
        status='pendiente'
    ).first()
    
    if existing_request:
        return False, "Ya existe una solicitud de compra pendiente para este material"
    
    # Calcular cantidad sugerida (hasta el stock máximo)
    suggested_quantity = material.max_stock - material.current_stock
    
    # Crear solicitud de compra
    request_number = generate_purchase_request_number()
    
    purchase_request = PurchaseRequest(
        request_number=request_number,
        material_id=material.id,
        quantity=suggested_quantity,
        requested_by=current_user.id,
        notes=f"Solicitud automática - Stock bajo: {material.current_stock} {material.unit}"
    )
    
    db.session.add(purchase_request)
    db.session.commit()
    
    return True, f"Solicitud de compra {request_number} creada"

def backup_database():
    """
    Crea un respaldo de la base de datos
    """
    import shutil
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"almacen_backup_{timestamp}.db"
    
    try:
        shutil.copy2('almacen.db', backup_filename)
        return True, f"Respaldo creado: {backup_filename}"
    except Exception as e:
        return False, f"Error al crear respaldo: {str(e)}"

def clean_old_movements(days=365):
    """
    Limpia movimientos antiguos (opcional, para mantenimiento)
    """
    # Importar aquí para evitar circular imports
    from app import StockMovement, db
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_movements = StockMovement.query.filter(
        StockMovement.created_at < cutoff_date
    ).count()
    
    if old_movements > 0:
        StockMovement.query.filter(
            StockMovement.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        return True, f"Se eliminaron {old_movements} movimientos antiguos"
    
    return True, "No hay movimientos antiguos para eliminar"

def get_department_statistics(department):
    """
    Obtiene estadísticas específicas de un departamento
    """
    # Importar aquí para evitar circular imports
    from app import Request, RequestItem
    
    # Requisiciones del departamento
    dept_requests = Request.query.filter_by(department=department).all()
    
    total_requests = len(dept_requests)
    pending_requests = len([r for r in dept_requests if r.status == 'pendiente'])
    completed_requests = len([r for r in dept_requests if r.status == 'completada'])
    
    # Calcular eficiencia
    efficiency = (completed_requests / total_requests * 100) if total_requests > 0 else 0
    
    # Materiales más solicitados
    from sqlalchemy import func
    popular_materials = db.session.query(
        RequestItem.material_id,
        func.sum(RequestItem.quantity_requested).label('total_quantity')
    ).join(Request).filter(
        Request.department == department
    ).group_by(RequestItem.material_id).order_by(
        func.sum(RequestItem.quantity_requested).desc()
    ).limit(5).all()
    
    return {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'completed_requests': completed_requests,
        'efficiency': efficiency,
        'popular_materials': popular_materials
    }

# Constantes útiles
MOVEMENT_TYPES = {
    'entrada': 'Entrada',
    'salida': 'Salida',
    'retorno': 'Retorno'
}

MATERIAL_CONDITIONS = {
    'bueno': 'Buen Estado',
    'reutilizable': 'Reutilizable',
    'reciclable': 'Solo Reciclable',
    'desecho': 'Desecho'
}

REQUEST_STATUSES = {
    'pendiente': 'Pendiente',
    'aprobada': 'Aprobada',
    'en_proceso': 'En Proceso',
    'completada': 'Completada',
    'cancelada': 'Cancelada'
}

DEPARTMENTS = [
    'Producción',
    'Mantenimiento',
    'Calidad',
    'Ingeniería',
    'Logística',
    'Administración'
]

MATERIAL_CATEGORIES = [
    'Metales',
    'Textiles',
    'Ferretería',
    'Químicos',
    'Electrónicos',
    'Herramientas',
    'Otros'
]