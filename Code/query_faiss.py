"""
    This script:
    1. loads the FAISS index from file.
    2. Creates embedding of User Input ingredients.
    3. The dense embedding vector is then matched with the FAISS Index.
    4. The top 5 vectors are finalized.
    5. DB lookup for this is returned based on the id.

"""


import os
from config_reader import fetch_config_dict
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import re

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

# Load index from file.
def load_index(index_path):
    """
        Loads index from path.
    """
    # Load the FAISS index
    faiss_index = faiss.read_index(os.path.join(index_path, "recipe_index.faiss"))

    # Load the recipe IDs
    recipe_ids = np.load(os.path.join(index_path,"recipe_ids.npy"))

    return faiss_index, recipe_ids

#Preprocess user input
def preprocess_ingredients(ingredients):
    """
    Preprocesses a list of ingredients by lowercasing, removing punctuation, and stripping whitespace.
    """
    if isinstance(ingredients, str):
        ingredients = [ingredients]

    if isinstance(ingredients, list):
        return [re.sub(r'[^\w\s]', '', ingredient.lower()).strip() for ingredient in ingredients if ingredient.strip()]
    return []

#Generate embedding on user input
def generate_embedding(ingredients):
    """
    Generates a dense embedding for a list of ingredients.
    """
    processed_ingredients = preprocess_ingredients(ingredients)
    embedding = model.encode(" ".join(processed_ingredients))
    return embedding

# query faiss.
def query_faiss(user_embedding, index, recipe_ids, top_k=15):
    """
    Queries the FAISS index to find the top-k closest matches.
    """
    
    # Query the FAISS index
    distances, indices = index.search(np.array([user_embedding]), k=top_k)
    
    # Map FAISS indices to recipe IDs
    matching_recipe_ids = recipe_ids[indices.flatten()]
    return matching_recipe_ids, distances.flatten()

def fetch_matching_recipes(recipe_ids, conn):
    """
    Fetches detailed information for matching recipes from the database.
    """
    try:
        # Convert recipe id to int  from NP Array
        recipe_ids = [int(s) for s in recipe_ids]

        # Query to fetch detailed information for matching recipes
        query = f"""
        SELECT *
        FROM recipes
        WHERE id = ANY(%s);
        """
        
        # Execute the query
        with conn.cursor() as cur:
            cur.execute(query, (list(recipe_ids),))
            results = cur.fetchall()
        
        # Close the connection
        conn.close()
        
        return results
    except Exception as e:
        print(f"Error fetching matching recipes: {e}")
        raise
def ranked_results(results, user_input):
    """
    The results are ranked based on how many user input ingredients appear as substrings in each recipe's ingredient list.
    """
    # Preprocess user input: Remove spaces, hyphens, and convert to lowercase
    user_input = [ingredient.lower().replace(" ", "").replace("-", "") for ingredient in user_input]

    # Initialize a dictionary to store match counts
    ranked_idx = {}
    for idx, result in enumerate(results):
        # Extract and preprocess the ingredient list from the result
        ingredient_list = result[-2]  # Assuming ingredients are in the second-to-last column
        ingredient_string = "".join(ingredient_list).lower().replace(" ", "").replace("-", "")
        
        # Count matches using substring search
        match_counter = sum(1 for user_ingredient in user_input if user_ingredient in ingredient_string)
        ranked_idx[idx] = match_counter

    # Sort the results by match count in descending order
    sorted_indices = sorted(ranked_idx.keys(), key=lambda x: ranked_idx[x], reverse=True)

    # Return the sorted results
    sorted_results = [results[i] for i in sorted_indices]
    return sorted_results

def main(user_input):
    
    # Load Index from file.
    print("Loading Index from file.")
    config_dict = fetch_config_dict()
    base_directory = config_dict.get('base_directory', '')
    index_folder = config_dict.get('index_directory', '')

    index_path = os.path.join(base_directory, index_folder)

    faiss_index, recipe_ids = load_index(index_path)
    print("Done.\nGenerating Embedding of User Input.")

    # Generate embedding for user input
    user_embedding = generate_embedding(user_input)
    print("Done.\nQuerying FAISS.")
    # Query FAISS
    matching_recipe_ids, distances = query_faiss(user_embedding, faiss_index, recipe_ids, top_k=25)
    print("Matching recipe IDs :", matching_recipe_ids)

    # Fetch results from DB
    conn = create_connection(config_dict)
    results = fetch_matching_recipes(matching_recipe_ids, conn)
    print("Results from DB : \n", results)
    results = ranked_results(results, user_input)
    print("Ranked_results\n", results[:5])


if __name__ == "__main__":
    user_input = ['chicken', 'butter', 'rice', 'cream', 'vodka']
    main(user_input)