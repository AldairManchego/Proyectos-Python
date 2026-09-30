import pandas as pd
import os, sys
from unidecode import unidecode
from pathlib import Path


def limpiar_masterskill(df: pd.DataFrame) -> pd.DataFrame:
    
    df = df[
        [
            "IdSkill",
            "Servicio",
            "Channel availability - canal habilitado",
            "Skill / Colas que contiene",
            "Nombre Perfil enrutamiento",
            "Servicio Fsct"
        ]
    ]

    df = df.rename(columns={
        "Nombre Perfil enrutamiento": "Perfil_Enrutamiento",
        "Skill / Colas que contiene": "Colas",
        "Channel availability - canal habilitado": "Canal",
        "Servicio Fsct": "Servicio_Fcst",
        "IdSkill": "IdFcst"
    })
    df = df.map(lambda x: x.strip().title() if isinstance(x, str) else x)
    df = df.drop_duplicates()
    df = df.sort_values("IdFcst").reset_index(drop=True)
    df.insert(0, "IdMasterSkill", range(1, len(df) + 1))
    df["IdMasterSkill"] = df["IdMasterSkill"].astype("int64")
    return df

def guardar_masterskill(
        df: pd.DataFrame, 
        ruta_global: str | Path, 
        ruta_local: str | Path) -> pd.DataFrame:
    nombre = "02.MasterSkill"
    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False, encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False, encoding="utf-8")
