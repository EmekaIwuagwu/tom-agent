import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import logging
from memory import get_memory_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_url(url: str) -> dict:
    """
    Crawls a URL using Playwright and extracts text and emails using BeautifulSoup.
    """
    logger.info(f"Scraping {url}...")
    content = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Wait until "domcontentloaded" to avoid hanging on external resources
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Give it some time for JS framework renders
            page.wait_for_timeout(3000)
            content = page.content()
            browser.close()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        text_content = soup.get_text(separator=' ', strip=True)
        text_content = ' '.join(text_content.split())
        
        # Basic email regex
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text_content)
        emails = list(set(emails))
        
        return {
            "url": url,
            "text": text_content[:15000],  # Limit to 15k characters for LLM context
            "emails_found": emails
        }
            
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {"url": url, "text": "", "emails_found": []}

def search_investors(query: str) -> dict:
    """
    Simulates a Google search or parses text to find targets.
    """
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    return scrape_url(search_url)

def process_and_save_investor(email: str, name: str, company: str, focus: str):
    """
    Saves the extracted investor to memory.
    """
    memory = get_memory_instance()
    investor_data = {
        "name": name,
        "company": company,
        "focus": focus,
        "status": "Prospect"
    }
    memory.add_investor(email, investor_data)
    logger.info(f"Saved prospect: {name} ({email}) at {company}")
    return investor_data
