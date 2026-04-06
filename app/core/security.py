"""Security utilities for password hashing and JWT token management."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordManager:
    """Manage password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise ValueError("Failed to hash password")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False


class TokenManager:
    """Manage JWT token generation and validation."""

    def __init__(self):
        self.settings = get_settings()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60  # 1 hour (increased from 30 min)
        self.refresh_token_expire_days = 7

    def create_access_token(self, subject: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "sub": subject,
            "exp": expire,
            "type": "access"
        }

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.settings.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise ValueError("Failed to create access token")

    def create_refresh_token(self, subject: str) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": subject,
            "exp": expire,
            "type": "refresh"
        }

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.settings.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise ValueError("Failed to create refresh token")

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            return None

    def get_token_expiry(self) -> int:
        """Get access token expiry time in seconds."""
        return self.access_token_expire_minutes * 60


# Global instances
password_manager = PasswordManager()
token_manager = TokenManager()
