"""
TTS Cache - Disk-based cache for Text-to-Speech audio.

Implements the TTS CACHING FLOW from the architecture:
1. Generate cache key: Hash(text + voice_id)
2. Check if audio cached on disk
3. Return cached audio OR generate and cache new audio

TTL: 24 hours (audio files are large, disk-based caching)
Saves 5-10 seconds on repeat TTS requests.
"""

import os
import time
import hashlib
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class TTSCache:
    """
    Disk-based cache for TTS audio files with TTL.

    Features:
    - Disk-based storage (audio files too large for memory)
    - 24-hour TTL by default
    - Automatic cleanup of expired files
    - Thread-safe operations
    - Hit/miss statistics
    """

    def __init__(
        self,
        cache_dir: str = "data_sources/cache/tts",
        ttl_seconds: int = 86400,  # 24 hours default
        max_size_mb: int = 500,  # 500MB max cache size
        enabled: bool = True
    ):
        """
        Initialize the TTS cache.

        Args:
            cache_dir: Directory to store cached audio files
            ttl_seconds: Time-to-live for each entry (24 hours default)
            max_size_mb: Maximum cache size in megabytes
            enabled: Whether caching is enabled
        """
        self._cache_dir = Path(cache_dir)
        self._ttl_seconds = ttl_seconds
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._enabled = enabled
        self._lock = threading.RLock()

        # Create cache directory if needed
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self._hits = 0
        self._misses = 0

        # Cleanup expired files on init
        self._cleanup_expired()

    @staticmethod
    def generate_cache_key(text: str, voice_id: str) -> str:
        """
        Generate a unique cache key for TTS audio.

        Args:
            text: The text to be spoken
            voice_id: The ElevenLabs voice ID

        Returns:
            str: MD5 hash as cache key
        """
        # Normalize text
        normalized_text = text.strip()

        # Create hash
        key_str = f"{voice_id}:{normalized_text}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self._cache_dir / f"{cache_key}.mp3"

    def _get_meta_path(self, cache_key: str) -> Path:
        """Get the metadata file path for a cache key."""
        return self._cache_dir / f"{cache_key}.meta"

    def get(self, cache_key: str) -> Tuple[bool, Optional[bytes]]:
        """
        Get cached audio data.

        Args:
            cache_key: The cache key to look up

        Returns:
            Tuple of (hit: bool, audio_data: Optional[bytes])
        """
        if not self._enabled:
            return False, None

        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        with self._lock:
            if not cache_path.exists():
                self._misses += 1
                return False, None

            # Check TTL
            if meta_path.exists():
                try:
                    created_at = float(meta_path.read_text().strip())
                    if time.time() - created_at > self._ttl_seconds:
                        # Expired - remove and return miss
                        self._remove_entry(cache_key)
                        self._misses += 1
                        return False, None
                except (ValueError, OSError):
                    # Corrupted metadata - remove entry
                    self._remove_entry(cache_key)
                    self._misses += 1
                    return False, None
            else:
                # No metadata - use file mtime
                file_mtime = cache_path.stat().st_mtime
                if time.time() - file_mtime > self._ttl_seconds:
                    self._remove_entry(cache_key)
                    self._misses += 1
                    return False, None

            # Cache hit
            try:
                audio_data = cache_path.read_bytes()
                self._hits += 1
                return True, audio_data
            except OSError:
                self._misses += 1
                return False, None

    def set(self, cache_key: str, audio_data: bytes) -> bool:
        """
        Store audio data in the cache.

        Args:
            cache_key: The cache key
            audio_data: The audio bytes to cache

        Returns:
            bool: True if successfully cached
        """
        if not self._enabled:
            return False

        with self._lock:
            # Check if we need to make room
            self._ensure_space(len(audio_data))

            cache_path = self._get_cache_path(cache_key)
            meta_path = self._get_meta_path(cache_key)

            try:
                # Write audio file
                cache_path.write_bytes(audio_data)

                # Write metadata (creation time)
                meta_path.write_text(str(time.time()))

                return True
            except OSError as e:
                print(f"TTS cache write error: {e}")
                return False

    def _remove_entry(self, cache_key: str) -> None:
        """Remove a cache entry (audio + metadata)."""
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        except OSError:
            pass

    def _ensure_space(self, needed_bytes: int) -> None:
        """Ensure there's enough space for new entry."""
        current_size = self._get_cache_size()

        if current_size + needed_bytes <= self._max_size_bytes:
            return

        # Need to evict - get all files sorted by age
        files = []
        for f in self._cache_dir.glob("*.mp3"):
            meta_path = self._cache_dir / f"{f.stem}.meta"
            if meta_path.exists():
                try:
                    created_at = float(meta_path.read_text().strip())
                except (ValueError, OSError):
                    created_at = f.stat().st_mtime
            else:
                created_at = f.stat().st_mtime

            files.append((f.stem, created_at, f.stat().st_size))

        # Sort by age (oldest first)
        files.sort(key=lambda x: x[1])

        # Evict until we have space
        for cache_key, _, size in files:
            if current_size + needed_bytes <= self._max_size_bytes:
                break
            self._remove_entry(cache_key)
            current_size -= size

    def _get_cache_size(self) -> int:
        """Get total size of cached files in bytes."""
        total = 0
        for f in self._cache_dir.glob("*.mp3"):
            try:
                total += f.stat().st_size
            except OSError:
                pass
        return total

    def _cleanup_expired(self) -> int:
        """Remove all expired entries."""
        removed = 0
        now = time.time()

        for cache_path in self._cache_dir.glob("*.mp3"):
            cache_key = cache_path.stem
            meta_path = self._get_meta_path(cache_key)

            if meta_path.exists():
                try:
                    created_at = float(meta_path.read_text().strip())
                    if now - created_at > self._ttl_seconds:
                        self._remove_entry(cache_key)
                        removed += 1
                except (ValueError, OSError):
                    self._remove_entry(cache_key)
                    removed += 1
            else:
                # Use file mtime
                try:
                    if now - cache_path.stat().st_mtime > self._ttl_seconds:
                        self._remove_entry(cache_key)
                        removed += 1
                except OSError:
                    pass

        return removed

    def clear(self) -> int:
        """Clear all cache entries."""
        removed = 0
        with self._lock:
            for f in self._cache_dir.glob("*"):
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass
            self._hits = 0
            self._misses = 0
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            cache_size = self._get_cache_size()

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
                "cache_size_mb": round(cache_size / (1024 * 1024), 2),
                "max_size_mb": self._max_size_bytes / (1024 * 1024),
                "ttl_hours": self._ttl_seconds / 3600,
                "enabled": self._enabled
            }

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the cache."""
        self._enabled = enabled


# ============================================
# SINGLETON INSTANCE
# ============================================
_tts_cache: Optional[TTSCache] = None
_cache_lock = threading.Lock()


def get_tts_cache() -> TTSCache:
    """
    Get the singleton TTSCache instance.

    Returns:
        TTSCache: The global TTS cache instance
    """
    global _tts_cache

    if _tts_cache is not None:
        return _tts_cache

    with _cache_lock:
        if _tts_cache is None:
            _tts_cache = TTSCache()
        return _tts_cache


def cache_tts_audio(text: str, voice_id: str, audio_data: bytes) -> str:
    """
    Convenience function to cache TTS audio.

    Args:
        text: The text that was spoken
        voice_id: The voice ID used
        audio_data: The audio bytes

    Returns:
        str: The cache key used
    """
    cache = get_tts_cache()
    cache_key = TTSCache.generate_cache_key(text, voice_id)
    cache.set(cache_key, audio_data)
    return cache_key


def get_cached_tts_audio(text: str, voice_id: str) -> Tuple[bool, Optional[bytes]]:
    """
    Convenience function to get cached TTS audio.

    Args:
        text: The text to be spoken
        voice_id: The voice ID

    Returns:
        Tuple of (hit: bool, audio_data: Optional[bytes])
    """
    cache = get_tts_cache()
    cache_key = TTSCache.generate_cache_key(text, voice_id)
    return cache.get(cache_key)
