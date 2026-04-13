"""Admin dashboard service — read-only queries on existing tables.

Aggregates data across users, orgs, projects, proposals, and feedback
for a single-pane admin overview. Does NOT create or modify any data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.user import User
from app.models.organization import Organization
from app.models.user_organization import UserOrganization
from app.models.project import Project
from app.models.company import Company
from app.models.analysis_result import AnalysisResult
from app.models.proposal_draft import ProposalDraft
from app.models.uploaded_file import UploadedFile

logger = logging.getLogger(__name__)


class AdminDashboardService:
    """Read-only admin queries across all tables."""

    def __init__(self, db: Session):
        self.db = db

    def get_overview(self) -> Dict[str, Any]:
        """High-level platform stats."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        return {
            "total_users": self.db.query(User).count(),
            "total_organizations": self.db.query(Organization).count(),
            "total_projects": self.db.query(Project).count(),
            "total_companies": self.db.query(Company).count(),
            "total_files_uploaded": self.db.query(UploadedFile).count(),
            "total_analyses": self.db.query(AnalysisResult).count(),
            "total_proposals": self.db.query(ProposalDraft).count(),
            "users_last_24h": self.db.query(User).filter(
                User.created_at >= last_24h
            ).count(),
            "projects_last_24h": self.db.query(Project).filter(
                Project.created_at >= last_24h
            ).count(),
            "projects_last_7d": self.db.query(Project).filter(
                Project.created_at >= last_7d
            ).count(),
            "timestamp": now.isoformat(),
        }

    def get_users(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """All users with their org and company info."""
        users = (
            self.db.query(User)
            .order_by(desc(User.created_at))
            .offset(offset).limit(limit)
            .all()
        )

        result = []
        for u in users:
            # Get user's orgs
            user_orgs = (
                self.db.query(UserOrganization, Organization)
                .join(Organization, UserOrganization.organization_id == Organization.id)
                .filter(UserOrganization.user_id == u.id)
                .all()
            )

            orgs = []
            company_name = None
            for uo, org in user_orgs:
                orgs.append({
                    "org_id": str(org.id),
                    "org_name": org.name,
                    "role": uo.role,
                })
                # Get company for this org
                company = (
                    self.db.query(Company)
                    .filter(Company.organization_id == org.id)
                    .first()
                )
                if company:
                    company_name = company.name

            result.append({
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "organizations": orgs,
                "company_name": company_name,
            })

        return result

    def get_projects_summary(self, limit: int = 50) -> List[Dict]:
        """All projects with status, file count, and whether analyzed/generated."""
        projects = (
            self.db.query(Project)
            .order_by(desc(Project.created_at))
            .limit(limit)
            .all()
        )

        result = []
        for p in projects:
            file_count = (
                self.db.query(UploadedFile)
                .filter(UploadedFile.project_id == p.id)
                .count()
            )
            total_file_size = (
                self.db.query(func.sum(UploadedFile.file_size))
                .filter(UploadedFile.project_id == p.id)
                .scalar()
            ) or 0

            has_analysis = (
                self.db.query(AnalysisResult)
                .filter(AnalysisResult.project_id == p.id)
                .first()
            ) is not None

            has_proposal = (
                self.db.query(ProposalDraft)
                .filter(ProposalDraft.project_id == p.id)
                .first()
            ) is not None

            # Get org name
            org_name = None
            if p.organization_id:
                org = self.db.query(Organization).filter(
                    Organization.id == p.organization_id
                ).first()
                if org:
                    org_name = org.name

            result.append({
                "id": str(p.id),
                "title": p.title,
                "status": p.status.value if p.status else "unknown",
                "org_name": org_name,
                "file_count": file_count,
                "total_file_size_kb": round(total_file_size / 1024, 1),
                "has_analysis": has_analysis,
                "has_proposal": has_proposal,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        return result

    def get_activity_timeline(self, limit: int = 100) -> List[Dict]:
        """Recent activity across all tables — unified timeline."""
        events = []

        # Recent users
        for u in self.db.query(User).order_by(desc(User.created_at)).limit(20).all():
            events.append({
                "type": "user_signup",
                "email": u.email,
                "detail": u.full_name,
                "timestamp": u.created_at.isoformat() if u.created_at else None,
            })

        # Recent projects
        for p in self.db.query(Project).order_by(desc(Project.created_at)).limit(20).all():
            events.append({
                "type": "project_created",
                "detail": p.title,
                "status": p.status.value if p.status else None,
                "timestamp": p.created_at.isoformat() if p.created_at else None,
            })

        # Recent file uploads
        for f in self.db.query(UploadedFile).order_by(desc(UploadedFile.created_at)).limit(20).all():
            events.append({
                "type": "file_uploaded",
                "detail": f.original_filename,
                "size_kb": round(f.file_size / 1024, 1) if f.file_size else 0,
                "timestamp": f.created_at.isoformat() if f.created_at else None,
            })

        # Recent analyses
        for a in self.db.query(AnalysisResult).order_by(desc(AnalysisResult.created_at)).limit(20).all():
            events.append({
                "type": "analysis_completed",
                "detail": a.document_type or "Unknown",
                "fit_score": a.fit_score,
                "timestamp": a.created_at.isoformat() if a.created_at else None,
            })

        # Sort all by timestamp descending
        events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
        return events[:limit]
