from fastapi import APIRouter, UploadFile, File
from fastapi.encoders import jsonable_encoder
import pandas as pd
import numpy as np
#from requests import session
import logging
from app.session.manager import create_session, get_session
from app.services.excel_loader import load_excel_to_db
from app.services.schema_infer import infer_schema_db, infer_schema_usable as infer_schema
from app.session.manager import store_metadata

router = APIRouter()
logger = logging.getLogger(__name__)

def read_excel_with_dynamic_header(file):
    # Load raw data without header
    raw = pd.read_excel(file, header=None)

    # Find the row with the maximum number of non-null values
    header_row = raw.notna().sum(axis=1).idxmax()

    # Re-read with that row as header
    df = pd.read_excel(file, header=header_row)

    return df


@router.post("/upload")
def upload(file: UploadFile = File(...)):
    session_id = create_session()
    session = get_session(session_id)
    conn = session["conn"]
    # logger.info(f"DuckDB table columns: {list(schema_db.keys())}")

    file.file.seek(0)
    df = pd.read_csv(file.file) if file.filename.endswith(".csv") else read_excel_with_dynamic_header(file.file)
    
    # 🔴 IMPORTANT: sanitize DataFrame for JSON
    df = df.replace({np.nan: None})

    # Optional but recommended: drop auto index columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    schema = infer_schema(df)
    # logger.info(f"Pandas DataFrame columns: {list(df.columns)}")
    preview = df.head(3).to_dict(orient="records")

    table = load_excel_to_db(df, conn)
    schema_db = infer_schema_db(conn, table)
    
    store_metadata(session_id, table, schema_db, schema, df=df)

    return {
        "sessionId": session_id,
        "table": table,
        "columns": list(df.columns),
        "rowCount": len(df),
        "preview": preview,
        "schema": schema
    }
