"""Acceso bajo demanda a topologias OLT por SSH/SFTP."""

import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from threading import RLock
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
PREFIJOS_CATEGORIA = {
    "HAC": "huawei",
    "ZAC": "zte",
    "NAC": "nokia",
    "OH": "onnet",
}
EXTENSIONES = {".vsd", ".vsdx", ".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".docx"}
IMAGENES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
VISIO = {".vsd", ".vsdx"}
CACHEABLES = VISIO | set(IMAGENES)
TIPOS_ARCHIVO = {**IMAGENES, ".vsd": "application/vnd.visio", ".vsdx": "application/vnd.ms-visio.drawing"}
PATRON_CACHE = re.compile(r"[0-9a-f]{64}\.(?:vsd|vsdx|jpg|jpeg|png)")
_INDICE_LOCK = RLock()
_PROYECTO = Path(__file__).resolve().parents[3]


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


def detectar_categoria_por_prefijo(texto: str) -> str | None:
    normalizado = _normalizar(texto).upper().strip()
    primero = re.split(r"[-\s_/]", normalizado, maxsplit=1)[0]
    if primero in PREFIJOS_CATEGORIA:
        return PREFIJOS_CATEGORIA[primero]
    prefijos = "|".join(re.escape(prefijo) for prefijo in PREFIJOS_CATEGORIA)
    coincidencia = re.search(rf"(?<![A-Z0-9])({prefijos})-", normalizado)
    if coincidencia:
        return PREFIJOS_CATEGORIA[coincidencia.group(1)]
    return None


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
    limpiar_cache_expirada()
    data = {"ssh": False, "ruta": False, "data_dir": False,
            "temporales_dir": False, "imagenes_dir": False}
    try:
        raiz, imagenes, temporales, _ = _directorios_locales()
        data.update(data_dir=raiz.is_dir(), temporales_dir=temporales.is_dir(),
                    imagenes_dir=imagenes.is_dir())
    except TopologiasError:
        pass
    try:
        with conexion() as (_, sftp):
            data["ssh"] = True
            try:
                base = sftp.normalize(settings.topologias_base_path)
                data["ruta"] = stat.S_ISDIR(sftp.stat(base).st_mode)
            except OSError:
                pass
    except TopologiasError:
        pass
    return data


def _buscar_en_sftp(
    sftp: paramiko.SFTPClient, categoria: str, texto: str, limite: int,
    incluir_categoria: bool = False,
) -> list[dict]:
    consulta = _normalizar(texto)
    resultados: list[dict] = []
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
                        item = {
                            "nombre": nombre,
                            "ruta": relativa,
                            "extension": extension,
                            "tamano_bytes": entrada.st_size,
                        }
                        if incluir_categoria:
                            item["categoria"] = categoria
                        resultados.append(item)
                        if len(resultados) >= limite:
                            break
    except OSError as exc:
        raise TopologiasError("No se pudo consultar el servidor de topologias", 503) from exc
    return resultados


def buscar(categoria: str, texto: str, limite: int) -> dict:
    _categoria(categoria)
    limpiar_cache_expirada()
    with conexion() as (_, sftp):
        resultados = _buscar_en_sftp(sftp, categoria, texto, limite)
    return {"categoria": categoria, "buscar": texto, "cantidad": len(resultados), "datos": resultados}


def buscar_global(texto: str, limite: int) -> dict:
    if not texto.strip():
        raise TopologiasError("Texto de busqueda requerido", 400)
    limpiar_cache_expirada()
    detectada = detectar_categoria_por_prefijo(texto)
    categorias = (detectada,) if detectada else tuple(CATEGORIAS)
    resultados: list[dict] = []
    with conexion() as (_, sftp):
        for categoria in categorias:
            resultados.extend(_buscar_en_sftp(sftp, categoria, texto,
                                              limite - len(resultados), True))
            if len(resultados) >= limite:
                break
    return {"buscar": texto, "cantidad": len(resultados), "datos": resultados}


def _rutas_locales() -> tuple[Path, Path, Path, Path]:
    raiz = Path(settings.topologias_local_dir).expanduser()
    if not raiz.is_absolute():
        raiz = _PROYECTO / raiz
    raiz = raiz.resolve()
    return raiz, raiz / "imagenes", raiz / "temporales", raiz / "topologias.json"


def _directorios_locales() -> tuple[Path, Path, Path, Path]:
    rutas = _rutas_locales()
    try:
        for carpeta in rutas[:3]:
            if carpeta.is_symlink():
                raise TopologiasError("Almacenamiento local de topologias no disponible", 503)
            carpeta.mkdir(parents=True, exist_ok=True)
        with _INDICE_LOCK:
            if not rutas[3].exists():
                guardar_indice({"topologias": []})
    except OSError as exc:
        raise TopologiasError("Almacenamiento local de topologias no disponible", 503) from exc
    return rutas


def cargar_indice() -> dict:
    with _INDICE_LOCK:
        indice = _directorios_locales()[3]
        try:
            with indice.open("r", encoding="utf-8") as archivo:
                contenido = json.load(archivo)
            if not isinstance(contenido, dict) or not isinstance(contenido.get("topologias"), list):
                raise ValueError("Indice invalido")
            return contenido
        except (OSError, ValueError) as exc:
            raise TopologiasError("Indice local de topologias no disponible", 503) from exc


def guardar_indice(data: dict) -> None:
    with _INDICE_LOCK:
        indice = _rutas_locales()[3]
        temporal = indice.with_suffix(".tmp")
        try:
            indice.parent.mkdir(parents=True, exist_ok=True)
            with temporal.open("w", encoding="utf-8") as archivo:
                json.dump(data, archivo, ensure_ascii=False, indent=2)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, indice)
        except OSError as exc:
            raise TopologiasError("No se pudo guardar el indice de topologias", 503) from exc
        finally:
            temporal.unlink(missing_ok=True)


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def limpiar_cache_expirada() -> None:
    with _INDICE_LOCK:
        _, imagenes, _, _ = _directorios_locales()
        indice = cargar_indice()
        vigentes = []
        referenciadas = set()
        cambio = False
        ahora = ahora_utc()
        ttl_horas = settings.topologias_cache_ttl_horas
        if ttl_horas <= 0:
            raise TopologiasError("TTL de topologias invalido", 503)
        ttl = timedelta(hours=ttl_horas)
        for registro in indice["topologias"]:
            if not isinstance(registro, dict):
                cambio = True
                continue
            archivo_relativo = registro.get("archivo") or registro.get("imagen", "")
            nombre = (archivo_relativo.removeprefix("imagenes/")
                      if isinstance(archivo_relativo, str) and archivo_relativo.startswith("imagenes/") else "")
            extension_origen = str(registro.get("extension_origen") or
                                   posixpath.splitext(registro.get("ruta_remota", ""))[1]).lower()
            if (not PATRON_CACHE.fullmatch(nombre) or extension_origen not in CACHEABLES
                    or posixpath.splitext(nombre)[1] != extension_origen
                    or not str(registro.get("enlace", "")).endswith("/" + nombre)):
                cambio = True
                continue
            archivo = imagenes / nombre
            if archivo.is_symlink() or not archivo.is_file():
                cambio = True
                continue
            if registro.get("archivo") != f"imagenes/{nombre}" or "imagen" in registro:
                registro["archivo"] = f"imagenes/{nombre}"
                registro.pop("imagen", None)
                cambio = True
            fecha = None
            valor = registro.get("creado_en")
            if isinstance(valor, str):
                try:
                    fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
                    if fecha.tzinfo is None:
                        fecha = None
                except ValueError:
                    pass
            if fecha is None:
                # Índices anteriores a este cambio usan la fecha del archivo local.
                fecha = datetime.fromtimestamp(archivo.stat().st_mtime, timezone.utc)
                registro["creado_en"] = fecha.isoformat().replace("+00:00", "Z")
                cambio = True
            if fecha > ahora:
                fecha = ahora
                registro["creado_en"] = ahora.isoformat().replace("+00:00", "Z")
                cambio = True
            if ahora - fecha > ttl:
                cambio = True
                continue
            vigentes.append(registro)
            referenciadas.add(nombre)
        if cambio:
            indice["topologias"] = vigentes
            guardar_indice(indice)
        try:
            for archivo in imagenes.iterdir():
                if (archivo.is_file() or archivo.is_symlink()) and archivo.name not in referenciadas:
                    if PATRON_CACHE.fullmatch(archivo.name):
                        archivo.unlink()
        except OSError as exc:
            raise TopologiasError("No se pudo limpiar el cache de topologias", 503) from exc


