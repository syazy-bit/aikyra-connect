import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  getProposal,
  updateProposal,
  submitProposal,
  withdrawProposal,
} from "../services/proposalService.js";
import { getTeam, getTeamMembers } from "../services/teamService.js";
import { getChallenge } from "../services/challengeService.js";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { Modal } from "../components/Modal.jsx";

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

const EDIT_FIELDS = [
  { key: "title", label: "Title", required: true, kind: "input" },
  { key: "summary", label: "Summary", required: true, kind: "textarea" },
  { key: "approach", label: "Approach", required: false, kind: "textarea" },
  { key: "resources_needed", label: "Resources needed", required: false, kind: "textarea" },
  { key: "timeline", label: "Timeline", required: false, kind: "textarea" },
];

function EditProposalModal({ proposal, onClose, onSaved }) {
  const initial = {
    title: proposal.title,
    summary: proposal.summary,
    approach: proposal.approach ?? "",
    resources_needed: proposal.resources_needed ?? "",
    timeline: proposal.timeline ?? "",
  };
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
      const fields = {
        title: form.title.trim(),
        summary: form.summary.trim(),
        approach: form.approach.trim() || null,
        resources_needed: form.resources_needed.trim() || null,
        timeline: form.timeline.trim() || null,
      };
      await updateProposal(proposal.id, fields);
      onSaved();
    } catch (err) {
      setError(err.message || "Could not save the proposal. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal open title="Edit proposal draft" onClose={onClose} wide>
      <form onSubmit={submit} noValidate>
        {EDIT_FIELDS.map((field) => (
          <div className="form-group" key={field.key}>
            <div className="form-label-wrapper">
              <label htmlFor={`edit-proposal-${field.key}`} className="form-label">
                {field.label}
                {field.required && (
                  <span className="form-label-required" aria-hidden="true">*</span>
                )}
              </label>
            </div>
            {field.kind === "input" ? (
              <input
                id={`edit-proposal-${field.key}`}
                className="form-control"
                value={form[field.key]}
                onChange={update(field.key)}
                maxLength={300}
                required={field.required}
              />
            ) : (
              <textarea
                id={`edit-proposal-${field.key}`}
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
          <Alert type="danger" title="Could not save the proposal">
            <p style={{ margin: 0 }}>{error}</p>
          </Alert>
        )}

        <div className="form-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function ProposalDetail() {
  const { route } = useRouter();
  const { user } = useAuth();
  const proposalId = route.params.id;

  const [proposal, setProposal] = useState(null);
  const [team, setTeam] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [members, setMembers] = useState([]);
  const [memberError, setMemberError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  const fetchProposal = () => {
    if (!proposalId) return;
    const handle = (promise) => promise.catch(() => null);

    setLoading(true);
    setError(null);
    getProposal(proposalId)
      .then(async (data) => {
        setProposal(data);
        const [t, c, memberResult] = await Promise.all([
          handle(getTeam(data.team_id)),
          handle(getChallenge(data.challenge_id)),
          Promise.resolve().then(() =>
            getTeamMembers(data.team_id).catch(() => null)
          ),
        ]);
        setTeam(t);
        setChallenge(c);
        setMembers(memberResult?.items ?? []);
        setMemberError(!memberResult);
      })
      .catch((err) => {
        setError(
          err.message ||
            "This proposal could not be loaded. It may not exist, or you may not have access to it."
        );
        setProposal(null);
      })
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => fetchProposal(), [proposalId]);

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading proposal..." />
        </div>
      </div>
    );
  }

  if (error || !proposal) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/workspace" className="back-link">
            ← Back to Workspace
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Proposal Unavailable">
              <p style={{ marginBottom: "var(--space-3)" }}>
                {error || "We could not find the proposal you were looking for."}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchProposal}>
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

  const isMember =
    !memberError && members.some((m) => m.user_id === user.id);
  const isLead =
    isMember &&
    members.some((m) => m.user_id === user.id && m.role === "lead");

  const canEdit = isMember && proposal.status === "draft";
  const canSubmit = isLead && proposal.status === "draft";
  const canWithdraw =
    isLead && (proposal.status === "draft" || proposal.status === "submitted");

  const performAction = async () => {
    setActionBusy(true);
    setActionError(null);
    try {
      if (confirmAction === "submit") {
        await submitProposal(proposal.id);
      } else {
        await withdrawProposal(proposal.id);
      }
      setConfirmAction(null);
      fetchProposal();
    } catch (err) {
      setActionError(
        err.message ||
          (confirmAction === "submit"
            ? "Could not submit the proposal. Please try again."
            : "Could not withdraw the proposal. Please try again.")
      );
    } finally {
      setActionBusy(false);
    }
  };

  const cancelAction = () => {
    setConfirmAction(null);
    setActionError(null);
  };

  const sections = [
    { key: "summary", label: "About the proposal", value: proposal.summary },
    { key: "approach", label: "Approach", value: proposal.approach },
    { key: "resources", label: "Resources needed", value: proposal.resources_needed },
    { key: "timeline", label: "Timeline", value: proposal.timeline },
  ].filter((s) => s.value);

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href="/workspace" className="back-link">
          ← Back to Workspace
        </Link>

        {/* Hero */}
        <section className="card detail-card">
          <div className="detail-status-row">
            <span className="section-kicker">Solution proposal</span>
            <StatusBadge status={proposal.status} />
          </div>
          <h1 className="detail-title">{proposal.title}</h1>

          <div className="detail-meta-bar">
            {team && (
              <Link
                href={`/teams/${team.id}`}
                className="detail-meta-item"
                style={{ textDecoration: "none" }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                {team.name}
              </Link>
            )}
            {proposal.submitted_at && (
              <span className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                Submitted {formatDate(proposal.submitted_at)}
              </span>
            )}
            {!proposal.submitted_at && (
              <span className="detail-meta-item">Draft — not yet submitted</span>
            )}
          </div>

          {(canEdit || canSubmit || canWithdraw) && (
            <div className="proposal-actions">
              {canEdit && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setEditOpen(true)}
                >
                  Edit draft
                </button>
              )}
              {canSubmit && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setActionError(null);
                    setConfirmAction("submit");
                  }}
                >
                  Submit for review
                </button>
              )}
              {canWithdraw && (
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => {
                    setActionError(null);
                    setConfirmAction("withdraw");
                  }}
                >
                  Withdraw
                </button>
              )}
            </div>
          )}

          {confirmAction && (
            <Alert
              type="warning"
              title={
                confirmAction === "submit"
                  ? "Submit this proposal?"
                  : "Withdraw this proposal?"
              }
            >
              <p style={{ marginBottom: "var(--space-3)" }}>
                {confirmAction === "submit"
                  ? "Submitting locks the draft and sends it into review. Only the team lead can change it afterwards."
                  : "Withdrawal is permanent — this proposal's review slot is consumed and cannot be reopened."}
              </p>
              {actionError && (
                <p className="form-error-msg" role="alert" style={{ marginBottom: "var(--space-3)" }}>
                  {actionError}
                </p>
              )}
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={performAction}
                  disabled={actionBusy}
                >
                  {actionBusy
                    ? confirmAction === "submit" ? "Submitting…" : "Withdrawing…"
                    : confirmAction === "submit" ? "Yes, submit" : "Yes, withdraw"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={cancelAction}
                  disabled={actionBusy}
                >
                  Cancel
                </button>
              </div>
            </Alert>
          )}
        </section>

        {/* Challenge / team context */}
        {(team || challenge) && (
          <section className="related-section" aria-labelledby="proposal-context-heading">
            <h2 id="proposal-context-heading" className="related-title">
              Context
            </h2>
            <div className="relation-chip-list">
              {challenge && (
                <Link
                  href={`/challenges/${challenge.id}`}
                  className="relation-chip relation-chip-challenge"
                >
                  <span className="relation-chip-label">Challenge</span>
                  <span className="relation-chip-value">{challenge.title}</span>
                </Link>
              )}
              {team && (
                <Link
                  href={`/teams/${team.id}`}
                  className="relation-chip relation-chip-team"
                >
                  <span className="relation-chip-label">Team</span>
                  <span className="relation-chip-value">{team.name}</span>
                </Link>
              )}
            </div>
          </section>
        )}

        {/* Sections */}
        {sections.map((section) => (
          <section className="related-section" key={section.key} aria-labelledby={`proposal-${section.key}-heading`}>
            <span className="section-kicker">{section.label}</span>
            <h2 id={`proposal-${section.key}-heading`} className="related-title">
              {section.label}
            </h2>
            <p className="proposal-section-text">{section.value}</p>
          </section>
        ))}

        {/* Footer meta */}
        <footer className="proposal-meta">
          {formatDate(proposal.created_at) && (
            <span>Created {formatDate(proposal.created_at)}</span>
          )}
          {formatDate(proposal.updated_at) && (
            <span>Last updated {formatDate(proposal.updated_at)}</span>
          )}
        </footer>
      </div>

      {editOpen && proposal && (
        <EditProposalModal
          proposal={proposal}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            setEditOpen(false);
            fetchProposal();
          }}
        />
      )}
    </div>
  );
}