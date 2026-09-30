"""Validación local con muestras sintéticas, sin consultas ni escrituras reales."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from microservicios.cmts.saturacion import service
from microservicios.cmts.saturacion.queries import obtener_muestras_flux

FECHA = datetime(2026, 9, 20, tzinfo=timezone.utc)
CLAVE = ("CMTS-1", "1", "NODO PRUEBA")


def registros(usos, *, bw=120_000_000, portadoras=4, snr=38, inicio=FECHA):
    for indice, uso in enumerate(usos):
        muestra = {"bw": bw, "utilizacion": bw * uso / 100, "portadoras": portadoras, "snr": snr}
        for campo, valor in muestra.items():
            yield {"cmts": CLAVE[0], "puerto": CLAVE[1], "descripcion": CLAVE[2],
                   "_time": inicio + timedelta(seconds=indice), "_field": campo, "_value": valor}


def evaluar(usos, **kwargs):
    acumulados = {}
    service._procesar_bloque(registros(usos, **kwargs), acumulados)
    acumulado = acumulados[CLAVE]
    return acumulado, service._resultado_puerto(CLAVE[1], CLAVE[2], acumulado)


def validar_reglas():
    for cantidad in (1, 99, 100, 101):
        acumulado, resultado = evaluar([90] * cantidad)
        assert acumulado["racha_uso_maxima"] == cantidad
        if cantidad < 100:
            assert resultado is None
        else:
            assert (resultado["estado"], resultado["tipo"]) == ("Saturación", "uso")
            assert resultado["ruido"] == 38 and not resultado["degradacion_snr"]
            assert resultado["capacidad_nominal"] == 120_000_000

    acumulado, resultado = evaluar([90] * 99 + [80] + [90] * 99)
    assert resultado is None and acumulado["racha_uso_maxima"] == 99
    assert acumulado["puntos_sobre_80"] == 198

    acumulados = {}
    service._procesar_bloque(registros([90] * 73), acumulados)
    service._procesar_bloque(registros([90] * 27, inicio=FECHA + timedelta(seconds=73)), acumulados)
    assert acumulados[CLAVE]["racha_uso_maxima"] == 100
    assert service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE])["estado"] == "Saturación"

    # El hueco rompe las tres rachas y conserva sus máximos.
    acumulados = {}
    service._procesar_bloque(registros([90] * 70, bw=60_000_000, snr=29), acumulados)
    service._procesar_bloque(registros([90] * 30, bw=60_000_000, snr=29,
                                     inicio=FECHA + timedelta(minutes=17)), acumulados)
    for criterio in ("uso", "capacidad", "snr"):
        assert acumulados[CLAVE][f"racha_{criterio}_maxima"] == 70
        assert acumulados[CLAVE][f"racha_{criterio}_actual"] == 30
    assert service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE])["estado"] == "Degradación"
    # Sin otra degradación confirmada, ese mismo hueco no autoriza reportar uso.
    acumulados = {}
    service._procesar_bloque(registros([90] * 70), acumulados)
    service._procesar_bloque(registros([90] * 30, inicio=FECHA + timedelta(minutes=17)), acumulados)
    assert service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE]) is None

    for cantidad in (59, 60):
        acumulado, resultado = evaluar([20] * cantidad, snr=29)
        assert acumulado["racha_snr_maxima"] == cantidad
        if cantidad == 59:
            assert resultado is None
        else:
            assert resultado["degradacion_snr"] and resultado["ruido"] == 29
            assert (resultado["estado"], resultado["tipo"]) == ("Degradación", "degradacion")

    for cantidad in (99, 100):
        acumulado, resultado = evaluar([20] * cantidad, bw=60_000_000)
        assert acumulado["racha_capacidad_maxima"] == cantidad
        if cantidad == 99:
            assert resultado is None
        else:
            assert resultado["degradacion_capacidad"] and not resultado["degradacion_snr"]
            assert resultado["estado"] == "Degradación"

    for kwargs in ({"snr": 29}, {"bw": 60_000_000}):
        _, resultado = evaluar([90] * 100, **kwargs)
        assert (resultado["estado"], resultado["tipo"]) == ("Saturación por degradación", "degradacion")
    _, resultado = evaluar([120] * 100)
    assert resultado["valor"] == 100
    _, resultado = evaluar([90] * 100 + [20])
    assert resultado["valor"] == 90
    _, resultado = evaluar([80.01] * 100, bw=96_000_000)
    assert resultado["estado"] == "Saturación" and not resultado["degradacion_capacidad"]

    # SNR cero, normal o faltante rompe rachas; capacidad faltante no usa BW histórico.
    for campo, invalido, criterio in (("snr", 0, "snr"), ("snr", 30, "snr"),
                                     ("snr", None, "snr"), ("portadoras", None, "capacidad"),
                                     ("portadoras", 2.5, "capacidad"), ("bw", 0, "uso"),
                                     ("utilizacion", None, "uso")):
        acumulados = {}
        filas = list(registros([90] * 199, bw=60_000_000, snr=29))
        for fila in filas:
            if fila["_time"] == FECHA + timedelta(seconds=99) and fila["_field"] == campo:
                fila["_value"] = invalido
        # Desordenar también verifica el orden temporal dentro del bloque.
        service._procesar_bloque(iter(reversed(filas)), acumulados)
        assert acumulados[CLAVE][f"racha_{criterio}_maxima"] == 99
        assert acumulados[CLAVE]["ultimo_snr"] == 29
    acumulado, resultado = evaluar([90] * 100, portadoras=None, snr=None)
    assert resultado["estado"] == "Saturación"
    assert resultado["capacidad_nominal"] is None and resultado["ruido"] is None
    assert acumulado["racha_capacidad_maxima"] == 0
    # Reemplazar la muestra central por SNR normal para evitar confirmar 118 dispersas.
    filas = list(registros([20] * 119, snr=29))
    for fila in filas:
        if fila["_field"] == "snr" and fila["_time"] == FECHA + timedelta(seconds=59):
            fila["_value"] = 38
    acumulados = {}
    service._procesar_bloque(iter(filas), acumulados)
    assert acumulados[CLAVE]["racha_snr_maxima"] == 59
    assert service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE]) is None

    acumulados = {}
    service._procesar_bloque(registros([20] * 60, snr=29), acumulados)
    service._procesar_bloque(registros([20], inicio=FECHA + timedelta(seconds=60)), acumulados)
    resultado = service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE])
    assert resultado["degradacion_snr"] and resultado["ruido"] == 38

    filas = list(registros([20] * 199, bw=60_000_000))
    for fila in filas:
        if fila["_field"] == "bw" and fila["_time"] == FECHA + timedelta(seconds=99):
            fila["_value"] = 96_000_000
    acumulados = {}
    service._procesar_bloque(iter(filas), acumulados)
    assert acumulados[CLAVE]["racha_capacidad_maxima"] == 99
    assert service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE]) is None

    # No asociar campos de distintos puertos ni timestamps con igual descripción.
    filas = list(registros([90] * 100))
    for fila in filas:
        if fila["_field"] == "utilizacion":
            fila["puerto"] = "2"
    acumulados = {}
    service._procesar_bloque(iter(filas), acumulados)
    assert len(acumulados) == 2
    assert all(a["racha_uso_maxima"] == 0 for a in acumulados.values())
    for fila in filas:
        if fila["_field"] == "utilizacion":
            fila["puerto"] = "1"
            fila["_time"] += timedelta(microseconds=1)
    acumulados = {}
    service._procesar_bloque(iter(filas), acumulados)
    assert acumulados[CLAVE]["racha_uso_maxima"] == 0


def validar_consulta():
    flujo = obtener_muestras_flux(FECHA, FECHA + timedelta(minutes=30))
    for campo in ("bw", "utilizacion", "snr", "portadoras"):
        assert f'r._field == "{campo}"' in flujo
    assert 'r._measurement == "estado_puertos"' in flujo
    assert 'strings.hasPrefix(v: r.descripcion, prefix: "NODO ")' in flujo
    for operacion in ("pivot(", "join(", "aggregateWindow(", "group(", "sort("):
        assert operacion not in flujo


def validar_streaming():
    consultas = []
    def consulta(inicio, fin):
        consultas.append((inicio, fin))
        return len(consultas)
    def stream(numero, *, fuente):
        assert fuente == "cmts"
        if numero == 1:
            yield from registros([90] * 73)
        elif numero == 2:
            yield from registros([90] * 27, inicio=FECHA + timedelta(seconds=73))

    estado = {}
    def guardar(nuevo):
        estado.update(nuevo)
    with patch.object(service, "obtener_muestras_flux", side_effect=consulta), \
         patch.object(service, "iterar_flux_temp", side_effect=stream) as streaming, \
         patch.object(service, "guardar_estado", side_effect=guardar), \
         patch.object(service, "leer_estado", side_effect=lambda: dict(estado)), \
         patch.object(service.time, "sleep"):
        resultado = service.calcular_saturacion_actual()
    assert streaming.call_count == service.TOTAL_BLOQUES == 192
    assert all(fin - inicio == timedelta(minutes=30) for inicio, fin in consultas)
    assert consultas[-1][1] - consultas[0][0] == timedelta(days=4)
    assert all(a[1] == b[0] for a, b in zip(consultas, consultas[1:]))
    assert resultado["datos"][0]["puertos"][0]["racha_uso_maxima"] == 100
    assert estado["fase"] == "analizando_resultados" and estado["porcentaje"] == 100
    assert estado["bloque_actual"] == estado["bloques_totales"] == 192
    assert not hasattr(service, "consultar_flux_temp")


def main():
    validar_reglas()
    validar_consulta()
    validar_streaming()
    print("Validación HFC: OK (rachas, clasificación, SNR, capacidad, query y 192 bloques simulados)")


if __name__ == "__main__":
    main()
