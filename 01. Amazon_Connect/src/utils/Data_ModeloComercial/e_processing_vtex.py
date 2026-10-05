import pandas as pd
import numpy as np
from pathlib import Path
import os

from routes.Paths import(
    Ruta_Vtex,
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

required_columns = [
    "order",
     "sequence",
     "creation date",
     "client document",
     "client name",
     "client last name",
     "quantity_sku",
     "total value",
     "shipping value",
     "sku total price",
     "sla type",
     "courrier",
     "estimate delivery date",
     "payment value"
]

def cargar_insumos() -> pd.DataFrame:

    """Carga df Vtex"""

    df_vtex = load_files_from_folder(
        Ruta_Vtex,
        set(required_columns),
        required_columns
    )

    columns_vtex = [
        "order",
        "sequence",
        "creation date",
        "client document",
        "client name",
        "client last name",
        "quantity_sku",
        "total value",
        "shipping value",
        "sku total price",
        "sla type",
        "courrier",
        "estimate delivery date",
        "payment value",
        "source_file",
        "file_date"
    ]

    df_vtex = df_vtex[columns_vtex]

    date_time_columns = ["creation date", "estimate delivery date", "file_date"]
    for col in date_time_columns:
        df_vtex[col] = pd.to_datetime(df_vtex[col],
                                    format="mixed",
                                    utc=True,
                                    errors="coerce").dt.tz_localize(None)
        
    df_vtex["Total_Venta"] = (df_vtex["shipping value"] + df_vtex["sku total price"]).round(2)
    df_vtex["date"] = df_vtex["creation date"].dt.date
    df_vtex = df_vtex.sort_values(by=["client document", "creation date"], ascending=[True, False]).reset_index(drop=True)
    df_vtex["client document"] = df_vtex["client document"].astype(str)

    return df_vtex

def transformar_vtex_ventas(
    df_vtex: pd.DataFrame,
    df_crm: pd.DataFrame
)-> pd.DataFrame:

    df_vtex = df_vtex.copy()
    df_vtex = df_vtex.merge(
    df_crm[columnas_crm_requeridas],
        how="left",
        left_on=[
            "client document",
            "date"
        ],
        right_on=[
            "NÚMERO_DOCUMENTO_DEL_CLIENTE",
            "START_DATE"
        ]
    ).drop(columns=["NÚMERO_DOCUMENTO_DEL_CLIENTE","START_DATE"])

    df_vtex["HORAS_DESDE_INICIO"] = ((df_vtex["creation date"] - df_vtex["FECHA_DE_INICIO"]).dt.total_seconds()/3600).round(2)
    df_vtex["HORAS_DESDE_FIN"] = ((df_vtex["creation date"] - df_vtex["FECHA_FIN"]).dt.total_seconds()/3600).round(2)

    df_vtex["VALIDACION_VENTA"] = np.where(
        (df_vtex["OFRECIMIENTO_EFECTIVO"].eq("Si")) & 
        (df_vtex["HORAS_DESDE_INICIO"].between(0, 24) | df_vtex["HORAS_DESDE_FIN"].between(0, 24)),
        "Venta efectiva",
        "Venta no efectiva"
    )
    return df_vtex

def guardar_vtex(
    df_vtex: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "13.Data_Vtex_Ventas.csv",
) -> None:
    
    """Guarda la data de Bonos como CSV en ambas rutas (global y local)."""

    df_vtex.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_vtex.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


def process_vtex_ventas(
    df_crm: pd.DataFrame,
    save_file: bool = False,
) -> pd.DataFrame:

    df_vtex = cargar_insumos()
    df_vtex = transformar_vtex_ventas(
        df_vtex=df_vtex,
        df_crm=df_crm
    )

    if save_file:
        guardar_vtex(
            df_vtex=df_vtex,
            ruta_global=Ruta_global,
            ruta_local=Ruta_local,
        )
    return df_vtex