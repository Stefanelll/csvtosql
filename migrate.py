import pandas as pd
import uuid
import re
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------ helpers

def strip_prefix(name):
    """Remove leading number prefix like '01 ' from name."""
    if not name:
        return name
    return re.sub(r'^\d+\s+', '', str(name).strip())

def parse_date(val):
    """Parse DD/MM/YYYY or YYYY-MM-DD to YYYY-MM-DD."""
    if not val or str(val).strip() == '':
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y'):
        try:
            return datetime.strptime(str(val).strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def format_phone(val):
    """Normalize Romanian phone numbers to +40XXXXXXXXX."""
    if not val or str(val).strip() == '':
        return None
    phone = re.sub(r'\s+', '', str(val).strip())
    if phone.startswith('07') and len(phone) == 10:
        return '+4' + phone
    if phone.startswith('+40') and len(phone) == 12:
        return phone
    return None  # invalid, skip

def escape(val):
    if val is None:
        return 'NULL'
    return "'" + str(val).replace("'", "''") + "'"

def map_gender(val):
    if not val or str(val).strip() == '':
        return None
    v = str(val).strip().upper()
    if v == 'M':
        return 'MALE'
    if v == 'F':
        return 'FEMALE'
    return None

def find_csv(data_folder, keywords):
    """Find a CSV file in data_folder whose name contains any of the keywords."""
    for f in data_folder.glob('*.csv'):
        name_lower = f.name.lower()
        if any(k in name_lower for k in keywords):
            return f
    return None

# ------------------------------------------------------------------ main

def main():
    data_folder = Path('data')
    output_folder = Path('output')
    output_folder.mkdir(exist_ok=True)

    # --- Auto-detect CSVs
    cust_csv = find_csv(data_folder, ['cust', 'customer', 'client'])
    pet_csv  = find_csv(data_folder, ['pet'])

    if not pet_csv and not cust_csv:
        print('❌ No CSV files found in data/')
        return

    if cust_csv:
        print(f'👤 Customers CSV : {cust_csv.name}')
    else:
        print('ℹ️  No customers CSV found — will extract clients from pets CSV.')
    if pet_csv:
        print(f'🐾 Pets CSV      : {pet_csv.name}')
    else:
        print('ℹ️  No pets CSV found — only clients will be imported.')

    # --- Inputs
    salon_id = input('\nEnter salon_id: ').strip()
    if not salon_id:
        print('❌ salon_id cannot be empty')
        return

    db_url = input('Enter DB URL (leave blank for default local): ').strip()
    if not db_url:
        print('❌ DB URL cannot be empty')
        return

    # -------------------------------------------------------------- clients

    client_id_map = {}   # raw_name -> new UUID
    client_rows   = []   # SQL value tuples
    problems      = []

    if cust_csv:
        df_cust = pd.read_csv(cust_csv, dtype=str).fillna('')
        for _, row in df_cust.iterrows():
            raw_name = str(row.get('Name', '')).strip()
            if not raw_name:
                continue

            new_id     = str(uuid.uuid4())
            client_id_map[raw_name] = new_id
            clean_name = strip_prefix(raw_name)
            email      = str(row.get('E-Mail', '')).strip() or None
            phone      = format_phone(row.get('Phone', ''))
            address    = str(row.get('Address', '')).strip() or None

            if row.get('Phone', '').strip() and phone is None:
                problems.append(f'Client "{clean_name}": invalid phone "{row.get("Phone", "")}" → set to NULL')

            client_rows.append(
                f"('{new_id}', '{salon_id}', {escape(clean_name)}, "
                f"{escape(email)}, {escape(phone)}, {escape(address)}, "
                f"TRUE, FALSE, FALSE, NOW(), NOW())"
            )
    elif pet_csv:
        # Fall back: extract unique clients from pets CSV
        df_pets_tmp = pd.read_csv(pet_csv, dtype=str).fillna('')
        for raw_name in df_pets_tmp['Customer'].unique():
            raw_name = str(raw_name).strip()
            if not raw_name:
                continue
            new_id = str(uuid.uuid4())
            client_id_map[raw_name] = new_id
            clean_name = strip_prefix(raw_name)
            client_rows.append(
                f"('{new_id}', '{salon_id}', {escape(clean_name)}, "
                f"NULL, NULL, NULL, TRUE, FALSE, FALSE, NOW(), NOW())"
            )

    clients_sql = (
        "INSERT INTO clients "
        "(id, salon_id, name, email, phone, address, is_active, is_blocked, is_whitelisted, created_at, updated_at) VALUES\n"
        + ',\n'.join(client_rows)
        + ';\n'
    )

    # -------------------------------------------------------------- pets

    pet_rows = []

    if pet_csv:
        df_pets = pd.read_csv(pet_csv, dtype=str).fillna('')
        for _, row in df_pets.iterrows():
            raw_customer = str(row.get('Customer', '')).strip()
            pet_name     = str(row.get('Pet', '')).strip()

            if not raw_customer or not pet_name:
                problems.append(f'Skipped row — missing Customer or Pet name')
                continue

            client_id = client_id_map.get(raw_customer)
            if not client_id:
                problems.append(f'Skipped pet "{pet_name}" — no matching client for "{raw_customer}"')
                continue

            pet_id     = str(uuid.uuid4())
            breed      = escape(str(row.get('Breed', '')).strip() or None)
            gender     = escape(map_gender(row.get('Gender', '')))
            notes      = escape(str(row.get('Detail', '')).strip() or None)
            birth_date = escape(parse_date(row.get('Birthday', '')))

            pet_rows.append(
                f"('{pet_id}', '{client_id}', {escape(pet_name)}, "
                f"{breed}, {gender}, {birth_date}, {notes}, TRUE, NOW(), NOW())"
            )

    pets_sql = (
        "INSERT INTO pets "
        "(id, client_id, name, breed, gender, birth_date, notes, is_active, created_at, updated_at) VALUES\n"
        + ',\n'.join(pet_rows)
        + ';\n'
    ) if pet_rows else None

    # -------------------------------------------------------------- write SQL

    stem = pet_csv.stem if pet_csv else cust_csv.stem
    output_path   = output_folder / f'{stem}_migration.sql'
    problems_path = output_folder / 'problems.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'-- Migration for salon_id: {salon_id}\n')
        f.write(f'-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'-- Clients: {len(client_rows)} | Pets: {len(pet_rows)}\n\n')
        f.write('-- ===== CLIENTS =====\n')
        f.write(clients_sql)
        if pets_sql:
            f.write('\n-- ===== PETS =====\n')
            f.write(pets_sql)

    with open(problems_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(problems) if problems else 'No problems found.')

    print(f'\n✅ SQL file    : {output_path}')
    print(f'📄 Problems    : {problems_path}')
    print(f'   Clients    : {len(client_rows)}')
    print(f'   Pets       : {len(pet_rows)}')
    if problems:
        print(f'   ⚠️  Problems : {len(problems)} (see problems.txt)')

    # -------------------------------------------------------------- confirm & run

    print(f'\n⚠️  Review the SQL file before running against the DB.')
    confirm = input('Run against DB now? (yes/no): ').strip().lower()
    if confirm != 'yes':
        print('👍 Skipped. SQL file is ready for manual review.')
        return

    # --- Dry-run preview
    print('\n' + '='*50)
    print('DRY-RUN PREVIEW')
    print('='*50)
    print(f'  Salon ID  : {salon_id}')
    print(f'  Clients   : {len(client_rows)} rows will be inserted into clients')
    print(f'  Pets      : {len(pet_rows)} rows will be inserted into pets')
    if problems:
        print(f'  ⚠️  Problems: {len(problems)} (phones set to NULL, see problems.txt)')
    print('\nSample clients (first 3):')
    for r in client_rows[:3]:
        print(f'  {r[:80]}...')
    if pet_rows:
        print('\nSample pets (first 3):')
        for r in pet_rows[:3]:
            print(f'  {r[:80]}...')
    print('='*50)

    final = input('\nEverything looks good? Confirm insert (yes/no): ').strip().lower()
    if final != 'yes':
        print('👍 Aborted. SQL file is still available for manual review.')
        return

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.begin() as conn:
            print('\nInserting clients...')
            conn.execute(text(clients_sql))
            print(f'✅ {len(client_rows)} clients inserted.')
            if pets_sql:
                print('Inserting pets...')
                conn.execute(text(pets_sql))
                print(f'✅ {len(pet_rows)} pets inserted.')
        print('\n🎉 Migration complete!')
    except Exception as e:
        print(f'\n❌ DB error: {e}')
        print('The SQL file is still available for manual inspection.')


if __name__ == '__main__':
    main()
