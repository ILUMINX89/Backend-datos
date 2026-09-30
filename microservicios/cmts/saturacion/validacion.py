"""Validación manual: python -m microservicios.cmts.saturacion.validacion."""

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from microservicios.app import app
from microservicios.cmts.saturacion import cache, router, service
from microservicios.cmts.saturacion.queries import obtener_muestras_flux


def validar_consultas() -> None:
    ahora = datetime.now(timezone.utc)
    for campos in (("bw", "portadoras"), ("bw", "utilizacion"), ("snr",)):
        flujo = obtener_muestras_flux(ahora - timedelta(hours=1), ahora, campos)
        for campo in ("bw", "portadoras", "utilizacion", "snr"):
            assert (f'r._field == "{campo}"' in flujo) == (campo in campos)
        for operacion in ("pivot(", "join(", "group("):
            assert operacion not in flujo


def ejecutar(filas, distribuido=False):
    llamadas = []
    def query(inicio, fin, campos):
        llamadas.append((inicio, fin, campos))
        return (len(llamadas) - 1) % 96, campos
    def stream(consulta, **kwargs):
        bloque, campos = consulta
        for indice, fila in enumerate(filas):
            destino = int((fila["_time"] - FECHA).total_seconds()) % 96 if distribuido else 0
            if destino == bloque and fila["_field"] in campos:
                yield fila
    with patch.object(service, "obtener_muestras_flux", side_effect=query), patch.object(service, "iterar_flux_temp", side_effect=stream):
        datos = service.calcular_saturacion_actual()["datos"]
    assert len(llamadas) == 288
    for pasada in range(3):
        bloques = llamadas[pasada * 96:(pasada + 1) * 96]
        assert all(fin - inicio == timedelta(hours=1) for inicio, fin, _ in bloques)
        assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)
        assert all(a[1] == b[0] for a, b in zip(bloques, bloques[1:]))
    return {p["puerto_fisico"]: p for grupo in datos for p in grupo["puertos"]}


FECHA = datetime(2026, 9, 20, tzinfo=timezone.utc)


def validar_reglas():
    filas = []
    def agregar(puerto, campo, valores):
        for indice, valor in enumerate(valores):
            filas.append({"cmts": "CMTS-1", "puerto": puerto, "descripcion": "MISMO NODO",
                "_time": FECHA + timedelta(seconds=indice), "_field": campo, "_value": valor})
    for puerto, bws, usos, portadoras in (
        ("caida", [120,120,50,50,50,50], [70,75,48,49,47,48], [4,4,2,2,2,2]),
        ("normal", [120], [110], [4]),
        ("81_mbps", [120], [81], [4]),
        ("sin_saturacion", [50], [20], [4]),
        ("historico", [50,50,120], [48,49,70], []),
        ("aislado", [50], [48], []),
        ("umbral_uso", [120], [96], [4]),
        ("umbral_capacidad", [96], [90], [4]),
        ("invalido", [0, float("nan"), -1], [99,99,99], [4]),
    ):
        agregar(puerto, "bw", bws); agregar(puerto, "utilizacion", usos); agregar(puerto, "portadoras", portadoras)
    agregar("snr59", "snr", [29] * 59 + [30,35,None,"NaN"])
    agregar("snr60", "snr", [29] * 60)
    agregar("normal", "snr", [29] * 60)
    agregar("sin_bw", "utilizacion", [99])
    # Igual descripcion nunca debe mezclar lecturas entre puertos ni timestamps.
    agregar("desfasado", "bw", [100])
    filas.append({"cmts":"CMTS-1", "puerto":"desfasado", "descripcion":"MISMO NODO",
                  "_time": FECHA + timedelta(seconds=1), "_field":"utilizacion", "_value":95})
    datos = ejecutar(filas)
    assert datos == ejecutar(filas, True)
    assert "81_mbps" not in datos and "umbral_uso" not in datos
    assert "snr59" not in datos and "invalido" not in datos and "sin_bw" not in datos and "desfasado" not in datos
    caida = datos["caida"]
    assert caida["estado"] == "Saturación por degradación" and caida["tipo"] == "degradacion"
    assert caida["max_portadoras_historicas"] == 4 and caida["capacidad_normal"] == 120
    assert caida["bw"] == 50 and caida["puntos_saturacion_degradada"] == 4
    assert caida["muestras_capacidad_degradada"] == 4 and caida["valor"] == 96
    assert datos["normal"]["tipo"] == "uso" and datos["normal"]["estado"] == "Saturación"
    assert datos["normal"]["valor"] == 91.67 and datos["normal"]["degradacion_snr"]
    assert datos["sin_saturacion"]["estado"] == "Degradación" and datos["sin_saturacion"]["puntos_sobre_80"] == 0
    assert datos["snr60"]["ruido"] == 29 and datos["snr60"]["degradacion_snr"]
    assert datos["historico"]["capacidad_normal"] == 120 and datos["historico"]["tipo"] == "degradacion"
    assert datos["aislado"]["tipo"] == "uso" and datos["umbral_capacidad"]["tipo"] == "uso"
    assert "lecturas_capacidad" not in Path(service.__file__).read_text(encoding="utf-8")


