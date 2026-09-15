from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sys

# Compatibilidad con: python .\tests\test_microservicios_olt.py
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import pytest

from microservicios.app import app
from microservicios.olt.caidas.service import analizar_caidas, reconstruir_caidas
from microservicios.olt.caidas.queries import obtener_caidas_flux
from microservicios.olt.correlacion import service as correlacion_service
from microservicios.olt.crc.service import agrupar_episodios_crc
from microservicios.olt.crc.queries import obtener_crc_flux
from microservicios.olt.saturacion.service import agrupar_episodios_saturacion
from microservicios.olt.saturacion.queries import obtener_saturacion_flux


BASE = datetime(2026, 9, 15, tzinfo=timezone.utc)


def test_saturacion_separa_episodios_y_clasifica():
    datos = [
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE, "SATURACION": 75},
        {
            "OLT": "OLT-1",
            "PUERTO": "1/1",
            "_time": BASE + timedelta(minutes=5),
            "SATURACION": 85,
        },
        {
            "OLT": "OLT-1",
            "PUERTO": "1/1",
            "_time": BASE + timedelta(minutes=35),
            "SATURACION": 95,
        },
    ]

    episodios = agrupar_episodios_saturacion(datos)[("OLT-1", "1/1")]

    assert len(episodios) == 1
    assert episodios[0]["muestras"] == 2
    assert episodios[0]["maximo"] == 85
    assert episodios[0]["tipo"] == 2


def test_crc_separa_con_intervalo_de_30_minutos():
    datos = [
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE, "CRC_POR_SEGUNDO": 11},
        {
            "OLT": "OLT-1",
            "PUERTO": "1/1",
            "_time": BASE + timedelta(minutes=30),
            "CRC_POR_SEGUNDO": 20,
        },
    ]

    episodios = agrupar_episodios_crc(datos)[("OLT-1", "1/1")]

    assert len(episodios) == 2


def test_caidas_reconstruye_y_aplica_ambos_criterios():
    datos = [
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE, "ESTADO": 1},
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE + timedelta(minutes=30), "ESTADO": 6},
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE + timedelta(minutes=60), "ESTADO": 2},
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE + timedelta(minutes=180), "ESTADO": 6},
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE + timedelta(minutes=200), "ESTADO": 3},
        {"OLT": "OLT-1", "PUERTO": "1/1", "_time": BASE + timedelta(minutes=210), "ESTADO": 6},
    ]

    caidas = reconstruir_caidas(datos, ahora=BASE + timedelta(minutes=240))
    analisis = analizar_caidas(caidas)[0]["puertos"][0]

    assert analisis["cantidad_caidas"] == 3
    assert analisis["caidas_mayores_2h"] == 1
    assert analisis["cumple_por_cantidad"] is True
    assert analisis["cumple_por_duracion"] is True


def test_queries_conservan_secuencia_temporal():
    saturacion = obtener_saturacion_flux()
    crc = obtener_crc_flux()
    caidas = obtener_caidas_flux()

    assert "derivative(unit: 1s, nonNegative: true)" in saturacion
    assert "r._value * 8.0 / 1000.0" in saturacion
    assert "max(" not in saturacion
    assert "derivative(unit: 1s, nonNegative: true)" in crc
    assert "max(" not in crc
    assert "range(start: -7d)" in caidas


def test_correlacion_no_incluye_fenomeno_fuera_del_margen(monkeypatch):
    sat = {"inicio": BASE, "fin": BASE + timedelta(minutes=5)}
    crc = {
        "inicio": BASE + timedelta(minutes=12),
        "fin": BASE + timedelta(minutes=12),
    }
    caida = {
        "inicio": BASE + timedelta(hours=3),
        "fin": BASE + timedelta(hours=4),
    }
    clave = ("OLT-1", "1/1")
    monkeypatch.setattr(
        correlacion_service, "obtener_episodios_saturacion", lambda: {clave: [sat]}
    )
    monkeypatch.setattr(
        correlacion_service, "obtener_episodios_crc", lambda: {clave: [crc]}
    )
    monkeypatch.setattr(
        correlacion_service,
        "obtener_caidas_por_puerto",
        lambda _periodo: {clave: [caida]},
    )

    puerto = correlacion_service.obtener_correlacion()["datos"][0]["puertos"][0]

    assert puerto["diagnostico"] == "SATURACION + CRC"
    assert puerto["cantidad_correlaciones"] == 1


def test_aplicacion_publica_health_rutas_y_tags(monkeypatch):
    respuestas = {
        "saturacion": {"consulta": "saturacion"},
        "caidas": {"consulta": "caidas"},
        "crc": {"consulta": "crc"},
        "correlacion": {"consulta": "correlacion"},
    }
    modulos = {
        nombre: importlib.import_module(f"microservicios.olt.{nombre}.router")
        for nombre in respuestas
    }
    for nombre, modulo in modulos.items():
        monkeypatch.setattr(modulo, f"obtener_{nombre}", lambda n=nombre: respuestas[n])

    cliente = TestClient(app)
    assert cliente.get("/health").json() == {
        "ok": True,
        "service": "Backend Datos API",
    }

    for nombre in respuestas:
        respuesta = cliente.get(f"/api/olt/{nombre}")
        assert respuesta.status_code == 200
        assert respuesta.json() == {"ok": True, "data": respuestas[nombre]}

    esquema = cliente.get("/openapi.json").json()
    assert set(esquema["paths"]) >= {
        "/health",
        "/api/olt/saturacion",
        "/api/olt/caidas",
        "/api/olt/crc",
        "/api/olt/correlacion",
        "/alarmas",
    }
    tags = {
        operacion["tags"][0]
        for ruta in esquema["paths"].values()
        for operacion in ruta.values()
        if operacion.get("tags")
    }
    assert tags >= {
        "OLT - Saturación",
        "OLT - Caídas",
        "OLT - CRC",
        "OLT - Correlación",
    }


def test_error_interno_no_expone_detalles(monkeypatch):
    modulo = importlib.import_module("microservicios.olt.saturacion.router")

    def fallar():
        raise RuntimeError("secreto de infraestructura")

    monkeypatch.setattr(modulo, "obtener_saturacion", fallar)
    cliente = TestClient(app, raise_server_exceptions=False)
    respuesta = cliente.get("/api/olt/saturacion")

    assert respuesta.status_code == 500
    assert respuesta.json() == {"ok": False, "error": "Error interno del servicio"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
