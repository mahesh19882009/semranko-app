import random
from datetime import datetime

from sqlalchemy import delete

from app.db.models import RankResult
from app.db.session import SessionLocal


def fake_rank_lookup(keyword: dict, domain: str) -> dict:
    position = random.randint(1, 50)
    return {
        "position": position,
        "url": f"https://{domain}",
        "keywordText": keyword["keyword"],
        "location": keyword.get("location") or "India",
        "device": keyword.get("device") or "desktop",
    }


def process_rank_check_job(project_id: str, domain: str, keywords: list[dict]) -> dict:
    if not project_id or not domain or not isinstance(keywords, list):
        raise ValueError("Invalid job payload")

    rows = []
    for keyword in keywords:
        result = fake_rank_lookup(keyword, domain)
        rows.append(
            {
                "projectId": project_id,
                "keywordId": keyword.get("id"),
                "keywordText": result["keywordText"],
                "position": result["position"],
                "url": result["url"],
                "location": result["location"],
                "device": result["device"],
                "checkedAt": datetime.utcnow(),
            }
        )

    db = SessionLocal()
    try:
        for keyword in keywords:
            db.execute(
                delete(RankResult).where(
                    RankResult.projectId == project_id,
                    RankResult.keywordId == keyword.get("id"),
                )
            )

        if rows:
            db.bulk_insert_mappings(RankResult, rows)

        db.commit()
        return {"inserted": len(rows)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
