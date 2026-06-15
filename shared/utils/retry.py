import asyncio
from functools import wraps
from loguru import logger

def async_retry(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        raise e
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} after error: {e}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator\n