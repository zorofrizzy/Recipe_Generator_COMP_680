"""
    This script:
    1. loads the FAISS index from file.
    2. Creates embedding of User Input ingredients.
    3. The dense embedding vector is then matched with the FAISS Index.
    4. The top 5 vectors are finalized.
    5. DB lookup for this is returned based on the id.
    6. Ranking of results based on nearest match.

"""

from flask import Flask, request, jsonify
import os
from config_reader import fetch_config_dict
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import re
from cli_fetch_recipe_ai import generate_recipe, generate_recipe_from_theme
import fetch_images

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config_dict = fetch_config_dict()

# Initialize model to generate embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

# Load FAISS index and recipe IDs
base_directory = config_dict.get('base_directory', '')
index_folder = config_dict.get('index_directory', '')
index_path = os.path.join(base_directory, index_folder)

faiss_index = faiss.read_index(os.path.join(index_path, "recipe_index.faiss"))
recipe_ids = np.load(os.path.join(index_path, "recipe_ids.npy"))
return_by_ai = bool(int(config_dict.get("return_by_ai", '0')))

print("FAISS index and recipe IDs loaded successfully.")


# Connect to Database
def create_connection():
    """
    Creates a connection to the database and returns the connection object.
    """
    conn = psycopg2.connect(
        dbname=config_dict["dbname"],
        user=config_dict["user"],
        password=config_dict["password"],
        host=config_dict["host"],
        port=config_dict["port"]
    )
    return conn



# Preprocess user input
def preprocess_ingredients(ingredients):
    """
    Preprocesses a list of ingredients by lowercasing, removing punctuation, and stripping whitespace.
    """
    if isinstance(ingredients, str):
        ingredients = [ingredients]

    if isinstance(ingredients, list):
        return [re.sub(r'[^\w\s]', '', ingredient.lower()).strip() for ingredient in ingredients if ingredient.strip()]
    return []

# Generate embedding on user input
def generate_embedding(ingredients):
    """
    Generates a dense embedding for a list of ingredients.
    """
    processed_ingredients = preprocess_ingredients(ingredients)
    embedding = model.encode(" ".join(processed_ingredients))
    return embedding

# Query FAISS
def query_faiss(user_embedding, index, recipe_ids, top_k=15):
    """
    Queries the FAISS index to find the top-k closest matches.
    """
    distances, indices = index.search(np.array([user_embedding]), k=top_k)
    
    # Map FAISS indices to recipe IDs
    matching_recipe_ids = recipe_ids[indices.flatten()]
    return matching_recipe_ids, distances.flatten()

# Fetch matching recipes from the database
def fetch_matching_recipes(recipe_ids, conn):
    """
    Fetches detailed information for matching recipes from the database.
    """
    try:
        # Convert recipe IDs to integers
        recipe_ids = [int(s) for s in recipe_ids]

        # Query to fetch detailed information for matching recipes
        query = """
        SELECT *
        FROM recipes
        WHERE id = ANY(%s);
        """

        # Execute the query
        with conn.cursor() as cur:
            cur.execute(query, (list(recipe_ids),))
            results = cur.fetchall()

        return results
    except Exception as e:
        print(f"Error fetching matching recipes: {e}")
        raise

# Rank results based on substring match
def ranked_results(results, user_input):
    """
    Ranks the results based on how many user input ingredients appear as substrings in each recipe's ingredient list.
    """
    # Preprocess user input: Remove spaces, hyphens, and convert to lowercase
    user_input = [ingredient.lower().replace(" ", "").replace("-", "") for ingredient in user_input]
    ai_flag_list = []
    # Initialize a dictionary to store match counts
    ranked_idx = {}
    for idx, result in enumerate(results):
        # Extract and preprocess the ingredient list from the result
        ingredient_list = result[-2]  # Assuming ingredients are in the second-to-last column
        ingredient_string = "".join(ingredient_list).lower().replace(" ", "").replace("-", "")

        # Count matches using substring search
        match_counter = sum(1 for user_ingredient in user_input if user_ingredient in ingredient_string)
        ranked_idx[idx] = match_counter
        ai_flag_list.append(match_counter)
    
    if return_by_ai:
        # If no exact match is found then we get data using AI
        ai_flag_list_shortened = list(set(ai_flag_list))
        if ai_flag_list_shortened == [0]:
            return True # Return True for AI generated response.
    # Sort the results by match count in descending order
    sorted_indices = sorted(ranked_idx.keys(), key=lambda x: ranked_idx[x], reverse=True)

    # Return the sorted results
    sorted_results = [results[i] for i in sorted_indices]
    return sorted_results
