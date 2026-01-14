import pandas as pd

def load_excel_to_db(df, conn, table_name="data"):
    # if file.filename.lower().endswith(".csv"):
    #     df = pd.read_csv(file.file)
    # # else:
    # #     df = pd.read_excel(file.file)
    # elif file.filename.lower().endswith((".xls", ".xlsx")):
    #     df = pd.read_excel(file.file)
    # else:
    #     raise ValueError("Unsupported file type")

    conn.register(table_name, df)
    return table_name
