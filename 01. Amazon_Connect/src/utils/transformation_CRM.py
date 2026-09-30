"""
Transformación del CRM.

Este módulo expone funciones puras (load_files, transform_crm) que puedes
importar desde otro script o notebook para obtener el DataFrame final en
memoria, sin necesidad de leer/escribir nada en disco:

    from transformation_CRM import load_files, transform_crm

    df_crm_raw = load_files(Ruta_crm)
    df_crm = transform_crm(
        df_crm_raw,
        df_arbol=df_arbol,
        df_festivos=df_festivos,
        df_contactos=df_contactos,
        df_opl=df_opl,
        df_master=df_master,
    )

El bloque `if __name__ == "__main__":` al final solo se ejecuta cuando
corres este archivo directamente (`python transformation_CRM.py`). Ahí es
donde se leen las rutas reales (Excel/CSV) y se guarda el CSV final en
Ruta_global y Ruta_local, igual que en el patrón:

    df_opl = data_opl(pd.read_excel(Ruta_opl, sheet_name="Combinado"))
    guardar_opl(df_opl, Ruta_global, Ruta_local)
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from unidecode import unidecode


REQUIRE_COLUMNS = {
    "RADICADO",
    "PRODUCTO",
    "TIPO",
    "SUBTIPO",
    "ID_LLAMADA_DE_CONTACTO",
    "SE_RESOLVIÓ_EL_CONTACTO",
    "MOTIVO_NO_FCR",
    "NOMBRE_ALIADO",
    "FECHA_DE_INICIO",
    "FECHA_FIN",
}

COLUMNAS_CRM = [
    "RADICADO",
    "ESTADO",
    "TIPO_PRI",
    "PRODUCTO",
    "TIPO",
    "SUBTIPO",
    "NÚMERO_CUENTA",
    "TIPO_DE_LLAMADA",
    "ES_CLIENTE_APP",
    "NÚMERO_DOCUMENTO_DEL_CLIENTE",
    "NOMBRE_CLIENTE",
    "NOMBRE_ALIADO",
    "SOLUCIÓN",
    "NOMBRE_DE_AGENTE_ASIGNADO_AL_CASO",
    "FECHA_DE_INICIO",
    "EN_DIAS",
    "SLA_DIAS",
    "FECHA_FIN",
    "VALOR_PUNTOS",
    "VALOR_DINERO",
    "MONTO_MÍNIMO",
    "CANAL_DE_ATENCIÓN",
    "ESTADO_GESTIÓN",
    "NÚMERO_PEDIDO",
    "NOMBRE_ASESOR",
    "DEVOLUCIÓN",
    "SE_RESOLVIÓ_EL_CONTACTO",
    "MOTIVO_NO_FCR",
    "CONTACTO_DE_CLIENTE",
    "ID_LLAMADA_DE_CONTACTO",
    "OFRECIMIENTO_EFECTIVO",
    "SKILL",
    "PROMESA_DE_VENTA",
    "MOTIVO_NO_ACEPTACIÓN",
    "FECHA_ÚLTIMO_CAMBIO",
    "MÉTODO_DE_APROBACIÓN_DE_VALIDACIÓN",
    "CÓDIGO_DE_VALIDACIÓN",
    "FILE_NAME",
    "CREATION_FILE_DATE",
]

COLUMNAS_FECHA = [
    "FECHA_DE_INICIO",
    "FECHA_FIN",
    "FECHA_ÚLTIMO_CAMBIO",
    "CREATION_FILE_DATE",
]

COLUMNAS_NUMERO = [
    "EN_DIAS",
    "SLA_DIAS",
    "VALOR_PUNTOS",
    "VALOR_DINERO",
]

EXCLUIR_REGISTROS = ["CHAT DE PRUEBA", "LLAMADA DE PRUEBA", "PRUEBAS PCO"]

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


def detect_delimiter(file_path: Path, file_size: int = 4092) -> str:
    """
    Detecta automáticamente el delimitador del CSV.
    """

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:

        sample = f.read(file_size)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            return dialect.delimiter

        except csv.Error:
            return ";" if sample.count(";") > sample.count(",") else ","


def load_files(folder_path: str | Path) -> pd.DataFrame:
    """
    Lee todos los CSV válidos del CRM en una carpeta
    y devuelve un único DataFrame consolidado.
    """

    folder_path = Path(folder_path)

    dfs = []

    for file in folder_path.iterdir():

        if not file.is_file():
            continue

        if file.suffix.lower() != ".csv":
            continue

        try:
            delimiter = detect_delimiter(file)
            df = pd.read_csv(file, delimiter=delimiter)

            columns_validation = REQUIRE_COLUMNS - set(df.columns)

            if columns_validation:
                print(
                    f"Archivo {file} omitido."
                    f"Ausencia de las siguientes columnas {columns_validation}."
                )
                continue

            df["FILE_NAME"] = file.name
            df["CREATION_FILE_DATE"] = datetime.fromtimestamp(file.stat().st_atime)
            dfs.append(df)

        except Exception as e:
            print(f"el archivo {file.name} no pudo ser proceado por el error: {e}.")

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True).drop_duplicates()


def _limpiar_columnas_crm(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Filtra pruebas, selecciona columnas, normaliza texto y renombra niveles."""

    df_crm = df_crm[~df_crm["SUBTIPO"].isin(EXCLUIR_REGISTROS)]
    df_crm = df_crm[COLUMNAS_CRM]

    for col in COLUMNAS_CRM:
        df_crm[col] = (
            df_crm[col]
            .astype("string")
            .str.strip()
            .map(lambda x: unidecode(x) if pd.notna(x) else x)
            .str.title()
        )

    df_crm = df_crm.rename(
        columns={
            "PRODUCTO": "NIVEL_1",
            "TIPO": "NIVEL_2",
            "SUBTIPO": "NIVEL_3",
        }
    )

    return df_crm


