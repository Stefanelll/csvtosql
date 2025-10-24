# CSV to PostgreSQL SQL Generator

This tool reads CSV files from customers and generates PostgreSQL `INSERT` statements based on your table schemas.

---

## Steps

**Step 1: Put your CSV files in `data/`**

**Step 2: Put your table schemas in `schemas/`**

* Each table schema is a CSV file.
* File name = table name, e.g., `pets.csv`
* Include all columns for the table (headers only, comma-separated). Example `pets.csv`:

```
id,salon_id,name,phone,email,address,notes,is_active,created_at,updated_at
```

**Step 3: Run the script**

### RECOMANDAT: Using Docker (simplest)

1. Build the Docker image:

```bash
docker build -t csvtosql .
```

2. Run the container
- WINDOWS:

```bash
docker run -it --rm -v "%cd%":/app csvtosql
```

- MacOS:
```bash
docker run -it --rm -v "$PWD":/app csvtosql
```

### OPTIONAL: Using Python locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the script:

```bash
python csvtosql.py
```

**Step 4: Follow the prompts**

* For each CSV column, select which table and column it maps to.
* For missing columns in the table, enter a value or leave blank for a placeholder.
* Placeholders: `column_change_value` for missing values.

**Step 5: Look at the output**

* Generated SQL files are in `output/`.
* For each CSV file, there is a corresponding `.sql` file.
* Example output:

```sql
INSERT INTO clients (id,salon_id,name,phone,email,address,notes)
VALUES ('id_change_value', '123', 'Gordon', 'phone_change_value', 'gordon@gmail.com', 'Paltinisului', 'notes_change_value');
-- End of row 1
```
