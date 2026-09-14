"""Cliente comun para consultas MySQL."""

from typing import Any

import mysql.connector
from mysql.connector import Error

from .config import settings


def crear_conexion():
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        connection_timeout=settings.mysql_connect_timeout,
    )


def consultar_mysql(
    consulta: str,
    parametros: tuple | None = None,
) -> list[dict[str, Any]]:
    conexion = None
    cursor = None

    try:
        conexion = crear_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            consulta,
            parametros or (),
        )

        return cursor.fetchall()

    except Error as exc:
        raise RuntimeError(f"La consulta a MySQL fallo: {exc}") from exc

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()
