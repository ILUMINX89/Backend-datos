"""Acceso bajo demanda a topologias OLT por SSH/SFTP."""

import hashlib
import posixpath
import shlex
import stat
import unicodedata
from contextlib import contextmanager
from pathlib import PurePosixPath
from typing import Iterator

import paramiko

from microservicios.config import settings


CATEGORIAS = {
    "huawei": "01 - OLT Huawei Topologia",
    "zte": "02 - OLT ZTE Topologia",
    "nokia": "03 - OLT NOKIA Topología",
    "onnet": "04 - OLT ONNET",
    "ftto": "05 - FTTO",
}
EXTENSIONES = {".vsd", ".vsdx", ".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".docx"}
IMAGENES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


class TopologiasError(Exception):
    def __init__(self, mensaje: str, estado: int = 500):
        self.mensaje = mensaje
        self.estado = estado
        super().__init__(mensaje)


def _normalizar(texto: str) -> str:
    return "".join(
        caracter for caracter in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caracter)
    )


def _categoria(categoria: str) -> str:
    if categoria not in CATEGORIAS:
        raise TopologiasError("Categoria invalida", 400)
    return CATEGORIAS[categoria]


def _ruta_relativa(ruta: str) -> str:
    if not ruta or "\\" in ruta or "\x00" in ruta:
        raise TopologiasError("Ruta invalida", 400)
    partes = PurePosixPath(ruta)
    if partes.is_absolute() or any(p in {".", "..", ""} for p in ruta.split("/")):
        raise TopologiasError("Ruta invalida", 400)
    if any(p.startswith(".") for p in partes.parts):
        raise TopologiasError("Ruta invalida", 400)
    return str(partes)


@contextmanager
def conexion() -> Iterator[tuple[paramiko.SSHClient, paramiko.SFTPClient]]:
    if not settings.topologias_ssh_password:
        raise TopologiasError("No se pudo conectar al servidor de topologias", 503)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=settings.topologias_ssh_host,
            port=settings.topologias_ssh_port,
            username=settings.topologias_ssh_user,
            password=settings.topologias_ssh_password,
            timeout=settings.topologias_ssh_timeout_seconds,
            auth_timeout=settings.topologias_ssh_timeout_seconds,
            banner_timeout=settings.topologias_ssh_timeout_seconds,
            look_for_keys=False,
            allow_agent=False,
        )
        sftp = ssh.open_sftp()
    except (OSError, EOFError, paramiko.SSHException) as exc:
        ssh.close()
        raise TopologiasError("No se pudo conectar al servidor de topologias", 503) from exc
    try:
        yield ssh, sftp
    finally:
        sftp.close()
        ssh.close()


def _directorio_categoria(sftp: paramiko.SFTPClient, categoria: str) -> str:
    carpeta = _categoria(categoria)
    try:
        base = sftp.normalize(settings.topologias_base_path)
        if not stat.S_ISDIR(sftp.stat(base).st_mode):
            raise TopologiasError("Ruta de topologias no disponible", 503)
        destino = sftp.normalize(posixpath.join(base, carpeta))
        if posixpath.dirname(destino) != base or not stat.S_ISDIR(sftp.stat(destino).st_mode):
            raise TopologiasError("Ruta de topologias no disponible", 503)
    except OSError as exc:
        raise TopologiasError("Ruta de topologias no disponible", 503) from exc
    return destino


def archivo_validado(sftp: paramiko.SFTPClient, categoria: str, ruta: str):
    raiz = _directorio_categoria(sftp, categoria)
    relativa = _ruta_relativa(ruta)
    extension = posixpath.splitext(relativa)[1].lower()
    if extension not in EXTENSIONES:
        raise TopologiasError("Tipo de archivo no permitido", 400)
    try:
        destino = sftp.normalize(posixpath.join(raiz, relativa))
    except OSError as exc:
        raise TopologiasError("Archivo no encontrado", 404) from exc
    if not destino.startswith(raiz + "/"):
        raise TopologiasError("Ruta invalida", 400)
    try:
        datos = sftp.stat(destino)
    except OSError as exc:
        raise TopologiasError("Archivo no encontrado", 404) from exc
    if not stat.S_ISREG(datos.st_mode):
        raise TopologiasError("Archivo no encontrado", 404)
    return destino, datos, extension


def estado() -> dict:
    with conexion() as (_, sftp):
        try:
            base = sftp.normalize(settings.topologias_base_path)
            disponible = stat.S_ISDIR(sftp.stat(base).st_mode)
        except OSError:
            disponible = False
    return {"ssh": True, "ruta": disponible}


