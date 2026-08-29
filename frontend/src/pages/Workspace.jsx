import React, { useEffect, useMemo, useState } from "react";
import { Link } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useApiResource } from "../hooks/useApiResource.js";
import {
  listTeams,
  getMyInvitations,
  createTeam,
  acceptInvitation,
  declineInvitation,
} from "../services/teamService.js";
import {
  listProposals,
  reviewProposal,
} from "../services/proposalService.js";
import { listChallenges, getChallengeMatches } from "../services/challengeService.js";
import { listProjects } from "../services/projectService.js";
import {
  listInstitutions,
  getInstitutionMembership,
} from "../services/institutionService.js";
import { TeamCard } from "../components/TeamCard.jsx";
import { ProposalRow } from "../components/ProposalRow.jsx";
import { ChallengeCard } from "../components/ChallengeCard.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { VerificationBadge } from "../components/VerificationBadge.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { Alert } from "../components/Alert.jsx";
import { Modal } from "../components/Modal.jsx";

const JOURNEY = [
  { n: 1, label: "Citizen problem" },
  { n: 2, label: "University matched" },
  { n: 3, label: "Workspace" },
  { n: 4, label: "Team formation" },
  { n: 5, label: "Proposal" },
  { n: 6, label: "Collaboration" },
  { n: 7, label: "Implementation" },
  { n: 8, label: "Impact" },
];

const CURRENT_STEP_INDEX = 2;

const RAIL_CHALLENGE_LIMIT = 4;

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function PanelSkeleton({ rows = 3 }) {
  return (
    <div className="workspace-list" role="status" aria-label="Loading section">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="skeleton-line"
          style={{ height: "3.5rem", borderRadius: "var(--radius-md)" }}
        />
      ))}
    </div>
  );
}

function PanelError({ title, message, onRetry }) {
  return (
    <Alert type="danger" title={title}>
      <p style={{ marginBottom: "var(--space-3)" }}>
        {message || "Something went wrong while loading this section."}
      </p>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
        Try again
      </button>
    </Alert>
  );
}

function PanelHeading({ kicker, title, count }) {
  return (
    <div className="panel-header">
      <div>
        <span className="section-kicker">{kicker}</span>
        <h2 className="panel-title">{title}</h2>
      </div>
      {typeof count === "number" && (
        <span className="panel-count">{count}</span>
      )}
    </div>
  );
}

function InviteRow({ invitation, teamName, busy, disabled, onAccept, onDecline }) {
  return (
    <div className="invite-row">
      <span className="invite-row-main">
        <span className="invite-row-name">{teamName ?? "A team in your institution"}</span>
        <span className="invite-row-meta">
          {formatDate(invitation.created_at)
            ? `Invited ${formatDate(invitation.created_at)}`
            : "You've been invited to join a team"}
        </span>
      </span>
      <StatusBadge status="invited" />
      <span className="invite-actions">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={onAccept}
          disabled={disabled || busy}
        >
          {busy === "accept" ? "Accepting…" : "Accept"}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onDecline}
          disabled={disabled || busy}
        >
          {busy === "decline" ? "Declining…" : "Decline"}
        </button>
      </span>
    </div>
  );
}

function WorkspaceJourney() {
  return (
    <section
      className="workspace-journey"
      aria-label="The Aikyra workflow, with the workspace as the current step"
    >
      <div className="container">
        <ol className="journey-steps">
          {JOURNEY.map((step, index) => (
            <React.Fragment key={step.n}>
              {index > 0 && (
                <li className="journey-sep" aria-hidden="true">→</li>
              )}
              <li
                className={`journey-step ${index === CURRENT_STEP_INDEX ? "is-current" : ""}`}
                aria-current={index === CURRENT_STEP_INDEX ? "step" : undefined}
              >
                <span className="journey-dot" aria-hidden="true">{step.n}</span>
                <span className="journey-label">{step.label}</span>
              </li>
            </React.Fragment>
          ))}
        </ol>
      </div>
    </section>
  );
}

