"""FP a asignar a los cortes de tela que se registraron sin proyecto.

Entre el 03/09/2026 y el 06/10/2026 se capturaron 11 cortes sin FP, porque los
motivos Muestra, Desperdicio y Material Defectuoso no pedían el proyecto. El
código ya no lo permite, pero esos registros siguen sin FP y solo producción
sabe a qué proyecto pertenece cada uno.

Escribe aquí la FP de cada corte y haz Reload de la app: al arrancar se aplican
solas. Es idempotente — solo toca movimientos de corte que aún no tienen FP, así
que puedes dejarlas puestas para siempre sin riesgo de que se repitan.

    1350: 'FP-2026-044',   # ← así

Deja en None los que de verdad no deban llevar FP; esos se quedan como están.
"""

ASIGNACIONES = {
    # id     FP            fecha y hora   material                metros  rollo                   motivo
    1350: None,   # 03/09 13:49 · Tela Lx Blanca 2.60    ·  70.00 m · rollo 93               · Material Defectuoso
    2051: None,   # 30/09 12:45 · Tela Lumicom De 3.20   ·   0.70 m · rollo 150              · Desperdicio
    2304: None,   # 01/10 14:40 · Tela Sarga Blanca 3.20 ·   2.00 m · rollo 128              · Desperdicio
    2305: None,   # 01/10 14:40 · Tela Sarga Blanca 3.20 ·   0.50 m · rollo 120              · Desperdicio
    2546: None,   # 02/10 09:20 · Tela Lx Negra 3.20     ·   0.76 m · rollo 173              · Desperdicio
    2646: None,   # 02/10 13:30 · Tela Lumicom De 3.20   ·  74.00 m · rollo ROL-20261002-009 · Material Defectuoso
    2684: None,   # 02/10 18:45 · Tela Liner 1.50        ·  41.00 m · rollo 166              · Material Defectuoso
    2685: None,   # 02/10 18:47 · Tela Liner 1.50        ·  28.00 m · rollo 84               · Desperdicio
    2686: None,   # 02/10 18:47 · Tela Liner 1.50        ·  41.00 m · rollo 83               · Material Defectuoso
    2687: None,   # 02/10 18:47 · Tela Liner 1.50        ·  45.00 m · rollo 82               · Desperdicio
    2742: None,   # 06/10 15:01 · Tela Lx Blanca 2.60    · 247.00 m · rollo ROL-20261001-003 · Desperdicio
}


def pendientes():
    """Devuelve {id: fp} solo con las asignaciones realmente capturadas."""
    return {
        int(mid): str(fp).strip()
        for mid, fp in ASIGNACIONES.items()
        if fp and str(fp).strip()
    }
