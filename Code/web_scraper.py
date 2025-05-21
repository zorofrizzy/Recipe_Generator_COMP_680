from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback

# Step 1: Configure Firefox WebDriver
def setup_driver():
    firefox_options = Options()
    firefox_options.headless = False  # Run in headless mode (no GUI)
    # Path to Firefox binary
    firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'  # Replace with the actual path to firefox.exe or firefox binary
    firefox_options.binary_location = firefox_binary_path

    service = Service('geckodriver.exe')  # Replace with the path to your geckodriver
    driver = webdriver.Firefox(service=service, options=firefox_options)
    return driver

# Step 2: Scrape the website
def scrape_main_dish_recipes(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 12)
    print(f"Navigating to URL: {url}")
    driver.get(url)

    #wait = WebDriverWait(driver, 20)  # Increase timeout to 20 seconds
    print("Waiting for teaser links to load...")

    teasers = []

    try:
        # Wait for the teaser links to load
        teaser_links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.Teaser__kicker-link')))
        print(f"Found {len(teaser_links)} teaser links.")

        for i, link in enumerate(teaser_links):
            teaser_url = link.get_attribute('data-gtm-teaser-url')
            image_url = link.get_attribute('data-gtm-image-url')

            print(f"Processing teaser {i + 1}:")
            print(f"Teaser URL: {teaser_url}")
            print(f"Image URL: {image_url}")

            teasers.append({
                'teaser_url': teaser_url,
                'image_url': image_url
            })

        print(f"Scraped {len(teasers)} teaser links successfully.")
        return teasers

    except Exception as e:
        print("An error occurred:")
        print(e)
        traceback.print_exc()
        return []

    return recipes

# Step 3: Save the data (optional)
def save_to_file(data, filename='recipes.txt'):
    with open(filename, 'w', encoding='utf-8') as file:
        for recipe in data:
            file.write(f"Title: {recipe['title']}\n")
            file.write(f"Description: {recipe['description']}\n")
            file.write(f"Link: {recipe['link']}\n")
            file.write("-" * 50 + "\n")

# Main function
if __name__ == "__main__":
    url = "https://www.thekitchn.com/collection/main-dish"
    driver = setup_driver()

    try:
        recipes = scrape_main_dish_recipes(driver, url)
        save_to_file(recipes)
    finally:
        driver.quit()