"""
Deezer AI Music Scraper
========================
Scrapes Deezer album pages to detect AI-generated content flags.

SETUP:
  pip3 install selenium requests pandas undetected-chromedriver

BEFORE RUNNING:
  Fill in your Deezer credentials below.

Then run:
  python3 deezer_scraper_variety.py
"""

import time
import random
import requests
import pandas as pd
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


# ─────────────────────────────────────────────
# !! FILL THESE IN BEFORE RUNNING !!
# ─────────────────────────────────────────────

DEEZER_EMAIL = "pelinumur05@gmail.com"
DEEZER_PASSWORD = "Pelinumur208"


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

OUTPUT_FILE = "deezer_ai_artists_variety10.csv"
MAX_ALBUMS = 2000
API_RESULTS_PER_QUERY = 100

# Broader genre coverage
SEARCH_QUERIES = [
    "new release 2025",
    "new release 2024",

    "pop 2025",
    "indie pop 2025",
    "electropop 2025",
    "dance pop 2025",

    "rock 2025",
    "indie rock 2025",
    "alternative rock 2025",
    "punk 2025",
    "metal 2025",

    "hip hop 2025",
    "rap 2025",
    "trap 2025",
    "drill 2025",

    "r&b 2025",
    "soul 2025",
    "neo soul 2025",

    "electronic 2025",
    "house 2025",
    "techno 2025",
    "ambient 2025",
    "lo-fi 2025",
    "drum and bass 2025",

    "jazz 2025",
    "blues 2025",
    "classical 2025",
    "opera 2025",

    "folk 2025",
    "country 2025",
    "americana 2025",

    "latin 2025",
    "reggaeton 2025",
    "afrobeats 2025",
    "reggae 2025",

    "world music 2025",
    "soundtrack 2025",
    "experimental 2025",
]

DELAY_BETWEEN_PAGES = (4, 8)


# ─────────────────────────────────────────────
# STEP 1: Collect album IDs via Deezer API
# ─────────────────────────────────────────────

def search_deezer_albums(query: str, limit: int = 50) -> list:
    url = "https://api.deezer.com/search/album"
    params = {"q": query, "limit": limit}

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [API ERROR] '{query}': {e}")
        return []

    albums = []
    for item in data.get("data", []):
        albums.append({
            "album_id": item["id"],
            "album_title": item["title"],
            "artist_id": item["artist"]["id"],
            "artist_name": item["artist"]["name"],
            "album_url": f"https://www.deezer.com/en/album/{item['id']}",
            "release_date": item.get("release_date", ""),
            "search_query": query,
        })

    return albums


def collect_album_ids(queries: list, max_albums: int) -> list:
    """
    Collect albums while enforcing:
    - unique album IDs
    - max 1 album per artist
    - shuffled query order
    - shuffled results within each query
    - shuffled final selection
    """
    seen_album_ids = set()
    seen_artist_ids = set()
    all_albums = []

    shuffled_queries = queries[:]
    random.shuffle(shuffled_queries)

    print("[API] Query order randomized for more variety.")

    for query in shuffled_queries:
        print(f"[API] Searching: '{query}'...")
        results = search_deezer_albums(query, limit=API_RESULTS_PER_QUERY)

        # Shuffle the results returned for this query
        random.shuffle(results)

        for album in results:
            album_id = album["album_id"]
            artist_id = album["artist_id"]

            if album_id in seen_album_ids:
                continue

            if artist_id in seen_artist_ids:
                continue

            seen_album_ids.add(album_id)
            seen_artist_ids.add(artist_id)
            all_albums.append(album)

            if len(all_albums) >= max_albums:
                break

        time.sleep(1)

        if len(all_albums) >= max_albums:
            break

    # Shuffle the final selected albums so scraping order also changes
    random.shuffle(all_albums)

    print(f"[API] Collected {len(all_albums)} unique albums from unique artists.\n")
    return all_albums[:max_albums]


# ─────────────────────────────────────────────
# STEP 2: Browser setup
# ─────────────────────────────────────────────

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


# ─────────────────────────────────────────────
# Helper: safe click
# ─────────────────────────────────────────────

def safe_click(driver, element) -> bool:
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────
# STEP 3: Cookie banner dismissal
# ─────────────────────────────────────────────

