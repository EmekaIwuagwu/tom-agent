import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from memory import get_memory_instance
from tools import AVAILABLE_TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("GEMINI_API_KEY not found in environment.")

SYSTEM_PROMPT = """
You are TOM, a personal autonomous AI Agent that operates like a real human employee. 
You have persistent memory, can browse the web, monitor blockchain networks, manage Gmail, 
notify via Telegram, and run investor outreach campaigns — all autonomously.

Your personality:
- A real human-feeling AI agent, not a robot or assistant.
- Proactive: flags things before being asked.
- Memory-driven: references past conversations naturally.
- Concise on Telegram (short messages, not essays).
- Professional but warm — like a trusted team member.
- Always confirms before sending emails or bulk actions.
- Uses clean formatting with emojis for readability on Telegram.
- Occasionally adds personality: "That's a strong investor fit" or "Their portfolio is heavy in DeFi — perfect match for Kortana".

Always check your memory first for context. Do not repeat questions you already know the answer to. 
If the user asks to send an email or start a campaign, draft the email and show it to the user FIRST, asking for confirmation like "looks good" or "send".
"""

# Convert dictionary of functions to a list of Python functions
agent_tools = list(AVAILABLE_TOOLS.values())

def get_gemini_model():
    return genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_PROMPT,
        tools=agent_tools
    )

def handle_user_input(user_message: str) -> str:
    """
    Takes user input from Telegram, retrieves history from Memory,
    sends logic to Gemini, handles tool calls automatically,
    and returns Gemini's final response text.
    """
    memory = get_memory_instance()
    
    # Format history for Gemini SDK
    history = memory.get_conversation_context()
    
    # Start a chat session with history
    model = get_gemini_model()
    
    # Convert history format
    formatted_history = []
    for msg in history:
        # Map our internal role representation to Gemini's expected formats
        role = msg["role"]
        if role == "assistant":
            role = "model"
        formatted_history.append({"role": role, "parts": [msg["content"]]})
        
    try:
        chat = model.start_chat(history=formatted_history, enable_automatic_function_calling=True)
        
        # Send message
        response = chat.send_message(user_message)
        
        reply_text = response.text
        
        if reply_text:
             memory.add_conversation_message("user", user_message)
             memory.add_conversation_message("assistant", reply_text)
             
        return reply_text
    
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return f"Sorry, I encountered an internal error: {e}"
