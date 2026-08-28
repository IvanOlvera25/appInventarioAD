#!/usr/bin/env python3
"""Reajusta a hora de la Ciudad de México los registros guardados en UTC.

La app ahora escribe todo con utils.now_mx() (UTC-6). Los registros creados
antes del cambio quedaron en UTC, así que se ven 6 horas adelantados. Este
script les resta ese desfase una sola vez.

Uso:
    python migrate_timezone_mx.py            # simulación: no escribe nada
    python migrate_timezone_mx.py --apply    # aplica el ajuste
    python migrate_timezone_mx.py --revert   # deshace el ajuste (+6 h)

Es idempotente: deja una marca en system_config y se niega a correr dos veces.
"""
import sys
from datetime import datetime, timedelta, time

from sqlalchemy import text

from app import app, db

SHIFT_HOURS = 6                     # CDMX = UTC-6 (México no usa horario de verano)
MARKER_KEY = 'tz_migrated_to_mx'

# Columnas DATETIME que la app llenaba con datetime.utcnow()
DATETIME_COLUMNS = {
    'user':               ['created_at', 'verified_at'],
    'department':         ['created_at'],
    'project':            ['created_at'],
    'category':           ['synced_at'],
    'unit':               ['synced_at'],
    'material':           ['created_at', 'last_movement', 'disabled_at'],
    'fabric_roll':        ['created_at', 'finished_at'],
    'request':            ['created_at', 'approved_at', 'cancellation_requested_at'],
    'project_summary':    ['last_updated'],
    'stock_movement':     ['created_at', 'updated_at', 'return_date'],
    'purchase_request':   ['created_at'],
    'system_alert':       ['created_at'],
    'verification_code':  ['created_at', 'expires_at'],
    'audit_log':          ['changed_at'],
    'warehouse_location': ['created_at'],
    # El módulo de herramientas se estrenó con el código anterior, así que sus
    # marcas de tiempo también quedaron en UTC. Solo se ajustan las DATETIME:
    # acquisition_date, expected_return_date y las start/end son DATE que capturó
    # una persona en hora local, y moverlas las volvería incorrectas.
    'tool':               ['created_at'],
    'tool_loan':          ['checkout_date', 'actual_return_date', 'created_at'],
    'tool_repair':        ['created_at'],
    'tool_reservation':   ['created_at', 'cancelled_at'],
}

# system_config.updated_at se queda fuera a propósito: es la única columna con
# ON UPDATE CURRENT_TIMESTAMP, así que MariaDB la reescribiría sola durante el
# UPDATE. Son 2 filas de metadatos internos que nadie consulta.

# stock_movement.fecha (DATE) y .hora (TIME) también salían de UTC, pero hay que
# desplazarlas juntas: restar 6 h puede cambiar el día. Se verificó que en las
# 1090 filas fecha+hora coincide con created_at, o sea que ninguna se capturó
# a mano: todas vienen del mismo utcnow().
DATE_TIME_PAIRS = [('stock_movement', 'fecha', 'hora')]

SKIP_TABLES = set()


