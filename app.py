import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import re

def setup_driver():
    service = Service("./chromedriver.exe")
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

        st.write("Searching for Top Places section...")
        places_section = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Places')]")))
        st.write("Top Places section found. Extracting data...")

        progress_bar = st.progress(0)
        progress_text = st.empty()

        try:
            more_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='More places']")))
            more_button.click()
            time.sleep(3)
        except (NoSuchElementException, TimeoutException):
            st.warning("Could not find 'More Places' button. Proceeding with available results.")

        
        while len(results) < max_results:
            place_cards = driver.find_elements(By.XPATH, "//div[@class='VkpGBb']")            
            for card in place_cards:
                if len(results) >= max_results:
                    progress_bar.progress(1.0)
                    progress_text.write(f"Progress: {max_results}/{max_results} restaurants")
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
                    
                    current_progress = min(len(results) / max_results, 1.0)
                    progress_bar.progress(current_progress)
                    progress_text.write(f"Progress: {len(results)}/{max_results} restaurants")                   
                    results.append({
                        "Name": name,
                        "Rating": rating,
                        "Location": location,
                        "Phone Number": phone_number,
                        "Price per Person": price_per_person,
                        "Service Options": service_options
                    })

                except Exception as e:
                    st.warning(f"Error extracting details for one restaurant: {str(e)}")
                    continue

            try:
                more_button = driver.find_element(By.XPATH, "//span[text()='More places']")
                more_button.click()
                time.sleep(3)
            except Exception as e:
                st.info("No more places to load. Finalizing results...")
                progress_bar.progress(1.0)
                progress_text.write(f"Progress: {len(results)}/{max_results} restaurants")
                break

        st.success(f"Successfully scraped {len(results)} places.")
    except Exception as e:
        st.error(f"Error during scraping: {str(e)}")
    finally:
        driver.quit()
        return results

def main():
    st.set_page_config(page_title="Restaurant Finder", layout="wide")
    
    st.title("🍽️ Top Restaurants At Your Region")
    st.markdown("""
    Discover the best restaurants in your area! Enter a location and get detailed information about top-rated restaurants.
    """)    
    with st.form("restaurant_search_form"):
        
        col1, col2 = st.columns(2)
        
        with col1:
            
            location = st.text_input("Enter City/Region", 
                                   placeholder="e.g., Mumbai, Delhi, Bangalore")        
        with col2:            
            max_results = st.slider("Number of Restaurants to Show", 
                                  min_value=1, 
                                  max_value=50, 
                                  value=3, 
                                  step=3)        
        search_button = st.form_submit_button("Search Restaurants 🔍")    
    
    if search_button and location:
        try:            
            with st.spinner(f'Searching for top restaurants in {location}...'):                
                search_query = f"Top restaurants in {location}"                
                results = scrape_google_top_places(search_query, max_results)
                
                if results:                    
                    df = pd.DataFrame(results)
                    df.index = range(1, len(df) + 1)
                    df.columns = [
                        "Restaurant Name",
                        "Rating",
                        "Location",
                        "Phone Number",
                        "Price Range",
                        "Available Services"
                    ]                    
                    st.success(f"Found {len(results)} restaurants in {location}!")                    
                    st.markdown("### 📋 Restaurant Details")
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )                    
                    csv = df.to_csv(index=True).encode('utf-8')
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name=f"restaurants_{location.lower().replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("No restaurants found. Please try a different location.")
                    
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.warning("Please try again or try a different location.")    
    
    st.markdown("""
    ---
    ℹ️ *This app scrapes real-time data from Google Places. Results may vary based on availability and current Google Places data.*
    """)

if __name__ == "__main__":
    main()