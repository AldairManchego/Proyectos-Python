import pandas as pd
import os, sys
from unidecode import unidecode
from pathlib import Path

def clean_col(valor):
    if isinstance(valor, str):
        valor = unidecode(valor.strip().title())

        if valor == "":
            return "-"
        return valor
    return valor


def data_opl(df: pd.DataFrame) -> pd.DataFrame:

    colmnas_opl = [
                "Identificacion", "ID Workday", "ID NICE", "Nombre", "Jefe Inmediato", "Lider", "Posicion",
                "Servicio", "Estado", "Fecha Inicio Servicio", "Grupo/Wave", "FECHA RETIRO", "Correo Corporativo",
                "Vista 360" ]
    
    df = df[colmnas_opl]
    df = df.fillna("-")
    df["FECHA RETIRO"] = pd.to_datetime(df["FECHA RETIRO"], format="%d/%m/%Y", errors="coerce")
    df["Fecha Inicio Servicio"] = pd.to_datetime(df["Fecha Inicio Servicio"], format="%d/%m/%Y", errors="coerce")

    col_limpias = ["Nombre", "Jefe Inmediato", "Lider", "Posicion", "Servicio", "Estado", "Grupo/Wave"]
    for col in col_limpias:
        df[col] = df[col].apply(clean_col)

    df = df.rename(columns={
        "Identificacion":"Documento",
        "ID Workday":"Id_Workday",
        "ID NICE":"Id_Nice",
        "Nombre":"Nombre_Agente",
        "Jefe Inmediato":"Supervisor",
        "Grupo/Wave":"Wave",
        "Correo Corporativo":"Correo_corporativo",
        "Vista 360":"Correo_contratista",
        "FECHA RETIRO": "Fecha_retiro",
        "Fecha Inicio Servicio":"Fecha_inicio_servicio"
    })

    category_column = ["Posicion", "Servicio", "Estado", "Wave"]
    for col in category_column:
        df[col] = df[col].astype("category")    
    df = (
    df[
        ~df["Estado"].str.contains(
            "Retiro|Abandono",
            case=False,
            na=False
        )
    ]
    .loc[lambda x: ~x["Correo_corporativo"].isin(["-"])]
    .drop_duplicates(subset=["Correo_corporativo"])
    .reset_index(drop=True)
    )
    df.insert(0, "Id_opl", range(1, len(df) + 1))
    df["Id_opl"] = df["Id_opl"].astype("int64")
    return df

def guardar_opl(
        df: pd.DataFrame, 
        ruta_global: str | Path, 
        ruta_local: str | Path
        ) -> None:
    nombre = "03.Opl_consolidado"
    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False,encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False,encoding="utf-8")