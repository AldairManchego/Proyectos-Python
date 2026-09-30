import pandas as pd
import numpy as np
import os, sys
from datetime import datetime
from pathlib import Path

from routes.Paths import Ruta_crm

from utils.Data_CRM.b_limpieza_columnas import (
    _limpiar_columnas_crm,
    _clasificar_canal,
    _normalizar_fechas_numeros,
)

from utils.Data_CRM.c_calculo_FCR import (
    _cruzar_arbol_tipificacion,
    _calcular_fcr,
)

from utils.Data_CRM.d_calculo_gestion import (
    _calcular_dias_cierre,
    _calcular_estado_gestion_abiertos,
    _calcular_grupo_dias_cierre,
)

from utils.Processing_data_comentarios import _transformacion_comentarios
from utils.functions import load_files_from_folder

def _enriquecer_con_fuentes(
    df_crm: pd.DataFrame,
    df_contactos: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_master: pd.DataFrame,
    df_comentarios: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza el CRM con contact search, OPL y master skill."""

    df_crm["ID_LLAMADA_DE_CONTACTO"] = df_crm["ID_LLAMADA_DE_CONTACTO"].str.lower()

    df_crm = df_crm.merge(
        df_contactos[["id de contacto", "agente", "duracion del contacto"]],
        how="left",
        left_on="ID_LLAMADA_DE_CONTACTO",
        right_on="id de contacto",
    ).drop(columns=["id de contacto"])

    df_crm = df_crm.merge(
        df_opl[["Nombre_Agente", "Correo_contratista"]],
        how="left",
        left_on="NOMBRE_ASESOR",
        right_on="Nombre_Agente",
    ).drop(columns=["Nombre_Agente"])

    df_crm["agente"] = df_crm["agente"].combine_first(df_crm["Correo_contratista"])
    df_crm = df_crm.drop(columns=["Correo_contratista"])

    df_crm = df_crm.merge(
        df_opl[["Id_opl", "Correo_contratista"]],
        how="left",
        left_on="agente",
        right_on="Correo_contratista",
    ).drop(columns=["Correo_contratista"])

    df_master = df_master.copy()
    df_master["Colas"] = df_master["Colas"].str.title()

    df_crm = df_crm.merge(
        df_master[["IdMasterSkill", "Canal", "Colas"]],
        how="left",
        left_on=["CANAL_DE_ATENCIÓN", "SKILL"],
        right_on=["Canal", "Colas"],
    ).drop(columns=["Canal", "Colas"])

    df_crm = df_crm.merge(
        df_comentarios[[
            "RADICADO_COMENTARIO",
            "COMENTARIO",
            "SOLUCION",
            "FECHA_COMENTARIO",
            "NUMERO_PEDIDO",
            "FECHA_ULTIMO_CAMBIO",
            "NOMBRE_ULTIMO_CAMBIO"
        ]],
        how="left",
        left_on=["RADICADO"],
        right_on=["RADICADO_COMENTARIO"]
    ).drop(columns=["RADICADO_COMENTARIO"])

    return df_crm

def _calcular_dias_desde_comentario(
    df_crm: pd.DataFrame,
    today: pd.Timestamp
) -> pd.DataFrame:

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    fecha_comentario = pd.to_datetime(
        df_crm["FECHA_COMENTARIO"],
        errors="coerce",
        utc=True
    ).dt.tz_localize(None)

    fecha_inicio = pd.to_datetime(df_crm["FECHA_DE_INICIO"], errors="coerce")

    fecha_base = (fecha_comentario.fillna(fecha_inicio).dt.normalize())

    dias_transcurridos = (pd.Timestamp(today).normalize() - fecha_base).dt.days

    df_crm["DIAS_DESDE_COMENTARIO"] = dias_transcurridos.where(
        mask_sin_fin,
        pd.NA
    )

    return df_crm

def _calcular_grupo_dias_comentario(
    df_crm: pd.DataFrame
) -> pd.DataFrame:

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    dias = pd.to_numeric(
        df_crm["DIAS_DESDE_COMENTARIO"],
        errors="coerce"
    )

    condiciones = [
        dias <= 1,
        dias <= 3,
        dias <= 5,
        dias <= 7,
        dias <= 10,
        dias <= 15,
    ]

    resultados = [
        "0 - 1 Día",
        "2 - 3 Días",
        "4 - 5 Días",
        "6 - 7 Días",
        "8 - 10 Días",
        "11 - 15 Días",
    ]

    df_crm["GRUPO_DIAS_COMENTARIO"] = np.where(
        mask_sin_fin,
        np.select(condiciones, resultados, default=">15 Días"),
        pd.NA
    )

    return df_crm

def transform_crm(
    df_crm: pd.DataFrame,
    df_arbol: pd.DataFrame,
    df_festivos: np.ndarray,
    df_contactos: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_master: pd.DataFrame,
    df_comentarios: pd.DataFrame,
    today: pd.Timestamp | None = None,
) -> pd.DataFrame:

    if today is None:
        today = pd.Timestamp.today().normalize()

    # Limpieza
    df_crm = _limpiar_columnas_crm(df_crm)
    df_crm = _clasificar_canal(df_crm)
    df_crm = _normalizar_fechas_numeros(df_crm)

    # FCR
    df_crm = _cruzar_arbol_tipificacion(
        df_crm,
        df_arbol
    )

    df_crm = _calcular_fcr(df_crm)

    # Gestión
    df_crm = _calcular_dias_cierre(
        df_crm,
        df_festivos,
        today
    )

    df_crm = _calcular_estado_gestion_abiertos(
        df_crm,
        df_festivos,
        today
    )

    df_crm = _calcular_grupo_dias_cierre(
        df_crm,
        today
    )

    # Enriquecimiento
    df_crm = _enriquecer_con_fuentes(
        df_crm,
        df_contactos,
        df_opl,
        df_master,
        df_comentarios
    )

# Calculos dis sin toque, fecha comentario
    df_crm = _calcular_dias_desde_comentario(
        df_crm,
        today
    )

    df_crm = _calcular_grupo_dias_comentario(
        df_crm
    )    

    # Ajustes finales
    df_crm = df_crm.rename(
        columns={
            "ANS_Dias": "ANS_DIAS",
            "Tipo_Dia": "TIPO_DIA",
            "agente": "CORREO_AGENTE",
            "duracion del contacto": "DURACION_CONTACTO",
        }
    )

    df_crm["HORA_INICIO"] = (
        df_crm["FECHA_DE_INICIO"]
        .dt.time
    )

    return df_crm


def guardar_crm(
    df_crm: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "04.Data_CRM.csv",
) -> None:
    """Guarda el CRM final como CSV en ambas rutas (global y local)."""

    df_crm.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_crm.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")