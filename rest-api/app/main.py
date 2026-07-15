from fastapi import FastAPI
from contextlib import asynccontextmanager
from .api.routes import router as api_router
from .api.chat_websocket import router as ws_router
import motor.motor_asyncio
import os

async def ensure_indexes(db):
    # Indexing nur für Username und Invite-Code, um Dopplungen zu vermeiden
    await db["users"].create_index("username", unique=True)
    await db["chats"].create_index("invite_code", unique=True)
    # bei anderen Attributen können doppelte Werte vorkommen

@asynccontextmanager
async def lifespan(application: FastAPI):
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    application.mongodb_client = mongo_client
    application.database = mongo_client["laika-rest-api"]
    print("LOG: mongoDB verbunden")
    await ensure_indexes(application.database)
    #
    yield
    # bei Shutdown dei Verbindung trennen
    mongo_client.close()
    print("LOG: mongoDB getrennt")

app = FastAPI(title="Rest-API for Laika", lifespan=lifespan)

# Router einbinden
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")