def _table_exists(conn, table):
    return conn.execute(text(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {'t': table}).scalar() > 0


def _column_exists(conn, table, column):
    return conn.execute(text(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {'t': table, 'c': column}).scalar() > 0


def already_migrated(conn):
    try:
        return conn.execute(text(
            "SELECT COUNT(*) FROM system_config WHERE `key` = :k"
        ), {'k': MARKER_KEY}).scalar() > 0
    except Exception:
        return False


def shift_datetime_columns(conn, delta, apply_changes):
    """Desplaza las columnas DATETIME. Devuelve [(tabla.columna, filas)]."""
    report = []
    sign = '-' if delta < 0 else '+'
    hours = abs(int(delta / 3600))

    for table, columns in DATETIME_COLUMNS.items():
        if table in SKIP_TABLES or not _table_exists(conn, table):
            continue
        for column in columns:
            if not _column_exists(conn, table, column):
                continue
            affected = conn.execute(text(
                f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` IS NOT NULL"
            )).scalar()
            if not affected:
                continue
            if apply_changes:
                conn.execute(text(
                    f"UPDATE `{table}` SET `{column}` = "
                    f"`{column}` {sign} INTERVAL {hours} HOUR "
                    f"WHERE `{column}` IS NOT NULL"
                ))
            report.append((f'{table}.{column}', affected))
    return report


def shift_date_time_pairs(conn, delta, apply_changes):
    """Desplaza los pares fecha/hora en Python: una resta puede cambiar el día,
    y en un solo UPDATE de SQL la segunda columna usaría el valor ya modificado
    de la primera."""
    report = []
    offset = timedelta(seconds=delta)

    for table, date_col, time_col in DATE_TIME_PAIRS:
        if not _table_exists(conn, table):
            continue
        if not (_column_exists(conn, table, date_col) and _column_exists(conn, table, time_col)):
            continue

        rows = conn.execute(text(
            f"SELECT id, `{date_col}`, `{time_col}` FROM `{table}` "
            f"WHERE `{date_col}` IS NOT NULL AND `{time_col}` IS NOT NULL"
        )).fetchall()
        if not rows:
            continue

        for row_id, d, t in rows:
            if isinstance(t, timedelta):        # MySQL devuelve TIME como timedelta
                t = (datetime.min + t).time()
            if isinstance(d, datetime):
                d = d.date()
            if not isinstance(t, time):
                continue
            moved = datetime.combine(d, t) + offset
            if apply_changes:
                conn.execute(text(
                    f"UPDATE `{table}` SET `{date_col}` = :d, `{time_col}` = :t WHERE id = :i"
                ), {'d': moved.date(), 't': moved.time(), 'i': row_id})
        report.append((f'{table}.{date_col}+{time_col}', len(rows)))
    return report


def main():
    apply_changes = '--apply' in sys.argv
    revert = '--revert' in sys.argv
    delta = (SHIFT_HOURS if revert else -SHIFT_HOURS) * 3600

    accion = 'REVERTIR (+6 h)' if revert else 'APLICAR (-6 h)'
    modo = 'EJECUCIÓN REAL' if apply_changes else 'SIMULACIÓN (no escribe nada)'
    print(f'\n{"=" * 66}\n  Ajuste de zona horaria UTC → Ciudad de México\n'
          f'  Acción: {accion}\n  Modo:   {modo}\n{"=" * 66}\n')

    with app.app_context():
        with db.engine.begin() as conn:
            migrated = already_migrated(conn)
            if migrated and not revert:
                print('⚠️  Este ajuste ya se aplicó antes (marca en system_config).')
                print('    Si de verdad necesitas repetirlo, borra la fila:')
                print(f"    DELETE FROM system_config WHERE `key` = '{MARKER_KEY}';\n")
                return 1
            if revert and not migrated:
                print('⚠️  No hay ajuste previo que revertir.\n')
                return 1

            report = shift_datetime_columns(conn, delta, apply_changes)
            report += shift_date_time_pairs(conn, delta, apply_changes)

            if not report:
                print('No se encontraron registros que ajustar.\n')
                return 0

            width = max(len(name) for name, _ in report)
            total = 0
            for name, count in sorted(report):
                print(f'  {name.ljust(width)}  {count:>8,} filas')
                total += count
            print(f'\n  {"TOTAL".ljust(width)}  {total:>8,} filas')

            if apply_changes:
                if revert:
                    conn.execute(text("DELETE FROM system_config WHERE `key` = :k"),
                                 {'k': MARKER_KEY})
                else:
                    from utils import now_mx
                    stamp = now_mx()
                    conn.execute(text(
                        "INSERT INTO system_config (`key`, `value`, `updated_at`) "
                        "VALUES (:k, :v, :t) ON DUPLICATE KEY UPDATE `value` = :v"
                    ), {'k': MARKER_KEY, 'v': stamp.strftime('%Y-%m-%d %H:%M:%S'), 't': stamp})
                print('\n✅ Ajuste aplicado y confirmado.\n')
            else:
                print('\nSimulación terminada. Para aplicarlo de verdad:')
                print('    python migrate_timezone_mx.py --apply\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
