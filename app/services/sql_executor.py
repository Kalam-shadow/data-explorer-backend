import time
from typing import Any, Dict, List


def is_safe_sql(sql: str) -> bool:
    forbidden = ["insert", "update", "delete", "drop", "alter", "create"]
    sql_lower = sql.lower()
    return (
        sql_lower.startswith("select")
        and not any(word in sql_lower for word in forbidden)
    )


def execute_sql(conn, sql: str) -> Dict[str, Any]:
    """Execute a read-only SELECT and return columns, rows and timing.

    Returns a dict with keys: columns, rows, rowCount, columnCount, executionTimeMs
    """
    if not is_safe_sql(sql):
        raise ValueError("Unsafe SQL detected")

    start = time.time()
    cursor = conn.execute(sql)

    # cursor.description may be None for some drivers; handle defensively
    columns: List[str] = [desc[0] for desc in cursor.description] if cursor.description else []

    rows = cursor.fetchall()

    # Convert tuples to lists for JSON serialization
    rows_list: List[List[Any]] = [list(r) for r in rows]

    execution_time_ms = round((time.time() - start) * 1000, 2)

    return {
        "columns": columns,
        "rows": rows_list,
        "rowCount": len(rows_list),
        "columnCount": len(columns),
        "executionTimeMs": execution_time_ms,
    }
