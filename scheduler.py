import logging
from apscheduler.schedulers.background import BackgroundScheduler
from tzlocal import get_localzone
import time

from blockchain_monitor import check_networks
from gmail_service import check_unread_emails_api
from telegram_bot import send_message_to_owner
from memory import get_memory_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=str(get_localzone()))

def job_check_networks():
    logger.info("Running scheduled network check...")
    try:
        check_networks(is_automated=True)
    except Exception as e:
        logger.error(f"Error checking networks via scheduler: {e}")

def job_check_emails():
    logger.info("Running scheduled email check...")
    try:
        memory = get_memory_instance()
        emails = check_unread_emails_api()
        
        if emails:
            # Get previously seen emails to avoid spamming
            seen_emails = memory.get("seen_emails") or []
            new_emails = [e for e in emails if e['id'] not in seen_emails]
            
            if new_emails:
                report = f"🔔 You have {len(new_emails)} NEW unread emails since last check:\n\n"
                for i, e in enumerate(new_emails, 1):
                    report += (
                        f"{i}. From: {e['sender_name']} ({e['sender_email']})\n"
                        f"   Subject: {e['subject']}\n"
                        f"   Preview: \"{e['preview']}\"\n\n"
                    )
                report += "Reply with /emails to see the full list or reply using AI."
                
                # Update memory
                for e in new_emails:
                    seen_emails.append(e['id'])
                # Keep only last 100 seen emails so it doesn't grow indefinitely
                memory.update("seen_emails", seen_emails[-100:])
                
                # Send async telegram message
                import asyncio
                from telegram_bot import get_application
                app = get_application()
                if app:
                    import os
                    owner = os.getenv("TELEGRAM_OWNER_USER_ID")
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(app.bot.send_message(chat_id=owner, text=report, parse_mode='Markdown'))
                    else:
                        loop.run_until_complete(app.bot.send_message(chat_id=owner, text=report, parse_mode='Markdown'))
                        
        memory.update_gmail_last_checked(time.time())
    except Exception as e:
        logger.error(f"Error checking emails via scheduler: {e}")

def start_scheduler():
    logger.info("Starting APScheduler for daily tasks...")
    
    # Check networks every day at 8 AM
    scheduler.add_job(job_check_networks, 'cron', hour=8, minute=0)
    
    # Check emails every 2 hours
    scheduler.add_job(job_check_emails, 'interval', hours=2)
    
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
