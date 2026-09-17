import csv
import os
import sys

import urllib3
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# ============================================================
# CARGAR .ENV
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL = os.getenv("CMTS_INFLUX_URL")
ORG = os.getenv("CMTS_INFLUX_ORG", "Claro")
TOKEN = os.getenv("CMTS_INFLUX_TOKEN")
BUCKET = os.getenv("CMTS_INFLUX_BUCKET", "CMTS")

VERIFY_SSL = os.getenv("CMTS_INFLUX_VERIFY_SSL", "false").strip().lower() in (
    "true",
    "1",
    "yes",
    "si",
)

TIMEOUT_MS = int(os.getenv("CMTS_INFLUX_TIMEOUT_MS", "120000"))


# ============================================================
# ESTRUCTURA DEL BUCKET
# ============================================================

MEASUREMENT = "estado_puertos"

# Campo que usamos únicamente para obtener una serie
# representativa por cada combinación de tags.
FIELD = "cm_registrados"

# Como buscamos el inventario actual, tomamos información
# reciente.
RANGO = "-1h"


# ============================================================
# VALIDACIONES
# ============================================================

if not URL:
    print("ERROR: Falta CMTS_INFLUX_URL en el .env")
    sys.exit(1)

if not TOKEN:
    print("ERROR: Falta CMTS_INFLUX_TOKEN en el .env")
    sys.exit(1)

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# NORMALIZACIÓN
# ============================================================


def normalizar_descripcion(descripcion):
    """
    Normaliza únicamente:
    - espacios al inicio/final
    - espacios múltiples
    - mayúsculas/minúsculas

    NO elimina:
    - SEG A
    - SEG B
    - números
    - contenido entre paréntesis

    Ejemplo:

    " NODO ABC   (CENTRO 1) "
        ->
    "NODO ABC (CENTRO 1)"
    """

    if descripcion is None:
        return ""

    return " ".join(str(descripcion).strip().upper().split())


# ============================================================
# CONSULTA INFLUX
# ============================================================


def consultar_datos(query_api):

    flux = f"""
from(bucket: "{BUCKET}")
    |> range(start: {RANGO})
    |> filter(
        fn: (r) =>
            r._measurement == "{MEASUREMENT}"
            and r._field == "{FIELD}"
    )
    |> filter(
        fn: (r) =>
            exists r.cmts
            and exists r.puerto
            and exists r.descripcion
    )
    |> group(
        columns: [
            "cmts",
            "puerto",
            "descripcion"
        ]
    )
    |> last()
    |> keep(
        columns: [
            "_time",
            "cmts",
            "puerto",
            "cmts_puerto",
            "descripcion"
        ]
    )
"""

    print("Ejecutando consulta en InfluxDB...")
    print()

    try:

        tablas = query_api.query(query=flux, org=ORG)

        return tablas

    except Exception as error:

        print("ERROR consultando InfluxDB:")
        print(error)

        sys.exit(1)


# ============================================================
# OBTENER NODOS
# ============================================================


def procesar_nodos(tablas):

    # estructura:
    #
    # {
    #   "NODO ABC (CENTRO)": {
    #       ("CMTS1", "1/0"),
    #       ("CMTS2", "2/1")
    #   }
    # }

    nodos = {}

    registros_leidos = 0
    registros_nodo = 0
    ignorados = 0

    for tabla in tablas:

        for registro in tabla.records:

            registros_leidos += 1

            valores = registro.values

            descripcion_original = valores.get("descripcion") or ""

            descripcion = normalizar_descripcion(descripcion_original)

            # Solo queremos nodos reales.
            # Excluye cosas como:
            #
            # PUERTO LIBRE
            # PUERTO AVERIADO
            # IPV6
            # SONDA DWH
            # CM MINTIC
            #
            if not descripcion.startswith("NODO "):
                ignorados += 1
                continue

            cmts = str(valores.get("cmts") or "SIN_CMTS").strip()

            puerto = str(valores.get("puerto") or "SIN_PUERTO").strip()

            registros_nodo += 1

            if descripcion not in nodos:

                nodos[descripcion] = {
                    "descripcion_original": (str(descripcion_original).strip()),
                    "ubicaciones": set(),
                }

            # Lo importante para detectar duplicado
            # es una ubicación distinta.
            #
            # Si Influx tiene 500 registros históricos del
            # mismo nodo en el mismo CMTS/puerto, sigue siendo
            # UNA sola ubicación.
            nodos[descripcion]["ubicaciones"].add((cmts, puerto))

    return (nodos, registros_leidos, registros_nodo, ignorados)


