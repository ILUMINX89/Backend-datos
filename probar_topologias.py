"""Prueba por consola de la API de topologias."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote

import requests

API_BASE = os.getenv(
    "TOPOLOGIAS_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")
TIMEOUT = 60

OPCIONES = {
    "1": ("Huawei", "huawei"),
    "2": ("ZTE", "zte"),
    "3": ("Nokia", "nokia"),
    "4": ("ONNET", "onnet"),
    "5": ("FTTO", "ftto"),
}


def _get(path: str, **params):
    respuesta = requests.get(
        f"{API_BASE}{path}",
        params=params,
        timeout=TIMEOUT,
    )
    respuesta.raise_for_status()
    return respuesta


def mostrar_menu() -> None:
    print("\n" + "=" * 72)
    print("TOPOLOGIAS OLT")
    print("=" * 72)
    for numero, (nombre, _categoria) in OPCIONES.items():
        print(f"{numero}. {nombre}")
    print("6. Probar conexion SSH / conversor")
    print("0. Salir")


def probar_conexion() -> None:
    print(_get("/api/topologias/health").json())


def buscar_topologias(categoria: str) -> list[dict]:
    termino = input(
        "OLT o texto a buscar (Enter = listar): "
    ).strip()

    respuesta = _get(
        f"/api/topologias/olts/{categoria}",
        buscar=termino,
        limite=100,
    ).json()

    datos = respuesta.get("data", {}).get("datos", [])
    print(f"\nResultados: {len(datos)}")

    for indice, archivo in enumerate(datos, start=1):
        print(
            f"{indice:>3}. {archivo.get('ruta')} "
            f"[{archivo.get('extension', '')}]"
        )

    return datos


def descargar_jpg(categoria: str, archivo: dict) -> None:
    extension = str(archivo.get("extension", "")).lower()
    ruta = str(archivo.get("ruta", ""))

    if extension in {".jpg", ".jpeg", ".png"}:
        endpoint = f"/api/topologias/olts/{categoria}/imagen"
    elif extension in {".vsd", ".vsdx"}:
        endpoint = f"/api/topologias/olts/{categoria}/jpg"
    else:
        print("Ese archivo no tiene vista de imagen.")
        return

    respuesta = _get(endpoint, ruta=ruta)
    disposition = respuesta.headers.get(
        "content-disposition",
        "",
    )

    nombre = Path(ruta).stem + ".jpg"
    marca = "filename*=UTF-8''"
    if marca in disposition:
        nombre = unquote(disposition.split(marca, 1)[1])

    destino = Path(nombre).name
    Path(destino).write_bytes(respuesta.content)
    print(f"Imagen guardada en: {Path(destino).resolve()}")


def main() -> int:
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "0":
            return 0

        try:
            if opcion == "6":
                probar_conexion()
                continue

            seleccion = OPCIONES.get(opcion)
            if not seleccion:
                print("Opcion invalida.")
                continue

            nombre, categoria = seleccion
            print(f"\n--- {nombre} ---")
            datos = buscar_topologias(categoria)

            if not datos:
                continue

            eleccion = input(
                "\nNumero para abrir/convertir imagen "
                "(Enter para volver): "
            ).strip()

            if not eleccion:
                continue

            indice = int(eleccion) - 1
            if indice < 0 or indice >= len(datos):
                print("Numero fuera de rango.")
                continue

            descargar_jpg(categoria, datos[indice])

        except requests.RequestException as exc:
            detalle = ""
            if exc.response is not None:
                detalle = f" - {exc.response.text}"
            print(f"Error API: {exc}{detalle}")
        except (ValueError, OSError) as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    sys.exit(main())
