'use client'
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import {
  createTeamApi,
  listTeamsApi,
  getTeamApi,
  addTeamMemberApi,
  updateTeamMemberRoleApi,
  removeTeamMemberApi,
} from "../features/pricing/pricingApi";
import { useSelector } from "react-redux";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Input from "../components/ui/Input";
import Badge from "../components/ui/Badge";
import { useToast } from "../components/ui/Toast";

const ROLE_OPTIONS = ["Owner", "Admin", "Editor", "Viewer"];

function RoleBadge({ role }) {
  const tone = role === "Owner" ? "primary" : role === "Admin" ? "primary" : role === "Editor" ? "info" : "secondary";
  return <Badge tone={tone}>{role}</Badge>;
}

export default function TeamPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const currentCreditBalance = pricingCurrent?.creditBalance ?? null;

  const [teams, setTeams] = useState([]);
  const [loadingTeams, setLoadingTeams] = useState(true);
  const [teamsError, setTeamsError] = useState(null);

  const [teamName, setTeamName] = useState("");
  const [loadingCreate, setLoadingCreate] = useState(false);

  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("Viewer");
  const [activeTeamId, setActiveTeamId] = useState(null);
  const [loadingAdd, setLoadingAdd] = useState(false);
  const [memberError, setMemberError] = useState(null);

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    loadTeams();
  }, [authenticated]);

  const loadTeams = async () => {
    setLoadingTeams(true);
    setTeamsError(null);
    try {
      const data = await listTeamsApi();
      setTeams(data?.teams || []);
      if (data?.teams?.length > 0 && !activeTeamId) {
        setActiveTeamId(data.teams[0].id);
      }
    } catch (err) {
      setTeamsError(err.message || "Failed to load teams");
    } finally {
      setLoadingTeams(false);
    }
  };

  const activeTeam = useMemo(
    () => teams.find((t) => t.id === activeTeamId),
    [teams, activeTeamId]
  );

  const isOwner = useMemo(() => {
    if (!activeTeam) return false;
    const storedUser = (() => {
      try {
        return JSON.parse(localStorage.getItem("user"));
      } catch {
        return null;
      }
    })();
    return storedUser?.id === activeTeam.owner_id;
  }, [activeTeam]);

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    setTeamsError(null);
    if (!teamName.trim()) {
      setTeamsError("Team name is required");
      addToast("Team name is required", "error");
      return;
    }
    setLoadingCreate(true);
    try {
      const data = await createTeamApi(teamName.trim());
      setTeams((prev) => [data, ...prev]);
      setActiveTeamId(data.id);
      setTeamName("");
      addToast("Team created successfully", "success");
    } catch (err) {
      setTeamsError(err.message || "Failed to create team");
      addToast(err.message || "Failed to create team", "error");
    } finally {
      setLoadingCreate(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!activeTeamId) return;
    setMemberError(null);
    if (!memberEmail.trim()) {
      setMemberError("Email is required");
      addToast("Email is required", "error");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(memberEmail.trim())) {
      setMemberError("Please enter a valid email");
      addToast("Please enter a valid email", "error");
      return;
    }
    setLoadingAdd(true);
    try {
      const data = await addTeamMemberApi(activeTeamId, memberEmail.trim(), memberRole);
      setTeams((prev) =>
        prev.map((team) =>
          team.id === activeTeamId
            ? {
                ...team,
                members: [...(team.members || []), data],
              }
            : team
        )
      );
      setMemberEmail("");
      setMemberRole("Viewer");
      addToast("Team member added successfully", "success");
    } catch (err) {
      setMemberError(err.message || "Failed to add member");
      addToast(err.message || "Failed to add member", "error");
    } finally {
      setLoadingAdd(false);
    }
  };

  const handleUpdateRole = async (teamId, userId, newRole) => {
    try {
      const data = await updateTeamMemberRoleApi(teamId, userId, newRole);
      setTeams((prev) =>
        prev.map((team) =>
          team.id === teamId
            ? {
                ...team,
                members: team.members.map((m) =>
                  m.user_id === userId ? { ...m, role: data.role } : m
                ),
              }
            : team
        )
      );
      addToast("Role updated successfully", "success");
    } catch (err) {
      addToast(err.message || "Failed to update role", "error");
    }
  };

  const handleRemoveMember = async (teamId, userId) => {
    try {
      await removeTeamMemberApi(teamId, userId);
      setTeams((prev) =>
        prev.map((team) =>
          team.id === teamId
            ? {
                ...team,
                members: team.members.filter((m) => m.user_id !== userId),
              }
            : team
        )
      );
      addToast("Member removed successfully", "success");
    } catch (err) {
      addToast(err.message || "Failed to remove member", "error");
    }
  };

  if (!authenticated) {
    return null;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Team Management</h1>
          <p className="mt-2 text-sm text-slate-500">
            Create teams, invite members, and manage roles.
          </p>
        </div>
        {isOwner && (
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <p className="text-xs font-medium text-slate-500">Team Credits</p>
            <p className="text-xl font-bold text-slate-900">
              {currentCreditBalance !== null && currentCreditBalance !== undefined
                ? currentCreditBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : '—'}
            </p>
          </div>
        )}
      </div>

      {teamsError && <Alert variant="error" message={teamsError} onDismiss={() => setTeamsError(null)} />}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Create / Add Member */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <h3 className="text-base font-semibold text-slate-900">Create Team</h3>
            <p className="mt-1 text-xs text-slate-500">Start a new team workspace.</p>
            <form onSubmit={handleCreateTeam} className="mt-4 space-y-3">
              <Input
                label="Team Name"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="e.g. Acme SEO"
              />
              <Button type="submit" loading={loadingCreate} fullWidth>
                Create Team
              </Button>
            </form>
          </Card>

          {activeTeam && isOwner && (
            <Card>
              <h3 className="text-base font-semibold text-slate-900">Add Member</h3>
              <p className="mt-1 text-xs text-slate-500">Invite a user to {activeTeam.name}.</p>
              <form onSubmit={handleAddMember} className="mt-4 space-y-3">
                <Input
                  label="Email"
                  type="email"
                  value={memberEmail}
                  onChange={(e) => setMemberEmail(e.target.value)}
                  placeholder="user@company.com"
                />
                <div>
                  <label className="text-sm font-medium text-slate-700">Role</label>
                  <select
                    value={memberRole}
                    onChange={(e) => setMemberRole(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-brand-600 focus:ring-brand-200"
                  >
                    {ROLE_OPTIONS.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </div>
                {memberError && <p className="text-xs text-danger">{memberError}</p>}
                <Button type="submit" loading={loadingAdd} fullWidth>
                  Add Member
                </Button>
              </form>
            </Card>
          )}
        </div>

        {/* Right: Team Directory */}
        <div className="lg:col-span-2">
          <Card padding="p-0">
            <div className="border-b border-slate-200 px-6 py-5">
              <h2 className="text-lg font-semibold text-slate-900">Team Directory</h2>
              <p className="mt-1 text-sm text-slate-500">
                {teams.length} team{teams.length === 1 ? "" : "s"} found
              </p>
            </div>

            {loadingTeams ? (
              <div className="p-6 space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-200" />
                ))}
              </div>
            ) : teams.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-sm text-slate-500">No teams yet. Create one to get started.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {teams.map((team) => {
                  const selected = team.id === activeTeamId;
                  return (
                    <div
                      key={team.id}
                      className={`cursor-pointer transition-colors ${selected ? "bg-brand-50/40" : "hover:bg-slate-50"}`}
                      onClick={() => setActiveTeamId(team.id)}
                    >
                      <div className="px-6 py-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">{team.name}</p>
                            <p className="text-xs text-slate-500">
                              {team.members?.length || 0} member{(team.members?.length || 0) === 1 ? "" : "s"}
                              {team.owner_id && ` • Owner`}
                            </p>
                          </div>
                          {selected && <Badge tone="primary">Active</Badge>}
                        </div>

                        {selected && team.members?.length > 0 && (
                          <div className="mt-4 space-y-2">
                            {team.members.map((member) => {
                              const memberIsOwner = member.user_id === team.owner_id;
                              return (
                                <div
                                  key={member.id}
                                  className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
                                >
                                  <div className="flex items-center gap-3">
                                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                                      {(member.user_name || member.user_email || "?")
                                        .slice(0, 2)
                                        .toUpperCase()}
                                    </div>
                                    <div>
                                      <p className="text-sm font-medium text-slate-900">
                                        {member.user_name || member.user_email || "Unknown User"}
                                      </p>
                                      <p className="text-xs text-slate-500">{member.user_email}</p>
                                    </div>
                                  </div>

                                  <div className="flex items-center gap-2">
                                    {memberIsOwner ? (
                                      <RoleBadge role="Owner" />
                                    ) : isOwner ? (
                                      <>
                                        <select
                                          value={member.role}
                                          onChange={(e) => {
                                            e.stopPropagation();
                                            handleUpdateRole(team.id, member.user_id, e.target.value);
                                          }}
                                          onClick={(e) => e.stopPropagation()}
                                          className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs outline-none focus:border-brand-600"
                                        >
                                          {ROLE_OPTIONS.map((role) => (
                                            <option key={role} value={role}>
                                              {role}
                                            </option>
                                          ))}
                                        </select>
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleRemoveMember(team.id, member.user_id);
                                          }}
                                          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-danger transition-colors"
                                          aria-label={`Remove ${member.user_email || "member"}`}
                                        >
                                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                            <path d="M2 4H12M5 4V3C5 2.44772 5.44772 2 6 2H8C8.55228 2 9 2.44772 9 3V4M11 4L10.364 10.364C10.2439 11.2971 9.44789 12 8.5 12H5.5C4.55211 12 3.75608 11.2971 3.636 10.364L3 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                          </svg>
                                        </button>
                                      </>
                                    ) : (
                                      <RoleBadge role={member.role} />
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
