from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
import logging
import pandas as pd
import re
from app.utils.file_utils import save_upload_tempfile, cleanup_tempfile
from app.services.excel_parser import parse_excel
from app.session.manager import create_session, get_session, store_metadata
from app.services.excel_loader import load_excel_to_db
from app.services.schema_infer import infer_schema_db, infer_schema_usable as infer_schema
from app.models.schemas import APIResponse, UploadResponse, ParsedDataResponse, FileMeta
from app.utils.logging_config import configure_logging

configure_logging()
router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=APIResponse)
async def upload(file: UploadFile = File(...)):
    # Stream upload to temp file (limits size) and parse
    tmp = None
    try:
        tmp = save_upload_tempfile(file)
        path = tmp["path"]

        # Parse and normalize the excel into a clean DataFrame
        df, meta = parse_excel(path)

        # quick row preview (sanitize NaN -> None for JSON and trim strings)
        raw_preview = df.head(10).to_dict(orient="records")
        preview = []
        for row in raw_preview:
            sanitized = {}
            for k, v in row.items():
                if pd.isna(v):
                    sanitized[k] = None
                elif isinstance(v, str):
                    sanitized[k] = v.strip()
                else:
                    sanitized[k] = v
            preview.append(sanitized)

        # Basic validation: infer schema and check for missing required columns
        inferred = infer_schema(df)
        validation_errors = []
        missing_required = meta.get("missing_required", [])
        if missing_required:
            validation_errors.append({"type": "missing_columns", "columns": missing_required})

        # Optional: store into in-memory DB for later queries
        session_id = create_session()
        session = get_session(session_id)
        conn = session["conn"]
        table = load_excel_to_db(df, conn)
        schema_db = infer_schema_db(conn, table)
        schema = infer_schema(df)

        store_metadata(session_id, table, schema_db, schema, df=df)

        # Build a flat backend response to match frontend expectations
        backend_resp = {
            "sessionId": session_id,
            "table": table,
            "columns": meta.get("columns", []),
            "rowCount": meta.get("row_count", 0),
            "preview": preview,
            "validationErrors": validation_errors,
            "file": {
                "filename": tmp.get("filename"),
                "content_type": tmp.get("content_type"),
                "size": tmp.get("size"),
            },
        }

        return JSONResponse(status_code=200, content=backend_resp)

    except Exception as exc:
        logger.exception("Upload error")
        return JSONResponse(status_code=400, content=APIResponse(success=False, message=str(exc), data=None, errors=[str(exc)]).dict())
    finally:
        if tmp:
            cleanup_tempfile(tmp.get("path"))
