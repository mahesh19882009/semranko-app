from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    passwordHash: Mapped[str] = mapped_column(String, nullable=False)
    isVerified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    emailVerificationToken: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    emailVerificationExpiresAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    passwordResetToken: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    passwordResetExpiresAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    authProvider: Mapped[str] = mapped_column(String, nullable=False, default="local", server_default="local")
    googleId: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)

    selectedPlan: Mapped[str] = mapped_column(String, nullable=False, default="starter", server_default="starter")
    subscriptionStatus: Mapped[str] = mapped_column(String, nullable=False, default="trialing", server_default="trialing")
    trialStartsAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    trialEndsAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    creditBalance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    pendingPlanChange: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    dailyKeywordMovement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    weeklyAuditSummary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    competitorAlerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    orders: Mapped[list["PaymentOrder"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    apiKeys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    ownedTeams: Mapped[list["Team"]] = relationship(back_populates="owner")
    teamMemberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "Project"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="projects")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="project")
    keywords: Mapped[list["Keyword"]] = relationship(back_populates="project")
    rankResults: Mapped[list["RankResult"]] = relationship(back_populates="project")
    audits: Mapped[list["Audit"]] = relationship(back_populates="project")
    reports: Mapped[list["Report"]] = relationship(back_populates="project")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="project")
    backlinks: Mapped[list["Backlink"]] = relationship(back_populates="project")


class Keyword(Base):
    __tablename__ = "Keyword"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="keywords")
    rankResults: Mapped[list["RankResult"]] = relationship(back_populates="keyword")

    __table_args__ = (
        Index("Keyword_projectId_idx", "projectId"),
        Index("Keyword_projectId_keyword_key", "projectId", "keyword", unique=True),
    )


class RankResult(Base):
    __tablename__ = "RankResult"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    keywordId: Mapped[Optional[str]] = mapped_column(String, ForeignKey("Keyword.id", ondelete="CASCADE"), nullable=True)

    keyword: Mapped[Optional[Keyword]] = relationship(back_populates="rankResults")
    project: Mapped[Project] = relationship(back_populates="rankResults")


class Competitor(Base):
    __tablename__ = "Competitor"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped[Project] = relationship(back_populates="competitors")

    __table_args__ = (
        Index("Competitor_projectId_idx", "projectId"),
        Index("Competitor_projectId_domain_key", "projectId", "domain", unique=True),
    )


class Audit(Base):
    __tablename__ = "Audit"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    totalIssues: Mapped[int] = mapped_column(Integer, nullable=False)
    criticalIssues: Mapped[int] = mapped_column(Integer, nullable=False)
    warningIssues: Mapped[int] = mapped_column(Integer, nullable=False)
    passedChecks: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="audits")
    issues: Mapped[list["AuditIssue"]] = relationship(back_populates="audit")

    __table_args__ = (Index("Audit_projectId_idx", "projectId"),)


class AuditIssue(Base):
    __tablename__ = "AuditIssue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    auditId: Mapped[str] = mapped_column(String, ForeignKey("Audit.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    audit: Mapped[Audit] = relationship(back_populates="issues")

    __table_args__ = (Index("AuditIssue_auditId_idx", "auditId"),)


class Report(Base):
    __tablename__ = "Report"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="COMPLETED", server_default="COMPLETED")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    visibilityScore: Mapped[int] = mapped_column(Integer, nullable=False)
    keywordCount: Mapped[int] = mapped_column(Integer, nullable=False)
    top10Count: Mapped[int] = mapped_column(Integer, nullable=False)
    competitorCount: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped[Project] = relationship(back_populates="reports")

    __table_args__ = (Index("Report_projectId_idx", "projectId"),)


