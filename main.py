import io
import sqlite3
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from db import delete_vin, get_all_cached_vins, get_cached_vin, init_db, insert_vin
from vin_utils import validate_vin
from vpic_client import VinDecodeServiceError, VinNotFoundError, decode_vin


class VinRequest(BaseModel):
    vin: str


class LookupResponse(BaseModel):
    vin: str
    make: str
    model: str
    model_year: str
    body_class: str
    cached: bool


class RemoveResponse(BaseModel):
    vin: str
    success: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"status": "testing ok"}


@app.post("/lookup", response_model=LookupResponse)
async def lookup(request: VinRequest) -> LookupResponse:
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


@app.get("/export")
async def export() -> Response:
    rows = get_all_cached_vins()

    columns = ["vin", "make", "model", "model_year", "body_class"]
    df = pd.DataFrame(rows, columns=columns)

    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)

    return Response(
        content=buffer.getvalue(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=export.parquet"},
    )


@app.post("/remove", response_model=RemoveResponse)
async def remove(request: VinRequest) -> RemoveResponse:
    normalized_vin = validate_vin(request.vin)

    try:
        delete_vin(normalized_vin)
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Failed to remove VIN from cache")

    return {"vin": normalized_vin, "success": True}
