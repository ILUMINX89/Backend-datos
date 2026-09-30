"""Prueba manual de la API de topologías OLT con conversión VSD/VSDX -> JPG."""

import ctypes
import os
import time
import webbrowser
from ctypes import wintypes
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import pythoncom
import requests
import win32com.client
import win32gui
import win32ui
from PIL import Image, ImageChops


BASE_HOST = os.environ.get("TOPOLOGIAS_API_HOST", "http://127.0.0.1:8000").rstrip("/")
BASE = BASE_HOST + "/api/olt/topologias"
BASE_DIR = Path(__file__).resolve().parent
CARPETA_IMAGENES = BASE_DIR / "data" / "topologias" / "imagenes"

NOMBRES_CATEGORIA = {
    "huawei": "Huawei",
    "zte": "ZTE",
    "nokia": "Nokia",
    "onnet": "ONNET",
    "ftto": "FTTO",
}

EXTENSIONES_VISIO = {".vsd", ".vsdx"}
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png"}

ANCHO_RENDER = 3840
ALTO_RENDER = 2160
MARGEN = 30


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


def procesar_mensajes(user32, segundos):
    msg = wintypes.MSG()
    fin = time.time() + segundos
    while time.time() < fin:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.01)


def recortar_imagen(imagen):
    fondo = Image.new("RGB", imagen.size, (255, 255, 255))
    bbox = ImageChops.difference(imagen, fondo).getbbox()
    if not bbox:
        return imagen

    izq, arriba, der, abajo = bbox
    return imagen.crop((
        max(0, izq - MARGEN),
        max(0, arriba - MARGEN),
        min(imagen.width, der + MARGEN),
        min(imagen.height, abajo + MARGEN),
    ))


def convertir_visio_a_jpg(ruta_visio):
    ruta_visio = Path(ruta_visio).resolve()
    if not ruta_visio.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_visio}")
    if ruta_visio.suffix.lower() not in EXTENSIONES_VISIO:
        raise ValueError(f"Extensión no soportada: {ruta_visio.suffix}")

    ruta_jpg = ruta_visio.with_suffix(".jpg")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    atl = ctypes.WinDLL("atl.dll")
    atl.AtlAxWinInit.restype = wintypes.BOOL

    hwnd = viewer = hdc_pantalla = dc_pantalla = dc_memoria = bitmap = None
    com_inicializado = False

    try:
        pythoncom.CoInitialize()
        com_inicializado = True

        if not atl.AtlAxWinInit():
            raise RuntimeError("No fue posible inicializar ATL")

        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND

        # Contenedor ActiveX oculto: no se usa WS_VISIBLE.
        hwnd = user32.CreateWindowExW(
            0, "AtlAxWin", "VisioViewer.Viewer", 0x00CF0000,
            0, 0, ANCHO_RENDER, ALTO_RENDER, None, None, None, None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        atl.AtlAxGetControl.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.c_void_p)]
        atl.AtlAxGetControl.restype = ctypes.c_long

        punk = ctypes.c_void_p()
        hr = atl.AtlAxGetControl(hwnd, ctypes.byref(punk))
        if hr != 0:
            raise RuntimeError(f"AtlAxGetControl falló. HRESULT: 0x{hr & 0xFFFFFFFF:08X}")

        unknown = pythoncom.ObjectFromAddress(punk.value, pythoncom.IID_IUnknown)
        dispatch = unknown.QueryInterface(pythoncom.IID_IDispatch)
        viewer = win32com.client.Dispatch(dispatch)

        if not viewer.Load(str(ruta_visio)) or not viewer.DocumentLoaded:
            raise RuntimeError(
                f"Visio Viewer no pudo cargar el archivo. LastErrorCode={viewer.LastErrorCode}"
            )

        procesar_mensajes(user32, 2)
        viewer.ToolbarVisible = False
        viewer.PageTabsVisible = False
        viewer.ScrollbarsVisible = False
        viewer.HighQualityRender = True
        viewer.Zoom = -1
        procesar_mensajes(user32, 2)

        viewer.Render(ANCHO_RENDER, ALTO_RENDER)
        procesar_mensajes(user32, 1)
        if viewer.LastErrorCode != 0:
            raise RuntimeError(f"Error en Render(). LastErrorCode={viewer.LastErrorCode}")

        hdc_pantalla = win32gui.GetDC(0)
        dc_pantalla = win32ui.CreateDCFromHandle(hdc_pantalla)
        dc_memoria = dc_pantalla.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(dc_pantalla, ANCHO_RENDER, ALTO_RENDER)
        dc_memoria.SelectObject(bitmap)
        dc_memoria.FillSolidRect((0, 0, ANCHO_RENDER, ALTO_RENDER), 0xFFFFFF)

        viewer.Paint(
            dc_memoria.GetSafeHdc(), 0, 0,
            ANCHO_RENDER, ALTO_RENDER, 0, 0,
        )
        if viewer.LastErrorCode != 0:
            raise RuntimeError(f"Error en Paint(). LastErrorCode={viewer.LastErrorCode}")

        info = bitmap.GetInfo()
        imagen = Image.frombuffer(
            "RGB",
            (info["bmWidth"], info["bmHeight"]),
            bitmap.GetBitmapBits(True),
            "raw", "BGRX", 0, 1,
        )
        imagen = recortar_imagen(imagen)
        imagen.save(ruta_jpg, "JPEG", quality=100, subsampling=0)
        return ruta_jpg

    finally:
        for recurso, metodo in (
            (dc_memoria, "DeleteDC"),
            (dc_pantalla, "DeleteDC"),
        ):
            if recurso is not None:
                try:
                    getattr(recurso, metodo)()
                except Exception:
                    pass

        if hdc_pantalla is not None:
            try:
                win32gui.ReleaseDC(0, hdc_pantalla)
            except Exception:
                pass
        if bitmap is not None:
            try:
                win32gui.DeleteObject(bitmap.GetHandle())
            except Exception:
                pass
        if viewer is not None:
            try:
                viewer.Unload()
            except Exception:
                pass
        if hwnd:
            try:
                user32.DestroyWindow(hwnd)
            except Exception:
                pass
        if com_inicializado:
            pythoncom.CoUninitialize()


