"""Consultas interactivas a InfluxDB para tráfico OLT."""

import json
import sys

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from influx import consultar_flux_temp

# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================

BUCKET = "trafico_temperatura_olts"

ESTADO_NORMAL = 6

SATURACION_MINIMA = 70.0

CRC_MINIMO_POR_SEGUNDO = 10.0

MINIMO_MUESTRAS_SATURACION = 2

SEPARACION_EPISODIO_MINUTOS = 30

MARGEN_CORRELACION_MINUTOS = 10


# ==========================================================
# CONSULTA 1
# SATURACIÓN
# ==========================================================

CONSULTA_SATURACION = f"""
from(bucket: "{BUCKET}")

  |> range(start: -24h)

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({{
      r with
      SATURACION:
        if r.INPUT > r.OUTPUT then
          (r.INPUT / 10000000.0) * 100.0
        else
          (r.OUTPUT / 10000000.0) * 100.0
  }}))

  |> filter(fn: (r) =>
      r.SATURACION > {SATURACION_MINIMA}
  )

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO",
          "_time"
      ]
  )
"""


# ==========================================================
# CONSULTA 2
# CAÍDAS - ÚLTIMOS 7 DÍAS
# ==========================================================

CONSULTA_CAIDAS = f"""
from(bucket: "{BUCKET}")

  |> range(start: -7d)

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "ESTADO"
  )

  |> keep(
      columns: [
          "_time",
          "_value",
          "OLT",
          "PUERTO"
      ]
  )

  |> rename(
      columns: {{
          _value: "ESTADO"
      }}
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> group(columns: [])
"""


# ==========================================================
# CONSULTA 3
# CRC - ÚLTIMAS 24 HORAS
# ==========================================================

CONSULTA_CRC = f"""
from(bucket: "{BUCKET}")

  |> range(start: -24h)

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "CRC"
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> rename(
      columns: {{
          _value: "CRC_POR_SEGUNDO"
      }}
  )

  |> filter(fn: (r) =>
      r.CRC_POR_SEGUNDO > {CRC_MINIMO_POR_SEGUNDO}
  )

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO",
          "_time"
      ]
  )
"""


# ==========================================================
# CONSULTA 4
# ESTADOS PARA CORRELACIÓN - ÚLTIMAS 24 HORAS
# ==========================================================

CONSULTA_CAIDAS_CORRELACION = f"""
from(bucket: "{BUCKET}")

  |> range(start: -24h)

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "ESTADO"
  )

  |> keep(
      columns: [
          "_time",
          "_value",
          "OLT",
          "PUERTO"
      ]
  )

  |> rename(
      columns: {{
          _value: "ESTADO"
      }}
  )

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO",
          "_time"
      ]
  )
"""


# ==========================================================
# SERIALIZACIÓN
# ==========================================================


def serializar(valor: Any) -> str:
    if isinstance(
        valor,
        (
            date,
            datetime,
        ),
    ):
        return valor.isoformat()

    return str(valor)


# ==========================================================
# AGRUPAR EVENTOS DE SATURACIÓN / CRC
# ==========================================================


def agrupar_eventos(
    datos,
    campo_valor,
    minimo_muestras=1,
    separacion_minutos=30,
):
    """
    Agrupa muestras por OLT + PUERTO.

    Si pasan 30 minutos o más entre dos muestras,
    se considera un episodio diferente.
    """

    grupos = defaultdict(list)

    for fila in datos:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        if not olt or not puerto or fecha is None:
            continue

        grupos[(olt, puerto)].append(fila)

    resultado = defaultdict(list)

    for (
        olt,
        puerto,
    ), muestras in grupos.items():

        muestras.sort(key=lambda fila: fila["_time"])

        episodio = []

        def guardar_episodio():
            if len(episodio) < minimo_muestras:
                return

            valores = []

            for item in episodio:

                valor = item.get(campo_valor)

                if valor is None:
                    continue

                try:
                    valores.append(float(valor))

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if not valores:
                return

            inicio = episodio[0]["_time"]

            fin = episodio[-1]["_time"]

            duracion_timestamps = (fin - inicio).total_seconds() / 60

            resultado[(olt, puerto)].append(
                {
                    "inicio": inicio,
                    "fin": fin,
                    "muestras": len(episodio),
                    "duracion_entre_timestamps_minutos": round(
                        duracion_timestamps,
                        2,
                    ),
                    "maximo": round(
                        max(valores),
                        2,
                    ),
                    "promedio": round(
                        sum(valores) / len(valores),
                        2,
                    ),
                }
            )

        for muestra in muestras:

            if not episodio:

                episodio.append(muestra)

                continue

            anterior = episodio[-1]

            diferencia = (muestra["_time"] - anterior["_time"]).total_seconds() / 60

            if diferencia >= separacion_minutos:

                guardar_episodio()

                episodio = [muestra]

            else:

                episodio.append(muestra)

        guardar_episodio()

    return resultado