# Write URL to DB
def upload_url_to_db(primary_id, url, conn):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE recipes
                   SET image_url = %s
                 WHERE id         = %s;
                """,
                (url, primary_id)          
            )

        conn.commit()                     
        print("URL updated in DB.")
    except Exception:                      
        conn.rollback()                    # undo partial work
        raise                              

# Clean FAISS response
def clean_faiss_response(input_json, conn):
    """
        Match keys. Add for cuisine and image url. 
    """
    results = input_json.get("results", [])

    for each_result in results:
        
        if each_result.get("image_url", "") not in  ["", None]:
            pass

        elif each_result.get("image_url", "") in ["", None]:
            each_result["image_url"] = fetch_images.main(each_result["name"])

            # Write to DB
            upload_url_to_db(each_result['id'], each_result["image_url"], conn)
        each_result["cuisine"] = ""

        if isinstance(each_result.get("nutrition", []), list) and len(each_result.get("nutrition", [])) == 7:
            nutrition_dict = {
                
                "calories": each_result["nutrition"][0],
                "protein": each_result["nutrition"][1],
                "saturated_fat": each_result["nutrition"][2],
                "sodium": each_result["nutrition"][3],
                "sugar": each_result["nutrition"][4],
                "total_fat": each_result["nutrition"][5],
            }
            each_result["nutrition"] = nutrition_dict

    return input_json

# Clean the AI response
def clean_ai_response(input_json):
    """
        1. Convert outer dict to list.
        2. Match key names.
    
    """
    recipe_dict = input_json.get("results", {})

    # Fix keys
    recipe_dict["id"] = -1
    recipe_dict["name"] = recipe_dict.get("generic_name", "")
    recipe_dict["source"] = "AI Generated"
    recipe_dict["image_url"] = recipe_dict.get("image_url", "")
    ingredients_list = []

    if recipe_dict.get("ingredients"):
        ingredients_list = recipe_dict["ingredients"]
    elif recipe_dict.get("ingredient"):
        ingredients_list = recipe_dict["ingredient"]
    else:
        ingredients_list = []

    recipe_dict["ingredients_tokenized"] = ingredients_list
    recipe_dict["ingredients"] = ingredients_list
    # recipe_dict["image_url"] = recipe_dict.get("image_url", "")
    if recipe_dict['image_url'].strip() == "":
        recipe_dict["image_url"] = fetch_images.main(recipe_dict["name"])

    input_json["results"] = [recipe_dict]
    return input_json

# Define the surprise endpoint
@app.route('/surprise', methods=['GET'])
def surprise():
    try:
        # Get user input ingredients from query parameters
        user_input = request.args.getlist('ingredients')
        if not user_input:
            user_input = "Random Recipe please"
        else:
            user_input = " ".join(user_input)

        print("Received user input:", user_input)


        ai_recipe = generate_recipe_from_theme(theme = user_input)
            
        return jsonify(clean_ai_response({"results": ai_recipe})), 200 # return list to handle.

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Define the search endpoint
@app.route('/search', methods=['GET'])
def search():
    try:
        # Get user input ingredients from query parameters
        user_input = request.args.getlist('ingredients')
        if not user_input:
            return jsonify({"error": "No ingredients provided"}), 400

        print("Received user input:", user_input)

        # Generate embedding for user input
        user_embedding = generate_embedding(user_input)

        # Query FAISS
        matching_recipe_ids, _ = query_faiss(user_embedding, faiss_index, recipe_ids, top_k=25)

        # Fetch results from DB
        conn = create_connection()
        results = fetch_matching_recipes(matching_recipe_ids, conn)
        

        # Rank results
        ranked_results_list = ranked_results(results, user_input)
        if ranked_results_list == True:
            ai_recipe = generate_recipe(ingredients = user_input)
            
            return jsonify(clean_ai_response({"results": ai_recipe})), 200 # return list to handle.
        # Format the response
        formatted_results = []
        for result in ranked_results_list[:5]:  # Return top 5 results
            formatted_results.append({
                "id": result[0],
                "name": result[1],
                "description": result[2],
                "steps" : result[3],
                "ingredients": result[4],
                "tags": result[5],
                "nutrition": result[6],
                "prep_time": result[7],
                "image_url": result[8],
                "ingredients_tokenized": result[-2],
                "source": result[-1]
            })

        return jsonify(clean_faiss_response({"results": formatted_results}, conn)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)