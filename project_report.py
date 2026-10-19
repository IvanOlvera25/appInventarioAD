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
            if len(results) != 2:
                raise ValueError('sp_resumen_fp debe devolver requisiciones y materiales')
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
    for material in materials:
        material['area'] = (material.get('area') or '').strip() or 'Sin área'
        for field in ('quantity_requested', 'quantity_delivered', 'quantity_pending'):
            material[field] = float(material.get(field) or 0)
    materials.sort(key=lambda m: (m['area'].casefold(), (m.get('category') or '').casefold(),
                                 (m.get('name') or '').casefold()))
    return {'requests': requests, 'materials': materials}
