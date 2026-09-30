import pandas as pd
import numpy as np
from datetime import datetime, time
from pathlib import Path
import os

from routes.Paths import (
    Ruta_opl,
    Ruta_auxiliares,
    Ruta_clasificacion_ax,
    Ruta_festivos,
    Ruta_local,
    Ruta_global
)
from utils.Processing_OPL import data_opl
from utils.functions import load_files_from_folder

def load_auxiliares_data():

    require_columns = {
        "agent",
        "startinterval",
        "endinterval",
        "agent idle time",
        "agent incoming connecting time",
        "contacts missed",
        "agent on contact time",
        "agent outbound connecting time",
        "average agent api connecting time",
        "average agent callback connecting time",
        "average agent incoming connecting time"
    }

    delete_dup_subset = [
        "agent",
        "startinterval",
        "endinterval"
    ]

    df_clasifica_aux = pd.read_csv( Ruta_clasificacion_ax, delimiter=";", encoding="latin-1")
    df_clasifica_aux = (df_clasifica_aux[["Atributo", "Aplica_Ocupacion", "Auxiliares"]])
    df_clasifica_aux["Atributo"] = (df_clasifica_aux["Atributo"].str.lower())

    df_opl = data_opl(pd.read_excel(Ruta_opl,sheet_name="Combinado"))
    df_opl["Correo_contratista"] = (df_opl["Correo_contratista"].str.lower())

    df_festivos = (pd.to_datetime(pd.read_csv(Ruta_festivos)["Fecha"],format="%d/%m/%Y")
        .drop_duplicates()
        .values.astype("datetime64[D]")
    )

    df_aux = load_files_from_folder(
        Ruta_auxiliares,
        require_columns,
        delete_dup_subset
    )

    return (
        df_aux,
        df_clasifica_aux,
        df_festivos,
        df_opl
    )

def calcular_auxiliares(
        df_aux:pd.DataFrame,
        df_clasifica_aux: pd.DataFrame,
        df_festivos: pd.DataFrame,
        df_opl: pd.DataFrame
) -> pd.DataFrame:

    columnas_datetime = [
            "startinterval"
            ]
    for col in columnas_datetime:
        df_aux[col] = pd.to_datetime(df_aux[col].astype(str)
                    .str.rsplit("-", n=1)
                    .str[0], errors="coerce")
    df_aux["Fecha"] = pd.to_datetime(df_aux["startinterval"].dt.date)
    order_col = [
        "agent",
        "Fecha",
        "Intervalo_Ini",
        "source_file", 
        "file_date"
    ]
    df_aux["Intervalo_Ini"] = df_aux["startinterval"].dt.time

    column_order = order_col + [col for col in df_aux.columns if col not in order_col]
    df_aux = df_aux[column_order]
    df_aux.columns.to_list()
    delete_columns = [
        "agent answer rate",
        "average agent api connecting time",
        "average agent callback connecting time",
        "average agent incoming connecting time",
        "average agent outbound connecting time",
        "online time",
        "source.name",
        "nonproductive time",
        "startinterval",
        "endinterval",
        "occupancy"
    ]
    df_aux = df_aux.drop(columns=delete_columns, errors="ignore")

    df_aux = pd.melt(
    df_aux,
    id_vars=order_col,
    var_name="Nombre_Estado",
    value_name="Time(seg)")
    df_aux = df_aux[~df_aux["Time(seg)"].isna()]
    df_aux["agent"] = df_aux["agent"].str.lower()

    df_aux = df_aux.merge(
        df_opl[["Id_opl","Correo_contratista"]],
        how="left",
        left_on="agent",
        right_on="Correo_contratista",
    ).drop(columns=["Correo_contratista"])

    inicio = time(8, 0, 0)
    fin = time(20, 0, 0)

    df_aux["Aplica_factura"] = np.where(
        (~df_aux["Fecha"].isin(df_festivos)) &
        (df_aux["Intervalo_Ini"] >= inicio) &
        (df_aux["Intervalo_Ini"] <= fin),
        "SI", "NO" 
    )
    df_aux = df_aux.merge(
        df_clasifica_aux[["Atributo","Aplica_Ocupacion", "Auxiliares"]],
        how="left",
        left_on="Nombre_Estado",
        right_on="Atributo"
    ).drop(columns=["Atributo"])

    return df_aux

def guardar_data_auxiliares(
        df_aux: pd.DataFrame,
        file_name: str = "06.Data_Conexion_Auxiliares.csv")-> None:

        df_aux.to_csv(os.path.join(Ruta_global, file_name), index=False, encoding="utf-8")
        df_aux.to_csv(os.path.join(Ruta_local, file_name), index=False, encoding="utf-8")

def ejecutar_auxiliares() -> pd.DataFrame:
    (
        df_aux,
        df_clasifica_aux,
        df_festivos,
        df_opl
    ) = load_auxiliares_data()

    resultado = calcular_auxiliares(
        df_aux=df_aux,
        df_clasifica_aux=df_clasifica_aux,
        df_festivos=df_festivos,
        df_opl=df_opl
    )

    guardar_data_auxiliares(resultado)

    return resultado