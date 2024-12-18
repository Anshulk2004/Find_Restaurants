import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import random

class RestaurantScraper:
    def __init__(self, region: str):
        """
        Initialize the scraper with browser configuration
        
        :param region: Geographical area to search for restaurants
        """
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Open browser maximized

        # Initialize WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        
        # Store the region
        self.region = region

    def scrape_restaurant_data(self, max_results=10):
        """
        Scrape restaurant details for the specified region.
        
        :param max_results: Maximum number of restaurant entries to scrape
        :return: A list of dictionaries containing restaurant data
        """
        driver = self.driver
        wait = WebDriverWait(driver, 10)
        restaurant_data = []

        try:
            # Navigate to Google
            driver.get("https://www.google.com")
            time.sleep(2)

            # Search for restaurants in the specified region
            search_query = f"Restaurants in {self.region}"
            search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(3)

            results_scraped = 0
            while results_scraped < max_results:
                # Find restaurant result blocks
                restaurants = driver.find_elements(By.XPATH, "//div[@class='VkpGBb']")
                for restaurant in restaurants:
                    try:
                        # Extract restaurant details
                        name = restaurant.find_element(By.CLASS_NAME, "dbg0pd").text or "N/A"
                        rating = restaurant.find_element(By.CLASS_NAME, "BTtC6e").text or "N/A"
                        details = restaurant.find_element(By.CLASS_NAME, "rllt__details").text or "N/A"
                        
                        # Split details for address and phone
                        details_split = details.split("·")
                        address = details_split[0].strip() if len(details_split) > 0 else "N/A"
                        phone = details_split[-1].strip() if len(details_split) > 1 else "N/A"

                        # Append restaurant details to the list
                        restaurant_data.append({
                            "Name": name,
                            "Rating": rating,
                            "Address": address,
                            "Phone": phone
                        })
                        results_scraped += 1
                    except Exception as e:
                        print(f"Error scraping restaurant: {e}")
                        continue

                    if results_scraped >= max_results:
                        break
                
                # Click the next page button if more results are needed
                try:
                    next_button = driver.find_element(By.ID, "pnnext")
                    next_button.click()
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print("No more pages or error navigating: ", e)
                    break

            return restaurant_data
        finally:
            driver.quit()

    def save_to_csv(self, data, filename="restaurants_data.csv"):
        """
        Save the scraped data to a CSV file.
        
        :param data: List of dictionaries containing restaurant data
        :param filename: Name of the CSV file to save the data
        """
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["Name", "Rating", "Address", "Phone"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Data saved to {filename}")


if __name__ == "__main__":
    # Define the region and number of results to scrape
    region = "Downtown Toronto"
    max_results = 20  # Maximum number of restaurants to scrape

    # Initialize scraper and start scraping
    scraper = RestaurantScraper(region=region)
    print(f"Scraping restaurant data for {region}...")
    restaurant_data = scraper.scrape_restaurant_data(max_results=max_results)

    # Save the scraped data to a CSV file
    scraper.save_to_csv(restaurant_data)
    print(f"Scraped {len(restaurant_data)} restaurants.")
