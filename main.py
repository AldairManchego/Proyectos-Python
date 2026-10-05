import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

SRC_PATH = (
    Path(__file__).parent
    / "01. Amazon_Connect"
    / "src"
)

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from routes.Paths import (
    Ruta_busquedad_contacto,
    Ruta_arbol_tipificacion,
    Ruta_opl,
    Ruta_festivos,
    Ruta_masterskill,
    Ruta_crm,
    Ruta_Comentarios,
    Ruta_local,
    Ruta_global
)

from utils.Processing_OPL import data_opl, guardar_opl
from utils.Processing_OPL_Historico import procesar_opl
from utils.Processing_Arbol import limpiar_df_arbol, guardar_arbol

from utils.Processing_MasterSkill import limpiar_masterskill, guardar_masterskill
from utils.Processing_data_comentarios import _transformacion_comentarios

from utils.functions import load_files_from_folder
from utils.Data_BusquedaContacto.c_limpieza_columnas import transformation_contact

from utils.Data_BusquedaContacto.d_save_final_file import save_contacts
from utils.Data_CRM.a_carga_data import load_files

from utils.Data_CRM.e_final_data_crm import transform_crm, guardar_crm

from utils.Processing_Auxiliares import ejecutar_auxiliares

from utils.Processing_KpiOverAll import ejecutar_kpioverall

from utils.Processing_Csat import ejecutar_csat


from routes.Paths import Ruta_historico_arbol
from utils.Data_ModeloComercial.a_processing_arbol_tip_historico import _load_arbol_historico, guardar_arbol_historico
from utils.Data_ModeloComercial.a_processing_crm import process_crm_ventas
from utils.Data_ModeloComercial.c_processing_bonos import process_bonos_ventas 
from utils.Data_ModeloComercial.d_processing_soat import process_soat_ventas
from utils.Data_ModeloComercial.e_processing_vtex import process_vtex_ventas
from utils.Data_ModeloComercial.f_processing_viajes import process_viajes_ventas

def log_step(mensaje: str) -> None:
    """
    Imprime mensajes con timestamp para seguimiento
    del proceso.
    """
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {mensaje}"
    )

def main():

    inicio = datetime.now()

    try:

