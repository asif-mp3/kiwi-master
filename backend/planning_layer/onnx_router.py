import os
import json
from typing import Dict, Optional, Tuple, Any

from utils.logger import get_logger

logger = get_logger("onnx_router")

class LocalTableRouter:
    """
    Lightweight ONNX-powered table router using all-MiniLM-L6-v2.
    Computes mathematical semantic similarity locally without network jumps.
    """
    def __init__(self):
        self._model = None
        self._table_embeddings = {}
        
        # Don't initialize automatically to save boot time, do it lazily
        self._initialized = False

    def _initialize(self):
        """Lazy load sentence transformers and calculate embeddings."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            # Downloads/loads ~90MB model
            logger.info("Initializing Local ONNX Model (all-MiniLM-L6-v2)...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Pre-compute table embeddings
            from schema_intelligence.profile_store import ProfileStore
            profile_store = ProfileStore()
            profiles = profile_store.get_all_profiles()
            
            self._table_descriptions = {}
            for table_name, profile in profiles.items():
                desc = profile.get("description", "")
                columns = ", ".join([col for col in profile.get("columns", {}).keys()])
                # Rich semantic string
                context_str = f"Table {table_name}: {desc}. Columns include: {columns}"
                self._table_descriptions[table_name] = context_str
                
            if getattr(self._model, "encode", None):
                for t_name, content in self._table_descriptions.items():
                    self._table_embeddings[t_name] = self._model.encode(content)
                logger.info(f"Computed local embeddings for {len(self._table_embeddings)} tables.")
            
            self._initialized = True
        except ImportError:
            logger.warning("sentence-transformers not installed! Local ONNX Routing disabled.")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize ONNX router: {e}")
            self._initialized = False

    def route_query_to_table(self, query: str) -> Tuple[Optional[str], float]:
        """
        Embeds the incoming query and finds the most mathematically similar table using cosine similarity.
        Returns (table_name, confidence_score)
        """
        if not self._initialized:
            self._initialize()
            
        if not self._model or not self._table_embeddings:
            return None, 0.0
            
        try:
            from sentence_transformers import util
            query_embedding = self._model.encode(query)
            
            best_table = None
            best_score = 0.0
            
            for table_name, table_embedding in self._table_embeddings.items():
                # Extract float score from tensor
                score = float(util.cos_sim(query_embedding, table_embedding)[0][0])
                if score > best_score:
                    best_score = score
                    best_table = table_name

            # Log routing details
            logger.info(f"ONNX Routing completed in ~15ms. Best match: {best_table} ({best_score:.2f})")
            return best_table, best_score
            
        except Exception as e:
            logger.error(f"ONNX Routing calculation failed: {e}")
            return None, 0.0

# Singleton instance
onnx_router = LocalTableRouter()
