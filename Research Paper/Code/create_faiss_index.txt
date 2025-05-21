"""
This script:

1. Loads data from DB.
2. Creates index on tokenized ingredients and saves it to file.
3. Saves id (primary key) into the index folder.
 
"""

import os
from config_reader import fetch_config_dict
import psycopg2
import pandas as pd
import re
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# Initialize model to generate embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

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

# Fetch data from DB
def fetch_data_from_db(conn):
    # Query to fetch required columns
    query = """
    SELECT id, ingredients_tokenized
    FROM recipes;
    """
    
    # Load data into a Pandas DataFrame
    df = pd.read_sql(query, conn)
    
    # Close the connection
    conn.close()
    
    return df

#Clean DB data after fetching
def preprocess_ingredients(ingredients):
    """
    Preprocesses a list of ingredients by lowercasing, removing punctuation, and stripping whitespace.
    """
    if isinstance(ingredients, list):
        return [re.sub(r'[^\w\s]', '', ingredient.lower()).strip() for ingredient in ingredients if ingredient.strip()]
    return []


def generate_embedding(ingredients):
    """
    Generates a dense embedding for a list of ingredients.
    """
    processed_ingredients = preprocess_ingredients(ingredients)
    embedding = model.encode(" ".join(processed_ingredients))
    return embedding

def build_faiss_index(embeddings):
    """
    Builds a FAISS index for fast similarity search.
    """
    dimension = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dimension)  # L2 distance for dense vectors
    index.add(np.vstack(embeddings))  # Add embeddings to the index
    return index

def save_faiss_index(faiss_index, recipe_ids, index_path):
    # Save the FAISS index
    faiss.write_index(faiss_index, os.path.join(index_path, "recipe_index.faiss"))
    print("Saved Index to File")
    
    # Save the recipe IDs
    np.save(os.path.join(index_path,"recipe_ids.npy"), recipe_ids)
    print("Saved Recipe ID to file.")

def main_create_embeddings():
    
    # Read config dict
    config_dict = fetch_config_dict()

    # Create Index output folder.
    base_directory = config_dict.get('base_directory', '')
    index_directory = config_dict.get('index_directory', '')
    index_path = os.path.join(base_directory, index_directory)
    if not os.path.exists(index_path):
        os.mkdir(index_path)
        print("Created directory to store index.")
    
    # Load data from DB.
    conn = create_connection(config_dict)
    df = fetch_data_from_db(conn)
    print("Loaded data from DB.")

    # Apply embedding generation to the DataFrame
    df["embedding"] = df["ingredients_tokenized"].apply(generate_embedding)
    print("Embeddings Generated")

    # Build the FAISS index
    embeddings = df["embedding"].tolist()
    faiss_index = build_faiss_index(embeddings)
    print("FAISS Index Generated")

    # Map recipe IDs to FAISS indices
    recipe_ids = df["id"].values

    # Save FAISS Index to file.
    save_faiss_index(faiss_index, recipe_ids, index_path)

    

if __name__ == '__main__':
    main_create_embeddings()