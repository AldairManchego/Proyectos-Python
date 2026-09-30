import pandas as pd
from pathlib import Path
import os
from routes.Paths import(
    Ruta_masterskill, 
    Ruta_opl,
    Ruta_busquedad_contacto,
    Ruta_festivos,
    Ruta_crm_ventas,
    Ruta_global, Ruta_local,
    Ruta_historico_arbol
)

from utils.Processing_OPL import data_opl
from utils.Processing_MasterSkill import limpiar_masterskill
from utils.functions import load_files_from_folder
from utils.Data_CRM.a_carga_data import load_files
from utils.Data_CRM.b_limpieza_columnas import _limpiar_columnas_crm, _clasificar_canal, _normalizar_fechas_numeros
from utils.Data_ModeloComercial.a_processing_arbol_tip_historico import _load_arbol_historico

def cargar_insumos() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame
]:
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

    delete_dup_columns_contacts = ["id de contacto"]

    df_contactos = load_files_from_folder(
        Ruta_busquedad_contacto,
        require_columns_contacts,
        delete_dup_columns_contacts,
    )

    df_contactos = df_contactos[
        ~df_contactos["cola"].isna()
    ]

    df_master = limpiar_masterskill(
        pd.read_excel(
            Ruta_masterskill,
            sheet_name="TB"
        )
    )

    df_opl = data_opl(
        pd.read_excel(
            Ruta_opl,
            sheet_name="Combinado"
        )
    )

    df_arbol_hist = _load_arbol_historico(
        Ruta_historico_arbol
    )

    df_crm = _normalizar_fechas_numeros(
        _clasificar_canal(
            _limpiar_columnas_crm(
                load_files(Ruta_crm_ventas)
            )
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

    df_crm["ID_LLAMADA_DE_CONTACTO"] = (
        df_crm["ID_LLAMADA_DE_CONTACTO"]
        .str.lower()
    )

    df_crm = df_crm.merge(
    df_contactos[
        ["id de contacto", "agente", "cola"]
    ],
    how="left",
    left_on="ID_LLAMADA_DE_CONTACTO",
    right_on="id de contacto",
).drop(columns=["id de contacto"])

    

    df_crm["START_MONTH_DATE"] = (
    df_crm["FECHA_DE_INICIO"]
    .dt.to_period("M")
    .dt.to_timestamp()
    .dt.date
)
    df_crm = df_crm.merge(
    df_arbol_hist[[
        "IdTipificacion",
        "Nivel_1",
        "Nivel_2",
        "Nivel_3",
        "BO_Asignado",
        "Aplica_Ofrecimiento",
        "source_file"
    ]],
    how = "left",
    left_on = ["NIVEL_1", "NIVEL_2", "NIVEL_3", "START_MONTH_DATE"],
    right_on = ["Nivel_1", "Nivel_2", "Nivel_3", "source_file"],
).drop(columns=["Nivel_1", "Nivel_2", "Nivel_3", "source_file"])

    df_crm = df_crm.merge(
    df_master[[
        "IdMasterSkill",
        "Canal",
        "Colas"
    ]],
    how = "left",
    left_on = ["CANAL_DE_ATENCIÓN","cola"],
    right_on = ["Canal", "Colas"]
).drop(columns=["Canal","cola"])

    df_crm = df_crm.merge(
    df_opl[[
        "Id_opl",
        "Correo_contratista"
    ]],
    how = "left",
    left_on = ["agente"],
    right_on = ["Correo_contratista"]
).drop(columns=["agente"])

    return df_crm

def guardar_crm(
    df_crm: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "10.Data_CRM_Ventas.csv",
) -> None:
    """Guarda el CRM final como CSV en ambas rutas (global y local)."""

    df_crm.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_crm.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


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
            df_crm,
            Ruta_global,
            Ruta_local,
        )

    return df_crm