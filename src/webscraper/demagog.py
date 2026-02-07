from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

driver = webdriver.Chrome()
driver.get("https://demagog.org.pl/wypowiedzi/")

def get_date():
    try:
        header = driver.find_element(By.CLASS_NAME, "dg-item__header-info")
        spans = header.find_elements(By.TAG_NAME, "span")
        if len(spans) > 0:
            return spans[0].text
    except NoSuchElementException:
        return "Unknown Date"

# Path to JSON file
json_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demagog-data.json")

# List to store all collected data
all_data = []

processed_count = 0
i = 0

while True:
    # Get all elements
    elements = driver.find_elements(By.CLASS_NAME, "medium-6")

    # Process only new elements (skip already processed)
    new_elements = elements[processed_count:]

    for el in new_elements:
        try:
            content = el.find_elements(By.TAG_NAME, "p")
            statements = map(lambda p: p.text, content)
            author = el.find_element(By.CLASS_NAME, "dg-item__person").text
            date = get_date()

            statement_class = next(statements)
            statement_text = next(statements)

            # Create data object
            data_object = {
                "Author": author,
                "Class": statement_class,
                "Statement": statement_text,
                "Date": date
            }

            all_data.append(data_object)

            print(f"Author: {author}")
            print(f"Class: {statement_class}")
            print(f"Statement: {statement_text}")
            print(f"Date: {date}")
            print("\n---")
        except (NoSuchElementException, StopIteration):
            pass

    # Update the count of processed elements
    processed_count = len(elements)

    # Save data to JSON file after processing new elements
    if new_elements:
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
        old_count = processed_count
        for _ in range(10):  # Try for up to 5 seconds
            time.sleep(0.5)
            current_elements = driver.find_elements(By.CLASS_NAME, "medium-6")
            if len(current_elements) > old_count:
                break

        i += 1
        print(f"Loaded batch {i}, total elements: {len(driver.find_elements(By.CLASS_NAME, 'medium-6'))}")

        # Remove the test limit or adjust as needed
        if i > 1:
            break
    except Exception as e:
        print(f"No more Load More button found or error occurred: {type(e).__name__}")
        print("All content loaded.")
        break

driver.quit()
