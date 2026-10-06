import pandas as pd
import os, sys, re, traceback
from unidecode import unidecode
from pathlib import Path
from datetime import datetime
from routes.Paths import Ruta_global, Ruta_local

def _load_arbol_historico(
        folder_route: str | Path,
        file_extension: tuple=(".xlsx",)
        )-> pd.DataFrame:
    folder_route = Path(folder_route)
    dfs = []

    for file in sorted(folder_route.iterdir()):
        if not file.is_file():
            continue
        if file.suffix.lower() not in file_extension:
            continue
        try:
            df_arbol_hist = pd.read_excel(file, sheet_name='Tipificación Vista360')
            df_arbol_hist = df_arbol_hist[df_arbol_hist.iloc[:,1].notna()].reset_index(drop=True)
            df_arbol_hist.columns = df_arbol_hist.iloc[0]
            df_arbol_hist = df_arbol_hist.iloc[1:,2:].reset_index(drop=True)
            df_arbol_hist = df_arbol_hist.rename(columns={
                        "PRODUCTO" : "Nivel_1",
                        "TIPO" : "Nivel_2",
                        "SUBTIPO" : "Nivel_3",
                        "¿Debe quedar predefinido?" : "SPC/FCR",
                        "Nuevo ANS" : "ANS_Dias",
                        "Tipo de día" : "Tipo_Dia",
                        "ANS/SLA": "SLA_Dia",
                        "BO A QUE PERTENECE" : "BO_Asignado",
                        "Aplica para ambos canales ": "Aplica_Ofrecimiento"
            })
            df_arbol_hist = df_arbol_hist[[
                    "Nivel_1", "Nivel_2", "Nivel_3",
                    "PRI", "SPC/FCR", "ANS_Dias",
                    "Tipo_Dia", "SLA_Dia","BO_Asignado",
                    "Aplica_Ofrecimiento"
                    ]]
            df_arbol_hist = df_arbol_hist.map(
                lambda x: unidecode(x.strip())
                if isinstance(x, str)
                else x
            )
            df_arbol_hist["ANS_Dias"] = pd.to_numeric(df_arbol_hist["ANS_Dias"], errors="coerce").fillna(0).astype(int)
            df_arbol_hist["BO_Asignado"] = df_arbol_hist["BO_Asignado"].fillna("N/A")
            df_arbol_hist["Tipo_Dia"] = df_arbol_hist["Tipo_Dia"].fillna("Calendario")
            df_arbol_hist["PRI"] = df_arbol_hist["PRI"].fillna("N/A")
            df_arbol_hist["Aplica_Ofrecimiento"] = df_arbol_hist["Aplica_Ofrecimiento"].fillna("No")
            df_arbol_hist = ( df_arbol_hist[df_arbol_hist["PRI"].notna()].reset_index(drop=True))
            df_arbol_hist = df_arbol_hist.drop_duplicates().reset_index(drop=True)

            match = re.search(r"(\d{2}_\d{2}_\d{4})", file.stem )
            df_arbol_hist["source_file"] = (
                pd.to_datetime(
                    match.group(1),
                    format="%d_%m_%Y"
                ).date()
                if match
                else pd.NaT
            )

            df_arbol_hist["file_date"] = datetime.fromtimestamp(file.stat().st_mtime)
            dfs.append(df_arbol_hist)

        except Exception:
             print(f"Error al leer el archivo: {file.name}: \n{traceback.format_exc()}")
    if not dfs:
        return pd.DataFrame()
    df_final = pd.concat(dfs, ignore_index=True)
  
    df_final =(
            df_final
            .sort_values("file_date")
            .drop_duplicates()
            .reset_index(drop=True)
        )
    df_final.insert( 0,"IdTipificacion", range(1, len(df_final) + 1))
    return df_final


def guardar_arbol_historico(
    df: pd.DataFrame,
    ruta_global: str | Path = Ruta_global,
    ruta_local: str | Path = Ruta_local
) -> pd.DataFrame:

    nombre = "09.Arbol_historico_tipificacion"

    df.to_csv(
        Path(ruta_global) / f"{nombre}.csv",
        index=False,
        encoding="utf-8"
    )

    df.to_csv(
        Path(ruta_local) / f"{nombre}.csv",
        index=False,
        encoding="utf-8"
    )

    return df