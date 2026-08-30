# Notes

## Background

Before diving into any sort of coding, the very first thing I did was work through the requirements and identify any potential edge cases I would have to cover. To be completely honest, the scope of the project was already well-defined in the requirements but I wanted to approach it in a way that reflects how I currently work on features/tasks.

I've also been looking into optimizing my own workflow using AI, and part of that has been adopting [Spec-Driven Development (SDD)](https://www.ibm.com/think/topics/spec-driven-development). So I made sure to write up my own `SPEC.md`, which essentially outlines all of the requirements and constraints I not only wanted myself to adhere to, but the agent as well.

Speaking of agents, the main AI tool I used throughout the process was Cursor. In terms of models, I stuck to Sonnet 4.6 as I've found it to be very reliable especially when giving it explicit do's and don'ts. I also created a `.cursorrules` file to give the agent a bit more context as well as establish some standards before writing a single line of code.

## Key decisions

**VIN Validation.** VINs are normalized (trimmed, uppercased) _before_ validation, not after. I made sure that a VIN with stray whitespace or lowercase letters is still valid once cleaned up, so validating the raw input first would incorrectly reject it. I initially had Cursor generate the validator using a regex; I rewrote it as explicit checks (length, alphanumeric, excluded letters) instead. The regex was more compact and honestly cool to look at but harder to read at a glance. I opted instead for the explicit checks as it was something I could unit test and explain with complete confidence.

**vPIC error handling.** I noticed that vPIC returns `200` even for VINs it has no data on, so "not found" has to be detected by checking whether the decoded fields come back empty, not by relying on the HTTP status. Therefore I decided to create two custom exceptions (`VinNotFoundError`, `VinDecodeServiceError`) rather than raising `HTTPException` directly from the vPIC client — this keeps the client decoupled from FastAPI (it's just "call an API and get data or fail"), independently testable, and leaves the route as the only place that decides what HTTP status a given failure becomes.

**`/remove` is idempotent.** When thinking through the remove route, I had to decide what would happen when trying to remove a VIN that did not exist in cache. Should it return false (because the VIN doesn't exist) or true because the end state is the same? I decided to go with the latter since it would maintain idempotency. Removing a VIN that was never cached still returns `success: true` — the end state (VIN not in cache) is the same either way, so it isn't a failure. A delete failure on our side (for example the SQLite operation itself throwing an error) surfaces as a 500 response rather than a success: false, there's no scenario where this route returns a 200 with success: false in the body.

**Plain `INSERT`, not `INSERT OR REPLACE`.** Cursor initially suggested `INSERT OR REPLACE` as a safety net against two concurrent requests for the same uncached VIN. This was something I decided to push back on, since by the time `insert_vin` is called, we've already confirmed via the cache check that no row exists. So a plain `INSERT` is correct for this flow. `INSERT OR REPLACE` would be optimal under real concurrent traffic, which is out of scope in the context of this assignment.

**Shared HTTP client.** Originally `decode_vin` created a new `httpx.AsyncClient` per call. Later, when looking for potential optimizations I decided to move client creation into the FastAPI `lifespan` (alongside the DB init) so one client is reused across requests, and switched `/lookup` to pull it via [dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/) (`Depends`) rather than reaching into `app.state` directly. This also made mocking a LOT easier for tests.

**Testing.** All three routes and the vPIC client have real `pytest` coverage (mocked vPIC calls, no real network access, and an isolated temp SQLite file per test via `monkeypatch` so the suite never touches the real `cache.db`). I wrote the first route test and the test fixtures by hand to make sure I actually understood the mocking/isolation setup. Once that was done, I guided Cursor in creating the rest of the test suites using the response shapes and edge cases I outlined earlier in `SPEC.md`.

## What I'd change at scale

- **Deploying as-is.** This would run today as a single process, with `cache.db` sitting on local disk. For the purposes of this assignment I believe that's fine, but it breaks the moment you run more than one since each instance would have its own separate cache file, so a VIN cached on one wouldn't show up on another. I'd need to move to a shared database like Postgres before this could run on multiple replicas or a platform without persistent local disk like Vercel.
- **Structured logging** around cache hits/misses and vPIC call latency — useful in production, not really testable/necessary at this scale.
- **Batch VIN lookups.** I saw that the vPIC API actually supports decoding multiple VINs in one call, which would reduce the number of round trips for a bulk use case.

## Known gaps

- `main.py` keeps all three routes and their request/response models in one file. I considered splitting into an APIRouter-based structure, but for just three straightforward routes I believe that would just overcomplicate things. However, that's something I would revisit if more routes needed to be added in the future.
- `GET /export` doesn't currently catch DB read failures the way `/lookup` and `/remove` do. I didn't define an error case for it in SPEC.md since it's a low-risk read, but it's the one inconsistency I'm aware of.
