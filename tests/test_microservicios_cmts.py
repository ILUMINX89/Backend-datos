from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Compatibilidad con: python .\tests\test_microservicios_cmts.py
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from microservicios.cmts.saturacion import service as saturacion_service
from microservicios.cmts.saturacion.queries import (
    obtener_bw_flux,
    obtener_snr_flux,
    obtener_utilizacion_flux,
)
from microservicios.cmts.intermitencias.queries import obtener_intermitencias_flux
from microservicios.cmts.intermitencias.service import analizar_intermitencias
from fastapi.testclient import TestClient
from microservicios.app import app


BASE = datetime(2026, 9, 18, tzinfo=timezone.utc)


def test_consulta_intermitencias_limita_la_ventana_a_siete_dias():
    consulta = obtener_intermitencias_flux()

    assert "range(start: -7d)" in consulta


def test_intermitencias_filtra_deduplica_y_ordena_por_cantidad():
    filas = [
        # Una intermitencia: no aparece aunque tenga muestras repetidas.
        {"cmts": "CMTS-1", "descripcion": "PUERTO-1", "evento": "A", "_time": BASE},
        {"cmts": "CMTS-1", "descripcion": "PUERTO-1", "evento": "A", "_time": BASE},
        # Dos intermitencias: aparece.
        {"cmts": "CMTS-1", "descripcion": "PUERTO-2", "evento": "A", "_time": BASE},
        {"cmts": "CMTS-1", "descripcion": "PUERTO-2", "evento": "B", "_time": BASE},
        # Tres intermitencias: aparece primero.
        {"cmts": "CMTS-2", "descripcion": "PUERTO-3", "evento": "A", "_time": BASE},
        {"cmts": "CMTS-2", "descripcion": "PUERTO-3", "evento": "B", "_time": BASE},
        {"cmts": "CMTS-2", "descripcion": "PUERTO-3", "evento": "C", "_time": BASE},
        # Un segundo evento fuera de la ventana no completa el minimo.
        {"cmts": "CMTS-3", "descripcion": "PUERTO-4", "evento": "A", "_time": BASE},
        {
            "cmts": "CMTS-3",
            "descripcion": "PUERTO-4",
            "evento": "B",
            "_time": BASE - timedelta(days=7, seconds=1),
        },
    ]

    resultado = analizar_intermitencias(
        filas,
        campo_evento="evento",
        ahora=BASE,
    )

    assert [(item["puerto"], item["cantidad_intermitencias"]) for item in resultado] == [
        ("PUERTO-3", 3),
        ("PUERTO-2", 2),
    ]


def test_puertos_docsis_actual_responde_con_lista():
    response = TestClient(app).get("/api/cmts/puertos-docsis/actual")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["data"]["datos"], list)


def test_intermitencias_actual_responde_con_lista():
    response = TestClient(app).get("/api/cmts/intermitencias/actual")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["data"]["datos"], list)


def test_consulta_utilizacion_lee_todos_los_puntos_de_la_ventana():
    utilizacion = obtener_utilizacion_flux()

    assert "range(start: -30m)" in utilizacion
    assert "limit(n:" not in utilizacion
    assert "limit(n: 1)" in obtener_bw_flux()
    assert "limit(n: 3)" in obtener_snr_flux()


def test_criticidad_prioriza_cantidad_de_puntos_sobre_90(monkeypatch):
    monkeypatch.setattr(saturacion_service, "obtener_bw_flux", lambda: "bw")
    monkeypatch.setattr(
        saturacion_service,
        "obtener_utilizacion_flux",
        lambda: "utilizacion",
    )
    monkeypatch.setattr(saturacion_service, "obtener_snr_flux", lambda: "snr")

    datos = {
        "bw": [
            {"cmts": "CMTS-1", "descripcion": "NODO A", "_value": 100, "_time": BASE},
            {"cmts": "CMTS-1", "descripcion": "NODO B", "_value": 100, "_time": BASE},
        ],
        "utilizacion": [
            {
                "cmts": "CMTS-1",
                "descripcion": "NODO A",
                "_value": valor,
                "_time": BASE - timedelta(minutes=indice),
            }
            for indice, valor in enumerate([90, 85, 82, 70])
        ]
        + [
            {
                "cmts": "CMTS-1",
                "descripcion": "NODO B",
                "_value": valor,
                "_time": BASE - timedelta(minutes=indice),
            }
            for indice, valor in enumerate([99, 95, 20, 10])
        ],
        "snr": [],
    }

    monkeypatch.setattr(
        saturacion_service,
        "consultar_flux_temp",
        lambda consulta, **_kwargs: datos[consulta],
    )

    resultado = saturacion_service.obtener_saturacion_actual()
    puertos = resultado["datos"][0]["puertos"]

    assert [puerto["puerto"] for puerto in puertos] == ["NODO A", "NODO B"]
    assert puertos[0]["puntos_sobre_90"] == 3
    assert puertos[0]["valor"] == 85.67
    assert puertos[1]["puntos_sobre_90"] == 2
    assert puertos[1]["valor"] == 97.0


def test_porcentaje_de_utilizacion_nunca_supera_100(monkeypatch):
    monkeypatch.setattr(saturacion_service, "obtener_bw_flux", lambda: "bw")
    monkeypatch.setattr(
        saturacion_service,
        "obtener_utilizacion_flux",
        lambda: "utilizacion",
    )
    monkeypatch.setattr(saturacion_service, "obtener_snr_flux", lambda: "snr")

    datos = {
        "bw": [
            {
                "cmts": "CMTS-1",
                "descripcion": "NODO A",
                "_value": 80,
                "_time": BASE,
            }
        ],
        "utilizacion": [
            {
                "cmts": "CMTS-1",
                "descripcion": "NODO A",
                "_value": 100,
                "_time": BASE,
            },
            {
                "cmts": "CMTS-1",
                "descripcion": "NODO A",
                "_value": 96,
                "_time": BASE - timedelta(minutes=1),
            },
        ],
        "snr": [],
    }

    monkeypatch.setattr(
        saturacion_service,
        "consultar_flux_temp",
        lambda consulta, **_kwargs: datos[consulta],
    )

    puerto = saturacion_service.obtener_saturacion_actual()["datos"][0]["puertos"][0]

    assert puerto["puntos_sobre_90"] == 2
    assert puerto["valor"] == 100.0
