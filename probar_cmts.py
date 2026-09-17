import os
from pathlib import Path

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)


url = os.getenv("INFLUX_CMTS_URL")
org = os.getenv("INFLUX_CMTS_ORG")
token = os.getenv("INFLUX_CMTS_TOKEN")
bucket = os.getenv("INFLUX_CMTS_BUCKET")
timeout_ms = int(os.getenv("INFLUX_CMTS_TIMEOUT_MS", "60000"))


print("URL:", url)
print("ORG:", org)
print("BUCKET:", bucket)
print("TOKEN cargado:", bool(token))
print("TIMEOUT:", timeout_ms, "ms")


if not url:
    raise RuntimeError("Falta INFLUX_CMTS_URL")

if not org:
    raise RuntimeError("Falta INFLUX_CMTS_ORG")

if not token:
    raise RuntimeError("Falta INFLUX_CMTS_TOKEN")

if not bucket:
    raise RuntimeError("Falta INFLUX_CMTS_BUCKET")


query_bw = f"""
from(bucket: "{bucket}")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "bw")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> last()
  |> keep(columns: [
      "_time",
      "_value",
      "cmts",
      "descripcion"
  ])
"""


query_utilizacion = f"""
from(bucket: "{bucket}")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "utilizacion")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> last()
  |> keep(columns: [
      "_time",
      "_value",
      "cmts",
      "descripcion"
  ])
"""


with InfluxDBClient(
    url=url,
    token=token,
    org=org,
    verify_ssl=False,
    timeout=timeout_ms,
) as client:

    query_api = client.query_api()

    print("\nConsultando BW...")

    tablas_bw = query_api.query(query=query_bw, org=org)

    print("Consultando utilización...")

    tablas_utilizacion = query_api.query(query=query_utilizacion, org=org)

    datos_bw = {}

    for tabla in tablas_bw:
        for registro in tabla.records:

            cmts = registro.values.get("cmts")
            descripcion = registro.values.get("descripcion")
            bw = registro.get_value()

            clave = (cmts, descripcion)

            datos_bw[clave] = {
                "bw": bw,
                "time_bw": registro.get_time(),
            }

    datos_utilizacion = {}

    for tabla in tablas_utilizacion:
        for registro in tabla.records:

            cmts = registro.values.get("cmts")
            descripcion = registro.values.get("descripcion")
            utilizacion = registro.get_value()

            clave = (cmts, descripcion)

            datos_utilizacion[clave] = {
                "utilizacion": utilizacion,
                "time_utilizacion": registro.get_time(),
            }

    saturados = []

    for clave, datos in datos_bw.items():

        if clave not in datos_utilizacion:
            continue

        cmts, descripcion = clave

        bw = datos["bw"]
        utilizacion = datos_utilizacion[clave]["utilizacion"]

        if bw is None or utilizacion is None:
            continue

        if bw <= 0:
            continue

        porcentaje = (float(utilizacion) / float(bw)) * 100.0

        # SOLO MAYORES A 80 %
        if porcentaje <= 80.0:
            continue

        saturados.append(
            {
                "cmts": cmts,
                "descripcion": descripcion,
                "bw": bw,
                "utilizacion": utilizacion,
                "porcentaje": porcentaje,
            }
        )

    saturados.sort(key=lambda x: x["porcentaje"], reverse=True)

    print("\n=== PUERTOS SOBRE 80% ===\n")

    for puerto in saturados:

        print(
            {
                "cmts": puerto["cmts"],
                "descripcion": puerto["descripcion"],
                "bw": puerto["bw"],
                "utilizacion": puerto["utilizacion"],
                "porcentaje": round(puerto["porcentaje"], 2),
            }
        )

    print("\nTotal de puertos por encima del 80%:", len(saturados))