function CreateTeamModal({ challenge, myInstitutions, onClose, onCreated }) {
  const [form, setForm] = useState(() => ({
    institution_id: myInstitutions[0]?.id ?? "",
    name: "",
    description: "",
  }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const hasInstitutions = myInstitutions.length > 0;

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
    setError(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!hasInstitutions) return;
    setBusy(true);
    setError(null);
    try {
      await createTeam({
        institution_id: form.institution_id,
        challenge_id: challenge.id,
        name: form.name.trim(),
        description: form.description.trim() || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err.message || "Could not create the team. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal open title="Create a team" onClose={onClose} wide>
      {!hasInstitutions ? (
        <Alert type="warning" title="No active institution membership found">
          <p style={{ margin: 0 }}>
            Teams are formed under your institution. We could not find an active
            membership for your account — ask your institution lead to add you,
            or register your institution first.
          </p>
        </Alert>
      ) : (
        <form onSubmit={submit} noValidate>
          <div className="form-group">
            <div className="form-label-wrapper">
              <label className="form-label">Challenge</label>
            </div>
            <p className="modal-context-line">{challenge.title}</p>
          </div>

          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="create-team-institution" className="form-label">
                Institution <span className="form-label-required" aria-hidden="true">*</span>
              </label>
            </div>
            <select
              id="create-team-institution"
              className="form-control"
              value={form.institution_id}
              onChange={update("institution_id")}
              required
            >
              {myInstitutions.map((institution) => (
                <option key={institution.id} value={institution.id}>
                  {institution.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="create-team-name" className="form-label">
                Team name <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <span className="form-helper">What should this response group be called?</span>
            </div>
            <input
              id="create-team-name"
              className="form-control"
              value={form.name}
              onChange={update("name")}
              placeholder="e.g. ADTU Groundwater Solutions Team"
              maxLength={200}
              required
            />
          </div>

          <div className="form-group">
            <div className="form-label-wrapper">
              <label htmlFor="create-team-description" className="form-label">
                Description
              </label>
              <span className="form-helper">Optional — what the team plans to focus on.</span>
            </div>
            <textarea
              id="create-team-description"
              className="form-control"
              value={form.description}
              onChange={update("description")}
              placeholder="Scope, focus areas, members you hope to bring in…"
              maxLength={5000}
              rows={3}
            />
          </div>

          {error && (
            <Alert type="danger" title="Could not create the team">
              <p style={{ margin: 0 }}>{error}</p>
            </Alert>
          )}

          <div className="form-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Creating…" : "Create team"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function RejectProposalModal({ proposal, onClose, onRejected }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await reviewProposal(proposal.id, {
        action: "reject",
        review_note: note.trim() || undefined,
      });
      onRejected();
    } catch (err) {
      setError(err.message || "Could not reject the proposal. Please try again.");
      setBusy(false);
    }
  };

  return (
    <Modal open title="Reject proposal" onClose={onClose} wide>
      <div className="form-group">
        <div className="form-label-wrapper">
          <label htmlFor="reject-proposal-note" className="form-label">
            Review note
          </label>
          <span className="form-helper">
            Explain what the team should improve — shown to the team on the
            proposal page. Rejection is final in this phase.
          </span>
        </div>
        <textarea
          id="reject-proposal-note"
          className="form-control"
          value={note}
          onChange={(event) => {
            setNote(event.target.value);
            setError(null);
          }}
          rows={4}
          maxLength={20000}
          placeholder="e.g. Missing impact metrics and budget breakdown."
        />
      </div>

      {error && (
        <Alert type="danger" title="Could not reject the proposal">
          <p style={{ margin: 0 }}>{error}</p>
        </Alert>
      )}

      <div className="form-footer">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onClose}
          disabled={busy}
        >
          Cancel
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={confirm}
          disabled={busy}
        >
          {busy ? "Rejecting…" : "Reject proposal"}
        </button>
      </div>
    </Modal>
  );
}

export function Workspace() {
  const { user } = useAuth();
  const displayName = user?.full_name || user?.email || "";

  const teams = useApiResource(() => listTeams({ limit: 100 }), []);
  const invitations = useApiResource(() => getMyInvitations(), []);
  const proposals = useApiResource(() => listProposals({ limit: 100 }), []);
  const institutions = useApiResource(() => listInstitutions({ limit: 100 }), []);
  const challenges = useApiResource(
    () => listChallenges({ sort: "urgency", hasDna: true, limit: RAIL_CHALLENGE_LIMIT }),
    []
  );
  const projectsApi = useApiResource(() => listProjects({ limit: 100 }), []);

  const teamItems = useMemo(() => teams.data?.items ?? [], [teams.data]);
  const invitationItems = useMemo(() => invitations.data?.items ?? [], [invitations.data]);
  const proposalItems = useMemo(() => proposals.data?.items ?? [], [proposals.data]);
  const challengeItems = useMemo(() => challenges.data?.items ?? [], [challenges.data]);

  const institutionById = useMemo(
    () => new Map((institutions.data?.items ?? []).map((i) => [i.id, i])),
    [institutions.data]
  );

  // Approved solutions from proposals accepted by this user's institution.
  const approvedForMe = useMemo(() => {
    const myTeamIds = new Set(teamItems.map((t) => t.id));
    return (projectsApi.data?.items ?? []).filter((project) =>
      myTeamIds.has(project.team_id)
    );
  }, [projectsApi.data, teamItems]);

  const teamById = useMemo(
    () => new Map(teamItems.map((t) => [t.id, t])),
    [teamItems]
  );

  const proposalCounts = useMemo(() => {
    const counts = new Map();
    for (const p of proposalItems) {
      counts.set(p.team_id, (counts.get(p.team_id) || 0) + 1);
    }
    return counts;
  }, [proposalItems]);

  const proposalsByTeam = useMemo(() => {
    const grouped = new Map();
    for (const p of proposalItems) {
      if (!grouped.has(p.team_id)) grouped.set(p.team_id, []);
      grouped.get(p.team_id).push(p);
    }
    return grouped;
  }, [proposalItems]);

  // --- Identity: which institutions is this user active in? ---------------
  // Primary source: institution_ids of teams visible to this user (their
  // teams belong to institutions where they hold an active membership).
  // Fallback for users with no teams yet: bounded, parallel membership probes
  // against the institutions feed (no "my memberships" endpoint exists).
  const teamInstitutionIds = useMemo(
    () => Array.from(new Set(teamItems.map((t) => t.institution_id).filter(Boolean))),
    [teamItems]
  );

  const [resolvedInstitutions, setResolvedInstitutions] = useState([]);
  const [resolvingInstitutions, setResolvingInstitutions] = useState(true);

  // --- Review rights: active owner/representative of an institution ---------
  // Computed after resolvedInstitutions is declared (useState above) so the
  // memo never reads the binding before its initializer runs.
  const reviewerInstitutionIds = useMemo(
    () =>
      new Set(
        resolvedInstitutions
          .filter(
            (i) =>
              i.membership_status === "active" &&
              (i.role === "owner" || i.role === "representative")
          )
          .map((i) => i.id)
      ),
    [resolvedInstitutions]
  );

  const canReview = reviewerInstitutionIds.size > 0;

  const proposalsNeedingReview = useMemo(
    () =>
      proposalItems.filter((proposal) => {
        if (proposal.status !== "submitted" && proposal.status !== "under_review") {
          return false;
        }
        const team = teamById.get(proposal.team_id);
        return Boolean(team && reviewerInstitutionIds.has(team.institution_id));
      }),
    [proposalItems, teamById, reviewerInstitutionIds]
  );

  useEffect(() => {
    let cancelled = false;
    setResolvingInstitutions(true);
    (async () => {
      const candidates = institutions.data?.items ?? [];
      let resolved = teamInstitutionIds
        .map((id) => institutionById.get(id))
        .filter(Boolean);
      if (resolved.length === 0 && candidates.length > 0) {
        const toProbe = candidates.slice(0, 25);
        const results = await Promise.all(
          toProbe.map((inst) =>
            getInstitutionMembership(inst.id).catch(() => ({ is_member: false }))
          )
        );
        resolved = toProbe.filter((_, index) => results[index].is_member);
      }
      // Capture the user's own role at each institution so institution-gated
      // actions (e.g. proposal review) can be surfaced. This is the user's
      // own membership only — never another user's data.
      const withRoles = await Promise.all(
        resolved.slice(0, 10).map(async (institution) => {
          const membership = await getInstitutionMembership(institution.id).catch(
            () => null
          );
          return {
            id: institution.id,
            name: institution.name,
            role: membership?.is_member ? membership.role : null,
            membership_status: membership?.membership_status ?? null,
          };
        })
      );
      if (!cancelled) {
        setResolvedInstitutions(withRoles);
        setResolvingInstitutions(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [teamInstitutionIds, institutionById]);

  // --- Matched challenges ------------------------------------------------
  // For each challenge on the rail, ask the match engine where this user's
  // institution ranks. Failures (e.g. 409 when DNA is unreliable) self-silence
  // to a DNA-status-only card — never a broken section.
  const myInstitutionIds = useMemo(
    () => new Set(resolvedInstitutions.map((institution) => institution.id)),
    [resolvedInstitutions]
  );

  const [railMatches, setRailMatches] = useState({});

  useEffect(() => {
    if (challengeItems.length === 0 || myInstitutionIds.size === 0) return undefined;
    let cancelled = false;
    setRailMatches({});
    const load = async () => {
      const entries = await Promise.all(
        challengeItems.map(async (challenge) => {
          try {
            const result = await getChallengeMatches(challenge.id, 5);
            const item = (result.items ?? []).find((match) =>
              myInstitutionIds.has(match.institution.id)
            );
            return [
              challenge.id,
              item
                ? { institution: item.institution, score: item.score }
                : null,
            ];
          } catch {
            return [challenge.id, null];
          }
        })
      );
      if (!cancelled) setRailMatches(Object.fromEntries(entries));
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [challengeItems, myInstitutionIds]);

  // --- Invitation actions --------------------------------------------------
  const [inviteAction, setInviteAction] = useState({ id: null, mode: null });
  const [inviteError, setInviteError] = useState(null);

  const refreshAfterInvite = () => {
    invitations.retry();
    teams.retry();
  };

  const actOnInvitation = async (invitation, mode) => {
    setInviteAction({ id: invitation.id, mode });
    setInviteError(null);
    try {
      if (mode === "accept") {
        await acceptInvitation(invitation.team_id, invitation.id);
      } else {
        await declineInvitation(invitation.team_id, invitation.id);
      }
      refreshAfterInvite();
    } catch (err) {
      setInviteError(
        err.message ||
          (mode === "accept"
            ? "Could not accept the invitation. Please try again."
            : "Could not decline the invitation. Please try again.")
      );
    } finally {
      setInviteAction({ id: null, mode: null });
    }
  };

  // --- Proposal review actions ----------------------------------------------
  const [reviewBusy, setReviewBusy] = useState(null);
  const [reviewError, setReviewError] = useState(null);
  const [rejectProposal, setRejectProposal] = useState(null);

  const actOnReview = async (proposal, action) => {
    setReviewBusy(proposal.id);
    setReviewError(null);
    try {
      await reviewProposal(proposal.id, { action });
      proposals.retry();
    } catch (err) {
      setReviewError(
        err.message ||
          (action === "start_review"
            ? "Could not start the review. Please try again."
            : "Could not approve the proposal. Please try again.")
      );
    } finally {
      setReviewBusy(null);
    }
  };

  const handleRejected = () => {
    setRejectProposal(null);
    proposals.retry();
  };

  // --- Create-team modal ---------------------------------------------------
  const [createTeamFor, setCreateTeamFor] = useState(null);

  const openCreateTeam = (challenge) => setCreateTeamFor(challenge);

  const handleTeamCreated = () => {
    setCreateTeamFor(null);
    teams.retry();
  };

  const allStudioResolved =
    !teams.loading && !invitations.loading && !proposals.loading &&
    !teams.error && !invitations.error && !proposals.error;

  const nothingPresent =
    allStudioResolved &&
    teamItems.length === 0 &&
    invitationItems.length === 0 &&
    proposalItems.length === 0;

  return (
    <div className="workspace-page">
      <WorkspaceJourney />

      <div className="container">
        {/* Page header */}
        <header className="workspace-header section-header-flex">
          <div>
            <span className="section-kicker">University Innovation Workspace</span>
            <h1 className="section-title">
              {displayName ? `${displayName.split(" ")[0]}'s workspace` : "Workspace"}
            </h1>
            <p className="section-description workspace-subtitle">
              Matched challenges, your university's teams and their solution
              proposals — one hub for turning community problems into
              implemented impact.
            </p>
          </div>
          <div className="workspace-ctas">
            <Link href="/challenges" className="btn btn-primary">
              Find a challenge
            </Link>
            <Link href="/institutions" className="btn btn-outline">
              Browse institutions
            </Link>
          </div>
        </header>

        {/* Institution identity */}
        {resolvedInstitutions.length > 0 && (
          <section className="workspace-institutions" aria-label="Your institutions">
            <span className="workspace-institutions-label">Your institution</span>
            <div className="workspace-institutions-list">
              {resolvedInstitutions.map((institution) => {
                const full = institutionById.get(institution.id);
                return (
                  <Link
                    key={institution.id}
                    href={`/institutions/${institution.id}`}
                    className="institution-tile"
                  >
                    <span className="institution-tile-name">{institution.name}</span>
                    <VerificationBadge status={full?.verification_status} />
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        <div className="workspace-grid">
          {/* Studio column — invitations → teams → proposals */}
          <div className="workspace-studio">
            {nothingPresent ? (
              <div className="card workspace-hero-empty">
                <div className="workspace-hero-empty-icon" aria-hidden="true">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                </div>
                <h2 className="related-title">Your workspace is ready</h2>
                <p>
                  Teams are how your university turns matched challenges into
                  solution proposals. When a team forms around a challenge, it
                  shows up here — along with any invitations and proposal drafts.
                </p>
                <div className="workspace-hero-actions">
                  <Link href="/challenges" className="btn btn-primary">
                    Find a challenge to work on
                  </Link>
                  <Link href="/institutions" className="btn btn-secondary">
                    View institutions
                  </Link>
                </div>
              </div>
            ) : (
              <>
                {/* Institution proposal review */}
                {canReview && (
                  <section
                    className="workspace-panel"
                    aria-labelledby="proposal-review-heading"
                  >
                    <PanelHeading
                      kicker="Institution review"
                      title="Proposal review"
                      count={proposalsNeedingReview.length}
                    />
                    {proposals.loading ? (
                      <PanelSkeleton rows={2} />
                    ) : proposals.error ? (
                      <PanelError
                        title="Could not load proposals to review"
                        onRetry={proposals.retry}
                      />
                    ) : proposalsNeedingReview.length === 0 ? (
                      <div className="panel-note">
                        No proposals awaiting your review. When a team submits a
                        proposal, you can start the review here.
                      </div>
                    ) : (
                      <>
                        <div className="workspace-list">
                          {proposalsNeedingReview.map((proposal) => {
                            const team = teamById.get(proposal.team_id);
                            const busy = reviewBusy === proposal.id;
                            return (
                              <div key={proposal.id} className="invite-row">
                                <span className="invite-row-main">
                                  <Link
                                    href={`/proposals/${proposal.id}`}
                                    className="invite-row-name"
                                    style={{ textDecoration: "none" }}
                                  >
                                    {proposal.title}
                                  </Link>
                                  <span className="invite-row-meta">
                                    {team ? `${team.name} · ` : ""}
                                    {proposal.submitted_at
                                      ? `Submitted ${formatDate(proposal.submitted_at)}`
                                      : "Proposal"}
                                  </span>
                                </span>
                                <StatusBadge status={proposal.status} />
                                <span className="invite-actions">
                                  {proposal.status === "submitted" && (
                                    <button
                                      type="button"
                                      className="btn btn-primary btn-sm"
                                      onClick={() =>
                                        actOnReview(proposal, "start_review")
                                      }
                                      disabled={busy || reviewBusy !== null}
                                    >
                                      {busy ? "Starting…" : "Start review"}
                                    </button>
                                  )}
                                  {proposal.status === "under_review" && (
                                    <>
                                      <button
                                        type="button"
                                        className="btn btn-primary btn-sm"
                                        onClick={() => actOnReview(proposal, "accept")}
                                        disabled={busy || reviewBusy !== null}
                                      >
                                        {busy ? "Approving…" : "Approve"}
                                      </button>
                                      <button
                                        type="button"
                                        className="btn btn-outline btn-sm"
                                        onClick={() => {
                                          setReviewError(null);
                                          setRejectProposal(proposal);
                                        }}
                                        disabled={busy || reviewBusy !== null}
                                      >
                                        Reject
                                      </button>
                                    </>
                                  )}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                        {reviewError && (
                          <Alert type="danger" title="Review action failed">
                            <p style={{ margin: 0 }}>{reviewError}</p>
                          </Alert>
                        )}
                      </>
                    )}
                  </section>
                )}

                {/* Pending invitations */}
                {(invitations.loading ||
                  invitations.error ||
                  invitationItems.length > 0 ||
                  teamItems.length > 0) && (
                  <section className="workspace-panel" aria-labelledby="invitations-heading">
                    <PanelHeading
                      kicker="Invitations"
                      title="Pending invitations"
                      count={invitationItems.length}
                    />
                    {invitations.loading ? (
                      <PanelSkeleton rows={2} />
                    ) : invitations.error ? (
                      <PanelError
                        title="Could not load invitations"
                        onRetry={invitations.retry}
                      />
                    ) : inviteError ? (
                      <Alert type="danger" title="Invitation action failed">
                        <p style={{ margin: 0 }}>{inviteError}</p>
                      </Alert>
                    ) : invitationItems.length > 0 ? (
                      <div className="workspace-list">
                        {invitationItems.map((invitation) => (
                          <InviteRow
                            key={invitation.id}
                            invitation={invitation}
                            teamName={teamById.get(invitation.team_id)?.name}
                            busy={inviteAction.id === invitation.id ? inviteAction.mode : null}
                            disabled={inviteAction.id === invitation.id}
                            onAccept={() => actOnInvitation(invitation, "accept")}
                            onDecline={() => actOnInvitation(invitation, "decline")}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="panel-note">
                        No pending invitations right now. When a team lead invites
                        you, it appears here.
                      </div>
                    )}
                  </section>
                )}

                {/* Teams */}
                <section className="workspace-panel" aria-labelledby="teams-heading">
                  <PanelHeading
                    kicker="Your university's response groups"
                    title="Teams in your workspace"
                    count={teamItems.length}
                  />
                  {teams.loading ? (
                    <PanelSkeleton rows={3} />
                  ) : teams.error ? (
                    <PanelError
                      title="Could not load teams"
                      onRetry={teams.retry}
                    />
                  ) : teamItems.length === 0 ? (
                    <EmptyState
                      title="No teams yet"
                      description="Teams form around a matched challenge, then build a solution proposal. Explore the problem board to begin."
                      actionText="Explore challenges"
                      actionHref="/challenges"
                    />
                  ) : (
                    <div className="workspace-list">
                      {teamItems.map((team) => (
                        <TeamCard
                          key={team.id}
                          team={team}
                          institution={institutionById.get(team.institution_id)}
                          proposalCount={proposalCounts.get(team.id) || 0}
                        />
                      ))}
                    </div>
                  )}
                </section>

                {/* Proposals */}
                <section className="workspace-panel" aria-labelledby="proposals-heading">
                  <PanelHeading
                    kicker="Solutions"
                    title="Proposals in your workspace"
                    count={proposalItems.length}
                  />
                  {proposals.loading ? (
                    <PanelSkeleton rows={3} />
                  ) : proposals.error ? (
                    <PanelError
                      title="Could not load proposals"
                      onRetry={proposals.retry}
                    />
                  ) : proposalItems.length === 0 ? (
                    <EmptyState
                      title="No proposals yet"
                      description="Proposals are how your teams turn a matched challenge into a concrete solution. Drafts will appear here as teams work."
                      actionText="Explore challenges"
                      actionHref="/challenges"
                    />
                  ) : (
                    <div className="proposal-groups">
                      {Array.from(proposalsByTeam.entries()).map(([teamId, list]) => {
                        const team = teamById.get(teamId);
                        return (
                          <div key={teamId} className="proposal-group">
                            <div className="proposal-group-label">
                              {team ? `From ${team.name}` : "From your teams"}
                            </div>
                            <div className="workspace-list">
                              {list.map((proposal) => (
                                <ProposalRow
                                  key={proposal.id}
                                  proposal={proposal}
                                  team={team}
                                />
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>

                {/* Approved solutions & support offers */}
                <section
                  className="workspace-panel"
                  aria-labelledby="approved-solutions-heading"
                >
                  <PanelHeading
                    kicker="Industry & NGO support"
                    title="Approved solutions"
                    count={approvedForMe.length}
                  />
                  {projectsApi.loading ? (
                    <PanelSkeleton rows={2} />
                  ) : projectsApi.error ? (
                    <PanelError
                      title="Could not load approved solutions"
                      onRetry={projectsApi.retry}
                    />
                  ) : approvedForMe.length === 0 ? (
                    <div className="panel-note">
                      Accepted proposals become approved solutions that are open
                      to support from industry organizations and NGOs.
                    </div>
                  ) : (
                    <div className="workspace-list">
                      {approvedForMe.map((project) => (
                        <div key={project.id} className="invite-row">
                          <span className="invite-row-main">
                            <Link
                              href={`/projects/${project.id}`}
                              className="invite-row-name"
                              style={{ textDecoration: "none" }}
                            >
                              {project.title}
                            </Link>
                            <span className="invite-row-meta">
                              <StatusBadge status={project.status} />{" "}
                              {project.institution_name}
                              {" · "}
                              {project.offer_count === 0
                                ? "Open for support"
                                : `${project.offer_count} support offer${
                                    project.offer_count === 1 ? "" : "s"
                                  }`}
                            </span>
                          </span>
                          <Link
                            href={`/projects/${project.id}`}
                            className="btn btn-secondary btn-sm"
                          >
                            View
                          </Link>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}
          </div>

          {/* Rail — challenges seeking teams + how-it-works */}
          <aside className="workspace-rail" aria-label="Challenges seeking teams">
            <section className="workspace-panel" aria-labelledby="rail-challenges-heading">
              <PanelHeading
                kicker="Problem board"
                title="Challenges seeking teams"
              />
              <p className="panel-description">
                DNA-analyzed problems. When your institution ranks in a
                challenge's capability match, its score is shown.
              </p>
              {challenges.loading ? (
                <PanelSkeleton rows={3} />
              ) : challenges.error ? (
                <PanelError
                  title="Could not load challenges"
                  onRetry={challenges.retry}
                />
              ) : challengeItems.length === 0 ? (
                <div className="panel-note">
                  Fresh community problems appear here once they are analyzed.
                  Explore the board to find more.
                </div>
              ) : (
                <div className="workspace-list">
                  {challengeItems.map((challenge) => (
                    <ChallengeCard
                      key={challenge.id}
                      challenge={challenge}
                      match={railMatches[challenge.id]}
                      footerAction={
                        <button
                          type="button"
                          className="btn btn-primary btn-sm btn-block"
                          onClick={() => openCreateTeam(challenge)}
                          disabled={resolvingInstitutions}
                          title={
                            resolvingInstitutions
                              ? "Checking your institution membership…"
                              : undefined
                          }
                        >
                          {resolvingInstitutions ? "Checking…" : "Create a team"}
                        </button>
                      }
                    />
                  ))}
                </div>
              )}
              <Link
                href="/challenges"
                className="btn btn-secondary btn-block rail-cta"
              >
                Browse the problem board
              </Link>
            </section>

            <div className="card workspace-guide">
              <span className="section-kicker">How it works</span>
              <h3 className="related-title">From problem to impact</h3>
              <ol className="workspace-guide-list">
                <li>Challenges matched to your university land here.</li>
                <li>Teams form around a challenge and draft a proposal.</li>
                <li>Submitted proposals move toward collaboration and funding.</li>
              </ol>
            </div>
          </aside>
        </div>
      </div>

      {/* Create-team dialog — opened from a matched challenge on the rail */}
      {createTeamFor && (
        <CreateTeamModal
          challenge={createTeamFor}
          myInstitutions={resolvedInstitutions}
          onClose={() => setCreateTeamFor(null)}
          onCreated={handleTeamCreated}
        />
      )}

      {/* Rejection note dialog — opened from the proposal review area */}
      {rejectProposal && (
        <RejectProposalModal
          proposal={rejectProposal}
          onClose={() => setRejectProposal(null)}
          onRejected={handleRejected}
        />
      )}
    </div>
  );
}