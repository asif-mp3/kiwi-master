"""
Query Cache - LRU cache for query results with TTL.

Implements the CACHING FLOW from the architecture:
1. Generate cache key: Hash(question + table + filters)
2. Check if result cached
3. Return cached result OR execute and cache new result

Saves significant time on repeat queries (~5% of all queries).
"""

import re
import time
import threading
import hashlib
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Single cache entry with value and metadata."""
    value: Any
    created_at: float
    hits: int = 0


class QueryCache:
    """
    Thread-safe LRU cache with TTL for query results.

    Features:
    - TTL-based expiration (default 5 minutes)
    - LRU eviction when max size reached
    - Thread-safe operations
    - Hit/miss statistics
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 300,  # 5 minutes default
        enabled: bool = True
    ):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries to store
            ttl_seconds: Time-to-live for each entry in seconds
            enabled: Whether caching is enabled (can be toggled)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._enabled = enabled
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0

    @staticmethod
    def normalize_question(question: str) -> str:
        """
        Normalize question for better cache matching.

        For Tamil/non-ASCII text: Only basic normalization (whitespace, punctuation)
        to avoid incorrect cache collisions.

        For English text: More aggressive normalization for better hit rate.

        Args:
            question: Raw user question

        Returns:
            str: Normalized question for cache key generation
        """
        # Step 1: Lowercase and strip
        q = question.lower().strip()

        # Step 2: Remove trailing punctuation
        q = q.rstrip('?!.')

        # Step 3: Standardize whitespace
        q = ' '.join(q.split())

        # Check if question contains non-ASCII (Tamil, etc.)
        # If so, skip aggressive normalization to avoid cache collisions
        has_non_ascii = any(ord(c) > 127 for c in q)
        if has_non_ascii:
            # For Tamil/non-English: Only basic normalization
            # This prevents different Tamil queries from colliding
            return q

        # Step 4: Remove common filler words (ENGLISH ONLY)
        filler_words = [
            'please', 'can you', 'could you', 'show me', 'tell me',
            'what is', "what's", 'give me', 'i want to know', 'i need',
            'hey', 'hi', 'hello', 'thanks', 'thank you',
            'the', 'a', 'an'
        ]
        for filler in filler_words:
            # Only remove if it's a complete word (not part of another word)
            q = re.sub(r'\b' + re.escape(filler) + r'\b', '', q, flags=re.IGNORECASE)

        # Step 5: Standardize month abbreviations
        month_map = {
            'jan': 'january', 'feb': 'february', 'mar': 'march',
            'apr': 'april', 'jun': 'june', 'jul': 'july',
            'aug': 'august', 'sep': 'september', 'oct': 'october',
            'nov': 'november', 'dec': 'december'
        }
        for abbrev, full in month_map.items():
            q = re.sub(r'\b' + abbrev + r'\b', full, q)

        # Final cleanup: remove extra spaces created by removals
        q = ' '.join(q.split())

        return q

    @staticmethod
    def generate_cache_key(
        question: str,
        spreadsheet_id: str,
        table_name: Optional[str] = None,
        filters: Optional[list] = None
    ) -> str:
        """
        Generate a unique cache key for a query.

        Args:
            question: User's question text
            spreadsheet_id: Google Sheets ID
            table_name: Optional specific table name
            filters: Optional list of filter conditions

        Returns:
            str: MD5 hash as cache key
        """
        # Use enhanced normalization for better cache hit rate
        normalized_q = QueryCache.normalize_question(question)

        # Build key components
        key_parts = [spreadsheet_id, normalized_q]

        if table_name:
            key_parts.append(table_name)

        if filters:
            # Sort filters for consistent ordering
            sorted_filters = sorted(
                [str(f) for f in filters]
            )
            key_parts.extend(sorted_filters)

        # Create hash
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, cache_key: str) -> Tuple[bool, Any]:
        """
        Get a value from the cache.

        Args:
            cache_key: The cache key to look up

        Returns:
            Tuple of (hit: bool, value: Any)
            - If hit: (True, cached_value)
            - If miss: (False, None)
        """
        if not self._enabled:
            return False, None

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._misses += 1
                return False, None

            # Check TTL expiration
            if time.time() - entry.created_at > self._ttl_seconds:
                # Expired - remove and return miss
                del self._cache[cache_key]
                self._misses += 1
                return False, None

            # Cache hit - move to end (LRU)
            self._cache.move_to_end(cache_key)
            entry.hits += 1
            self._hits += 1

            return True, entry.value

    def set(self, cache_key: str, value: Any) -> None:
        """
        Store a value in the cache.

        Args:
            cache_key: The cache key
            value: The value to cache
        """
        if not self._enabled:
            return

        with self._lock:
            # Remove if exists (will re-add at end)
            if cache_key in self._cache:
                del self._cache[cache_key]

            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # Add new entry
            self._cache[cache_key] = CacheEntry(
                value=value,
                created_at=time.time()
            )

    def invalidate(self, cache_key: str) -> bool:
        """
        Remove a specific entry from the cache.

        Args:
            cache_key: The cache key to remove

        Returns:
            bool: True if entry was removed, False if not found
        """
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    def invalidate_by_spreadsheet(self, spreadsheet_id: str) -> int:
        """
        Invalidate all cache entries for a specific spreadsheet.
        Used when spreadsheet data is refreshed.

        Args:
            spreadsheet_id: The spreadsheet ID to invalidate

        Returns:
            int: Number of entries removed
        """
        with self._lock:
            # Find all keys containing this spreadsheet ID
            # (Keys start with spreadsheet_id in the hash input)
            # Since we use MD5, we can't easily reverse it,
            # so we clear all cache on refresh for simplicity
            count = len(self._cache)
            self._cache.clear()
            return count

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit rate
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
                "current_size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl_seconds,
                "enabled": self._enabled
            }

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the cache."""
        self._enabled = enabled

    def set_ttl(self, ttl_seconds: int) -> None:
        """Update the TTL (does not affect existing entries)."""
        self._ttl_seconds = ttl_seconds


# ============================================
# SINGLETON INSTANCE
# ============================================
_query_cache: Optional[QueryCache] = None
_cache_lock = threading.Lock()


def get_query_cache() -> QueryCache:
    """
    Get the singleton QueryCache instance.

    Returns:
        QueryCache: The global cache instance
    """
    global _query_cache

    if _query_cache is not None:
        return _query_cache

    with _cache_lock:
        if _query_cache is None:
            _query_cache = QueryCache()
        return _query_cache


def cache_query_result(
    question: str,
    spreadsheet_id: str,
    result: Any,
    table_name: Optional[str] = None,
    filters: Optional[list] = None
) -> str:
    """
    Convenience function to cache a query result.

    Args:
        question: User's question
        spreadsheet_id: Google Sheets ID
        result: The result to cache
        table_name: Optional table name for more specific caching
        filters: Optional filters for more specific caching

    Returns:
        str: The cache key used
    """
    cache = get_query_cache()
    cache_key = QueryCache.generate_cache_key(
        question, spreadsheet_id, table_name, filters
    )
    cache.set(cache_key, result)
    return cache_key


def get_cached_query_result(
    question: str,
    spreadsheet_id: str,
    table_name: Optional[str] = None,
    filters: Optional[list] = None
) -> Tuple[bool, Any]:
    """
    Convenience function to get a cached query result.

    Args:
        question: User's question
        spreadsheet_id: Google Sheets ID
        table_name: Optional table name
        filters: Optional filters

    Returns:
        Tuple of (hit: bool, result: Any)
    """
    cache = get_query_cache()
    cache_key = QueryCache.generate_cache_key(
        question, spreadsheet_id, table_name, filters
    )
    return cache.get(cache_key)


def invalidate_spreadsheet_cache(spreadsheet_id: str) -> int:
    """
    Invalidate all cache for a spreadsheet (e.g., on data refresh).

    Args:
        spreadsheet_id: The spreadsheet ID

    Returns:
        int: Number of entries cleared
    """
    cache = get_query_cache()
    return cache.invalidate_by_spreadsheet(spreadsheet_id)
