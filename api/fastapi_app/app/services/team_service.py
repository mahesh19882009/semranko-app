import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Team, TeamMember, User
from app.services.credit_service import deduct_credits, refund_credits

logger = logging.getLogger(__name__)


def create_team(db: Session, owner_id: str, name: str) -> Team:
    existing_teams = db.scalars(select(Team).where(Team.ownerId == owner_id)).all()
    if len(existing_teams) >= 1:
        deduct_credits_for_team_action(
            db,
            owner_id,
            10,
            "New team created",
            f"Team creation: {name}",
        )

    team = Team(ownerId=owner_id, name=name)
    db.add(team)
    db.flush()

    member = TeamMember(teamId=team.id, userId=owner_id, role="Owner")
    db.add(member)
    db.flush()
    db.commit()
    return team


def get_user_teams(db: Session, user_id: str) -> list[Team]:
    owned = db.scalars(select(Team).where(Team.ownerId == user_id)).all()
    member_teams = db.scalars(
        select(Team).join(TeamMember, TeamMember.teamId == Team.id).where(TeamMember.userId == user_id)
    ).all()
    seen = set()
    result = []
    for team in list(owned) + list(member_teams):
        if team.id not in seen:
            seen.add(team.id)
            result.append(team)
    return result


def get_team_by_id(db: Session, team_id: str) -> Team | None:
    return db.scalar(select(Team).where(Team.id == team_id))


def get_team_members(db: Session, team_id: str) -> list[TeamMember]:
    return db.scalars(select(TeamMember).where(TeamMember.teamId == team_id)).all()


def add_team_member(db: Session, team_id: str, user_id: str, role: str = "Viewer") -> TeamMember:
    existing = db.scalar(
        select(TeamMember).where(
            TeamMember.teamId == team_id,
            TeamMember.userId == user_id,
        )
    )
    if existing:
        return existing

    team = db.scalar(select(Team).where(Team.id == team_id))
    if not team:
        raise ValueError("Team not found")

    current_members = db.scalars(
        select(TeamMember).where(
            TeamMember.teamId == team_id,
            TeamMember.userId != team.ownerId,
        )
    ).all()

    if len(current_members) >= 1:
        deduct_credits_for_team_action(
            db,
            team.ownerId,
            10,
            "Team member added",
            f"Team member added: {user_id}",
        )

    member = TeamMember(teamId=team_id, userId=user_id, role=role)
    db.add(member)
    db.flush()
    db.commit()
    return member


def update_team_member_role(db: Session, team_id: str, user_id: str, role: str) -> TeamMember | None:
    member = db.scalar(
        select(TeamMember).where(
            TeamMember.teamId == team_id,
            TeamMember.userId == user_id,
        )
    )
    if not member:
        return None
    member.role = role
    db.add(member)
    db.flush()
    db.commit()
    return member


def remove_team_member(db: Session, team_id: str, user_id: str) -> bool:
    member = db.scalar(
        select(TeamMember).where(
            TeamMember.teamId == team_id,
            TeamMember.userId == user_id,
        )
    )
    if not member:
        return False
    db.delete(member)
    db.flush()
    db.commit()
    return True


def delete_team(db: Session, team_id: str, owner_id: str) -> bool:
    team = db.scalar(select(Team).where(Team.id == team_id, Team.ownerId == owner_id))
    if not team:
        return False
    db.delete(team)
    db.flush()
    db.commit()
    return True


def get_team_owner_id(db: Session, user_id: str) -> str | None:
    team = db.scalar(select(Team).where(Team.ownerId == user_id))
    if team:
        return team.ownerId
    membership = db.scalar(select(TeamMember).where(TeamMember.userId == user_id))
    if membership:
        team = db.scalar(select(Team).where(Team.id == membership.teamId))
        if team:
            return team.ownerId
    return user_id


def deduct_credits_for_team_action(
    db: Session,
    user_id: str,
    amount: float,
    action_type: str,
    description: str,
    related_order_id: str | None = None,
) -> float:
    owner_id = get_team_owner_id(db, user_id)
    return deduct_credits(db, owner_id, amount, action_type, description, related_order_id)


def check_team_credits(db: Session, user_id: str, required: float) -> bool:
    owner_id = get_team_owner_id(db, user_id)
    from app.services.credit_service import check_credits
    return check_credits(db, owner_id, required)