# ==========================================================
# SATURACIÓN
# ==========================================================


def consultar_saturacion():

    print()
    print("Consultando episodios de saturación...")
    print()

    datos = consultar_flux_temp(CONSULTA_SATURACION)

    episodios = agrupar_eventos(
        datos,
        campo_valor="SATURACION",
        minimo_muestras=MINIMO_MUESTRAS_SATURACION,
        separacion_minutos=SEPARACION_EPISODIO_MINUTOS,
    )

    resultado_olts = defaultdict(list)

    for (
        olt,
        puerto,
    ), eventos in episodios.items():

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "cantidad_episodios": len(eventos),
                "episodios": eventos,
            }
        )

    resultado = []

    for olt in sorted(resultado_olts.keys()):

        puertos = resultado_olts[olt]

        puertos.sort(
            key=lambda item: max(evento["maximo"] for evento in item["episodios"]),
            reverse=True,
        )

        resultado.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos),
                "puertos": puertos,
            }
        )

    return {
        "consulta": "saturacion",
        "periodo": "ultimas_24_horas",
        "criterio": ("saturacion_mayor_70_" "minimo_2_muestras"),
        "separacion_nuevo_episodio_minutos": SEPARACION_EPISODIO_MINUTOS,
        "cantidad_olts": len(resultado),
        "datos": resultado,
    }


# ==========================================================
# RECONSTRUIR CAÍDAS
# ==========================================================


def reconstruir_caidas(
    datos,
):
    """
    Reconstruye todas las caídas encontradas.

    ESTADO == 6:
        normal

    ESTADO != 6:
        caída / anomalía
    """

    puertos = defaultdict(list)

    for fila in datos:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        if not olt or not puerto:
            continue

        puertos[(olt, puerto)].append(fila)

    ahora = datetime.now(timezone.utc)

    resultado = defaultdict(list)

    for (
        olt,
        puerto,
    ), muestras in puertos.items():

        muestras.sort(key=lambda fila: fila["_time"])

        inicio_caida = None

        ultimo_estado_caido = None

        estado_caida = None

        for muestra in muestras:

            fecha = muestra.get("_time")

            estado = muestra.get("ESTADO")

            if fecha is None:
                continue

            try:
                estado = int(estado)

            except (
                TypeError,
                ValueError,
            ):
                continue

            # ==================================
            # CAÍDO
            # ==================================

            if estado != ESTADO_NORMAL:

                if inicio_caida is None:

                    inicio_caida = fecha

                    estado_caida = estado

                ultimo_estado_caido = fecha

                continue

            # ==================================
            # RECUPERADO
            # ==================================

            if estado == ESTADO_NORMAL and inicio_caida is not None:

                fin_caida = fecha

                duracion_minutos = (fin_caida - inicio_caida).total_seconds() / 60

                resultado[(olt, puerto)].append(
                    {
                        "inicio": inicio_caida,
                        "fin": fin_caida,
                        "duracion_minutos": round(
                            duracion_minutos,
                            2,
                        ),
                        "duracion_horas": round(
                            duracion_minutos / 60,
                            2,
                        ),
                        "dia": inicio_caida.strftime("%Y-%m-%d"),
                        "estado_detectado": estado_caida,
                        "mayor_2_horas": duracion_minutos >= 120,
                        "activa": False,
                    }
                )

                inicio_caida = None
                ultimo_estado_caido = None
                estado_caida = None

        # ======================================
        # SIGUE CAÍDO
        # ======================================

        if inicio_caida is not None:

            duracion_minutos = (ahora - inicio_caida).total_seconds() / 60

            resultado[(olt, puerto)].append(
                {
                    "inicio": inicio_caida,
                    "fin": None,
                    "ultima_muestra_caida": ultimo_estado_caido,
                    "duracion_minutos": round(
                        duracion_minutos,
                        2,
                    ),
                    "duracion_horas": round(
                        duracion_minutos / 60,
                        2,
                    ),
                    "dia": inicio_caida.strftime("%Y-%m-%d"),
                    "estado_detectado": estado_caida,
                    "mayor_2_horas": duracion_minutos >= 120,
                    "activa": True,
                }
            )

    return resultado


