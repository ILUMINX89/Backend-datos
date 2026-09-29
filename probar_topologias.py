"""Prueba manual de la API de topologias OLT (sin acceso SSH directo)."""

import os
import webbrowser
from urllib.parse import urljoin

import requests


BASE_HOST = os.environ.get("TOPOLOGIAS_API_HOST", "http://127.0.0.1:8000").rstrip("/")
BASE = BASE_HOST + "/api/olt/topologias"
OPCIONES = {"1": ("huawei", "Huawei"), "2": ("zte", "ZTE"), "3": ("nokia", "Nokia"), "4": ("onnet", "ONNET"), "5": ("ftto", "FTTO")}


def consultar(url: str, **params):
    try:
        respuesta = requests.get(url, params=params, timeout=180)
        contenido = respuesta.json()
        if not respuesta.ok or not contenido.get("ok"):
            print("Error:", contenido.get("error", "Respuesta inesperada"))
            return None
        return contenido["data"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        print("No se pudo consultar la API:", exc)
        return None


def main():
    while True:
        print("\n========================================\nTOPOLOGIAS OLT\n========================================")
        for numero, (_, nombre) in OPCIONES.items():
            print(f"{numero}. {nombre}")
        print("6. Probar conexión\n0. Salir")
        opcion = input("Opción: ").strip()
        if opcion == "0":
            return
        if opcion == "6":
            print(consultar(BASE + "/health"))
            continue
        if opcion not in OPCIONES:
            print("Opción inválida")
            continue
        categoria = OPCIONES[opcion][0]
        texto = input("OLT o texto a buscar: ").strip()
        datos = consultar(BASE + "/" + categoria, buscar=texto, limite=200)
        if datos is None:
            continue
        encontrados = datos["datos"]
        if not encontrados:
            print("Sin resultados")
            continue
        for indice, item in enumerate(encontrados, 1):
            print(f"{indice}. {item['ruta']}")
        elegido = input("Número para visualizar (Enter para volver): ").strip()
        if not elegido.isdigit() or not 1 <= int(elegido) <= len(encontrados):
            continue
        item = encontrados[int(elegido) - 1]
        if item["extension"] not in {".jpg", ".jpeg", ".png", ".vsd", ".vsdx"}:
            print("Este tipo de archivo se descarga mediante /archivo")
            continue
        topologia = consultar(BASE + f"/{categoria}/link", ruta=item["ruta"])
        if topologia:
            url = urljoin(BASE_HOST + "/", topologia["enlace"].lstrip("/"))
            print("OLT:", topologia["olt"])
            print("Imagen:", url)
            webbrowser.open(url)


if __name__ == "__main__":
    main()
