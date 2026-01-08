from fastapi import FastAPI
from app.routes import upload, query, exit
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()


origins = [
    "http://localhost:8080",
    os.getenv("FRONTEND_URL"),  # read from .env
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(query.router)
app.include_router(exit.router)
