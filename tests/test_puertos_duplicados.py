from fastapi.testclient import TestClient

from microservicios.app import app
from microservicios.cmts.puertos_duplicados import router as duplicados_router
from microservicios.cmts.puertos_duplicados.queries import (
    obtener_puertos_duplicados_flux,
)
from microservicios.cmts.puertos_duplicados.service import (
    normalizar_descripcion,
    procesar_puertos_duplicados,
)


def test_normalizacion_conserva_el_nombre_completo():
    assert (
        normalizar_descripcion("  Nodo centro 01   (seg a) ")
        == "NODO CENTRO 01 (SEG A)"
    )


def test_detecta_ubicaciones_distintas_y_descarta_descripciones_no_nodo():
    filas = [
        {"descripcion": " Nodo centro 01 ", "cmts": "CMTS-02", "puerto": "2/0/1"},
        {"descripcion": "NODO   CENTRO 01", "cmts": "CMTS-01", "puerto": "1/0/0"},
        {"descripcion": "NODO CENTRO 01", "cmts": "CMTS-01", "puerto": "1/0/0"},
        {"descripcion": "PUERTO LIBRE", "cmts": "CMTS-03", "puerto": "3/0/0"},
        {"descripcion": "NODO UNICO", "cmts": "CMTS-04", "puerto": "4/0/0"},
    ]

    assert procesar_puertos_duplicados(filas) == [
        {
            "nodo": "NODO CENTRO 01",
            "cantidad_ubicaciones": 2,
            "ubicaciones": [
                {"cmts": "CMTS-01", "puerto": "1/0/0"},
                {"cmts": "CMTS-02", "puerto": "2/0/1"},
            ],
        }
    ]


def test_consulta_usa_la_fuente_y_ventana_requeridas():
    consulta = obtener_puertos_duplicados_flux()

    assert "range(start: -1h)" in consulta
    assert 'r._measurement == "estado_puertos"' in consulta
    assert 'r._field == "cm_registrados"' in consulta
    assert '["cmts", "puerto", "descripcion"]' in consulta


def test_endpoint_devuelve_el_contrato_esperado(monkeypatch):
    monkeypatch.setattr(
        duplicados_router,
        "obtener_puertos_duplicados_actuales",
        lambda: {"cantidad_nodos_duplicados": 0, "datos": []},
    )

    response = TestClient(app).get("/api/cmts/puertos-duplicados/actual")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {"cantidad_nodos_duplicados": 0, "datos": []},
    }
