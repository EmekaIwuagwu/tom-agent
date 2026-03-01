import os
import json
import logging
import time
from dotenv import load_dotenv
from openai import OpenAI
from memory import get_memory_instance
from tools import AVAILABLE_TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- High-Availability FREE Fallback Models ---
MODELS_TO_TRY = [
    os.getenv("AI_MODEL_NAME", "google/gemini-2.0-flash-lite-preview-02-05:free"),
    "google/gemini-2.0-flash-001",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct"
]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """
You are TOM, a personal autonomous AI Agent. 
You MUST use your tools to provide accurate data. Do NOT guess or hallucinate.

TOOL GUIDE & CRITICAL RULES:
1. 'check_emails': ONLY for listing Gmail messages (Subjects & IDs). Use status='read', 'unread', or 'all'.
2. 'read_email_content': ONLY for reading the FULL body of a specific email using an ID.
3. 'send_gmail': ONLY for sending emails (e.g., investor pitches or custom messages).
4. 'check_blockchain_networks': ONLY for checking the status of Kortana Testnet/Mainnet blocks.
5. 'quick_search_investors': When asked to find investors, USE THIS TOOL. Pass search queries like 'seed blockchain investors "@gmail.com"'. Do NOT give up if the first try fails; try different queries.
6. 'scrape_webpage': If you find an interesting VC website but no emails in the search snippet, use this tool to visit their direct URL and rip the emails from their actual site.

CRITICAL:
- If the user asks about finding new targeted people or investors, use 'quick_search_investors'!
- Do NOT say "I cannot browse the web." You CAN browse the web using these two tools. You are a scraping powerhouse.
"""

def get_tool_definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": "check_blockchain_networks",
                "description": "Fetch live blockchain status for Kortana (blocks, exploreres, health)."
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_emails",
                "description": "Scan Gmail for messages and get their IDs. Can filter by status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Filter by 'unread', 'read', or 'all' (default is all)."},
                        "max_results": {"type": "integer", "description": "Number of emails to return (default 15, max 50)."},
                        "search_query": {"type": "string", "description": "Gmail search query, e.g., 'from:racknerd' or 'subject:invoice'."}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_email_content",
                "description": "Get the complete text content of a specific email by its ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "The unique message ID."}
                    },
                    "required": ["email_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_gmail",
                "description": "Send a new email using Gmail to investors or anyone else.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_email": {"type": "string", "description": "The recipient's email address."},
                        "subject": {"type": "string", "description": "The subject line of the email."},
                        "content": {"type": "string", "description": "The main text body of the email."},
                        "attach_deck": {"type": "boolean", "description": "True to automatically attach the startup pitch deck."}
                    },
                    "required": ["to_email", "subject", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_investor_pipeline",
                "description": "List existing investor prospects and their status."
            }
        },
        {
            "type": "function",
            "function": {
                "name": "quick_search_investors",
                "description": "Searches the web (Google/LinkedIn) for investors based on a query, returning text and found emails.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query (e.g. 'blockchain investors email')."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_webpage",
                "description": "Crawls a specific URL to extract visible text and email addresses.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The full URL of the webpage to scrape."}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_investor_contact",
                "description": "Saves a newly found investor into the pipeline memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                        "company": {"type": "string"},
                        "focus": {"type": "string", "description": "e.g., 'Web3', 'DeFi'"}
                    },
                    "required": ["email", "name", "company", "focus"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_memory_state",
                "description": "Retrieve project info (startup name, pitch, etc)."
            }
        }
    ]

def attempt_chat_completion(model_name: str, messages: list):
    try:
        for _ in range(5):
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=get_tool_definitions(),
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                messages.append(assistant_message)
                for tool_call in assistant_message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except:
                        fn_args = {}
                        
                    logger.info(f"Tom executing tool [{fn_name}] using model [{model_name}]")
                    
                    if fn_name in AVAILABLE_TOOLS:
                        try:
                            result = AVAILABLE_TOOLS[fn_name](**fn_args)
                        except Exception as e:
                            result = f"Error executing tool: {e}"
                    else:
                        result = f"Unknown tool: {fn_name}"
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": str(result)
                    })
                continue
            
            return assistant_message.content

    except Exception as e:
        raise e

def handle_user_input(user_message: str) -> str:
    if not OPENROUTER_API_KEY:
        return "Missing OPENROUTER_API_KEY in .env!"

    memory = get_memory_instance()
    history = memory.get_conversation_context()

    initial_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-4:]:
        initial_messages.append({"role": msg["role"], "content": msg["content"]})
    initial_messages.append({"role": "user", "content": user_message})

    for i, model in enumerate(MODELS_TO_TRY):
        try:
            logger.info(f"Trying model {model}...")
            # Use current_messages copy
            current_messages = [m.copy() for m in initial_messages]
            reply = attempt_chat_completion(model, current_messages)
            
            if reply:
                memory.add_conversation_message("user", user_message)
                memory.add_conversation_message("assistant", reply)
                return reply
                
        except Exception as e:
            msg = str(e).lower()
            logger.warning(f"Failed with {model}: {msg}")
            if "not found" in msg or "404" in msg:
                continue
            if i == len(MODELS_TO_TRY) - 1:
                return f"I'm temporarily exhausted across all my brains! 🤯 Error: {e}"
            continue

    return "All brains are busy. Please retry in 10 seconds!"
