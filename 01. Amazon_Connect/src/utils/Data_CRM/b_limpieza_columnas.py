import csv
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode
from routes.Paths import Ruta_crm

REQUIRE_COLUMNS = {
    "RADICADO",
    "PRODUCTO",
    "TIPO",
    "SUBTIPO",
    "ID_LLAMADA_DE_CONTACTO",
    "SE_RESOLVIÓ_EL_CONTACTO",
    "MOTIVO_NO_FCR",
    "NOMBRE_ALIADO",
    "FECHA_DE_INICIO",
    "FECHA_FIN",
}

COLUMNAS_CRM = [
    "RADICADO",
    "ESTADO",
    "TIPO_PRI",
    "PRODUCTO",
    "TIPO",
    "SUBTIPO",
    "NÚMERO_CUENTA",
    "TIPO_DE_LLAMADA",
    "ES_CLIENTE_APP",
    "NÚMERO_DOCUMENTO_DEL_CLIENTE",
    "NOMBRE_CLIENTE",
    "NOMBRE_ALIADO",
    "NOMBRE_DE_AGENTE_ASIGNADO_AL_CASO",
    "FECHA_DE_INICIO",
    "FECHA_FIN",
    "EN_DIAS",
    "SLA_DIAS",
    "VALOR_PUNTOS",
    "VALOR_DINERO",
    "MONTO_MÍNIMO",
    "CANAL_DE_ATENCIÓN",
    "ESTADO_GESTIÓN",
    "NÚMERO_PEDIDO",
    "NOMBRE_ASESOR",
    "DEVOLUCIÓN",
    "SE_RESOLVIÓ_EL_CONTACTO",
    "MOTIVO_NO_FCR",
    "CONTACTO_DE_CLIENTE",
    "ID_LLAMADA_DE_CONTACTO",
    "NO_TICKET",
    "OFRECIMIENTO_EFECTIVO",
    "SKILL",
    "PROMESA_DE_VENTA",
    "MOTIVO_NO_ACEPTACIÓN",
    "FECHA_ÚLTIMO_CAMBIO",
    "MÉTODO_DE_APROBACIÓN_DE_VALIDACIÓN",
    "CÓDIGO_DE_VALIDACIÓN",
    "FILE_NAME",
    "CREATION_FILE_DATE",
]

COLUMNAS_FECHA = [
    "FECHA_DE_INICIO",
    "FECHA_FIN",
    "FECHA_ÚLTIMO_CAMBIO",
    "CREATION_FILE_DATE",
]

COLUMNAS_NUMERO = [
    "EN_DIAS",
    "SLA_DIAS",
    "VALOR_PUNTOS",
    "VALOR_DINERO",
]

EXCLUIR_REGISTROS = ["CHAT DE PRUEBA", "LLAMADA DE PRUEBA", "PRUEBAS PCO"]


def _limpiar_columnas_crm(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Filtra pruebas, selecciona columnas, normaliza texto y renombra niveles."""

    df_crm = df_crm[~df_crm["SUBTIPO"].isin(EXCLUIR_REGISTROS)]
    df_crm = df_crm[COLUMNAS_CRM]

    for col in COLUMNAS_CRM:
        df_crm[col] = (
            df_crm[col]
            .astype("string")
            .str.strip()
            .map(lambda x: unidecode(x) if pd.notna(x) else x)
            .str.title()
        )

    df_crm = df_crm.rename(
        columns={
            "PRODUCTO": "NIVEL_1",
            "TIPO": "NIVEL_2",
            "SUBTIPO": "NIVEL_3",
        }
    )
    return df_crm


def _clasificar_canal(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Agrupa CANAL_DE_ATENCIÓN en Chat / Voz / Correo / Otros."""

    condiciones_canal = [
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Whatsapp", "Chat", "Pagina Web"]),
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Telefonico"]),
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Correo Electronico"]),
    ]
    resultado_canal = ["Chat", "Voz", "Correo"]

    df_crm["CANAL_DE_ATENCIÓN"] = np.select(
        condiciones_canal, resultado_canal, default="Otros"
    )
    return df_crm


def _normalizar_fechas_numeros(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas de fecha y de número a sus tipos correctos."""

    for col in COLUMNAS_FECHA:
        df_crm[col] = pd.to_datetime(
            df_crm[col], utc=True, errors="coerce"
        ).dt.tz_localize(None)

    for col in COLUMNAS_NUMERO:
        df_crm[col] = pd.to_numeric(df_crm[col], errors="coerce").fillna(0).astype("int")

    df_crm["START_DATE"] = df_crm["FECHA_DE_INICIO"].dt.date
    df_crm["END_DATE"] = df_crm["FECHA_FIN"].dt.date

    return df_crm