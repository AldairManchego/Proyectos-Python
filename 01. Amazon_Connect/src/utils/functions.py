import pandas as pd
import os, sys, csv, traceback
from unidecode import unidecode
from pathlib import Path
from datetime import datetime

# ********************** Funciones para procesar Arbol Tipificacaciones ******************************
def Columna_fcr(texto):
    if isinstance(texto, str):
        texto = texto.upper().strip()
        if "FCR SI" in texto:
            return "SI"
        elif "FCR NO" in texto:
            return "NO"
    return "N/A"

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
        ["Nivel_1", "Nivel_2", "Nivel_3", "PRI", "SPC/FCR", "ANS_Dias", "Tipo_Dia", "BO_Asignado"]
    ]

    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.map(lambda x: unidecode(x) if isinstance(x, str) else x)
    df["SPC/FCR"] = df["SPC/FCR"].apply(Columna_fcr)
    df["ANS_Dias"] = pd.to_numeric(df["ANS_Dias"], errors="coerce").fillna(0)
    df["BO_Asignado"] = df["BO_Asignado"].fillna("N/A")
    df["Tipo_Dia"] = df["Tipo_Dia"].fillna("Calendario")
    df["PRI"] = df["PRI"].fillna("N/A")
    df = df.drop_duplicates().reset_index(drop=True)
    df.insert(0, "IdTipificacion", range(1, len(df) + 1))

    cols = ["IdTipificacion", "ANS_Dias"]
    df[cols] = df[cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).astype("Int64")
    
    return df

def guardar_arbol(df: pd.DataFrame, ruta_global: str, ruta_local: str) -> pd.DataFrame:
    
    nombre = "01.Arbol_tipificaciones"

    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False, encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False, encoding="utf-8")

# ************************ Funciones para procesar el MasterSkill *******************************

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
    df = df.drop_duplicates()
    df = df.sort_values("IdFcst").reset_index(drop=True)
    df.insert(0, "IdMasterSkill", range(1, len(df) + 1))
    df["IdMasterSkill"] = df["IdMasterSkill"].astype("int64")
    return df

def guardar_masterskill(df: pd.DataFrame, ruta_global: str, ruta_local: str) -> pd.DataFrame:
    nombre = "02.MasterSkill"
    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False, encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False, encoding="utf-8")

# ************************** Procesamiento OPL ***************************************

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
        ruta_global: str, 
        ruta_local
        ) -> None:
    nombre = "03.Opl_consolidado"
    df.to_csv(os.path.join(ruta_global, f"{nombre}.csv"), index=False,encoding="utf-8")
    df.to_csv(os.path.join(ruta_local, f"{nombre}.csv"), index=False,encoding="utf-8")

#**************************** Detectar delimitador ********************

def detect_delimiter(
    path_file: str | Path,
    encoding: str = "utf-8",
    file_size: int = 4096
) -> str:

    with open(
        path_file,
        "r",
        encoding=encoding,
        errors="ignore"
    ) as f:

        sample = f.read(file_size)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|"
        )
        return dialect.delimiter

    except csv.Error:

        counts = {
            ",": sample.count(","),
            ";": sample.count(";"),
            "\t": sample.count("\t"),
            "|": sample.count("|")
        }

        return max(counts, key=counts.get)

#*************************************Detectar el Encogin de csv*****************************

def detect_encoding(file: Path) -> str:
    with open(file, "rb") as f:
        header = f.read(4)

    if header.startswith(b"\xff\xfe"):
        return "utf-16-le"

    if header.startswith(b"\xfe\xff"):
        return "utf-16-be"

    if header.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    return "utf-8"

#***************************leer archivos csv y excel de una carpeta***************************
def _read_files_from_folder(
        file: Path,
        sheet_name: str | int | None = None
        ) -> pd.DataFrame:

    suffix = file.suffix.lower()

    if suffix == ".csv":

        encoding = detect_encoding(file)

        delimiter = detect_delimiter(
            file,
            encoding=encoding
        )

        try:
            return pd.read_csv(
                file,
                delimiter=delimiter,
                encoding=encoding,
                low_memory=False
            )

        except UnicodeDecodeError:

            return pd.read_csv(
                file,
                delimiter=delimiter,
                encoding="latin-1",
                low_memory=False
            )

    elif suffix == ".xlsx":
        return pd.read_excel(
            file,
            sheet_name=sheet_name or 0
            )

    raise ValueError(
        f"Extension o archivo no valida: {suffix}"
    )

#****************** leer y cargar archvios de una carpeta ************************************
def load_files_from_folder(
        folder_route: "str | Path",
        require_columns: set,
        delete_dup_subset: "list[str] | None" = None,
        file_extensions: tuple = (".csv", ".xlsx"),
        sheet_name: str | int | None = None
        )-> pd.DataFrame:
    
    folder_route = Path(folder_route)
    dfs = []

    for file in sorted(folder_route.iterdir()):
        if not file.is_file():
            continue
        if file.suffix.lower() not in file_extensions:
            continue

        try:
            df = _read_files_from_folder(
                file,
                sheet_name=sheet_name)
            df.columns = (
                df.columns.astype(str)
                .str.strip()
                .str.lower()
                .map(unidecode)
            )

            faltantes = set(require_columns) - set(df.columns)
            if faltantes:
                print(
                    f"{file.name} omitido."
                    f"Columnas faltantes: {faltantes}"
                )
                continue

            df["source_file"] = file.name
            df["file_date"] = datetime.fromtimestamp(file.stat().st_atime)
            dfs.append(df)

        except Exception:
            print(f"Error al leer el archivo: {file.name}: \n{traceback.format_exc()}")

    if not dfs:
        return pd.DataFrame()

    df_final = pd.concat(dfs, ignore_index=True)
    if delete_dup_subset:
        df_final =(
            df_final
            .sort_values("file_date")
            .drop_duplicates(subset=delete_dup_subset,keep="last")
            .reset_index(drop=True)
        )
    return df_final