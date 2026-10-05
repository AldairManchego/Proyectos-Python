import os
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode

from routes.Paths import (
    Ruta_crm_ventas,
    Ruta_busquedad_contacto,
    Ruta_masterskill,
    Ruta_opl,
    Ruta_historico_arbol,
    Ruta_global,
    Ruta_local,
)

from utils.Processing_OPL import data_opl
from utils.Processing_MasterSkill import limpiar_masterskill
from utils.functions import load_files_from_folder
from utils.Data_CRM.a_carga_data import load_files
from utils.Data_ModeloComercial.a_processing_arbol_tip_historico import (
    _load_arbol_historico,
)


COLUMNAS_CRM_VENTAS = [
    "NÚMERO_DOCUMENTO_DEL_CLIENTE",
    "RADICADO",
    "IdTipificacion",
    "NIVEL_1",
    "NIVEL_2",
    "NIVEL_3",
    "TIPO_DE_LLAMADA",
    "NOMBRE_CLIENTE",
    "CONTACTO_DE_CLIENTE",
    "NOMBRE_ALIADO",
    "Id_opl",
    "NOMBRE_ASESOR",
    "Correo_contratista",
    "FECHA_DE_INICIO",
    "START_DATE",
    "FECHA_FIN",
    "END_DATE",
    "START_MONTH_DATE",
    "OFRECIMIENTO_EFECTIVO",
    "Aplica_Ofrecimiento",
    "VALOR_PUNTOS",
    "CANAL_DE_ATENCIÓN",
    "Colas",
    "SKILL",
    "IdMasterSkill",
    "ESTADO_GESTIÓN",
    "NÚMERO_PEDIDO",
]