def extraer_nombre_olt(nombre_archivo: str) -> str:
    nombre = Path(nombre_archivo).stem
    prefijos = "|".join(re.escape(prefijo) for prefijo in PREFIJOS_CATEGORIA)
    coincidencia = re.search(rf"(?<![A-Z0-9])(?:{prefijos})-[A-Z0-9._-]+", nombre, re.IGNORECASE)
    return coincidencia.group(0).rstrip("._-") if coincidencia else nombre


def _descargar(sftp: paramiko.SFTPClient, remoto: str, local: Path) -> None:
    try:
        with sftp.open(remoto, "rb") as origen, local.open("wb") as destino:
            shutil.copyfileobj(origen, destino, length=1024 * 1024)
    except OSError as exc:
        raise TopologiasError("No se pudo descargar la topologia", 502) from exc


def _respuesta_materializada(registro: dict, desde_cache: bool) -> dict:
    return {
        "olt": registro["olt"],
        "categoria": registro["categoria"],
        "ruta_remota": registro["ruta_remota"],
        "archivo_origen": registro["archivo_origen"],
        "enlace": registro["enlace"],
        "desde_cache": desde_cache,
    }


def materializar_topologia(categoria: str, ruta: str) -> dict:
    _categoria(categoria)
    relativa = _ruta_relativa(ruta)
    extension = posixpath.splitext(relativa)[1].lower()
    if extension not in CACHEABLES:
        raise TopologiasError("Este tipo de archivo no se almacena en cache", 400)
    _, imagenes, temporales, _ = _directorios_locales()
    with _INDICE_LOCK:
        limpiar_cache_expirada()
        clave = hashlib.sha256(f"{categoria}/{relativa}".encode("utf-8")).hexdigest()
        archivo_nombre = clave + extension
        archivo = imagenes / archivo_nombre
        indice = cargar_indice()
        registros = indice["topologias"]
        anterior = next((r for r in registros if r.get("categoria") == categoria
                         and r.get("ruta_remota") == relativa), None)
        if (anterior and anterior.get("archivo") == f"imagenes/{archivo_nombre}"
                and archivo.is_file() and not archivo.is_symlink()):
            return _respuesta_materializada(anterior, True)
        with conexion() as (_, sftp):
            remoto, datos, _ = archivo_validado(sftp, categoria, relativa)
            tamano = int(datos.st_size)
            mtime = int(datos.st_mtime)

            temporal = temporales / f"{clave}-{uuid.uuid4().hex}{extension}"
            try:
                _descargar(sftp, remoto, temporal)
                os.replace(temporal, archivo)
            except OSError as exc:
                raise TopologiasError("No se pudo guardar el archivo local", 503) from exc
            finally:
                temporal.unlink(missing_ok=True)

            registro = {
                "olt": extraer_nombre_olt(posixpath.basename(relativa)),
                "categoria": categoria,
                "archivo_origen": posixpath.basename(relativa),
                "ruta_remota": relativa,
                "archivo": f"imagenes/{archivo_nombre}",
                "enlace": f"{settings.topologias_public_base.rstrip('/')}/{archivo_nombre}",
                "extension_origen": extension,
                "tamano_remoto": tamano,
                "mtime_remoto": mtime,
                "creado_en": ahora_utc().isoformat().replace("+00:00", "Z"),
            }
            indice["topologias"] = [r for r in registros if not (
                r.get("categoria") == categoria and r.get("ruta_remota") == relativa)] + [registro]
            guardar_indice(indice)
            return _respuesta_materializada(registro, False)


def archivo_local(nombre: str) -> Path:
    limpiar_cache_expirada()
    if not PATRON_CACHE.fullmatch(nombre):
        raise TopologiasError("Archivo no encontrado", 404)
    raiz, imagenes, _, _ = _rutas_locales()
    destino = imagenes / nombre
    if (imagenes.is_symlink() or imagenes.resolve().parent != raiz
            or destino.is_symlink() or not destino.is_file()
            or destino.resolve().parent != imagenes.resolve()):
        raise TopologiasError("Archivo no encontrado", 404)
    if not any(r.get("archivo") == f"imagenes/{nombre}" for r in cargar_indice()["topologias"]):
        raise TopologiasError("Archivo no encontrado", 404)
    return destino
