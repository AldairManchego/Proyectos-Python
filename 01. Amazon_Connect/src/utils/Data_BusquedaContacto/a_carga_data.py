import os, sys
from datetime import datetime
from pathlib import Path
import warnings

import pandas as pd
from unidecode import unidecode

from utils.functions import detect_delimiter


COLUMNAS_REQUERIDAS = {
    "id de contacto",
    "canal",
    "marca de tiempo de inicio",
    "cola",
    "agente",
    "marca de tiempo de desconexion",
    "marca de tiempo de conexion a agente",
    "marca de tiempo en cola",
    "marca de tiempo de inicio de acw",
    "marca de tiempo de fin de acw"
}



def load_contacts(folder_path: str | Path) -> pd.DataFrame:
    folder_path = Path(folder_path)
    dfs = []
    for file in folder_path.iterdir():
        if not file.is_file():
            continue

        if file.suffix.lower() != ".csv":
            continue
        try:
            delimiter = detect_delimiter(file)
            df = pd.read_csv( file, delimiter=delimiter)
            df.columns = ( df.columns
                .str.strip()
                .str.lower()
            )

            faltantes = ( COLUMNAS_REQUERIDAS - set(df.columns) )

            if faltantes:
                print(
                    f"{file.name} omitido. "
                    f"Columnas faltantes: {faltantes}"
                )
                continue

            df["source_file"] = file.name
            df["file_create"] = datetime.fromtimestamp( file.stat().st_mtime )
            df = df[df["id de contacto"].notna()]
            df = df[
                df["cola"].notna()
                & (df["cola"].astype(str).str.strip() != "")
                & df["canal"].notna()
                & (df["canal"].astype(str).str.strip() != "")
            ]
            dfs.append(df)

        except Exception as e:
            print( f"Error leyendo {file.name}: {e}" )

    if not dfs:
        return pd.DataFrame()
    return (
        pd.concat(
            dfs,
            ignore_index=True
        )
        .drop_duplicates(subset=["id de contacto"])
    )