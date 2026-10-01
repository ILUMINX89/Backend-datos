"""Consultas de recursos ZTE con baja disponibilidad."""

from typing import Any

from microservicios.mysql import consultar_mysql


CONSULTA_LICENCIAS_BAJAS = """
SELECT
    olt,
    recurso,
    usado,
    disponible,
    CAST(usado AS DECIMAL(30, 0)) + CAST(disponible AS DECIMAL(30, 0)) AS total,
    (disponible / NULLIF(
        CAST(usado AS DECIMAL(30, 0)) + CAST(disponible AS DECIMAL(30, 0)),
        0
    )) * 100 AS porcentaje_disponible,
    actualizado_en
FROM OLT.recursos_zte
WHERE CAST(usado AS DECIMAL(30, 0)) + CAST(disponible AS DECIMAL(30, 0)) > 0
  AND (disponible / (
      CAST(usado AS DECIMAL(30, 0)) + CAST(disponible AS DECIMAL(30, 0))
  )) * 100 < %s
ORDER BY porcentaje_disponible ASC, olt ASC, recurso ASC
"""


def obtener_licencias_bajas_mysql(umbral_pct: float) -> list[dict[str, Any]]:
    """Obtiene únicamente los recursos ZTE bajo el umbral indicado."""
    return consultar_mysql(CONSULTA_LICENCIAS_BAJAS, (umbral_pct,))