class Notification(Base):
    __tablename__ = "Notification"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    projectId: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("Project.id", ondelete="SET NULL"),
        nullable=True,
    )

    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="UNREAD", server_default="UNREAD")
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info", server_default="info")

    entityType: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entityId: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    readAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="notifications")
    project: Mapped[Optional["Project"]] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("notification_user_id_idx", "userId"),
        Index("notification_project_id_idx_v2", "projectId"),
        Index("notification_status_idx", "status"),
        Index("notification_created_at_idx", "createdAt"),
    )


class PaymentOrder(Base):
    __tablename__ = "PaymentOrder"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    razorpayOrderId: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    razorpayPaymentId: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    razorpaySignature: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    planId: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in paise, net amount actually paid
    credit_applied_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in paise
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String, nullable=False, default="created", server_default="created")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="orders")

    __table_args__ = (
        Index("PaymentOrder_userId_idx", "userId"),
        Index("PaymentOrder_razorpayOrderId_idx", "razorpayOrderId"),
    )


class Subscription(Base):
    __tablename__ = "Subscription"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    planId: Mapped[int] = mapped_column(Integer, nullable=False)
    razorpayPaymentId: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    razorpayOrderId: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="inactive", server_default="inactive")
    startDate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    endDate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="subscriptions")

    __table_args__ = (
        Index("Subscription_userId_idx", "userId"),
        Index("Subscription_status_idx", "status"),
    )

class Backlink(Base):
    __tablename__ = "Backlink"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    sourceUrl: Mapped[str] = mapped_column(Text, nullable=False)
    sourceDomain: Mapped[str] = mapped_column(String, nullable=False)
    anchor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domainRank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    firstSeen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="backlinks")
    __table_args__ = (Index("Backlink_projectId_idx", "projectId"),)


class SerpFeature(Base):
    __tablename__ = "SerpFeature"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    featureType: Mapped[str] = mapped_column(String, nullable=False)
    isPresent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("SerpFeature_projectId_idx", "projectId"),
        Index("SerpFeature_projectId_keyword_feature_key", "projectId", "keywordText", "featureType", unique=True),
    )


class ApiKey(Base):
    __tablename__ = "ApiKey"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lastUsed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    expiresAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="apiKeys")

    __table_args__ = (
        Index("ApiKey_userId_idx", "userId"),
        Index("ApiKey_key_idx", "key"),
    )


class ScheduledReport(Base):
    __tablename__ = "ScheduledReport"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)  # daily, weekly, monthly
    format: Mapped[str] = mapped_column(String, nullable=False)  # pdf, csv
    recipients: Mapped[str] = mapped_column(String, nullable=False)  # comma-separated emails
    startDate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)  # When to start sending reports
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lastSentAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    nextSendAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User")
    project: Mapped[Project] = relationship("Project")

    __table_args__ = (
        Index("ScheduledReport_userId_idx", "userId"),
        Index("ScheduledReport_projectId_idx", "projectId"),
    )


class Team(Base):
    __tablename__ = "Team"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ownerId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    owner: Mapped[User] = relationship("User", back_populates="ownedTeams")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")

    __table_args__ = (
        Index("Team_ownerId_idx", "ownerId"),
    )


class TeamMember(Base):
    __tablename__ = "TeamMember"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    teamId: Mapped[str] = mapped_column(String, ForeignKey("Team.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")  # owner, admin, member, viewer
    joinedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    team: Mapped[Team] = relationship("Team", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="teamMemberships")

    __table_args__ = (
        Index("TeamMember_teamId_idx", "teamId"),
        Index("TeamMember_userId_idx", "userId"),
        Index("TeamMember_team_user_key", "teamId", "userId", unique=True),
    )


class TeamInvite(Base):
    __tablename__ = "TeamInvite"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    teamId: Mapped[str] = mapped_column(String, ForeignKey("Team.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")
    invitedBy: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")  # pending, accepted, declined, expired
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    team: Mapped[Team] = relationship("Team")
    inviter: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("TeamInvite_teamId_idx", "teamId"),
        Index("TeamInvite_email_idx", "email"),
        Index("TeamInvite_status_idx", "status"),
    )