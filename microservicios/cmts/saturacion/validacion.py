"""Validación local con muestras sintéticas, sin consultas ni escrituras reales."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from microservicios.cmts.saturacion import service
from microservicios.cmts.saturacion.queries import obtener_muestras_flux

FECHA = datetime(2026, 9, 20, tzinfo=timezone.utc)
CLAVE = ("CMTS-1", "1", "NODO PRUEBA")


def registros(usos, *, bw=120_000_000, portadoras=4, snr=38, inicio=FECHA):
    for indice, uso in enumerate(usos):
        muestra = {
            "bw": bw,
            "utilizacion": bw * uso / 100,
            "portadoras": portadoras,
            "snr": snr,
        }
        for campo, valor in muestra.items():
            yield {
                "cmts": CLAVE[0],
                "puerto": CLAVE[1],
                "descripcion": CLAVE[2],
                "_time": inicio + timedelta(seconds=indice),
                "_field": campo,
                "_value": valor,
            }


def evaluar(usos, **kwargs):
    acumulados = {}
    service._procesar_bloque(registros(usos, **kwargs), acumulados)
    acumulado = acumulados[CLAVE]
    return acumulado, service._resultado_puerto(CLAVE[1], CLAVE[2], acumulado)


def validar_reglas():
    # Menos de 100 puntos => descarta
    for cantidad in (1, 99):
        _, resultado = evaluar([90] * cantidad)
        assert resultado is None

    # Saturación normal
    acumulado, resultado = evaluar([90] * 100, snr=35)
    assert resultado["estado"] == "Saturación normal"
    assert resultado["ratio_degradacion"] == 0.0
    assert resultado["puntos_sobre_80"] == 100

    # Degradación por SNR
    _, resultado = evaluar([90] * 100, snr=29)
    assert resultado["estado"] == "Degradación"
    assert resultado["ratio_degradacion"] == 1.0

    # Degradación por capacidad
    _, resultado = evaluar([90] * 100, bw=60_000_000, portadoras=4, snr=35)
    assert resultado["estado"] == "Degradación"
    assert resultado["ratio_degradacion"] == 1.0

    # Huecos: ya no rompen rachas, los puntos se acumulan globalmente
    acumulados = {}
    service._procesar_bloque(registros([90] * 50), acumulados)
    service._procesar_bloque(
        registros([90] * 50, inicio=FECHA + timedelta(minutes=60)), acumulados
    )
    resultado = service._resultado_puerto(CLAVE[1], CLAVE[2], acumulados[CLAVE])
    assert resultado["estado"] == "Saturación normal"
    assert resultado["puntos_sobre_80"] == 100


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

    with patch.object(
        service, "obtener_muestras_flux", side_effect=consulta
    ), patch.object(
        service, "iterar_flux_temp", side_effect=stream
    ) as streaming, patch.object(
        service, "guardar_estado", side_effect=guardar
    ), patch.object(
        service, "leer_estado", side_effect=lambda: dict(estado)
    ), patch.object(
        service.time, "sleep"
    ):
        resultado = service.calcular_saturacion_actual()
    assert streaming.call_count == service.TOTAL_BLOQUES == 32
    assert all(fin - inicio == timedelta(minutes=180) for inicio, fin in consultas)
    assert consultas[-1][1] - consultas[0][0] == timedelta(days=4)
    assert all(a[1] == b[0] for a, b in zip(consultas, consultas[1:]))
    assert resultado["datos"][0]["puertos"][0]["puntos_sobre_80"] == 100
    assert estado["fase"] == "analizando_resultados" and estado["porcentaje"] == 100
    assert estado["bloque_actual"] == estado["bloques_totales"] == 32
    assert not hasattr(service, "consultar_flux_temp")


def main():
    validar_reglas()
    validar_consulta()
    validar_streaming()
    print(
        "Validación HFC: OK (rachas, clasificación, SNR, capacidad, query y 192 bloques simulados)"
    )


if __name__ == "__main__":
    main()
