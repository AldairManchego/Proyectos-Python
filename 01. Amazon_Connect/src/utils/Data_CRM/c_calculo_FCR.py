import csv
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode
from routes.Paths import Ruta_crm


VALIDACION_CANAL = [f.title() for f in ["chat", "voz"]]

VALIDACION_NIVEL_2 = [
    f.title()
    for f in [
        "Aclaracion",
        "Peticiones",
        "Quejas",
        "Reclamos",
        "Registro",
        "Seguridad",
    ]
]

VALIDACION_NIVEL_3 = [f.title() for f in ["seguimiento y/o solucion de pqr"]]

VALIDACION_SKILL = [
    f.title()
    for f in [
        "buzon_tienda_online",
        "personas_back office_outbound",
        "empresas_back office_outbound",
        "personas_tentativa_de_fraude",
        "buzon_clientes",
        "monitoreo_voz_outbound",
        "monitoreo_digital_outbound",
        "monitoreo_digital _outbound",
        "negocios_comprobante",
        "buzon_empresas",
        "empresas_tentativa_de_fraude",
        "personas_voz_outbound personas",
        "empresas_voz_outbound empresas",
        "buzon_tienda_aliados",
        "buzon_proteccion_de_datos",
    ]
]

VALIDACION_MOTIVO_NO_FCR = [
    f.title()
    for f in [
        "cliente no continua en la interaccion/chat",
        "se contacta tercero",
        "fuera de horario",
    ]
]

def _cruzar_arbol_tipificacion(df_crm: pd.DataFrame, df_arbol: pd.DataFrame) -> pd.DataFrame:
    """Cruza el CRM con el árbol de tipificación (Nivel 1/2/3)."""

    return df_crm.merge(
        df_arbol[
            [
                "IdTipificacion",
                "Nivel_1",
                "Nivel_2",
                "Nivel_3",
                "SPC/FCR",
                "ANS_Dias",
                "Tipo_Dia",
                "SLA_Dia",
                "SLA_TipoDia"
            ]
        ],
        how="left",
        left_on=["NIVEL_1", "NIVEL_2", "NIVEL_3"],
        right_on=["Nivel_1", "Nivel_2", "Nivel_3"],
    ).drop(columns=["Nivel_1", "Nivel_2", "Nivel_3"])


def _calcular_fcr(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Calcula CONTADOR_FCR y MAL_TIPIFICADO_FCR."""

    condiciones_fcr = (
        df_crm["CANAL_DE_ATENCIÓN"].isin(VALIDACION_CANAL)
        & df_crm["NIVEL_2"].isin(VALIDACION_NIVEL_2)
        & ~df_crm["NIVEL_3"].isin(VALIDACION_NIVEL_3)
        & ~df_crm["TIPO_DE_LLAMADA"].isin(["Contacto Salida"])
        & ~df_crm["SKILL"].isin(VALIDACION_SKILL)
        & ~df_crm["MOTIVO_NO_FCR"].isin(VALIDACION_MOTIVO_NO_FCR)
    )

    df_crm["CONTADOR_FCR"] = np.where(condiciones_fcr, 1, 0)

    condicion_mal_tipificado = (
        (df_crm["SPC/FCR"].notna())
        & (df_crm["CONTADOR_FCR"] > 0)
        & (df_crm["SE_RESOLVIÓ_EL_CONTACTO"] != df_crm["SPC/FCR"])
    )

    df_crm["MAL_TIPIFICADO_FCR"] = np.where(condicion_mal_tipificado, 1, 0)

    return df_crm