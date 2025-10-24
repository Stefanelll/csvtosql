import pandas as pd
from pathlib import Path

# --- Folders ---
data_folder = Path("/app/data")
schema_folder = Path("/app/schemas")
output_folder = Path("/app/output")
output_folder.mkdir(exist_ok=True)

# --- Read table schemas ---
schemas = {}
for schema_file in schema_folder.glob("*.csv"):
    table_name = schema_file.stem
    df_schema = pd.read_csv(schema_file, nrows=0)  # only headers
    schemas[table_name] = list(df_schema.columns)

if not schemas:
    print("No schema CSVs found in /app/schemas!")
    exit(1)

table_list = list(schemas.keys())

# --- Read customer CSVs ---
csv_files = list(data_folder.glob("*.csv"))
if not csv_files:
    print("No customer CSVs found in /app/data!")
    exit(1)

for csv_path in csv_files:
    print(f"\nProcessing CSV: {csv_path.name}\n")
    df = pd.read_csv(csv_path)
    print("Columns found in CSV:", list(df.columns))

    # --- Step 1: Map CSV columns to table columns ---
    mappings = {}
    for col in df.columns:
        print(f"\nMapping for CSV column: '{col}'")

        # --- Table selection with Ignore option ---
        print("Select table (or ignore this column):")
        for i, t in enumerate(table_list, start=1):
            print(f"{i}. {t}")
        print(f"{len(table_list)+1}. Ignore this column")
        while True:
            try:
                table_idx = int(input("Enter table number: ").strip())
                if 1 <= table_idx <= len(table_list):
                    table = table_list[table_idx - 1]
                    break
                elif table_idx == len(table_list) + 1:
                    table = None  # mark as ignored
                    break
            except:
                pass
            print("Invalid number, try again.")

        if table is None:
            print(f"Column '{col}' will be ignored.")
            continue  # skip mapping this column


        # --- Column selection ---
        table_cols = schemas[table]
        print(f"Select column in table '{table}':")
        for i, c in enumerate(table_cols, start=1):
            print(f"{i}. {c}")
        while True:
            try:
                col_idx = int(input("Enter column number: ").strip())
                if 1 <= col_idx <= len(table_cols):
                    column = table_cols[col_idx - 1]
                    break
            except:
                pass
            print("Invalid number, try again.")

        mappings[col] = {"table": table, "column": column}

    # --- Step 2: Detect missing columns per table (only for mapped tables) ---
    table_extra_columns = {}
    used_tables = set([map_info["table"] for map_info in mappings.values()])
    for table in used_tables:
        mapped_cols = [map_info["column"] for map_info in mappings.values() if map_info["table"] == table]
        missing_cols = [c for c in schemas[table] if c not in mapped_cols]
        extra_col_values = {}
        for col in missing_cols:
            val = input(f"Table '{table}' has extra column '{col}' missing from CSV. Enter value or leave blank for placeholder: ").strip()
            if val == "":
                val = f"{col}_change_value"
            extra_col_values[col] = val
        table_extra_columns[table] = extra_col_values

    # --- Step 3: Generate INSERTs ---
    sql_statements = []
    for i, row in df.iterrows():
        for table in used_tables:
            cols = []
            vals = []

            # CSV-mapped columns
            for csv_col, map_info in mappings.items():
                if map_info["table"] != table:
                    continue
                cols.append(map_info["column"])
                value = row[csv_col]
                if pd.isna(value):
                    vals.append("NULL")
                elif isinstance(value, (int, float)):
                    vals.append(str(value))
                else:
                    vals.append(f"'{value}'")

            # Extra columns from schema
            for col, val in table_extra_columns.get(table, {}).items():
                cols.append(col)
                vals.append(f"'{val}'" if not val.startswith("'") else val)

            sql = f"INSERT INTO {table} ({', '.join(cols)})\nVALUES ({', '.join(vals)});"
            sql_statements.append(sql)
            sql_statements.append("")  # blank line between tables

        sql_statements.append(f"-- End of row {i + 1}\n")

    # --- Step 4: Write output SQL ---
    output_file = output_folder / f"{csv_path.stem}.sql"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))

    print(f"\n✅ SQL file written: {output_file}")
    print("Placeholders for column values are ready to edit manually.\n")
