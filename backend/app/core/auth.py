from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import jwt
from jwt import PyJWKClient
from app.core.config import settings

security = HTTPBearer()

# Clerk JWKS client with cache refresh
jwks_client = PyJWKClient(
    f"https://{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json",
    cache_keys=True,
    max_cached_keys=16,
    cache_jwk_set=300  # Cache for 5 minutes, then refresh
)

async def _verify_jwt_token(token: str) -> dict:
    """Shared JWT verification logic"""
    try:
        # Get the signing key from Clerk's JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode the token with correct issuer
        # Add leeway to tolerate clock skew between client and server (up to 60 seconds)
        expected_issuer = f"https://{settings.CLERK_JWT_ISSUER}"
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            leeway=60,  # Allow 60 seconds of clock skew
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

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return await _verify_jwt_token(credentials.credentials)

async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Try to get email from token, but it might not be there if JWT template isn't configured
    email = token_payload.get("email")
    name = token_payload.get("name")
    
    # If email is missing from JWT, fetch it from Clerk's API
    if not email:
        try:
            # Fetch user details from Clerk API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    user_data = response.json()
                    email = user_data.get("email_addresses", [{}])[0].get("email_address")
                    first_name = user_data.get('first_name', '') or ''
                    last_name = user_data.get('last_name', '') or ''
                    name = f"{first_name} {last_name}".strip()
                    if name == '' or name == 'None None' or 'None' in name:
                        name = None
                else:
                    # Failed to get user data from Clerk API
                    pass
        except Exception:
            # Error fetching from Clerk API, continue with None email
            pass
    
    return {
        "id": user_id,
        "email": email,
        "name": name,
    }

async def get_current_user_sse(request: Request, token: Optional[str] = Query(None)) -> dict:
    """
    Get current user for SSE endpoints that support both header and query param auth.
    EventSource doesn't support custom headers, so we allow token via query parameter.
    """
    jwt_token = None
    
    # Try to get token from query parameter first (for SSE)
    if token:
        jwt_token = token
    else:
        # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]  # Remove "Bearer " prefix
    
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )
    
    # Verify the token using shared logic
    payload = await _verify_jwt_token(jwt_token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Try to get email from token, but it might not be there if JWT template isn't configured
    email = payload.get("email")
    name = payload.get("name")
    
    # If email is missing from JWT, fetch it from Clerk's API
    if not email:
        try:
            # Fetch user details from Clerk API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    user_data = response.json()
                    email = user_data.get("email_addresses", [{}])[0].get("email_address")
                    first_name = user_data.get('first_name', '') or ''
                    last_name = user_data.get('last_name', '') or ''
                    name = f"{first_name} {last_name}".strip()
                    if name == '' or name == 'None None' or 'None' in name:
                        name = None
                else:
                    # Failed to get user data from Clerk API
                    pass
        except Exception:
            # Error fetching from Clerk API, continue with None email
            pass
    
    return {
        "id": user_id,
        "email": email,
        "name": name,
    }

class RequireAuth:
    def __init__(self, min_credits: int = 0):
        self.min_credits = min_credits
    
    async def __call__(self, current_user: dict = Depends(get_current_user)):
        # TODO: Check user credits from database
        return current_user