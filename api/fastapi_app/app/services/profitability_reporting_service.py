"""
Profitability Reporting Service

Calculates gross profit and margin per pricing plan using:
- Actual configured plan prices
- Actual credit consumption from CreditLedger
- Actual DataForSEO costs from DataForSEOCost
- External DataForSEO pricing for estimation where actual data is missing
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.models import User, Subscription, DataForSEOCost, CreditLedger, Keyword, Project
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_plan_revenue(db: Session, plan_key: str, days: int = 30) -> float:
    """Calculate total revenue for a plan in the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    subscriptions = db.scalars(
        select(Subscription)
        .where(Subscription.planId == plan_key)
        .where(Subscription.status == "active")
        .where(Subscription.createdAt >= cutoff)
    ).all()
    
    revenue = 0.0
    for sub in subscriptions:
        plan_def = settings.plan_config.plans.get(plan_key)
        if plan_def:
            if sub.billingCycle == "yearly":
                revenue += plan_def.yearly_price_inr / 12
            else:
                revenue += plan_def.monthly_price_inr
    
    return revenue


def _get_dfs_cost_by_plan(db: Session, plan_key: str, days: int = 30) -> dict:
    """Calculate DataForSEO costs for a plan in the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    users = db.scalars(
        select(User.id).where(User.selectedPlan == plan_key)
    ).all()
    
    if not users:
        return {
            "total_estimated_usd": 0.0,
            "total_estimated_inr": 0.0,
            "request_count": 0,
            "cache_hit_count": 0,
            "by_endpoint": {},
        }
    
    costs = db.scalars(
        select(DataForSEOCost)
        .where(DataForSEOCost.userId.in_(users))
        .where(DataForSEOCost.createdAt >= cutoff)
    ).all()
    
    total_estimated_usd = 0.0
    request_count = 0
    cache_hit_count = 0
    by_endpoint = {}
    
    for cost in costs:
        meta = cost.meta or {}
        cache_hit = meta.get("cache_hit", False)
        
        if cache_hit:
            cache_hit_count += 1
            continue
        
        estimated_cost = float(cost.costCredits or 0.0)
        total_estimated_usd += estimated_cost
        request_count += 1
        
        endpoint = cost.endpoint or "unknown"
        if endpoint not in by_endpoint:
            by_endpoint[endpoint] = {
                "count": 0,
                "estimated_usd": 0.0,
                "keyword_count": cost.keywordCount or 0,
            }
        by_endpoint[endpoint]["count"] += 1
        by_endpoint[endpoint]["estimated_usd"] += estimated_cost
        by_endpoint[endpoint]["keyword_count"] += cost.keywordCount or 0
    
    conversion = getattr(settings.plan_config, "conversion", None)
    usd_to_inr = getattr(conversion, "usd_to_inr", 95.23) if conversion else 95.23
    
    return {
        "total_estimated_usd": total_estimated_usd,
        "total_estimated_inr": total_estimated_usd * usd_to_inr,
        "request_count": request_count,
        "cache_hit_count": cache_hit_count,
        "by_endpoint": by_endpoint,
    }


def _get_credit_usage_by_plan(db: Session, plan_key: str, days: int = 30) -> dict:
    """Calculate credit consumption for a plan in the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    users = db.scalars(
        select(User.id).where(User.selectedPlan == plan_key)
    ).all()
    
    if not users:
        return {
            "total_consumed": 0.0,
            "total_reserved": 0.0,
            "total_refunded": 0.0,
            "action_types": {},
        }
    
    ledgers = db.scalars(
        select(CreditLedger)
        .where(CreditLedger.userId.in_(users))
        .where(CreditLedger.timestamp >= cutoff)
    ).all()
    
    total_consumed = 0.0
    total_reserved = 0.0
    total_refunded = 0.0
    action_types = {}
    
    for entry in ledgers:
        action = entry.actionType or "unknown"
        if action not in action_types:
            action_types[action] = {
                "count": 0,
                "total_amount": 0.0,
            }
        
        action_types[action]["count"] += 1
        action_types[action]["total_amount"] += float(entry.amount or 0.0)
        
        if action == "charge":
            total_consumed += float(entry.amount or 0.0)
        elif action == "reservation":
            total_reserved += float(entry.amount or 0.0)
        elif action == "refund":
            total_refunded += float(entry.amount or 0.0)
    
    return {
        "total_consumed": abs(total_consumed),
        "total_reserved": total_reserved,
        "total_refunded": total_refunded,
        "action_types": action_types,
    }


