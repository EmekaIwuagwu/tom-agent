import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from agent import handle_user_input

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_USER_ID")

# Create application globally to use bot for external sends
application = None

def get_application():
    global application
    if not application and TELEGRAM_TOKEN:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
    return application

def send_message_to_owner(text: str):
    """Utility function for background tasks to send async message to owner."""
    app = get_application()
    if not app:
        logger.error("Telegram app not initialized. Cannot send message.")
        return
        
    async def _send():
        try:
            await app.bot.send_message(chat_id=TELEGRAM_OWNER_ID, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending message to owner: {e}")
            
    # Try running it in current event loop or new one
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_send())
        else:
            loop.run_until_complete(_send())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_send())

async def is_owner(update: Update) -> bool:
    user_id = str(update.effective_user.id)
    if TELEGRAM_OWNER_ID and user_id != TELEGRAM_OWNER_ID:
        await update.message.reply_text("⛔ Access denied. I operate exclusively for my owner.")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update): return
    await update.message.reply_text("Hello! I'm TOM, your autonomous AI Agent. I'm online and ready. Type /help to see my commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update): return
    help_text = """
*TOM's Commands*
/status - Check blockchain networks right now
/emails - Check Gmail for new emails right now
/pipeline - Show investor pipeline status
/prospects - List all investor prospects
/campaign - Start an investor outreach campaign
/memory - Show what I currently remember
/help - List these commands

You can also talk to me naturally like: 'Check my networks' or 'Who haven't I followed up with?'
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def process_via_agent(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str = ""):
    """Passes the input to Gemini Agent."""
    if not await is_owner(update): return
    
    user_text = update.message.text
    if prefix:
         user_text = f"User ran command '{prefix}'. Fulfill this request using your tools."
         
    # Send a typing action so the user knows Tom is thinking
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    response = handle_user_input(user_text)
    
    if response:
        # Split text if too long for Telegram (4096 chars constraint)
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text("I'm sorry, I couldn't process that.")

# Shortcuts mapping
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/status")

async def emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/emails")

async def pipeline_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/pipeline")
    
async def prospects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/prospects")

async def campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/campaign")

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context, "/memory")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_via_agent(update, context)

def setup_bot():
    app = get_application()
    if not app:
        logger.error("Telegram bot could not be initialized.")
        return None
        
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("emails", emails_command))
    app.add_handler(CommandHandler("pipeline", pipeline_command))
    app.add_handler(CommandHandler("prospects", prospects_command))
    app.add_handler(CommandHandler("campaign", campaign_command))
    app.add_handler(CommandHandler("memory", memory_command))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    return app

def run_bot():
    app = setup_bot()
    if app:
        logger.info("Starting Telegram Bot Polling...")
        app.run_polling()
