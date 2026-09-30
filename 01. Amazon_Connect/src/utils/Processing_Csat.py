import pandas as pd, numpy as np
from pathlib import Path
from unidecode import unidecode
import sys, os, csv
from datetime import datetime, time

from routes.Paths import (
    Ruta_busquedad_contacto,
    Ruta_arbol_tipificacion,
    Ruta_opl,
    Ruta_festivos,
    Ruta_masterskill,
    Ruta_crm,
    Ruta_Comentarios,
    Ruta_Csat_2,
    Ruta_Csat_3,
    Ruta_Csat_4,
    Ruta_local,
    Ruta_global
)

from utils.Processing_OPL import data_opl
from utils.functions import load_files_from_folder
from utils.Processing_MasterSkill import limpiar_masterskill
from utils.Processing_OPL import data_opl
from utils.Processing_Arbol import limpiar_df_arbol
from utils.Processing_data_comentarios import _transformacion_comentarios
from utils.Data_CRM.a_carga_data import load_files
from utils.Data_CRM.e_final_data_crm import transform_crm

def load_data_csat():
    df_opl = data_opl(pd.read_excel(Ruta_opl, sheet_name="Combinado"))
    df_opl["Nombre_Agente"] = df_opl["Nombre_Agente"].astype(str).str.lower()
    # Condiciones para data CSAT
    required_columns = {
        "sessionid",
        "agentname",
        "queue"
    }
    delete_dup_subset = ["sessionid"]

    # Condiciones para ContacSearch
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
        "marca de tiempo de fin de acw"
    }

    delete_dup_columns_contacts = ["id de contacto"]
    df_contactos = load_files_from_folder(
    Ruta_busquedad_contacto,
    require_columns_contacts,
    delete_dup_columns_contacts
)

    df_contactos = df_contactos[~df_contactos["cola"].isna()]
    df_master = limpiar_masterskill(pd.read_excel(Ruta_masterskill, sheet_name="TB"))
    df_arbol = limpiar_df_arbol(pd.read_excel(Ruta_arbol_tipificacion, sheet_name='Tipificación Vista360'))
    df_comentarios = _transformacion_comentarios(Ruta_Comentarios)
    df_festivos = (
        pd.to_datetime( pd.read_csv(Ruta_festivos)["Fecha"], format= "%d/%m/%Y")
        .drop_duplicates()
        .values.astype("datetime64[D]")
    )

    df_crm = transform_crm(
        load_files(Ruta_crm),
        df_arbol,
        df_festivos,
        df_contactos,
        df_opl,
        df_master,
        df_comentarios)
        
    df_csat_2 = load_files_from_folder(
    Ruta_Csat_2,
    required_columns,
    delete_dup_subset
)

    df_csat_2 = df_csat_2.rename(columns={
        "question0":"Acepta_encuesta",
        "question1":"CSAT",
        "question2":"Facilidad",
        "question3":"Hubo_solucion",
        "question4":"Cliente_acepta_comentario",
        "question5":"Comentario_cliente",
    })
    df_csat_3 = load_files_from_folder(
        Ruta_Csat_3,
        required_columns,
        delete_dup_subset
    )
    df_csat_3 = df_csat_3.rename(columns={
        "question0":"Acepta_encuesta",
        "question1":"Empatia",
        "question2":"CSAT",
        "question3":"Hubo_solucion",
        "question4":"Cliente_acepta_comentario",
        "question5":"Comentario_cliente",
    })

    df_csat_4 = load_files_from_folder(
        Ruta_Csat_4,
        required_columns,
        delete_dup_subset
    )
    df_csat_4 = df_csat_4.rename(columns={
        "question0":"Acepta_encuesta",
        "question1":"Hubo_solucion",
        "question2":"Empatia",
        "question3":"CSAT",
        "question4":"Cliente_acepta_comentario",
        "question5":"Comentario_cliente",
    })
    df_csat = pd.concat([df_csat_2, df_csat_3, df_csat_4], ignore_index=True).drop_duplicates()

    return (
        df_csat,
        df_contactos,
        df_crm,
        df_opl,
        df_arbol,
        df_master
    )

def calcular_csat(        
    df_csat: pd.DataFrame,
    df_contactos: pd.DataFrame,
    df_crm: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_arbol: pd.DataFrame,
    df_master: pd.DataFrame
)->pd.DataFrame:
    df_csat["updatedat"] = pd.to_datetime(
    df_csat["updatedat"],
    format="%Y-%m-%dT%H:%M:%S.%fZ",
    errors="coerce"
    ).dt.date

    df_csat = df_csat[df_csat["queue"].notna()]
    df_csat["queue"] = df_csat["queue"].str.title()
    df_csat["agentname"] = df_csat["agentname"].str.lower()

    df_csat = df_csat.merge(
    df_contactos[[
        "id de contacto",
         "canal",
         "agente",
         "duracion de la interaccion del agente",
         "marca de tiempo de inicio"]],
         how = "left",
         left_on= ["sessionid"],
         right_on=["id de contacto"]
).drop(columns=["id de contacto","documenttype"])

    df_csat = df_csat.merge(
        df_crm[[
            "ID_LLAMADA_DE_CONTACTO",
            "RADICADO",
            "IdTipificacion",
            "NIVEL_1",
            "NIVEL_2",
            "NIVEL_3",
            "NÚMERO_DOCUMENTO_DEL_CLIENTE",
            "NOMBRE_CLIENTE",
            "NOMBRE_ALIADO",
            "NÚMERO_PEDIDO",
            "CUMPLIMIENTO_ANS",
            "CUMPLIMIENTO_SLA",
            "COMENTARIO",
            "SOLUCION"
        ]],
        how="left",
        left_on="sessionid",
        right_on="ID_LLAMADA_DE_CONTACTO"
    ).drop(columns=["ID_LLAMADA_DE_CONTACTO"])

    df_csat = df_csat.merge(
        df_master[[
            "IdMasterSkill",
            "Canal",
            "Colas"
        ]],
        how="left",
        left_on=["canal", "queue"],
        right_on=["Canal", "Colas"]
    ).drop(columns=["Canal", "Colas"])

    df_csat = df_csat.merge(
        df_opl[[
            "Id_opl",
            "Nombre_Agente"
        ]],
        how="left",
        left_on="agentname",
        right_on="Nombre_Agente"
    ).drop(columns=["Nombre_Agente"])

    df_csat.columns = (df_csat.columns.astype(str)
                        .str.lower()
                        .str.strip()
                        .str.replace(" ", "_", regex=False)
                        .map(unidecode))
    return df_csat

def guardar_data_csat(
        df_aux: pd.DataFrame,
        file_name: str = "08.Data_Csat.csv")-> None:

        df_aux.to_csv(os.path.join(Ruta_global, file_name), index=False, encoding="utf-8")
        df_aux.to_csv(os.path.join(Ruta_local, file_name), index=False, encoding="utf-8")

def ejecutar_csat() -> pd.DataFrame:
    (
        df_csat,
        df_contactos,
        df_crm,
        df_opl,
        df_arbol,
        df_master
    ) = load_data_csat()

    resultado = calcular_csat(
        df_csat=df_csat,
        df_contactos=df_contactos,
        df_crm=df_crm,
        df_opl=df_opl,
        df_arbol=df_arbol,
        df_master=df_master
    )
    
    guardar_data_csat(resultado)

    return resultado