def obtener_ruta_local(enlace):
    nombre = Path(unquote(urlparse(enlace).path)).name
    return CARPETA_IMAGENES / nombre


def main():
    while True:
        print("\n========================================")
        print("TOPOLOGIAS OLT")
        print("========================================")
        print("1. Buscar topología\n2. Probar conexión\n0. Salir")

        opcion = input("Opción: ").strip()
        if opcion == "0":
            return
        if opcion == "2":
            print(consultar(BASE + "/health"))
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
            print(f"{indice}. {item['nombre']}")

        elegido = input("Número para visualizar (Enter para volver): ").strip()
        if not elegido.isdigit() or not 1 <= int(elegido) <= len(encontrados):
            continue

        item = encontrados[int(elegido) - 1]
        extension = item["extension"].lower()

        if extension not in EXTENSIONES_IMAGEN | EXTENSIONES_VISIO:
            print("Este tipo de archivo se descarga mediante /archivo")
            continue

        topologia = consultar(
            BASE + "/link",
            categoria=item["categoria"],
            ruta=item["ruta"],
        )
        if not topologia:
            continue

        url = urljoin(BASE_HOST + "/", topologia["enlace"].lstrip("/"))
        fabricante = NOMBRES_CATEGORIA.get(
            topologia["categoria"],
            topologia["categoria"].upper(),
        )

        print(f"OLT {fabricante}:", topologia["olt"])
        print("Archivo:", url)

        if extension in EXTENSIONES_IMAGEN:
            webbrowser.open(url)
            continue

        ruta_local = obtener_ruta_local(topologia["enlace"])
        print("Archivo local:", ruta_local)

        if not ruta_local.exists():
            print("No se encontró el archivo materializado:", ruta_local)
            continue

        respuesta = input("¿Desea convertir la topología a JPG? (y/n): ").strip().lower()
        if respuesta != "y":
            print("Conversión cancelada.")
            continue

        print("Generando JPG...")
        inicio = time.time()

        try:
            jpg = convertir_visio_a_jpg(ruta_local)
            print("JPG generado correctamente:", jpg)
            print(f"Tiempo: {time.time() - inicio:.2f} segundos")
            webbrowser.open(jpg.as_uri())
        except Exception as error:
            print("ERROR convirtiendo la topología:", error)


if __name__ == "__main__":
    main()
