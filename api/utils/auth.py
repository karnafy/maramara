"""Auth utilities: Supabase JWT verification + Flask decorators."""
from __future__ import annotations

from functools import wraps
from typing import Callable

import jwt
from flask import g, request, session

from config import get_settings
from utils.errors import AuthError, ForbiddenError
from db.supabase_client import get_admin_client


def _extract_token() -> str | None:
    """Extract JWT from either Authorization header (mobile) or session (web)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    if "access_token" in session:
        return session["access_token"]
    return None


def verify_supabase_jwt(token: str) -> dict:
    """Verify Supabase-issued JWT and return claims."""
    settings = get_settings()
    try:
        # Supabase signs with HS256 using the JWT secret.
        # If secret not configured, fall back to verifying via admin client (slower).
        if settings.supabase_jwt_secret:
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return claims
        # Fallback: verify by asking Supabase who this user is
        admin = get_admin_client()
        user_resp = admin.auth.get_user(token)
        if user_resp and user_resp.user:
            return {
                "sub": user_resp.user.id,
                "email": user_resp.user.email,
                "role": "authenticated",
            }
        raise AuthError("Invalid token")
    except jwt.PyJWTError as e:
        raise AuthError(f"Token validation failed: {e}") from e
    except AuthError:
        raise
    except Exception as e:
        # Supabase client can raise AuthApiError (expired/invalid) that isn't a PyJWTError.
        # Normalise those to our AuthError so the web layer can redirect to /auth/login.
        msg = str(e)
        if "expired" in msg.lower():
            raise AuthError("Session expired") from e
        raise AuthError(f"Token validation failed: {msg}") from e


def require_auth(f: Callable) -> Callable:
    """Decorator: ensure caller presents a valid Supabase JWT."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            raise AuthError("Authentication required")
        claims = verify_supabase_jwt(token)
        g.user_id = claims["sub"]
        g.user_email = claims.get("email")
        g.access_token = token
        g.claims = claims
        return f(*args, **kwargs)
    return wrapper


def require_role(*allowed_roles: str) -> Callable:
    """Decorator: ensure user has one of the allowed roles (user/therapist/admin)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @require_auth
        def wrapper(*args, **kwargs):
            admin = get_admin_client()
            resp = admin.table("profiles").select("role").eq("id", g.user_id).single().execute()
            user_role = resp.data.get("role") if resp.data else None
            if user_role not in allowed_roles:
                raise ForbiddenError(
                    f"Requires role: {', '.join(allowed_roles)} (you are: {user_role})"
                )
            g.user_role = user_role
            return f(*args, **kwargs)
        return wrapper
    return decorator


def current_user_id() -> str:
    """Current user UUID (raises if no auth context)."""
    if not hasattr(g, "user_id"):
        raise AuthError("No user context")
    return g.user_id
