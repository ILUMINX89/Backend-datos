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
    flujo = obtener_muestras_flux(ahora - timedelta(hours=4), ahora)
    assert 'r._field == "bw" or r._field == "utilizacion"' in flujo
    assert 'exists r.cmts and exists r.puerto and exists r.descripcion' in flujo
    assert 'keep(columns: ["_time", "_field", "_value", "cmts", "puerto", "descripcion"])' in flujo
    for operacion in ("pivot(", "join(", "group(", "max(", "last(", '"portadoras"'):
        assert operacion not in flujo


def validar_calculo() -> None:
    bloques: list[tuple[datetime, datetime]] = []
    consultas: list[str] = []
    fecha = datetime(2026, 9, 20, tzinfo=timezone.utc)
    filas: list[dict[str, object]] = []

    def agregar(puerto: str, descripcion: str, indice: int, bw: float, uso: float) -> None:
        instante = fecha + timedelta(seconds=indice)
        for campo, valor in (("bw", bw), ("utilizacion", uso)):
            filas.append({
                "cmts": "CMTS-1", "puerto": puerto, "descripcion": descripcion,
                "_field": campo, "_value": valor, "_time": instante,
            })

    # 99 puntos: excluido. El segundo puerto con igual descripción no se suma.
    for indice in range(99):
        agregar("1/0", "NODO A", indice, 100, 95)
    for indice in range(99):
        agregar("1/1", "NODO A", indice, 200, 190)

    # 100 puntos: incluido; BW cambia en cada lectura.
    for indice in range(100):
        bw = 100 if indice % 2 == 0 else 200
        agregar("2/0", "NODO B", indice, bw, bw * 0.95)

    # 120 críticos, 30 no críticos. Incluye el umbral exacto y ambos límites.
    for indice in range(120):
        agregar("3/0", "NODO C", indice, 100, 80 if indice < 60 else 200)
    for indice in range(30):
        agregar("3/0", "NODO C", indice + 120, 100, -10 if indice == 0 else 70)

    # Una lectura sin pareja y otra con BW cero no cuentan.
    filas.append({
        "cmts": "CMTS-1", "puerto": "2/0", "descripcion": "NODO B",
        "_field": "utilizacion", "_value": 95, "_time": fecha + timedelta(seconds=200),
    })
    agregar("2/0", "NODO B", 201, 0, 95)

    def consulta_bloque(inicio: datetime, fin: datetime) -> str:
        bloques.append((inicio, fin))
        return f"bloque-{len(bloques)}"

    def consultar(consulta: str, **_kwargs: object) -> list[dict[str, object]]:
        consultas.append(consulta)
        return filas if consulta == "bloque-1" else []

    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "obtener_muestras_flux", side_effect=consulta_bloque))
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=consultar))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        datos = service.calcular_saturacion_actual()["datos"]

    assert len(bloques) == 24
    assert consultas == [f"bloque-{numero}" for numero in range(1, 25)]
    assert all(fin - inicio == timedelta(hours=4) for inicio, fin in bloques)
    assert all(actual[1] == siguiente[0] for actual, siguiente in zip(bloques, bloques[1:]))
    assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)

    assert len(datos) == 1
    puertos = datos[0]["puertos"]
    assert [puerto["puerto"] for puerto in puertos] == ["NODO C", "NODO B"]
    assert [puerto["puntos_sobre_80"] for puerto in puertos] == [120, 100]
    assert [puerto["muestras_analizadas"] for puerto in puertos] == [150, 100]
    assert [puerto["valor"] for puerto in puertos] == [90.0, 95.0]
    assert [puerto["puerto_fisico"] for puerto in puertos] == ["3/0", "2/0"]
    assert [puerto["tipo"] for puerto in puertos] == ["uso", "uso"]
    assert all(0 <= puerto["valor"] <= 100 for puerto in puertos)


def validar_fuentes() -> None:
    fecha = datetime.now(timezone.utc)
    base = {"cmts": "CMTS-1", "puerto": "1/0", "descripcion": "A", "_time": fecha}
    bw = {**base, "_field": "bw", "_value": 100}
    uso = {**base, "_field": "utilizacion", "_value": 95}
    for filas, mensaje in (
        ([uso], "No se obtuvieron datos BW CMTS"),
        ([bw], "No se obtuvieron muestras de utilización CMTS"),
        ([bw, {**uso, "_time": fecha + timedelta(seconds=1)}], "No se pudieron emparejar BW y utilización CMTS"),
    ):
        with ExitStack() as parches:
            parches.enter_context(patch.object(service, "obtener_muestras_flux", return_value="bloque"))
            parches.enter_context(patch.object(service, "consultar_flux_temp", return_value=filas))
            parches.enter_context(patch.object(service.time, "sleep", return_value=None))
            try:
                service.calcular_saturacion_actual()
            except RuntimeError as error:
                assert str(error) == mensaje
            else:
                raise AssertionError(f"Debió fallar: {mensaje}")


def validar_cache_y_rutas(directorio: Path) -> None:
    anterior = {"generado_en": "2026-09-18T00:00:00+00:00", "ventana": "4d", "datos": [{"cmts": "CMTS-1"}]}
    estado = {"estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None}
    with ExitStack() as parches:
        parches.enter_context(patch.object(cache, "ARCHIVO_SATURACION", directorio / "hfc_saturacion.json"))
        parches.enter_context(patch.object(cache, "ARCHIVO_ESTADO", directorio / "hfc_estado.json"))
        cache.guardar_saturacion(anterior)
        cache.guardar_estado(estado)

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
    validar_calculo()
    validar_fuentes()
    with TemporaryDirectory() as temporal:
        validar_cache_y_rutas(Path(temporal))
    print("Validación CMTS saturación: OK")


if __name__ == "__main__":
    main()
