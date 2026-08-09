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
    planAnniversaryAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, server_default="NULL")  # When plan was activated for anniversary tracking
    lastCreditResetAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, server_default="NULL")  # Last time credits were reset
    userGstin: Mapped[Optional[str]] = mapped_column(String, nullable=True, server_default="NULL")
    userGstName: Mapped[Optional[str]] = mapped_column(String, nullable=True, server_default="NULL")
    userGstAddress: Mapped[Optional[str]] = mapped_column(String, nullable=True, server_default="NULL")
    userGstState: Mapped[Optional[str]] = mapped_column(String, nullable=True, server_default="NULL")
    userGstStateCode: Mapped[Optional[str]] = mapped_column(String, nullable=True, server_default="NULL")

    dailyKeywordMovement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    weeklyAuditSummary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    competitorAlerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    refreshFrequency: Mapped[str] = mapped_column(String, nullable=False, default="weekly", server_default="weekly")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    orders: Mapped[list["PaymentOrder"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    keywordLists: Mapped[list["KeywordList"]] = relationship(back_populates="user")
    creditLedgerEntries: Mapped[list["CreditLedger"]] = relationship(
        "CreditLedger",
        back_populates="user",
        primaryjoin="and_(CreditLedger.userId == User.id, CreditLedger.userId != None)",
    )
    dataforseoCosts: Mapped[list["DataForSEOCost"]] = relationship("DataForSEOCost", back_populates="user")


class KeywordList(Base):
    __tablename__ = "KeywordList"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="keywordLists")
    items: Mapped[list["KeywordListItem"]] = relationship(back_populates="keywordList", cascade="all, delete-orphan")


class KeywordListItem(Base):
    __tablename__ = "KeywordListItem"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    listId: Mapped[str] = mapped_column(String, ForeignKey("KeywordList.id", ondelete="CASCADE"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)

    keywordList: Mapped[KeywordList] = relationship(back_populates="items")


class CompetitorRank(Base):
    __tablename__ = "CompetitorRank"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    competitorId: Mapped[str] = mapped_column(String, ForeignKey("Competitor.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("CompetitorRank_projectId_idx", "projectId"),
        Index("CompetitorRank_projectId_competitor_keyword_key", "projectId", "competitorId", "keywordText", unique=True),
    )


class AIOTracking(Base):
    __tablename__ = "AIOTracking"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    hasAIOverview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aiOverviewText: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aiOverviewTitle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    aiOverviewMarkdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    images: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    aiOverviewType: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    citedDomains: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("AIOTracking_projectId_idx", "projectId"),
        Index("AIOTracking_projectId_keyword_key", "projectId", "keywordText", unique=True),
    )


class Project(Base):
    __tablename__ = "Project"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    locationCode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    client_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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


class Keyword(Base):
    __tablename__ = "Keyword"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cpc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    competition: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backlinks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    referring_domains: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_badge: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    check_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    visibility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

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
    etv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    keyword: Mapped[Optional[Keyword]] = relationship(back_populates="rankResults")
    project: Mapped[Project] = relationship(back_populates="rankResults")

    __table_args__ = (
        Index("RankResult_projectId_keywordId_checkedAt_idx", "projectId", "keywordId", "checkedAt"),
    )


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
    purchaseType: Mapped[str] = mapped_column(String, nullable=False, default="SUBSCRIPTION_UPGRADE", server_default="SUBSCRIPTION_UPGRADE")  # SUBSCRIPTION_UPGRADE or CREDIT_TOP_UP
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


class TrackedKeyword(Base):
    __tablename__ = "TrackedKeyword"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lockedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    lockedUntil: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lastPosition: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lastCheckedAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    trackAio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    dataStatus: Mapped[str] = mapped_column(String, nullable=False, default="fresh", server_default="fresh")

    user: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("TrackedKeyword_userId_idx", "userId"),
        Index("TrackedKeyword_userId_keyword_key", "userId", "keyword", unique=True),
    )


class DataForSEOCost(Base):
    __tablename__ = "DataForSEOCost"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[Optional[str]] = mapped_column(String, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)
    taskType: Mapped[str] = mapped_column(String, nullable=False)  # 'rank_tracker', 'aio', etc.
    endpoint: Mapped[str] = mapped_column(String, nullable=False)  # API endpoint called
    costCredits: Mapped[float] = mapped_column(Float, nullable=False)  # Cost in credits
    costUsd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Cost in USD for reporting
    keywordCount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Number of keywords processed
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional context
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    user: Mapped[Optional[User]] = relationship("User")

    __table_args__ = (
        Index("DataForSEOCost_userId_idx", "userId"),
        Index("DataForSEOCost_createdAt_idx", "createdAt"),
        Index("DataForSEOCost_taskType_idx", "taskType"),
    )


class KeywordCache(Base):
    __tablename__ = "KeywordCache"

    keyword: Mapped[str] = mapped_column(String, primary_key=True)
    location: Mapped[str] = mapped_column(String, primary_key=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cpc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    competition: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backlinks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    referring_domains: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_badge: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    check_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lastApiCallAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)  # Track when API was last called for this keyword
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )


class KeywordResearchCache(Base):
    __tablename__ = "KeywordResearchCache"

    userId: Mapped[str] = mapped_column(String, primary_key=True)
    seedKeyword: Mapped[str] = mapped_column(String, primary_key=True)
    locationCode: Mapped[int] = mapped_column(Integer, primary_key=True)
    ideasJson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())


class CompetitorCache(Base):
    __tablename__ = "CompetitorCache"

    domain: Mapped[str] = mapped_column(String, primary_key=True)
    location: Mapped[str] = mapped_column(String, primary_key=True)
    keywordsJson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreditLedger(Base):
    __tablename__ = "CreditLedger"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    ownerId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False, server_default="")
    triggeredByUserId: Mapped[Optional[str]] = mapped_column(String, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    actionType: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    relatedOrderId: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amountPaidInr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed", server_default="completed")
    invoiceNumber: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    queryTarget: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    creditsSpent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    planName: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, index=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="creditLedgerEntries", foreign_keys=[userId])
    owner: Mapped[User] = relationship("User", foreign_keys=[ownerId])
    triggeredByUser: Mapped[Optional[User]] = relationship("User", foreign_keys=[triggeredByUserId])

    __table_args__ = (
        Index("CreditLedger_userId_idx", "userId"),
        Index("CreditLedger_ownerId_idx", "ownerId"),
        Index("CreditLedger_actionType_idx", "actionType"),
        Index("CreditLedger_timestamp_idx", "timestamp"),
    )


class UserCacheUnlock(Base):
    __tablename__ = "UserCacheUnlock"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    ownerId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    targetString: Mapped[str] = mapped_column(String, nullable=False)
    unlockedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    owner: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("UserCacheUnlock_ownerId_idx", "ownerId"),
        Index("UserCacheUnlock_ownerId_targetString_key", "ownerId", "targetString", unique=True),
    )


class AsyncTaskQueue(Base):
    __tablename__ = "AsyncTaskQueue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    taskId: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    taskType: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    keywordsJson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    locationCode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="desktop")
    userId: Mapped[Optional[str]] = mapped_column(String, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)
    projectId: Mapped[Optional[str]] = mapped_column(String, ForeignKey("Project.id", ondelete="SET NULL"), nullable=True)
    resultJson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    errorMessage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )
    completedAt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    __table_args__ = (
        Index("AsyncTaskQueue_status_idx", "status"),
        Index("AsyncTaskQueue_taskType_idx", "taskType"),
        Index("AsyncTaskQueue_createdAt_idx", "createdAt"),
    )