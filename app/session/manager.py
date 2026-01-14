import duckdb
import uuid
import time

_sessions = {}

SESSION_TTL = 30 * 60  # 30 minutes
def create_session():
    session_id = str(uuid.uuid4())
    conn = duckdb.connect(":memory:")
    _sessions[session_id] = {
        "conn": conn,
        "table": None,
        "schema_db": None,
        "schema": None,
        "df": None,       # optional: keep DataFrame copy
        "file_path": None, # optional: if you save to disk
        "created_at": time.time(),
        "last_access": time.time()
    }
    return session_id

# def get_session(session_id: str):
#     return _sessions.get(session_id)
def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        return None

    if time.time() - session["last_access"] > SESSION_TTL:
        delete_session(session_id)
        return None

    session["last_access"] = time.time()
    return session


def store_metadata(session_id: str, table: str, schema_db: dict, schema: dict, df=None, file_path=None):
    if session_id in _sessions:
        _sessions[session_id]["table"] = table
        _sessions[session_id]["schema"] = schema
        _sessions[session_id]["schema_db"] = schema_db
        _sessions[session_id]["df"] = df
        _sessions[session_id]["file_path"] = file_path


def delete_session(session_id: str):
    session = _sessions.pop(session_id, None)
    if session:
        conn = session["conn"]
        conn.close()