def validar_streaming():
    from types import SimpleNamespace
    from microservicios import influx
    from influxdb_client.client.exceptions import InfluxDBError
    with patch.object(influx, "crear_cliente_cmts") as crear:
        api = crear.return_value.__enter__.return_value.query_api.return_value
        api.query_stream.return_value = iter([SimpleNamespace(values={"result":"x", "table":1, "_value":7})])
        assert list(influx.iterar_flux_temp("consulta", fuente="cmts")) == [{"_value":7}]
        api.query.assert_not_called()
        api.query_stream.assert_called_once()
        api.query_stream.side_effect = InfluxDBError(message="fallo")
        try:
            list(influx.iterar_flux_temp("consulta", fuente="cmts"))
        except RuntimeError:
            pass
        else:
            raise AssertionError("Streaming debe propagar errores")


def validar_cache_y_rutas(directorio: Path) -> None:
    anterior = {"generado_en": "2026-09-18T00:00:00+00:00", "ventana": "4d", "datos": [{"cmts": "CMTS-1"}]}
    estado = {"estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None}
    with ExitStack() as parches:
        parches.enter_context(patch.object(cache, "ARCHIVO_SATURACION", directorio / "hfc_saturacion.json"))
        parches.enter_context(patch.object(cache, "ARCHIVO_ESTADO", directorio / "hfc_estado.json"))
        cache.guardar_saturacion(anterior)
        cache.guardar_estado(estado)

        with patch.object(service, "iterar_flux_temp", side_effect=AssertionError("GET no debe consultar Influx")):
            assert router.saturacion_actual() == {"ok": True, "data": anterior}
            assert router.saturacion_estado()["data"] == estado

        with TestClient(app) as cliente:
            actual = cliente.get("/api/cmts/saturacion/actual")
            assert actual.status_code == 200
            assert actual.json() == {"ok": True, "data": anterior}
            respuesta = cliente.get("/api/cmts/saturacion/estado")
            assert respuesta.status_code == 200
            assert respuesta.json()["data"]["estado"] == "listo"
            assert respuesta.json()["data"]["error"] is None

        with patch.object(service, "calcular_saturacion_actual", side_effect=RuntimeError("Influx no disponible")):
            try:
                service.actualizar_saturacion()
            except RuntimeError:
                pass
            else:
                raise AssertionError("Debió fallar sin cambiar el cache")
        assert cache.leer_saturacion() == anterior

        with ExitStack() as fallos:
            fallos.enter_context(patch.object(service, "iterar_flux_temp", side_effect=[[], TimeoutError("timeout")]))
            with TestClient(app) as cliente:
                assert cliente.post("/api/cmts/saturacion/actualizar").status_code == 200
                estado_error = cliente.get("/api/cmts/saturacion/estado").json()["data"]
                assert estado_error["estado"] == "error"
                assert estado_error["error"] == "timeout"
                assert cliente.get("/api/cmts/saturacion/actual").json()["data"] == anterior

        # TestClient ejecuta tareas de fondo antes de devolver la respuesta.
        with patch.object(router, "actualizar_saturacion", return_value=anterior) as actualizar:
            with TestClient(app) as cliente:
                respuesta = cliente.post("/api/cmts/saturacion/actualizar")
                assert respuesta.status_code == 200
                assert respuesta.json() == {"ok": True, "estado": "procesando"}
                estado_final = cliente.get("/api/cmts/saturacion/estado").json()["data"]
                assert estado_final["estado"] == "listo"
                assert estado_final["error"] is None
                assert cliente.get("/api/cmts/saturacion/actual").json()["data"] == anterior
            actualizar.assert_called_once()


def main() -> None:
    validar_consultas()
    validar_reglas()
    validar_streaming()
    with TemporaryDirectory() as temporal:
        validar_cache_y_rutas(Path(temporal))
    print("Validación CMTS saturación: OK (negocio, 288 bloques, streaming, caché y rutas)")


if __name__ == "__main__":
    main()
