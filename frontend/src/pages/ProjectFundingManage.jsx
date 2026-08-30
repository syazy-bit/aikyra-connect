import React, { useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  getProject,
  getProjectFunding,
  createFundingGoal,
  updateFundingGoal,
  closeFundingGoal,
} from "../services/projectService.js";
import { getTeamMembers } from "../services/teamService.js";
import { FundingProgress } from "../components/FundingProgress.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { Modal } from "../components/Modal.jsx";
import { minorToRupees, rupeesToMinor } from "../utils/money.js";

/**
 * Owner funding management for one approved solution (team lead only).
 *
 * Security: the backend is the boundary. This page only decides whether to
 * SHOW management controls; every create/edit/close request is authorized
 * server-side (project -> team -> ACTIVE lead membership). If the backend
 * returns 403/409 the error is surfaced verbatim rather than bypassed.
 *
 * Money: inputs are whole rupees; they are converted to integer minor units
 * (paise) for the API (see utils/money.js). Floats never enter the money path.
 */

function validateAmount(value) {
  if (String(value ?? "").trim() === "") {
    return null;
  }
  return rupeesToMinor(value) === null
    ? "Enter a positive amount of at least ₹0.01, e.g. 50000 for ₹50,000 or 50000.50 for ₹50,000.50."
    : null;
}

