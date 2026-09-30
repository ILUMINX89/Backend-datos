import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pythoncom
import win32com.client
import win32gui
import win32ui
from PIL import Image, ImageChops


# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_TOPOLOGIAS = Path(
    r"C:\Github\Backend-datos\data\topologias\imagenes"
)

ANCHO_RENDER = 3840
ALTO_RENDER = 2160
MARGEN = 30

EXTENSIONES_VISIO = {".vsd", ".vsdx"}


# ============================================================
# PROCESAR MENSAJES WINDOWS
# ============================================================

def procesar_mensajes(user32, segundos):
    msg = wintypes.MSG()
    fin = time.time() + segundos

    while time.time() < fin:
        while user32.PeekMessageW(
            ctypes.byref(msg),
            None,
            0,
            0,
            1,
        ):
            user32.TranslateMessage(
                ctypes.byref(msg)
            )

            user32.DispatchMessageW(
                ctypes.byref(msg)
            )

        time.sleep(0.01)


# ============================================================
# RECORTAR ESPACIO BLANCO
# ============================================================

def recortar_imagen(imagen, margen=MARGEN):
    fondo = Image.new(
        "RGB",
        imagen.size,
        (255, 255, 255),
    )

    diferencia = ImageChops.difference(
        imagen,
        fondo,
    )

    bbox = diferencia.getbbox()

    if not bbox:
        return imagen

    izquierda, arriba, derecha, abajo = bbox

    izquierda = max(
        0,
        izquierda - margen,
    )

    arriba = max(
        0,
        arriba - margen,
    )

    derecha = min(
        imagen.width,
        derecha + margen,
    )

    abajo = min(
        imagen.height,
        abajo + margen,
    )

    return imagen.crop(
        (
            izquierda,
            arriba,
            derecha,
            abajo,
        )
    )


# ============================================================
# CONVERTIR VISIO A JPG
# ============================================================

