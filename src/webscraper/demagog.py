"""
Web scraper for demagog.org.pl/wypowiedzi/
Scrapes political statements filtered by classification:
  Prawda, Częściowa prawda, Manipulacja, Fałsz
Clicks "Więcej wypowiedzi" to load more results until the page
stops responding within 15 seconds.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
)
import time
import json
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://demagog.org.pl/wypowiedzi/"
PAGE_LOAD_TIMEOUT = 15          # seconds – max wait for "Więcej wypowiedzi"
DETAIL_PAGE_TIMEOUT = 10        # seconds – max wait for detail page elements
CLASSES_TO_SCRAPE = ["Prawda", "Częściowa prawda", "Manipulacja", "Fałsz"]

JSON_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "demagog-data.json"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_existing_data(path: str) -> list[dict]:
    """Load previously scraped data from JSON file (if exists)."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[INFO] Loaded {len(data)} existing records from {path}")
            return data
        except Exception as exc:
            print(f"[WARN] Could not load existing data ({type(exc).__name__}). Starting fresh.")
    return []


def save_data(path: str, data: list[dict]) -> None:
    """Persist data to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved {len(data)} records to {path}")


def init_driver() -> webdriver.Chrome:
    """Create and return a Chrome WebDriver instance."""
    options = webdriver.ChromeOptions()
    # Uncomment the next line to run headless:
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


# ---------------------------------------------------------------------------
# Filter interaction
# ---------------------------------------------------------------------------

def apply_class_filter(driver: webdriver.Chrome, class_name: str) -> bool:
    """
    Apply the "Ocena wypowiedzi" filter for the given *class_name*.
    Returns True on success, False otherwise.
    """
    driver.get(BASE_URL)
    time.sleep(3)  # let the page fully render

    try:
        # --- 1. Click the "Ocena wypowiedzi" collapsible header to open it ---
        rating_header = None

        # Try various selectors for the filter header
        filter_headers = driver.find_elements(
            By.CSS_SELECTOR, "button.dg-filter__btn, .dg-filter__header, .dg-filter__title"
        )
        for fh in filter_headers:
            try:
                if "Ocena wypowiedzi" in fh.text:
                    rating_header = fh
                    break
            except StaleElementReferenceException:
                continue

        # Fallback: XPath search for any element containing that text
        if rating_header is None:
            try:
                rating_header = driver.find_element(
                    By.XPATH, "//*[contains(text(), 'Ocena wypowiedzi')]"
                )
            except Exception:
                pass

        if rating_header is None:
            print("[ERROR] Could not find 'Ocena wypowiedzi' filter header.")
            return False

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'instant', block:'center'});",
            rating_header,
        )
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", rating_header)
        time.sleep(1)

        # --- 2. Select the desired class checkbox/radio ---
        class_option = None

        # Try labels
        labels = driver.find_elements(By.CSS_SELECTOR, "label")
        for label in labels:
            try:
                if label.text.strip() == class_name:
                    class_option = label
                    break
            except StaleElementReferenceException:
                continue

        # Fallback: XPath with normalize-space
        if class_option is None:
            try:
                class_option = driver.find_element(
                    By.XPATH,
                    f"//label[normalize-space(text())='{class_name}']"
                )
            except Exception:
                pass

        # Another fallback: partial match within filter container
        if class_option is None:
            try:
                class_option = driver.find_element(
                    By.XPATH,
                    f"//*[contains(@class,'dg-filter')]//label[contains(.,'{class_name}')]"
                )
            except Exception:
                pass

        if class_option is None:
            print(f"[ERROR] Could not find filter option for class '{class_name}'.")
            return False

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'instant', block:'center'});",
            class_option,
        )
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", class_option)
        time.sleep(0.5)

        # --- 3. Click "Pokaż wyniki" button ---
        show_results_btn = None

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                txt = btn.text.strip()
                if "pokaż wyniki" in txt.lower():
                    show_results_btn = btn
                    break
            except StaleElementReferenceException:
                continue

        # Fallback: XPath
        if show_results_btn is None:
            try:
                show_results_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZĄĆĘŁŃÓŚŹŻ', 'abcdefghijklmnopqrstuvwxyząćęłńóśźż'), 'pokaż wyniki')]"
                )
            except Exception:
                pass

        # Fallback: input[type=submit]
        if show_results_btn is None:
            try:
                show_results_btn = driver.find_element(
                    By.XPATH,
                    "//input[contains(@value, 'Pokaż wyniki') or contains(@value, 'pokaż wyniki')]"
                )
            except Exception:
                pass

        # Fallback: anchor with text
        if show_results_btn is None:
            try:
                show_results_btn = driver.find_element(
                    By.XPATH,
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZĄĆĘŁŃÓŚŹŻ', 'abcdefghijklmnopqrstuvwxyząćęłńóśźż'), 'pokaż wyniki')]"
                )
            except Exception:
                pass

        if show_results_btn is None:
            print("[WARN] Could not find 'Pokaż wyniki' button – trying form submit.")
            try:
                form = driver.find_element(By.CSS_SELECTOR, "form.dg-filter__form, form")
                form.submit()
            except Exception:
                print("[ERROR] Could not submit filter form either.")
                return False
        else:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'instant', block:'center'});",
                show_results_btn,
            )
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", show_results_btn)

        # Wait for filtered results to load
        time.sleep(4)
        print(f"[INFO] Filter applied for class: {class_name}")
        return True

    except Exception as exc:
        print(f"[ERROR] Failed to apply filter for '{class_name}': {type(exc).__name__}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Loading more results
# ---------------------------------------------------------------------------

def click_load_more(driver: webdriver.Chrome, current_count: int) -> int:
    """
    Click "Więcej wypowiedzi" and wait for new elements to appear.
    Returns the new element count, or -1 if loading failed / timed out.
    """
    try:
        load_more_btn = driver.find_element(
            By.CSS_SELECTOR, ".dg-load-more a, .dg-load-more button, .dg-load-more"
        )
    except Exception:
        print("[INFO] 'Więcej wypowiedzi' button not found – all content loaded.")
        return -1

    if not load_more_btn.is_displayed():
        print("[INFO] 'Więcej wypowiedzi' button is hidden – all content loaded.")
        return -1

    # Scroll to and click
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior:'instant', block:'center'});",
        load_more_btn,
    )
    time.sleep(0.5)

    start_time = time.time()
    driver.execute_script("arguments[0].click();", load_more_btn)

    # Wait until new elements appear or timeout (15 s)
    deadline = start_time + PAGE_LOAD_TIMEOUT
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            new_elements = driver.find_elements(By.CSS_SELECTOR, ".medium-6")
            if len(new_elements) > current_count:
                elapsed = time.time() - start_time
                print(
                    f"[INFO] New elements loaded: {len(new_elements)} "
                    f"(was {current_count}) – {elapsed:.1f}s"
                )
                return len(new_elements)
        except WebDriverException:
            pass

    elapsed = time.time() - start_time
    print(
        f"[WARN] Timeout ({elapsed:.1f}s) waiting for new elements "
        f"after 'Więcej wypowiedzi'."
    )
    return -1


# ---------------------------------------------------------------------------
# Scraping detail pages
# ---------------------------------------------------------------------------

def scrape_visible_statements(
    driver: webdriver.Chrome,
    processed_statements: set,
    class_name: str,
    start_idx: int = 0,
) -> tuple:
    """
    Scrape statement elements on the listing page starting from *start_idx*.
    Opens each detail page in a new tab, extracts the full statement text.
    Returns (new_records, next_start_idx).
    """
    elements = driver.find_elements(By.CSS_SELECTOR, ".medium-6")
    new_records = []
    idx = start_idx

    while idx < len(elements):
        el = elements[idx]
        idx += 1

        try:
            link_els = el.find_elements(By.CSS_SELECTOR, "div.dg-item__title a")
            if not link_els:
                continue
            link_url = link_els[0].get_attribute("href")
            if not link_url or not link_url.strip():
                continue

            # Author
            author_els = el.find_elements(By.CSS_SELECTOR, ".dg-item__person")
            author = author_els[0].text.strip() if author_els else "Unknown"

            # Date from listing
            date = "Unknown"
            try:
                header_info = el.find_element(By.CSS_SELECTOR, ".dg-item__header-info")
                date_span = header_info.find_element(By.TAG_NAME, "span")
                date = date_span.text.strip()
            except Exception:
                pass

            # Open detail page in a new tab
            main_window = driver.current_window_handle
            driver.execute_script("window.open(arguments[0], '_blank');", link_url)
            driver.switch_to.window(driver.window_handles[-1])

            try:
                statement_div = WebDriverWait(driver, DETAIL_PAGE_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".dg-post-quote__statement")
                    )
                )
                statement_p = statement_div.find_element(By.TAG_NAME, "p")
                statement_text = statement_p.text.strip()

                if not statement_text:
                    raise ValueError("Empty statement")

                if statement_text not in processed_statements:
                    record = {
                        "Author": author,
                        "Class": class_name,
                        "Statement": statement_text,
                        "Date": date,
                    }
                    new_records.append(record)
                    processed_statements.add(statement_text)
                    print(
                        f"  [{class_name}] {author} | {date} "
                        f"| {statement_text[:80]}..."
                    )
                else:
                    print(f"  [SKIP] Duplicate: {statement_text[:60]}...")

            except Exception as exc:
                print(
                    f"  [WARN] Could not scrape detail page "
                    f"{link_url}: {type(exc).__name__}"
                )

            finally:
                # Close detail tab, return to listing
                try:
                    driver.close()
                except Exception:
                    pass
                driver.switch_to.window(main_window)
                time.sleep(0.3)

            # Re-fetch elements (DOM may have changed)
            elements = driver.find_elements(By.CSS_SELECTOR, ".medium-6")

        except StaleElementReferenceException:
            elements = driver.find_elements(By.CSS_SELECTOR, ".medium-6")
            continue
        except Exception as exc:
            print(f"  [ERROR] Element {idx}: {type(exc).__name__}: {exc}")
            try:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
            except Exception:
                pass
            continue

    return new_records, idx


# ---------------------------------------------------------------------------
# Main scraping loop for a single class
# ---------------------------------------------------------------------------

def scrape_class(
    driver: webdriver.Chrome,
    class_name: str,
    all_data: list,
    processed_statements: set,
) -> None:
    """Scrape all available statements for a given classification class."""
    print(f"\n{'='*60}")
    print(f"  Scraping class: {class_name}")
    print(f"{'='*60}")

    if not apply_class_filter(driver, class_name):
        print(f"[ERROR] Skipping class '{class_name}' – could not apply filter.")
        return

    next_idx = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n--- Batch {batch_num} for '{class_name}' ---")

        # Scrape currently visible (new) elements
        new_records, next_idx = scrape_visible_statements(
            driver, processed_statements, class_name, start_idx=next_idx
        )

        if new_records:
            all_data.extend(new_records)
            save_data(JSON_FILE_PATH, all_data)
            print(f"[INFO] +{len(new_records)} new records (total: {len(all_data)})")

        # Try to load more
        current_count = len(driver.find_elements(By.CSS_SELECTOR, ".medium-6"))
        new_count = click_load_more(driver, current_count)

        if new_count == -1:
            print(f"[INFO] No more results to load for class '{class_name}'.")
            break

    print(f"[INFO] Finished class '{class_name}'. Total records now: {len(all_data)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    all_data = load_existing_data(JSON_FILE_PATH)
    processed_statements = {
        item["Statement"] for item in all_data if "Statement" in item
    }

    driver = init_driver()

    try:
        for cls in CLASSES_TO_SCRAPE:
            scrape_class(driver, cls, all_data, processed_statements)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user. Saving collected data...")
        save_data(JSON_FILE_PATH, all_data)
    except Exception as exc:
        print(f"\n[FATAL] {type(exc).__name__}: {exc}")
        save_data(JSON_FILE_PATH, all_data)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n[DONE] Total records: {len(all_data)}")


if __name__ == "__main__":
    main()