# ============================================================
# DETECTAR DUPLICADOS
# ============================================================


def obtener_duplicados(nodos):

    duplicados = {}

    for nombre_nodo, datos in nodos.items():

        ubicaciones = datos["ubicaciones"]

        # Duplicado:
        #
        # MISMO nombre completo del nodo
        # +
        # más de una ubicación CMTS/puerto
        if len(ubicaciones) > 1:

            duplicados[nombre_nodo] = datos

    return duplicados


# ============================================================
# EXPORTAR CSV
# ============================================================


def exportar_csv(duplicados):

    nombre_archivo = "nodos_duplicados_cmts.csv"

    with open(nombre_archivo, "w", newline="", encoding="utf-8-sig") as archivo:

        writer = csv.writer(archivo, delimiter=";")

        writer.writerow(["NODO", "CMTS", "PUERTO", "CANTIDAD_UBICACIONES"])

        for nombre_nodo in sorted(duplicados.keys()):

            datos = duplicados[nombre_nodo]

            ubicaciones = sorted(datos["ubicaciones"])

            cantidad = len(ubicaciones)

            for cmts, puerto in ubicaciones:

                writer.writerow([nombre_nodo, cmts, puerto, cantidad])

    return nombre_archivo


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 80)
    print("ANÁLISIS DE NODOS - BUCKET CMTS")
    print("=" * 80)

    print(f"URL         : {URL}")
    print(f"ORG         : {ORG}")
    print(f"BUCKET      : {BUCKET}")
    print(f"MEASUREMENT : {MEASUREMENT}")
    print(f"RANGO       : {RANGO}")

    print("TOKEN       : " + ("CARGADO" if TOKEN else "NO CARGADO"))

    print()

    # ========================================================
    # CLIENTE
    # ========================================================

    client = InfluxDBClient(
        url=URL, token=TOKEN, org=ORG, verify_ssl=VERIFY_SSL, timeout=TIMEOUT_MS
    )

    try:

        query_api = client.query_api()

        # ====================================================
        # CONSULTAR
        # ====================================================

        tablas = consultar_datos(query_api)

        print("Consulta terminada.")

        print()

        # ====================================================
        # PROCESAR
        # ====================================================

        nodos, registros_leidos, registros_nodo, ignorados = procesar_nodos(tablas)

        # ====================================================
        # DUPLICADOS
        # ====================================================

        duplicados = obtener_duplicados(nodos)

        total_nodos_unicos = len(nodos)

        total_nodos_duplicados = len(duplicados)

        total_no_duplicados = total_nodos_unicos - total_nodos_duplicados

        # Cantidad física de asociaciones
        # nodo + CMTS + puerto
        total_ubicaciones = sum(len(datos["ubicaciones"]) for datos in nodos.values())

        # ====================================================
        # RESUMEN
        # ====================================================

        print("=" * 80)
        print("RESULTADO")
        print("=" * 80)

        print(f"Registros leídos         : " f"{registros_leidos}")

        print(f"Registros de nodos       : " f"{registros_nodo}")

        print(f"Registros ignorados      : " f"{ignorados}")

        print()

        print(f"Total nombres de nodo    : " f"{total_nodos_unicos}")

        print(f"Total ubicaciones        : " f"{total_ubicaciones}")

        print(f"Nodos duplicados         : " f"{total_nodos_duplicados}")

        print(f"Nodos no duplicados      : " f"{total_no_duplicados}")

        # ====================================================
        # MOSTRAR DUPLICADOS
        # ====================================================

        print()
        print("=" * 80)
        print("NODOS DUPLICADOS")
        print("=" * 80)

        if not duplicados:

            print()
            print("No se encontraron " "nodos duplicados.")

        else:

            for nombre_nodo in sorted(duplicados.keys()):

                datos = duplicados[nombre_nodo]

                ubicaciones = sorted(datos["ubicaciones"])

                print()

                print(f"{nombre_nodo}")

                print(f"Ubicaciones: " f"{len(ubicaciones)}")

                for numero, (cmts, puerto) in enumerate(ubicaciones, start=1):

                    print(f"  {numero}. " f"CMTS: {cmts} " f"| PUERTO: {puerto}")

        # ====================================================
        # CSV
        # ====================================================

        print()

        if duplicados:

            archivo_csv = exportar_csv(duplicados)

            print("=" * 80)

            print(f"CSV generado: " f"{archivo_csv}")

            print("=" * 80)

    finally:

        client.close()


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    main()
