"""
Context resolver for handling follow-up questions and pronoun resolution.
Uses conversation history and LLM to rewrite questions with full context.
"""

import os
import google.generativeai as genai
from typing import List, Dict, Optional

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class ContextResolver:
    """Resolves follow-up questions using conversation history"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.followup_indicators = [
            'it', 'that', 'this', 'them', 'those', 'these',
            'what about', 'how about', 'and', 'also',
            'next', 'previous', 'same', 'similar',
            'maximum', 'minimum', 'average', 'total',
            'the', 'its', 'their'
        ]
    
    def is_followup(self, question: str, conversation_history: List[Dict]) -> bool:
        """
        Detect if question is a follow-up that needs context.
        
        Args:
            question: Current user question
            conversation_history: List of previous messages
            
        Returns:
            True if question appears to be a follow-up
        """
        if not conversation_history:
            return False
        
        question_lower = question.lower()
        
        # Check for common follow-up indicators
        for indicator in self.followup_indicators:
            if indicator in question_lower:
                return True
        
        # Check if question is very short (likely incomplete)
        if len(question.split()) <= 5:
            return True
        
        return False
    
    def resolve_context(self, question: str, conversation_history: List[Dict]) -> str:
        """
        Resolve question context using conversation history.
        
        Args:
            question: Current user question
            conversation_history: List of previous messages
            
        Returns:
            Rewritten question with full context
        """
        if not conversation_history:
            return question
        
        # Get last few Q&A pairs for context
        context_messages = []
        for msg in conversation_history[-6:]:  # Last 3 Q&A pairs
            if msg['role'] == 'user':
                context_messages.append(f"User: {msg['content']}")
            elif msg['role'] == 'assistant':
                # Just include first line of answer for context
                answer_preview = msg['content'].split('\n')[0][:200]
                context_messages.append(f"Assistant: {answer_preview}")
        
        context = "\n".join(context_messages)
        
        # Use LLM to rewrite question with context
        prompt = f"""You are helping to resolve a follow-up question in a conversation about data analytics.

Conversation History:
{context}

Current Question: {question}

Task: Rewrite the current question to be a standalone question that includes all necessary context from the conversation history. The rewritten question should be clear and complete without needing the conversation history.

Rules:
1. Resolve pronouns (it, that, this, etc.) to specific entities
2. Include time references (next day, previous month, etc.) as specific dates
3. Include metric names if referenced implicitly
4. Keep the question concise but complete
5. If the question is already standalone, return it as-is

Rewritten Question:"""
        
        try:
            response = self.model.generate_content(prompt)
            rewritten = response.text.strip()
            
            # Clean up the response
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1]
            
            return rewritten
        except Exception as e:
            print(f"Error resolving context: {e}")
            return question
    
    def extract_entities(self, question: str) -> Dict[str, List[str]]:
        """
        Extract entities from question (dates, metrics, etc.).
        
        Args:
            question: User question
            
        Returns:
            Dictionary of entity types and values
        """
        entities = {
            'dates': [],
            'metrics': [],
            'operations': []
        }
        
        # Simple entity extraction (can be enhanced)
        question_lower = question.lower()
        
        # Common metrics
        metrics = ['temperature', 'wind speed', 'pm2.5', 'ozone', 'humidity', 'pressure']
        for metric in metrics:
            if metric in question_lower:
                entities['metrics'].append(metric)
        
        # Common operations
        operations = ['maximum', 'minimum', 'average', 'sum', 'count', 'total']
        for op in operations:
            if op in question_lower:
                entities['operations'].append(op)
        
        return entities
