"""Consultas interactivas a InfluxDB para tráfico OLT."""

import json
import sys

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from influx import consultar_flux_temp

# ==========================================================
# CONSULTA 1
# SATURACIÓN
# ==========================================================

CONSULTA_SATURACION = """
from(bucket: "trafico_temperatura_olts")

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

  |> map(fn: (r) => ({
      r with
      _value: r._value * 8.0 / 1000.0
  }))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({
      r with
      SATURACION:
        if r.INPUT > r.OUTPUT then
          (r.INPUT / 10000000.0) * 100.0
        else
          (r.OUTPUT / 10000000.0) * 100.0
  }))

  |> filter(fn: (r) =>
      r.SATURACION > 70.0
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> max(
      column: "SATURACION"
  )

  |> group(columns: [])

  |> sort(
      columns: ["SATURACION"],
      desc: true
  )
"""


# ==========================================================
# CONSULTA 2
# HISTÓRICO DE ESTADO - ÚLTIMOS 7 DÍAS
# ==========================================================

CONSULTA_CAIDAS = """
from(bucket: "trafico_temperatura_olts")

  |> range(start: -2d)

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
      columns: {
          _value: "ESTADO"
      }
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
###ERRORES CRC
###Consulta


CONSULTA_CRC = """
from(bucket: "trafico_temperatura_olts")

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
      columns: {
          _value: "CRC_POR_SEGUNDO"
      }
  )

  |> filter(fn: (r) =>
      r.CRC_POR_SEGUNDO > 10.0
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> max(
      column: "CRC_POR_SEGUNDO"
  )

  |> group(columns: [])

  |> sort(
      columns: ["CRC_POR_SEGUNDO"],
      desc: true
  )
"""


def serializar(valor: Any) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()

    return str(valor)


# ==========================================================
# SATURACIÓN
# ==========================================================


def consultar_saturacion():
    print()
    print("Consultando saturación de puertos...")
    print()

    datos = consultar_flux_temp(CONSULTA_SATURACION)

    return {
        "consulta": "saturacion",
        "cantidad": len(datos),
        "datos": datos,
    }


# ==========================================================
# CAÍDAS
# ==========================================================


def analizar_caidas(datos):
    """
    Reconstruye episodios de caída.

    Reglas:
    - ESTADO == 6  -> puerto normal
    - ESTADO != 6  -> puerto caído/anómalo

    Un puerto se incluye si:
    - tuvo 3 o más caídas en los últimos 7 días
    O
    - tuvo al menos una caída de 2 horas o más
    """

    puertos = defaultdict(list)

    # ==========================================
    # AGRUPAR MUESTRAS POR OLT Y PUERTO
    # ==========================================

    for fila in datos:
        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        if not olt or not puerto:
            continue

        puertos[(olt, puerto)].append(fila)

    ahora = datetime.now(timezone.utc)

    resultado_olts = defaultdict(list)

    # ==========================================
    # ANALIZAR CADA PUERTO
    # ==========================================

    for (
        olt,
        puerto,
    ), muestras in puertos.items():

        muestras.sort(key=lambda fila: fila["_time"])

        caidas = []

        inicio_caida = None
        ultimo_estado_caido = None
        estado_caida = None

        # ======================================
        # RECORRER HISTÓRICO DE ESTADOS
        # ======================================

        for muestra in muestras:

            fecha = muestra.get("_time")

            estado = muestra.get("ESTADO")

            try:
                estado = int(estado)

            except (
                TypeError,
                ValueError,
            ):
                continue

            # ==================================
            # ESTADO ANÓMALO
            # ==================================

            if estado != 6:

                # Si todavía no había una caída
                # abierta, inicia una nueva.
                if inicio_caida is None:
                    inicio_caida = fecha
                    estado_caida = estado

                ultimo_estado_caido = fecha

                continue

            # ==================================
            # RECUPERACIÓN
            # ==================================

            if estado == 6 and inicio_caida is not None:

                fin_caida = fecha

                duracion_segundos = (fin_caida - inicio_caida).total_seconds()

                duracion_minutos = round(
                    duracion_segundos / 60,
                    2,
                )

                caidas.append(
                    {
                        "inicio": inicio_caida,
                        "fin": fin_caida,
                        "duracion_minutos": duracion_minutos,
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

                # Cerramos el episodio
                inicio_caida = None
                ultimo_estado_caido = None
                estado_caida = None

        # ======================================
        # SI EL PUERTO SIGUE CAÍDO
        # ======================================

        if inicio_caida is not None:

            duracion_segundos = (ahora - inicio_caida).total_seconds()

            duracion_minutos = round(
                duracion_segundos / 60,
                2,
            )

            caidas.append(
                {
                    "inicio": inicio_caida,
                    "fin": None,
                    "ultima_muestra_caida": ultimo_estado_caido,
                    "duracion_minutos": duracion_minutos,
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

        # ======================================
        # CRITERIOS
        # ======================================

        cantidad_caidas = len(caidas)

        caidas_mayores_2h = [
            caida for caida in caidas if caida["duracion_minutos"] >= 120
        ]

        cumple_por_cantidad = cantidad_caidas >= 3

        cumple_por_duracion = len(caidas_mayores_2h) > 0

        # Si no cumple ninguno,
        # no lo agregamos al resultado.
        if not (cumple_por_cantidad or cumple_por_duracion):
            continue

        # ======================================
        # TOTALES DEL PUERTO
        # ======================================

        tiempo_total = sum(caida["duracion_minutos"] for caida in caidas)

        tiempo_total_horas = round(
            tiempo_total / 60,
            2,
        )

        # ======================================
        # MOTIVO DE INCLUSIÓN
        # ======================================

        motivos = []

        if cumple_por_cantidad:
            motivos.append("3_o_mas_caidas")

        if cumple_por_duracion:
            motivos.append("caida_mayor_2_horas")

        # ======================================
        # AGREGAR PUERTO A SU OLT
        # ======================================

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
                "tiempo_total_caido_horas": tiempo_total_horas,
                "caidas": caidas,
            }
        )


###
###ERRORES CRC


def consultar_crc():
    print()
    print("Consultando errores CRC " "de las últimas 24 horas...")
    print()

    datos = consultar_flux_temp(CONSULTA_CRC)

    return {
        "consulta": "errores_crc",
        "periodo": "ultimas_24_horas",
        "criterio": "mas_de_10_crc_por_segundo",
        "cantidad": len(datos),
        "datos": datos,
    }

    # ==========================================
    # FORMATO FINAL AGRUPADO POR OLT
    # ==========================================

    resultado = []

    for olt in sorted(resultado_olts.keys()):

        puertos_olt = resultado_olts[olt]

        # Primero los puertos con más caídas.
        # Si empatan, los de mayor tiempo caído.
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
        "criterio": "3_o_mas_caidas",
        "cantidad_olts": len(resultado),
        "cantidad_puertos": total_puertos,
        "datos": resultado,
    }


# ==========================================================
# IMPRIMIR JSON
# ==========================================================


def imprimir_resultado(resultado):

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
    print("=" * 48)

    print(" MONITOR OLT - CONSULTAS INFLUXDB")

    print("=" * 48)

    print("1. Saturación de puertos")

    print("2. Caídas recurrentes de puertos")

    print("3. Errores CRC mayores a 10/s")

    print("0. Salir")

    print("=" * 48)


def main() -> int:

    while True:

        mostrar_menu()

        opcion = input("Seleccione una opción: ").strip()

        try:

            if opcion == "1":

                resultado = consultar_saturacion()

                imprimir_resultado(resultado)

            elif opcion == "2":

                resultado = consultar_caidas()

                imprimir_resultado(resultado)

            elif opcion == "3":
                resultado = consultar_crc()
                imprimir_resultado(resultado)

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
