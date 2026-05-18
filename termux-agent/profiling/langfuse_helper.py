import os
import functools
import logging

try:
    # Langfuse 4.x SDK integration
    from langfuse import observe, get_client
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False

def safe_observe(*args, **kwargs):
    """
    A wrapper around langfuse.observe that does nothing if langfuse is not installed
    or if environment variables are missing.
    """
    if HAS_LANGFUSE and os.getenv("LANGFUSE_PUBLIC_KEY"):
        return observe(*args, **kwargs)
    else:
        def dummy_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return dummy_decorator

def update_trace(metadata=None, tags=None, input_tokens=0, output_tokens=0, name=None, session_id=None, user_id=None):
    """Update current langfuse context using the client (v4.x compatible)."""
    if HAS_LANGFUSE and os.getenv("LANGFUSE_PUBLIC_KEY"):
        try:
            client = get_client()
            # Update the current span/observation
            client.update_current_span(
                name=name,
                metadata=metadata,
                input=input_tokens if input_tokens > 0 else None,
                output=output_tokens if output_tokens > 0 else None
            )
            # In 4.x, tags are usually set via the client's internal state or at start.
            # We skip detailed trace-level updates here to keep it simple and robust.
        except Exception as e:
            # Silent fail to prevent agent crashes
            pass

def flush_langfuse():
    """Flush any pending traces to Langfuse."""
    if HAS_LANGFUSE and os.getenv("LANGFUSE_PUBLIC_KEY"):
        try:
            get_client().flush()
        except:
            pass

def set_session_id(session_id):
    """Set the session ID for the current trace (not directly exposed in 4.x Client yet)."""
    # Note: In 4.x @observe, session_id is typically passed as a kwarg to the decorated function.
    pass