def convertir_visio_a_jpg(ruta_visio):
    ruta_visio = Path(ruta_visio).resolve()

    # --------------------------------------------------------
    # VALIDACIONES
    # --------------------------------------------------------

    if not ruta_visio.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {ruta_visio}"
        )

    if ruta_visio.suffix.lower() not in EXTENSIONES_VISIO:
        raise ValueError(
            f"Extensión no soportada: {ruta_visio.suffix}"
        )

    ruta_jpg = ruta_visio.with_suffix(".jpg")

    # --------------------------------------------------------
    # WINDOWS / ATL
    # --------------------------------------------------------

    user32 = ctypes.WinDLL(
        "user32",
        use_last_error=True,
    )

    atl = ctypes.WinDLL("atl.dll")

    atl.AtlAxWinInit.restype = wintypes.BOOL

    WS_OVERLAPPEDWINDOW = 0x00CF0000

    # --------------------------------------------------------
    # VARIABLES PARA LIMPIEZA
    # --------------------------------------------------------

    hwnd = None
    viewer = None

    hdc_pantalla = None
    dc_pantalla = None
    dc_memoria = None
    bitmap = None

    com_inicializado = False

    try:

        # ====================================================
        # COM
        # ====================================================

        pythoncom.CoInitialize()
        com_inicializado = True

        # ====================================================
        # ATL
        # ====================================================

        if not atl.AtlAxWinInit():
            raise RuntimeError(
                "No fue posible inicializar ATL"
            )

        # ====================================================
        # CREAR ACTIVEX OCULTO
        # ====================================================

        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ]

        user32.CreateWindowExW.restype = wintypes.HWND

        hwnd = user32.CreateWindowExW(
            0,
            "AtlAxWin",
            "VisioViewer.Viewer",

            # Sin WS_VISIBLE.
            # La conversión ocurre en segundo plano.
            WS_OVERLAPPEDWINDOW,

            0,
            0,
            ANCHO_RENDER,
            ALTO_RENDER,
            None,
            None,
            None,
            None,
        )

        if not hwnd:
            raise ctypes.WinError(
                ctypes.get_last_error()
            )

        # ====================================================
        # OBTENER CONTROL ACTIVEX
        # ====================================================

        atl.AtlAxGetControl.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(
                ctypes.c_void_p
            ),
        ]

        atl.AtlAxGetControl.restype = ctypes.c_long

        punk = ctypes.c_void_p()

        hr = atl.AtlAxGetControl(
            hwnd,
            ctypes.byref(punk),
        )

        if hr != 0:
            raise RuntimeError(
                "AtlAxGetControl falló. "
                f"HRESULT: "
                f"0x{hr & 0xFFFFFFFF:08X}"
            )

        # ====================================================
        # IUNKNOWN -> IDISPATCH
        # ====================================================

        unknown = pythoncom.ObjectFromAddress(
            punk.value,
            pythoncom.IID_IUnknown,
        )

        dispatch = unknown.QueryInterface(
            pythoncom.IID_IDispatch
        )

        viewer = win32com.client.Dispatch(
            dispatch
        )

        # ====================================================
        # CARGAR VISIO
        # ====================================================

        resultado = viewer.Load(
            str(ruta_visio)
        )

        if not resultado or not viewer.DocumentLoaded:
            raise RuntimeError(
                "Visio Viewer no pudo cargar el archivo. "
                f"LastErrorCode={viewer.LastErrorCode}"
            )

        procesar_mensajes(
            user32,
            2,
        )

        # ====================================================
        # CONFIGURAR VIEWER
        # ====================================================

        viewer.ToolbarVisible = False
        viewer.PageTabsVisible = False
        viewer.ScrollbarsVisible = False
        viewer.HighQualityRender = True

        # Ajustar página completa.
        viewer.Zoom = -1

        procesar_mensajes(
            user32,
            2,
        )

        # ====================================================
        # RENDER 4K
        # ====================================================

        viewer.Render(
            ANCHO_RENDER,
            ALTO_RENDER,
        )

        procesar_mensajes(
            user32,
            1,
        )

        if viewer.LastErrorCode != 0:
            raise RuntimeError(
                "Error durante Render(). "
                f"LastErrorCode={viewer.LastErrorCode}"
            )

        # ====================================================
        # CREAR BITMAP
        # ====================================================

        hdc_pantalla = win32gui.GetDC(0)

        dc_pantalla = (
            win32ui.CreateDCFromHandle(
                hdc_pantalla
            )
        )

        dc_memoria = (
            dc_pantalla.CreateCompatibleDC()
        )

        bitmap = win32ui.CreateBitmap()

        bitmap.CreateCompatibleBitmap(
            dc_pantalla,
            ANCHO_RENDER,
            ALTO_RENDER,
        )

        dc_memoria.SelectObject(
            bitmap
        )

        # Fondo blanco
        dc_memoria.FillSolidRect(
            (
                0,
                0,
                ANCHO_RENDER,
                ALTO_RENDER,
            ),
            0xFFFFFF,
        )

        # ====================================================
        # PAINT
        # ====================================================

        viewer.Paint(
            dc_memoria.GetSafeHdc(),
            0,
            0,
            ANCHO_RENDER,
            ALTO_RENDER,
            0,
            0,
        )

        if viewer.LastErrorCode != 0:
            raise RuntimeError(
                "Error durante Paint(). "
                f"LastErrorCode={viewer.LastErrorCode}"
            )

        # ====================================================
        # BITMAP -> PIL
        # ====================================================

        info = bitmap.GetInfo()

        bits = bitmap.GetBitmapBits(
            True
        )

        imagen = Image.frombuffer(
            "RGB",
            (
                info["bmWidth"],
                info["bmHeight"],
            ),
            bits,
            "raw",
            "BGRX",
            0,
            1,
        )

        # ====================================================
        # RECORTE AUTOMÁTICO
        # ====================================================

        imagen = recortar_imagen(
            imagen
        )

        # ====================================================
        # GUARDAR JPG
        # ====================================================

        imagen.save(
            ruta_jpg,
            "JPEG",
            quality=100,
            subsampling=0,
        )

        return ruta_jpg

    finally:

        # ====================================================
        # LIMPIEZA
        # ====================================================

        if dc_memoria is not None:
            try:
                dc_memoria.DeleteDC()
            except Exception:
                pass

        if dc_pantalla is not None:
            try:
                dc_pantalla.DeleteDC()
            except Exception:
                pass

        if hdc_pantalla is not None:
            try:
                win32gui.ReleaseDC(
                    0,
                    hdc_pantalla,
                )
            except Exception:
                pass

        if bitmap is not None:
            try:
                win32gui.DeleteObject(
                    bitmap.GetHandle()
                )
            except Exception:
                pass

        if viewer is not None:
            try:
                viewer.Unload()
            except Exception:
                pass

        if hwnd:
            try:
                user32.DestroyWindow(
                    hwnd
                )
            except Exception:
                pass

        if com_inicializado:
            pythoncom.CoUninitialize()


# ============================================================
# BUSCAR ARCHIVOS VISIO
# ============================================================

def obtener_archivos_visio(carpeta):
    return sorted(
        archivo
        for archivo in carpeta.iterdir()
        if archivo.is_file()
        and archivo.suffix.lower() in EXTENSIONES_VISIO
    )


# ============================================================
# CONVERSIÓN INDIVIDUAL
# ============================================================

