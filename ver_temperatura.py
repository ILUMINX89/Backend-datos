from microservicios.config import settings
from microservicios.influx import consultar_flux_temp

consulta = f"""
import "influxdata/influxdb/schema"

schema.fieldKeys(
    bucket: "{settings.influx_temp_bucket}",
    start: -30d
)
"""

datos = consultar_flux_temp(consulta)

print("BUCKET:", settings.influx_temp_bucket)
print()

for fila in datos:
    campo = str(fila.get("_value", ""))

    if any(
        palabra in campo.lower()
        for palabra in (
            "temp",
            "temperature",
            "temperatura",
            "board",
            "cpu",
            "sensor",
        )
    ):
        print(fila)