def calculate_plan_profitability(db: Session, plan_key: str, days: int = 30) -> dict:
    """Calculate profitability metrics for a single plan."""
    plan_def = settings.plan_config.plans.get(plan_key)
    if not plan_def:
        return {"error": f"Plan {plan_key} not found"}
    
    revenue = _get_plan_revenue(db, plan_key, days)
    dfs_cost = _get_dfs_cost_by_plan(db, plan_key, days)
    credit_usage = _get_credit_usage_by_plan(db, plan_key, days)
    
    gross_profit = revenue - dfs_cost["total_estimated_inr"]
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0
    
    return {
        "plan_key": plan_key,
        "plan_name": plan_def.name,
        "monthly_price_inr": plan_def.monthly_price_inr,
        "yearly_price_inr": plan_def.yearly_price_inr,
        "monthly_credits": plan_def.monthly_credits,
        "keyword_limit": plan_def.keyword_limit,
        "domain_limit": plan_def.domain_limit,
        "period_days": days,
        "revenue_inr": round(revenue, 2),
        "dataforseo_cost": {
            "estimated_usd": round(dfs_cost["total_estimated_usd"], 4),
            "estimated_inr": round(dfs_cost["total_estimated_inr"], 2),
            "request_count": dfs_cost["request_count"],
            "cache_hit_count": dfs_cost["cache_hit_count"],
            "by_endpoint": {
                k: {
                    "count": v["count"],
                    "estimated_usd": round(v["estimated_usd"], 4),
                    "keyword_count": v["keyword_count"],
                }
                for k, v in dfs_cost["by_endpoint"].items()
            },
        },
        "credit_usage": {
            "total_consumed": round(credit_usage["total_consumed"], 2),
            "total_reserved": round(credit_usage["total_reserved"], 2),
            "total_refunded": round(credit_usage["total_refunded"], 2),
            "action_types": {
                k: {
                    "count": v["count"],
                    "total_amount": round(v["total_amount"], 2),
                }
                for k, v in credit_usage["action_types"].items()
            },
        },
        "gross_profit_inr": round(gross_profit, 2),
        "gross_margin_percent": round(gross_margin, 2),
        "profit_loss": "PROFIT" if gross_profit > 0 else "LOSS",
    }


def calculate_all_plans_profitability(db: Session, days: int = 30) -> dict:
    """Calculate profitability for all configured plans."""
    results = {}
    for plan_key in settings.plan_config.plans:
        if plan_key == "enterprise":
            continue
        results[plan_key] = calculate_plan_profitability(db, plan_key, days)
    return results


def get_profitability_summary(db: Session, days: int = 30) -> dict:
    """Get a summary of profitability across all plans."""
    plans = settings.plan_config.plans
    total_revenue = 0.0
    total_dfs_cost = 0.0
    total_gross_profit = 0.0
    plan_summaries = []
    
    for plan_key, plan_def in plans.items():
        if plan_key == "enterprise":
            continue
        
        result = calculate_plan_profitability(db, plan_key, days)
        plan_summaries.append(result)
        
        total_revenue += result.get("revenue_inr", 0.0)
        total_dfs_cost += result.get("dataforseo_cost", {}).get("estimated_inr", 0.0)
        total_gross_profit += result.get("gross_profit_inr", 0.0)
    
    overall_margin = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    
    return {
        "period_days": days,
        "total_plans": len(plan_summaries),
        "total_revenue_inr": round(total_revenue, 2),
        "total_dfs_cost_inr": round(total_dfs_cost, 2),
        "total_gross_profit_inr": round(total_gross_profit, 2),
        "overall_gross_margin_percent": round(overall_margin, 2),
        "plans": plan_summaries,
    }