def preparar_crm(
    df_crm: pd.DataFrame
) -> pd.DataFrame:

    excluir_registros = [
        "CHAT DE PRUEBA",
        "LLAMADA DE PRUEBA",
        "PRUEBAS PCO",
    ]

    columnas_fecha = [
        "FECHA_DE_INICIO",
        "FECHA_FIN",
        "FECHA_ÚLTIMO_CAMBIO",
        "CREATION_FILE_DATE",
    ]

    columnas_numero = [
        "EN_DIAS",
        "SLA_DIAS",
        "VALOR_PUNTOS",
        "VALOR_DINERO",
    ]

    df_crm = (
        df_crm[
            ~df_crm["SUBTIPO"].isin(excluir_registros)
        ]
        .copy()
    )

    for col in df_crm.columns:

        if col not in columnas_fecha:

            df_crm[col] = (
                df_crm[col]
                .astype("string")
                .str.strip()
                .map(
                    lambda x:
                    unidecode(x)
                    if pd.notna(x)
                    else x
                )
            )

    df_crm = df_crm.rename(
        columns={
            "PRODUCTO": "NIVEL_1",
            "TIPO": "NIVEL_2",
            "SUBTIPO": "NIVEL_3",
        }
    )

    condiciones_canal = [
        df_crm["CANAL_DE_ATENCIÓN"].isin(
            ["Whatsapp", "Chat", "Pagina Web"]
        ),
        df_crm["CANAL_DE_ATENCIÓN"].isin(
            ["Telefonico"]
        ),
        df_crm["CANAL_DE_ATENCIÓN"].isin(
            ["Correo Electronico"]
        ),
    ]

    df_crm["CANAL_DE_ATENCIÓN"] = np.select(
        condiciones_canal,
        ["Chat", "Voz", "Correo"],
        default="Otros",
    )

    # Ajuste UTC/Zulu -> Hora Colombia

    for col in columnas_fecha:

        df_crm[col] = (
            pd.to_datetime(
                df_crm[col],
                utc=True,
                errors="coerce",
            )
            .dt.tz_convert("America/Bogota")
            .dt.tz_localize(None)
        )

    for col in columnas_numero:

        df_crm[col] = (
            pd.to_numeric(
                df_crm[col],
                errors="coerce",
            )
            .fillna(0)
        )

    df_crm["START_DATE"] = (
        df_crm["FECHA_DE_INICIO"]
        .dt.date
    )

    df_crm["END_DATE"] = (
        df_crm["FECHA_FIN"]
        .dt.date
    )

    df_crm["START_MONTH_DATE"] = (
        df_crm["FECHA_DE_INICIO"]
        .dt.to_period("M")
        .dt.to_timestamp()
        .dt.date
    )

    df_crm["ID_LLAMADA_DE_CONTACTO"] = (
        df_crm["ID_LLAMADA_DE_CONTACTO"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    df_crm["NÚMERO_DOCUMENTO_DEL_CLIENTE"] = (
        df_crm["NÚMERO_DOCUMENTO_DEL_CLIENTE"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_crm["Prioridad"] = (
        df_crm["OFRECIMIENTO_EFECTIVO"]
        .map(
            {
                "Si": 1,
                "No": 2,
            }
        )
        .fillna(99)
        .astype(int)
    )

    df_crm = df_crm.sort_values(
        by=[
            "NÚMERO_DOCUMENTO_DEL_CLIENTE",
            "START_DATE",
            "Prioridad",
        ]
    )

    return df_crm


def cargar_insumos():

    require_columns_contacts = {
        "id de contacto",
        "canal",
        "marca de tiempo de inicio",
        "cola",
        "agente",
        "marca de tiempo de desconexion",
        "marca de tiempo de conexion a agente",
        "marca de tiempo en cola",
        "marca de tiempo de inicio de acw",
        "marca de tiempo de fin de acw",
    }

    df_contactos = load_files_from_folder(
        Ruta_busquedad_contacto,
        require_columns_contacts,
        ["id de contacto"],
    )

    df_contactos = df_contactos[
        ~df_contactos["cola"].isna()
    ]

    df_master = limpiar_masterskill(
        pd.read_excel(
            Ruta_masterskill,
            sheet_name="TB",
        )
    )

    df_opl = data_opl(
        pd.read_excel(
            Ruta_opl,
            sheet_name="Combinado",
        )
    )

    df_arbol_hist = _load_arbol_historico(
        Ruta_historico_arbol
    )

    df_crm = preparar_crm(
        load_files(
            Ruta_crm_ventas
        )
    )

    return (
        df_crm,
        df_contactos,
        df_arbol_hist,
        df_master,
        df_opl,
    )


def transformar_crm_ventas(
    df_crm: pd.DataFrame,
    df_contactos: pd.DataFrame,
    df_arbol_hist: pd.DataFrame,
    df_master: pd.DataFrame,
    df_opl: pd.DataFrame,
) -> pd.DataFrame:

    df_crm = df_crm.copy()

    df_crm = df_crm.merge(
        df_contactos[
            [
                "id de contacto",
                "agente",
                "cola",
            ]
        ],
        how="left",
        left_on="ID_LLAMADA_DE_CONTACTO",
        right_on="id de contacto",
    ).drop(
        columns=["id de contacto"]
    )

    df_crm = df_crm.merge(
        df_arbol_hist[
            [
                "IdTipificacion",
                "Nivel_1",
                "Nivel_2",
                "Nivel_3",
                "BO_Asignado",
                "Aplica_Ofrecimiento",
                "source_file",
            ]
        ],
        how="left",
        left_on=[
            "NIVEL_1",
            "NIVEL_2",
            "NIVEL_3",
            "START_MONTH_DATE",
        ],
        right_on=[
            "Nivel_1",
            "Nivel_2",
            "Nivel_3",
            "source_file",
        ],
    ).drop(
        columns=[
            "Nivel_1",
            "Nivel_2",
            "Nivel_3",
            "source_file",
        ]
    )

    df_crm = df_crm.merge(
        df_master[
            [
                "IdMasterSkill",
                "Canal",
                "Colas",
            ]
        ],
        how="left",
        left_on=[
            "CANAL_DE_ATENCIÓN",
            "cola",
        ],
        right_on=[
            "Canal",
            "Colas",
        ],
    ).drop(
        columns=[
            "Canal",
            "cola",
        ]
    )

    df_crm = df_crm.merge(
        df_opl[
            [
                "Id_opl",
                "Correo_contratista",
            ]
        ],
        how="left",
        left_on="agente",
        right_on="Correo_contratista",
    ).drop(
        columns=["agente"]
    )

    return df_crm


def guardar_crm(
    df_crm: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "10.Data_CRM_Ventas.csv",
) -> None:

    df_crm.to_csv(
        os.path.join(
            ruta_global,
            nombre_archivo,
        ),
        index=False,
        encoding="utf-8",
    )

    df_crm.to_csv(
        os.path.join(
            ruta_local,
            nombre_archivo,
        ),
        index=False,
        encoding="utf-8",
    )


def process_crm_ventas(
    save_file: bool = False,
) -> pd.DataFrame:

    (
        df_crm,
        df_contactos,
        df_arbol_hist,
        df_master,
        df_opl,
    ) = cargar_insumos()

    df_crm = transformar_crm_ventas(
        df_crm=df_crm,
        df_contactos=df_contactos,
        df_arbol_hist=df_arbol_hist,
        df_master=df_master,
        df_opl=df_opl,
    )

    if save_file:

        guardar_crm(
            df_crm=df_crm,
            ruta_global=Ruta_global,
            ruta_local=Ruta_local,
        )

    return df_crm