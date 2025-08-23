from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
from jwt import PyJWKClient
from app.core.config import settings

security = HTTPBearer()

# Clerk JWKS client
jwks_client = PyJWKClient(f"https://{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    
    try:
        # Get the signing key from Clerk's JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_JWT_ISSUER,
            options={"verify_aud": False}  # Clerk doesn't use aud claim
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return {
        "id": user_id,
        "email": token_payload.get("email"),
        "name": token_payload.get("name"),
    }

class RequireAuth:
    def __init__(self, min_credits: int = 0):
        self.min_credits = min_credits
    
    async def __call__(self, current_user: dict = Depends(get_current_user)):
        # TODO: Check user credits from database
        return current_user