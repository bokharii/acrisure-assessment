# Acrisure Assessment — VIN Decoder API

A simple FastAPI backend that decodes VINs using the [vPIC API](https://vpic.nhtsa.dot.gov/api/), backed by a SQLite cache.

## Table of Contents

- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the service](#running-the-service)
- [Running tests](#running-tests)
- [API](#api)
  - [`POST /lookup`](#post-lookup)
  - [`POST /remove`](#post-remove)
  - [`GET /export`](#get-export)
- [Notes](#notes)

## Requirements

- Python 3.12+ (a `.python-version` file is included for [pyenv](https://github.com/pyenv/pyenv) users)

## Project Structure

- `main.py` — where the FastAPI app, route definitions, and request/response models all live
- `db.py` — handles SQLite connection and cache read/write functions
- `vin_utils.py` — takes care of VIN normalization and validation
- `vpic_client.py` — vPIC API client (async, with custom exceptions for not-found vs. service errors)
- `test_*.py` — tests (covering validation, the vPIC client, and all three routes)
- `SPEC.md` — requirements and constraints outlined before I started my implementation
- `NOTES.md` — my personal thought process throughout the implementation

## Getting Started

1. Clone the repo and enter the project directory:

   ```bash
   git clone https://github.com/bokharii/acrisure-assessment.git
   cd acrisure-assessment
   ```

2. (If using pyenv) install and select the pinned Python version:

   ```bash
   pyenv install 3.12.3
   pyenv local 3.12.3
   ```

3. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Running the service

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. FastAPI also provides interactive docs available through SwaggerUI. This can be found at `http://127.0.0.1:8000/docs`, and you can test out each route individually.

Also on startup, `cache.db` (a SQLite file) is created automatically if it doesn't already exist.

## Running tests

```bash
pytest -v
```

The test suite uses a temporary, isolated database and mocks the vPIC client, so your local `cache.db` is never touched, and no real network calls are made.

## API

### `POST /lookup`

Decodes a VIN, using the cache if available. The VIN is trimmed and uppercased before validation, so `" 1hgcm82633a004352 "` is accepted the same as `1HGCM82633A004352`.

**Request:**

```json
{ "vin": "1HGCM82633A004352" }
```

```bash
curl -X POST http://127.0.0.1:8000/lookup \
  -H "Content-Type: application/json" \
  -d '{"vin": "1HGCM82633A004352"}'
```

**Response (first call, not yet cached):**

```json
{
  "vin": "1HGCM82633A004352",
  "make": "HONDA",
  "model": "Accord",
  "model_year": "2003",
  "body_class": "Coupe",
  "cached": false
}
```

Calling `/lookup` again with the same VIN returns the same data from the cache, with `"cached": true` — no second request to vPIC is made.

**Errors:**

- `400` — VIN is not exactly 17 alphanumeric characters (after trimming and uppercasing), or contains `I`, `O`, or `Q`
- `404` — VIN is well-formed but vPIC has no data for it
- `502` — vPIC request failed, timed out, or returned an unusable response
- `500` — cache read/write failed

### `POST /remove`

Removes a VIN from the cache, if present. Idempotent — returns `success: true` whether or not the VIN was actually cached.

**Request:**

```json
{ "vin": "1HGCM82633A004352" }
```

```bash
curl -X POST http://127.0.0.1:8000/remove \
  -H "Content-Type: application/json" \
  -d '{"vin": "1HGCM82633A004352"}'
```

**Response:**

```json
{ "vin": "1HGCM82633A004352", "success": true }
```

**Errors:**

- `400` — invalid VIN format
- `500` — cache delete failed

### `GET /export`

Downloads all cached VINs as a Parquet file (`application/octet-stream`, triggers a file download). Will return a valid, empty Parquet file (correct columns, zero rows) if the cache is empty at the time of download.

```bash
curl -o export.parquet http://127.0.0.1:8000/export
```

This writes the response directly to `export.parquet` in your current directory.

## Notes

See [NOTES.md](./NOTES.md) for design decisions and tradeoffs.