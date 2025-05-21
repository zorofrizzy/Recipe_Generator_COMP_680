"""
    This script:
    1. Fetches image URL from unsplash.
    2. Downloads them to a local folder.
    3. Pushes image URL to DB.

"""

import requests
from config_reader import fetch_config_dict
import json
import re

config_dict = fetch_config_dict()
ACCESS_KEY = config_dict.get("unsplash_access_key", '')

# Preprocess query
def preprocess_query(query):
    """
        1. Convert list to string. 
        2. Handle spaces
        3. Return query str
    """
    query_str = None

    if isinstance(query, list):
        query.append("recipe")
        query_str = '%20'.join(query)
    elif isinstance(query, str):
        if ' ' in query.strip():
            query_str = query.replace(" ", "%20")
        else:
            query_str = query
        query_str = "recipe%20" + query_str 
    return query_str



def search_image(query):
    url = f"https://api.unsplash.com/search/photos?page=1&query={query};client_id={ACCESS_KEY};orientation=landscape;per_page=1"
    response = requests.get(url)
    photo = response.json()
    # print(json.dumps(photo, indent=4))
    fetched_url_list = photo.get("results", [])
    
    final_url = ''
    for item in fetched_url_list:
        url_dict = item.get("urls", {})
        final_url = url_dict.get("full")

    return final_url





def main(query = ''):

    query = preprocess_query(query)
    image_url = search_image(query)
    return image_url


if __name__ == "__main__":
    x = main(query = 'Crock Pot Chicken And Noodles')
    print(x)