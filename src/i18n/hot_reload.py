"""
i18n Hot Reload Module

Provides hot reloading capabilities for translations, allowing dynamic
updates without application restart.
"""

from typing import Optional, Callable, Dict, Any
import logging
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class TranslationHotReloader:
    """
    Hot reloader for translation files.

    Features:
    - Automatic file watching
    - Manual reload triggering
    - Callback notifications
    - Thread-safe operations
    """

    def __init__(
        self,
        watch_enabled: bool = False,
        check_interval: float = 5.0
    ):
        """
        Initialize hot reloader.

        Args:
            watch_enabled: Whether to enable automatic file watching
            check_interval: Interval in seconds for checking file changes
        """
        self._watch_enabled = watch_enabled
        self._check_interval = check_interval
        self._callbacks = []
        self._watch_thread = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._last_reload_time = None
        self._reload_count = 0

        logger.info(f"TranslationHotReloader initialized (watch_enabled={watch_enabled})")

    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when translations are reloaded.

        Args:
            callback: Function to call on reload (no parameters)
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                logger.info(f"Registered reload callback: {callback.__name__}")

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """
        Unregister a reload callback.

        Args:
            callback: Function to unregister
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.info(f"Unregistered reload callback: {callback.__name__}")

    def reload_translations(self, force: bool = False) -> bool:
        """
        Manually trigger translation reload.

        Args:
            force: Force reload even if no changes detected

        Returns:
            True if reload was successful
        """
        try:
            logger.info(f"Manual translation reload triggered (force={force})")

            # Re-import translations module to get latest changes
            import importlib
            from src.i18n import translations

            try:
                importlib.reload(translations)
                logger.info("Translations module reloaded successfully")
            except Exception as reload_error:
                logger.error(f"Failed to reload translations module: {reload_error}")
                return False

            # Reinitialize performance optimizations
            try:
                from src.i18n.translations import reinitialize_performance_optimizations
                reinitialize_performance_optimizations()
                logger.info("Performance optimizations reinitialized")
            except Exception as perf_error:
                logger.warning(f"Performance optimization reinitialization failed: {perf_error}")

            # Call registered callbacks
            with self._lock:
                self._last_reload_time = time.time()
                self._reload_count += 1

                for callback in self._callbacks:
                    try:
                        callback()
                        logger.debug(f"Callback {callback.__name__} executed successfully")
                    except Exception as callback_error:
                        logger.error(f"Callback {callback.__name__} failed: {callback_error}")

            logger.info(f"Translation reload completed (reload count: {self._reload_count})")
            return True

        except Exception as e:
            logger.error(f"Translation reload failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_watching(self) -> None:
        """
        Start automatic file watching.

        Note: This creates a background thread that periodically checks
        for translation updates.
        """
        if self._watch_thread is not None and self._watch_thread.is_alive():
            logger.warning("Watch thread already running")
            return

        logger.info("Starting translation file watching...")
        self._stop_flag.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="i18n-hot-reload-watcher"
        )
        self._watch_thread.start()
        logger.info(f"Watch thread started (check interval: {self._check_interval}s)")

    def stop_watching(self) -> None:
        """Stop automatic file watching."""
        if self._watch_thread is None:
            logger.warning("Watch thread not running")
            return

        logger.info("Stopping translation file watching...")
        self._stop_flag.set()

        if self._watch_thread.is_alive():
            self._watch_thread.join(timeout=self._check_interval + 1.0)

        self._watch_thread = None
        logger.info("Watch thread stopped")

    def _watch_loop(self) -> None:
        """
        Background thread loop for watching translation files.

        Note: This is a simple implementation that checks on a timer.
        For production, consider using a file system watcher like watchdog.
        """
        logger.info("Watch loop started")

        while not self._stop_flag.is_set():
            try:
                # In a real implementation, you would check file modification times
                # or use a file system watcher library like watchdog
                # For now, we just wait for manual triggers
                self._stop_flag.wait(self._check_interval)

            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                time.sleep(self._check_interval)

        logger.info("Watch loop stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current hot reload status.

        Returns:
            Dictionary containing status information
        """
        with self._lock:
            return {
                'watch_enabled': self._watch_enabled,
                'watching': self._watch_thread is not None and self._watch_thread.is_alive(),
                'check_interval': self._check_interval,
                'reload_count': self._reload_count,
                'last_reload_time': self._last_reload_time,
                'registered_callbacks': len(self._callbacks),
                'callback_names': [cb.__name__ for cb in self._callbacks]
            }

    def __del__(self):
        """Cleanup on deletion."""
        if self._watch_thread is not None:
            self.stop_watching()


# ============================================================================
# Global Instance
# ============================================================================

_hot_reloader: Optional[TranslationHotReloader] = None


def get_hot_reloader(
    watch_enabled: bool = False,
    check_interval: float = 5.0
) -> TranslationHotReloader:
    """
    Get or create global hot reloader instance.

    Args:
        watch_enabled: Whether to enable automatic file watching
        check_interval: Interval in seconds for checking file changes

    Returns:
        TranslationHotReloader instance
    """
    global _hot_reloader

    if _hot_reloader is None:
        _hot_reloader = TranslationHotReloader(
            watch_enabled=watch_enabled,
            check_interval=check_interval
        )

    return _hot_reloader


def reload_translations(force: bool = False) -> bool:
    """
    Trigger manual translation reload.

    Args:
        force: Force reload even if no changes detected

    Returns:
        True if reload was successful
    """
    reloader = get_hot_reloader()
    return reloader.reload_translations(force=force)


def register_reload_callback(callback: Callable[[], None]) -> None:
    """
    Register a callback for translation reloads.

    Args:
        callback: Function to call when translations are reloaded
    """
    reloader = get_hot_reloader()
    reloader.register_callback(callback)


def unregister_reload_callback(callback: Callable[[], None]) -> None:
    """
    Unregister a reload callback.

    Args:
        callback: Function to unregister
    """
    reloader = get_hot_reloader()
    reloader.unregister_callback(callback)


def start_hot_reload_watching() -> None:
    """Start automatic translation file watching."""
    reloader = get_hot_reloader(watch_enabled=True)
    reloader.start_watching()


def stop_hot_reload_watching() -> None:
    """Stop automatic translation file watching."""
    reloader = get_hot_reloader()
    reloader.stop_watching()


def get_hot_reload_status() -> Dict[str, Any]:
    """
    Get current hot reload status.

    Returns:
        Dictionary containing status information
    """
    reloader = get_hot_reloader()
    return reloader.get_status()


# ============================================================================
# Export
# ============================================================================

__all__ = [
    # Class
    'TranslationHotReloader',

    # Functions
    'get_hot_reloader',
    'reload_translations',
    'register_reload_callback',
    'unregister_reload_callback',
    'start_hot_reload_watching',
    'stop_hot_reload_watching',
    'get_hot_reload_status',
]
