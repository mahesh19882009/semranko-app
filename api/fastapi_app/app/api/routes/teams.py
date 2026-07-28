from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.team_service import (
    create_team,
    get_user_teams,
    get_team,
    get_team_members,
    add_team_member,
    remove_team_member,
    update_team_member_role,
    delete_team,
    invite_user_to_team,
    get_team_invites,
    accept_team_invite,
    cancel_team_invite,
)

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str


class AddTeamMemberRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateTeamMemberRequest(BaseModel):
    role: str


@router.post("/create")
async def create_team_endpoint(
    request: CreateTeamRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new team
    """
    team = create_team(db, current_user["id"], request.name)
    
    return ok("Team created", {
        "id": team.id,
        "name": team.name,
        "ownerId": team.ownerId,
        "createdAt": team.createdAt.isoformat()
    })


@router.get("/list")
async def list_teams(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    List all teams for the current user
    """
    teams = get_user_teams(db, current_user["id"])
    
    teams_data = [
        {
            "id": team.id,
            "name": team.name,
            "ownerId": team.ownerId,
            "createdAt": team.createdAt.isoformat()
        }
        for team in teams
    ]
    
    return ok("Teams retrieved", {"teams": teams_data})


@router.get("/{team_id}")
async def get_team_endpoint(
    team_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific team
    """
    team = get_team(db, team_id, current_user["id"])
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return ok("Team retrieved", {
        "id": team.id,
        "name": team.name,
        "ownerId": team.ownerId,
        "createdAt": team.createdAt.isoformat()
    })


@router.get("/{team_id}/members")
async def get_team_members_endpoint(
    team_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all members of a team
    """
    # Verify user is a member
    team = get_team(db, team_id, current_user["id"])
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    members = get_team_members(db, team_id)
    
    return ok("Team members retrieved", {"members": members})


@router.post("/{team_id}/invite")
async def invite_team_member_endpoint(
    team_id: str,
    request: AddTeamMemberRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Invite a user to a team by email
    """
    result = invite_user_to_team(db, team_id, request.email, request.role, current_user["id"])
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ok("User invited to team", {
        "success": True,
        "invite": result.get("invite")
    })


@router.put("/{team_id}/members/{user_id}/role")
async def update_team_member_role_endpoint(
    team_id: str,
    user_id: str,
    request: UpdateTeamMemberRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a team member's role
    """
    success = update_team_member_role(db, team_id, user_id, request.role, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update member role")
    
    return ok("Member role updated", {"success": True})


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member_endpoint(
    team_id: str,
    user_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a member from a team
    """
    result = remove_team_member(db, team_id, user_id, current_user["id"])
    
    if not result:
        # Check specific failure reason
        requesting_member = db.execute(
            select(TeamMember)
            .where(TeamMember.teamId == team_id)
            .where(TeamMember.userId == current_user["id"])
        ).scalar_one_or_none()
        
        if not requesting_member or requesting_member.role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Only admins and owners can remove team members")
        
        team = db.execute(
            select(Team)
            .where(Team.id == team_id)
        ).scalar_one_or_none()
        
        if team and team.ownerId == user_id:
            raise HTTPException(status_code=400, detail="Cannot remove the team owner")
        
        raise HTTPException(status_code=400, detail="Failed to remove member")
    
    return ok("Member removed", {"success": True})


@router.delete("/{team_id}")
async def delete_team_endpoint(
    team_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a team
    """
    success = delete_team(db, team_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete team")
    
    return ok("Team deleted", {"success": True})


@router.get("/{team_id}/invites")
async def get_team_invites_endpoint(
    team_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all pending invitations for a team
    """
    # Verify user is a member of the team
    team = get_team(db, team_id, current_user["id"])
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    invites = get_team_invites(db, team_id)
    return ok("Team invitations retrieved", {"invites": invites})


@router.post("/{team_id}/invites/{invite_id}/accept")
async def accept_team_invite_endpoint(
    team_id: str,
    invite_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Accept a team invitation
    """
    result = accept_team_invite(db, invite_id, current_user["id"])
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ok(result["message"], {"success": True})


@router.delete("/{team_id}/invites/{invite_id}")
async def cancel_team_invite_endpoint(
    team_id: str,
    invite_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a team invitation
    """
    result = cancel_team_invite(db, invite_id, team_id, current_user["id"])
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ok(result["message"], {"success": True})
