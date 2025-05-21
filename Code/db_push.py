"""
This script is use to batch insert data in the database. Credentials to be picked from the config.ini file.
Functionality:
    1. Read Config Dict
    2. Connect to DB.
    3. Read the CSV files
    4. Validate the csv rows
    5. Push batch to DB.

DB Create script -->
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    instructions TEXT[],
    main_ingredients TEXT[],
    tags TEXT[],
    nutrition TEXT[],
    total_time TEXT,
    image_url TEXT,
    ingredients_tokenized TEXT[],
    data_source TEXT
);

"""


import psycopg2
import ast
from config_reader import fetch_config_dict
import os
import pandas as pd



db_columns = [
'id', 'name', 'description', 'instructions', 'main_ingredients',
'tags', 'nutrition', 'total_time', 'image_url',
'ingredients_tokenized', 'data_source']

ARRAY_COLUMNS = {'instructions', 'main_ingredients', 'tags', 'nutrition', 'ingredients_tokenized'}


# Connect to Database
def create_connection(config_dict):
    """
        This function creates the connection to the database and returns the cursor object.
        Input -> config.ini data (dict)
        Output -> Conn object.
    """
    # Database connection setup
    conn = psycopg2.connect(
        dbname=config_dict["dbname"],
        user=config_dict["user"],
        password=config_dict["password"],
        host=config_dict["host"],
        port=config_dict["port"]
    )
    #cur = conn.cursor()
    return conn

# Read CSV file
def read_csv_file(csv_path, csv_to_fetch):
    """
        Read the csv file based on the input argument.
    """
    df = pd.read_csv(os.path.join(csv_path, csv_to_fetch))
    return df

# Get Column Mapping for each CSV file
def get_column_mapping(key):
    """
        This fxn returns the column mapping for each of the files.
        DB COlumn : CSV Column
    """

    # Column mapping from DB to CSV
    COLUMN_MAP = {
    'big_csv.csv': {
        'name': 'name',
        'description': 'description',
        'instructions': 'steps',
        'main_ingredients': 'ingredients',
        'tags': 'tags',
        'nutrition': 'nutrition',
        'total_time': 'minutes',
        'image_url': '',
        'ingredients_tokenized': 'ingredients',
        'data_source': 'big_csv'
        },
    'small_csv.csv': {
        'name': 'Title',
        'description': '',
        'instructions': 'split_steps',
        'main_ingredients': 'Cleaned_Ingredients',
        'tags': '',
        'nutrition': '',
        'total_time': '',
        'image_url': '',
        'ingredients_tokenized': 'Ingredients_tokenized',
        'data_source': 'small_csv'
        }
    }

    return COLUMN_MAP.get(key, {})

# Get max ID from the table
def get_max_id(cursor):
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM recipes;")
    return cursor.fetchone()[0]

# Validate each row of df
def validate_and_transform_row(row, column_map):
    transformed_row = []
    for db_col in db_columns:
        if db_col == 'id':
            transformed_row.append(None)  # Placeholder for ID
            continue  # Skip the primary key

        csv_col = column_map.get(db_col)
        value = row.get(csv_col, None)

        # Normalize NaN to None
        if pd.isna(value):
            value = None

        # Convert list-type columns to Python lists
        if db_col in ARRAY_COLUMNS:
            if isinstance(value, str):
                try:
                    value = ast.literal_eval(value)
                    if not isinstance(value, list):
                        value = [value]
                except Exception:
                    value = [v.strip() for v in value.split(',') if v.strip()]
            else:
                value = value if isinstance(value, list) else []

        transformed_row.append(value)

    return transformed_row  # Ensure no critical fields are missing

# Push batch to DB.
def insert_batch(conn, rows):
    cols = [col for col in db_columns]
    placeholders = ", ".join(["%s"] * len(cols))
    insert_query = f"INSERT INTO recipes ({', '.join(cols)}) VALUES ({placeholders});"

    with conn.cursor() as cur:
        cur.executemany(insert_query, rows)
    conn.commit()

# Generate Primary Key ID & Append Data SOurce.
def generate_ids(rows, max_id, filename):
    """
        This function adds the max_id as the id to the first element of list.
        This function adds the filename as the data source to the last element of list.
    """
    for i, row in enumerate(rows):
        row[0] = max_id + i + 1  # Replace the placeholder (index 0) with the generated ID
        row[-1] = filename
        yield row


# Start the CSV Processing.
def process_csv(df, conn, column_map, filename, batch_size=100):
    valid_rows = []
    failed_rows = []

    # Get the current maximum ID
    with conn.cursor() as cur:
        max_id = get_max_id(cur)

    for _, row in df.iterrows():
        try:
            transformed_row = validate_and_transform_row(row, column_map)
            valid_rows.append(transformed_row)
        except Exception as e:
            print(f"Error processing row: {row}, Error: {e}")
            failed_rows.append(row)

        # Batch insert
        if len(valid_rows) >= batch_size:
            rows_with_ids = list(generate_ids(valid_rows, max_id, filename))
            insert_batch(conn, rows_with_ids)
            max_id += len(valid_rows)  # Update the max_id and data source for the next batch
            valid_rows.clear()
    # Add Data Source here


    # Final insert
    if valid_rows:
        rows_with_ids = list(generate_ids(valid_rows, max_id, filename))
        insert_batch(conn, rows_with_ids)

    # Save failed rows
    if failed_rows:
        failed_df = pd.DataFrame(failed_rows)
        fail_filename = f"failed_{os.path.basename(filename)}"
        failed_df.to_csv(fail_filename, index=False)
        print(f"⚠️ Saved failed records to {fail_filename}")

# MAIN
def main():
    """
        Main function to enter the script.
    """
    # Fetch config dict.

    config_dict = fetch_config_dict()
    
    # CSV file names
    csv_path = os.path.join(config_dict.get('base_directory', ''), config_dict.get('data_dir', ''))
    small_csv_name, big_csv_name = os.listdir(csv_path) # [small.csv, big_csv]


    # Connect to DB
    conn = create_connection(config_dict)
    print("Connected to DB")

    # Read the small csv file.
    small_csv = read_csv_file(csv_path, small_csv_name)
    print(f"Processing: {small_csv_name}")
    column_map = get_column_mapping(small_csv_name)
    process_csv(small_csv, conn, column_map, small_csv_name, batch_size=100)

    # Read the small csv file.
    big_csv = read_csv_file(csv_path, big_csv_name)
    print(f"Processing: {big_csv_name}")
    column_map = get_column_mapping(big_csv_name)
    process_csv(big_csv, conn, column_map, big_csv_name, batch_size=100)

if __name__ ==  '__main__':

    main()