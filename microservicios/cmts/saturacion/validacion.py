"""Validacion manual y local de la saturacion CMTS.

Ejecutar con: python -m microservicios.cmts.saturacion.validacion
"""

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
    assert 'r._field == "portadoras" or r._field == "utilizacion"' in flujo
    assert 'keep(columns: ["_time", "_field", "_value", "cmts", "descripcion"])' in flujo
    assert all(operacion not in flujo for operacion in ("join(", "group(", "max(", "last(", '"bw"'))


def validar_calculo() -> None:
    bloques: list[tuple[datetime, datetime]] = []
    consultas: list[str] = []
    antiguo = datetime(2026, 9, 20, tzinfo=timezone.utc)
    reciente = datetime(2026, 9, 21, tzinfo=timezone.utc)

    def consulta_bloque(inicio: datetime, fin: datetime) -> str:
        bloques.append((inicio, fin))
        return f"bloque-{len(bloques)}"

    def consultar(consulta: str, **_kwargs: object) -> list[dict[str, object]]:
        consultas.append(consulta)
        if consulta != "bloque-1":
            return []
        filas: list[dict[str, object]] = []
        for puerto, actual, normal, cantidad, porcentaje in (
            ("A", 10, 10, 99, 95),
            ("B", 10, 10, 100, 90),
            ("C", 7, 10, 100, 65),
            ("D", 7, 10, 99, 65),
            ("E", 8, 10, 100, 89),
        ):
            for valor, fecha in ((actual, reciente), (normal, antiguo)):
                filas.append({"cmts": "CMTS-1", "descripcion": puerto,
                              "_field": "portadoras", "_value": valor, "_time": fecha})
            filas.extend({"cmts": "CMTS-1", "descripcion": puerto,
                         "_field": "utilizacion", "_value": porcentaje / 100 * normal * 30_000_000}
                        for _ in range(cantidad))
        return filas

    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "obtener_muestras_flux", side_effect=consulta_bloque))
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=consultar))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        datos = service.calcular_saturacion_actual()["datos"]

    assert len(bloques) == 24
    assert consultas == [f"bloque-{n}" for n in range(1, 25)]
    assert all(fin - inicio == timedelta(hours=4) for inicio, fin in bloques)
    assert all(actual[1] == siguiente[0] for actual, siguiente in zip(bloques, bloques[1:]))
    assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)
    assert abs(datetime.now(timezone.utc) - bloques[-1][1]) < timedelta(minutes=1)

    puertos = datos[0]["puertos"]
    assert [puerto["puerto"] for puerto in puertos] == ["B", "C"]
    assert [puerto["puntos_sobre_90"] for puerto in puertos] == [100, 100]
    assert [puerto["valor"] for puerto in puertos] == [90.0, 65.0]
    assert [puerto["tipo"] for puerto in puertos] == ["uso", "degradacion"]
    assert [puerto["estado"] for puerto in puertos] == ["Saturación", "Saturación por degradación"]
    assert [puerto["bw"] for puerto in puertos] == [300_000_000, 210_000_000]


def validar_cache_y_rutas(directorio: Path) -> None:
    anterior = {
        "generado_en": "2026-09-18T00:00:00+00:00",
        "ventana": "4d",
        "datos": [{"cmts": "CMTS-1"}],
    }
    estado = {"estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None}

    with ExitStack() as parches:
        parches.enter_context(patch.object(cache, "ARCHIVO_SATURACION", directorio / "hfc_saturacion.json"))
        parches.enter_context(patch.object(cache, "ARCHIVO_ESTADO", directorio / "hfc_estado.json"))
        cache.guardar_saturacion(anterior)
        cache.guardar_estado(estado)

        with patch.object(router, "actualizar_saturacion", side_effect=AssertionError("Calculo inesperado")):
            with TestClient(app) as cliente:
                actual = cliente.get("/api/cmts/saturacion/actual")
                estado_http = cliente.get("/api/cmts/saturacion/estado")
            assert actual.status_code == 200
            assert actual.json() == {"ok": True, "data": anterior}
            assert estado_http.status_code == 200
            assert estado_http.json() == {"ok": True, "data": estado}

        with patch.object(service, "calcular_saturacion_actual", side_effect=RuntimeError("Influx no disponible")):
            try:
                service.actualizar_saturacion()
            except RuntimeError as error:
                assert str(error) == "Influx no disponible"
            else:
                raise AssertionError("El fallo del calculo debio propagarse")
        assert cache.leer_saturacion() == anterior


def main() -> None:
    validar_consultas()
    validar_calculo()
    with TemporaryDirectory() as temporal:
        validar_cache_y_rutas(Path(temporal))
    print("Validación CMTS saturación: OK")


if __name__ == "__main__":
    main()
