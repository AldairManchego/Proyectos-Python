import os, sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from unidecode import unidecode
from utils.Data_BusquedaContacto.b_calculo_metricas import _calculate_contact_metrics

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
        'numero de telefono del cliente',
        'numero de telefono del sistema',
        'marca de tiempo de inicio',
        'marca de tiempo de desconexion',
        'duracion del contacto',
        'marca de tiempo de conexion a agente',
        'marca temporal programada',
        'marca de tiempo en cola',
        'marca de tiempo de inicio de acw',
        'marca de tiempo de fin de acw',
        'duracion de la interaccion del agente',
        'numero de esperas',
        'metodo de iniciacion',
        'motivo de la desconexion',
        'subtipo de canal',
        'direccion de contacto',
        'asunto del correo electronico',
        'direccion de correo electronico del sistema',
        'direccion de correo electronico del cliente',
        'source_file',
        'file_date',
        'agente'
    ]

    df_contactos = df_contactos[columnas_requeridas]
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
    columnas_datetime =[
        "marca de tiempo de inicio",
        "marca de tiempo de desconexion",
        "marca de tiempo de conexion a agente",
        "marca de tiempo en cola",
        "marca de tiempo de inicio de acw",
        "marca de tiempo de fin de acw"
        ]
    
    for col in columnas_datetime:
        df_contactos[col] = pd.to_datetime(
        df_contactos[col].astype(str).str.strip(),
        format="%d/%m/%Y %H:%M",
        errors="coerce"
        )
#Columnas llave
    df_contactos["fecha_inicio"] = df_contactos["marca de tiempo de inicio"].dt.date

    df_contactos["fecha_fin"] = df_contactos["marca de tiempo de desconexion"].dt.date

    df_contactos["llave_documento_fecha"] = ( df_contactos["NÚMERO_DOCUMENTO_DEL_CLIENTE"].astype(str) +
                                              df_contactos["fecha_inicio"].astype(str)
                                              )

    df_contactos["llave_recontacto"] = ( df_contactos["NÚMERO_DOCUMENTO_DEL_CLIENTE"].astype(str) +
                                        df_contactos["fecha_inicio"].astype(str) +
                                        df_contactos["IdTipificacion"].astype(str)
                                        )

    df_contactos = _calculate_contact_metrics(
        df_contactos
    )
    
    return df_contactos