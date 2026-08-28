import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getTeam, getTeamMembers, inviteMember } from "../services/teamService.js";
import { listProposals, createProposal } from "../services/proposalService.js";
import { getChallenge } from "../services/challengeService.js";
import { getInstitution } from "../services/institutionService.js";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { ProposalRow } from "../components/ProposalRow.jsx";
import { Modal } from "../components/Modal.jsx";

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function InviteForm({ teamId, onInvited }) {
  const [userId, setUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (!userId.trim()) return;
    setBusy(true);
    setError(null);
    setSuccess(false);
    try {
      await inviteMember(teamId, userId.trim());
      setUserId("");
      setSuccess(true);
      onInvited();
    } catch (err) {
      setError(err.message || "Could not send the invitation. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="invite-form">
      <form onSubmit={submit} noValidate>
        <div className="form-label-wrapper">
          <label htmlFor="invite-user-id" className="form-label">
            Member user ID
          </label>
          <span className="form-helper">
            The invite API references users by their account ID (no person
            search exists yet). The invitee must belong to this team's
            institution.
          </span>
        </div>
        <div className="invite-form-row">
          <input
            id="invite-user-id"
            className="form-control"
            value={userId}
            onChange={(event) => {
              setUserId(event.target.value);
              setError(null);
            }}
            placeholder="Paste the member's user ID (UUID)"
            maxLength={64}
            required
          />
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Inviting…" : "Invite"}
          </button>
        </div>
        {error && (
          <p className="form-error-msg" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="form-success-msg" role="status">
            Invitation sent. It will appear once the colleague accepts.
          </p>
        )}
      </form>
    </div>
  );
}

const PROPOSAL_FIELDS = [
  { key: "title", label: "Title", required: true, kind: "input" },
  { key: "summary", label: "Summary", required: true, kind: "textarea" },
  { key: "approach", label: "Approach", required: false, kind: "textarea" },
  { key: "resources_needed", label: "Resources needed", required: false, kind: "textarea" },
  { key: "timeline", label: "Timeline", required: false, kind: "textarea" },
];

function NewProposalModal({ team, onClose, onCreated }) {
  const initial = Object.fromEntries(
    PROPOSAL_FIELDS.map((field) => [field.key, ""])
  );
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const update = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
    setError(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        team_id: team.id,
        challenge_id: team.challenge_id,
        title: form.title.trim(),
        summary: form.summary.trim(),
        approach: form.approach.trim() || undefined,
        resources_needed: form.resources_needed.trim() || undefined,
        timeline: form.timeline.trim() || undefined,
      };
      const created = await createProposal(payload);
      onCreated(created);
    } catch (err) {
      setError(err.message || "Could not create the proposal. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal open title="New proposal draft" onClose={onClose} wide>
      <form onSubmit={submit} noValidate>
        {PROPOSAL_FIELDS.map((field) => (
          <div className="form-group" key={field.key}>
            <div className="form-label-wrapper">
              <label htmlFor={`proposal-${field.key}`} className="form-label">
                {field.label}
                {field.required && (
                  <span className="form-label-required" aria-hidden="true">*</span>
                )}
              </label>
              {field.kind === "textarea" && (
                <span className="form-helper">
                  {field.required ? "Concise, grounded description." : "Optional."}
                </span>
              )}
            </div>
            {field.kind === "input" ? (
              <input
                id={`proposal-${field.key}`}
                className="form-control"
                value={form[field.key]}
                onChange={update(field.key)}
                maxLength={300}
                required={field.required}
              />
            ) : (
              <textarea
                id={`proposal-${field.key}`}
                className="form-control"
                value={form[field.key]}
                onChange={update(field.key)}
                rows={field.key === "summary" ? 4 : 3}
                maxLength={20000}
                required={field.required}
              />
            )}
          </div>
        ))}

        {error && (
          <Alert type="danger" title="Could not create the proposal">
            <p style={{ margin: 0 }}>{error}</p>
          </Alert>
        )}

        <div className="form-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Creating draft…" : "Create draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function TeamDetail() {
  const { route, navigate } = useRouter();
  const { user } = useAuth();
  const teamId = route.params.id;

  const [team, setTeam] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [institution, setInstitution] = useState(null);
  const [members, setMembers] = useState([]);
  const [memberError, setMemberError] = useState(false);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showNewProposal, setShowNewProposal] = useState(false);

  const fetchTeam = () => {
    if (!teamId) return;
    const handle = (promise) =>
      promise.catch(() => null);

    setLoading(true);
    setError(null);
    getTeam(teamId)
      .then(async (data) => {
        setTeam(data);
        const [ch, inst, props, memberResult] = await Promise.all([
          handle(getChallenge(data.challenge_id)),
          handle(getInstitution(data.institution_id)),
          handle(listProposals({ teamId, limit: 100 })),
          Promise.resolve().then(() =>
            getTeamMembers(teamId).catch(() => null)
          ),
        ]);
        setChallenge(ch);
        setInstitution(inst);
        setProposals(props?.items ?? []);
        setMembers(memberResult?.items ?? []);
        setMemberError(!memberResult);
      })
      .catch((err) => {
        setError(
          err.message ||
            "This team could not be loaded. It may not exist, or you may not have access yet."
        );
        setTeam(null);
      })
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => fetchTeam(), [teamId]);

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading team..." />
        </div>
      </div>
    );
  }

  if (error || !team) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/workspace" className="back-link">
            ← Back to Workspace
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Team Unavailable">
              <p style={{ marginBottom: "var(--space-3)" }}>
                {error || "We could not find the team you were looking for."}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchTeam}>
                  Retry
                </button>
                <Link href="/workspace" className="btn btn-primary btn-sm">
                  Return to Workspace
                </Link>
              </div>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  const memberLeads = members.filter((m) => m.role === "lead").length;
  const memberCount = members.length;

  const currentUserIsMember =
    !memberError && members.some((m) => m.user_id === user.id);
  const currentUserIsLead =
    currentUserIsMember &&
    members.some((m) => m.user_id === user.id && m.role === "lead");

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href="/workspace" className="back-link">
          ← Back to Workspace
        </Link>

        {/* Hero */}
        <section className="card detail-card team-detail-hero">
          <div className="detail-status-row">
            <span className="section-kicker">Solution team</span>
            <StatusBadge status={team.status} />
          </div>
          <h1 className="detail-title">{team.name}</h1>

          <div className="detail-meta-bar">
            {institution && (
              <Link
                href={`/institutions/${institution.id}`}
                className="detail-meta-item"
                style={{ textDecoration: "none" }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                {institution.name}
              </Link>
            )}
            {formatDate(team.created_at) && (
              <span className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                Formed {formatDate(team.created_at)}
              </span>
            )}
            {memberCount > 0 && (
              <span className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                {memberCount} member{memberCount === 1 ? "" : "s"} · {memberLeads} lead{memberLeads === 1 ? "" : "s"}
              </span>
            )}
          </div>

          {team.description && (
            <p className="card-description" style={{ marginTop: "var(--space-4)" }}>
              {team.description}
            </p>
          )}
        </section>

        {/* Working on */}
        {challenge && (
          <section className="related-section" aria-labelledby="team-challenge-heading">
            <h2 id="team-challenge-heading" className="related-title">
              Working on
            </h2>
            <Link
              href={`/challenges/${challenge.id}`}
              className="card related-card"
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <span>
                <span className="related-card-title">{challenge.title}</span>
                <span className="related-card-location" style={{ marginBottom: 0 }}>
                  {challenge.location}
                </span>
              </span>
              <StatusBadge status={challenge.status} />
            </Link>
          </section>
        )}

        {/* Members */}
        <section className="related-section" aria-labelledby="team-members-heading">
          <div className="panel-header">
            <div>
              <span className="section-kicker">Roster</span>
              <h2 id="team-members-heading" className="related-title">
                Team members
              </h2>
            </div>
          </div>
          {memberError ? (
            <div className="panel-note">
              The full roster is available to team members. Institution leads can
              manage teams from their workspace.
            </div>
          ) : members.length === 0 ? (
            <div className="panel-note">This team does not list any members yet.</div>
          ) : (
            <>
              <ul className="member-list">
                {members.map((member, index) => (
                  <li key={member.id} className="member-row">
                    <span className="member-index" aria-hidden="true">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="member-name">
                      Member {index + 1}
                      {member.status === "invited" && " (invited)"}
                    </span>
                    <span className={`member-role-chip ${member.role === "lead" ? "is-lead" : ""}`}>
                      {member.role === "lead" ? "Team lead" : "Member"}
                    </span>
                    {member.joined_at && (
                      <span className="member-meta">
                        Joined {formatDate(member.joined_at)}
                      </span>
                    )}
                    {member.status !== "active" && (
                      <StatusBadge status={member.status} />
                    )}
                  </li>
                ))}
              </ul>
              {currentUserIsLead && (
                <InviteForm teamId={team.id} onInvited={fetchTeam} />
              )}
            </>
          )}
        </section>

        {/* Proposals */}
        <section className="related-section" aria-labelledby="team-proposals-heading">
          <div className="panel-header">
            <div>
              <span className="section-kicker">Solutions</span>
              <h2 id="team-proposals-heading" className="related-title">
                Proposals
              </h2>
            </div>
            {currentUserIsMember && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowNewProposal(true)}
              >
                New proposal
              </button>
            )}
          </div>
          {proposals.length === 0 ? (
            <div className="panel-note">
              This team has not drafted any proposals yet.
            </div>
          ) : (
            <div className="workspace-list">
              {proposals.map((proposal) => (
                <ProposalRow key={proposal.id} proposal={proposal} showTeam={false} />
              ))}
            </div>
          )}
        </section>
      </div>

      {showNewProposal && team && (
        <NewProposalModal
          team={team}
          onClose={() => setShowNewProposal(false)}
          onCreated={(created) => navigate(`/proposals/${created.id}`)}
        />
      )}
    </div>
  );
}