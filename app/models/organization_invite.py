"""Organization invite model for multi-tenant SaaS."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid

from app.db.base import BaseModel


class OrganizationInvite(BaseModel):
    """
    Organization invite model for sending invite codes to users.

    Stores invite codes that users can use to join organizations.
    """

    __tablename__ = "organization_invites"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign keys
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Invite code
    code = Column(String(12), nullable=False, unique=True, index=True)
    role = Column(String(50), default="member", nullable=False)  # viewer, member, admin, owner

    # Status
    is_active = Column(Integer, default=1, nullable=False)  # 1 = active, 0 = revoked
    used_count = Column(Integer, default=0, nullable=False)
    max_uses = Column(Integer, default=None, nullable=True)  # None = unlimited

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # None = no expiration
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", backref="invites")
    creator = relationship("User", backref="invites_created")

    def __repr__(self):
        return f"<OrganizationInvite(id={self.id}, code={self.code}, org_id={self.organization_id})>"

    def is_valid(self) -> bool:
        """Check if invite code is still valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    @staticmethod
    def generate_code() -> str:
        """Generate a random 12-character invite code."""
        import string
        import secrets
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(12))
