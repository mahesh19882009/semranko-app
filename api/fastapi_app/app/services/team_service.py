from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Team, TeamMember, TeamInvite, User, Project
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_team(db: Session, owner_id: str, name: str) -> Team:
    """
    Create a new team
    """
    team = Team(
        name=name,
        ownerId=owner_id
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add owner as team member with admin role
    add_team_member(db, team.id, owner_id, "admin")
    
    return team


def get_user_teams(db: Session, user_id: str) -> List[Team]:
    """
    Get all teams for a user
    """
    return db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.teamId)
        .where(TeamMember.userId == user_id)
        .order_by(Team.createdAt.desc())
    ).scalars().all()


def get_team(db: Session, team_id: str, user_id: str) -> Optional[Team]:
    """
    Get a specific team (if user is a member)
    """
    # Check if user is a member of the team
    membership = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == user_id)
    ).scalar_one_or_none()
    
    if not membership:
        return None
    
    return db.execute(
        select(Team)
        .where(Team.id == team_id)
    ).scalar_one_or_none()


def add_team_member(db: Session, team_id: str, user_id: str, role: str = "member") -> TeamMember:
    """
    Add a member to a team
    """
    # Check if already a member
    existing = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == user_id)
    ).scalar_one_or_none()
    
    if existing:
        return existing
    
    member = TeamMember(
        teamId=team_id,
        userId=user_id,
        role=role
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    return member


def get_team_members(db: Session, team_id: str) -> List[dict]:
    """
    Get all members of a team
    """
    members = db.execute(
        select(TeamMember, User)
        .join(User, TeamMember.userId == User.id)
        .where(TeamMember.teamId == team_id)
    ).all()
    
    return [
        {
            "id": member.id,
            "userId": member.userId,
            "userName": user.name,
            "userEmail": user.email,
            "role": member.role,
            "joinedAt": member.joinedAt.isoformat()
        }
        for member, user in members
    ]


def remove_team_member(db: Session, team_id: str, user_id: str, requesting_user_id: str) -> bool:
    """
    Remove a member from a team
    Only admins or owners can remove members
    """
    # Check if requesting user is admin or owner
    requesting_member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == requesting_user_id)
    ).scalar_one_or_none()
    
    if not requesting_member or requesting_member.role not in ["admin", "owner"]:
        return False
    
    # Cannot remove owner
    team = db.execute(
        select(Team)
        .where(Team.id == team_id)
    ).scalar_one_or_none()
    
    if team and team.ownerId == user_id:
        return False
    
    # Remove member
    member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == user_id)
    ).scalar_one_or_none()
    
    if member:
        db.delete(member)
        db.commit()
        return True
    
    return False


def update_team_member_role(db: Session, team_id: str, user_id: str, new_role: str, requesting_user_id: str) -> bool:
    """
    Update a team member's role
    Only admins or owners can update roles
    """
    # Check if requesting user is admin or owner
    requesting_member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == requesting_user_id)
    ).scalar_one_or_none()
    
    if not requesting_member or requesting_member.role not in ["admin", "owner"]:
        return False
    
    # Update member role
    member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == user_id)
    ).scalar_one_or_none()
    
    if member:
        member.role = new_role
        db.commit()
        return True
    
    return False


def delete_team(db: Session, team_id: str, user_id: str) -> bool:
    """
    Delete a team (only owner can delete)
    """
    team = db.execute(
        select(Team)
        .where(Team.id == team_id)
    ).scalar_one_or_none()
    
    if not team:
        raise ValueError("Team not found")
    
    if team.ownerId != user_id:
        raise ValueError("Only the team owner can delete this team")
    
    db.delete(team)
    db.commit()
    
    return True


