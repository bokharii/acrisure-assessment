# SPEC

All VINs should be normalized before validation: trimmed of whitespace and uppercased.
VIN format: exactly 17 alphanumeric characters, excluding I, O, and Q (matches real world VIN conventions)

## /lookup
**Input:** `vin` (string)

**Behavior:**
1. Normalize input (trim whitespace, uppercase).
2. Validate against VIN format above. If the VIN is invalid, return a 400 error.
3. Check SQLite cache for this VIN.
4. If VIN is found, return cached record, `cached=true`.
5. If the VIN is not found, call vPIC `DecodeVinValues` for this VIN.
6. If vPIC returns valid data; store it in cache, return result, `cached=false`.
7. If vPIC returns no data for a well-formed VIN, return 404.
8. If the vPIC call fails or times out, return 502.

**Edge cases:**
- VIN that does not meet requirements (wrong length, non-alphanumeric, contains I/O/Q) should result in a 400 error
- VIN follows the standard convention but vPIC has no data should result in a 404, response: `{"detail": "No data found for VIN: <vin>"}`
- if vPIC API call fails or times out we should return a 502 error code
- Timeout threshold for the call should be 10 seconds

**Example of a successful response that hits our cache:**
```json
{
  "vin": "1HGCM82633A004352",
  "make": "string",
  "model": "string",
  "model_year": "string",
  "body_class": "string",
  "cached": true
}
```

**Example of a successful response that does not hit cache and is fetched directly from vPIC**
```json
{
  "vin": "1HGCM82633A004352",
  "make": "string",
  "model": "string",
  "model_year": "string",
  "body_class": "string",
  "cached": false
}
```

## /remove
**Input:** `vin` (string)

**Behavior:**
1. Normalize input (trim whitespace, uppercase).
2. Validate against VIN format above. If the VIN is invalid, return a 400 error.
3. If there exists a row in the SQLite cache that matches the inputted VIN, delete it.
4. If the delete completes without an error, return 'success=true', regardless of if that row actually existed (my design choice)
5. If the database operation itself fails, return a 500 error.

**Edge cases:**
- VIN that does not meet requirements (wrong length, non-alphanumeric, contains I/O/Q) should result in a 400 error
- Requesting to remove a VIN that doesn't exist in the cache should result in `success: true` (idempotent)
- If there is a database error during delete then we should return a 500 error

**Example response**
```json
{
  "vin": "1HGCM82633A004352",
  "success": true
}
```

## /export
**Input:** none

**Behavior:**
1. Query all the rows currently in the SQLite cache
2. Load results into a table structure (pandas DataFrame)
3. Write the table to Parquet format
4. Return the Parquet file as a binary download

**Edge cases:**
- If the cache is empty, represent this through a valid empty Parquet file (should have the correct columns but zero rows)

**Example response**
A binary file (application/octet-stream), served with Content-Disposition:attachment