def _clasificar_canal(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Agrupa CANAL_DE_ATENCIÓN en Chat / Voz / Correo / Otros."""

    condiciones_canal = [
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Whatsapp", "Chat", "Pagina Web"]),
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Telefonico"]),
        df_crm["CANAL_DE_ATENCIÓN"].isin(["Correo Electronico"]),
    ]
    resultado_canal = ["Chat", "Voz", "Correo"]

    df_crm["CANAL_DE_ATENCIÓN"] = np.select(
        condiciones_canal, resultado_canal, default="Otros"
    )

    return df_crm


def _normalizar_fechas_numeros(df_crm: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas de fecha y de número a sus tipos correctos."""

    for col in COLUMNAS_FECHA:
        df_crm[col] = pd.to_datetime(
            df_crm[col], utc=True, errors="coerce"
        ).dt.tz_localize(None)

    for col in COLUMNAS_NUMERO:
        df_crm[col] = pd.to_numeric(df_crm[col], errors="coerce").fillna(0).astype("int")

    df_crm["START_DATE"] = df_crm["FECHA_DE_INICIO"].dt.date
    df_crm["END_DATE"] = df_crm["FECHA_FIN"].dt.date

    return df_crm


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


def _calcular_dias_cierre(
    df_crm: pd.DataFrame, df_festivos: np.ndarray, today: pd.Timestamp
) -> pd.DataFrame:
    """Calcula DIAS_CIERRE (hábiles u corridos, según Tipo_Dia) y CUMPLIMIENTO_ANS."""

    validacion_habiles = df_crm["Tipo_Dia"].eq("Habiles")

    start = (
        df_crm.loc[validacion_habiles, "FECHA_DE_INICIO"]
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    end = (
        df_crm.loc[validacion_habiles, "FECHA_FIN"]
        .fillna(today)
        .dt.normalize()
        .values.astype("datetime64[D]")
    )

    dias_habiles = np.busday_count(
        start + np.timedelta64(1, "D"),
        end + np.timedelta64(1, "D"),
        holidays=df_festivos,
    )

    df_crm["DIAS_CIERRE"] = df_crm["EN_DIAS"]
    df_crm.loc[validacion_habiles, "DIAS_CIERRE"] = dias_habiles
    df_crm["DIAS_CIERRE"] = (
        pd.to_numeric(df_crm["DIAS_CIERRE"], errors="coerce").fillna(0).clip(lower=0)
    )

    condicion = df_crm["DIAS_CIERRE"].le(df_crm["ANS_Dias"]).fillna(False)

    df_crm["CUMPLIMIENTO_ANS"] = np.where(
        df_crm["FECHA_FIN"].notna(),
        np.where(condicion, "Cumple", "No Cumple"),
        pd.NA,
    )

    return df_crm


def _calcular_estado_gestion_abiertos(
    df_crm: pd.DataFrame, df_festivos: np.ndarray, today: pd.Timestamp
) -> pd.DataFrame:
    """Calcula ESTADO_GESTION (Verde/Amarillo/Rojo/Negro) para casos sin FECHA_FIN."""

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    inicio_abiertos = (
        df_crm.loc[mask_sin_fin, "FECHA_DE_INICIO"]
        .dt.normalize()
        .to_numpy()
        .astype("datetime64[D]")
    )

    fin_today = np.datetime64(pd.Timestamp(today).normalize(), "D")

    dias_habiles_gestion = np.busday_count(
        inicio_abiertos + np.timedelta64(1, "D"),
        fin_today + np.timedelta64(1, "D"),
        holidays=df_festivos,
    )

    dias_corridos_gestion = (fin_today - inicio_abiertos).astype(int)

    mask_habiles_abiertos = (
        df_crm.loc[mask_sin_fin, "Tipo_Dia"].eq("Habiles").to_numpy()
    )

    resultado_final = np.where(
        mask_habiles_abiertos, dias_habiles_gestion, dias_corridos_gestion
    )
    resultado_final = np.nan_to_num(resultado_final, nan=0)

    dias_ns = (
        pd.to_numeric(df_crm.loc[mask_sin_fin, "ANS_Dias"], errors="coerce")
        .fillna(0)
        .to_numpy()
    )

    porc_gestion = np.divide(
        resultado_final,
        dias_ns,
        out=np.full(resultado_final.shape, np.nan, dtype=float),
        where=dias_ns != 0,
    )

    condiciones_estado = [
        (porc_gestion > 0) & (porc_gestion <= 0.5),
        (porc_gestion > 0.5) & (porc_gestion <= 0.75),
        (porc_gestion > 0.75) & (porc_gestion <= 1),
        (porc_gestion > 1),
    ]
    resultados_estado = ["Verde", "Amarillo", "Rojo", "Negro"]

    estado_abiertos = np.select(condiciones_estado, resultados_estado, default=pd.NA)

    df_crm["ESTADO_GESTION"] = pd.NA
    df_crm.loc[mask_sin_fin, "ESTADO_GESTION"] = estado_abiertos

    return df_crm


def _calcular_grupo_dias_cierre(
    df_crm: pd.DataFrame, today: pd.Timestamp
) -> pd.DataFrame:
    """Calcula GRUPO_DIAS_CIERRE para los casos sin FECHA_FIN."""

    mask_sin_fin = df_crm["FECHA_FIN"].isna()

    inicio_all = df_crm["FECHA_DE_INICIO"].dt.normalize().values.astype("datetime64[D]")
    fin_today = np.datetime64(pd.Timestamp(today).normalize(), "D")
    dias_transcurridos = (fin_today - inicio_all).astype(int)

    meta = pd.to_numeric(df_crm["ANS_Dias"], errors="coerce")

    dias_restantes = (meta - dias_transcurridos).astype("float64")

    condiciones_grupo = [
        dias_restantes < 0,
        dias_restantes <= 1,
        dias_restantes <= 3,
        dias_restantes <= 5,
        dias_restantes <= 7,
        dias_restantes <= 9,
    ]
    resultados_grupo = [
        "Vencido",
        "0 - 1 Día",
        "2 - 3 Días",
        "4 - 5 Días",
        "6 - 7 Días",
        "8 - 9 Días",
    ]

    grupo_dias = np.select(condiciones_grupo, resultados_grupo, default=">=10 Días")

    df_crm["GRUPO_DIAS_CIERRE"] = np.where(mask_sin_fin, grupo_dias, pd.NA)

    return df_crm


def _enriquecer_con_fuentes(
    df_crm: pd.DataFrame,
    df_contactos: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_master: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza el CRM con contact search, OPL y master skill."""

    df_crm["ID_LLAMADA_DE_CONTACTO"] = df_crm["ID_LLAMADA_DE_CONTACTO"].str.lower()

    df_crm = df_crm.merge(
        df_contactos[["id de contacto", "agente", "duración del contacto"]],
        how="left",
        left_on="ID_LLAMADA_DE_CONTACTO",
        right_on="id de contacto",
    ).drop(columns=["id de contacto"])

    df_crm = df_crm.merge(
        df_opl[["Nombre_Agente", "Correo_contratista"]],
        how="left",
        left_on="NOMBRE_ASESOR",
        right_on="Nombre_Agente",
    ).drop(columns=["Nombre_Agente"])

    df_crm["agente"] = df_crm["agente"].combine_first(df_crm["Correo_contratista"])
    df_crm = df_crm.drop(columns=["Correo_contratista"])

    df_crm = df_crm.merge(
        df_opl[["Id_opl", "Correo_contratista"]],
        how="left",
        left_on="agente",
        right_on="Correo_contratista",
    ).drop(columns=["Correo_contratista"])

    df_master = df_master.copy()
    df_master["Colas"] = df_master["Colas"].str.title()

    df_crm = df_crm.merge(
        df_master[["IdMasterSkill", "Canal", "Colas"]],
        how="left",
        left_on=["CANAL_DE_ATENCIÓN", "SKILL"],
        right_on=["Canal", "Colas"],
    ).drop(columns=["Canal", "Colas"])

    return df_crm


def transform_crm(
    df_crm: pd.DataFrame,
    df_arbol: pd.DataFrame,
    df_festivos: np.ndarray,
    df_contactos: pd.DataFrame,
    df_opl: pd.DataFrame,
    df_master: pd.DataFrame,
    today: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Ejecuta el pipeline completo de transformación del CRM y devuelve
    el DataFrame final en memoria (no guarda nada en disco).
    """

    if today is None:
        today = pd.Timestamp.today().normalize()

    df_crm = _limpiar_columnas_crm(df_crm)
    df_crm = _clasificar_canal(df_crm)
    df_crm = _normalizar_fechas_numeros(df_crm)
    df_crm = _cruzar_arbol_tipificacion(df_crm, df_arbol)
    df_crm = _calcular_fcr(df_crm)
    df_crm = _calcular_dias_cierre(df_crm, df_festivos, today)
    df_crm = _calcular_estado_gestion_abiertos(df_crm, df_festivos, today)
    df_crm = _calcular_grupo_dias_cierre(df_crm, today)
    df_crm = _enriquecer_con_fuentes(df_crm, df_contactos, df_opl, df_master)

    df_crm = df_crm.rename(
        columns={
            "ANS_Dias": "ANS_DIAS",
            "Tipo_Dia": "TIPO_DIA",
            "agente": "CORREO_AGENTE",
            "duración del contacto": "DURACION_CONTACTO",
        }
    )
    df_crm["HORA_INICIO"] = df_crm["FECHA_DE_INICIO"].dt.time

    return df_crm


def guardar_crm(
    df_crm: pd.DataFrame,
    ruta_global: str | Path,
    ruta_local: str | Path,
    nombre_archivo: str = "04.Data_CRM.csv",
) -> None:
    """Guarda el CRM final como CSV en ambas rutas (global y local)."""

    df_crm.to_csv(os.path.join(ruta_global, nombre_archivo), index=False, encoding="utf-8")
    df_crm.to_csv(os.path.join(ruta_local, nombre_archivo), index=False, encoding="utf-8")


def main(guardar: bool = True) -> pd.DataFrame:
    """
    Ejecuta el pipeline real completo: lee las rutas configuradas en
    routes.Paths, arma df_contactos/df_opl/df_master/df_festivos/df_arbol,
    corre transform_crm y devuelve df_crm en memoria.

    guardar=True (default): además guarda todos los CSV/Excel intermedios
        y el CRM final en Ruta_global y Ruta_local, igual que el notebook
        original.
    guardar=False: no escribe nada en disco, solo devuelve df_crm. Útil
        cuando otro script (por ejemplo main.py) va a seguir trabajando
        con el DataFrame en memoria y no necesita el CSV.

    Se puede importar y llamar desde cualquier otro archivo:

        from transformation_CRM import main as build_crm

        df_crm = build_crm(guardar=False)
    """

    # Imports locales: solo se necesitan para correr el pipeline real
    # (lectura de rutas y, opcionalmente, guardado en disco). Si desde
    # otro archivo solo importas load_files/transform_crm, no se ejecutan.
    from routes.Paths import (
        Ruta_arbol_tipificacion,
        Ruta_global,
        Ruta_local,
        Ruta_masterskill,
        Ruta_opl,
        Ruta_busquedad_contacto,
        Ruta_crm,
        Ruta_festivos,
    )
    from utils.functions import (
        limpiar_df_arbol,
        guardar_arbol,
        limpiar_masterskill,
        guardar_masterskill,
        data_opl,
        guardar_opl,
    )
    from utils.transformation_contact_search import load_contacts

    df_contactos = load_contacts(Ruta_busquedad_contacto)
    df_contactos = df_contactos[df_contactos["id de contacto"].notna()]

    df_opl = data_opl(pd.read_excel(Ruta_opl, sheet_name="Combinado"))
    df_master = limpiar_masterskill(pd.read_excel(Ruta_masterskill, sheet_name="TB"))

    df_festivos = (
        pd.to_datetime(pd.read_csv(Ruta_festivos)["Fecha"], format="%d/%m/%Y")
        .drop_duplicates()
        .values.astype("datetime64[D]")
    )

    df_arbol = limpiar_df_arbol(
        pd.read_excel(Ruta_arbol_tipificacion, sheet_name="Tipificación Vista360")
    )

    df_crm_raw = load_files(Ruta_crm)

    df_crm = transform_crm(
        df_crm_raw,
        df_arbol=df_arbol,
        df_festivos=df_festivos,
        df_contactos=df_contactos,
        df_opl=df_opl,
        df_master=df_master,
    )

    if guardar:
        guardar_arbol(df_arbol, Ruta_global, Ruta_local)
        guardar_masterskill(df_master, Ruta_global, Ruta_local)
        guardar_opl(df_opl, Ruta_global, Ruta_local)
        guardar_crm(df_crm, Ruta_global, Ruta_local)

    return df_crm


if __name__ == "__main__":
    main()