import csv
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode
from routes.Paths import Ruta_crm

def _calcular_dias_cierre(
    df_crm: pd.DataFrame,
    df_festivos: np.ndarray,
    today: pd.Timestamp,
) -> pd.DataFrame:
    """
    Calcula los días de cierre y cumplimiento para:
    - ANS (PRI)
    - SLA (Cliente)
    """
    # Calculo ANS (PRI)
    validacion_habiles = df_crm["Tipo_Dia"].eq("Habiles")

    start = (
        df_crm.loc[validacion_habiles, "FECHA_DE_INICIO"]
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    end = (
        df_crm.loc[validacion_habiles, "FECHA_FIN"]
        .fillna(today)
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    dias_habiles = np.busday_count(
        start + np.timedelta64(1, "D"),
        end + np.timedelta64(1, "D"),
        holidays=df_festivos,
    )

    df_crm["DIAS_CIERRE"] = df_crm["EN_DIAS"] 

    df_crm.loc[validacion_habiles,"DIAS_CIERRE",] = dias_habiles

    df_crm["DIAS_CIERRE"] = (pd.to_numeric(df_crm["DIAS_CIERRE"],errors="coerce",)
        .fillna(0)
        .clip(lower=0)
    )

    condicion = (df_crm["DIAS_CIERRE"].le(df_crm["ANS_Dias"]).fillna(False))

    df_crm["CUMPLIMIENTO_ANS"] = np.where(
        df_crm["FECHA_FIN"].notna(),
        np.where(condicion, "Cumple", "No Cumple"),
        pd.NA,
    )

    # Calculo SLA (Cliente)
    validacion_habiles_sla = df_crm["SLA_TipoDia"].eq("Habiles")
    start_sla = (
        df_crm.loc[validacion_habiles_sla, "FECHA_DE_INICIO"]
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    end_sla = (
        df_crm.loc[validacion_habiles_sla, "FECHA_FIN"]
        .fillna(today)
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    dias_habiles_sla = np.busday_count(
        start_sla + np.timedelta64(1, "D"),
        end_sla + np.timedelta64(1, "D"),
        holidays=df_festivos,
    )

    df_crm["DIAS_CIERRE_SLA"] = df_crm["EN_DIAS"]
    df_crm.loc[validacion_habiles_sla,"DIAS_CIERRE_SLA", ] = dias_habiles_sla

    df_crm["DIAS_CIERRE_SLA"] = (pd.to_numeric(df_crm["DIAS_CIERRE_SLA"],errors="coerce",)
        .fillna(0)
        .clip(lower=0)
    )

    condicion_sla = (df_crm["DIAS_CIERRE_SLA"].le(df_crm["SLA_Dia"]).fillna(False))

    df_crm["CUMPLIMIENTO_SLA"] = np.where(
        df_crm["FECHA_FIN"].notna(),
        np.where(condicion_sla, "Cumple", "No Cumple"),
        pd.NA,
    )
    return df_crm

def _calcular_estado_gestion_abiertos(
    df_crm: pd.DataFrame, df_festivos: np.ndarray, today: pd.Timestamp
) -> pd.DataFrame:
    """Calcula ESTADO_GESTION (Verde/Amarillo/Rojo/Negro) para casos sin FECHA_FIN."""

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    inicio_abiertos = (
        df_crm.loc[mask_sin_fin, "FECHA_DE_INICIO"]
        .dt.normalize()
        .to_numpy()
        .astype("datetime64[D]")
    )

    fin_today = np.datetime64(pd.Timestamp(today).normalize(), "D")

    dias_habiles_gestion = np.busday_count(
        inicio_abiertos + np.timedelta64(1, "D"),
        fin_today + np.timedelta64(1, "D"),
        holidays=df_festivos,
    )

    dias_corridos_gestion = (fin_today - inicio_abiertos).astype(int)

    mask_habiles_abiertos = (
        df_crm.loc[mask_sin_fin, "Tipo_Dia"].eq("Habiles").to_numpy()
    )

    resultado_final = np.where(
        mask_habiles_abiertos, dias_habiles_gestion, dias_corridos_gestion
    )
    resultado_final = np.nan_to_num(resultado_final, nan=0)

    dias_ns = (
        pd.to_numeric(df_crm.loc[mask_sin_fin, "ANS_Dias"], errors="coerce")
        .fillna(0)
        .to_numpy()
    )

    porc_gestion = np.divide(
        resultado_final,
        dias_ns,
        out=np.full(resultado_final.shape, np.nan, dtype=float),
        where=dias_ns != 0,
    )

    condiciones_estado = [
        (porc_gestion > 0) & (porc_gestion <= 0.5),
        (porc_gestion > 0.5) & (porc_gestion <= 0.75),
        (porc_gestion > 0.75) & (porc_gestion <= 1),
        (porc_gestion > 1),
    ]
    resultados_estado = ["Verde", "Amarillo", "Rojo", "Negro"]

    estado_abiertos = np.select(condiciones_estado, resultados_estado, default=pd.NA)

    df_crm["ESTADO_GESTION"] = pd.NA
    df_crm.loc[mask_sin_fin, "ESTADO_GESTION"] = estado_abiertos

    return df_crm


def _calcular_grupo_dias_cierre(
    df_crm: pd.DataFrame, today: pd.Timestamp
) -> pd.DataFrame:
    """Calcula GRUPO_DIAS_CIERRE para los casos sin FECHA_FIN."""

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    inicio_all = df_crm["FECHA_DE_INICIO"].dt.normalize().values.astype("datetime64[D]")
    fin_today = np.datetime64(pd.Timestamp(today).normalize(), "D")
    dias_transcurridos = (fin_today - inicio_all).astype(int)

    meta = pd.to_numeric(df_crm["ANS_Dias"], errors="coerce")

    dias_restantes = (meta - dias_transcurridos).astype("float64")

    condiciones_grupo = [
        dias_restantes < 0,
        dias_restantes <= 1,
        dias_restantes <= 3,
        dias_restantes <= 5,
        dias_restantes <= 7,
        dias_restantes <= 9,
    ]
    resultados_grupo = [
        "Vencido",
        "0 - 1 Día",
        "2 - 3 Días",
        "4 - 5 Días",
        "6 - 7 Días",
        "8 - 9 Días",
    ]

    grupo_dias = np.select(condiciones_grupo, resultados_grupo, default=">=10 Días")

    df_crm["GRUPO_DIAS_CIERRE"] = np.where(mask_sin_fin, grupo_dias, pd.NA)

    return df_crm