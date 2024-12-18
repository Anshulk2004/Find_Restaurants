from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import csv
import re

# Setup ChromeDriver with options
def setup_driver():
    driver_path = "./chromedriver.exe"  # Path to ChromeDriver
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=service, options=options)

# Scrape Google Places data with "More Places" click
def scrape_google_top_places(search_query, max_results=10):
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    results = []
    seen_restaurants = set()

    try:
        # Open Google and perform search
        driver.get("https://www.google.com")
        time.sleep(2)

        search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)

        # Find the "Places" section
        print("Searching for Top Places section...")
        places_section = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Places')]")))
        print("Top Places section found. Extracting data...")

        try:
            more_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='More places']")))
            more_button.click()
            time.sleep(3)  # Wait for more places to load
        except (NoSuchElementException, TimeoutException):
            print("Could not find 'More Places' button. Proceeding with available results.")

        # Click on "More Places" to load more results
        while len(results) < max_results:
            # Wait for results to load
            place_cards = driver.find_elements(By.XPATH, "//div[@class='VkpGBb']")
            
            # Extract restaurants from current page
            for card in place_cards:
                if len(results) >= max_results:
                    break
                try:
                    # Extract Name
                    name = card.find_element(By.CSS_SELECTOR, "div.dbg0pd").text

                    if name in seen_restaurants:
                        continue
                    seen_restaurants.add(name)

                    card.click()
                    time.sleep(3)

                    phone_number = "N/A"
                    price_per_person = "N/A"
                    service_options = "N/A"

                    try:
                        phone_number = driver.find_element(By.CSS_SELECTOR, "span[aria-label^='Call phone number']").text
                    except:
                        try:
                            phone_number = driver.find_element(By.CSS_SELECTOR, "div.p3Ci").text
                        except:
                            pass
                    # Extract Price per Person
                    try:
                        # First try the specific XPath for price extraction
                        price_element = driver.find_element(By.XPATH, "//div[@class='MNVeJb lnxHfb']//span[contains(text(), '₹')]")
                        price_per_person = price_element.text
                    except:
                        try:
                            # Fallback to finding by CSS selector
                            price_per_person = driver.find_element(By.CSS_SELECTOR, "div.p3Ci").text
                            # Extract the price range
                            price_per_person_match = re.search(r'(₹\d+–\d+)', price_per_person)
                            price_per_person = price_per_person_match.group(1) if price_per_person_match else "N/A"
                        except:
                            pass
                    
                    if not price_per_person or price_per_person.strip() == '':
                        price_per_person = "N/A"

                    # Extract Service Options
                    try:
                        service_options_element = driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/local:business_availability_modes']")
                        service_options = service_options_element.text.replace("Service options: ", "")
                    except:
                        pass

                    details_element = card.find_elements(By.CSS_SELECTOR, "div.rllt__details")
                    
                    # Try new address extraction method first
                    try:
                        address_element = driver.find_element(By.XPATH, "//div[@data-attrid='kc:/location/location:address']//span[@class='LrzXr']")
                        location = address_element.text
                    except:
                        # Fallback to previous method
                        if details_element:
                            full_details = details_element[0].text
                            
                            # Extract Rating
                            rating_match = re.search(r'(\d+\.\d+)', full_details)
                            rating = rating_match.group(1) if rating_match else "N/A"
                            
                            # Extract Location
                            location_lines = full_details.split('\n')
                            # Try to find a line that looks like an address
                            location_candidates = [
                                line for line in location_lines
                                if any(x in line for x in ['Street', 'Road', 'Block','Lane', 'Area', 'Colony', 'Building','Floor','Rd','Level','Ln','St','No.'])
                            ]
                            location = ", ".join(location_candidates) if location_candidates else "N/A"
                        else:
                            location = "N/A"
                    
                    if 'rating' not in locals():
                        if details_element:
                            full_details = details_element[0].text
                            rating_match = re.search(r'(\d+\.\d+)', full_details)
                            rating = rating_match.group(1) if rating_match else "N/A"
                        else:
                            rating = "N/A"

                    # Append restaurant data
                    results.append({
                        "Name": name,
                        "Rating": rating,
                        "Location": location,
                        "Phone Number": phone_number,
                        "Price per Person": price_per_person,
                        "Service Options": service_options
                    })

                    # driver.back()
                    # time.sleep(2)

                except Exception as e:
                    print(f"Error extracting details for one card: {e}")
                    continue

            # Click "More Places" to load additional results
            try:
                more_button = driver.find_element(By.XPATH, "//span[text()='More places']")
                more_button.click()
                time.sleep(3)  # Wait for more places to load
            except Exception as e:
                print("No 'More places' button found, stopping...")
                break

        print(f"Successfully scraped {len(results)} places.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
        return results

def save_to_csv(data, filename="google_top_places.csv"):
    # Sort results by rating in descending order
    sorted_data = sorted(data, key=lambda x: float(x['Rating']) if x['Rating'] != 'N/A' else 0, reverse=True)
    
    # Clean and format data before writing
    cleaned_data = []
    for restaurant in sorted_data:
        # Clean up phone number (remove any extra spaces)
        phone = restaurant['Phone Number'].strip() if restaurant['Phone Number'] != 'N/A' else 'Not Available'
        
        # Clean up location (remove multiple spaces, trim)
        location = ' '.join(restaurant['Location'].split()) if restaurant['Location'] != 'N/A' else 'Not Available'
        
        # Format price per person
        price = restaurant['Price per Person'] if restaurant['Price per Person'] != 'N/A' else 'Not Available'
        
        # Format service options
        services = restaurant['Service Options'] if restaurant['Service Options'] != 'N/A' else 'No specific services noted'
        
        cleaned_data.append({
            "Restaurant Name": restaurant['Name'],
            "Rating": restaurant['Rating'],
            "Location": location,
            "Phone Number": phone,
            "Price Range": price,
            "Available Services": services
        })
    
    # Write to CSV
    with open(filename, "w", newline="", encoding="utf-8") as file:
        # Use more descriptive field names
        fieldnames = ["Restaurant Name", "Rating", "Location", "Phone Number", "Price Range", "Available Services"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Write a header with some additional information
        writer.writerow({
            "Restaurant Name": "Pune's Top Restaurants",
            "Rating": f"Total Restaurants: {len(cleaned_data)}",
            "Location": f"Search Query: {search_query}",
            "Phone Number": f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "Price Range": "",
            "Available Services": ""
        })
        writer.writerow({field: field for field in fieldnames})  # Column headers
        
        # Write the actual data
        writer.writerows(cleaned_data)
    
    print(f"Cleaned and organized data saved to {filename}")
    
    # Optional: Print summary to console
    print("\n--- Restaurant Scrape Summary ---")
    print(f"Total Restaurants Found: {len(cleaned_data)}")
    top_5 = cleaned_data[:5]
    print("\nTop 5 Restaurants by Rating:")
    for idx, rest in enumerate(top_5, 1):
        print(f"{idx}. {rest['Restaurant Name']} (Rating: {rest['Rating']})")

# Modify the main function to pass search query
if __name__ == "__main__":
    search_query = "Top restaurants in Pune"  # Modify query as needed
    max_results = 20  # Get top 20 places

    print("Starting scrape for Google Top Places...")
    scraped_data = scrape_google_top_places(search_query, max_results)

    if scraped_data:
        save_to_csv(scraped_data)
    else:
        print("No data scraped.")