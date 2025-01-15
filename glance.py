import os
import sys
import time
import subprocess

# ==============================================================================
# 1) DEPENDENCY INSTALLATION
# ==============================================================================

BASE_DEPENDENCIES = [
    "openai",
    "selenium"
]

def install_dependency(package_name):
    """
    Installs a Python package using pip.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"Successfully installed {package_name}")
    except subprocess.CalledProcessError:
        print(f"Failed to install {package_name}. Please install it manually.")

def check_and_install_dependencies():
    """
    Ensures all required dependencies are installed.
    """
    # 1) Install base dependencies first
    for package in BASE_DEPENDENCIES:
        try:
            __import__(package)
        except ImportError:
            print(f"Dependency {package} is not installed. Attempting to install...")
            install_dependency(package)

    # 2) Install OS-specific window manager library:
    #    - pygetwindow on Windows
    #    - pywinctl on Linux/macOS
    if os.name == 'nt':
        os_dep = "pygetwindow"
    else:
        os_dep = "pywinctl"

    try:
        __import__(os_dep)
    except ImportError:
        print(f"OS-specific dependency {os_dep} is not installed. Attempting to install...")
        install_dependency(os_dep)

# Perform dependency checks/installs before importing them anywhere else
check_and_install_dependencies()

# ==============================================================================
# 2) IMPORTS (Safe to do now that dependencies are ensured)
# ==============================================================================
from selenium import webdriver
from selenium.webdriver.common.by import By

# Import our separate file that contains the OpenAI API key
from api_config_prod import get_api_key

# Initialize the OpenAI client
from openai import OpenAI
client = OpenAI(api_key=get_api_key())

# We still import these for completeness, though we won't rely on them for URL logic
if os.name == 'nt':  # Windows
    import pygetwindow as gw
    WM_MODE = "pygetwindow"
    print("Using pygetwindow on Windows.")
else:
    import pywinctl as wc
    WM_MODE = "pywinctl"
    print("Using pywinctl on Linux/macOS.")

# ==============================================================================
# 4) SELENIUM SETUP (ChromeDriver must be in PATH or specify path)
# ==============================================================================
driver = webdriver.Chrome()

# ==============================================================================
# 6) SUMMARIZATION LOGIC
# ==============================================================================
def extract_text_from_url(url):
    """
    Uses Selenium to open 'url' in Chrome and extract the visible text from <body>.
    """
    driver.get(url)
    time.sleep(2)  # Let the page load
    body = driver.find_element(By.TAG_NAME, "body")
    return body.text

def summarize_text(text, model="gpt-4"):
    """
    Summarizes 'text' using OpenAI's ChatCompletion (openai>=1.0.0).
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": f"Summarize this text:\n{text}"}
        ]
    )
    return response.choices[0].message.content

# ==============================================================================
# 7) MAIN LOOP (Always-On Summarization)
# ==============================================================================
def main():
    """
    Repeatedly:
      1) Checks the browser's current URL.
      2) If the URL hasn't been processed yet, extract & summarize text.
      3) Wait 5 seconds and repeat.
    """
    processed_urls = set()

    print("\nBrowser is open. Feel free to browse freely within the Selenium window.")
    print("The script will automatically scrape and summarize the text of any new page you visit.")

    while True:
        try:
            current_url = driver.current_url
        except Exception as e:
            # If something goes wrong with retrieving the current URL, just wait and retry
            print(f"Error retrieving current URL: {e}")
            time.sleep(5)
            continue

        # Basic sanity check to avoid 'about:blank' or empty URLs
        if not current_url or current_url.startswith("about:"):
            time.sleep(5)
            continue

        # Avoid re-processing the same URL
        if current_url not in processed_urls:
            print(f"Processing new URL: {current_url}")

            # Extract text from the page
            try:
                extracted_text = extract_text_from_url(current_url)
            except Exception as e:
                print(f"Error extracting text from '{current_url}': {e}")
                time.sleep(5)
                continue

            # Summarize the extracted text
            try:
                summary = summarize_text(extracted_text)
                print(f"Summary:\n{summary}\n")
            except Exception as e:
                print(f"Error summarizing text: {e}")
                time.sleep(5)
                continue

            # Mark URL as processed
            processed_urls.add(current_url)

        # Wait 5 seconds before repeating
        time.sleep(5)

# ==============================================================================
# 8) SCRIPT ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        driver.quit()
