"""
Question cache for storing and retrieving similar questions.
Uses semantic similarity to detect and return cached answers.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class QuestionCache:
    """Cache for question-answer pairs with semantic similarity matching"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize question cache.
        
        Args:
            similarity_threshold: Minimum similarity score for cache hit (0-1)
        """
        self.cache = []  # List of {question, embedding, answer, metadata, timestamp}
        self.similarity_threshold = similarity_threshold
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Same as schema retrieval
    
    def add_to_cache(self, question: str, answer: str, metadata: Dict = None):
        """
        Add a question-answer pair to cache.
        
        Args:
            question: User question
            answer: System answer
            metadata: Additional metadata (plan, data, etc.)
        """
        # Generate embedding for question
        embedding = self.model.encode(question, convert_to_numpy=True)
        
        cache_entry = {
            'question': question,
            'embedding': embedding,
            'answer': answer,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.cache.append(cache_entry)
    
    def find_similar(self, question: str) -> Optional[Tuple[str, Dict, float]]:
        """
        Find similar question in cache.
        
        Args:
            question: User question to search for
            
        Returns:
            Tuple of (answer, metadata, similarity_score) if found, None otherwise
        """
        if not self.cache:
            return None
        
        # Generate embedding for query
        query_embedding = self.model.encode(question, convert_to_numpy=True)
        
        # Calculate similarities
        best_match = None
        best_score = 0.0
        
        for entry in self.cache:
            # Cosine similarity
            similarity = np.dot(query_embedding, entry['embedding']) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(entry['embedding'])
            )
            
            if similarity > best_score:
                best_score = similarity
                best_match = entry
        
        # Return if above threshold
        if best_score >= self.similarity_threshold:
            return (best_match['answer'], best_match['metadata'], best_score)
        
        return None
    
    def clear_cache(self):
        """Clear all cached questions"""
        self.cache = []
    
    def get_cache_size(self) -> int:
        """Get number of cached questions"""
        return len(self.cache)
    
    def get_recent_questions(self, n: int = 5) -> List[str]:
        """
        Get n most recent questions from cache.
        
        Args:
            n: Number of recent questions to return
            
        Returns:
            List of recent questions
        """
        recent = sorted(self.cache, key=lambda x: x['timestamp'], reverse=True)[:n]
        return [entry['question'] for entry in recent]
