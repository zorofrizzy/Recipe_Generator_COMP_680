import pandas as pd
import requests
import json
import time
import re

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def clean_response(response):
    # Remove Markdown triple backticks and `json` label
    response = re.sub(r"```json|```", "", response)
    # Strip leading/trailing whitespace and newlines
    response = response.strip()
    return response

def generate_with_ollama(prompt, model="gemma3:1b", max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            # Define the payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False  # Set to False to get the full response at once
            }
            
            # Send the POST request
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # Clean the response
                cleaned_response = clean_response(raw_response)
                return cleaned_response
            else:
                print(f"Error: {response.status_code}, {response.text}")
                retries += 1
                time.sleep(2 ** retries)  # Exponential backoff
        
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}. Retrying ({retries + 1}/{max_retries})...")
            retries += 1
            time.sleep(2 ** retries)  # Exponential backoff
    
    raise Exception("Failed to generate response after multiple retries.")


# Function to call generation
def generate_recipe_details(recipe_name, ingredients, model="gemma3:1b"):
    # Combine all prompts into one
    prompt = f"""
    You are tasked with generating details for a recipe named "{recipe_name}" with the following ingredients: {', '.join(ingredients)}.
    Please provide the following information in JSON format:
    {{
        "generic_name": "A concise and generic name for the recipe (e.g., 'Yam Muffins' for 'i yam what i yam muffins').",
        "description": "A short description of the recipe.",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "cuisine": "The type of cuisine this recipe belongs to."
    }}
    Ensure the response is valid JSON.
    """
    
    # Generate response
    response = generate_with_ollama(prompt, model)
    
    # Parse JSON response
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {response}")
        raise ValueError("Invalid JSON response from Ollama.") from e


# Load recipes from a CSV file
df = pd.read_csv(r"C:\Users\zsj36405\Desktop\COMP 680\Recipe_Generator\temp_data\small_csv.csv")

# Ensure columns exist
df["description"] = df.get("description", None)
df["tags"] = df.get("tags", None)
df["cuisine"] = df.get("cuisine", None)
df["generic_name"] = df.get("generic_name", None)

# Define batch size
batch_size = 50

# Counter to track processed rows
processed_count = 0

for index, row in df.iterrows():
    start_time = time.time()
    if pd.isna(row["description"]) or pd.isna(row["tags"]) or pd.isna(row["cuisine"] or pd.isna(row["generic_name"])):
        recipe_name = row["Title"]
        ingredients = row["Ingredients"]  # Assuming this is a list or string
        
        # Convert ingredients to a list if it's a string
        if isinstance(ingredients, str):
            ingredients = [ingredient.strip() for ingredient in ingredients.split(",")]
        
        # Generate details
        try:
            details = generate_recipe_details(recipe_name, ingredients)
            df.at[index, "description"] = details["description"]
            df.at[index, "tags"] = ", ".join(details["tags"])
            df.at[index, "cuisine"] = details["cuisine"]
            df.at[index, "generic_name"] = details["generic_name"]
        except Exception as e:
            print(f"Failed to process recipe '{recipe_name}': {e}")
    # Increment processed count
    processed_count += 1
    print("Processed recipe # {} in {:.2f} seconds".format(processed_count, time.time() - start_time))
    # Save the DataFrame every `batch_size` rows
    if processed_count % batch_size == 0:
        print(f"Processed {processed_count} rows. Saving progress...")
        df.to_csv(r"C:\Users\zsj36405\Desktop\COMP 680\Recipe_Generator\temp_data\updated_small_csv.csv", index=False)

# Save updated data back to CSV
df.to_csv(r"C:\Users\zsj36405\Desktop\COMP 680\Recipe_Generator\temp_data\updated_small_csv.csv", index=False)