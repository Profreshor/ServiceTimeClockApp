# utils/db_utils.py
import pandas as pd
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def get_engine():
    """
    Builds a SQLAlchemy engine using settings from config.json.
    Supports SQL Authentication with username/password.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path) as f:
        config = json.load(f)
    
    server = config["sql_server"]
    database = config["database"]
    username = config["username"]
    password = config["password"]

    # Encode special characters in password if needed
    from urllib.parse import quote_plus
    password_encoded = quote_plus(password)

    # --- SQLAlchemy connection string (SQL Auth) ---
    connection_str = (
        f"mssql+pyodbc://{username}:{password_encoded}@{server}/{database}"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    )

    engine = create_engine(connection_str, fast_executemany=True)
    return engine, config["view_name"]

def fetch_punches_today():
    """
    Extracts all records from CK_ServicePunches_today (or configured view).
    Returns a pandas DataFrame.
    """
    engine, view_name = get_engine()
    query = text(f"SELECT * FROM {view_name};")

    try:
        print(f"Querying SQL view: {view_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        print(f"Rows fetched: {len(df)}")
        return df

    except SQLAlchemyError as e:
        print(f"❌ SQL Error: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame for safety


# --- Local test block ---
if __name__ == "__main__":
    df = fetch_punches_today()
    print(df.head())
