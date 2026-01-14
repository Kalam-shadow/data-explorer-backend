import pandas as pd


def infer_schema_db(conn, table_name):
    result = conn.execute(f"DESCRIBE {table_name}").fetchall()
    return {row[0]: row[1] for row in result}

def infer_schema_usable(df: pd.DataFrame) -> dict[str, str]:
    """
    Infer semantic column types for frontend + NL→SQL.
    Private helper — upload-only usage.
    """
    schema: dict[str, str] = {}

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_numeric_dtype(series):
            schema[col] = "number"
        elif pd.api.types.is_datetime64_any_dtype(series):
            schema[col] = "datetime"
        elif pd.api.types.is_bool_dtype(series):
            schema[col] = "boolean"
        else:
            schema[col] = "text"

    return schema