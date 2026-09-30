import pandas as pd
import numpy as np
import csv, os, sys
from pathlib import Path
from unidecode import unidecode

from utils.functions import detect_delimiter

def _transformacion_comentarios(files_path: str|Path)-> pd.DataFrame:
    files_path = Path(files_path)
    dfs = []
    required_columns = [
        "RADICADO",
        "COMENTARIO",
        "SOLUCIÓN",
        "FECHA_COMENTARIO",
        "NÚMERO_PEDIDO",
        "FECHA_ÚLTIMO_CAMBIO",
        "NOMBRE_ÚLTIMO_CAMBIO"
    ]
    clean_columns =[
        "NOMBRE_ÚLTIMO_CAMBIO"
    ]

    for file in files_path.iterdir():
        if not file.is_file():
            continue
        try:
            if file.suffix.lower() == ".csv":
                delimiter = detect_delimiter(file)
                df = pd.read_csv(file, delimiter=delimiter)
            else:
                continue
            validacion_columns = set(required_columns) - set(df.columns)
            if validacion_columns:
                print(f"No fue posible procesar el archivo: {file.name} debido a la ausencia de las columnas: {validacion_columns}")
                continue

            for col in clean_columns:
                df[col] = (
                    df[col]
                    .astype("object")
                    .map(lambda x: unidecode(x) if isinstance(x, str) else x)
                    .str.strip()
                    .str.title()
                )   
            df = df[required_columns]
            df.columns = (df.columns.astype("string")
                          .str.strip()
                          .map(unidecode)
                          .str.upper())

            df["FECHA_COMENTARIO"] = df["FECHA_COMENTARIO"].fillna(df["FECHA_ULTIMO_CAMBIO"])
            df = df[df["RADICADO"].notna()]
            df = df.rename(columns={"RADICADO":"RADICADO_COMENTARIO"})
            dfs.append(df)

        except Exception as e:
            print(f"no fue posible procesar el archivo: {file.name} debido al error: {e}")

    if not dfs:
        return pd.DataFrame()

    df_final = (
        pd.concat(dfs, ignore_index=True)
        .drop_duplicates()
        .sort_values("FECHA_COMENTARIO")
        .drop_duplicates(
            subset=["RADICADO_COMENTARIO"],
            keep="last"
        )
    )
    return df_final