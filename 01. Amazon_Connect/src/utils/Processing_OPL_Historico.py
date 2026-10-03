import pandas as pd
import numpy as np
import sys, csv, traceback
from pathlib import Path
from unidecode import unidecode
from datetime import datetime, timedelta

from routes.Paths import Ruta_opl, Ruta_opl_historico, Ruta_local

required_columns = [
        "Identificacion", "ID NICE", "ID Workday", "Nombre", "Jefe Inmediato", "Lider",
        "Posicion", "Servicio", "Servicio factura", "Unidad de negocio",
        "Genero", "Fecha de nacimiento", "Fecha Inicio Servicio", "Fecha de contratación",
        "Condición", "Grupo/Wave", "Site", "Estado", "HOJA", "Vista 360","Correo Corporativo"
    ]

def cargar_insumos() -> tuple[
    pd.DataFrame,
    pd.DataFrame
]:
    df_opl = pd.read_excel(
        Ruta_opl,
        sheet_name="Combinado",
        engine="openpyxl")

    df_opl = df_opl[required_columns]

    for col in required_columns:
        df_opl[col] = (
            df_opl[col]
            .fillna("-")
            .astype(str)
            .str.strip()
            .map(unidecode)
        )

    df_opl.columns = (df_opl.columns
                    .str.strip()
                    .str.upper()
                    .map(unidecode))

    df_opl = df_opl[df_opl["ESTADO"].isin(["ACTIVO", "APOYO", "MATERNA"])]

    columns_dates = [
            "FECHA DE NACIMIENTO", 
            "FECHA INICIO SERVICIO", 
            "FECHA DE CONTRATACION", 

        ]
    for col in columns_dates:
            df_opl[col] = pd.to_datetime(df_opl[col], format='%d/%m/%Y', errors='coerce')
    df_opl = df_opl.drop_duplicates(["IDENTIFICACION", "ID WORKDAY", "VISTA 360"])

    df_opl = df_opl.rename(columns={
    "VISTA 360":"CORREO CONTRATISTA"    
    })

# Carga OPL Historico:
    df_opl_historico = pd.read_excel(Ruta_opl_historico)
    df_opl_historico = df_opl_historico.drop_duplicates(["IDENTIFICACION", "ID WORKDAY", "CORREO CONTRATISTA", "FECHA CARGA"],keep="last")
    
    return df_opl, df_opl_historico


def transformar_opl(
    df_opl: pd.DataFrame,
    df_opl_historico: pd.DataFrame
) -> pd.DataFrame:

    today = datetime.now().date()

    # Fechas que se deben generar
    if today.weekday() == 4:  # Viernes
        fechas = [
            today,
            today + timedelta(days=1),  # Sábado
            today + timedelta(days=2),  # Domingo
            today + timedelta(days=3),  # Lunes
        ]
    else:
        fechas = [
            today,
            today + timedelta(days=1)   # Día siguiente
        ]

    dfs = []

    for fecha in fechas:
        df_temp = df_opl.copy()
        df_temp["FECHA CARGA"] = pd.to_datetime(fecha)
        dfs.append(df_temp)

    # OPL del día + fechas futuras
    df_opl = pd.concat(dfs, ignore_index=True)

    # Agregar al histórico
    df_opl = pd.concat(
        [df_opl_historico, df_opl],
        ignore_index=True
    )

    # Eliminar duplicados
    df_opl = df_opl.drop_duplicates(
        subset=[
            "IDENTIFICACION",
            "ID WORKDAY",
            "CORREO CONTRATISTA",
            "FECHA CARGA"
        ],
        keep="last"
    )
    df_opl = df_opl[~df_opl["HOJA"].isin(["Bajas"])]
    return df_opl


def guardar_opl(
    df_opl: pd.DataFrame,
    Ruta_opl_historico: str | Path,
    Ruta_local: str | Path,
    nombre_archivo: str = "history_PCOL_OPL.xlsx",
) -> None:

    df_opl.to_excel(Ruta_opl_historico, index=False)
    df_opl.to_excel(Path(Ruta_local)/nombre_archivo, index=False)
    
def procesar_opl(
    save_file: bool = False,
) -> pd.DataFrame:

    df_opl, df_opl_historico = cargar_insumos()

    df_opl = transformar_opl(
        df_opl=df_opl,
        df_opl_historico=df_opl_historico
    )

    if save_file:
        guardar_opl(
            df_opl=df_opl,
            Ruta_opl_historico=Ruta_opl_historico,
            Ruta_local=Ruta_local,
        )

    return df_opl