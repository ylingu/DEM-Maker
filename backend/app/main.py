from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import items

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+$",
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
app.include_router(items.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/greet/{name}")
def greet(name: str):
    return {"message": f"Hello, {name}!"}