function GoalAmountField({ id, label, helper, value, onChange, max, error }) {
  return (
    <div className="form-group">
      <div className="form-label-wrapper">
        <label htmlFor={id} className="form-label">
          {label}
        </label>
        <span className="form-helper">{helper}</span>
      </div>
      <div className="funding-amount-input">
        <span className="funding-amount-prefix" aria-hidden="true">
          ₹
        </span>
        <input
          id={id}
          className={`form-control${error ? " has-error" : ""}`}
          type="number"
          inputMode="decimal"
          min="0.01"
          step="0.01"
          max={max}
          value={value}
          onChange={onChange}
          placeholder="e.g. 50000"
          aria-invalid={error ? "true" : undefined}
        />
      </div>
      {error && (
        <span className="form-helper is-invalid" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export function ProjectFundingManage() {
  const { route } = useRouter();
  const { user } = useAuth();
  const projectId = route.params.id;

  const [project, setProject] = useState(null);
  const [fundingSummary, setFundingSummary] = useState(null);
  const [hasCampaign, setHasCampaign] = useState(false);
  const [isLead, setIsLead] = useState(false);
  const [leadChecked, setLeadChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [goalInput, setGoalInput] = useState("");
  const [editInput, setEditInput] = useState("");
  const [goalError, setGoalError] = useState(null);
  const [editError, setEditError] = useState(null);
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [refreshWarning, setRefreshWarning] = useState(null);
  const [confirmClose, setConfirmClose] = useState(false);

  const load = () => {
    if (!projectId) return;
    setLoading(true);
    setLoadError(null);
    setActionError(null);
    setSuccess(null);
    setRefreshWarning(null);
    Promise.all([getProject(projectId), getProjectFunding(projectId)])
      .then(([projectData, fundingBody]) => {
        setProject(projectData);
        setHasCampaign(Boolean(fundingBody?.funding));
        setFundingSummary(fundingBody?.funding ?? null);
        if (fundingBody?.funding) {
          setEditInput(String(minorToRupees(fundingBody.funding.goal_minor)));
        }
        return projectData;
      })
      .then((projectData) => {
        // Lead detection is a UX-information check only; the backend is the
        // security boundary.
        return getTeamMembers(projectData.team_id)
          .then((members) => {
            const isLeader = (members.items ?? []).some(
              (m) => m.user_id === user?.id && m.role === "lead"
            );
            setIsLead(isLeader);
          })
          .catch(() => setIsLead(false))
          .then(() => setLeadChecked(true));
      })
      .catch((err) => {
        setProject(null);
        setLoadError(
          err.message ||
            "This project could not be loaded. It may not exist."
        );
        setLeadChecked(true);
      })
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => load(), [projectId]);

  const refreshAfterAction = (summary) => {
    Promise.all([getProject(projectId), getProjectFunding(projectId)])
      .then(([projectData, fundingBody]) => {
        setProject(projectData);
        setHasCampaign(Boolean(fundingBody?.funding));
        setFundingSummary(fundingBody?.funding ?? null);
        if (fundingBody?.funding) {
          setEditInput(String(minorToRupees(fundingBody.funding.goal_minor)));
        }
        setRefreshWarning(null);
      })
      .catch(() => {
        // Keep the just-saved mutation's server response on screen so the
        // user never sees stale data presented as live; warn quietly that
        // the freshest totals could not be loaded.
        if (summary) {
          setFundingSummary(summary);
        }
        setRefreshWarning(
          "The change was saved, but the latest funding details could not be refreshed. Please reload."
        );
      });
  };

  const runAction = async (mode, fn) => {
    setBusy(mode);
    setActionError(null);
    setSuccess(null);
    setRefreshWarning(null);
    try {
      const summary = await fn();
      setSuccess(actionSuccessCopy(mode));
      setFundingSummary(summary);
      setHasCampaign(true);
      if (summary?.goal_minor != null) {
        setEditInput(String(minorToRupees(summary.goal_minor)));
      }
      refreshAfterAction(summary);
      return summary;
    } catch (err) {
      setActionError(
        err.message ||
          "The action could not be completed. Please check the project and try again."
      );
      return undefined;
    } finally {
      setBusy(null);
    }
  };

  const actionSuccessCopy = (mode) =>
    mode === "publish"
      ? "Funding goal published. It is now visible on the public project."
      : mode === "edit"
        ? "Funding goal updated. Public totals are re-computed from contributions."
        : "Funding closed. Contributions and totals are preserved.";

  const publish = () => {
    const minor = rupeesToMinor(goalInput);
    if (minor === null) {
      setGoalError(validateAmount(goalInput) || "Enter a valid amount first.");
      return;
    }
    return runAction("publish", () =>
      createFundingGoal(projectId, { goal_minor: minor, currency: "INR" })
    );
  };

  const edit = () => {
    const minor = rupeesToMinor(editInput);
    if (minor === null) {
      setEditError(validateAmount(editInput) || "Enter a valid amount first.");
      return;
    }
    return runAction("edit", () =>
      updateFundingGoal(projectId, { goal_minor: minor })
    );
  };

  const close = () =>
    runAction("close", () => closeFundingGoal(projectId)).then((summary) => {
      if (summary) setConfirmClose(false);
    });

  const summaryBlock = useMemo(
    () => (
      <div className="funding-block funding-block--large">
        <FundingProgress funding={fundingSummary} />
      </div>
    ),
    [fundingSummary]
  );

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading funding management..." />
        </div>
      </div>
    );
  }

  if (loadError || !project) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/workspace" className="back-link">
            ← Back to Workspace
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Project Unavailable">
              <p style={{ margin: 0 }}>
                {loadError || "We could not find the project you were looking for."}
              </p>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href="/workspace" className="back-link">
          ← Back to Workspace
        </Link>

        <section className="card detail-card">
          <div className="detail-status-row">
            <span className="section-kicker">Community funding</span>
            <StatusBadge status={project.status} />
          </div>
          <h1 className="detail-title">{project.title}</h1>
          <div className="detail-meta-bar">
            <span className="detail-meta-item">
              {project.institution_name} · {project.team_name}
            </span>
          </div>
          <p className="proposal-section-text">{project.challenge_title}</p>
        </section>

        {!leadChecked ? (
          <LoadingSpinner size="md" message="Checking ownership..." />
        ) : !isLead ? (
          <div className="card" style={{ padding: "var(--space-5)" }}>
            <EmptyState
              title="Only the active team lead can manage funding"
              description="Funding goal publishing, editing and closing require the project team's active lead. If you believe this is incorrect, your team lead can transfer leadership from the team page."
              actionText="View this solution"
              actionHref={`/projects/${project.id}`}
            />
          </div>
        ) : (
          <>
            {actionError && (
              <Alert type="danger" title="Funding action failed">
                <p style={{ margin: 0 }}>{actionError}</p>
              </Alert>
            )}
            {success && (
              <Alert type="success" title="Done">
                <p style={{ margin: 0 }}>{success}</p>
              </Alert>
            )}
            {refreshWarning && (
              <Alert type="warning" title="Refresh pending">
                <p style={{ margin: 0 }}>{refreshWarning}</p>
              </Alert>
            )}

            {!hasCampaign || !fundingSummary ? (
              /* No goal yet — publish form */
              <section className="card" style={{ padding: "var(--space-6)" }}>
                <span className="section-kicker">Community funding</span>
                <h2 className="related-title">Help this solution become reality</h2>
                <p className="funding-note">
                  Your approved solution can carry one verified funding target.
                  Publish it here and it is immediately visible to the public on
                  the approved solution — there is no separate approval step.
                  Online contributions are coming soon: no money is collected on
                  this page today, and publishing simply verifies and publicly
                  presents the target.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    publish();
                  }}
                  noValidate
                >
                  <GoalAmountField
                    id="funding-goal-amount"
                    label="Funding target"
                    helper="Amount in Indian rupees, e.g. 50000 for ₹50,000 or 50000.50 for ₹50,000.50. This page converts to paise for the API; the server only ever receives whole paise."
                    value={goalInput}
                    onChange={(event) => {
                      const next = event.target.value;
                      setGoalInput(next);
                      setGoalError(validateAmount(next));
                      setActionError(null);
                    }}
                    error={goalError}
                  />
                  <div className="form-footer">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={busy === "publish" || !rupeesToMinor(goalInput)}
                    >
                      {busy === "publish" ? "Publishing…" : "Publish Funding Goal"}
                    </button>
                  </div>
                </form>
              </section>
            ) : fundingSummary.status === "CLOSED" ? (
              /* Closed — read-only owner view */
              <section className="card" style={{ padding: "var(--space-6)" }}>
                <span className="section-kicker">Community funding</span>
                <h2 className="related-title">Funding closed</h2>
                {summaryBlock}
                <div className="funding-coming-soon" style={{ marginTop: "var(--space-5)" }}>
                  <h3 className="funding-coming-soon-title">This funding round is closed</h3>
                  <p>
                    The goal is no longer accepting support. Contributions and
                    totals are preserved; the goal cannot be edited or reopened.
                  </p>
                </div>
                <p className="funding-note" style={{ marginTop: "var(--space-4)" }}>
                  This status is visible to the public on the approved solution.
                </p>
              </section>
            ) : (
              /* Open goal — summary + edit + close */
              <section className="card" style={{ padding: "var(--space-6)" }}>
                <span className="section-kicker">Community funding</span>
                <h2 className="related-title">Funding in progress</h2>
                {summaryBlock}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    edit();
                  }}
                  noValidate
                  style={{ marginTop: "var(--space-6)" }}
                >
                  <GoalAmountField
                    id="funding-goal-edit"
                    label="Funding target"
                    helper="Amount in Indian rupees. The server rejects a target below the amount already raised, and edits to a closed round."
                    value={editInput}
                    onChange={(event) => {
                      const next = event.target.value;
                      setEditInput(next);
                      setEditError(validateAmount(next));
                      setActionError(null);
                    }}
                    error={editError}
                  />
                  <div className="form-footer">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={busy === "edit" || !rupeesToMinor(editInput)}
                    >
                      {busy === "edit" ? "Saving…" : "Save changes"}
                    </button>
                  </div>
                </form>
                <div className="management-divider" />
                <div className="management-danger-zone">
                  <div>
                    <h3 className="related-title" style={{ marginBottom: "var(--space-1)" }}>
                      Close funding round
                    </h3>
                    <p className="funding-note">
                      Closing stops new support and is final and reversible
                      only by the platform operators. Existing contributions and
                      totals are preserved.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      setActionError(null);
                      setSuccess(null);
                      setConfirmClose(true);
                    }}
                    disabled={busy === "close"}
                  >
                    {busy === "close" ? "Closing funding round…" : "Close funding round"}
                  </button>
                </div>
              </section>
            )}
          </>
        )}
      </div>

      {confirmClose && (
        <Modal open title="Close funding?" onClose={() => setConfirmClose(false)} wide>
          <p className="funding-note">
            Closing the funding goal is final. The goal and its totals stay
            visible as CLOSED on the public project; new support will not be
            presented. This does not alter any completed contributions.
          </p>
          {actionError && (
            <Alert type="danger" title="Could not close">
              <p style={{ margin: 0 }}>{actionError}</p>
            </Alert>
          )}
          <div className="form-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setConfirmClose(false)}
              disabled={busy === "close"}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={close}
              disabled={busy === "close"}
            >
              {busy === "close" ? "Closing funding round…" : "Close funding round"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}