from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

# --- CONFIGURATION ---
# The 'or ""' ensures Pylance sees this as a string, not 'str | None' [cite: 2026-03-08]
SECRET_KEY: str = os.getenv("SECRET_KEY") or ""

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in .env file!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30-day session [cite: 2026-03-05]

# Setup the password scrambler with the fix for Python 3.14/Bcrypt [cite: 2026-03-08]
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False  # Prevents the 72-byte value error crash [cite: 2026-03-08]
)

def get_password_hash(password: str) -> str:
    """Turns 'password123' into a secure hash."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the entered password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Creates the JWT 'passport' for the user."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Casting SECRET_KEY to str here satisfies the jwt.encode requirements [cite: 2026-03-08]
    return jwt.encode(to_encode, str(SECRET_KEY), algorithm=ALGORITHM)

# This tells FastAPI to look for the "Authorization" header in the browser request [cite: 2026-03-05]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    The 'Security Guard' function. It decodes the 30-day passport 
    and returns the User ID. [cite: 2026-03-05, 2026-03-08]
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token using your SECRET_KEY [cite: 2026-03-08]
        payload = jwt.decode(token, str(SECRET_KEY), algorithms=[ALGORITHM])
        
        # We don't type hint user_id as :str here because .get() could return None [cite: 2026-03-08]
        user_id = payload.get("sub") 
        
        if user_id is None:
            raise credentials_exception
            
        # Returning it as a string satisfies the expected return type [cite: 2026-03-08]
        return str(user_id) 
        
    except JWTError:
        raise credentials_exception