from fastapi import FastAPI, Request, HTTPException, status
from routers.auth import router
from routers.scissors import scissors_router
from fastapi.staticfiles import StaticFiles
from fastapi_cache.decorator import cache
from fastapi_cache.backends.memory import InMemoryCacheBackend
from fastapi_cache import FastAPICache
from asgi_caches.middleware import CacheMiddleware

cache_backend = InMemoryCacheBackend()

app = FastAPI()

cache = FastAPICache(backend=cache_backend)
app.add_middleware(CacheMiddleware, cache=cache, key_prefix="scissor")

app.mount("/static", StaticFiles(directory="static"), name="static")

rate_limit = FastAPICache(backend=InMemoryCacheBackend())

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    key = f"rate_limit_{request.client.host}"
    current_requests = cache.get(key, count=0)
    if current_requests >= 5:  # Adjust limit as needed
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )
    cache.set(key, current_requests + 1, expire=60)  # Adjust expiration as needed
    response = await call_next(request)
    return response

# Include the router
app.include_router(router)
app.include_router(scissors_router)
