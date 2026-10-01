"""Validación local con muestras sintéticas, sin consultas ni escrituras reales."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import BackgroundTasks

from microservicios.cmts.saturacion import router
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

    estado = {
        "estado": "procesando",
        "bloque_actual": 96,
        "bloques_totales": 192,
        "porcentaje": 50.0,
        "chunk_minutos": 30,
    }
    escrituras = []

    def guardar(nuevo):
        escrituras.append(dict(nuevo))
        estado.update(nuevo)

    with patch.object(
        service, "obtener_muestras_flux", side_effect=consulta
    ), patch.object(
        service, "iterar_flux_temp", side_effect=stream
    ) as streaming, patch.object(
        service, "guardar_estado", side_effect=guardar
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
    assert service.CHUNK_MINUTOS == 180
    assert service.TOTAL_BLOQUES == 32
    for campo in (
        "ejecucion_id",
        "chunk_minutos",
        "ventana_dias",
        "bloques_totales",
        "version_saturacion",
    ):
        assert campo in escrituras[0]
    assert escrituras[0]["bloque_actual"] == 0
    assert escrituras[0]["bloques_totales"] == 32
    assert escrituras[0]["porcentaje"] == 0.0
    assert escrituras[0]["chunk_minutos"] == 180
    assert not hasattr(service, "consultar_flux_temp")


def validar_bloqueo_actualizacion():
    assert router._actualizacion_lock.acquire(blocking=False)
    try:
        tareas = BackgroundTasks()
        with patch.object(router, "iniciar_ejecucion_saturacion") as iniciar:
            respuesta = router.saturacion_actualizar(tareas)
        assert respuesta == {"ok": True, "estado": "procesando"}
        assert not tareas.tasks
        iniciar.assert_not_called()
    finally:
        router._actualizacion_lock.release()


def validar_estado_final():
    estado = {}

    def guardar(nuevo):
        estado.update(nuevo)

    with patch.object(service, "guardar_estado", side_effect=guardar), patch.object(
        service, "guardar_saturacion"
    ), patch.object(
        service, "calcular_saturacion_actual", return_value={"datos": []}
    ):
        service.actualizar_saturacion()
    assert estado["estado"] == "listo"
    assert estado["fase"] == "finalizado"
    assert estado["bloque_actual"] == estado["bloques_totales"] == 32
    assert estado["porcentaje"] == 100.0
    assert estado["error"] is None
    assert estado["ejecucion_id"]
    assert estado["chunk_minutos"] == 180
    assert estado["version_saturacion"] == service.VERSION_SATURACION


def main():
    validar_reglas()
    validar_consulta()
    validar_streaming()
    validar_bloqueo_actualizacion()
    validar_estado_final()
    print(
        "Validacion HFC: OK (estado por ejecucion, lock y 32 bloques simulados)"
    )


if __name__ == "__main__":
    main()
