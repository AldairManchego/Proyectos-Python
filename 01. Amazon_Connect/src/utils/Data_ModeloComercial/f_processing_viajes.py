import pandas as pd
import numpy as np
from pathlib import Path
import os

from routes.Paths import(
    Ruta_Viajes,
    Ruta_global,
    Ruta_local
)
from utils.functions import load_files_from_folder

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

required_columns =[
"fecha",
"hora",
"agencia",
"estado",
"servicios",
"tipo",
"total dinero",
"numero de documento del titular"
]

def cargar_insumos() -> pd.DataFrame: 

    """Carga df Viajes"""
    df_viajes = load_files_from_folder(
        Ruta_Viajes,
        set(required_columns),
        required_columns
    )

    df_viajes["fecha_transaccion"] = pd.to_datetime(
                                        df_viajes["fecha"].astype(str) + " " + df_viajes["hora"].astype(str)
    )
    columns_viajes =[
    "fecha_transaccion",
    "fecha",
    "agencia",
    "estado",
    "servicios",
    "tipo",
    "total dinero",
    "numero de documento del titular",
    "source_file",
    "file_date"
    ]

    df_viajes = df_viajes[columns_viajes]

    df_viajes = df_viajes.rename(columns={
        "fecha":"date",
        "numero de documento del titular":"documento_cliente",
    })

    df_viajes["documento_cliente"] = df_viajes["documento_cliente"].astype(str)
    df_viajes["date"] = pd.to_datetime(df_viajes["date"]).dt.date
    df_viajes["servicios"] = pd.to_numeric(df_viajes["servicios"])

    return df_viajes
    


def transformar_viajes_ventas(
    df_viajes: pd.DataFrame,
    df_crm: pd.DataFrame
)-> pd.DataFrame:

    df_viajes = df_viajes.copy()
    df_viajes = df_viajes.merge(
        df_crm[columnas_crm_requeridas],
            how="left",
            left_on=[
                "documento_cliente",
                "date"
            ],
            right_on=[
                "NÚMERO_DOCUMENTO_DEL_CLIENTE",
                "START_DATE"
            ]
        ).drop(columns=["NÚMERO_DOCUMENTO_DEL_CLIENTE","START_DATE"])

    df_viajes["HORAS_DESDE_INICIO"] = ((df_viajes["fecha_transaccion"] - df_viajes["FECHA_DE_INICIO"]).dt.total_seconds()/3600).round(2)
    df_viajes["HORAS_DESDE_FIN"] = ((df_viajes["fecha_transaccion"] - df_viajes["FECHA_FIN"]).dt.total_seconds()/3600).round(2)

    df_viajes["VALIDACION_VENTA"] = np.where(
        (df_viajes["OFRECIMIENTO_EFECTIVO"].eq("Si")) & 
        (df_viajes["HORAS_DESDE_INICIO"].between(0, 24) | df_viajes["HORAS_DESDE_FIN"].between(0, 24)),
        "Venta efectiva",
        "Venta no efectiva"
    )

    return df_viajes

def guardar_viajes(
    df_viajes: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "14.Data_Viajes_Ventas.csv",
) -> None:
    
    """Guarda la data de Bonos como CSV en ambas rutas (global y local)."""

    df_viajes.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_viajes.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


def process_viajes_ventas(
    df_crm: pd.DataFrame,
    save_file: bool = False,
) -> pd.DataFrame:

    df_viajes = cargar_insumos()
    df_viajes = transformar_viajes_ventas(
        df_viajes=df_viajes,
        df_crm=df_crm
    )

    if save_file:
        guardar_viajes(
            df_viajes=df_viajes,
            ruta_global=Ruta_global,
            ruta_local=Ruta_local,
        )
    return df_viajes