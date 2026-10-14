"""Asigna retroactivamente la FP a los cortes de tela que se registraron sin ella.

Los cortes con motivo Muestra, Desperdicio y Material Defectuoso no pedían FP, así
que entre el 03/09/2026 y el 06/10/2026 se registraron 11 salidas sin proyecto al
que cargarlas (ver el commit que exige FP en todos los motivos salvo Ajuste).

Uso:
    1. Llena ASIGNACIONES con la FP que producción confirme para cada movimiento.
       Deja fuera (o en None) los que de verdad no deban llevar FP.
    2. Corre en seco para revisar lo que haría, sin tocar nada:
           python3 reclasificar_cortes_sin_fp.py
    3. Aplica los cambios:
           python3 reclasificar_cortes_sin_fp.py --aplicar

El script solo toca movimientos con reference_type='corte_rollo' y fp_code vacío;
si un id ya tiene FP lo deja igual y lo reporta. Además corrige el área, que en
todos estos registros quedó como 'Producción' por el default anterior.
"""

import sys

import pymysql

from config import Config as C

# ── id del movimiento → FP confirmada por producción ─────────────────────────
# Pon None en los que deban quedarse sin FP.
ASIGNACIONES = {
    1350: None,   # 03/09 13:49 · Tela Lx Blanca 2.60   ·  70.00 m · rollo 93               · Material Defectuoso
    2051: None,   # 30/09 12:45 · Tela Lumicom De 3.20  ·   0.70 m · rollo 150              · Desperdicio
    2304: None,   # 01/10 14:40 · Tela Sarga Blanca 3.20·   2.00 m · rollo 128              · Desperdicio
    2305: None,   # 01/10 14:40 · Tela Sarga Blanca 3.20·   0.50 m · rollo 120              · Desperdicio
    2546: None,   # 02/10 09:20 · Tela Lx Negra 3.20    ·   0.76 m · rollo 173              · Desperdicio
    2646: None,   # 02/10 13:30 · Tela Lumicom De 3.20  ·  74.00 m · rollo ROL-20261002-009 · Material Defectuoso
    2684: None,   # 02/10 18:45 · Tela Liner 1.50       ·  41.00 m · rollo 166              · Material Defectuoso
    2685: None,   # 02/10 18:47 · Tela Liner 1.50       ·  28.00 m · rollo 84               · Desperdicio
    2686: None,   # 02/10 18:47 · Tela Liner 1.50       ·  41.00 m · rollo 83               · Material Defectuoso
    2687: None,   # 02/10 18:47 · Tela Liner 1.50       ·  45.00 m · rollo 82               · Desperdicio
    2742: None,   # 06/10 15:01 · Tela Lx Blanca 2.60   · 247.00 m · rollo ROL-20261001-003 · Desperdicio
}

# Área que corresponde a cada motivo, igual que CUT_REASON_DEFAULT_AREA en app.py.
AREA_POR_MOTIVO = {
    'Producción':          'Producción',
    'Muestra':             'Muestra',
    'Desperdicio':         'Desperdicio',
    'Material Defectuoso': 'Material Defectuoso',
    'Ajuste de Inventario': 'Ajuste de Inventario',
}


def motivo_de(notes):
    if notes and 'Motivo: ' in notes:
        return notes.split('Motivo: ')[1].split(' · ')[0].strip()
    return ''


def main():
    aplicar = '--aplicar' in sys.argv

    pendientes = {mid: fp for mid, fp in ASIGNACIONES.items() if fp}
    if not pendientes:
        print('No hay ninguna FP asignada en ASIGNACIONES. Llena el diccionario y vuelve a correr.')
        return 1

    conn = pymysql.connect(host=C.REMOTE_DB_HOST, port=C.REMOTE_DB_PORT,
                           user=C.REMOTE_DB_USER, password=C.REMOTE_DB_PASSWORD,
                           database=C.MAIN_SCHEMA, charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)
    cambios, omitidos = [], []
    try:
        with conn.cursor() as cur:
            marcas = ','.join(['%s'] * len(pendientes))
            cur.execute(
                f"""SELECT id, fp_code, area, quantity, notes
                    FROM stock_movement
                    WHERE id IN ({marcas}) AND reference_type = 'corte_rollo'""",
                list(pendientes),
            )
            filas = {r['id']: r for r in cur.fetchall()}

        for mid, fp in pendientes.items():
            fila = filas.get(mid)
            if not fila:
                omitidos.append((mid, 'no existe o no es un corte de rollo'))
                continue
            if fila['fp_code']:
                omitidos.append((mid, f"ya tiene FP {fila['fp_code']}"))
                continue

            motivo = motivo_de(fila['notes'])
            area_nueva = AREA_POR_MOTIVO.get(motivo, fila['area'])
            # La nota guarda el detalle del corte: se le añade la FP asignada.
            notes_nuevas = f"{fila['notes']} · FP asignada posteriormente: {fp}"
            cambios.append({
                'id': mid, 'fp': fp, 'motivo': motivo, 'metros': fila['quantity'],
                'area_vieja': fila['area'], 'area_nueva': area_nueva,
                'notes': notes_nuevas,
            })

        print(f"{'ID':>6} {'FP':<14} {'MOTIVO':<22} {'METROS':>8}  ÁREA")
        print('-' * 78)
        for c in cambios:
            print(f"{c['id']:>6} {c['fp']:<14} {c['motivo']:<22} {c['metros']:>8}  "
                  f"{c['area_vieja']} → {c['area_nueva']}")
        for mid, razon in omitidos:
            print(f"{mid:>6} (omitido: {razon})")

        if not aplicar:
            print(f"\nSIMULACIÓN: {len(cambios)} movimiento(s) se actualizarían. "
                  f"Vuelve a correr con --aplicar para guardarlos.")
            return 0

        with conn.cursor() as cur:
            for c in cambios:
                cur.execute(
                    """UPDATE stock_movement
                       SET fp_code = %s, area = %s, notes = %s
                       WHERE id = %s AND reference_type = 'corte_rollo'
                         AND (fp_code IS NULL OR fp_code = '')""",
                    (c['fp'], c['area_nueva'], c['notes'], c['id']),
                )
        conn.commit()
        print(f"\nListo: {len(cambios)} movimiento(s) actualizados.")
        return 0
    except Exception as e:
        conn.rollback()
        print(f'Error, no se guardó nada: {e}')
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
