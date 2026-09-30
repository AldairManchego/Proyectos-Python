import pandas as pd
import os, sys, csv
from unidecode import unidecode
from datetime import datetime
from pathlib import Path
from utils.functions import detect_delimiter
from routes.Paths import Ruta_crm

def load_files(folder_path: Path)-> pd.DataFrame:
    require_columns = {
        "RADICADO",
        "PRODUCTO",
        "TIPO",
        "SUBTIPO",
        "ID_LLAMADA_DE_CONTACTO",
        "SE_RESOLVIÓ_EL_CONTACTO",
        "MOTIVO_NO_FCR",
        "NOMBRE_ALIADO",
        "FECHA_DE_INICIO",
        "FECHA_FIN"
    }
    dfs = []
    folder_path = Path(folder_path)

    for file in folder_path.iterdir():
        if not file.is_file():
            continue
        try:
            if file.suffix.lower() == ".csv":
                delimiter = detect_delimiter(file)
                df = pd.read_csv(file, delimiter=delimiter, low_memory=False)
            else:
                continue
            columns_validation = require_columns - set(df.columns)
            if columns_validation:
                print(
                    f"Archivo {file} omitido."
                    f"Ausencia de las siguientes columnas {columns_validation}."
                )
                continue
            df["FILE_NAME"] = file.name
            df["CREATION_FILE_DATE"] = datetime.fromtimestamp(file.stat().st_atime)
            dfs.append(df)
        except Exception as e:
            print(f"el archivo {file.name} no pudo ser proceado por el error: {e}.")
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True).drop_duplicates()