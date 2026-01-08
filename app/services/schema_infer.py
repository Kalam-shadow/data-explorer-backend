def infer_schema(conn, table_name):
    result = conn.execute(f"DESCRIBE {table_name}").fetchall()
    return {row[0]: row[1] for row in result}
