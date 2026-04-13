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
from app.models.proposal_generation import ProposalGeneration
from app.models.proposal_feedback import ProposalFeedback
from app.models.proposal_learnings import ProposalLearnings
from app.models.company import CompanyWritingPreferences

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

    # ---- Drill-down endpoints ------------------------------------------------

    def get_user_detail(self, user_id: str) -> Dict[str, Any]:
        """Full journey of a single user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Orgs + companies
        user_orgs = (
            self.db.query(UserOrganization, Organization)
            .join(Organization, UserOrganization.organization_id == Organization.id)
            .filter(UserOrganization.user_id == user.id)
            .all()
        )

        orgs = []
        for uo, org in user_orgs:
            company = self.db.query(Company).filter(
                Company.organization_id == org.id
            ).first()

            org_projects = (
                self.db.query(Project)
                .filter(Project.organization_id == org.id)
                .order_by(desc(Project.created_at))
                .all()
            )

            orgs.append({
                "org_id": str(org.id),
                "org_name": org.name,
                "role": uo.role,
                "company": {
                    "name": company.name,
                    "industry": company.industry_focus,
                    "created_at": company.created_at.isoformat() if company.created_at else None,
                } if company else None,
                "project_count": len(org_projects),
                "projects": [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "status": p.status.value if p.status else "unknown",
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in org_projects
                ],
            })

        # Feedback given by this user
        feedback = (
            self.db.query(ProposalFeedback)
            .filter(ProposalFeedback.created_by == user_id)
            .order_by(desc(ProposalFeedback.created_at))
            .limit(20)
            .all()
        )

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "organizations": orgs,
            "feedback_given": [
                {
                    "rating": f.rating,
                    "feedback_text": f.feedback_text,
                    "feedback_tags": f.feedback_tags,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in feedback
            ],
        }

    def get_project_detail(self, project_id: str) -> Dict[str, Any]:
        """Every step of the pipeline for a single project."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}

        # Organization
        org_name = None
        if project.organization_id:
            org = self.db.query(Organization).filter(
                Organization.id == project.organization_id
            ).first()
            org_name = org.name if org else None

        # Files
        files = (
            self.db.query(UploadedFile)
            .filter(UploadedFile.project_id == project_id)
            .order_by(UploadedFile.created_at.asc())
            .all()
        )

        # Analysis
        analysis = (
            self.db.query(AnalysisResult)
            .filter(AnalysisResult.project_id == project_id)
            .first()
        )
        analysis_data = None
        if analysis:
            analysis_data = {
                "document_type": analysis.document_type,
                "fit_score": analysis.fit_score,
                "compliance_count": len(analysis.compliance_matrix) if analysis.compliance_matrix else 0,
                "mandatory_count": len(analysis.mandatory_requirements) if analysis.mandatory_requirements else 0,
                "risks_count": len(analysis.risks) if analysis.risks else 0,
                "eval_criteria_count": len(analysis.evaluation_criteria) if analysis.evaluation_criteria else 0,
                "contract_type": analysis.contract_type,
                "set_aside_status": analysis.set_aside_status,
                "naics_codes": analysis.naics_codes,
                "estimated_value": analysis.estimated_value,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            }

        # Proposal
        proposal = (
            self.db.query(ProposalDraft)
            .filter(ProposalDraft.project_id == project_id)
            .first()
        )
        proposal_data = None
        if proposal:
            sections = {}
            for s in ProposalDraft.SECTION_ORDER:
                text = getattr(proposal, s, None) or ""
                sections[s] = {
                    "word_count": len(text.split()) if text else 0,
                    "char_count": len(text),
                    "has_content": bool(text.strip()),
                }
            proposal_data = {
                "id": str(proposal.id),
                "sections": sections,
                "total_words": sum(s["word_count"] for s in sections.values()),
                "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            }

        # Pipeline status
        pipeline = {
            "1_created": {"done": True, "at": project.created_at.isoformat() if project.created_at else None},
            "2_files_uploaded": {"done": len(files) > 0, "count": len(files)},
            "3_analyzed": {"done": analysis is not None, "at": analysis_data.get("created_at") if analysis_data else None},
            "4_proposal_generated": {"done": proposal is not None, "at": proposal_data.get("created_at") if proposal_data else None},
        }

        return {
            "project": {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "status": project.status.value if project.status else "unknown",
                "org_name": org_name,
                "created_at": project.created_at.isoformat() if project.created_at else None,
            },
            "pipeline": pipeline,
            "files": [
                {
                    "id": str(f.id),
                    "filename": f.original_filename,
                    "size_kb": round(f.file_size / 1024, 1) if f.file_size else 0,
                    "mime_type": f.mime_type,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in files
            ],
            "analysis": analysis_data,
            "proposal": proposal_data,
        }

    def get_org_detail(self, org_id: str) -> Dict[str, Any]:
        """Full org detail — members, projects, company, feedback, learnings."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            return {"error": "Organization not found"}

        # Members
        members = (
            self.db.query(UserOrganization, User)
            .join(User, UserOrganization.user_id == User.id)
            .filter(UserOrganization.organization_id == org_id)
            .all()
        )

        # Company
        company = self.db.query(Company).filter(
            Company.organization_id == org_id
        ).first()

        # Projects
        projects = (
            self.db.query(Project)
            .filter(Project.organization_id == org_id)
            .order_by(desc(Project.created_at))
            .all()
        )

        # Feedback
        feedback = (
            self.db.query(ProposalFeedback)
            .filter(ProposalFeedback.organization_id == org_id)
            .order_by(desc(ProposalFeedback.created_at))
            .limit(20)
            .all()
        )

        # Learnings
        learnings = self.db.query(ProposalLearnings).filter(
            ProposalLearnings.organization_id == org_id
        ).first()

        # Proposal generations
        generations = (
            self.db.query(ProposalGeneration)
            .filter(ProposalGeneration.organization_id == org_id)
            .order_by(desc(ProposalGeneration.created_at))
            .limit(10)
            .all()
        )

        return {
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "description": org.description,
                "created_at": org.created_at.isoformat() if org.created_at else None,
            },
            "members": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": uo.role,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                }
                for uo, u in members
            ],
            "company": {
                "name": company.name,
                "description": company.description,
                "usp": company.unique_selling_proposition,
                "capabilities": company.key_capabilities,
                "experience": company.experience,
                "industry": company.industry_focus,
            } if company else None,
            "projects": [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "status": p.status.value if p.status else "unknown",
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ],
            "proposal_generations": [
                {
                    "id": str(g.id),
                    "title": g.proposal_title[:100] if g.proposal_title else None,
                    "type": g.proposal_type,
                    "status": g.status,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in generations
            ],
            "feedback": [
                {
                    "rating": f.rating,
                    "feedback_text": f.feedback_text,
                    "feedback_tags": f.feedback_tags,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in feedback
            ],
            "learnings": {
                "total_proposals": learnings.total_proposals_generated,
                "total_feedback": learnings.total_feedback_entries,
                "love": learnings.love_count,
                "okay": learnings.okay_count,
                "not_right": learnings.not_right_count,
                "satisfaction": learnings.get_satisfaction_percentage(),
                "common_issues": learnings.common_issues,
                "learned_preferences": learnings.learned_preferences,
            } if learnings else None,
        }
