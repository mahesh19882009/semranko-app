import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamMemberAdd,
    TeamMemberUpdate,
    TeamResponse,
    TeamMemberResponse,
)
from app.services.team_service import (
    create_team,
    get_user_teams,
    get_team_by_id,
    get_team_members,
    add_team_member,
    update_team_member_role,
    remove_team_member,
    delete_team,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/")
async def create_team_endpoint(
    payload: TeamCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    team = create_team(db, current_user["id"], payload.name)
    members = get_team_members(db, team.id)
    member_list = [
        {
            "id": m.id,
            "team_id": m.teamId,
            "user_id": m.userId,
            "role": m.role,
            "joined_at": m.joinedAt.isoformat() if m.joinedAt else None,
            "user_name": m.user.name if m.user else None,
            "user_email": m.user.email if m.user else None,
        }
        for m in members
    ]
    return ok("Team created", {
        "id": team.id,
        "owner_id": team.ownerId,
        "name": team.name,
        "created_at": team.createdAt.isoformat() if team.createdAt else None,
        "members": member_list,
    })


@router.get("/")
async def list_teams(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    teams = get_user_teams(db, current_user["id"])
    result = []
    for team in teams:
        members = get_team_members(db, team.id)
        member_list = [
            {
                "id": m.id,
                "team_id": m.teamId,
                "user_id": m.userId,
                "role": m.role,
                "joined_at": m.joinedAt.isoformat() if m.joinedAt else None,
                "user_name": m.user.name if m.user else None,
                "user_email": m.user.email if m.user else None,
            }
            for m in members
        ]
        result.append({
            "id": team.id,
            "owner_id": team.ownerId,
            "name": team.name,
            "created_at": team.createdAt.isoformat() if team.createdAt else None,
            "members": member_list,
        })
    return ok("Teams retrieved", {"teams": result})


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = get_team_members(db, team_id)
    member_list = [
        {
            "id": m.id,
            "team_id": m.teamId,
            "user_id": m.userId,
            "role": m.role,
            "joined_at": m.joinedAt.isoformat() if m.joinedAt else None,
            "user_name": m.user.name if m.user else None,
            "user_email": m.user.email if m.user else None,
        }
        for m in members
    ]
    return ok("Team retrieved", {
        "id": team.id,
        "owner_id": team.ownerId,
        "name": team.name,
        "created_at": team.createdAt.isoformat() if team.createdAt else None,
        "members": member_list,
    })


@router.post("/{team_id}/members")
async def add_member(
    team_id: str,
    payload: TeamMemberAdd,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.ownerId != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only team owner can add members")
    
    # Query user by email to get UUID
    from app.db.models import User
    target_user = db.scalar(select(User).where(User.email == payload.email))
    if not target_user:
        raise HTTPException(status_code=404, detail="User account not registered on this system")
    
    member = add_team_member(db, team_id, target_user.id, payload.role)
    return ok("Member added", {
        "id": member.id,
        "team_id": member.teamId,
        "user_id": member.userId,
        "role": member.role,
        "joined_at": member.joinedAt.isoformat() if member.joinedAt else None,
        "user_name": target_user.name,
        "user_email": target_user.email,
    })


@router.put("/{team_id}/members/{user_id}")
async def update_member_role(
    team_id: str,
    user_id: str,
    payload: TeamMemberUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.ownerId != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only team owner can update members")
    member = update_team_member_role(db, team_id, user_id, payload.role)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return ok("Member updated", {
        "id": member.id,
        "team_id": member.teamId,
        "user_id": member.userId,
        "role": member.role,
    })


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.ownerId != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only team owner can remove members")
    success = remove_team_member(db, team_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return ok("Member removed")


@router.delete("/{team_id}")
async def delete_team_endpoint(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    success = delete_team(db, team_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Team not found or you are not the owner")
    return ok("Team deleted")
