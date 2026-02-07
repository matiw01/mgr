from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

driver = webdriver.Chrome()
driver.get("https://demagog.org.pl/wypowiedzi/")

# Path to JSON file
json_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demagog-data.json")

# List to store all collected data
all_data = []

# Track URLs we've already processed to avoid duplicates
processed_urls = set()
i = 0

while True:
    # Get all elements
    elements = driver.find_elements(By.CLASS_NAME, "medium-6")

    elements_processed_in_batch = 0
    elements_to_process = []

    # First pass: collect URLs that need processing
    for idx, el in enumerate(elements):
        try:
            link_elements = el.find_elements(By.CSS_SELECTOR, "div.dg-item__title a")
            if not link_elements:
                continue

            link_url = link_elements[0].get_attribute("href")
            if not link_url or link_url.strip() == "" or link_url in processed_urls:
                continue

            elements_to_process.append((idx, link_url))
        except Exception as e:
            continue

    # Second pass: process each URL
    for idx, link_url in elements_to_process:
        try:
            # Re-fetch elements to avoid stale references
            elements = driver.find_elements(By.CLASS_NAME, "medium-6")
            if idx >= len(elements):
                continue

            el = elements[idx]

            # Mark this URL as processed
            processed_urls.add(link_url)

            # Get author and class from the list view
            content = el.find_elements(By.TAG_NAME, "p")
            statements = list(map(lambda p: p.text, content))

            author_elements = el.find_elements(By.CLASS_NAME, "dg-item__person")
            if not author_elements:
                print(f"Skipping element {idx} - no author found")
                continue

            author = author_elements[0].text
            statement_class = statements[0] if len(statements) > 0 else "Unknown"

            # Get date from the list view (before navigating to detail page)
            date = "Unknown Date"
            try:
                header_info = el.find_element(By.CLASS_NAME, "dg-item__header-info")
                date_span = header_info.find_element(By.TAG_NAME, "span")
                date = date_span.text
            except Exception as e:
                print(f"Could not extract date from list view: {type(e).__name__}")
                date = "Unknown Date"

            # Open link in the same window
            driver.get(link_url)

            # Wait for the statement page to load
            time.sleep(1.5)

            # Get the full statement and date from the detail page
            try:
                statement_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "dg-post-quote__statement"))
                )
                statement_p = statement_div.find_element(By.TAG_NAME, "p")
                statement_text = statement_p.text

                # Validate we got actual content
                if not statement_text or statement_text.strip() == "":
                    print(f"Skipping URL {link_url} - empty statement on detail page")
                    driver.back()
                    time.sleep(1)
                    continue

            except Exception as e:
                # If we can't find the statement div, this might be an invalid page
                print(f"Skipping URL {link_url} - could not find statement on detail page: {type(e).__name__}")
                try:
                    driver.back()
                    time.sleep(1)
                except:
                    # Session might be dead, break
                    print("Session lost, stopping...")
                    break
                continue


            # Create data object
            data_object = {
                "Author": author,
                "Class": statement_class,
                "Statement": statement_text,
                "Date": date
            }

            all_data.append(data_object)
            elements_processed_in_batch += 1

            print(f"Author: {author}")
            print(f"Class: {statement_class}")
            print(f"Statement: {statement_text[:100]}...")
            print(f"Date: {date}")
            print("\n---")

            # Go back to the list page
            try:
                driver.back()
                time.sleep(1.5)
            except Exception as e:
                print(f"Could not go back: {type(e).__name__}")
                # Session might be dead
                break

        except Exception as e:
            print(f"Error processing URL {link_url}: {type(e).__name__}")
            # Check if session is still alive
            try:
                current_url = driver.current_url
                # If we're on a detail page, try to go back
                if "wypowiedzi/" in current_url and current_url != "https://demagog.org.pl/wypowiedzi/":
                    try:
                        driver.back()
                        time.sleep(1)
                    except:
                        # Navigate directly to main page
                        driver.get("https://demagog.org.pl/wypowiedzi/")
                        time.sleep(2)
            except:
                # Session is dead, stop processing
                print("Session lost, stopping this batch...")
                break

    # Save data to JSON file after processing elements in this batch
    if elements_processed_in_batch > 0:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(all_data)} records to {json_file_path}")

    # Check if there are more pages to load
    try:
        load_more_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dg-load-more"))
        )

        # Check if button is still visible/enabled
        if not load_more_button.is_displayed():
            print("Load More button is no longer visible. All content loaded.")
            break

        # Scroll to the button to ensure it's visible and not intercepted
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", load_more_button)
        time.sleep(1.5)  # Wait for scroll to complete and any animations

        # Use JavaScript click to avoid interception issues
        driver.execute_script("arguments[0].click();", load_more_button)

        # Wait for new content to load - wait for element count to increase
        old_count = len(elements)
        for _ in range(10):  # Try for up to 5 seconds
            time.sleep(0.5)
            current_elements = driver.find_elements(By.CLASS_NAME, "medium-6")
            if len(current_elements) > old_count:
                break

        i += 1
        print(f"Loaded batch {i}, total elements: {len(driver.find_elements(By.CLASS_NAME, 'medium-6'))}")

    except Exception as e:
        print(f"No more Load More button found or error occurred: {type(e).__name__}")
        print("All content loaded.")
        break

driver.quit()