# ==========================================================
# CAÍDAS RECURRENTES / MAYORES DE 2 HORAS
# ==========================================================


def analizar_caidas(
    datos,
):
    """
    Un puerto se muestra si cumple:

    - 3 o más caídas en los últimos 7 días

    O

    - al menos una caída de 2 horas o más
    """

    caidas_por_puerto = reconstruir_caidas(datos)

    resultado_olts = defaultdict(list)

    for (
        olt,
        puerto,
    ), caidas in caidas_por_puerto.items():

        cantidad_caidas = len(caidas)

        caidas_mayores_2h = [
            caida for caida in caidas if caida["duracion_minutos"] >= 120
        ]

        cumple_por_cantidad = cantidad_caidas >= 3

        cumple_por_duracion = len(caidas_mayores_2h) > 0

        if not (cumple_por_cantidad or cumple_por_duracion):
            continue

        tiempo_total = sum(caida["duracion_minutos"] for caida in caidas)

        motivos = []

        if cumple_por_cantidad:

            motivos.append("3_o_mas_caidas")

        if cumple_por_duracion:

            motivos.append("caida_mayor_2_horas")

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "cantidad_caidas": cantidad_caidas,
                "caidas_mayores_2h": len(caidas_mayores_2h),
                "cumple_por_cantidad": cumple_por_cantidad,
                "cumple_por_duracion": cumple_por_duracion,
                "motivos": motivos,
                "tiempo_total_caido_minutos": round(
                    tiempo_total,
                    2,
                ),
                "tiempo_total_caido_horas": round(
                    tiempo_total / 60,
                    2,
                ),
                "caidas": caidas,
            }
        )

    resultado = []

    for olt in sorted(resultado_olts.keys()):

        puertos_olt = resultado_olts[olt]

        puertos_olt.sort(
            key=lambda item: (
                item["cantidad_caidas"],
                item["tiempo_total_caido_minutos"],
            ),
            reverse=True,
        )

        resultado.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos_olt),
                "puertos": puertos_olt,
            }
        )

    return resultado


def consultar_caidas():

    print()
    print("Consultando caídas " "de los últimos 7 días...")
    print()

    datos = consultar_flux_temp(CONSULTA_CAIDAS)

    resultado = analizar_caidas(datos)

    total_puertos = sum(olt["cantidad_puertos"] for olt in resultado)

    return {
        "consulta": "caidas_recurrentes",
        "periodo": "ultimos_7_dias",
        "criterio": ("3_o_mas_caidas_" "o_caida_mayor_2_horas"),
        "cantidad_olts": len(resultado),
        "cantidad_puertos": total_puertos,
        "datos": resultado,
    }


# ==========================================================
# CRC
# ==========================================================


