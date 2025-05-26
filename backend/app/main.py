from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import drone, websockets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+$",
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
app.include_router(drone.router)
app.include_router(websockets.router)
