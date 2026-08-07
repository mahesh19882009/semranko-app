"""
One-time cleanup script to remove duplicate CreditLedger entries created by
credit top-up order creation + verify-credit-payment + razorpay-webhook.

For each relatedOrderId, this keeps the earliest ledger entry and removes
later duplicates so each payment order maps to exactly one successful ledger row.
"""
import logging
import sys
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CreditLedger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = get_settings()
    database_url = settings.SQLALCHEMY_DATABASE_URI
    if not database_url:
        logger.error("DATABASE_URL is not configured")
        sys.exit(1)

    engine = create_engine(database_url)
    with Session(engine) as db:
        dup_groups = (
            db.query(
                CreditLedger.relatedOrderId,
                func.count(CreditLedger.id).label("count"),
            )
            .filter(CreditLedger.relatedOrderId.isnot(None))
            .group_by(CreditLedger.relatedOrderId)
            .having(func.count(CreditLedger.id) > 1)
            .all()
        )

        logger.info("Found %d order_ids with duplicate ledger entries", len(dup_groups))

        deleted = 0
        for order_id, count in dup_groups:
            entries = (
                db.query(CreditLedger)
                .filter(CreditLedger.relatedOrderId == order_id)
                .order_by(CreditLedger.createdAt.asc(), CreditLedger.id.asc())
                .all()
            )

            keeper = entries[0]
            duplicates = entries[1:]
            logger.info(
                "order_id=%s: keeping id=%s createdAt=%s, deleting %d duplicates",
                order_id,
                keeper.id,
                keeper.createdAt,
                len(duplicates),
            )

            for dup in duplicates:
                db.delete(dup)
                deleted += 1

        db.commit()
        logger.info("Deleted %d duplicate ledger entries", deleted)


if __name__ == "__main__":
    main()
