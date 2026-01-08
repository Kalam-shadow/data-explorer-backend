def is_safe_sql(sql: str) -> bool:
    forbidden = ["insert", "update", "delete", "drop", "alter", "create"]
    sql_lower = sql.lower()
    return (
        sql_lower.startswith("select")
        and not any(word in sql_lower for word in forbidden)
    )

def execute_sql(conn, sql: str):
    if not is_safe_sql(sql):
        raise ValueError("Unsafe SQL detected")
    return conn.execute(sql).fetchall()
