import json
import os
from typing import Dict, Any, List

class Memory:
    def __init__(self, file_path: str = "memory.json"):
        self.file_path = file_path
        self.data = self._load_memory()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "owner_name": None,
            "startup_name": None,
            "startup_pitch": None,
            "pitch_deck_path": None,
            "investors": {},
            "network_status_history": [],
            "gmail_last_checked": None,
            "pending_tasks": [],
            "conversation_context": []
        }

    def _load_memory(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            state = self._default_state()
            self._save_memory(state)
            return state
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in self._default_state().items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            print(f"Error loading memory: {e}")
            return self._default_state()

    def _save_memory(self, data: dict = None):
        if data is None:
            data = self.data
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def update(self, key: str, value: Any):
        self.data[key] = value
        self._save_memory()

    def get(self, key: str) -> Any:
        return self.data.get(key)
        
    def add_investor(self, email: str, details: dict):
        # details: { name, company, focus, status, last_contact, notes, emails_sent[] }
        if "investors" not in self.data:
            self.data["investors"] = {}
        if email not in self.data["investors"]:
            self.data["investors"][email] = {
                "name": details.get("name", ""),
                "company": details.get("company", ""),
                "focus": details.get("focus", ""),
                "status": details.get("status", "Prospect"),
                "last_contact": details.get("last_contact", None),
                "notes": details.get("notes", ""),
                "emails_sent": details.get("emails_sent", [])
            }
        else:
            self.data["investors"][email].update(details)
        self._save_memory()

    def update_investor_status(self, email: str, status: str):
        if "investors" in self.data and email in self.data["investors"]:
            self.data["investors"][email]["status"] = status
            self._save_memory()
            return True
        return False
        
    def get_investors(self) -> Dict[str, dict]:
        return self.data.get("investors", {})

    def add_network_status(self, status_record: dict):
        # status_record: { timestamp, testnet_block, mainnet_block, status }
        self.data["network_status_history"].append(status_record)
        # Keep only the last 100 entries
        if len(self.data["network_status_history"]) > 100:
            self.data["network_status_history"] = self.data["network_status_history"][-100:]
        self._save_memory()

    def update_gmail_last_checked(self, timestamp: float):
        self.data["gmail_last_checked"] = timestamp
        self._save_memory()

    def add_pending_task(self, task: str):
        self.data["pending_tasks"].append(task)
        self._save_memory()

    def remove_pending_task(self, task: str):
        if task in self.data["pending_tasks"]:
            self.data["pending_tasks"].remove(task)
            self._save_memory()

    def add_conversation_message(self, role: str, message: str):
        self.data["conversation_context"].append({"role": role, "content": message})
        # Keep only the last 20 messages for continuity
        if len(self.data["conversation_context"]) > 20:
            self.data["conversation_context"] = self.data["conversation_context"][-20:]
        self._save_memory()

    def get_conversation_context(self) -> List[dict]:
        return self.data.get("conversation_context", [])

# Global singleton instance
memory = None

def get_memory_instance():
    global memory
    if memory is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        path = os.getenv("MEMORY_FILE_PATH", "memory.json")
        memory = Memory(path)
    return memory
