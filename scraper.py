import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import logging
from memory import get_memory_instance
from duckduckgo_search import DDGS

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

def search_investors(query: str, max_results: int = 6) -> dict:
    """
    Searches the web using DuckDuckGo to find targeted pages, then scrapes them to extract text and emails.
    """
    logger.info(f"Searching web for: {query}")
    results_text = []
    all_emails = set()
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        if not results:
            return {"text": "No search results found.", "emails_found": []}
            
        for r in results:
            link = r.get("href")
            title = r.get("title")
            snippet = r.get("body", "")
            
            # Extract emails directly from snippets
            snippet_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', snippet)
            for e in snippet_emails:
                all_emails.add(e)
            
            results_text.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}\n")
            
            # Deep scrape the result link to find more emails
            scrape_data = scrape_url(link)
            if scrape_data["emails_found"]:
                for e in scrape_data["emails_found"]:
                    all_emails.add(e)
            
            # Add a bit of the site text for the AI to read
            site_text = scrape_data["text"][:2000] # Limit text per site to save tokens
            if site_text:
                results_text.append(f"Content from {link}:\n{site_text}...\n")
                
        return {
            "text": "\n---\n".join(results_text)[:15000],  # Limit total context size
            "emails_found": list(all_emails)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"text": f"Search encountered an error: {e}", "emails_found": []}

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
