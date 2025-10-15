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

logger = setup_logger()

# -------------------------------------------------------------------
# Connection + configuration helpers
# -------------------------------------------------------------------
def get_engine():
    """
    Reads SQL connection settings from config.json and returns
    a SQLAlchemy engine + the view name.
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
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

    # Only log the connection target once at startup, not on every query
    logger.debug(f"DB Engine created for {server}/{database}")
    engine = create_engine(connection_str, fast_executemany=True)
    return engine, view_name


# -------------------------------------------------------------------
# Extraction logic
# -------------------------------------------------------------------
def fetch_punches_today():
    """
    Extracts all records from the configured SQL view.
    Returns a pandas DataFrame or empty DataFrame on error.
    """
    engine, view_name = get_engine()
    query = text(f"SELECT * FROM {view_name};")

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"SQL view '{view_name}' returned {len(df)} rows.")
        return df

    except SQLAlchemyError as e:
        logger.error(f"SQL error querying {view_name}: {e}")
        return pd.DataFrame()


# -------------------------------------------------------------------
# Technician roster
# -------------------------------------------------------------------
def fetch_dim_techs():
    """
    Fetches all active technicians from COEMP to build the roster,
    including those without any punches today.
    """
    engine, _ = get_engine()
    query = text("""
        SELECT EmpId, Name AS EmpName, BrnId
        FROM dbo.COEMP WITH (NOLOCK)
        WHERE Title = 'TECHNICIAN'
          AND ISNULL(Inactive, 0) = 0
          AND TRY_CAST(EmpId AS INT) < 1000
    """)

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Technician roster loaded — {len(df)} techs.")
        return df

    except SQLAlchemyError as e:
        logger.error(f"SQL error fetching technician roster: {e}")
        return pd.DataFrame()