def convertir_individual():
    print()
    print("=== CONVERSIÓN INDIVIDUAL ===")
    print()

    entrada = input(
        "Nombre, hash o ruta del archivo VSD/VSDX: "
    ).strip().strip('"')

    if not entrada:
        print("No se indicó ningún archivo.")
        return

    ruta = Path(entrada)

    # ========================================================
    # SI NO ES RUTA ABSOLUTA, BUSCAR EN CARPETA DE TOPOLOGÍAS
    # ========================================================

    if not ruta.is_absolute():
        ruta = CARPETA_TOPOLOGIAS / ruta

    # ========================================================
    # SI NO TIENE EXTENSIÓN, BUSCAR .VSD Y .VSDX
    # ========================================================

    if ruta.suffix.lower() not in EXTENSIONES_VISIO:

        candidatos = [
            ruta.with_suffix(".vsd"),
            ruta.with_suffix(".vsdx"),
        ]

        encontrados = [
            archivo
            for archivo in candidatos
            if archivo.exists()
        ]

        if len(encontrados) == 1:
            ruta = encontrados[0]

        elif len(encontrados) > 1:
            print()
            print(
                "Se encontraron ambas versiones:"
            )

            for numero, archivo in enumerate(
                encontrados,
                start=1,
            ):
                print(
                    f"{numero}. {archivo.name}"
                )

            print()

            seleccion = input(
                "Seleccione el archivo: "
            ).strip()

            try:
                indice = int(seleccion) - 1
                ruta = encontrados[indice]

            except (
                ValueError,
                IndexError,
            ):
                print(
                    "Selección no válida."
                )
                return

        else:
            print()
            print(
                "No se encontró el hash como "
                ".vsd ni como .vsdx:"
            )

            print(ruta.name)

            return

    # ========================================================
    # MOSTRAR ARCHIVO ENCONTRADO
    # ========================================================

    print()
    print("Archivo encontrado:")
    print(ruta)

    print()
    print("Convirtiendo a JPG...")

    # ========================================================
    # CONVERTIR
    # ========================================================

    try:
        inicio = time.time()

        jpg = convertir_visio_a_jpg(
            ruta
        )

        duracion = time.time() - inicio

        print()
        print(
            "OK - Conversión completada."
        )

        print(
            f"JPG: {jpg}"
        )

        print(
            f"Tiempo: {duracion:.2f} segundos"
        )

    except Exception as error:
        print()
        print("ERROR:")
        print(error)

# ============================================================
# BARRIDO MASIVO
# ============================================================

def convertir_masivo():
    print()
    print("=== BARRIDO MASIVO ===")
    print()

    archivos = obtener_archivos_visio(
        CARPETA_TOPOLOGIAS
    )

    total = len(archivos)

    if total == 0:
        print(
            "No se encontraron archivos "
            ".vsd o .vsdx."
        )
        return

    print(
        f"Topologías encontradas: {total}"
    )

    print()

    respuesta = input(
        "¿Desea convertirlas todas a JPG? (y/n): "
    ).strip().lower()

    if respuesta != "y":
        print("Operación cancelada.")
        return

    print()

    correctos = 0
    errores = 0

    inicio_total = time.time()

    for numero, archivo in enumerate(
        archivos,
        start=1,
    ):
        print(
            f"[{numero}/{total}] "
            f"{archivo.name}"
        )

        try:
            inicio = time.time()

            jpg = convertir_visio_a_jpg(
                archivo
            )

            duracion = time.time() - inicio

            correctos += 1

            print(
                f"    OK -> {jpg.name}"
            )

            print(
                f"    Tiempo: "
                f"{duracion:.2f} s"
            )

        except Exception as error:
            errores += 1

            print(
                f"    ERROR -> {error}"
            )

        print()

    duracion_total = (
        time.time() - inicio_total
    )

    print("=" * 60)
    print("BARRIDO FINALIZADO")
    print("=" * 60)

    print(
        f"Total encontrados : {total}"
    )

    print(
        f"Convertidos       : {correctos}"
    )

    print(
        f"Errores           : {errores}"
    )

    print(
        f"Tiempo total      : "
        f"{duracion_total:.2f} segundos"
    )


# ============================================================
# MENÚ
# ============================================================

def main():
    while True:
        print()
        print("=" * 60)
        print("VISIO -> JPG")
        print("=" * 60)

        print(
            f"Carpeta: "
            f"{CARPETA_TOPOLOGIAS}"
        )

        print()
        print("1. Convertir un archivo")
        print("2. Barrido masivo")
        print("0. Salir")
        print()

        opcion = input(
            "Seleccione una opción: "
        ).strip()

        if opcion == "1":
            convertir_individual()

        elif opcion == "2":
            convertir_masivo()

        elif opcion == "0":
            print("Saliendo...")
            break

        else:
            print(
                "Opción no válida."
            )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()