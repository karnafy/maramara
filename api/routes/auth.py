"""Auth routes: signup, login, logout, me, role selection."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, redirect, render_template, request, session, url_for
from pydantic import BaseModel, EmailStr, Field

from utils.auth import require_auth
from utils.errors import AppError, AuthError
from db.supabase_client import get_admin_client, get_client

bp = Blueprint("auth", __name__)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(default="user", pattern="^(user|therapist)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------- HTML pages (therapist + admin web) ----------------

@bp.get("/signup")
def signup_page():
    return render_template("auth/signup.html")


@bp.get("/login")
def login_page():
    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    session.clear()
    if request.accept_mimetypes.best == "application/json":
        return jsonify({"success": True})
    return redirect(url_for("index"))


# ---------------- JSON API (used by mobile + web forms via fetch) ----------------

@bp.post("/api/signup")
def api_signup():
    payload = SignupRequest(**request.get_json(force=True))
    sb = get_client()
    try:
        resp = sb.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {"data": {"full_name": payload.full_name, "role": payload.role}},
        })
    except Exception as e:
        raise AppError(f"Signup failed: {e}", status_code=400) from e

    if not resp.user:
        raise AppError("Signup failed - no user returned", status_code=400)

    # Set requested role on the auto-created profile
    admin = get_admin_client()
    admin.table("profiles").update({
        "role": payload.role,
        "full_name": payload.full_name,
    }).eq("id", resp.user.id).execute()

    return jsonify({
        "success": True,
        "data": {"user_id": resp.user.id, "email": resp.user.email, "role": payload.role},
    }), 201


@bp.post("/api/login")
def api_login():
    payload = LoginRequest(**request.get_json(force=True))
    sb = get_client()
    try:
        resp = sb.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception as e:
        raise AuthError("Invalid credentials") from e

    if not resp.session:
        raise AuthError("Login failed")

    # Set session (for web dashboard)
    session["access_token"] = resp.session.access_token
    session["refresh_token"] = resp.session.refresh_token
    session["user"] = {
        "id": resp.user.id,
        "email": resp.user.email,
    }

    # Load role
    admin = get_admin_client()
    profile = admin.table("profiles").select("role,full_name,onboarding_completed,language").eq(
        "id", resp.user.id
    ).single().execute()
    if profile.data:
        session["user"]["role"] = profile.data["role"]
        session["user"]["full_name"] = profile.data["full_name"]
        session["user"]["onboarding_completed"] = profile.data["onboarding_completed"]
        session["user"]["language"] = profile.data["language"]

    return jsonify({
        "success": True,
        "data": {
            "access_token": resp.session.access_token,
            "refresh_token": resp.session.refresh_token,
            "expires_at": resp.session.expires_at,
            "user": session["user"],
        },
    })


@bp.get("/api/me")
@require_auth
def api_me():
    admin = get_admin_client()
    profile = admin.table("profiles").select("*").eq("id", g.user_id).single().execute()
    return jsonify({"success": True, "data": profile.data})
