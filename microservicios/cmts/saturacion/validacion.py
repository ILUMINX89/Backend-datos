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
from microservicios.cmts.saturacion.queries import obtener_bw_flux


def validar_consultas() -> None:
    bw = obtener_bw_flux()
    assert "range(start: -4d)" in bw
    assert 'keep(columns: ["_time", "_value", "cmts", "descripcion"])' in bw
    assert all(operacion not in bw for operacion in ("join(", "group(", "max(", "last("))


def validar_calculo() -> None:
    bloques: list[tuple[datetime, datetime]] = []
    consultas: list[str] = []

    def consulta_utilizacion(inicio: datetime, fin: datetime) -> str:
        bloques.append((inicio, fin))
        return "utilizacion"

    def consultar(consulta: str, **_kwargs: object) -> list[dict[str, object]]:
        consultas.append(consulta)
        if consulta == "bw":
            antiguo = datetime(2026, 9, 20, tzinfo=timezone.utc)
            reciente = datetime(2026, 9, 21, tzinfo=timezone.utc)
            return [
                {"cmts": "CMTS-1", "descripcion": puerto, "_value": valor, "_time": fecha}
                for puerto in ("A", "B", "C", "D", "E")
                for valor, fecha in ((80 if puerto == "C" else 79 if puerto in ("D", "E") else 100, reciente),
                                     (100, antiguo))
            ]
        if consulta == "utilizacion" and consultas.count("utilizacion") == 1:
            return [
                {"cmts": "CMTS-1", "descripcion": puerto, "_value": valor}
                for puerto, cantidad, valor in (("A", 99, 95), ("B", 100, 96),
                                                ("C", 100, 76), ("D", 100, 55.3),
                                                ("E", 99, 55.3))
                for _ in range(cantidad)
            ]
        return []

    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "obtener_bw_flux", return_value="bw"))
        parches.enter_context(patch.object(service, "obtener_utilizacion_flux", side_effect=consulta_utilizacion))
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=consultar))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        datos = service.calcular_saturacion_actual()["datos"]

    assert len(bloques) == 16
    assert consultas == ["bw", *("utilizacion" for _ in range(16))]
    assert all(fin - inicio == timedelta(hours=6) for inicio, fin in bloques)
    assert all(actual[1] == siguiente[0] for actual, siguiente in zip(bloques, bloques[1:]))
    assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)
    assert abs(datetime.now(timezone.utc) - bloques[-1][1]) < timedelta(minutes=1)

    puertos = datos[0]["puertos"]
    assert [puerto["puerto"] for puerto in puertos] == ["B", "C", "D"]
    assert [puerto["puntos_sobre_90"] for puerto in puertos] == [100, 100, 100]
    assert [puerto["valor"] for puerto in puertos] == [96.0, 95.0, 70.0]
    assert [puerto["bw"] for puerto in puertos] == [100, 80, 79]
    assert [puerto["tipo"] for puerto in puertos] == ["uso", "uso", "degradacion"]
    assert puertos[2]["estado"] == "Saturación por degradación"
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
