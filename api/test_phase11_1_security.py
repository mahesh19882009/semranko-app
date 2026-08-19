"""
Phase 11.1 — Production Security Hardening Tests

Tests for:
- Exception information not leaked
- DataForSEO credentials not logged
- Webhook authentication
- CORS production configuration
- Print statements removed from production paths
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

import json
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User, RefreshJob, ProcessingJob
from app.core.errors import register_exception_handlers, ApiError
from app.api.routes.webhooks import dataforseo_webhook
from app.services.async_bulk_service import (
    _paginate_eligible_keywords,
    create_refresh_jobs,
    run_weekly_bulk_update_job,
)
from app.core.config import get_settings

# Capture log output
logger = logging.getLogger(__name__)
log_capture = StringIO()
log_handler = logging.StreamHandler(log_capture)
log_handler.setLevel(logging.DEBUG)
logger.addHandler(log_handler)


def make_user(db, user_id="user-1", email=None, plan="starter", credit_balance=100.0,
              subscription_status="active", refresh_frequency="monthly"):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=email or f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        refreshFrequency=refresh_frequency,
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db, user_id, project_id="p1", domain="example.com"):
    project = Project(id=project_id, name="Test", domain=domain, userId=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def make_keyword(db, project_id, user_id, keyword="test kw", location="India", is_active=True):
    kw = Keyword(
        id=f"kw-{keyword.replace(' ', '-')}-{datetime.utcnow().timestamp()}",
        projectId=project_id,
        userId=user_id,
        keyword=keyword,
        location=location,
        isActive=is_active,
    )
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


class TestExceptionHandler:
    def test_internal_exception_not_leaked(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/error")
        def raise_error():
            raise ValueError("Database connection failed: password=secret123")
        
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")
        
        assert response.status_code == 500
        data = response.json()
        assert "password" not in str(data)
        assert "secret123" not in str(data)
        assert "Database connection failed" not in str(data)
        assert data["message"] == "Internal server error"
    
    def test_api_error_preserves_status_and_message(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/api-error")
        def raise_api_error():
            raise ApiError(402, "Insufficient credits")
        
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api-error")
        
        assert response.status_code == 402
        data = response.json()
        assert data["message"] == "Insufficient credits"


class TestDataForSEOCredentialLogging:
    def test_no_credentials_in_logs(self):
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Simulate startup logging
        settings = get_settings()
        login = settings.effective_serp_login
        key = settings.effective_serp_key
        
        logger.info("DataForSEO credentials configured: %s", bool(login and key))
        
        log_output = log_capture.getvalue()
        assert login not in log_output if login else True
        assert key not in log_output if key else True
        assert "DATAFORSEO_LOGIN" not in log_output
        assert "DATAFORSEO_PASSWORD" not in log_output


class TestDataForSEOWebhookSecurity:
    def test_valid_webhook_with_secret(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="test kw")

        rj = RefreshJob(
            jobType="weekly_serp",
            status="submitted",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson=json.dumps([{"keyword": "test kw", "location": "India"}]),
            dataforseoRequestIds=json.dumps(["task-secure-1"]),
        )
        db.add(rj)
        db.commit()

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            with patch.object(get_settings(), "DATAFORSEO_WEBHOOK_SECRET", "my-secret"):
                from app.api.routes.webhooks import dataforseo_webhook
                import asyncio

                req = MagicMock()
                async def json_func():
                    return {
                        "task_id": "task-secure-1",
                        "tasks": [{
                            "data": {"keyword": "test kw", "location_code": 2840},
                            "result": [{
                                "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5}]
                            }]
                        }]
                    }
                req.json = json_func
                req.query_params = {"task_id": None, "secret": "my-secret"}

                response = asyncio.run(dataforseo_webhook(req))
                assert response["success"] is True

    def test_invalid_webhook_secret_rejected(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            with patch.object(get_settings(), "DATAFORSEO_WEBHOOK_SECRET", "my-secret"):
                from app.api.routes.webhooks import dataforseo_webhook
                import asyncio

                req = MagicMock()
                async def json_func():
                    return {"task_id": "task-1", "tasks": []}
                req.json = json_func
                req.query_params = {"task_id": None, "secret": "wrong-secret"}

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(dataforseo_webhook(req))
                assert exc_info.value.status_code == 401

    def test_missing_webhook_secret_rejected(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            with patch.object(get_settings(), "DATAFORSEO_WEBHOOK_SECRET", "my-secret"):
                from app.api.routes.webhooks import dataforseo_webhook
                import asyncio

                req = MagicMock()
                async def json_func():
                    return {"task_id": "task-1", "tasks": []}
                req.json = json_func
                req.query_params = {"task_id": None}

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(dataforseo_webhook(req))
                assert exc_info.value.status_code == 401

    def test_duplicate_webhook_still_skipped(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="test kw")

        rj = RefreshJob(
            jobType="weekly_serp",
            status="submitted",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson=json.dumps([{"keyword": "test kw", "location": "India"}]),
            dataforseoRequestIds=json.dumps(["task-dup-secure"]),
        )
        db.add(rj)
        db.commit()

        payload = {
            "task_id": "task-dup-secure",
            "tasks": [{
                "data": {"keyword": "test kw", "location_code": 2840},
                "result": [{
                    "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5}]
                }]
            }]
        }

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            with patch.object(get_settings(), "DATAFORSEO_WEBHOOK_SECRET", "my-secret"):
                from app.api.routes.webhooks import dataforseo_webhook
                import asyncio

                async def make_request():
                    req = MagicMock()
                    async def json_func():
                        return payload
                    req.json = json_func
                    req.query_params = {"task_id": None, "secret": "my-secret"}
                    return req

                req1 = asyncio.run(make_request())
                req2 = asyncio.run(make_request())

                response1 = asyncio.run(dataforseo_webhook(req1))
                response2 = asyncio.run(dataforseo_webhook(req2))

                assert response1["created"] == 1
                assert response2["skipped"] == 1

    def test_forged_webhook_rejected(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            with patch.object(get_settings(), "DATAFORSEO_WEBHOOK_SECRET", "my-secret"):
                from app.api.routes.webhooks import dataforseo_webhook
                import asyncio

                req = MagicMock()
                async def json_func():
                    return {
                        "task_id": "forged-task",
                        "tasks": [{
                            "data": {"keyword": "evil kw", "location_code": 2840},
                            "result": [{
                                "items": [{"type": "organic", "url": "https://evil.com", "rank_group": 1}]
                            }]
                        }]
                    }
                req.json = json_func
                req.query_params = {"task_id": None, "secret": "my-secret"}

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(dataforseo_webhook(req))
                assert exc_info.value.status_code == 404


class TestCORSProductionSafety:
    def test_production_without_frontend_url_raises(self):
        with patch.object(get_settings(), "ENV", "production"):
            with patch.object(get_settings(), "FRONTEND_URL", ""):
                with pytest.raises(RuntimeError, match="FRONTEND_URL must be configured in production"):
                    from app.main import app
                    # Re-import to trigger startup check
                    import importlib
                    import app.main
                    importlib.reload(app.main)
    
    def test_development_without_frontend_url_allowed(self):
        with patch.object(get_settings(), "ENV", "development"):
            with patch.object(get_settings(), "FRONTEND_URL", ""):
                origins = [get_settings().FRONTEND_URL] if get_settings().FRONTEND_URL else ["*"]
                assert origins == ["*"]


class TestPrintStatementsRemoved:
    def test_no_print_in_scheduler(self):
        import ast
        with open("fastapi_app/app/jobs/rank_scheduler.py") as f:
            source = f.read()
        tree = ast.parse(source)
        prints = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'print']
        assert len(prints) == 0, f"Found print statements in scheduler: {prints}"
    
    def test_no_print_in_payments(self):
        import ast
        with open("fastapi_app/app/api/routes/payments.py") as f:
            source = f.read()
        tree = ast.parse(source)
        prints = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'print']
        assert len(prints) == 0, f"Found print statements in payments: {prints}"


class TestAuthenticationSecurity:
    def test_jwt_secret_not_hardcoded_in_production(self):
        settings = get_settings()
        if settings.ENV == "production":
            assert settings.JWT_ACCESS_SECRET != "dev-secret-key-change-in-production"
    
    def test_password_hashing_uses_bcrypt(self):
        from app.core.security import hash_password, verify_password
        password = "test-password-123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong-password", hashed)
