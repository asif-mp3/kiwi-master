"""
Conversation history manager for Kiwi-RAG chatbot.
Handles saving, loading, and managing chat conversations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

CONVERSATIONS_DIR = "data_sources/conversations"

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle pandas Timestamp and other non-serializable objects"""
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return super().default(obj)

class ConversationManager:
    """Manages chat conversation history"""
    
    def __init__(self):
        self.conversations_dir = Path(CONVERSATIONS_DIR)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
    
    def create_conversation(self, title: str = None) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if title is None:
            title = f"New Chat {conversation_id}"
        
        conversation = {
            "id": conversation_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        self._save_conversation(conversation)
        return conversation_id
    
    def save_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to a conversation"""
        conversation = self.load_conversation(conversation_id)
        
        if conversation is None:
            # Create new conversation if it doesn't exist
            conversation = {
                "id": conversation_id,
                "title": self._generate_title_from_content(content),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": []
            }
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()
        
        # Auto-generate title from first user message
        if len(conversation["messages"]) == 1 and role == "user":
            conversation["title"] = self._generate_title_from_content(content)
        
        self._save_conversation(conversation)
    
    def load_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Load a conversation by ID"""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None
    
    def list_conversations(self) -> List[Dict]:
        """List all conversations, sorted by most recent"""
        conversations = []
        
        for file_path in self.conversations_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conv = json.load(f)
                    conversations.append({
                        "id": conv["id"],
                        "title": conv["title"],
                        "updated_at": conv["updated_at"],
                        "message_count": len(conv["messages"])
                    })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        # Sort by updated_at (most recent first)
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                print(f"Error deleting conversation {conversation_id}: {e}")
                return False
        return False
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> bool:
        """Rename a conversation"""
        conversation = self.load_conversation(conversation_id)
        
        if conversation:
            conversation["title"] = new_title
            conversation["updated_at"] = datetime.now().isoformat()
            self._save_conversation(conversation)
            return True
        return False
    
    def _save_conversation(self, conversation: Dict):
        """Save conversation to file"""
        file_path = self.conversations_dir / f"{conversation['id']}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def _generate_title_from_content(self, content: str, max_length: int = 50) -> str:
        """Generate a title from message content"""
        # Take first line or first max_length characters
        title = content.split('\n')[0]
        if len(title) > max_length:
            title = title[:max_length] + "..."
        return title or "New Chat"
