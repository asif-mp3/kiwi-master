"""
ChromaDB client for schema-level semantic retrieval.

CRITICAL: This module uses Hugging Face embeddings ONLY.
ONNX embeddings are explicitly disabled to ensure Streamlit compatibility on Windows.

Embedding Model: sentence-transformers/all-MiniLM-L6-v2
- No API key required (uses local cached model)
- No Visual C++ dependencies
- No ONNX runtime required
- Streamlit-safe and Windows-safe

NOTE: RAG search is DISABLED in table_router.py (USE_RAG_SEARCH = False).
When CHROMADB_ENABLED = False, all methods become no-ops to save resources.
"""

# MASTER SWITCH: Set to False to disable ChromaDB entirely (saves memory & startup time)
# RAG search is disabled in table_router.py anyway, so this saves wasted computation
CHROMADB_ENABLED = False

import os
from typing import List

# Only import heavy dependencies if enabled
if CHROMADB_ENABLED:
    import chromadb
    from chromadb.config import Settings
    from chromadb.api.types import EmbeddingFunction
    from schema_intelligence.embedding_builder import build_schema_documents


class CustomSentenceTransformerEmbedding:
    """
    Custom embedding function using sentence-transformers directly.
    This avoids ChromaDB's built-in wrapper which has PyTorch compatibility issues.

    NOTE: Only instantiated when CHROMADB_ENABLED = True
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if not CHROMADB_ENABLED:
            return
        try:
            from sentence_transformers import SentenceTransformer
            import torch

            # Set environment variable to avoid tokenizers parallelism warning
            os.environ["TOKENIZERS_PARALLELISM"] = "false"

            # Load model with explicit device configuration
            self.model = SentenceTransformer(model_name, device='cpu')
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize SentenceTransformer model. "
                f"Error: {e}"
            )

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        if not CHROMADB_ENABLED:
            return []
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()


class SchemaVectorStore:
    """
    Vector store for schema-level semantic search.

    IMPORTANT: This class explicitly uses Hugging Face embeddings to avoid ONNX.
    ChromaDB's default embedding function (ONNX) causes DLL errors on Windows/Streamlit.

    NOTE: When CHROMADB_ENABLED = False, all methods are no-ops.
    RAG search is disabled in table_router.py so this saves resources.
    """

    def __init__(self, persist_dir="schema_store"):
        """
        Initialize ChromaDB with explicit Hugging Face embeddings.

        GUARDRAIL: This constructor NEVER allows ChromaDB to use default embeddings.
        If embedding initialization fails, the system will fail fast with a clear error.
        """
        self.enabled = CHROMADB_ENABLED
        if not self.enabled:
            print("  [ChromaDB] DISABLED - all operations are no-ops (saves memory & startup time)")
            return

        # Use PersistentClient for proper disk persistence with settings
        settings = Settings(
            allow_reset=True,
            is_persistent=True
        )
        self.client = chromadb.PersistentClient(path=persist_dir, settings=settings)
        self.collection_name = "schema"

        # CRITICAL: Create Hugging Face embedding function explicitly
        # This prevents ChromaDB from defaulting to ONNX embeddings
        try:
            # Use our custom embedding function to avoid PyTorch meta tensor issues
            self.embedding_function = CustomSentenceTransformerEmbedding()
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Hugging Face embeddings. "
                f"ONNX embeddings are disabled by design. "
                f"Ensure sentence-transformers is installed: pip install sentence-transformers\n"
                f"Error: {e}"
            )

        # Verify we're not using ONNX (runtime guardrail)
        embedding_type = type(self.embedding_function).__name__
        if "onnx" in embedding_type.lower():
            raise RuntimeError(
                f"ONNX embeddings detected ({embedding_type}). "
                f"This is not allowed. The system must use Hugging Face embeddings only."
            )
    
    def clear_collection(self):
        """
        Clear all schema embeddings from the collection.
        Used during full reset to remove old schema references.
        """
        if not self.enabled:
            return  # No-op when disabled

        try:
            # Delete the collection
            self.client.delete_collection(self.collection_name)
            print(f"   Deleted ChromaDB collection: {self.collection_name}")
        except Exception as e:
            # Collection may not exist
            print(f"   ChromaDB collection doesn't exist (first run or already cleared)")
    
    def delete_by_source_id(self, source_id: str):
        """
        Delete all documents (schema and row embeddings) for a given source_id.

        This is used for atomic sheet-level rebuilds: when a sheet changes,
        ALL embeddings derived from that sheet are deleted before rebuilding.

        Args:
            source_id: Source identifier (spreadsheet_id#sheet_name)

        Returns:
            Number of documents deleted
        """
        if not self.enabled:
            return 0  # No-op when disabled

        try:
            # Get or create collection
            try:
                collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            except Exception:
                # Collection doesn't exist, nothing to delete
                return 0
            
            # Query for all documents with this source_id
            # ChromaDB doesn't support direct deletion by metadata filter,
            # so we need to get IDs first then delete them
            results = collection.get(
                where={"source_id": source_id},
                include=["metadatas"]
            )
            
            if not results or not results['ids']:
                print(f"   No ChromaDB documents found for source_id: {source_id}")
                return 0
            
            # Delete documents by ID
            ids_to_delete = results['ids']
            collection.delete(ids=ids_to_delete)
            
            print(f"   Deleted {len(ids_to_delete)} ChromaDB document(s) for source_id: {source_id}")
            return len(ids_to_delete)
            
        except Exception as e:
            print(f"   [WARN]  Error deleting ChromaDB documents for source_id {source_id}: {e}")
            return 0

    def rebuild(self, source_ids=None):
        """
        Rebuild schema vector store from scratch or for specific source_ids.

        IMPORTANT: Always passes explicit embedding function to prevent ONNX fallback.

        Args:
            source_ids: Optional list of source_ids to rebuild.
                       If None: Full rebuild (delete all, rebuild all)
                       If provided: Delete only documents matching these source_ids, then rebuild
        """
        if not self.enabled:
            return  # No-op when disabled

        if source_ids is None:
            # FULL REBUILD: Delete entire collection and rebuild from scratch
            print("   Performing FULL ChromaDB rebuild...")
            
            # Delete existing collection if present
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass  # Collection may not exist yet

            # Create fresh collection WITH EXPLICIT EMBEDDING FUNCTION
            # This is critical - never allow ChromaDB to use default embeddings
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function  # EXPLICIT: No ONNX fallback
            )
        else:
            # PARTIAL REBUILD: Delete only documents for specified source_ids
            print(f"   Performing PARTIAL ChromaDB rebuild for {len(source_ids)} source(s)...")
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            
            # Delete documents for each source_id
            for source_id in source_ids:
                self.delete_by_source_id(source_id)

        # Build documents from schema
        documents = build_schema_documents()
        
        # Filter documents if partial rebuild
        if source_ids is not None:
            # Only rebuild documents for specified source_ids
            documents = [doc for doc in documents if doc.get("source_id") in source_ids]
            print(f"   Rebuilding {len(documents)} document(s) for specified source_ids")

        # Build clean metadata (NO None values)
        metadatas = []
        for doc in documents:
            meta = {"type": doc["type"]}

            if doc.get("table") is not None:
                meta["table"] = doc["table"]

            if doc.get("metric") is not None:
                meta["metric"] = doc["metric"]
            
            # Add source_id to metadata for filtering
            if doc.get("source_id") is not None:
                meta["source_id"] = doc["source_id"]

            metadatas.append(meta)

        # Add embeddings (auto-persisted by Chroma)
        # Embeddings are generated using Hugging Face model (all-MiniLM-L6-v2)
        if documents:  # Only add if there are documents to add
            self.collection.add(
                ids=[doc["id"] for doc in documents],
                documents=[doc["text"] for doc in documents],
                metadatas=metadatas
            )
            print(f"   Added {len(documents)} document(s) to ChromaDB")

    def count(self):
        """Get the number of documents in the collection."""
        if not self.enabled:
            return 0  # No-op when disabled

        # Get collection WITH EXPLICIT EMBEDDING FUNCTION
        collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function  # EXPLICIT: No ONNX fallback
        )
        return collection.count()

    def query(self, question: str, top_k: int = 5) -> List[dict]:
        """
        Query the vector store for relevant schema documents.

        This is the CORE RAG retrieval method that finds semantically similar
        schema information based on the user's question.

        Args:
            question: User's natural language question
            top_k: Number of results to return (default: 5)

        Returns:
            List of dicts with:
            - document: The schema text
            - metadata: Dict with table, type, metric info
            - distance: Similarity distance (lower = more similar)
        """
        if not self.enabled:
            return []  # No-op when disabled

        try:
            # Get collection
            try:
                collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            except Exception:
                print("[RAG] No ChromaDB collection found - returning empty results")
                return []

            # Query for similar documents
            results = collection.query(
                query_texts=[question],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    })

            return formatted_results

        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return []

    def get_relevant_tables(self, question: str, top_k: int = 3) -> List[tuple]:
        """
        Get the most relevant table names for a question.

        This method uses semantic search to find tables that are most likely
        to contain the answer to the user's question.

        Args:
            question: User's natural language question
            top_k: Number of tables to return

        Returns:
            List of (table_name, relevance_score) tuples, sorted by relevance
        """
        if not self.enabled:
            return []  # No-op when disabled

        results = self.query(question, top_k=top_k * 2)  # Get more results to dedupe tables

        # Aggregate scores by table
        table_scores = {}
        for result in results:
            table_name = result['metadata'].get('table')
            if table_name:
                # Convert distance to similarity (lower distance = higher similarity)
                similarity = 1.0 / (1.0 + result['distance'])
                if table_name in table_scores:
                    table_scores[table_name] = max(table_scores[table_name], similarity)
                else:
                    table_scores[table_name] = similarity

        # Sort by score and return top_k
        sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_tables[:top_k]

    def get_schema_context(self, question: str, top_k: int = 5) -> str:
        """
        Get formatted schema context for LLM prompt.

        This method retrieves relevant schema information and formats it
        for inclusion in the LLM context/prompt.

        Args:
            question: User's natural language question
            top_k: Number of schema documents to include

        Returns:
            Formatted string with relevant schema information
        """
        results = self.query(question, top_k=top_k)

        if not results:
            return "No relevant schema information found."

        context_parts = []
        for i, result in enumerate(results, 1):
            meta = result['metadata']
            table = meta.get('table', 'Unknown')
            doc_type = meta.get('type', 'schema')
            context_parts.append(f"{i}. [{table}] ({doc_type}): {result['document']}")

        return "\n".join(context_parts)
