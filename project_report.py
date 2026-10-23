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


# El tercer result set identifica el material y dice cuánto puede salir. Los
# nombres exactos los pone el procedimiento, así que se aceptan los alias
# habituales en lugar de atar la app a una revisión concreta de la base.
_AVAILABILITY_ID_KEYS = ('material_id', 'id_material', 'idmaterial', 'id')
_AVAILABILITY_CODE_KEYS = ('material_code', 'codigo', 'code', 'clave')
_AVAILABILITY_NAME_KEYS = ('material_name', 'material', 'nombre', 'name', 'descripcion')
_AVAILABILITY_QTY_KEYS = (
    'max_salida', 'maximo', 'max', 'disponible', 'cantidad_disponible',
    'por_entregar', 'pendiente_entrega', 'quantity_available', 'available',
    'cantidad', 'quantity',
)


def _first_key(row, candidates):
    """Primera columna presente de una lista de alias, comparando sin may/min."""
    normalizadas = {str(key).strip().lower(): key for key in row}
    for candidate in candidates:
        if candidate in normalizadas:
            return normalizadas[candidate]
    return None


def parse_fp_availability(rows):
    """Normaliza el tercer result set a {material_id|code|name: cantidad}.

    Devuelve tres índices para que quien consulte pueda cruzar por lo que tenga
    a la mano. Si no se reconoce la forma de las filas, devuelve índices vacíos
    y quien llama decide el respaldo.
    """
    por_id, por_codigo, por_nombre = {}, {}, {}
    for row in rows or []:
        qty_key = _first_key(row, _AVAILABILITY_QTY_KEYS)
        if qty_key is None:
            continue
        try:
            cantidad = float(row.get(qty_key) or 0)
        except (TypeError, ValueError):
            continue

        id_key = _first_key(row, _AVAILABILITY_ID_KEYS)
        if id_key is not None and row.get(id_key) not in (None, ''):
            try:
                por_id[int(row[id_key])] = cantidad
            except (TypeError, ValueError):
                pass

        code_key = _first_key(row, _AVAILABILITY_CODE_KEYS)
        if code_key is not None and row.get(code_key):
            por_codigo[str(row[code_key]).strip().casefold()] = cantidad

        name_key = _first_key(row, _AVAILABILITY_NAME_KEYS)
        if name_key is not None and row.get(name_key):
            por_nombre[str(row[name_key]).strip().casefold()] = cantidad

    return {'by_id': por_id, 'by_code': por_codigo, 'by_name': por_nombre}


def read_fp_availability(engine, fp_code):
    """Tercer result set de sp_resumen_fp: lo que se puede sacar de almacén.

    Es el tope oficial de una salida. Se consulta aquí y no se recalcula en la
    app para que almacén y el procedimiento no puedan discrepar.
    Devuelve (índices, filas_crudas).
    """
    rows = read_project_report(engine, fp_code).get('availability', [])
    return parse_fp_availability(rows), rows
