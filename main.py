import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import delete_vin, get_cached_vin, init_db, insert_vin
from vin_utils import validate_vin
from vpic_client import VinDecodeServiceError, VinNotFoundError, decode_vin


class VinRequest(BaseModel):
    vin: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"status": "testing ok"}


@app.post("/lookup")
async def lookup(request: VinRequest) -> dict:
    normalized_vin = validate_vin(request.vin)

    cached = get_cached_vin(normalized_vin)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        data = await decode_vin(normalized_vin)
    except VinNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"No data found for VIN: {normalized_vin}"
        )
    except VinDecodeServiceError:
        raise HTTPException(status_code=502, detail="vPIC service unavailable")

    insert_vin(normalized_vin, data)

    return {
        "vin": normalized_vin,
        "make": data["make"],
        "model": data["model"],
        "model_year": data["model_year"],
        "body_class": data["body_class"],
        "cached": False,
    }


@app.post("/remove")
async def remove(request: VinRequest) -> dict:
    normalized_vin = validate_vin(request.vin)

    try:
        delete_vin(normalized_vin)
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Failed to remove VIN from cache")

    return {"vin": normalized_vin, "success": True}
