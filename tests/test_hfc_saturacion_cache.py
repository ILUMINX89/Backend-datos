from datetime import datetime, timezone

from fastapi.testclient import TestClient

from microservicios.app import app
from microservicios.cmts.saturacion import cache, service
from microservicios.cmts.saturacion.queries import obtener_snr_flux, obtener_utilizacion_flux


BASE = datetime(2026, 9, 18, tzinfo=timezone.utc)


def test_flux_agrega_cuatro_dias_y_snr_limita_sesenta():
    utilizacion = obtener_utilizacion_flux()
    assert utilizacion.count("range(start: -4d)") == 2
    assert "puntos_sobre_90" in utilizacion
    assert "reduce(" in utilizacion
    assert "limit(n:" not in utilizacion
    assert "range(start: -4d)" in obtener_snr_flux()
    assert "limit(n: 60)" in obtener_snr_flux()


def test_calculo_usa_agregados_y_ordena_por_criticidad(monkeypatch):
    agregados = [
        {"cmts": "CMTS-1", "descripcion": "NODO B", "bw": 100,
         "muestras_analizadas": 4, "puntos_sobre_90": 2,
         "promedio_sobre_90": 97, "promedio_total": 56},
        {"cmts": "CMTS-1", "descripcion": "NODO A", "bw": 100,
         "muestras_analizadas": 4, "puntos_sobre_90": 3,
         "promedio_sobre_90": 95.666, "promedio_total": 81},
    ]
    monkeypatch.setattr(service, "obtener_utilizacion_flux", lambda: "utilizacion")
    monkeypatch.setattr(service, "obtener_snr_flux", lambda: "snr")
    monkeypatch.setattr(
        service, "consultar_flux_temp",
        lambda consulta, **_kwargs: agregados if consulta == "utilizacion" else [],
    )
    puertos = service.calcular_saturacion_actual()["datos"][0]["puertos"]
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
    estado = cliente.get("/api/cmts/saturacion/estado")
    assert actual.status_code == 200
    assert actual.json()["data"]["ventana"] == "4d"
    assert estado.status_code == 200
    assert estado.json()["data"]["estado"] == "listo"


def test_fallo_de_calculo_no_sobrescribe_el_ultimo_cache(monkeypatch, tmp_path):
    ruta = tmp_path / "hfc_saturacion.json"
    monkeypatch.setattr(cache, "ARCHIVO_SATURACION", ruta)
    anterior = {"generado_en": BASE.isoformat(), "ventana": "4d", "datos": [{"cmts": "CMTS-1"}]}
    cache.guardar_saturacion(anterior)
    monkeypatch.setattr(
        service, "calcular_saturacion_actual",
        lambda: (_ for _ in ()).throw(RuntimeError("Influx no disponible")),
    )

    try:
        service.actualizar_saturacion()
    except RuntimeError:
        pass

    assert cache.leer_saturacion() == anterior
