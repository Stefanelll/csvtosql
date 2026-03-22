# CSV to SQL — Migration Tool

This repo contains two scripts for importing salon client & pet data into the Animalia database.

---

## Scripts

### 1. `migrate.py` — Automated migration (use this one)

Reads a customers CSV and a pets CSV, generates a ready-to-run SQL file, and optionally inserts directly into the database.

**Use this when onboarding a new salon that exports data as CSV.**

#### Required CSV files (place in `data/`)

| File | Expected columns |
|---|---|
| `cust_*.csv` | `Name, Nickname, Gender, E-Mail, Phone, Birthday, Zip Code, Address` |
| `pet_*.csv` | `Customer, Pet, Breed, Gender, Detail, Birthday` |

- The `Customer` column in the pets CSV must match the `Name` column in the customers CSV.
- Client names can have a number prefix (e.g. `"01 Moise Geanina"`) — the script strips it automatically.
- Phone numbers are normalized to `+40XXXXXXXXX`. Invalid numbers are set to `NULL` and logged in `output/problems.txt`.
- Dates are converted from `DD/MM/YYYY` to `YYYY-MM-DD` automatically.

#### How to run

```bash
docker build -t csvtosql .

docker run -it --rm --network=host -v "$PWD":/app --entrypoint python csvtosql migrate.py
```

The script will ask for:
1. **`salon_id`** — UUID of the salon in the database (look it up with the query below)
2. **DB URL** — press Enter to use the local default, or paste the production URL

Then it will:
- Write a SQL file to `output/` for review
- Show a dry-run preview (counts + sample rows)
- Ask for final confirmation before inserting into the DB

#### Finding a salon_id

```sql
SELECT id, name, created_at FROM salons WHERE name ILIKE '%salon name%';
```

**Local DB:**
```
postgresql://<user>:<password>@localhost:5433/<dbname>
```

**Production DB:**
```
postgresql://<user>:<password>@<host>/<dbname>
```

#### Output files

| File | Description |
|---|---|
| `output/*_migration.sql` | Generated SQL — review before running |
| `output/problems.txt` | Invalid phones and skipped rows |

---

### 2. `csvtosql.py` — Interactive generic mapper

An interactive script that lets you manually map any CSV column to any table/column. Useful for one-off imports or CSVs with non-standard formats.

Run it with Docker:
```bash
docker run -it --rm -v "$PWD":/app csvtosql
```

The output SQL will have placeholders (`column_change_value`) for values that need manual editing (IDs, timestamps, etc.) before running against the DB.

See `csvtosql_readme.md` for full details.