def dismiss_cookie_banner(driver):
    cookie_button_selectors = [
        "#didomi-notice-agree-button",
        "#didomi-notice-decline-button",
        "button[aria-label='Agree and close']",
        "button[aria-label='Disagree and close']",
        '[data-testid="didomi-notice-agree-button"]',
        '[data-testid="cookie-accept"]',
        '[data-testid="cookie-decline"]',
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'decline')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'refuse')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close')]",
    ]

    for selector in cookie_button_selectors:
        try:
            if selector.startswith("//"):
                btn = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
            else:
                btn = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )

            if safe_click(driver, btn):
                print("         [COOKIE] Banner dismissed.")
                time.sleep(1)
                return True

        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
            continue
        except Exception:
            continue

    js_ids = [
        "didomi-notice-agree-button",
        "didomi-notice-decline-button",
    ]

    for el_id in js_ids:
        try:
            clicked = driver.execute_script("""
                const el = document.getElementById(arguments[0]);
                if (el) {
                    el.click();
                    return true;
                }
                return false;
            """, el_id)

            if clicked:
                print("         [COOKIE] Banner dismissed via JS.")
                time.sleep(1)
                return True

        except Exception:
            continue

    print("         [COOKIE] No banner found.")
    return False


# ─────────────────────────────────────────────
# STEP 4: Login to Deezer
# ─────────────────────────────────────────────

def login_to_deezer(driver, email: str, password: str) -> bool:
    print("[LOGIN] Navigating to Deezer login page...")
    driver.get("https://www.deezer.com/en/login")
    time.sleep(4)

    dismissed = dismiss_cookie_banner(driver)
    print(f"[LOGIN] Cookie dismissed: {dismissed}")
    time.sleep(1)

    try:
        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'input[type="email"], input[name="email"], #login_mail'
            ))
        )

        email_input.clear()
        for char in email:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))

        time.sleep(0.5)

        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'input[type="password"], input[name="password"], #login_password'
            ))
        )

        password_input.clear()
        for char in password:
            password_input.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))

        time.sleep(0.5)

        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'button[type="submit"], input[type="submit"], '
                'button.btn-login, [data-testid="login-button"]'
            ))
        )

        clicked = safe_click(driver, submit_btn)
        if not clicked:
            driver.save_screenshot("login_click_failed.png")
            print("[LOGIN] Could not click submit button. See: login_click_failed.png")
            return False

        print("[LOGIN] Credentials submitted, waiting for redirect...")
        time.sleep(8)

        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()

        if "login" not in current_url:
            print("[LOGIN] Login successful!")
            return True

        if "logout" in page_source or "my music" in page_source or "favorites" in page_source:
            print("[LOGIN] Login appears successful!")
            return True

        driver.save_screenshot("login_failed_screenshot.png")
        print("[LOGIN] Login may have failed. See: login_failed_screenshot.png")
        return False

    except TimeoutException:
        driver.save_screenshot("login_timeout_screenshot.png")
        print("[LOGIN] Timed out. See: login_timeout_screenshot.png")
        return False

    except NoSuchElementException as e:
        driver.save_screenshot("login_error_screenshot.png")
        print(f"[LOGIN] Element not found: {e}")
        return False

    except Exception as e:
        driver.save_screenshot("login_unknown_error_screenshot.png")
        print(f"[LOGIN] Unexpected error: {e}")
        return False


# ─────────────────────────────────────────────
# STEP 5: Wait for album page to load
# ─────────────────────────────────────────────

def wait_for_page_ready(driver, timeout: int = 20) -> bool:
    candidates = [
        (By.ID, "page_naboo_album"),
        (By.CSS_SELECTOR, '[data-testid="masthead"]'),
        (By.CSS_SELECTOR, '[data-testid="is-fully-fetched"]'),
        (By.CSS_SELECTOR, '[data-testid="ai-generated-alert"]'),
        (By.ID, "page_content"),
        (By.TAG_NAME, "main"),
        (By.CSS_SELECTOR, "h1"),
        (By.CSS_SELECTOR, "h2.chakra-heading"),
    ]

    for by, sel in candidates:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            return True
        except TimeoutException:
            continue

    return False


# ─────────────────────────────────────────────
# STEP 6: Check one album page for the AI flag
# ─────────────────────────────────────────────

def check_album_for_ai_flag(driver, album_url: str, album_index: int) -> dict:
    result = {"ai_flagged": False, "flag_text": "", "error": ""}

    try:
        driver.get(album_url)

        page_loaded = wait_for_page_ready(driver, timeout=20)
        if not page_loaded:
            driver.save_screenshot(f"timeout_screenshot_{album_index}.png")
            result["error"] = f"Page did not load — see timeout_screenshot_{album_index}.png"
            return result

        time.sleep(3)

        if album_index < 3:
            driver.save_screenshot(f"debug_screenshot_{album_index}.png")
            print(f"         [DEBUG] Screenshot saved: debug_screenshot_{album_index}.png")

        try:
            ai_el = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="ai-generated-alert"]'
            )
            result["ai_flagged"] = True

            try:
                heading = ai_el.find_element(By.CLASS_NAME, "chakra-heading")
                body = ai_el.find_element(By.CLASS_NAME, "chakra-text")
                result["flag_text"] = f"{heading.text} | {body.text}"
            except NoSuchElementException:
                result["flag_text"] = ai_el.text.strip()

        except NoSuchElementException:
            result["ai_flagged"] = False

    except Exception as e:
        try:
            driver.save_screenshot(f"error_screenshot_{album_index}.png")
        except Exception:
            pass
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────
# STEP 7: Extra data from Deezer API
# ─────────────────────────────────────────────

