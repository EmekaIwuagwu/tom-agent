import logging
from memory import get_memory_instance
from blockchain_monitor import check_networks
from gmail_service import check_unread_emails_playwright, send_email_api
from scraper import scrape_url, search_investors, process_and_save_investor

logger = logging.getLogger(__name__)

# Core tools that Gemini can call

def get_memory_state() -> str:
    """Returns the current state of Tom's memory."""
    memory = get_memory_instance()
    mem_str = (
        f"Owner Name: {memory.get('owner_name')}\n"
        f"Startup Name: {memory.get('startup_name')}\n"
        f"Startup Pitch: {memory.get('startup_pitch')}\n"
        f"Pitch Deck Path: {memory.get('pitch_deck_path')}\n"
    )
    return mem_str

def set_memory_value(key: str, value: str) -> str:
    """Sets a memory value for owner_name, startup_name, startup_pitch, or pitch_deck_path."""
    valid_keys = ["owner_name", "startup_name", "startup_pitch", "pitch_deck_path"]
    if key in valid_keys:
        memory = get_memory_instance()
        memory.update(key, value)
        return f"Successfully updated {key} to {value}."
    return f"Invalid key. Valid keys are: {valid_keys}"

def check_blockchain_networks() -> str:
    """Checks the status of Kortana testnet and mainnet, and returns the report."""
    return check_networks(is_automated=False)

def check_unread_emails() -> str:
    """Scans the Gmail inbox for unread emails and returns a structured list."""
    emails = check_unread_emails_playwright()
    if not emails:
        return "No unread emails right now."
        
    report = f"📬 You have {len(emails)} unread emails:\n\n"
    for i, e in enumerate(emails, 1):
        report += (
            f"{i}. From: {e['sender_name']} ({e['sender_email']})\n"
            f"   Subject: {e['subject']}\n"
            f"   Preview: \"{e['preview']}\"\n\n"
        )
    report += "Reply with 'read X' to see full email, or 'reply X' to respond."
    return report

def send_gmail(to_email: str, subject: str, content: str, attach_deck: bool = False) -> str:
    """Sends an email using the Gmail API, optionally attaching the pitch deck."""
    memory = get_memory_instance()
    attachment_path = None
    if attach_deck:
        attachment_path = memory.get("pitch_deck_path")
        if not attachment_path:
            return "Failed to send: Pitch deck path is not set in memory."
            
    success = send_email_api(to_email, subject, content, attachment_path)
    if success:
        # If it was to a prospect, update emails sent and status
        if "investors" in memory.data and to_email in memory.data["investors"]:
            import time
            memory.data["investors"][to_email]["status"] = "Contacted"
            memory.data["investors"][to_email]["last_contact"] = time.time()
            memory.data["investors"][to_email]["emails_sent"].append(subject)
            memory._save_memory()
        return f"Successfully sent email to {to_email}."
    else:
        return f"Failed to send email to {to_email}."

def scrape_webpage(url: str) -> str:
    """Crawls a URL to extract visible text and email addresses."""
    data = scrape_url(url)
    if not data["text"]:
         return f"Failed to scrape {url} or nothing found."
    
    return (
        f"Scraped {url}:\n"
        f"Text excerpt: {data['text']}...\n"
        f"Emails found: {', '.join(data['emails_found'])}\n\n"
        f"If this is an investor, call save_investor_contact to save them."
    )

def quick_search_investors(query: str) -> str:
    """Googles for investors and returns webpage text and found emails."""
    data = search_investors(query)
    return f"Search results for '{query}':\nText excerpt: {data['text']}...\nEmails found: {data['emails_found']}"

def save_investor_contact(email: str, name: str, company: str, focus: str) -> str:
    """Saves a newly found investor into the pipeline memory."""
    process_and_save_investor(email, name, company, focus)
    return f"Saved prospect {name} ({email}) from {company} to pipeline."

def get_investor_pipeline() -> str:
    """Returns all investors stored in memory grouped by their status."""
    memory = get_memory_instance()
    investors = memory.get_investors()
    if not investors:
        return "The pipeline is currently empty."
        
    by_status = {}
    for email, data in investors.items():
        st = data.get("status", "Prospect")
        if st not in by_status:
            by_status[st] = []
        by_status[st].append(f"- {data['name']} ({email}) - {data['company']}")
        
    report = "📊 *Investor Pipeline*\n\n"
    stages = ["Prospect", "Contacted", "Replied", "Meeting Scheduled", "Closed", "Passed"]
    # Ensure all stages exist in report visually
    found = False
    for stage in stages:
        if stage in by_status:
           found = True
           report += f"{'🟡' if stage == 'Prospect' else '📤' if stage == 'Contacted' else '📬' if stage == 'Replied' else '📅' if stage == 'Meeting Scheduled' else '✅' if stage == 'Closed' else '❌'} {stage}:\n"
           report += "\n".join(by_status[stage])
           report += "\n\n"
           
    # add unknown stages
    for stage in by_status:
        if stage not in stages:
            report += f"❓ {stage}:\n" + "\n".join(by_status[stage]) + "\n\n"
            
    if not found:
        # just list what we have
        for stage, items in by_status.items():
             report += f"{stage}:\n" + "\n".join(items) + "\n\n"

    return report

def update_investor_status(email: str, new_status: str) -> str:
    """Updates an investor's status in the pipeline (e.g., Prospect, Contacted, Replied)."""
    memory = get_memory_instance()
    success = memory.update_investor_status(email, new_status)
    if success:
        return f"Updated {email} status to {new_status}."
    return f"Could not find investor {email}."

# Dictionary mapping function names to actual Python functions
AVAILABLE_TOOLS = {
    "get_memory_state": get_memory_state,
    "set_memory_value": set_memory_value,
    "check_blockchain_networks": check_blockchain_networks,
    "check_unread_emails": check_unread_emails,
    "send_gmail": send_gmail,
    "scrape_webpage": scrape_webpage,
    "quick_search_investors": quick_search_investors,
    "save_investor_contact": save_investor_contact,
    "get_investor_pipeline": get_investor_pipeline,
    "update_investor_status": update_investor_status
}
