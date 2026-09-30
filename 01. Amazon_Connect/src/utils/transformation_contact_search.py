import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from unidecode import unidecode

from utils.functions import detect_delimiter


COLUMNAS_REQUERIDAS = {
    "id de contacto",
    "canal",
    "marca de tiempo de inicio",
    "cola",
    "agente",
    "marca de tiempo de desconexión",
    "marca de tiempo de conexión a agente",
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
            df = pd.read_csv( file, delimiter=delimiter )
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

def _calculate_contact_metrics(
    df_contactos: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula:

    - Rellamadas
    - Recontactos
    - Voz -> Chat
    - Chat -> Voz
    """

    tipificaciones_excluir = {
        "Llamada de Prueba",
        "Interacción de Prueba",
        "Chat de Prueba",
        "Pruebas PCO",
        "Devolución llamada EFECTIVA",
        "Devolución llamada NO EFECTIVA"
    }

    documentos_excluir = {
        "2222222956",
        "2222222005"
    }

    df_valido = df_contactos[
        ~df_contactos["método de iniciación"].isin(
            ["Transferir", "Saliente"]
        )
        &
        (
            ~df_contactos["NIVEL_3"].isin(
                tipificaciones_excluir
            )
            |
            ~df_contactos[
                "NÚMERO_DOCUMENTO_DEL_CLIENTE"
            ].astype(str).isin(
                documentos_excluir
            )
        )
    ].copy()

    df_valido = df_valido.sort_values(
        [
            "llave_documento_fecha",
            "marca de tiempo de inicio"
        ]
    )

    # ==========================
    # RELLAMADAS
    # ==========================

    df_valido["orden_interaccion"] = (
        df_valido
        .groupby("llave_documento_fecha")
        .cumcount()
        + 1
    )

    df_valido["conteo_rellamda"] = (
        df_valido
        .groupby("llave_documento_fecha")
        ["id de contacto"]
        .transform("count")
    )

    df_valido["es_rellamada"] = (
        df_valido["orden_interaccion"] > 1
    ).astype(int)

    # ==========================
    # RECONTACTOS
    # ==========================

    df_valido["conteo_recontacto"] = (
        df_valido
        .groupby("llave_recontacto")
        ["id de contacto"]
        .transform("count")
    )

    df_valido["orden_recontacto"] = (
        df_valido
        .sort_values("marca de tiempo de inicio")
        .groupby("llave_recontacto")
        .cumcount()
        + 1
    )

    df_valido["es_recontacto"] = (
        df_valido["orden_recontacto"] > 1
    ).astype(int)

    # ==========================
    # VOZ -> CHAT
    # CHAT -> VOZ
    # ==========================

    df_resumen = (
        df_valido
        .sort_values(
            [
                "llave_documento_fecha",
                "orden_interaccion"
            ]
        )
        .copy()
    )

    df_resumen["es_chat"] = (
        df_resumen["canal"] == "Chat"
    )

    df_resumen["es_voz"] = (
        df_resumen["canal"] == "Voz"
    )

    df_resumen = (
        df_resumen
        .groupby(
            "llave_documento_fecha",
            sort=False
        )
        .agg(
            primer_contacto=("canal", "first"),
            tiene_chat=("es_chat", "any"),
            tiene_voz=("es_voz", "any")
        )
        .reset_index()
    )

    df_resumen["voz_a_chat"] = (
        (
            df_resumen["primer_contacto"] == "Voz"
        )
        &
        (
            df_resumen["tiene_chat"]
        )
    ).astype(int)

    df_resumen["chat_a_voz"] = (
        (
            df_resumen["primer_contacto"] == "Chat"
        )
        &
        (
            df_resumen["tiene_voz"]
        )
    ).astype(int)

    df_valido = df_valido.merge(
        df_resumen[
            [
                "llave_documento_fecha",
                "voz_a_chat",
                "chat_a_voz"
            ]
        ],
        on="llave_documento_fecha",
        how="left"
    )

    df_contactos = df_contactos.merge(
        df_valido[
            [
                "id de contacto",
                "orden_interaccion",
                "conteo_rellamda",
                "es_rellamada",
                "conteo_recontacto",
                "orden_recontacto",
                "es_recontacto",
                "voz_a_chat",
                "chat_a_voz"
            ]
        ],
        on="id de contacto",
        how="left"
    )

    return df_contactos

def transformation_contact(
    df_contactos: pd.DataFrame,
    df_crm: pd.DataFrame,
    df_master: pd.DataFrame,
    df_opl: pd.DataFrame
) -> pd.DataFrame:
    """
    Enriquecimiento y cálculo de métricas
    de contactos.
    """

    columnas_requeridas = [
        'id de contacto',
        'id de flujo del primer contacto',
        'id de contacto inicial',
        'id del contacto anterior',
        'id de contacto siguiente',
        'canal',
        'cola',
        'perfil de enrutamiento',
        'número de teléfono del cliente',
        'número de teléfono del sistema',
        'marca de tiempo de inicio',
        'marca de tiempo de desconexión',
        'duración del contacto',
        'marca de tiempo de conexión a agente',
        'marca temporal programada',
        'marca de tiempo en cola',
        'marca de tiempo de inicio de acw',
        'marca de tiempo de fin de acw',
        'duración de la interacción del agente',
        'número de esperas',
        'método de iniciación',
        'motivo de la desconexión',
        'subtipo de canal',
        'dirección de contacto',
        'asunto del correo electrónico',
        'dirección de correo electrónico del sistema',
        'dirección de correo electrónico del cliente',
        'source_file',
        'file_create',
        'agente'
    ]

    df_contactos = df_contactos[columnas_requeridas].copy()

    columnas_normalizar = [
        "canal",
        "cola",
        "perfil de enrutamiento"
    ]

    for col in columnas_normalizar:
        df_contactos[col] = (
            df_contactos[col]
            .astype("string")
            .str.strip()
            .str.title()
            .map(lambda x: unidecode(x) if pd.notna(x) else x)
        )

#Cruce de data con CRM
    df_contactos = df_contactos.merge(
        df_crm[
            [
                "ID_LLAMADA_DE_CONTACTO",
                "NIVEL_1",
                "NIVEL_2",
                "NIVEL_3",
                "NÚMERO_DOCUMENTO_DEL_CLIENTE",
                "NOMBRE_ALIADO",
                "SOLUCION",
                "IdTipificacion",
                "MÉTODO_DE_APROBACIÓN_DE_VALIDACIÓN",
                "CÓDIGO_DE_VALIDACIÓN"
            ]
        ],
        how="left",
        left_on="id de contacto",
        right_on="ID_LLAMADA_DE_CONTACTO"
    ).drop(columns=["ID_LLAMADA_DE_CONTACTO"])
    df_contactos = df_contactos.drop_duplicates(subset=["id de contacto"])

# Cruce data MasterSkill
    df_contactos = df_contactos.merge(
        df_master[
            [
                "IdMasterSkill",
                "Canal",
                "Colas"
            ]
        ],
        how="left",
        left_on=["canal", "cola"],
        right_on=["Canal", "Colas"]
    ).drop(columns=["Canal", "Colas"])

# Cruce data OPL
    df_contactos = df_contactos.merge(
        df_opl[
            [
                "Id_opl",
                "Correo_contratista"
            ]
        ],
        how="left",
        left_on="agente",
        right_on="Correo_contratista"
    ).drop(columns=["Correo_contratista"])

# Columnas tipo fecha
    columnas_datetime = [
        "marca de tiempo de inicio",
        "marca de tiempo de desconexión",
        "marca de tiempo de conexión a agente",
        "marca de tiempo en cola",
        "marca de tiempo de inicio de acw",
        "marca de tiempo de fin de acw",
        "file_create"
    ]

    for col in columnas_datetime:
        df_contactos[col] = pd.to_datetime(
            df_contactos[col],
            errors="coerce"
        )
#Columnas llave
    df_contactos["fecha_inicio"] = (
        df_contactos["marca de tiempo de inicio"].dt.date
    )

    df_contactos["fecha_fin"] = (
        df_contactos["marca de tiempo de desconexión"].dt.date
    )

    df_contactos["llave_documento_fecha"] = (
        df_contactos["NÚMERO_DOCUMENTO_DEL_CLIENTE"].astype(str)
        + df_contactos["fecha_inicio"].astype(str)
    )

    df_contactos["llave_recontacto"] = (
        df_contactos["NÚMERO_DOCUMENTO_DEL_CLIENTE"].astype(str)
        + df_contactos["fecha_inicio"].astype(str)
        + df_contactos["IdTipificacion"].astype(str)
    )

    df_contactos = _calculate_contact_metrics(
        df_contactos
    )

    return df_contactos

def save_contacts(
    df: pd.DataFrame,
    ruta_global: str,
    ruta_local: str,
    filename: str = "05.Data_Contactos.csv"
) -> None:
    """
    Guarda contactos procesados.
    """

    df.to_csv(
        os.path.join(ruta_global, filename),
        index=False,
        encoding="utf-8"
    )

    df.to_csv(
        os.path.join(ruta_local, filename),
        index=False,
        encoding="utf-8"
    )

    print(f"Archivo guardado: {filename}")