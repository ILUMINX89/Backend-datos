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
    assert 'r._field == "snr"' in flujo
    assert 'r._field == "portadoras"' in flujo
    for operacion in ("pivot(", "join(", "group(", "max(", "last("):
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

    # Puertos con igual descripcion se evaluan por separado.
    for indice in range(99):
        agregar("1/0", "NODO A", indice, 100, 95)
    for indice in range(99):
        agregar("1/1", "NODO A", indice, 200, 190)

    # Cada lectura usa su BW; el maximo historico detecta caidas.
    for indice in range(100):
        bw = 100 if indice % 2 == 0 else 200
        agregar("2/0", "NODO B", indice, bw, bw * 0.95)

    # El umbral exacto no cuenta; los valores superiores a 100 se limitan.
    for indice in range(120):
        agregar("3/0", "NODO C", indice, 100, 80 if indice < 60 else 200)
    for indice in range(30):
        agregar("3/0", "NODO C", indice + 120, 100, -10 if indice == 0 else 70)

    # Lecturas sin BW correspondiente o con BW cero no cuentan.
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
    assert [puerto["puerto_fisico"] for puerto in puertos] == ["2/0", "1/0", "1/1", "3/0"]
    assert [puerto["puntos_sobre_80"] for puerto in puertos] == [100, 99, 99, 60]
    assert [puerto["muestras_analizadas"] for puerto in puertos] == [100, 99, 99, 150]
    assert [puerto["valor"] for puerto in puertos] == [95.0, 95.0, 95.0, 100.0]
    assert [puerto["tipo"] for puerto in puertos] == ["degradacion", "uso", "uso", "uso"]
    assert all(0 <= puerto["valor"] <= 100 for puerto in puertos)


def validar_fuentes() -> None:
    fecha = datetime.now(timezone.utc)
    base = {"cmts": "CMTS-1", "puerto": "1/0", "descripcion": "A", "_time": fecha}
    bw = {**base, "_field": "bw", "_value": 100}
    uso = {**base, "_field": "utilizacion", "_value": 95}
    for filas, cantidad in (
        ([], 0),
        ([uso], 0),
        ([bw], 0),
        ([bw, {**uso, "_time": fecha + timedelta(seconds=1)}], 0),
    ):
        with ExitStack() as parches:
            parches.enter_context(patch.object(service, "obtener_muestras_flux", return_value="bloque"))
            parches.enter_context(patch.object(service, "consultar_flux_temp", return_value=filas))
            parches.enter_context(patch.object(service.time, "sleep", return_value=None))
            assert len(service.calcular_saturacion_actual()["datos"]) == cantidad


def validar_reglas() -> None:
    fecha = datetime.now(timezone.utc)
    filas = []

    def agregar(puerto: str, campo: str, valores: list) -> None:
        for indice, valor in enumerate(valores):
            filas.append({"cmts": "CMTS-1", "puerto": puerto, "descripcion": "NODO",
                          "_field": campo, "_value": valor,
                          "_time": fecha + timedelta(seconds=indice)})

    agregar("A", "utilizacion", [20, 30, 50, 70, 80])
    agregar("A", "bw", [100] * 5)
    agregar("B", "utilizacion", [81, 82, 85, 90])
    agregar("C", "utilizacion", [30, 40, 99, 35])
    agregar("C", "bw", [100] * 4)
    agregar("D", "utilizacion", [105, 110])
    agregar("D", "bw", [100] * 2)
    agregar("E", "snr", [29] * 59 + [30, 35, None, "", "NaN", "error"])
    agregar("F", "snr", [29] * 60)
    agregar("B", "snr", [28] * 60)
    agregar("B", "portadoras", [8, None, "NaN", "", -1, 2.5])
    agregar("B", "bw", [100] * 4)
    agregar("C", "utilizacion", [None, "", "NaN", "error", float("inf")])
    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=[filas] + [[]] * 23))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        puertos = service.calcular_saturacion_actual()["datos"][0]["puertos"]
    assert [p["puerto_fisico"] for p in puertos] == ["B", "D", "C", "F"]
    por_puerto = {p["puerto_fisico"]: p for p in puertos}
    assert por_puerto["B"]["puntos_sobre_80"] == 4
    assert por_puerto["B"]["valor"] == 84.5
    assert por_puerto["B"]["bw"] == 100
    assert por_puerto["B"]["capacidad_nominal"] == 240
    assert por_puerto["B"]["estado"] == "Saturación por degradación"
    assert por_puerto["D"]["valor"] == 100
    assert por_puerto["C"]["puntos_sobre_80"] == 1
    assert por_puerto["F"]["estado"] == "Degradación"
    assert por_puerto["F"]["ruido"] == 29
    assert por_puerto["F"]["valor"] == 0
    # La confirmacion tambien acumula muestras de distintos bloques.
    snr = [fila for fila in filas if fila["puerto"] == "F"]
    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=[snr[:30], snr[30:]] + [[]] * 22))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        assert service.calcular_saturacion_actual()["datos"][0]["puertos"][0]["tipo"] == "degradacion"


