import pandas as pd
import numpy as np
from pathlib import Path
import os

from routes.Paths import(
    Ruta_Soat,
    Ruta_global,
    Ruta_local
)

from utils.functions import load_files_from_folder
from utils.Data_ModeloComercial.b_processing_crm_ventas import process_crm_ventas

columnas_crm_requeridas = [
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
        "NÚMERO_PEDIDO"
    ]

columns_soat =[
    "fecha_homologada",
    "nro_documento",
    "puntos redimidos",
    "pagado dinero",
    "puntos red dinero",
    "source_file",
    "file_date"
]

def cargar_insumos() -> tuple[
    pd.DataFrame,
    pd.DataFrame
    ]:

    """Carga df Soat"""
    required_columns =[
    "fecha_homologada",
    "nro_documento",
    "puntos redimidos",
    "pagado dinero",
    "puntos red dinero"
    ]

    df_soat = load_files_from_folder(
        Ruta_Soat,
        set(required_columns),
        required_columns
        )
    df_soat = df_soat[columns_soat]
    columnas_datetime =["file_date", "fecha_homologada"]
    for col in columnas_datetime:
        df_soat[col] = pd.to_datetime(df_soat[col],
                                    format="mixed",
                                    utc=True,
                                    errors="coerce").dt.tz_localize(None)
    df_soat["date"] = df_soat["fecha_homologada"].dt.date
    df_soat = df_soat.sort_values(by=["nro_documento", "fecha_homologada"], ascending=[True, False]).reset_index(drop=True)
    df_soat["nro_documento"] = df_soat["nro_documento"].astype(str)

    columnas_numericas = ["pagado dinero","puntos red dinero"]
    for col in columnas_numericas:
        df_soat[col] = (
            df_soat[col]
            .astype(str)
            .str.strip()
            .str.replace("$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        df_soat[col] = pd.to_numeric(
            df_soat[col],
            errors="coerce"
        ).fillna(0)

    df_soat["Total_Ventas"] = (
        df_soat["pagado dinero"] +
        df_soat["puntos red dinero"]
    )

    """Carga crm"""
    df_crm = process_crm_ventas(save_file = False)
    df_crm["FECHA_DE_INICIO"] = pd.to_datetime(
    df_crm["FECHA_DE_INICIO"],
    errors="coerce"
    )

    df_crm["FECHA_FIN"] = pd.to_datetime(
        df_crm["FECHA_FIN"],
        errors="coerce"
    )

    df_crm["Prioridad"] = (
        df_crm["OFRECIMIENTO_EFECTIVO"]
            .map({"Si": 1, "No": 2})
    )

    df_crm = df_crm.sort_values(
        by=[
            "NÚMERO_DOCUMENTO_DEL_CLIENTE",
            "START_DATE",
            "Prioridad"
        ]
    )
    df_crm["NÚMERO_DOCUMENTO_DEL_CLIENTE"] = df_crm["NÚMERO_DOCUMENTO_DEL_CLIENTE"].astype(str)

    return(
        df_soat, df_crm
    )

def transformar_soat_ventas(
    df_soat: pd.DataFrame,
    df_crm: pd.DataFrame
)-> pd.DataFrame:

    df_soat = df_soat.copy()
    df_crm = df_crm.copy()

    df_soat = df_soat.merge(
        df_crm[columnas_crm_requeridas],
            how="left",
            left_on=[
                "nro_documento",
                "date"
            ],
            right_on=[
                "NÚMERO_DOCUMENTO_DEL_CLIENTE",
                "START_DATE"
            ]
        ).drop(columns=["NÚMERO_DOCUMENTO_DEL_CLIENTE","START_DATE"])

    df_soat["HORAS_DESDE_INICIO"] = ((df_soat["fecha_homologada"] - df_soat["FECHA_DE_INICIO"]).dt.total_seconds()/3600).round(2)
    df_soat["HORAS_DESDE_FIN"] = ((df_soat["fecha_homologada"] - df_soat["FECHA_FIN"]).dt.total_seconds()/3600).round(2)

    df_soat["VALIDACION_VENTA"] = np.where(
        (df_soat["OFRECIMIENTO_EFECTIVO"].eq("Si")) & 
        (df_soat["HORAS_DESDE_INICIO"].between(0, 24) | df_soat["HORAS_DESDE_FIN"].between(0, 24)),
        "Venta efectiva",
        "Venta no efectiva"
    )
    return df_soat

def guardar_crm(
    df_soat: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "12.Data_Soat_Ventas.csv",
) -> None:
    
    """Guarda la data de Soat como CSV en ambas rutas (global y local)."""

    df_soat.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_soat.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


def process_soat_ventas(
    save_file: bool = False,
) -> pd.DataFrame:

    df_soat, df_crm = cargar_insumos()
    df_soat = transformar_soat_ventas(
        df_soat=df_soat,
        df_crm=df_crm
    )

    if save_file:
        guardar_crm(
            df_soat,
            Ruta_global,
            Ruta_local,
        )
    return df_soat