def buscar(categoria: str, texto: str, limite: int) -> dict:
    _categoria(categoria)
    consulta = _normalizar(texto)
    resultados = []
    with conexion() as (_, sftp):
        try:
            raiz = _directorio_categoria(sftp, categoria)
            pendientes = [(raiz, "")]
            while pendientes and len(resultados) < limite:
                directorio, relativa_dir = pendientes.pop()
                for entrada in sftp.listdir_attr(directorio):
                    nombre = entrada.filename
                    if nombre.startswith("."):
                        continue
                    relativa = posixpath.join(relativa_dir, nombre)
                    if stat.S_ISDIR(entrada.st_mode):
                        pendientes.append((posixpath.join(directorio, nombre), relativa))
                    elif stat.S_ISREG(entrada.st_mode):
                        extension = posixpath.splitext(nombre)[1].lower()
                        if extension in EXTENSIONES and consulta in _normalizar(nombre):
                            resultados.append({
                                "nombre": nombre,
                                "ruta": relativa,
                                "extension": extension,
                                "tamano_bytes": entrada.st_size,
                            })
                            if len(resultados) >= limite:
                                break
        except OSError as exc:
            raise TopologiasError("No se pudo consultar el servidor de topologias", 503) from exc
    return {"categoria": categoria, "buscar": texto, "cantidad": len(resultados), "datos": resultados}


def _comando(ssh: paramiko.SSHClient, comando: str) -> bool:
    _, stdout, stderr = ssh.exec_command(comando, timeout=120)
    try:
        return stdout.channel.recv_exit_status() == 0
    finally:
        stdout.close()
        stderr.close()


def herramientas_conversion() -> dict[str, bool]:
    with conexion() as (ssh, _):
        return {
            "libreoffice": _comando(ssh, "command -v libreoffice >/dev/null 2>&1 || command -v soffice >/dev/null 2>&1"),
            "pdftoppm": _comando(ssh, "command -v pdftoppm >/dev/null 2>&1"),
        }


def jpg_cacheado(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient, categoria: str, ruta: str) -> str:
    origen, datos, extension = archivo_validado(sftp, categoria, ruta)
    if extension not in {".vsd", ".vsdx"}:
        raise TopologiasError("Se requiere un archivo VSD o VSDX", 400)
    cache = settings.topologias_cache_path.rstrip("/")
    if not cache.startswith("/") or ".." in PurePosixPath(cache).parts:
        raise TopologiasError("Cache de topologias no disponible", 503)
    clave = hashlib.sha256(f"{categoria}/{ruta}".encode("utf-8")).hexdigest()
    destino = posixpath.join(cache, clave + ".jpg")
    try:
        if sftp.stat(destino).st_mtime >= datos.st_mtime:
            return destino
    except OSError:
        pass
    disponible = herramientas_conversion_en_sesion(ssh)
    if not all(disponible.values()):
        raise TopologiasError("Conversion JPG no disponible en el servidor", 503)
    q = shlex.quote
    pdf_nombre = posixpath.splitext(posixpath.basename(origen))[0] + ".pdf"
    # Cada conversion usa un directorio temporal propio; el original nunca se modifica.
    comando = (
        "set -e; "
        f"mkdir -p -- {q(cache)}; "
        f"tmp=$(mktemp -d {q(posixpath.join(cache, '.conversion-XXXXXXXX'))}); "
        "trap 'rm -rf -- \"$tmp\"' EXIT; "
        f"pdf_nombre={q(pdf_nombre)}; "
        f"(command -v libreoffice >/dev/null 2>&1 && libreoffice || soffice) "
        f"-env:UserInstallation=file://\"$tmp\"/lo-profile --headless --convert-to pdf "
        f"--outdir \"$tmp\" {q(origen)} >/dev/null 2>&1; "
        f"pdftoppm -f 1 -l 1 -singlefile -jpeg -r 150 "
        f"\"$tmp/$pdf_nombre\" "
        f"\"$tmp/page\" >/dev/null 2>&1; "
        f"mv -f -- \"$tmp/page.jpg\" {q(destino)}"
    )
    if not _comando(ssh, comando):
        raise TopologiasError("No se pudo convertir la topologia a JPG", 502)
    return destino


def herramientas_conversion_en_sesion(ssh: paramiko.SSHClient) -> dict[str, bool]:
    return {
        "libreoffice": _comando(ssh, "command -v libreoffice >/dev/null 2>&1 || command -v soffice >/dev/null 2>&1"),
        "pdftoppm": _comando(ssh, "command -v pdftoppm >/dev/null 2>&1"),
    }
