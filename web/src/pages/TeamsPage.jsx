import { useState, useEffect } from "react";
import {
  createTeamApi,
  listTeamsApi,
  getTeamMembersApi,
  inviteTeamMemberApi,
  removeTeamMemberApi,
  deleteTeamApi,
  getTeamInvitesApi,
  cancelTeamInviteApi,
} from "../lib/api";
import { formatDate } from "../utils/date";
import { getStoredUser } from "../utils/auth";
import ConfirmModal from "../components/ConfirmModal";

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [teamInvites, setTeamInvites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [teamName, setTeamName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [creating, setCreating] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState("");
  const [showRemoveMemberConfirm, setShowRemoveMemberConfirm] = useState(false);
  const [showDeleteTeamConfirm, setShowDeleteTeamConfirm] = useState(false);
  const [memberToRemove, setMemberToRemove] = useState(null);
  const [currentUserRole, setCurrentUserRole] = useState(null);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await listTeamsApi();
      setTeams(result.data.teams || []);
    } catch (err) {
      setError(err?.message || "Failed to load teams");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!teamName.trim()) return;

    setCreating(true);
    setError("");

    try {
      await createTeamApi(teamName);
      setShowCreateModal(false);
      setTeamName("");
      await loadTeams();
    } catch (err) {
      setError(err?.message || "Failed to create team");
    } finally {
      setCreating(false);
    }
  };

  const handleSelectTeam = async (team) => {
    setSelectedTeam(team);
    setTeamMembers([]);
    setTeamInvites([]);
    
    try {
      const [membersResult, invitesResult] = await Promise.all([
        getTeamMembersApi(team.id),
        getTeamInvitesApi(team.id)
      ]);
      setTeamMembers(membersResult.data.members || []);
      setTeamInvites(invitesResult.data.invites || []);
      
      // Set current user's role
      const currentUser = membersResult.data.members?.find(m => m.userId === getStoredUser()?.id);
      setCurrentUserRole(currentUser?.role || null);
    } catch (err) {
      setError(err?.message || "Failed to load team details");
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim() || !selectedTeam) return;

    setInviting(true);
    setError("");

    try {
      await inviteTeamMemberApi(selectedTeam.id, inviteEmail, inviteRole);
      setShowInviteModal(false);
      setInviteEmail("");
      setInviteRole("member");
      // Reload invitations
      const invitesResult = await getTeamInvitesApi(selectedTeam.id);
      setTeamInvites(invitesResult.data.invites || []);
    } catch (err) {
      setError(err?.message || "Failed to invite team member");
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = (userId, userName) => {
    setMemberToRemove({ userId, userName });
    setShowRemoveMemberConfirm(true);
  };

  const confirmRemoveMember = async () => {
    if (!memberToRemove || !selectedTeam) return;

    setShowRemoveMemberConfirm(false);

    try {
      await removeTeamMemberApi(selectedTeam.id, memberToRemove.userId);
      const result = await getTeamMembersApi(selectedTeam.id);
      setTeamMembers(result.data.members || []);
    } catch (err) {
      setError(err?.message || "Failed to remove team member");
    }

    setMemberToRemove(null);
  };

  const handleCancelInvite = async (inviteId) => {
    if (!selectedTeam) return;
    
    try {
      await cancelTeamInviteApi(selectedTeam.id, inviteId);
      const result = await getTeamInvitesApi(selectedTeam.id);
      setTeamInvites(result.data.invites || []);
    } catch (err) {
      setError(err?.message || "Failed to cancel invitation");
    }
  };

  const handleDeleteTeam = async () => {
    if (!selectedTeam) return;
    setShowDeleteTeamConfirm(true);
  };

  const confirmDeleteTeam = async () => {
    if (!selectedTeam) return;
    
    setShowDeleteTeamConfirm(false);
    
    try {
      await deleteTeamApi(selectedTeam.id);
      setSelectedTeam(null);
      setTeamMembers([]);
      await loadTeams();
    } catch (err) {
      setError(err?.message || "Failed to delete team");
    }
  };

  const getRoleColor = (role) => {
    switch (role) {
      case "owner": return "bg-purple-100 text-purple-800";
      case "admin": return "bg-blue-100 text-blue-800";
      case "member": return "bg-green-100 text-green-800";
      case "viewer": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const canRemoveMember = (memberRole, currentUserRole) => {
    // Only owners and admins can remove members
    if (currentUserRole !== "owner" && currentUserRole !== "admin") return false;
    // Cannot remove owner
    if (memberRole === "owner") return false;
    // Admins cannot remove other admins (only owners can)
    if (currentUserRole === "admin" && memberRole === "admin") return false;
    return true;
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Teams</h1>
            <p className="text-slate-600">Collaborate with your team on SEO projects</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700"
          >
            Create Team
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Teams List */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Your Teams</h2>
            
            {loading ? (
              <p className="text-slate-600">Loading teams...</p>
            ) : teams.length === 0 ? (
              <p className="text-slate-600">No teams yet. Create your first team!</p>
            ) : (
              <div className="space-y-2">
                {teams.map((team) => (
                  <div
                    key={team.id}
                    onClick={() => handleSelectTeam(team)}
                    className={`p-4 rounded-lg cursor-pointer transition ${
                      selectedTeam?.id === team.id
                        ? "bg-blue-50 border-2 border-blue-500"
                        : "bg-slate-50 border-2 border-transparent hover:bg-slate-100"
                    }`}
                  >
                    <p className="font-medium text-slate-900">{team.name}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Created {formatDate(team.createdAt)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Team Details */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            {!selectedTeam ? (
              <div className="text-center py-8">
                <p className="text-slate-600">Select a team to view details</p>
              </div>
            ) : (
              <div>
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">{selectedTeam.name}</h2>
                    <p className="text-sm text-slate-600 mt-1">
                      Team ID: {selectedTeam.id}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowInviteModal(true)}
                      className="bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700"
                    >
                      Invite Member
                    </button>
                    <button
                      onClick={handleDeleteTeam}
                      className="bg-red-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-red-700"
                    >
                      Delete Team
                    </button>
                  </div>
                </div>

                <h3 className="text-lg font-semibold text-slate-900 mb-4">Team Members</h3>
                
                {teamMembers.length === 0 && teamInvites.length === 0 ? (
                  <p className="text-slate-600">No members yet. Invite someone to get started!</p>
                ) : (
                  <>
                    {teamMembers.length > 0 && (
                      <div className="space-y-3">
                        {teamMembers.map((member) => (
                          <div key={member.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                            <div>
                              <p className="font-medium text-slate-900">{member.userName}</p>
                              <p className="text-sm text-slate-600">{member.userEmail}</p>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getRoleColor(member.role)}`}>
                                {member.role}
                              </span>
                              {canRemoveMember(member.role, currentUserRole) && (
                                <button
                                  onClick={() => handleRemoveMember(member.userId, member.userName)}
                                  className="text-sm text-red-600 hover:text-red-900"
                                >
                                  Remove
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {teamInvites.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-medium text-slate-700 mb-3">Pending Invitations</h4>
                        <div className="space-y-2">
                          {teamInvites.map((invite) => (
                            <div key={invite.id} className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
                              <div>
                                <p className="font-medium text-slate-900">{invite.email}</p>
                                <p className="text-xs text-slate-600">
                                  Role: <span className="capitalize">{invite.role}</span> • 
                                  Expires: {formatDate(invite.expiresAt)}
                                </p>
                              </div>
                              <button
                                onClick={() => handleCancelInvite(invite.id)}
                                className="text-sm text-red-600 hover:text-red-900"
                              >
                                Cancel
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        <ConfirmModal
          isOpen={showRemoveMemberConfirm}
          onClose={() => setShowRemoveMemberConfirm(false)}
          onConfirm={confirmRemoveMember}
          title="Remove Team Member"
          message={`Are you sure you want to remove ${memberToRemove?.userName || 'this team member'} from the team?`}
        />

        <ConfirmModal
          isOpen={showDeleteTeamConfirm}
          onClose={() => setShowDeleteTeamConfirm(false)}
          onConfirm={confirmDeleteTeam}
          title="Delete Team"
          message="Are you sure you want to delete this team? This action cannot be undone."
        />

        {/* Create Team Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Create Team</h2>
              
              <form onSubmit={handleCreateTeam}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Team Name
                  </label>
                  <input
                    type="text"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    placeholder="e.g., Marketing Team"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {creating ? "Creating..." : "Create"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Invite Member Modal */}
        {showInviteModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Invite Team Member</h2>
              
              <form onSubmit={handleInvite}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@example.com"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Role
                  </label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>

                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowInviteModal(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={inviting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {inviting ? "Inviting..." : "Invite"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