def invite_user_to_team(db: Session, team_id: str, email: str, role: str, inviting_user_id: str) -> dict:
    """
    Invite a user to a team by email
    Creates a pending invitation that can be accepted later
    """
    # Check if inviting user is admin or owner
    inviting_member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == inviting_user_id)
    ).scalar_one_or_none()
    
    if not inviting_member or inviting_member.role not in ["admin", "owner"]:
        return {"success": False, "message": "Only admins can invite users"}
    
    # Check if user already exists and is already a member
    existing_user = db.execute(
        select(User)
        .where(User.email == email)
    ).scalar_one_or_none()
    
    if existing_user:
        # Check if already a member
        existing_member = db.execute(
            select(TeamMember)
            .where(TeamMember.teamId == team_id)
            .where(TeamMember.userId == existing_user.id)
        ).scalar_one_or_none()
        
        if existing_member:
            return {"success": False, "message": "User is already a member of this team"}
    
    # Check if there's already a pending invitation
    existing_invite = db.execute(
        select(TeamInvite)
        .where(TeamInvite.teamId == team_id)
        .where(TeamInvite.email == email)
        .where(TeamInvite.status == "pending")
    ).scalar_one_or_none()
    
    if existing_invite:
        return {"success": False, "message": "User already has a pending invitation"}
    
    # Create invitation (expires in 7 days)
    invite = TeamInvite(
        teamId=team_id,
        email=email,
        role=role,
        invitedBy=inviting_user_id,
        status="pending",
        expiresAt=datetime.now() + timedelta(days=7)
    )
    
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    # TODO: Send email invitation here
    
    return {
        "success": True, 
        "message": "Invitation sent successfully",
        "invite": {
            "id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "status": invite.status,
            "expiresAt": invite.expiresAt.isoformat(),
            "createdAt": invite.createdAt.isoformat()
        }
    }


def get_team_invites(db: Session, team_id: str) -> List[dict]:
    """
    Get all pending invitations for a team
    """
    invites = db.execute(
        select(TeamInvite)
        .where(TeamInvite.teamId == team_id)
        .where(TeamInvite.status == "pending")
        .order_by(TeamInvite.createdAt.desc())
    ).scalars().all()
    
    return [
        {
            "id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "invitedBy": invite.invitedBy,
            "status": invite.status,
            "expiresAt": invite.expiresAt.isoformat(),
            "createdAt": invite.createdAt.isoformat()
        }
        for invite in invites
    ]


def accept_team_invite(db: Session, invite_id: str, user_id: str) -> dict:
    """
    Accept a team invitation
    """
    invite = db.execute(
        select(TeamInvite)
        .where(TeamInvite.id == invite_id)
        .where(TeamInvite.status == "pending")
    ).scalar_one_or_none()
    
    if not invite:
        return {"success": False, "message": "Invitation not found or expired"}
    
    # Check if invitation email matches user's email
    user = db.execute(
        select(User)
        .where(User.id == user_id)
    ).scalar_one_or_none()
    
    if not user or user.email != invite.email:
        return {"success": False, "message": "This invitation is for a different email address"}
    
    # Check if not expired
    if invite.expiresAt < datetime.now():
        invite.status = "expired"
        db.commit()
        return {"success": False, "message": "Invitation has expired"}
    
    # Add user to team
    add_team_member(db, invite.teamId, user_id, invite.role)
    
    # Mark invitation as accepted
    invite.status = "accepted"
    db.commit()
    
    return {"success": True, "message": "Successfully joined the team"}


def cancel_team_invite(db: Session, invite_id: str, team_id: str, requesting_user_id: str) -> dict:
    """
    Cancel a team invitation (only admins/owners)
    """
    # Check if requesting user is admin or owner
    requesting_member = db.execute(
        select(TeamMember)
        .where(TeamMember.teamId == team_id)
        .where(TeamMember.userId == requesting_user_id)
    ).scalar_one_or_none()
    
    if not requesting_member or requesting_member.role not in ["admin", "owner"]:
        return {"success": False, "message": "Only admins can cancel invitations"}
    
    invite = db.execute(
        select(TeamInvite)
        .where(TeamInvite.id == invite_id)
        .where(TeamInvite.teamId == team_id)
    ).scalar_one_or_none()
    
    if not invite:
        return {"success": False, "message": "Invitation not found"}
    
    invite.status = "cancelled"
    db.commit()
    
    return {"success": True, "message": "Invitation cancelled"}
