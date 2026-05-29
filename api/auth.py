import httpx
from fastapi import Header, HTTPException, Request

from config import API_KEY, AUTHELIA_INTERNAL_URL


async def require_auth(
    request: Request,
    x_api_key: str | None = Header(None),
) -> None:
    # Fast path: API key provided
    if x_api_key is not None:
        if API_KEY and x_api_key == API_KEY:
            return
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Fallback: validate Authelia session cookie
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{AUTHELIA_INTERNAL_URL}/authelia/api/verify",
                headers={
                    "Cookie": request.headers.get("cookie", ""),
                    "X-Original-URL": str(request.url),
                    "Host": request.headers.get("host", ""),
                    "X-Forwarded-For": request.headers.get("x-forwarded-for", ""),
                    "X-Forwarded-Proto": request.headers.get("x-forwarded-proto", "http"),
                    "X-Forwarded-Method": request.method,
                },
                timeout=5.0,
            )
        if resp.status_code == 200:
            return
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    raise HTTPException(
        status_code=401,
        detail="Not authenticated — provide X-API-Key header or log in via Authelia",
    )