def consultar_crc():

    print()
    print("Consultando errores CRC " "de las últimas 24 horas...")
    print()

    datos = consultar_flux_temp(CONSULTA_CRC)

    episodios = agrupar_eventos(
        datos,
        campo_valor="CRC_POR_SEGUNDO",
        minimo_muestras=1,
        separacion_minutos=SEPARACION_EPISODIO_MINUTOS,
    )

    resultado_olts = defaultdict(list)

    for (
        olt,
        puerto,
    ), eventos in episodios.items():

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "cantidad_episodios": len(eventos),
                "episodios": eventos,
            }
        )

    resultado = []

    for olt in sorted(resultado_olts.keys()):

        puertos = resultado_olts[olt]

        puertos.sort(
            key=lambda item: max(evento["maximo"] for evento in item["episodios"]),
            reverse=True,
        )

        resultado.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos),
                "puertos": puertos,
            }
        )

    return {
        "consulta": "errores_crc",
        "periodo": "ultimas_24_horas",
        "criterio": "mas_de_10_crc_por_segundo",
        "cantidad_olts": len(resultado),
        "datos": resultado,
    }


# ==========================================================
# CORRELACIÓN
# ==========================================================


def eventos_se_relacionan(
    evento_a,
    evento_b,
    margen_minutos=MARGEN_CORRELACION_MINUTOS,
):
    """
    Determina si dos eventos se cruzan
    o están separados por un margen
    máximo configurable.
    """

    margen_segundos = margen_minutos * 60

    inicio_a = evento_a["inicio"].timestamp()

    fin_a_valor = evento_a.get("fin")

    if fin_a_valor is None:
        fin_a_valor = datetime.now(timezone.utc)

    fin_a = fin_a_valor.timestamp()

    inicio_b = evento_b["inicio"].timestamp()

    fin_b_valor = evento_b.get("fin")

    if fin_b_valor is None:
        fin_b_valor = datetime.now(timezone.utc)

    fin_b = fin_b_valor.timestamp()

    return inicio_b <= (fin_a + margen_segundos) and fin_b >= (
        inicio_a - margen_segundos
    )


