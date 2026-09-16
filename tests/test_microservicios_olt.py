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
from microservicios.olt.caidas import service as caidas_service
from microservicios.olt.caidas.service import analizar_caidas, reconstruir_caidas
from microservicios.olt.caidas.queries import obtener_caidas_flux
from microservicios.olt.correlacion import service as correlacion_service
from microservicios.olt.crc.service import agrupar_episodios_crc
from microservicios.olt.crc.queries import obtener_crc_flux
from microservicios.olt.saturacion.service import agrupar_episodios_saturacion
from microservicios.olt.saturacion.queries import obtener_saturacion_flux
from microservicios.olt.perdida_latencia import service as perdida_latencia_service
from microservicios.olt.perdida_latencia.queries import (
    obtener_latencia_actual_flux,
    obtener_latencia_equipo_flux,
)
from microservicios.olt.temperatura import service as temperatura_service


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


def test_caidas_actuales_limita_busquedas_historicas_a_cuatro_dias(monkeypatch):
    caidas_service._cache_ultima_actividad.clear()
    rangos = {}
    consultas = {
        "estado_actual": [],
        "ultima_muestra": [
            {
                "OLT": "OLT-1",
                "PUERTO": "1/1",
                "_time": BASE - timedelta(minutes=20),
                "TRAFICO": 0,
            }
        ],
        "ultima_actividad": [
            {
                "OLT": "OLT-1",
                "PUERTO": "1/1",
                "_time": BASE - timedelta(hours=1),
                "TRAFICO": 10,
            }
        ],
    }

    monkeypatch.setattr(
        caidas_service,
        "obtener_estado_actual_flux",
        lambda: "estado_actual",
    )

    def ultima_muestra(periodo):
        rangos["ultima_muestra"] = periodo
        return "ultima_muestra"

    def ultima_actividad(puertos, periodo):
        rangos["ultima_actividad"] = periodo
        assert puertos == [("OLT-1", "1/1")]
        return "ultima_actividad"

    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_muestra_conocida_flux",
        ultima_muestra,
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_actividad_flux",
        ultima_actividad,
    )
    monkeypatch.setattr(
        caidas_service,
        "consultar_flux_temp",
        lambda consulta: consultas[consulta],
    )

    resultado = caidas_service.obtener_caidas_actuales()

    assert rangos == {
        "ultima_muestra": "-4d",
        "ultima_actividad": "-4d",
    }
    assert resultado["criterios"]["busqueda_ultima_actividad"] == (
        "ultimos_4_dias"
    )


def test_ultima_actividad_reutiliza_cache_y_expira_a_los_cinco_minutos(
    monkeypatch,
):
    caidas_service._cache_ultima_actividad.clear()
    clave = ("OLT-1", "1/1")
    reloj = {"ahora": 0.0}
    consultas = []

    monkeypatch.setattr(
        caidas_service,
        "monotonic",
        lambda: reloj["ahora"],
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_actividad_flux",
        lambda puertos, periodo: consultas.append((puertos, periodo)) or "flux",
    )
    monkeypatch.setattr(
        caidas_service,
        "consultar_flux_temp",
        lambda _consulta: [
            {
                "OLT": clave[0],
                "PUERTO": clave[1],
                "_time": BASE,
                "TRAFICO": 10,
            }
        ],
    )

    primera = caidas_service._buscar_ultima_actividad([clave])
    reloj["ahora"] = 30.0
    segunda = caidas_service._buscar_ultima_actividad([clave])

    assert primera == segunda
    assert consultas == [([clave], "-4d")]

    reloj["ahora"] = 301.0
    caidas_service._buscar_ultima_actividad([clave])

    assert consultas == [([clave], "-4d"), ([clave], "-4d")]


def test_ultima_actividad_cachea_ausencia_solo_diez_segundos(monkeypatch):
    caidas_service._cache_ultima_actividad.clear()
    clave = ("OLT-1", "1/1")
    reloj = {"ahora": 0.0}
    cantidad_consultas = 0

    monkeypatch.setattr(
        caidas_service,
        "monotonic",
        lambda: reloj["ahora"],
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_actividad_flux",
        lambda _puertos, _periodo: "flux",
    )

    def consultar(_consulta):
        nonlocal cantidad_consultas
        cantidad_consultas += 1
        return []

    monkeypatch.setattr(caidas_service, "consultar_flux_temp", consultar)

    assert caidas_service._buscar_ultima_actividad([clave]) == {}
    reloj["ahora"] = 5.0
    assert caidas_service._buscar_ultima_actividad([clave]) == {}
    assert cantidad_consultas == 1

    reloj["ahora"] = 11.0
    assert caidas_service._buscar_ultima_actividad([clave]) == {}
    assert cantidad_consultas == 2