def get_album_details_from_api(album_id: int) -> dict:
    details = {
        "nb_tracks": None,
        "genre": "",
        "release_date": "",
        "fans": None,
    }

    try:
        data = requests.get(
            f"https://api.deezer.com/album/{album_id}",
            timeout=10
        ).json()

        details["nb_tracks"] = data.get("nb_tracks")
        details["release_date"] = data.get("release_date", "")
        details["fans"] = data.get("fans")

        if data.get("genres") and data["genres"].get("data"):
            details["genre"] = ", ".join(
                g.get("name", "") for g in data["genres"]["data"] if g.get("name")
            )

    except Exception:
        pass

    return details


def get_artist_details_from_api(artist_id: int) -> dict:
    details = {"artist_nb_albums": None, "artist_fans": None}

    try:
        data = requests.get(
            f"https://api.deezer.com/artist/{artist_id}",
            timeout=10
        ).json()

        details["artist_nb_albums"] = data.get("nb_album")
        details["artist_fans"] = data.get("nb_fan")

    except Exception:
        pass

    return details


# ─────────────────────────────────────────────
# STEP 8: Main loop
# ─────────────────────────────────────────────

def run_scraper():
    print("=" * 60)
    print("  Deezer AI Music Scraper")
    print("=" * 60)

    if DEEZER_EMAIL == "your@email.com" or DEEZER_PASSWORD == "yourpassword":
        print("\nPlease fill in DEEZER_EMAIL and DEEZER_PASSWORD at the top of the script.\n")
        return None

    albums = collect_album_ids(SEARCH_QUERIES, MAX_ALBUMS)

    print("[BROWSER] Starting Chrome...\n")
    driver = create_driver()

    try:
        login_ok = login_to_deezer(driver, DEEZER_EMAIL, DEEZER_PASSWORD)
        if not login_ok:
            print("\nLogin failed. Check the screenshot files for details.")
            return None

        time.sleep(3)
        print("\n[BROWSER] Logged in. Starting album scraping...\n")

        results = []

        for i, album in enumerate(albums):
            album_id = album["album_id"]
            album_url = album["album_url"]
            album_title = album["album_title"]
            artist_name = album["artist_name"]

            print(f"[{i+1}/{len(albums)}] {artist_name} — {album_title}")
            print(f"         {album_url}")

            flag_result = check_album_for_ai_flag(driver, album_url, i)
            album_details = get_album_details_from_api(album_id)
            artist_details = get_artist_details_from_api(album["artist_id"])

            if flag_result["error"]:
                print(f"         [ERROR] {flag_result['error']}")
            elif flag_result["ai_flagged"]:
                print(f"         [AI FLAG] {flag_result['flag_text']}")
            else:
                print("         [OK] No AI flag")

            results.append({
                "artist_id": album["artist_id"],
                "artist_name": artist_name,
                "artist_nb_albums": artist_details["artist_nb_albums"],
                "artist_fans_deezer": artist_details["artist_fans"],
                "album_id": album_id,
                "album_title": album_title,
                "album_url": album_url,
                "release_date": album_details.get("release_date") or album.get("release_date", ""),
                "nb_tracks": album_details["nb_tracks"],
                "genre": album_details["genre"],
                "deezer_fans": album_details["fans"],
                "ai_flagged": flag_result["ai_flagged"],
                "ai_flag_text": flag_result["flag_text"],
                "scrape_error": flag_result["error"],
                "search_query": album.get("search_query", ""),
            })

            if (i + 1) % 10 == 0:
                pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
                print(f"\n[SAVED] {OUTPUT_FILE}\n")

            time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))

    finally:
        driver.quit()
        print("\n[BROWSER] Closed.")

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)

    total = len(df)
    ai_count = int(df["ai_flagged"].sum())
    errors = int(df["scrape_error"].astype(bool).sum())

    print("\n" + "=" * 60)
    print("  SCRAPING COMPLETE")
    print("=" * 60)
    print(f"  Total albums  : {total}")
    print(f"  AI-flagged    : {ai_count}")
    print(f"  Non-AI        : {total - ai_count}")
    print(f"  Errors        : {errors}")
    print(f"  Saved to      : {OUTPUT_FILE}")
    print("=" * 60)

    return df


if __name__ == "__main__":
    df = run_scraper()
    if df is not None:
        print("\nFirst few rows:")
        print(df.head())