def consultar_correlacion():

    print()
    print("Analizando correlación " "Saturación + CRC + Caídas...")
    print()

    # ==========================================
    # CONSULTAS
    # ==========================================

    datos_saturacion = consultar_flux_temp(CONSULTA_SATURACION)

    datos_crc = consultar_flux_temp(CONSULTA_CRC)

    datos_caidas = consultar_flux_temp(CONSULTA_CAIDAS_CORRELACION)

    # ==========================================
    # EPISODIOS
    # ==========================================

    saturaciones = agrupar_eventos(
        datos_saturacion,
        campo_valor="SATURACION",
        minimo_muestras=MINIMO_MUESTRAS_SATURACION,
        separacion_minutos=SEPARACION_EPISODIO_MINUTOS,
    )

    crc = agrupar_eventos(
        datos_crc,
        campo_valor="CRC_POR_SEGUNDO",
        minimo_muestras=1,
        separacion_minutos=SEPARACION_EPISODIO_MINUTOS,
    )

    caidas = reconstruir_caidas(datos_caidas)

    claves = set()

    claves.update(saturaciones.keys())

    claves.update(crc.keys())

    claves.update(caidas.keys())

    resultado_olts = defaultdict(list)

    # ==========================================
    # CRUCE POR OLT + PUERTO
    # ==========================================

    for clave in claves:

        olt, puerto = clave

        eventos_sat = saturaciones.get(
            clave,
            [],
        )

        eventos_crc = crc.get(
            clave,
            [],
        )

        eventos_caida = caidas.get(
            clave,
            [],
        )

        correlaciones = []

        # ======================================
        # SATURACIÓN + CRC
        # ======================================

        for sat in eventos_sat:

            for evento_crc in eventos_crc:

                if eventos_se_relacionan(
                    sat,
                    evento_crc,
                ):

                    correlaciones.append(
                        {
                            "tipo": "SATURACION + CRC",
                            "saturacion": sat,
                            "crc": evento_crc,
                        }
                    )

        # ======================================
        # SATURACIÓN + CAÍDA
        # ======================================

        for sat in eventos_sat:

            for caida in eventos_caida:

                if eventos_se_relacionan(
                    sat,
                    caida,
                ):

                    correlaciones.append(
                        {
                            "tipo": "SATURACION + CAIDA",
                            "saturacion": sat,
                            "caida": caida,
                        }
                    )

        # ======================================
        # CRC + CAÍDA
        # ======================================

        for evento_crc in eventos_crc:

            for caida in eventos_caida:

                if eventos_se_relacionan(
                    evento_crc,
                    caida,
                ):

                    correlaciones.append(
                        {
                            "tipo": "CRC + CAIDA",
                            "crc": evento_crc,
                            "caida": caida,
                        }
                    )

        if not correlaciones:
            continue

        # ======================================
        # DIAGNÓSTICO GENERAL
        # ======================================

        tiene_sat = bool(eventos_sat)

        tiene_crc = bool(eventos_crc)

        tiene_caida = bool(eventos_caida)

        if tiene_sat and tiene_crc and tiene_caida:

            diagnostico = "SATURACION + CRC + CAIDA"

        elif tiene_sat and tiene_crc:

            diagnostico = "SATURACION + CRC"

        elif tiene_sat and tiene_caida:

            diagnostico = "SATURACION + CAIDA"

        elif tiene_crc and tiene_caida:

            diagnostico = "CRC + CAIDA"

        else:

            continue

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "diagnostico": diagnostico,
                "cantidad_correlaciones": len(correlaciones),
                "saturaciones": eventos_sat,
                "crc": eventos_crc,
                "caidas": eventos_caida,
                "correlaciones": correlaciones,
            }
        )

    # ==========================================
    # AGRUPAR POR OLT
    # ==========================================

    resultado = []

    for olt in sorted(resultado_olts.keys()):

        puertos = resultado_olts[olt]

        puertos.sort(
            key=lambda item: item["cantidad_correlaciones"],
            reverse=True,
        )

        resultado.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos),
                "puertos": puertos,
            }
        )

    total_puertos = sum(olt["cantidad_puertos"] for olt in resultado)

    return {
        "consulta": "correlacion_eventos",
        "periodo": "ultimas_24_horas",
        "margen_correlacion_minutos": MARGEN_CORRELACION_MINUTOS,
        "cantidad_olts": len(resultado),
        "cantidad_puertos": total_puertos,
        "datos": resultado,
    }


# ==========================================================
# IMPRIMIR RESULTADO
# ==========================================================


def imprimir_resultado(
    resultado,
):

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
            default=serializar,
        )
    )


# ==========================================================
# MENÚ
# ==========================================================


def mostrar_menu():

    print()
    print("=" * 55)

    print(" MONITOR OLT - CONSULTAS INFLUXDB")

    print("=" * 55)

    print("1. Saturación de puertos")

    print("2. Caídas recurrentes / mayores a 2 horas")

    print("3. Errores CRC mayores a 10/s")

    print("4. Correlación Saturación + CRC + Caídas")

    print("0. Salir")

    print("=" * 55)


# ==========================================================
# MAIN
# ==========================================================


def main() -> int:

    while True:

        mostrar_menu()

        opcion = input("Seleccione una opción: ").strip()

        try:

            # ==================================
            # SATURACIÓN
            # ==================================

            if opcion == "1":

                resultado = consultar_saturacion()

                imprimir_resultado(resultado)

            # ==================================
            # CAÍDAS
            # ==================================

            elif opcion == "2":

                resultado = consultar_caidas()

                imprimir_resultado(resultado)

            # ==================================
            # CRC
            # ==================================

            elif opcion == "3":

                resultado = consultar_crc()

                imprimir_resultado(resultado)

            # ==================================
            # CORRELACIÓN
            # ==================================

            elif opcion == "4":

                resultado = consultar_correlacion()

                imprimir_resultado(resultado)

            # ==================================
            # SALIR
            # ==================================

            elif opcion == "0":

                print("Saliendo...")

                return 0

            else:

                print("Opción no válida.")

        except Exception as exc:

            print(
                f"Error: {exc}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    raise SystemExit(main())
