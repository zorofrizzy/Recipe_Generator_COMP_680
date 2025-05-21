"""
This script generates a recipe from user ingredients if it is not available in the DB.

"""

from config_reader import fetch_config_dict
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

def clean_nutrition(result_list):
    """
        Clean the nutrition to incorporate the format:
        "nutrition": ["calories, total fat, sugar, sodium, protein, saturated fat"]
        convert to dict
    """
    for idx, each_recipe in enumerate(result_list):
        if isinstance(each_recipe[6], list):
            each_recipe[6] = {
                "calories": each_recipe[6][0],
                "total_fat": each_recipe[6][1],
                "sugar": each_recipe[6][2],
                "sodium": each_recipe[6][3],
                "protein": each_recipe[6][4],
                "saturated_fat": each_recipe[6][5],

            }
        elif isinstance(each_recipe[6], str):
            each_recipe[6] = {
                "calories": "",
                "total_fat": "",
                "sugar": "",
                "sodium": "",
                "protein": "",
                "saturated_fat": "",

            }

def generate_with_ollama(prompt, model="gemma3:1b", max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            # Define the payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True  # Set to False to get the full response at once
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
def generate_recipe_on_ingredients(ingredients, model="gemma3:1b"):
    # Combine all prompts into one
    prompt = f"""
    You are tasked with generating details for a recipe with the following ingredients: {', '.join(ingredients)}. Note that there could be a spelling mistake in the ingredients.
    Please provide the following information in JSON format:
    {{
        "generic_name": "A concise and generic name for the recipe (e.g., 'Yam Muffins' for 'i yam what i yam muffins').",
        "description": "A short description of the recipe. Under 300 words.",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "nutrition": ["calories", "total_fat", "sugar", "sodium", "protein", "saturated_fat"],
        "ingredient": ["ingredient1", "ingredient2", "ingredient3", "ingredient4", "ingredient5", "ingredient6"....],
        "steps": ["step1", "step2", "step3", "step4", "step5", "step6"....],
        "cuisine": "The type of cuisine this recipe belongs to.",
        "prep_time" : "time to prepare the dish",


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

def main():
    print(generate_recipe_on_ingredients(['selt', 'chikan', 'tomaeto']))

if __name__ == "__main__":
    main()