from fastapi import FastAPI, Request, HTTPException, status
from routers.auth import router
from routers.scissors import scissors_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the router
app.include_router(router)
app.include_router(scissors_router)