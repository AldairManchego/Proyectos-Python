import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from unidecode import unidecode

def save_contacts(
    df: pd.DataFrame,
    ruta_global: str,
    ruta_local: str,
    filename: str = "05.Data_Contactos.csv"
) -> None:
    """
    Guarda contactos procesados.
    """

    df.to_csv(
        os.path.join(ruta_global, filename),
        index=False,
        encoding="utf-8"
    )

    df.to_csv(
        os.path.join(ruta_local, filename),
        index=False,
        encoding="utf-8"
    )