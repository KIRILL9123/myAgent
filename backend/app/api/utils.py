import asyncio
from fastapi import HTTPException
from typing import Callable, Any

async def run_api_tool(func: Callable, *args, **kwargs) -> Any:
    """
    Executes a blocking service/connector function in a separate thread,
    validates the return payload, and maps error dictionaries to FastAPI HTTPExceptions.
    """
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
        
        # If the result indicates an error in our unified format
        if isinstance(result, dict) and result.get("status") == "error":
            message = result.get("message", "Unknown error occurred.")
            
            # Map appropriate HTTP status codes based on message context
            if "not found" in message.lower() or "does not exist" in message.lower():
                status_code = 404
            elif "unauthorized" in message.lower() or "credentials" in message.lower():
                status_code = 401
            else:
                status_code = 400
                
            raise HTTPException(status_code=status_code, detail=message)
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
