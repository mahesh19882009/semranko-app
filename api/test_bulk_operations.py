import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Project, Keyword, RankResult
from app.services.keyword_service import add_keywords_bulk, delete_keywords_bulk
from app.services.ranking_service import delete_rankings_bulk


def make_user(db: Session, user_id="user-1"):
    user = User(
        id=user_id,
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="pro",
        creditBalance=0.0,
        subscriptionStatus="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db: Session, user_id="user-1", project_id="proj-1"):
    project = Project(id=project_id, name="Test Project", domain="test.com", userId=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


class TestBulkKeywords:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_bulk_add_keywords(self):
        user = make_user(self.db, user_id="user-b1")
        project = make_project(self.db, user_id=user.id, project_id="proj-b1")

        result = add_keywords_bulk(self.db, user.id, project.id, ["kw1", "kw2", "kw3"])
        assert result["added"] == 3
        assert result["skipped"] == 0
        assert len(result["keywords"]) == 3

    def test_bulk_add_skips_duplicates(self):
        user = make_user(self.db, user_id="user-b2")
        project = make_project(self.db, user_id=user.id, project_id="proj-b2")
        kw = Keyword(projectId=project.id, keyword="kw1", device="desktop")
        self.db.add(kw)
        self.db.commit()

        result = add_keywords_bulk(self.db, user.id, project.id, ["kw1", "kw2", "kw1"])
        assert result["added"] == 1
        assert result["skipped"] == 2

    def test_bulk_add_limit_exceeded(self):
        user = make_user(self.db, user_id="user-b3")
        project = make_project(self.db, user_id=user.id, project_id="proj-b3")
        for i in range(100):
            kw = Keyword(projectId=project.id, keyword=f"existing{i}", device="desktop")
            self.db.add(kw)
        self.db.commit()

        with pytest.raises(Exception) as exc_info:
            add_keywords_bulk(self.db, user.id, project.id, ["new1", "new2"])
        assert "limit exceeded" in str(exc_info.value).lower()

    def test_bulk_delete_keywords(self):
        user = make_user(self.db, user_id="user-b4")
        project = make_project(self.db, user_id=user.id, project_id="proj-b4")
        kw1 = Keyword(projectId=project.id, keyword="kw1", device="desktop")
        kw2 = Keyword(projectId=project.id, keyword="kw2", device="desktop")
        self.db.add_all([kw1, kw2])
        self.db.commit()
        self.db.refresh(kw1)
        self.db.refresh(kw2)

        deleted = delete_keywords_bulk(self.db, user.id, [kw1.id, kw2.id])
        assert deleted == 2

        remaining = self.db.scalar(select(Keyword).where(Keyword.projectId == project.id))
        assert remaining is None


class TestBulkRankings:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_bulk_delete_rankings(self):
        user = make_user(self.db, user_id="user-r1")
        project = make_project(self.db, user_id=user.id, project_id="proj-r1")
        keyword = Keyword(projectId=project.id, keyword="test", device="desktop")
        self.db.add(keyword)
        self.db.commit()
        self.db.refresh(keyword)

        rr1 = RankResult(projectId=project.id, keywordId=keyword.id, keywordText="test", position=1)
        rr2 = RankResult(projectId=project.id, keywordId=keyword.id, keywordText="test", position=2)
        self.db.add_all([rr1, rr2])
        self.db.commit()
        self.db.refresh(rr1)
        self.db.refresh(rr2)

        deleted = delete_rankings_bulk(self.db, user.id, [rr1.id, rr2.id])
        assert deleted == 2

        remaining = self.db.scalar(select(RankResult).where(RankResult.projectId == project.id))
        assert remaining is None
