"""Prueba manual de la API de topologias OLT (sin acceso SSH directo)."""

import os
import webbrowser
from urllib.parse import urljoin

import requests


BASE_HOST = os.environ.get("TOPOLOGIAS_API_HOST", "http://127.0.0.1:8000").rstrip("/")
BASE = BASE_HOST + "/api/olt/topologias"


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
        print("1. Buscar topología\n2. Ver guardadas\n3. Probar conexión\n0. Salir")
        opcion = input("Opción: ").strip()
        if opcion == "0":
            return
        if opcion == "3":
            print(consultar(BASE + "/health"))
            continue
        if opcion == "2":
            datos = consultar(BASE + "/guardadas")
            if datos:
                for item in datos["datos"]:
                    print(f"[{item['categoria']}] {item['olt']}: {urljoin(BASE_HOST + '/', item['enlace'].lstrip('/'))}")
                print("Guardadas vigentes:", datos["cantidad"])
            continue
        if opcion != "1":
            print("Opción inválida")
            continue
        texto = input("Texto / OLT a buscar: ").strip()
        if not texto:
            continue
        datos = consultar(BASE + "/buscar", texto=texto, limite=200)
        if datos is None:
            continue
        encontrados = datos["datos"]
        if not encontrados:
            print("Sin resultados")
            continue
        for indice, item in enumerate(encontrados, 1):
            print(f"{indice}. [{item['categoria']}] {item['ruta']}")
        elegido = input("Número para visualizar (Enter para volver): ").strip()
        if not elegido.isdigit() or not 1 <= int(elegido) <= len(encontrados):
            continue
        item = encontrados[int(elegido) - 1]
        if item["extension"] not in {".jpg", ".jpeg", ".png", ".vsd", ".vsdx"}:
            print("Este tipo de archivo se descarga mediante /archivo")
            continue
        topologia = consultar(BASE + "/link", categoria=item["categoria"], ruta=item["ruta"])
        if topologia:
            url = urljoin(BASE_HOST + "/", topologia["enlace"].lstrip("/"))
            print("OLT:", topologia["olt"])
            print("Imagen:", url)
            webbrowser.open(url)


if __name__ == "__main__":
    main()
