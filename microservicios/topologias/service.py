"""Acceso SSH/SFTP a las topologias de OLT almacenadas en el servidor."""

from __future__ import annotations

import hashlib
import mimetypes
import posixpath
import shlex
import stat
import unicodedata
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Iterator

import paramiko

from microservicios.config import settings

CATEGORIAS_OLT = {
    "huawei": "01 - OLT Huawei Topologia",
    "zte": "02 - OLT ZTE Topologia",
    "nokia": "03 - OLT NOKIA Topología",
    "onnet": "04 - OLT ONNET",
    "ftto": "05 - FTTO",
}

EXTENSIONES_PERMITIDAS = {
    ".vsd", ".vsdx", ".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".docx"
}
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png"}
EXTENSIONES_CONVERTIBLES = {".vsd", ".vsdx"}
MAX_ARCHIVOS = 5000
MAX_PROFUNDIDAD = 8


def _normalizar(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.casefold()
    texto = "".join(c if c.isalnum() else " " for c in texto)
    return " ".join(texto.split())


def _categoria(categoria: str) -> str:
    clave = categoria.strip().casefold()
    if clave not in CATEGORIAS_OLT:
        raise ValueError(
            f"Categoria invalida. Use: {', '.join(CATEGORIAS_OLT)}"
        )
    return clave


def _ruta_categoria(categoria: str) -> str:
    clave = _categoria(categoria)
    return posixpath.join(
        settings.topologias_base_path.rstrip("/"),
        CATEGORIAS_OLT[clave],
    )


def _ruta_relativa_segura(ruta: str) -> str:
    valor = ruta.strip().replace("\\", "/")
    if not valor:
        raise ValueError("La ruta del archivo es obligatoria")

    path = PurePosixPath(valor)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Ruta de archivo invalida")

    limpia = posixpath.normpath(str(path))
    if limpia in {"", ".", ".."} or limpia.startswith("../"):
        raise ValueError("Ruta de archivo invalida")
    return limpia


def _ruta_archivo(categoria: str, ruta: str) -> tuple[str, str]:
    relativa = _ruta_relativa_segura(ruta)
    base = _ruta_categoria(categoria)
    completa = posixpath.normpath(posixpath.join(base, relativa))
    if not completa.startswith(base.rstrip("/") + "/"):
        raise ValueError("Ruta fuera de la categoria permitida")
    return completa, relativa


def _conectar_ssh() -> paramiko.SSHClient:
    if not settings.topologias_ssh_host:
        raise RuntimeError("TOPOLOGIAS_SSH_HOST no esta configurado")
    if not settings.topologias_ssh_user:
        raise RuntimeError("TOPOLOGIAS_SSH_USER no esta configurado")
    if not settings.topologias_ssh_password:
        raise RuntimeError("TOPOLOGIAS_SSH_PASSWORD no esta configurado")

    cliente = paramiko.SSHClient()
    if settings.topologias_ssh_strict_host_key:
        cliente.load_system_host_keys()
        cliente.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        cliente.connect(
            hostname=settings.topologias_ssh_host,
            port=settings.topologias_ssh_port,
            username=settings.topologias_ssh_user,
            password=settings.topologias_ssh_password,
            timeout=settings.topologias_ssh_timeout_seconds,
            banner_timeout=settings.topologias_ssh_timeout_seconds,
            auth_timeout=settings.topologias_ssh_timeout_seconds,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:
        cliente.close()
        raise RuntimeError(
            "No se pudo conectar por SSH al servidor de topologias"
        ) from exc
    return cliente


def _iso(timestamp: int | float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _recorrer(
    sftp: paramiko.SFTPClient,
    actual: str,
    base: str,
    profundidad: int = 0,
) -> Iterator[dict[str, Any]]:
    if profundidad > MAX_PROFUNDIDAD:
        return

    try:
        entradas = sftp.listdir_attr(actual)
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer {actual}") from exc

    entradas.sort(key=lambda item: item.filename.casefold())

    for entrada in entradas:
        nombre = entrada.filename
        ruta = posixpath.join(actual, nombre)

        if stat.S_ISDIR(entrada.st_mode):
            yield from _recorrer(sftp, ruta, base, profundidad + 1)
            continue
        if not stat.S_ISREG(entrada.st_mode):
            continue

        extension = PurePosixPath(nombre).suffix.casefold()
        if extension not in EXTENSIONES_PERMITIDAS:
            continue

        relativa = posixpath.relpath(ruta, base)
        yield {
            "nombre": nombre,
            "ruta": relativa,
            "extension": extension,
            "tamano_bytes": int(entrada.st_size),
            "modificado": _iso(entrada.st_mtime),
            "es_imagen": extension in EXTENSIONES_IMAGEN,
            "convertible_a_jpg": extension in EXTENSIONES_CONVERTIBLES,
        }


def menu_topologias() -> dict[str, Any]:
    opciones = []
    for clave, carpeta in CATEGORIAS_OLT.items():
        opciones.append(
            {
                "id": clave,
                "nombre": clave.upper(),
                "carpeta": carpeta,
                "endpoint": f"/api/topologias/olts/{clave}",
            }
        )
    return {"cantidad": len(opciones), "opciones": opciones}


def listar_topologias(
    categoria: str,
    buscar: str = "",
    limite: int = 200,
) -> dict[str, Any]:
    clave = _categoria(categoria)
    termino = _normalizar(buscar)
    limite = max(1, min(int(limite), 1000))
    base = _ruta_categoria(clave)

    cliente = _conectar_ssh()
    sftp = None
    try:
        sftp = cliente.open_sftp()
        datos = []
        revisados = 0

        for archivo in _recorrer(sftp, base, base):
            revisados += 1
            if revisados > MAX_ARCHIVOS:
                break

            if termino:
                buscable = _normalizar(
                    f"{archivo['nombre']} {archivo['ruta']}"
                )
                if termino not in buscable:
                    continue

            datos.append(archivo)
            if len(datos) >= limite:
                break

        return {
            "categoria": clave,
            "carpeta": CATEGORIAS_OLT[clave],
            "buscar": buscar.strip(),
            "cantidad": len(datos),
            "limite": limite,
            "datos": datos,
        }
    finally:
        if sftp is not None:
            sftp.close()
        cliente.close()


def _stat_archivo(
    sftp: paramiko.SFTPClient,
    ruta: str,
) -> paramiko.SFTPAttributes:
    try:
        atributos = sftp.stat(ruta)
    except OSError as exc:
        raise FileNotFoundError("Archivo no encontrado") from exc

    if not stat.S_ISREG(atributos.st_mode):
        raise FileNotFoundError("Archivo no encontrado")
    return atributos


def iterar_archivo(
    categoria: str,
    ruta: str,
    solo_imagen: bool = False,
) -> tuple[Iterator[bytes], dict[str, Any]]:
    remota, relativa = _ruta_archivo(categoria, ruta)
    extension = PurePosixPath(relativa).suffix.casefold()

    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError("Tipo de archivo no permitido")
    if solo_imagen and extension not in EXTENSIONES_IMAGEN:
        raise ValueError("El archivo solicitado no es una imagen")

    cliente = _conectar_ssh()
    sftp = cliente.open_sftp()

    try:
        atributos = _stat_archivo(sftp, remota)
        archivo = sftp.file(remota, "rb")
    except Exception:
        sftp.close()
        cliente.close()
        raise

    def generador() -> Iterator[bytes]:
        try:
            while True:
                bloque = archivo.read(256 * 1024)
                if not bloque:
                    break
                yield bloque
        finally:
            archivo.close()
            sftp.close()
            cliente.close()

    mime, _ = mimetypes.guess_type(relativa)
    return generador(), {
        "nombre": posixpath.basename(relativa),
        "tamano_bytes": int(atributos.st_size),
        "media_type": mime or "application/octet-stream",
    }


def _ejecutar(
    cliente: paramiko.SSHClient,
    comando: str,
    timeout: int,
) -> tuple[int, str]:
    _stdin, stdout, stderr = cliente.exec_command(comando, timeout=timeout)
    error = stderr.read().decode("utf-8", errors="replace").strip()
    codigo = stdout.channel.recv_exit_status()
    return codigo, error


def diagnostico_topologias() -> dict[str, Any]:
    cliente = _conectar_ssh()
    try:
        herramientas = {}
        for nombre, comando in {
            "libreoffice": "command -v libreoffice || command -v soffice",
            "pdftoppm": "command -v pdftoppm",
        }.items():
            _stdin, stdout, _stderr = cliente.exec_command(
                comando,
                timeout=settings.topologias_ssh_timeout_seconds,
            )
            herramientas[nombre] = bool(
                stdout.read().decode("utf-8", errors="replace").strip()
            )

        return {
            "ssh": True,
            "host": settings.topologias_ssh_host,
            "base_path": settings.topologias_base_path,
            "herramientas": herramientas,
            "conversion_jpg_disponible": all(herramientas.values()),
        }
    finally:
        cliente.close()


def convertir_a_jpg(
    categoria: str,
    ruta: str,
) -> dict[str, Any]:
    clave = _categoria(categoria)
    origen, relativa = _ruta_archivo(clave, ruta)
    extension = PurePosixPath(relativa).suffix.casefold()

    if extension not in EXTENSIONES_CONVERTIBLES:
        raise ValueError("Solo se pueden convertir archivos .vsd o .vsdx")

    cliente = _conectar_ssh()
    sftp = None
    try:
        sftp = cliente.open_sftp()
        origen_stat = _stat_archivo(sftp, origen)

        cache_dir = settings.topologias_cache_path.rstrip("/")
        firma = hashlib.sha256(
            f"{clave}:{relativa}".encode("utf-8")
        ).hexdigest()[:24]
        destino = posixpath.join(cache_dir, f"{firma}.jpg")

        try:
            cache_stat = sftp.stat(destino)
            if (
                stat.S_ISREG(cache_stat.st_mode)
                and cache_stat.st_mtime >= origen_stat.st_mtime
            ):
                return {
                    "categoria": clave,
                    "origen": relativa,
                    "cache": destino,
                    "desde_cache": True,
                }
        except OSError:
            pass

        q_cache = shlex.quote(cache_dir)
        q_origen = shlex.quote(origen)
        q_destino = shlex.quote(destino)

        comando = (
            "set -eu; "
            f"mkdir -p {q_cache}; "
            f"TMP_DIR=$(mktemp -d {q_cache}/conv.XXXXXX); "
            "trap 'rm -rf \"$TMP_DIR\"' EXIT; "
            "LO=$(command -v libreoffice || command -v soffice || true); "
            "PPM=$(command -v pdftoppm || true); "
            "[ -n \"$LO\" ] || { echo 'libreoffice no instalado' >&2; exit 41; }; "
            "[ -n \"$PPM\" ] || { echo 'pdftoppm no instalado' >&2; exit 42; }; "
            f"\"$LO\" --headless --convert-to pdf --outdir \"$TMP_DIR\" "
            f"{q_origen} >/dev/null 2>&1; "
            "PDF=$(find \"$TMP_DIR\" -maxdepth 1 -type f -name '*.pdf' "
            "-print -quit); "
            "[ -n \"$PDF\" ] || { echo 'no se genero PDF' >&2; exit 43; }; "
            "\"$PPM\" -jpeg -f 1 -singlefile -r 150 \"$PDF\" "
            "\"$TMP_DIR/render\" >/dev/null 2>&1; "
            "[ -f \"$TMP_DIR/render.jpg\" ] || "
            "{ echo 'no se genero JPG' >&2; exit 44; }; "
            f"mv \"$TMP_DIR/render.jpg\" {q_destino}; "
            f"chmod 600 {q_destino}"
        )

        codigo, error = _ejecutar(
            cliente,
            comando,
            settings.topologias_conversion_timeout_seconds,
        )
        if codigo != 0:
            raise RuntimeError(
                "No se pudo convertir la topologia a JPG: "
                + (error or f"codigo {codigo}")
            )

        return {
            "categoria": clave,
            "origen": relativa,
            "cache": destino,
            "desde_cache": False,
        }
    finally:
        if sftp is not None:
            sftp.close()
        cliente.close()


def iterar_jpg_convertido(
    categoria: str,
    ruta: str,
) -> tuple[Iterator[bytes], dict[str, Any]]:
    conversion = convertir_a_jpg(categoria, ruta)
    remota = str(conversion["cache"])

    cliente = _conectar_ssh()
    sftp = cliente.open_sftp()
    try:
        atributos = _stat_archivo(sftp, remota)
        archivo = sftp.file(remota, "rb")
    except Exception:
        sftp.close()
        cliente.close()
        raise

    nombre = PurePosixPath(str(conversion["origen"])).stem + ".jpg"

    def generador() -> Iterator[bytes]:
        try:
            while True:
                bloque = archivo.read(256 * 1024)
                if not bloque:
                    break
                yield bloque
        finally:
            archivo.close()
            sftp.close()
            cliente.close()

    return generador(), {
        "nombre": nombre,
        "tamano_bytes": int(atributos.st_size),
        "desde_cache": conversion["desde_cache"],
    }