# CARGA DE MAESTRAS

        log_step("Cargando árbol de tipificación")
        df_arbol = limpiar_df_arbol( pd.read_excel( Ruta_arbol_tipificacion, sheet_name="Tipificación Vista360" ))
        log_step(f"Árbol cargado. Registros: {len(df_arbol):,}")

        # ==================================================
        log_step("Cargando OPL")
        df_opl = data_opl( pd.read_excel( Ruta_opl, sheet_name="Combinado" ))
        log_step( f"OPL cargado. Registros: {len(df_opl):,}")

        # ==================================================
        log_step("Cargando MasterSkill")
        df_master = limpiar_masterskill( pd.read_excel( Ruta_masterskill, sheet_name="TB" ))
        log_step( f"MasterSkill cargado. Registros: {len(df_master):,}")

        # ==================================================
        log_step("Cargando festivos")
        df_festivos = ( pd.to_datetime( pd.read_csv(Ruta_festivos)["Fecha"], format="%d/%m/%Y")
            .drop_duplicates()
            .values.astype("datetime64[D]")
        )
        log_step( f"Festivos cargados. Total: {len(df_festivos):,}")

        # ==================================================

        log_step("Cargando contactos")
        require_columns = {
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

        delete_dup_columns = ["id de contacto"]

        df_contactos = load_files_from_folder(
            Ruta_busquedad_contacto,
            require_columns,
            delete_dup_columns
        )
        df_contactos = df_contactos[~df_contactos["cola"].isna()]
        
        log_step(f"Contactos cargados. Registros: {len(df_contactos):,}")

        # ==================================================
        log_step("Cargando comentarios")
        df_comentarios = _transformacion_comentarios( Ruta_Comentarios)
        log_step( f"Comentarios cargados. Registros: {len(df_comentarios):,}")

        # ==================================================
        log_step("Cargando CRM")
        df_crm_base = load_files( Ruta_crm )
        log_step( f"CRM cargado. Registros: {len(df_crm_base):,}")

# TRANSFORMACIONES
        log_step("Transformando CRM")
        df_crm = transform_crm(
            df_crm_base,
            df_arbol,
            df_festivos,
            df_contactos,
            df_opl,
            df_master,
            df_comentarios
        )
        log_step( f"CRM transformado. Registros: {len(df_crm):,}")

        # ==================================================
        log_step("Transformando contactos")
        df_contactos = transformation_contact(
            df_contactos,
            df_crm,
            df_master,
            df_opl
        )
        log_step(f"Contactos transformados. Registros: {len(df_contactos):,}")

         # =================================================
        log_step("Transformando y cargando auxiliares")
        df_aux = ejecutar_auxiliares()

        log_step(f"Auxiliares procesados. Registros: {len(df_aux):,}")

         # ================================================= 
        log_step("Transformando y cargando KpiOverAll")
        df_kpi = ejecutar_kpioverall()

        log_step(f"Data KpiOverAll procesada. Registros: {len(df_kpi):,}")
        
        # ================================================= 
        log_step("Transformando y cargando CSAT")
        df_csat = ejecutar_csat()

        log_step(f"Data Csat procesada. Registros: {len(df_csat):,}")

# GUARDADO DE ARCHIVOS
        
        log_step("Guardando Contactos")
        save_contacts(
            df_contactos,
            Ruta_global,
            Ruta_local
        )
        log_step("Contactos guardados")

        # ==================================================
        log_step("Guardando CRM")
        guardar_crm(
            df_crm,
            Ruta_global,
            Ruta_local
        )
        log_step("CRM guardado")

        # ==================================================
        log_step("Guardando OPL")
        guardar_opl(
            df_opl,
            Ruta_global,
            Ruta_local
        )
        log_step("OPL guardado")

        # ==================================================
        log_step("Guardando MasterSkill")
        guardar_masterskill(
            df_master,
            Ruta_global,
            Ruta_local
        )
        log_step("MasterSkill guardado")

        # ==================================================
        log_step("Guardando Árbol")

        guardar_arbol(
            df_arbol,
            Ruta_global,
            Ruta_local
        )
        log_step("Árbol guardado")

        # ==================================================
        log_step("Guardado OPL_HISTORICO")
        df_opl = procesar_opl(save_file=True)
        log_step(f"Data OPL Historico. Registros: {len(df_opl):,}")

        # ==================================================

        """Data Ventas"""
        df_arbol_hist = guardar_arbol_historico(_load_arbol_historico(Ruta_historico_arbol))
        log_step(f"Guardado Arbol Tipificaciones Historico. Tot_Reg: {len(df_arbol_hist)}, Max_Reg: {df_arbol_hist["source_file"].max()}")

        df_crm_ventas = process_crm_ventas(save_file=True)
        log_step(f"Guardado Data CRM Ventas. Tot_Reg: {len(df_crm_ventas)}, Max_Reg: {df_crm_ventas["FECHA_DE_INICIO"].max()}")

        df_bonos = process_bonos_ventas(df_crm=df_crm_ventas, save_file=True)
        log_step(f"Guardado Data Bonos Ventas. Tot_Reg: {len(df_bonos)}, Max_Reg: {df_bonos["order_date"].max()}")

        df_soat = process_soat_ventas(df_crm=df_crm_ventas,save_file=True)
        log_step(f"Guardado Data Soat Ventas. Tot_Reg: {len(df_soat)}, Max_Reg: {df_soat["fecha_homologada"].max()}")

        df_vtex = process_vtex_ventas(df_crm=df_crm_ventas,save_file=True)
        log_step(f"Guardado Data Vtex Ventas. Tot_Reg: {len(df_vtex)}, Max_Reg: {df_vtex["creation date"].max()}")

        df_viajes = process_viajes_ventas(df_crm=df_crm_ventas,save_file=True)
        log_step(f"Guardado Data Vaijes Ventas. Tot_Reg: {len(df_viajes)}, Max_Reg: {df_viajes["fecha_transaccion"].max()}")
        
        # ==================================================
        fin = datetime.now()
        log_step(
            f"Proceso finalizado correctamente. "
            f"Duración total: {fin - inicio}"
        )

    except Exception as e:

        log_step(
            f"ERROR EN EL PROCESO: {e}"
        )
        raise

if __name__ == "__main__":
    main()