def test_puerto_recien_caido_reintenta_historial_sin_esperar_300_segundos(
    monkeypatch,
):
    caidas_service._cache_ultima_actividad.clear()
    clave = ("OLT-1", "1/1")
    reloj = {"ahora": 0.0}
    respuestas_historial = [
        [],
        [
            {
                "OLT": clave[0],
                "PUERTO": clave[1],
                "_time": BASE,
                "TRAFICO": 10,
            }
        ],
    ]

    monkeypatch.setattr(
        caidas_service,
        "monotonic",
        lambda: reloj["ahora"],
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_estado_actual_flux",
        lambda: "estado_actual",
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_muestra_conocida_flux",
        lambda _periodo: "ultima_muestra",
    )
    monkeypatch.setattr(
        caidas_service,
        "obtener_ultima_actividad_flux",
        lambda _puertos, _periodo: "ultima_actividad",
    )

    def consultar(consulta):
        if consulta == "estado_actual":
            return [
                {
                    "OLT": clave[0],
                    "PUERTO": clave[1],
                    "_time": BASE + timedelta(hours=1),
                    "TRAFICO": 0,
                }
            ]
        if consulta == "ultima_muestra":
            return []
        return respuestas_historial.pop(0)

    monkeypatch.setattr(caidas_service, "consultar_flux_temp", consultar)

    primera = caidas_service.obtener_caidas_actuales()
    assert primera["datos"][0]["puertos"][0]["estado"] == "CAIDO_SIN_FECHA"

    reloj["ahora"] = 11.0
    segunda = caidas_service.obtener_caidas_actuales()
    assert segunda["datos"][0]["puertos"][0]["estado"] == "CAIDO_ACTUAL"


def test_ultima_actividad_invalida_cache_cuando_el_puerto_se_recupera():
    caidas_service._cache_ultima_actividad.clear()
    clave = ("OLT-1", "1/1")
    caidas_service._cache_ultima_actividad[clave] = (
        float("inf"),
        {"fecha": BASE, "trafico": 10},
    )

    caidas_service._invalidar_cache_ultima_actividad([clave])

    assert clave not in caidas_service._cache_ultima_actividad


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


def test_consulta_perdida_latencia_usa_fuente_confirmada():
    actual = obtener_latencia_actual_flux()
    historica = obtener_latencia_equipo_flux("AAC-BOG.CENTRO_ONNET-H1")

    assert 'r._measurement == "ping_monitor"' in actual
    assert 'r._field == "latency"' in actual
    assert 'r._field == "packet_loss"' in actual
    assert "range(start: -10m)" in actual
    assert 'r.equipo == "AAC-BOG.CENTRO_ONNET-H1"' in historica


def test_servicio_perdida_latencia_compacta_por_equipo(monkeypatch):
    monkeypatch.setattr(
        perdida_latencia_service,
        "consultar_flux_temp",
        lambda _query, **_kwargs: [
            {"equipo": "OLT-1", "_field": "latency", "_value": 50, "_time": BASE},
            {"equipo": "OLT-1", "_field": "packet_loss", "_value": 10},
            {"equipo": "OLT-2", "_field": "latency", "_value": 85},
            {"equipo": "OLT-2", "_field": "packet_loss", "_value": 24},
            {"equipo": "OLT-3", "_field": "packet_loss", "_value": 100},
            {"equipo": "OLT-3", "_field": "latency", "_value": 90},
            {"equipo": "OLT-4", "_field": "packet_loss", "_value": 51},
            {"equipo": "OLT-4", "_field": "latency", "_value": 91},
            {"equipo": "OLT-5", "_field": "latency", "_value": 65},
            {"equipo": "OLT-6", "_field": "packet_loss", "_value": 24},
            {"equipo": "OLT-7", "_field": "latency", "_value": float("nan")},
            {"equipo": "equipo no valido", "_field": "latency", "_value": 2},
        ],
    )

    resultado = perdida_latencia_service.obtener_perdida_latencia_actual()

    assert resultado["cantidad"] == 5
    assert resultado["datos"] == [
        {
            "equipo": "OLT-2",
            "valor": 24.0,
            "unidad": "%",
            "estado": "Pérdida + Latencia",
            "nivel": "neutral",
            "valor_secundario": 85.0,
            "unidad_secundaria": "ms",
        },
        {
            "equipo": "OLT-3",
            "valor": 100.0,
            "unidad": "%",
            "estado": "Pérdida + Latencia",
            "nivel": "rojo",
            "valor_secundario": 90.0,
            "unidad_secundaria": "ms",
        },
        {
            "equipo": "OLT-4",
            "valor": 51.0,
            "unidad": "%",
            "estado": "Pérdida + Latencia",
            "nivel": "neutral",
            "valor_secundario": 91.0,
            "unidad_secundaria": "ms",
        },
        {
            "equipo": "OLT-5",
            "valor": 65.0,
            "unidad": "ms",
            "estado": "Latencia",
            "nivel": "neutral",
        },
        {
            "equipo": "OLT-6",
            "valor": 24.0,
            "unidad": "%",
            "estado": "Pérdida",
            "nivel": "neutral",
        },
    ]
    assert len({fila["equipo"] for fila in resultado["datos"]}) == resultado["cantidad"]


def test_temperatura_agrupa_por_olt_y_usa_maxima(monkeypatch):
    monkeypatch.setattr(
        temperatura_service,
        "consultar_flux_temp",
        lambda _query: [
            {"OLT": "OLT-1", "TARJETA": "A", "TEMPERATURA": 72},
            {"OLT": "OLT-1", "TARJETA": "B", "TEMPERATURA": 81},
            {"OLT": "OLT-1", "TARJETA": "C", "TEMPERATURA": 76},
            {"OLT": "OLT-2", "TARJETA": "A", "TEMPERATURA": 69},
        ],
    )

    resultado = temperatura_service.obtener_temperatura_actual()

    assert resultado["cantidad"] == 1
    assert resultado["datos"] == [
        {
            "olt": "OLT-1",
            "temperatura": 81.0,
            "estado": "Alta",
            "nivel": "naranja",
        }
    ]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
