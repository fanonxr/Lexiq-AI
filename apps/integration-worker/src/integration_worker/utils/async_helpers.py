"""Async helpers for Celery tasks.

This module provides utilities for running async code in Celery tasks,
which run in a synchronous context and need special handling for event loops.
"""

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Run an async coroutine in a Celery task.
    
    This function properly handles event loops in Celery workers, which can
    have issues with asyncio.run() when event loops already exist or are closed.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
        
    Raises:
        RuntimeError: If the event loop cannot be created or accessed
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        
        # Check if the loop is closed
        if loop.is_closed():
            # Loop is closed, create a new one
            logger.debug("Event loop is closed, creating new loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        # Check if the loop is running
        if loop.is_running():
            # If loop is already running, we can't use run_until_complete
            # This shouldn't happen in Celery tasks, but handle it gracefully
            logger.warning("Event loop is already running, creating new loop in thread")
            # Create a new event loop in a new thread
            import threading
            
            result = None
            exception = None
            
            def run_in_thread():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if exception:
                raise exception
            return result
        else:
            # Loop exists and isn't running - use it
            return loop.run_until_complete(coro)
    except RuntimeError as e:
        # No event loop exists or other runtime error
        if "no current event loop" in str(e).lower() or "no running event loop" in str(e).lower():
            # No event loop exists, create a new one
            logger.debug("No event loop exists, creating new loop")
            return asyncio.run(coro)
        else:
            # Some other runtime error, try to create a new loop
            logger.warning(f"Runtime error with event loop: {e}, creating new loop")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as inner_e:
                logger.error(f"Failed to create new event loop: {inner_e}")
                raise

