import os
import numpy as np
import pandas as pd
from unidecode import unidecode

from routes.Paths import (
    Ruta_busquedad_contacto,
    Ruta_opl,
    Ruta_masterskill,
    Ruta_overall,
    Ruta_local,
    Ruta_global
)

from utils.Processing_OPL import data_opl
from utils.Processing_MasterSkill import limpiar_masterskill
from utils.functions import load_files_from_folder


def load_data_kpi():

    require_columns_contactos = {
        "id de contacto",
        "canal",
        "marca de tiempo de inicio",
        "cola",
        "agente",
        "marca de tiempo de desconexion",
        "marca de tiempo de conexion a agente",
        "marca de tiempo en cola",
        "marca de tiempo de inicio de acw",
        "marca de tiempo de fin de acw",
    }

    delete_dup_columns_contactos = [
        "id de contacto"
    ]

    df_contactos = load_files_from_folder(
        Ruta_busquedad_contacto,
        require_columns_contactos,
        delete_dup_columns_contactos
    )

    require_columns_kpi = {
        "channel",
        "queue",
        "agent",
        "startinterval",
        "endinterval",
        "contacts answered in 20 seconds",
        "contacts answered in 180 seconds",
        "contacts handled",
        "contacts queued"
    }

    delete_dup_columns_kpi = [
        "channel",
        "queue",
        "agent",
        "startinterval"
    ]

    df_kpi = load_files_from_folder(
        Ruta_overall,
        require_columns_kpi,
        delete_dup_columns_kpi
    )

    df_opl = data_opl(pd.read_excel(Ruta_opl, sheet_name="Combinado"))

    df_opl["Correo_contratista"] = (df_opl["Correo_contratista"].str.lower())

    df_master = limpiar_masterskill(pd.read_excel(Ruta_masterskill,sheet_name="TB"))

    return (
        df_kpi,
        df_contactos,
        df_opl,
        df_master
    )


def calcular_kpi(
    df_kpi: pd.DataFrame,
    df_contactos: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_master: pd.DataFrame
) -> pd.DataFrame:

    df_kpi = df_kpi[
        df_kpi["channel"].notna()
        & df_kpi["queue"].notna()
    ].copy()

    df_kpi["startinterval"] = pd.to_datetime(
        df_kpi["startinterval"]
        .astype(str)
        .str.rsplit("-", n=1)
        .str[0],
        errors="coerce"
    )

    df_kpi["fecha"] = pd.to_datetime(df_kpi["startinterval"].dt.date)

    df_kpi["intervalo_inicio"] = (df_kpi["startinterval"].dt.time)

    df_kpi["contactos_atendidos_en_umbral"] = np.where(
        df_kpi["channel"].isin(["Voz", "Voice"]),
        df_kpi["contacts answered in 20 seconds"],
        df_kpi["contacts answered in 180 seconds"]
    )

    df_kpi["channel"] = np.where(df_kpi["channel"] == "Voice", "Voz", df_kpi["channel"])

    df_kpi["queue"] = (df_kpi["queue"].fillna("").str.title().map(unidecode)
    )

    df_kpi["agent"] = (df_kpi["agent"].str.lower())

    df_kpi = df_kpi.merge(
        df_master[
            [
                "IdMasterSkill",
                "Canal",
                "Colas"
            ]
        ],
        how="left",
        left_on=["channel", "queue"],
        right_on=["Canal", "Colas"]
    ).drop(
        columns=[
            "Canal",
            "Colas",
            "startinterval",
            "endinterval"
        ],
        errors="ignore"
    )

    df_kpi = df_kpi.merge(
        df_opl[
            [
                "Id_opl",
                "Correo_contratista"
            ]
        ],
        how="left",
        left_on="agent",
        right_on="Correo_contratista"
    ).drop(
        columns=["Correo_contratista"],
        errors="ignore"
    )

    return df_kpi

def guardar_data_kpioverall(
    df_kpi: pd.DataFrame,
    file_name: str = "07.Data_KpiOverAll.csv"
) -> None:
    df_kpi.to_csv(os.path.join(Ruta_global, file_name), index=False, encoding="utf-8")
    df_kpi.to_csv(os.path.join(Ruta_local, file_name),index=False, encoding="utf-8")


def ejecutar_kpioverall() -> pd.DataFrame:
    (
        df_kpi,
        df_contactos,
        df_opl,
        df_master
    ) = load_data_kpi()

    resultado = calcular_kpi(
        df_kpi,
        df_contactos,
        df_opl,
        df_master
    )

    guardar_data_kpioverall(resultado)

    return resultado