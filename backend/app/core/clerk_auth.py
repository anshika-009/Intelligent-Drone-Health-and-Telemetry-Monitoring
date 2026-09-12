import os

import jwt
from fastapi import HTTPException, Request, WebSocket
from jwt import PyJWKClient
from dotenv import load_dotenv
load_dotenv()

CLERK_JWKS_URL = os.environ.get('CLERK_JWKS_URL', '')
_jwk_client = PyJWKClient(CLERK_JWKS_URL) if CLERK_JWKS_URL else None

def _verify(token: str) -> dict:
    if _jwk_client is None:
        raise HTTPException(500, 'Server auth is not configured (missing CLERK_JWKS_URL env var).')
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=['RS256'], options={'verify_aud': False})
    except jwt.PyJWTError as error:
        raise HTTPException(401, f'Invalid or expired session: {error}') from error


def get_current_user(request: Request) -> str:
    """FastAPI dependency for REST endpoints. Add `Depends(get_current_user)`
    to any route that should require sign-in. Returns the Clerk user ID."""
    auth_header = request.headers.get('authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(401, 'Sign in required.')
    payload = _verify(auth_header.removeprefix('Bearer '))
    return payload['sub']


async def get_current_user_ws(websocket: WebSocket) -> str | None:
    """Auth check for WebSocket endpoints. Call this at the top of the
    handler, before accept(). Returns the Clerk user ID, or None if the
    connection was rejected (the socket is already closed in that case)."""
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=4401)
        return None
    try:
        payload = _verify(token)
        return payload['sub']
    except HTTPException:
        await websocket.close(code=4401)
        return None