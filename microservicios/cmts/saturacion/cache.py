"""Cache JSON atomico para la saturacion HFC."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
DIRECTORIO_CACHE = RAIZ_PROYECTO / "data" / "cache"
ARCHIVO_SATURACION = DIRECTORIO_CACHE / "hfc_saturacion.json"
ARCHIVO_ESTADO = DIRECTORIO_CACHE / "hfc_estado.json"

SATURACION_INICIAL: dict[str, Any] = {
    "generado_en": None, "ventana": "4d", "datos": []
}
ESTADO_INICIAL: dict[str, Any] = {
    "estado": "listo", "iniciado_en": None, "finalizado_en": None, "error": None
}


def _leer(ruta: Path, predeterminado: dict[str, Any]) -> dict[str, Any]:
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return dict(predeterminado)
    return contenido if isinstance(contenido, dict) else dict(predeterminado)


def _guardar_atomico(ruta: Path, contenido: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal: Path | None = None
    try:
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=ruta.parent, prefix=f".{ruta.name}.",
            suffix=".tmp", delete=False
        ) as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
            archivo.flush()
            os.fsync(archivo.fileno())
            temporal = Path(archivo.name)
        temporal.replace(ruta)
    finally:
        if temporal is not None and temporal.exists():
            temporal.unlink()


def leer_saturacion() -> dict[str, Any]:
    return _leer(ARCHIVO_SATURACION, SATURACION_INICIAL)


def guardar_saturacion(contenido: dict[str, Any]) -> None:
    _guardar_atomico(ARCHIVO_SATURACION, contenido)


def leer_estado() -> dict[str, Any]:
    return _leer(ARCHIVO_ESTADO, ESTADO_INICIAL)


def guardar_estado(contenido: dict[str, Any]) -> None:
    _guardar_atomico(ARCHIVO_ESTADO, contenido)
