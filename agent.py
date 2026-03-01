import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory import get_memory_instance
from tools import AVAILABLE_TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

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

MODEL = "gemini-3-flash-preview"

def handle_user_input(user_message: str) -> str:
    """
    Takes user input from Telegram, retrieves history from Memory,
    sends logic to Gemini, handles tool calls automatically,
    and returns Gemini's final response text.
    """
    memory = get_memory_instance()
    history = memory.get_conversation_context()

    # Build conversation history in genai format
    contents = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    # Add current user message
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    try:
        # Agentic loop: keep calling Gemini until there are no more tool calls
        while True:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=list(AVAILABLE_TOOLS.values()),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )

            candidate = response.candidates[0]
            
            # Check if there are any tool calls
            tool_calls = [part for part in candidate.content.parts if part.function_call]

            if not tool_calls:
                # No tool calls — final text response
                reply_text = "".join(part.text for part in candidate.content.parts if part.text)
                if reply_text:
                    memory.add_conversation_message("user", user_message)
                    memory.add_conversation_message("assistant", reply_text)
                return reply_text

            # Append the model's response (with tool calls) to the history
            contents.append(candidate.content)

            # Execute each tool call and collect results
            tool_results = []
            for part in tool_calls:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                logger.info(f"Tom calling tool: {fn_name}({fn_args})")

                if fn_name in AVAILABLE_TOOLS:
                    try:
                        result = AVAILABLE_TOOLS[fn_name](**fn_args)
                    except Exception as e:
                        result = f"Error executing {fn_name}: {e}"
                else:
                    result = f"Unknown tool: {fn_name}"

                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fn_name,
                            response={"result": str(result)}
                        )
                    )
                )

            # Add tool results back into the conversation
            contents.append(types.Content(role="user", parts=tool_results))

    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return f"Sorry, I hit an error: {e}"
