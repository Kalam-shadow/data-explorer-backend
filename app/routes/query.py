from datetime import datetime, timezone
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.session.manager import get_session
from app.services.ai_client import generate_sql
from app.services.sql_executor import execute_sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("query")

router = APIRouter()

class QueryRequest(BaseModel):
    session_id: str
    question: str


@router.post("/query")
def query(request: QueryRequest):
    # 1. Validate session
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = session.get("conn")
    table = session.get("table")
    schema_db = session.get("schema_db")
    schema = session.get("schema")

    if not conn or not table or not schema:
        raise HTTPException(status_code=400, detail="Session missing metadata")

    # 2. Load prompt template
    with open("app/prompts/nl_to_sql.txt", "r", encoding="utf-8") as f:
        template = f.read()

    # 3. Quote column names safely for DuckDB
    quoted_columns = "\n".join(
        [f'"{col}"' if " " in col else col for col in schema.keys()]
    )

    prompt = (
        template.format(
            table=table,
            columns=quoted_columns,
            schema_db=schema_db,
            schema=schema
        )
        + f"\nQuestion: {request.question}"
    )

    # 4. Generate SQL using LLM
    sql = generate_sql(prompt)

    if not sql or not sql.strip().lower().startswith("select"):
        raise HTTPException(
            status_code=400,
            detail="Generated SQL is invalid or not a SELECT query"
        )

    # logger.info("Generated SQL: %s", sql)

    # 5. Execute SQL safely
    try:
        result = execute_sql(conn, sql)
    except Exception as e:
        logger.exception("SQL execution failed")
        raise HTTPException(status_code=500, detail=str(e))

    # 6. Return consistent response
    return {
        "data": result,
        "rowCount": len(result),
        "query": sql,
        "executedAt": datetime.now(timezone.utc).isoformat(),
        # "sessionId": request.session_id,
        # "table": table,
        # "columns": list(schema.keys())
    }

@router.get("/session/{session_id}")
def validate_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session expired")

    if not session["table"] or not session["schema"]:
        return {
            "valid": False,
            "reason": "incomplete"
        }

    return {
        "valid": True,
        "sessionId": session_id,
        "table": session["table"],
        "schema": session["schema"],
        "rowCount": session["conn"].execute(
            f"SELECT COUNT(*) FROM {session['table']}"
        ).fetchone()[0]
    }


# from datetime import datetime, timezone
# from http.client import HTTPException
# from unittest import result
# from duckdb import sql
# from fastapi import APIRouter
# from pydantic import BaseModel
# from app.session.manager import get_session
# from app.services.ai_client import generate_sql
# from app.services.sql_executor import execute_sql

# import logging
# logger = logging.getLogger(__name__)


# router = APIRouter()

# class QueryRequest(BaseModel):
#     session_id: str
#     question: str

# @router.post("/query")
# def query(request: QueryRequest):
#     session = get_session(request.session_id)
#     if not session:
#         raise HTTPException(status_code=400, detail="Invalid session")

#     conn = session["conn"]
#     table = session.get("table")
#     schema = session.get("schema")

#     if not table or not schema:
#         return {"error": "Session missing metadata"}

#     with open("app/prompts/nl_to_sql.txt") as f:
#         template = f.read()

#     prompt = template.format(
#         table=table,
#         columns="\n".join(schema.keys())
#     ) + f"\nQuestion: {request.question}"

#     sql = generate_sql(prompt)

#     if sql.startswith("ERROR"):
#         return {"error": sql}

#     result = execute_sql(conn, sql)
#     logger.info("Executed SQL: %s", sql)
#     logger.debug("Result: %s", result)

#     return {
#         "data": result,
#         "rowCount": len(result),
#         "query": sql,
#         "executedAt": datetime.now(timezone.utc).isoformat(),
#         # "sessionId": request.session_id,
#         # "table": table,
#         # "columns": list(schema.keys())
#     }