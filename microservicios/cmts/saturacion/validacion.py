"""Validacion manual de saturacion CMTS.

Ejecutar:

python -m microservicios.cmts.saturacion.validacion
"""

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from microservicios.app import app
from microservicios.cmts.saturacion import (
    cache,
    router,
    service,
)
from microservicios.cmts.saturacion.queries import (
    obtener_muestras_flux,
)


def validar_consultas() -> None:

    ahora = datetime.now(timezone.utc)

    flujo = obtener_muestras_flux(
        ahora - timedelta(hours=4),
        ahora,
    )

    assert 'r._field == "bw" or ' 'r._field == "utilizacion"' in flujo

    assert (
        "keep(columns: "
        '["_time", "_field", "_value", '
        '"cmts", "descripcion"])' in flujo
    )

    for operacion in (
        "join(",
        "max(",
        "last(",
        '"portadoras"',
    ):
        assert operacion not in flujo


def validar_calculo() -> None:

    bloques: list[tuple[datetime, datetime]] = []

    consultas: list[str] = []

    antiguo = datetime(
        2026,
        9,
        20,
        tzinfo=timezone.utc,
    )

    reciente = datetime(
        2026,
        9,
        21,
        tzinfo=timezone.utc,
    )

    # puerto,
    # bw_actual,
    # bw_normal,
    # cantidad muestras,
    # porcentaje uso

    casos = (
        # 99 puntos:
        # no debe aparecer
        (
            "A",
            122_880_000,
            122_880_000,
            99,
            95,
        ),
        # normal:
        # 100 puntos >= 90
        (
            "B",
            122_880_000,
            122_880_000,
            100,
            95,
        ),
        # 20% degradado:
        # 80% capacidad
        # umbral = 70
        (
            "C",
            98_304_000,
            122_880_000,
            100,
            75,
        ),
        # 30% degradado:
        # umbral = 60
        (
            "D",
            86_016_000,
            122_880_000,
            100,
            65,
        ),
        # capacidad 90%
        # NO degradado
        # umbral sigue 90
        (
            "E",
            110_592_000,
            122_880_000,
            100,
            80,
        ),
    )

    def consulta_bloque(
        inicio: datetime,
        fin: datetime,
    ) -> str:

        bloques.append(
            (
                inicio,
                fin,
            )
        )

        return f"bloque-{len(bloques)}"

    def consultar(
        consulta: str,
        **_kwargs: object,
    ) -> list[dict[str, object]]:

        consultas.append(consulta)

        # Solo colocamos datos
        # en el primer bloque.
        if consulta != "bloque-1":
            return []

        filas: list[dict[str, object]] = []

        for (
            puerto,
            bw_actual,
            bw_normal,
            cantidad,
            porcentaje,
        ) in casos:

            # BW antiguo = capacidad normal
            filas.append(
                {
                    "cmts": "CMTS-1",
                    "descripcion": puerto,
                    "_field": "bw",
                    "_value": bw_normal,
                    "_time": antiguo,
                }
            )

            # BW reciente = capacidad actual
            filas.append(
                {
                    "cmts": "CMTS-1",
                    "descripcion": puerto,
                    "_field": "bw",
                    "_value": bw_actual,
                    "_time": reciente,
                }
            )

            # La utilización usa el BW actual,
            # igual que el cálculo real.
            utilizacion = porcentaje / 100.0 * bw_actual

            filas.extend(
                {
                    "cmts": "CMTS-1",
                    "descripcion": puerto,
                    "_field": "utilizacion",
                    "_value": utilizacion,
                    "_time": reciente,
                }
                for _ in range(cantidad)
            )

        return filas

    with ExitStack() as parches:

        parches.enter_context(
            patch.object(
                service,
                "obtener_muestras_flux",
                side_effect=consulta_bloque,
            )
        )

        parches.enter_context(
            patch.object(
                service,
                "consultar_flux_temp",
                side_effect=consultar,
            )
        )

        parches.enter_context(
            patch.object(
                service.time,
                "sleep",
                return_value=None,
            )
        )

        datos = service.calcular_saturacion_actual()["datos"]

    # ==========================================
    # 24 BLOQUES DE 4 HORAS
    # ==========================================

    assert len(bloques) == 24

    assert consultas == [
        f"bloque-{numero}"
        for numero in range(
            1,
            25,
        )
    ]

    assert all(fin - inicio == timedelta(hours=4) for inicio, fin in bloques)

    assert all(
        actual[1] == siguiente[0]
        for actual, siguiente in zip(
            bloques,
            bloques[1:],
        )
    )

    assert bloques[-1][1] - bloques[0][0] == timedelta(days=4)

    # ==========================================
    # RESULTADOS
    # ==========================================

    puertos = datos[0]["puertos"]

    assert [puerto["puerto"] for puerto in puertos] == [
        "B",
        "C",
        "D",
    ]

    assert [puerto["puntos_sobre_90"] for puerto in puertos] == [
        100,
        100,
        100,
    ]

    assert [puerto["valor"] for puerto in puertos] == [
        95.0,
        75.0,
        65.0,
    ]

    assert [puerto["tipo"] for puerto in puertos] == [
        "uso",
        "degradacion",
        "degradacion",
    ]

    assert [puerto["estado"] for puerto in puertos] == [
        "Saturación",
        "Saturación por degradación",
        "Saturación por degradación",
    ]

    assert [puerto["bw"] for puerto in puertos] == [
        122_880_000,
        98_304_000,
        86_016_000,
    ]


