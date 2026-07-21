async def tool_middleware(handler, *args, **kwargs):
    
    return await handler(*args, **kwargs)