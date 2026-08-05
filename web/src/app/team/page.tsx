"use client";

import { useEffect, useState } from "react";
import {
  createTeam,
  createTeamInvite,
  createTeamRubric,
  createTeamScenario,
  deleteTeamRubric,
  deleteTeamScenario,
  getTeam,
  listTeamRubrics,
  listTeamScenarios,
  listTeamsForUser,
  removeTeamMember,
  updateMemberRole,
  type TeamOut,
  type TeamRubricOut,
  type TeamScenarioOut,
  type TeamWithMembersOut,
} from "@/lib/api";
import { getStoredUserId } from "@/lib/localUser";

function shareUrl(path: string): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}${path}`;
}

export default function TeamPage() {
  const [userId, setUserId] = useState<string | null | undefined>(undefined);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [selected, setSelected] = useState<TeamWithMembersOut | null>(null);
  const [scenarios, setScenarios] = useState<TeamScenarioOut[]>([]);
  const [rubrics, setRubrics] = useState<TeamRubricOut[]>([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [scenarioPrompt, setScenarioPrompt] = useState("");
  const [rubricName, setRubricName] = useState("");
  const [rubricCriteria, setRubricCriteria] = useState("");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(() => setUserId(getStoredUserId()));
  }, []);

  useEffect(() => {
    if (!userId) return;
    listTeamsForUser(userId)
      .then((fetched) => {
        setTeams(fetched);
        if (fetched.length > 0) refreshTeam(fetched[0].id);
      })
      .catch(() => setTeams([]));
  }, [userId]);

  async function refreshTeam(teamId: string) {
    const [team, teamScenarios, teamRubrics] = await Promise.all([
      getTeam(teamId),
      listTeamScenarios(teamId),
      listTeamRubrics(teamId),
    ]);
    setSelected(team);
    setScenarios(teamScenarios);
    setRubrics(teamRubrics);
  }

  async function handleCreateTeam() {
    if (!userId || !newTeamName.trim()) return;
    setError(null);
    try {
      const team = await createTeam(newTeamName.trim(), userId);
      setNewTeamName("");
      setTeams((prev) => [...prev, { id: team.id, name: team.name, created_at: team.created_at }]);
      await refreshTeam(team.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't create team");
    }
  }

  async function handleInvite() {
    if (!selected) return;
    try {
      const invite = await createTeamInvite(selected.id, "member");
      setInviteLink(shareUrl(`/team/join/${invite.token}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't create invite");
    }
  }

  async function handleRemoveMember(memberId: string) {
    if (!selected) return;
    await removeTeamMember(selected.id, memberId);
    await refreshTeam(selected.id);
  }

  async function handleRoleChange(memberId: string, role: "admin" | "member") {
    if (!selected) return;
    await updateMemberRole(selected.id, memberId, role);
    await refreshTeam(selected.id);
  }

  async function handleCreateScenario() {
    if (!selected || !scenarioTitle.trim() || !scenarioPrompt.trim()) return;
    await createTeamScenario(selected.id, scenarioTitle.trim(), scenarioPrompt.trim());
    setScenarioTitle("");
    setScenarioPrompt("");
    setScenarios(await listTeamScenarios(selected.id));
  }

  async function handleDeleteScenario(scenarioId: string) {
    if (!selected) return;
    await deleteTeamScenario(selected.id, scenarioId);
    setScenarios(await listTeamScenarios(selected.id));
  }

  async function handleCreateRubric() {
    if (!selected || !rubricName.trim() || !rubricCriteria.trim()) return;
    const criteria = rubricCriteria
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    await createTeamRubric(selected.id, rubricName.trim(), criteria);
    setRubricName("");
    setRubricCriteria("");
    setRubrics(await listTeamRubrics(selected.id));
  }

  async function handleDeleteRubric(rubricId: string) {
    if (!selected) return;
    await deleteTeamRubric(selected.id, rubricId);
    setRubrics(await listTeamRubrics(selected.id));
  }

  if (userId === undefined) return <div className="container">Loading…</div>;
  if (userId === null) {
    return (
      <div className="container stack">
        <h1>Team workspaces</h1>
        <p>No account on this device yet — start a practice session first.</p>
      </div>
    );
  }

  return (
    <div className="container stack">
      <h1>Team workspaces (§4.3)</h1>
      <p style={{ color: "var(--muted)" }}>
        No login system exists in this app yet — anyone with a team ID and a user ID can act on
        it. Roles are tracked for the UI, not enforced as real access control.
      </p>

      {error && <p className="error-banner">{error}</p>}

      <div className="card stack">
        <p>Your teams</p>
        <div className="row">
          {teams.map((t) => (
            <button
              key={t.id}
              className="btn"
              style={selected?.id === t.id ? { borderColor: "var(--accent)", fontWeight: 600 } : undefined}
              onClick={() => refreshTeam(t.id)}
            >
              {t.name}
            </button>
          ))}
        </div>
        <input
          className="btn"
          style={{ textAlign: "left", cursor: "text" }}
          placeholder="New team name"
          value={newTeamName}
          onChange={(e) => setNewTeamName(e.target.value)}
        />
        <button className="btn btn-primary" onClick={handleCreateTeam}>
          Create team
        </button>
      </div>

      {selected && (
        <>
          <div className="card stack">
            <div className="pill">Members</div>
            {selected.members.map((m) => (
              <div key={m.user_id} className="row" style={{ alignItems: "center", gap: 8 }}>
                <span style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{m.user_id}</span>
                <span className="pill">{m.role}</span>
                <button
                  className="btn"
                  onClick={() => handleRoleChange(m.user_id, m.role === "admin" ? "member" : "admin")}
                >
                  Make {m.role === "admin" ? "member" : "admin"}
                </button>
                <button className="btn btn-danger" onClick={() => handleRemoveMember(m.user_id)}>
                  Remove
                </button>
              </div>
            ))}
            <button className="btn" onClick={handleInvite}>
              Generate invite link
            </button>
            {inviteLink && <p style={{ wordBreak: "break-all" }}>{inviteLink}</p>}
          </div>

          <div className="card stack">
            <div className="pill">Custom scenarios</div>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
              Real practice prompts your team can use — shown in Practice Studio like any built-in
              context.
            </p>
            {scenarios.map((s) => (
              <div key={s.id} className="feedback-item">
                <div className="criterion">{s.title}</div>
                <p>{s.prompt}</p>
                <button className="btn btn-danger" onClick={() => handleDeleteScenario(s.id)}>
                  Delete
                </button>
              </div>
            ))}
            <input
              className="btn"
              style={{ textAlign: "left", cursor: "text" }}
              placeholder="Title"
              value={scenarioTitle}
              onChange={(e) => setScenarioTitle(e.target.value)}
            />
            <input
              className="btn"
              style={{ textAlign: "left", cursor: "text" }}
              placeholder="Prompt"
              value={scenarioPrompt}
              onChange={(e) => setScenarioPrompt(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleCreateScenario}>
              Add scenario
            </button>
          </div>

          <div className="card stack">
            <div className="pill">Custom rubrics</div>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
              Stored and manageable for real — not yet consumed by scoring, since the mock LLM
              rubric evaluator ignores rubric criteria entirely (see README §4.3).
            </p>
            {rubrics.map((r) => (
              <div key={r.id} className="feedback-item">
                <div className="criterion">{r.name}</div>
                <p>{r.criteria.join(", ")}</p>
                <button className="btn btn-danger" onClick={() => handleDeleteRubric(r.id)}>
                  Delete
                </button>
              </div>
            ))}
            <input
              className="btn"
              style={{ textAlign: "left", cursor: "text" }}
              placeholder="Rubric name"
              value={rubricName}
              onChange={(e) => setRubricName(e.target.value)}
            />
            <input
              className="btn"
              style={{ textAlign: "left", cursor: "text" }}
              placeholder="Criteria, comma-separated"
              value={rubricCriteria}
              onChange={(e) => setRubricCriteria(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleCreateRubric}>
              Add rubric
            </button>
          </div>
        </>
      )}
    </div>
  );
}
