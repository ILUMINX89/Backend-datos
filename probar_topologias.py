"""Prueba manual de la API de topologias OLT (sin acceso SSH directo)."""

import os
from pathlib import Path

import requests


BASE = os.environ.get("TOPOLOGIAS_API_URL", "http://127.0.0.1:8000/api/olt/topologias").rstrip("/")
OPCIONES = {"1": ("huawei", "Huawei"), "2": ("zte", "ZTE"), "3": ("nokia", "Nokia"), "4": ("onnet", "ONNET"), "5": ("ftto", "FTTO")}


def consultar(url: str, **params):
    try:
        respuesta = requests.get(url, params=params, timeout=30)
        contenido = respuesta.json()
        if not respuesta.ok or not contenido.get("ok"):
            print("Error:", contenido.get("error", "Respuesta inesperada"))
            return None
        return contenido["data"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        print("No se pudo consultar la API:", exc)
        return None


def guardar_imagen(url: str, ruta: str):
    nombre = Path(ruta.replace("\\", "/")).name
    extension = ".png" if url.endswith("/imagen") and nombre.lower().endswith(".png") else ".jpg"
    destino = Path.cwd() / (Path(nombre).stem + extension)
    try:
        with requests.get(url, params={"ruta": ruta}, stream=True, timeout=180) as respuesta:
            if not respuesta.ok:
                try:
                    print("Error:", respuesta.json().get("error", "No se pudo obtener la imagen"))
                except ValueError:
                    print("No se pudo obtener la imagen")
                return
            with destino.open("wb") as salida:
                for bloque in respuesta.iter_content(64 * 1024):
                    if bloque:
                        salida.write(bloque)
        print("Imagen guardada en:", destino)
    except requests.RequestException as exc:
        print("Error al descargar:", exc)


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
        if item["extension"] in {".jpg", ".jpeg", ".png"}:
            guardar_imagen(BASE + f"/{categoria}/imagen", item["ruta"])
        elif item["extension"] in {".vsd", ".vsdx"}:
            guardar_imagen(BASE + f"/{categoria}/jpg", item["ruta"])
        else:
            print("Este tipo de archivo se descarga mediante /archivo")


if __name__ == "__main__":
    main()