def validar_fuentes() -> None:

    fecha = datetime.now(timezone.utc)

    bw = {
        "cmts": "CMTS-1",
        "descripcion": "A",
        "_field": "bw",
        "_value": 122_880_000,
        "_time": fecha,
    }

    uso = {
        "cmts": "CMTS-1",
        "descripcion": "A",
        "_field": "utilizacion",
        "_value": 50_000_000,
        "_time": fecha,
    }

    # ==========================================
    # SIN BW
    # ==========================================

    with ExitStack() as parches:

        parches.enter_context(
            patch.object(
                service,
                "obtener_muestras_flux",
                return_value="bloque",
            )
        )

        parches.enter_context(
            patch.object(
                service,
                "consultar_flux_temp",
                return_value=[uso],
            )
        )

        parches.enter_context(
            patch.object(
                service.time,
                "sleep",
                return_value=None,
            )
        )

        try:
            service.calcular_saturacion_actual()

        except RuntimeError as error:

            assert str(error) == "No se obtuvieron datos BW CMTS"

        else:
            raise AssertionError("Debió fallar sin BW")

    # ==========================================
    # SIN UTILIZACION
    # ==========================================

    with ExitStack() as parches:

        parches.enter_context(
            patch.object(
                service,
                "obtener_muestras_flux",
                return_value="bloque",
            )
        )

        parches.enter_context(
            patch.object(
                service,
                "consultar_flux_temp",
                return_value=[bw],
            )
        )

        parches.enter_context(
            patch.object(
                service.time,
                "sleep",
                return_value=None,
            )
        )

        try:
            service.calcular_saturacion_actual()

        except RuntimeError as error:

            assert str(error) == ("No se obtuvieron muestras " "de utilización CMTS")

        else:
            raise AssertionError("Debió fallar sin utilización")


def validar_cache_y_rutas(
    directorio: Path,
) -> None:

    anterior = {
        "generado_en": ("2026-09-18T00:00:00+00:00"),
        "ventana": "4d",
        "datos": [{"cmts": "CMTS-1"}],
    }

    estado = {
        "estado": "listo",
        "iniciado_en": None,
        "finalizado_en": None,
        "error": None,
    }

    with ExitStack() as parches:

        parches.enter_context(
            patch.object(
                cache,
                "ARCHIVO_SATURACION",
                directorio / "hfc_saturacion.json",
            )
        )

        parches.enter_context(
            patch.object(
                cache,
                "ARCHIVO_ESTADO",
                directorio / "hfc_estado.json",
            )
        )

        cache.guardar_saturacion(anterior)

        cache.guardar_estado(estado)

        with patch.object(
            router,
            "actualizar_saturacion",
            side_effect=AssertionError("Calculo inesperado"),
        ):

            with TestClient(app) as cliente:

                actual = cliente.get("/api/cmts/saturacion/actual")

            assert actual.status_code == 200

            assert actual.json() == {
                "ok": True,
                "data": anterior,
            }

        # Si falla el cálculo,
        # debe conservar cache anterior.

        with patch.object(
            service,
            "calcular_saturacion_actual",
            side_effect=RuntimeError("Influx no disponible"),
        ):

            try:
                service.actualizar_saturacion()

            except RuntimeError:
                pass

        assert cache.leer_saturacion() == anterior


def main() -> None:

    validar_consultas()

    validar_calculo()

    validar_fuentes()

    with TemporaryDirectory() as temporal:

        validar_cache_y_rutas(Path(temporal))

    print("Validación CMTS saturación: OK")


if __name__ == "__main__":
    main()
