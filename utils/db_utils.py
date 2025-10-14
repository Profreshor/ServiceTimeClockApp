# utils/db_utils.py
"""
Database utility module for the Warner Service Time Clock app.
Handles SQL Server connections and extracts raw punch data from the configured view.
"""

import os
import json
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from utils.log_utils import setup_logger


# -------------------------------------------------------------------
# Initialize logger once for the module
# -------------------------------------------------------------------
logger = setup_logger()


# -------------------------------------------------------------------
# Connection + configuration helpers
# -------------------------------------------------------------------
def get_engine():
    """
    Reads SQL connection settings from config.json and returns
    a SQLAlchemy engine + the view name.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    # Defensive load (in case pathing changes when deployed)
    with open(os.path.abspath(config_path)) as f:
        config = json.load(f)

    server = config["sql_server"]
    database = config["database"]
    username = config["username"]
    password = config["password"]
    view_name = config["view_name"]

    # Encode any special characters in the password
    password_encoded = quote_plus(password)

    connection_str = (
        f"mssql+pyodbc://{username}:{password_encoded}@{server}/{database}"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    )

    logger.info(f"Connecting to SQL Server: {server} / {database}")
    engine = create_engine(connection_str, fast_executemany=True)
    return engine, view_name


# -------------------------------------------------------------------
# Extraction logic
# -------------------------------------------------------------------
def fetch_punches_today():
    """
    Extracts all records from the configured SQL view (e.g., dbo.CK_ShopTimePunches_today).
    Returns a pandas DataFrame.
    """
    engine, view_name = get_engine()
    query = text(f"SELECT * FROM {view_name};")

    try:
        logger.info(f"Querying SQL view: {view_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Rows fetched: {len(df)}")
        return df

    except SQLAlchemyError as e:
        logger.error(f"SQL Error while querying {view_name}: {str(e)}")
        return pd.DataFrame()


# -------------------------------------------------------------------
# Local test (stand-alone execution)
# -------------------------------------------------------------------
if __name__ == "__main__":
    df = fetch_punches_today()
    if not df.empty:
        logger.info(f"Sample data preview:\n{df.head()}")
    else:
        logger.warning("No data returned from SQL view.")