def validar_capacidad() -> None:
    fecha = datetime.now(timezone.utc)
    filas = []

    def agregar(puerto: str, bw: list, trafico: list, portadoras: int | None = 4) -> None:
        for indice, (ancho, uso) in enumerate(zip(bw, trafico)):
            campos = [("bw", ancho), ("utilizacion", uso)]
            if portadoras is not None:
                campos.append(("portadoras", portadoras))
            for campo, valor in campos:
                filas.append({"cmts": "CMTS-1", "puerto": puerto, "descripcion": "MISMO NODO",
                              "_time": fecha + timedelta(seconds=indice), "_field": campo, "_value": valor})

    agregar("caida", [120, 120, 50, 50, 50, 50, 120], [70, 75, 48, 49, 47, 48, 70])
    agregar("normal", [120], [110])
    agregar("sin_saturacion", [50], [20])
    agregar("81_mbps", [120], [81])
    agregar("limite", [110], [119])
    agregar("historico", [50, 50, 120], [48, 49, 70], None)
    agregar("aislado", [50], [48], None)
    agregar("umbral_capacidad", [96], [90])
    agregar("umbral_uso", [120], [96])
    # SNR confirmado es diagnostico adicional, sin cambiar la causa de saturacion.
    for indice in range(60):
        filas.append({"cmts": "CMTS-1", "puerto": "normal", "descripcion": "MISMO NODO",
                      "_time": fecha + timedelta(seconds=indice), "_field": "snr", "_value": 29})
    # El BW normal aparece en otro bloque: la referencia abarca los cuatro dias.
    posteriores = [f for f in filas if f["puerto"] == "historico" and f["_time"] == fecha + timedelta(seconds=2)]
    anteriores = [f for f in filas if f not in posteriores]
    with ExitStack() as parches:
        parches.enter_context(patch.object(service, "consultar_flux_temp", side_effect=[anteriores, posteriores] + [[]] * 22))
        parches.enter_context(patch.object(service.time, "sleep", return_value=None))
        puertos = service.calcular_saturacion_actual()["datos"][0]["puertos"]
    datos = {p["puerto_fisico"]: p for p in puertos}
    assert "81_mbps" not in datos and "umbral_uso" not in datos
    assert datos["caida"]["estado"] == "Saturación por degradación"
    assert datos["caida"]["tipo"] == "degradacion"
    assert datos["caida"]["valor"] == 96
    assert datos["caida"]["puntos_sobre_80"] == 4
    assert datos["caida"]["puntos_saturacion_degradada"] == 4
    assert datos["caida"]["bw"] == 120  # Recuperacion no borra el problema historico.
    assert datos["normal"]["estado"] == "Saturación"
    assert datos["normal"]["tipo"] == "uso"
    assert datos["normal"]["valor"] == 91.67 and datos["normal"]["ruido"] == 29
    assert datos["sin_saturacion"]["estado"] == "Degradación"
    assert datos["sin_saturacion"]["puntos_sobre_80"] == 0
    assert datos["sin_saturacion"]["bw"] == 50 and datos["sin_saturacion"]["capacidad_nominal"] == 120
    assert datos["limite"]["valor"] == 100
    assert datos["historico"]["estado"] == "Saturación por degradación"
    assert datos["historico"]["capacidad_nominal"] is None
    assert datos["historico"]["bw_maximo_historico"] == 120
    assert datos["aislado"]["tipo"] == "uso"  # Sin mezclar BW de otros puertos.
    assert datos["umbral_capacidad"]["tipo"] == "uso"
    assert puertos[0]["puerto_fisico"] == "caida"


def validar_cache_y_rutas(directorio: Path) -> None:
    anterior = {"generado_en": "2026-09-18T00:00:00+00:00", "ventana": "4d", "datos": [{"cmts": "CMTS-1"}]}
    estado = {"estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None}
    with ExitStack() as parches:
        parches.enter_context(patch.object(cache, "ARCHIVO_SATURACION", directorio / "hfc_saturacion.json"))
        parches.enter_context(patch.object(cache, "ARCHIVO_ESTADO", directorio / "hfc_estado.json"))
        cache.guardar_saturacion(anterior)
        cache.guardar_estado(estado)

        with patch.object(service, "consultar_flux_temp", side_effect=AssertionError("GET no debe consultar Influx")):
            assert router.saturacion_actual() == {"ok": True, "data": anterior}
            assert router.saturacion_estado()["data"] == estado

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

        with ExitStack() as fallos:
            fallos.enter_context(patch.object(service, "consultar_flux_temp", side_effect=[[], TimeoutError("timeout")]))
            fallos.enter_context(patch.object(service.time, "sleep", return_value=None))
            with TestClient(app) as cliente:
                assert cliente.post("/api/cmts/saturacion/actualizar").status_code == 200
                estado_error = cliente.get("/api/cmts/saturacion/estado").json()["data"]
                assert estado_error["estado"] == "error"
                assert estado_error["error"] == "timeout"
                assert cliente.get("/api/cmts/saturacion/actual").json()["data"] == anterior

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
    validar_reglas()
    validar_capacidad()
    with TemporaryDirectory() as temporal:
        validar_cache_y_rutas(Path(temporal))
    print("Validación CMTS saturación: OK")


if __name__ == "__main__":
    main()
