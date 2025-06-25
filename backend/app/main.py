from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import drone, image, process, websockets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://tauri.localhost"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_credentials=True,
    allow_headers=[
        "Content-Type",
        "Accept",
        "Origin",
    ],
)
app.include_router(drone.router)
app.include_router(image.router)
app.include_router(process.router)
app.include_router(websockets.router)
