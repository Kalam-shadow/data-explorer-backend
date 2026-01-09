from fastapi import APIRouter, UploadFile, File
import pandas as pd
#from requests import session
#import logging
from app.session.manager import create_session, get_session
from app.services.excel_loader import load_excel_to_db
from app.services.schema_infer import infer_schema
from app.session.manager import store_metadata

router = APIRouter()
#logger = logging.getLogger(__name__)

@router.post("/upload")
def upload(file: UploadFile = File(...)):
    session_id = create_session()
    session = get_session(session_id)
    conn = session["conn"]

    table = load_excel_to_db(file, conn)
    schema = infer_schema(conn, table)

    #logger.info(f"DuckDB table columns: {list(schema.keys())}")

    file.file.seek(0)
    df = pd.read_csv(file.file) if file.filename.endswith(".csv") else pd.read_excel(file.file)
    
    #logger.info(f"Pandas DataFrame columns: {list(df.columns)}")
    preview = df.head(3).to_dict(orient="records")

    store_metadata(session_id, table, schema, df=df)

    return {
        "sessionId": session_id,
        "table": table,
        "columns": list(df.columns),
        "rowCount": len(df),
        "preview": preview,
        "schema": schema
    }
