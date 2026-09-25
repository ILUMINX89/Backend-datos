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
from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_snr_flux


def validar_consultas() -> None:
    assert "range(start: -4d)" in obtener_bw_flux()
    snr = obtener_snr_flux()
    assert "range(start: -4d)" in snr
    assert "tail(n: 60)" in snr


def validar_calculo() -> None:
    bloques: list[tuple[datetime, datetime]] = []
    consultas: list[str] = []

    def consulta_utilizacion(inicio: datetime, fin: datetime) -> str:
        bloques.append((inicio, fin))
        return "utilizacion"

    def consultar(consulta: str, **_kwargs: object) -> list[dict[str, object]]:
        consultas.append(consulta)
        if consulta == "bw":
            return [
                {"cmts": "CMTS-1", "descripcion": puerto, "_value": 100}
                for puerto in ("A", "B", "C")
            ]
        if consulta == "utilizacion" and consultas.count("utilizacion") == 1:
            return [
                {"cmts": "CMTS-1", "descripcion": puerto, "_value": valor}
                for puerto, valores in (("A", (95, 96, 96)), ("B", (99, 99)), ("C", (120,)))
                for valor in valores
            ]
        return []

    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "obtener_bw_flux", return_value="bw"))
        parches.enter_context(patch.object(service, "obtener_snr_flux", return_value="snr"))
        parches.enter_context(patch.object(service, "obtener_utilizacion_flux", side_effect=consulta_utilizacion))
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=consultar))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        datos = service.calcular_saturacion_actual()["datos"]

    assert len(bloques) == 16
    assert consultas == ["bw", *("utilizacion" for _ in range(16)), "snr"]
    assert all(fin - inicio == timedelta(hours=6) for inicio, fin in bloques)
    assert all(actual[1] == siguiente[0] for actual, siguiente in zip(bloques, bloques[1:]))
    assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)
    assert abs(datetime.now(timezone.utc) - bloques[-1][1]) < timedelta(minutes=1)

    puertos = datos[0]["puertos"]
    assert [puerto["puerto"] for puerto in puertos] == ["A", "B", "C"]
    assert [puerto["puntos_sobre_90"] for puerto in puertos] == [3, 2, 1]
    assert puertos[0]["valor"] == 95.67
    assert puertos[2]["valor"] == 100.0
    assert all(0 <= puerto["valor"] <= 100 for puerto in puertos)


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
