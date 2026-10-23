"""Lectura del resumen oficial de un FP, sin reconstruir entregas desde requisiciones."""
from datetime import date, datetime
from decimal import Decimal


def read_project_report(engine, fp_code):
    """Consume todos los result sets, incluido el vacío final de MySQL CALL.

    La conexión pertenece a esta lectura: las tablas temporales del procedimiento
    y el cursor nunca se comparten entre solicitudes HTTP.
    """
    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute('CALL sp_resumen_fp(%s)', (fp_code,))
            results = []
            while True:
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    results.append([dict(zip(columns, row)) for row in cursor.fetchall()])
                if not cursor.nextset():
                    break
            if len(results) < 2:
                raise ValueError('sp_resumen_fp debe devolver al menos requisiciones y materiales')
        finally:
            cursor.close()
    finally:
        # Devuelve la conexión al pool sin conservar una transacción abierta.
        try:
            connection.rollback()
        finally:
            connection.close()

    def serializable(row):
        return {key: (value.isoformat() if isinstance(value, (date, datetime))
                      else float(value) if isinstance(value, Decimal) else value)
                for key, value in row.items()}

    requests = [serializable(row) for row in results[0]]
    materials = [serializable(row) for row in results[1]]
    # El procedimiento ganó un tercer result set (tope de salida por material).
    # Se acepta tanto la versión de 2 como la de 3 para no atar la app a una
    # revisión concreta de la base.
    availability = [serializable(row) for row in results[2]] if len(results) > 2 else []

    for material in materials:
        material['area'] = (material.get('area') or '').strip() or 'Sin área'
        for field in ('quantity_requested', 'quantity_delivered', 'quantity_pending'):
            material[field] = float(material.get(field) or 0)
    materials.sort(key=lambda m: (m['area'].casefold(), (m.get('category') or '').casefold(),
                                 (m.get('name') or '').casefold()))
    return {'requests': requests, 'materials': materials, 'availability': availability}


# Tercer result set de sp_resumen_fp. Columnas reales del procedimiento:
#   area, material_id, name, unit, category, quantity_requested,
#   quantity_delivered, quantity_supplied, quantity_on_stock,
#   quantity_supplied_pending, quantity_max_deliverable
# donde quantity_max_deliverable = GREATEST(LEAST(abastecido_pendiente, stock), 0)
# y las filas vienen por (área, material), ya filtradas a las que sí pueden salir.
# Se aceptan además algunos alias por si el procedimiento se renombra.
_AVAILABILITY_ID_KEYS = ('material_id', 'id_material', 'idmaterial', 'id')
_AVAILABILITY_CODE_KEYS = ('material_code', 'codigo', 'code', 'clave')
_AVAILABILITY_NAME_KEYS = ('name', 'material_name', 'material', 'nombre', 'descripcion')
_AVAILABILITY_AREA_KEYS = ('area', 'área', 'departamento', 'department')
_AVAILABILITY_QTY_KEYS = (
    'quantity_max_deliverable', 'max_salida', 'maximo', 'max', 'disponible',
    'cantidad_disponible', 'por_entregar', 'pendiente_entrega',
    'quantity_available', 'available', 'cantidad', 'quantity',
)


def _first_key(row, candidates):
    """Primera columna presente de una lista de alias, comparando sin may/min."""
    normalizadas = {str(key).strip().lower(): key for key in row}
    for candidate in candidates:
        if candidate in normalizadas:
            return normalizadas[candidate]
    return None


def parse_fp_availability(rows, area=None):
    """Normaliza el tercer result set a {material_id|code|name: cantidad}.

    El procedimiento devuelve una fila por (área, material), así que las
    cantidades se SUMAN por material. Con `area` se limita a esa área, que es lo
    que corresponde cuando la salida se captura para un área concreta.

    Devuelve tres índices para cruzar por lo que se tenga a la mano. Si no se
    reconoce la forma de las filas, los índices van vacíos y quien llama decide
    el respaldo.
    """
    por_id, por_codigo, por_nombre = {}, {}, {}
    area_buscada = str(area).strip().casefold() if area else None

    for row in rows or []:
        qty_key = _first_key(row, _AVAILABILITY_QTY_KEYS)
        if qty_key is None:
            continue
        try:
            cantidad = float(row.get(qty_key) or 0)
        except (TypeError, ValueError):
            continue

        if area_buscada is not None:
            area_key = _first_key(row, _AVAILABILITY_AREA_KEYS)
            fila_area = str(row.get(area_key) or '').strip().casefold() if area_key else ''
            if fila_area != area_buscada:
                continue

        def acumular(destino, clave):
            destino[clave] = destino.get(clave, 0.0) + cantidad

        id_key = _first_key(row, _AVAILABILITY_ID_KEYS)
        if id_key is not None and row.get(id_key) not in (None, ''):
            try:
                acumular(por_id, int(row[id_key]))
            except (TypeError, ValueError):
                pass

        code_key = _first_key(row, _AVAILABILITY_CODE_KEYS)
        if code_key is not None and row.get(code_key):
            acumular(por_codigo, str(row[code_key]).strip().casefold())

        name_key = _first_key(row, _AVAILABILITY_NAME_KEYS)
        if name_key is not None and row.get(name_key):
            acumular(por_nombre, str(row[name_key]).strip().casefold())

    return {'by_id': por_id, 'by_code': por_codigo, 'by_name': por_nombre}


def read_fp_availability(engine, fp_code, area=None):
    """Tercer result set de sp_resumen_fp: lo que se puede sacar de almacén.

    Es el tope oficial de una salida. Se consulta aquí y no se recalcula en la
    app para que almacén y el procedimiento no puedan discrepar.
    Devuelve (índices, filas_crudas).
    """
    rows = read_project_report(engine, fp_code).get('availability', [])
    return parse_fp_availability(rows, area=area), rows
