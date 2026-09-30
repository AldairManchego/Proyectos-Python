import pandas as pd
import os, sys, re
from unidecode import unidecode
from pathlib import Path
# ********************** Funciones para procesar Arbol Tipificacaciones ******************************
def Columna_fcr(texto):
    if isinstance(texto, str):
        texto = texto.upper().strip()
        if "FCR SI" in texto:
            return "SI"
        elif "FCR NO" in texto:
            return "NO"
    return "N/A"

def extraer_sla(texto):
    if pd.isna(texto):
        return pd.Series([0, "Calendario"])
    
    texto = str(texto).strip().lower()
    patron = re.search(r"(\d+)\s*dia[s]?", texto)
    sla_dia = int(patron.group(1)) if patron else 0

    if "habil" in texto:
        tipo_dia = "Habiles"
    elif "calendario" in texto:
        tipo_dia = "Calendario"
    else:
        tipo_dia = "Calendario"
    return pd.Series([sla_dia, tipo_dia])

                       
def limpiar_df_arbol(df : pd.DataFrame) -> pd.DataFrame:
    df = df[df.iloc[:,2].notna()].reset_index(drop=True)
    df.columns = df.iloc[1]
    df = df.iloc[2:].reset_index(drop=True)
    df = df.rename(columns={
        "PRODUCTO" : "Nivel_1",
        "TIPO" : "Nivel_2",
        "SUBTIPO" : "Nivel_3",
        "¿Debe quedar predefinido?" : "SPC/FCR",
        "Nuevo ANS" : "ANS_Dias",
        "Tipo de día" : "Tipo_Dia",
        "BO A QUE PERTENECE" : "BO_Asignado"
    })
    df = df[
        ["Nivel_1", "Nivel_2", "Nivel_3", "PRI", "SPC/FCR", "ANS_Dias", "Tipo_Dia", "BO_Asignado", "ANS/SLA"]
    ]

    df = df.map(lambda x: x.strip().title() if isinstance(x, str) else x)
    df = df.map(lambda x: unidecode(x) if isinstance(x, str) else x)

    df["SPC/FCR"] = df["SPC/FCR"].apply(Columna_fcr)
    df["ANS_Dias"] = pd.to_numeric(df["ANS_Dias"], errors="coerce").fillna(0)
    df["BO_Asignado"] = df["BO_Asignado"].fillna("N/A")
    df["Tipo_Dia"] = df["Tipo_Dia"].fillna("Calendario")
    df["PRI"] = df["PRI"].fillna("N/A")
    df = df.drop_duplicates().reset_index(drop=True)
    df.insert(0, "IdTipificacion", range(1, len(df) + 1))

    if "ANS/SLA" in df.columns:
        df[["SLA_Dia", "SLA_TipoDia"]] = df["ANS/SLA"].apply(extraer_sla)
        df["SLA_Dia"] = (pd.to_numeric(df["SLA_Dia"], errors="coerce").fillna(0).astype("int64"))

    cols = ["IdTipificacion", "ANS_Dias"]
    df[cols] = df[cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).astype("Int64")

    df = df.drop(columns=["ANS/SLA"])

    return df

def guardar_arbol(
        df: pd.DataFrame, 
        ruta_global: str | Path, 
        ruta_local: str | Path) -> pd.DataFrame:
    
    nombre = "01.Arbol_tipificaciones"

    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False, encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False, encoding="utf-8")

