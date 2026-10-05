import pandas as pd
import numpy as np
from pathlib import Path
import os

from routes.Paths import(
    Ruta_Bonos,
    Ruta_global,
    Ruta_local
)
from utils.functions import load_files_from_folder

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

columns_bonos = [
    "supplier",
    "order_id",
    "order_date",
    "numero documento",
    "puntos",
    "source_file",
    "file_date"
]

def cargar_insumos() -> pd.DataFrame:

    """Carga y preparacion df Bonos"""

    Required_columns = [
        "supplier",
        "order_id",
        "order_date",
        "numero documento"
        ]

    df_bonos = load_files_from_folder(
        Ruta_Bonos, 
        set(Required_columns),
        Required_columns)
    df_bonos = df_bonos[columns_bonos]
    df_bonos["order_date"] = pd.to_datetime(df_bonos["order_date"],
                                            format="mixed",
                                            utc=True, 
                                            errors="coerce").dt.tz_localize(None)

    df_bonos["date"] = df_bonos["order_date"].dt.date
    df_bonos = df_bonos.sort_values(by=["numero documento", "order_date"], ascending=[True, False]).reset_index(drop=True)
    df_bonos["numero documento"] = (
        df_bonos["numero documento"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    return df_bonos

def transformar_bonos_venta(
        df_bonos: pd.DataFrame,
        df_crm: pd.DataFrame
) -> pd.DataFrame:
    
    df_bonos = df_bonos.copy()

    df_bonos = df_bonos.merge(
    df_crm[COLUMNAS_CRM_VENTAS],
    how="left",
    left_on=[
        "numero documento",
        "date"
        ],
    right_on=[
        "NÚMERO_DOCUMENTO_DEL_CLIENTE",
        "START_DATE"
    ]
    ).drop(columns=["NÚMERO_DOCUMENTO_DEL_CLIENTE","START_DATE"])

    df_bonos["HORAS_DESDE_INICIO"] = ((df_bonos["order_date"] - df_bonos["FECHA_DE_INICIO"]).dt.total_seconds()/3600).round(2)
    df_bonos["HORAS_DESDE_FIN"] = ((df_bonos["order_date"] - df_bonos["FECHA_FIN"]).dt.total_seconds()/3600).round(2)

    df_bonos["VALIDACION_VENTA"] = np.where(
        (df_bonos["OFRECIMIENTO_EFECTIVO"].eq("Si")) & 
        (df_bonos["HORAS_DESDE_INICIO"].between(0, 24) | df_bonos["HORAS_DESDE_FIN"].between(0, 24)),
        "Venta efectiva",
        "Venta no efectiva"
    )
    return df_bonos

def guardar_bonos(
    df_bonos: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "11.Data_Bonos_Ventas.csv",
) -> None:
    """Guarda la data de Bonos como CSV en ambas rutas (global y local)."""

    df_bonos.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_bonos.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


def process_bonos_ventas(
    df_crm: pd.DataFrame,
    save_file: bool = False,
) -> pd.DataFrame:

    df_bonos = cargar_insumos()

    df_bonos = transformar_bonos_venta(
        df_bonos=df_bonos,
        df_crm=df_crm,
    )

    if save_file:

        guardar_bonos(
            df_bonos=df_bonos,
            ruta_global=Ruta_global,
            ruta_local=Ruta_local,
        )

    return df_bonos