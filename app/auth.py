"""Password hashing and token-based login (JWT)."""
import os, time
import bcrypt, jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db, User

SECRET = os.environ.get("SECRET_KEY", "local-development-secret-key-change-in-production")
TTL = 60 * 60 * 24 * 7


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def check_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    return jwt.encode({"sub": str(user.id), "exp": int(time.time()) + TTL}, SECRET, algorithm="HS256")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please log in.")
    try:
        data = jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has expired. Please log in again.")
    user = db.get(User, int(data["sub"]))
    if user is None:
        raise HTTPException(401, "Account not found.")
    return user
