from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logfire
import os
from jarit.db.database import Base, engine
from jarit.api.router import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="JarIt API", version="1.0.0")

logfire_token = os.environ.get("LOGFIRE_WRITE_TOKEN")
logfire.configure(token=logfire_token)
logfire.instrument_pydantic_ai()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("DOMAIN_NAME","http://localhost"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(router)
