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
import argparse

def setup_driver():
    driver_path = "./chromedriver.exe"
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=service, options=options)

def scrape_google_top_places(search_query, max_results=10):
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    results = []
    seen_restaurants = set()

    try:
        
        driver.get("https://www.google.com")
        time.sleep(2)

        search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        print("Searching for Top Places section")
        places_section = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Places')]")))
        print("Top Places section found. Extracting their data....")

        try:
            more_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='More places']")))
            more_button.click()
            time.sleep(3)

        except (NoSuchElementException, TimeoutException):
            print("Could not find 'More Places' button. Proceeding with available results.")
        
        while len(results) < max_results:
            
            place_cards = driver.find_elements(By.XPATH, "//div[@class='VkpGBb']")
            for card in place_cards:
                if len(results) >= max_results:
                    break
                try:
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
                            try:
                                phone_number = driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/local:alt phone'] span.LrzXr").text
                            except:
                                phone_number = "Phone Not Available"
                   
                    try:
                        price_element = driver.find_element(By.XPATH, "//div[@class='MNVeJb lnxHfb']//span[contains(text(), '₹')]")
                        price_per_person = price_element.text
                        price_per_person = re.search(r'(₹[\d,]+(?:–[\d,]+)?)', price_per_person).group(1) if price_per_person else "N/A"
                    except:
                        try:                            
                            price_per_person = driver.find_element(By.CSS_SELECTOR, "div.p3Ci").text                            
                            price_per_person_match = re.search(r'(₹[\d,]+(?:–[\d,]+)?)', price_per_person)
                            price_per_person = price_per_person_match.group(1) if price_per_person_match else "N/A"
                        except:
                            try:
                                price_element = driver.find_element(By.CSS_SELECTOR, "div.MNVeJb div span.GKdNbc")
                                price_per_person = price_element.text.strip() if price_element else "Price Range Not Available"
                            except:
                                price_per_person = "Price Range Not Available"
                    if not price_per_person or price_per_person.strip() == '':
                        price_per_person = "N/A"

                    try:
                        service_options_element = driver.find_element(By.CSS_SELECTOR, "div[data-attrid='kc:/local:business_availability_modes']")
                        service_options = service_options_element.text.replace("Service options: ", "")
                    except:
                        try:
                            service_options_element = driver.find_element(By.CSS_SELECTOR, "div[data-p] span.GKdNbc")
                            service_options = service_options_element.text.strip() if service_options_element else "Service Options Not Available"
                        except:
                            service_options = "Service Options Not Available"

                    details_element = card.find_elements(By.CSS_SELECTOR, "div.rllt__details")
                    try:
                        address_element = driver.find_element(By.XPATH, "//div[@data-attrid='kc:/location/location:address']//span[@class='LrzXr']")
                        location = address_element.text
                    except:
                        if details_element:
                            full_details = details_element[0].text
                            rating_match = re.search(r'(\d+\.\d+)', full_details)
                            rating = rating_match.group(1) if rating_match else "N/A"
                            
                            location_lines = full_details.split('\n')                            
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
                    
                    results.append({
                        "Name": name,
                        "Rating": rating,
                        "Location": location,
                        "Phone Number": phone_number,
                        "Price per Person": price_per_person,
                        "Service Options": service_options
                    })

                except Exception as e:
                    print(f"Error extracting details for one card: {e}")
                    continue

            try:
                more_button = driver.find_element(By.XPATH, "//span[text()='More places']")
                more_button.click()
                time.sleep(3)
            except Exception as e:
                print("No 'More places' button found, stopping...")
                break

        print(f"Successfully scraped {len(results)} places.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
        return results

def to_csv(data, filename="google_top_places.csv"):
    
    sorted_data = sorted(data, key=lambda x: float(x['Rating']) if x['Rating'] != 'N/A' else 0, reverse=True)    
    cleaned_data = []
    for restaurant in sorted_data:
        
        phone = restaurant['Phone Number'].strip() if restaurant['Phone Number'] != 'N/A' else 'Not Available'        
        location = ' '.join(restaurant['Location'].split()) if restaurant['Location'] != 'N/A' else 'Not Available'        
        price = restaurant['Price per Person'] if restaurant['Price per Person'] != 'N/A' else 'Not Available'        
        services = restaurant['Service Options'] if restaurant['Service Options'] != 'N/A' else 'No specific services noted'
        
        cleaned_data.append({
            "Restaurant Name": restaurant['Name'],
            "Rating": restaurant['Rating'],
            "Location": location,
            "Phone Number": phone,
            "Price Range": price,
            "Available Services": services
        })
    
    with open(filename, "w", newline="", encoding="utf-8") as file:
        
        fieldnames = ["Restaurant Name", "Rating", "Location", "Phone Number", "Price Range", "Available Services"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        writer.writerow({
            "Restaurant Name": "Pune's Top Restaurants",
            "Rating": f"Total Restaurants: {len(cleaned_data)}",
            "Location": f"Search Query: {search_query}",
            "Phone Number": "",
            "Price Range": "",
            "Available Services": ""
        })
        writer.writerow({field: field for field in fieldnames})
        writer.writerows(cleaned_data)

# if __name__ == "__main__":
#     search_query = "Top restaurants in Mumbai"
#     max_results = 5

#     print("Starting scrape for Google Top Places in that region!")
#     scraped_data = scrape_google_top_places(search_query, max_results)
#     if scraped_data:
#         to_csv(scraped_data)
#     else:
#         print("No data scraped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape top restaurants from Google Places.")
    parser.add_argument("location", type=str)
    parser.add_argument("--max_results", type=int, default=10)
    parser.add_argument("--output", type=str, default="top_places.csv")
    args = parser.parse_args()
    
    search_query = f"Top restaurants in {args.location}"
    
    print(f"Starting to find restaurants in {args.location} with {args.max_results} results")
    scraped_data = scrape_google_top_places(search_query, args.max_results)

    if scraped_data:
        to_csv(scraped_data, args.output)
    else:
        print("No data scraped.")