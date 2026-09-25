from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from microservicios.app import app
from microservicios.cmts.saturacion import cache, service
from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_snr_flux, obtener_utilizacion_flux


BASE = datetime(2026, 9, 18, tzinfo=timezone.utc)


def test_flux_agrega_cuatro_dias_y_snr_limita_sesenta():
    utilizacion = obtener_utilizacion_flux(BASE, BASE.replace(hour=6))
    assert "range(start: time(v:" in utilizacion
    assert "join(" not in utilizacion
    assert "reduce(" not in utilizacion
    assert "|> keep(columns: [\"_value\", \"cmts\", \"descripcion\"])" in utilizacion
    assert "range(start: -4d)" in obtener_bw_flux()
    assert "|> last()" in obtener_bw_flux()
    assert "range(start: -4d)" in obtener_snr_flux()
    assert "tail(n: 60)" in obtener_snr_flux()
    assert "sort(" not in obtener_snr_flux()


def test_calculo_usa_agregados_y_ordena_por_criticidad(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "obtener_bw_flux", lambda: "bw")
    monkeypatch.setattr(service, "obtener_utilizacion_flux", lambda _inicio, _fin: "utilizacion")
    monkeypatch.setattr(service, "obtener_snr_flux", lambda: "snr")
    monkeypatch.setattr(service.time, "sleep", lambda _seconds: None)

    def consultar(consulta, **_kwargs):
        calls.append(consulta)
        if consulta == "bw":
            return [
                {"cmts": "CMTS-1", "descripcion": "NODO A", "_value": 100},
                {"cmts": "CMTS-1", "descripcion": "NODO B", "_value": 100},
            ]
        if consulta == "utilizacion" and calls.count("utilizacion") == 1:
            return [
                {"cmts": "CMTS-1", "descripcion": "NODO A", "_value": value}
                for value in (95, 96, 96)
            ] + [
                {"cmts": "CMTS-1", "descripcion": "NODO B", "_value": value}
                for value in (97, 97)
            ]
        return []

    monkeypatch.setattr(
        service, "consultar_flux_temp", consultar,
    )
    puertos = service.calcular_saturacion_actual()["datos"][0]["puertos"]
    assert calls == ["bw"] + ["utilizacion"] * 16 + ["snr"]
    assert [puerto["puerto"] for puerto in puertos] == ["NODO A", "NODO B"]
    assert puertos[0]["puntos_sobre_90"] == 3
    assert puertos[0]["valor"] == 95.67


def test_get_actual_y_estado_solo_leen_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "ARCHIVO_SATURACION", tmp_path / "hfc_saturacion.json")
    monkeypatch.setattr(cache, "ARCHIVO_ESTADO", tmp_path / "hfc_estado.json")
    cache.guardar_saturacion({"generado_en": BASE.isoformat(), "ventana": "4d", "datos": []})
    cache.guardar_estado({"estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None})

    cliente = TestClient(app)
    actual = cliente.get("/api/cmts/saturacion/actual")
    actual_con_refresh = cliente.get("/api/cmts/saturacion/actual?refresh=1")
    estado = cliente.get("/api/cmts/saturacion/estado")
    assert actual.status_code == 200
    assert actual.json()["data"]["ventana"] == "4d"
    assert actual_con_refresh.json()["data"]["ventana"] == "4d"
    assert estado.status_code == 200
    assert estado.json()["data"]["estado"] == "listo"


def test_fallo_de_calculo_no_sobrescribe_el_ultimo_cache(monkeypatch, tmp_path):
    ruta = tmp_path / "hfc_saturacion.json"
    monkeypatch.setattr(cache, "ARCHIVO_SATURACION", ruta)
    anterior = {"generado_en": BASE.isoformat(), "ventana": "4d", "datos": [{"cmts": "CMTS-1"}]}
    cache.guardar_saturacion(anterior)
    monkeypatch.setattr(service, "obtener_bw_flux", lambda: "bw")
    monkeypatch.setattr(service, "obtener_utilizacion_flux", lambda _inicio, _fin: "utilizacion")
    monkeypatch.setattr(service.time, "sleep", lambda _seconds: None)
    calls = 0

    def consultar(consulta, **_kwargs):
        nonlocal calls
        if consulta == "bw":
            return [{"cmts": "CMTS-1", "descripcion": "NODO A", "_value": 100}]
        calls += 1
        if calls == 2:
            raise RuntimeError("Influx no disponible")
        return [{"cmts": "CMTS-1", "descripcion": "NODO A", "_value": 95}]

    monkeypatch.setattr(service, "consultar_flux_temp", consultar)
    with pytest.raises(RuntimeError, match="Influx no disponible"):
        service.actualizar_saturacion()

    assert calls == 2
    assert cache.leer_saturacion() == anterior
