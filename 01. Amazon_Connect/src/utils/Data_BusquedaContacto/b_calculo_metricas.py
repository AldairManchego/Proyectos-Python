import os, sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from unidecode import unidecode

def _calculate_contact_metrics(
    df_contactos: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula:

    - Rellamadas
    - Recontactos
    - Voz -> Chat
    - Chat -> Voz
    """

    tipificaciones_excluir = {
        "Llamada de Prueba",
        "Interaccion de Prueba",
        "Interacción de Prueba",
        "Chat de Prueba",
        "Pruebas PCO",
        "Devolución llamada EFECTIVA",
        "Devolución llamada NO EFECTIVA"
    }

    documentos_excluir = {
        "2222222956",
        "2222222005"
    }

    df_valido = df_contactos[
        ~df_contactos["metodo de iniciacion"].isin(
            ["Transferir", "Saliente"]
        )
        &
        (
            ~df_contactos["NIVEL_3"].isin(
                tipificaciones_excluir
            )
            |
            ~df_contactos[
                "NÚMERO_DOCUMENTO_DEL_CLIENTE"
            ].astype(str).isin(
                documentos_excluir
            )
        )
    ].copy()

    df_valido = df_valido.sort_values(["llave_documento_fecha","marca de tiempo de inicio"])

    # ==========================
    # RELLAMADAS
    # ==========================

    df_valido["orden_interaccion"] = (
        df_valido
        .groupby("llave_documento_fecha")
        .cumcount()
        + 1
    )

    df_valido["conteo_rellamda"] = (
        df_valido
        .groupby("llave_documento_fecha")
        ["id de contacto"]
        .transform("count")
    )

    df_valido["es_rellamada"] = (df_valido["orden_interaccion"] > 1).astype(int)

    # ==========================
    # RECONTACTOS
    # ==========================

    df_valido["conteo_recontacto"] = (
        df_valido
        .groupby("llave_recontacto")
        ["id de contacto"]
        .transform("count")
    )

    df_valido["orden_recontacto"] = (
        df_valido
        .sort_values("marca de tiempo de inicio")
        .groupby("llave_recontacto")
        .cumcount()
        + 1
    )

    df_valido["es_recontacto"] = (df_valido["orden_recontacto"] > 1).astype(int)

    # ==========================
    # VOZ -> CHAT
    # CHAT -> VOZ
    # ==========================

    df_resumen = (df_valido.sort_values(["llave_documento_fecha","orden_interaccion"]).copy())

    df_resumen["es_chat"] = (df_resumen["canal"] == "Chat")
    df_resumen["es_voz"] = (df_resumen["canal"] == "Voz")

    df_resumen = ( df_resumen.groupby("llave_documento_fecha", sort=False)
        .agg(
            primer_contacto=("canal", "first"),
            tiene_chat=("es_chat", "any"),
            tiene_voz=("es_voz", "any")
        ).reset_index())

    df_resumen["voz_a_chat"] = ((df_resumen["primer_contacto"] == "Voz") & (df_resumen["tiene_chat"])).astype(int)
    df_resumen["chat_a_voz"] = ((df_resumen["primer_contacto"] == "Chat" ) & (df_resumen["tiene_voz"])).astype(int)

    df_valido = df_valido.merge(
        df_resumen[
            [
                "llave_documento_fecha",
                "voz_a_chat",
                "chat_a_voz"
            ]
        ],
        on="llave_documento_fecha",
        how="left"
    )

    df_contactos = df_contactos.merge(
        df_valido[
            [
                "id de contacto",
                "orden_interaccion",
                "conteo_rellamda",
                "es_rellamada",
                "conteo_recontacto",
                "orden_recontacto",
                "es_recontacto",
                "voz_a_chat",
                "chat_a_voz"
            ]
        ],
        on="id de contacto",
        how="left"
    )
    return df_contactos