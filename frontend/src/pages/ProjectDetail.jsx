import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import {
  getProject,
  updateProjectLifecycle,
} from "../services/projectService.js";
import { getTeamMembers } from "../services/teamService.js";
import { useAuth } from "../context/AuthContext.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { SupportTypeBadge } from "../components/SupportTypeBadge.jsx";
import { OfferSupportModal } from "../components/OfferSupportModal.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

const LIFECYCLE_STEPS = [
  { key: "prototype", label: "Prototype" },
  { key: "pilot", label: "Pilot" },
  { key: "implemented", label: "Implemented" },
];

const NEXT_LIFECYCLE = {
  prototype: { status: "pilot", label: "Advance to Pilot" },
  pilot: { status: "implemented", label: "Mark as Implemented" },
};

export function ProjectDetail() {
  const { route } = useRouter();
  const { isAuthenticated, user } = useAuth();
  const projectId = route.params.id;

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [offerOpen, setOfferOpen] = useState(false);

  const [members, setMembers] = useState([]);
  const [memberError, setMemberError] = useState(false);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [lifecycleError, setLifecycleError] = useState(null);

  const fetchProject = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    setLifecycleError(null);
    getProject(projectId)
      .then(async (data) => {
        setProject(data);
        if (data.team_id) {
          const memberResult = await getTeamMembers(data.team_id).catch(() => null);
          const items = memberResult?.items ?? [];
          setMembers(items);
          setMemberError(!memberResult);
        }
      })
      .catch((err) => {
        setError(
          err.message ||
            "This project could not be loaded. It may not exist."
        );
        setProject(null);
      })
      .finally(() => setLoading(false));
  };

  const advanceLifecycle = async () => {
    const next = NEXT_LIFECYCLE[project.status];
    if (!next) return;
    setLifecycleBusy(true);
    setLifecycleError(null);
    try {
      await updateProjectLifecycle(project.id, next.status);
      await fetchProject();
    } catch (err) {
      setLifecycleError(
        err.message || "The project lifecycle could not be advanced."
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => fetchProject(), [projectId]);

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading project..." />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/projects" className="back-link">
            ← Back to Projects
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Project Unavailable">
              <p style={{ marginBottom: "var(--space-3)" }}>
                {error || "We could not find the project you were looking for."}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={fetchProject}
                >
                  Retry
                </button>
                <Link href="/projects" className="btn btn-primary btn-sm">
                  Return to Projects
                </Link>
              </div>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  const offers = project.offers ?? [];
  const currentIndex = LIFECYCLE_STEPS.findIndex(
    (step) => step.key === project.status
  );
  const isLead =
    isAuthenticated &&
    !memberError &&
    members.some((m) => m.user_id === user.id && m.role === "lead");
  const nextAdvance = NEXT_LIFECYCLE[project.status];

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href="/projects" className="back-link">
          ← Back to Projects
        </Link>

        {/* Hero */}
        <section className="card detail-card">
          <div className="detail-status-row">
            <span className="section-kicker">Approved solution</span>
            <StatusBadge status={project.status} />
          </div>
          <h1 className="detail-title">{project.title}</h1>

          <div className="detail-meta-bar">
            <span className="detail-meta-item">
              {project.institution_name} · {project.team_name}
            </span>
            {formatDate(project.created_at) && (
              <span className="detail-meta-item">
                Approved {formatDate(project.created_at)}
              </span>
            )}
          </div>

          <p className="proposal-section-text">{project.challenge_title}</p>

          {isAuthenticated && (
            <div className="proposal-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setOfferOpen(true);
                }}
              >
                Offer support
              </button>
            </div>
          )}
        </section>

        {/* Project lifecycle */}
        <section
          className="lifecycle-card"
          aria-labelledby="project-lifecycle-heading"
        >
          <h2 id="project-lifecycle-heading" className="sr-only">
            Project lifecycle
          </h2>
          <ol className="lifecycle-steps">
            {LIFECYCLE_STEPS.map((step, index) => {
              let state = "is-future";
              if (index < currentIndex) state = "is-complete";
              if (index === currentIndex) state = "is-current";
              return (
                <li
                  key={step.key}
                  className={`lifecycle-step ${state}`}
                  aria-current={index === currentIndex ? "step" : undefined}
                >
                  <span className="journey-dot" aria-hidden="true">
                    {index < currentIndex ? "✓" : index + 1}
                  </span>
                  <span className="journey-label">{step.label}</span>
                  {index < LIFECYCLE_STEPS.length - 1 && (
                    <span className="lifecycle-sep" aria-hidden="true">
                      →
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
          <div className="lifecycle-actions">
            {nextAdvance && isLead ? (
              <button
                type="button"
                className="btn btn-primary"
                disabled={lifecycleBusy}
                onClick={advanceLifecycle}
              >
                {lifecycleBusy ? "Updating…" : nextAdvance.label}
              </button>
            ) : (
              !nextAdvance && (
                <span className="lifecycle-note">
                  This solution has been fully implemented and is now closed to
                  further lifecycle changes.
                </span>
              )
            )}
          </div>
          {lifecycleError && (
            <Alert type="danger" title="Could not advance">
              <p style={{ marginBottom: 0 }}>{lifecycleError}</p>
            </Alert>
          )}
        </section>

        {/* Support offers */}
        <section
          className="related-section"
          aria-labelledby="project-offers-heading"
        >
          <span className="section-kicker">Industry & NGO support</span>
          <h2 id="project-offers-heading" className="related-title">
            Support offers
          </h2>

          {offers.length === 0 ? (
            <div className="card" style={{ padding: "var(--space-4)" }}>
              <EmptyState
                title="No support offers yet"
                description="This approved solution is open to support from industry organizations and NGOs."
                actionText="Offer support"
                onActionClick={isAuthenticated ? () => setOfferOpen(true) : undefined}
                actionHref={isAuthenticated ? undefined : "/login"}
              />
            </div>
          ) : (
            <div className="workspace-list">
              {offers.map((offer) => (
                <div key={offer.id} className="invite-row">
                  <span className="invite-row-main">
                    <span className="invite-row-name">
                      {offer.organization.name}
                    </span>
                    <span className="invite-row-meta">
                      {formatDate(offer.created_at)}
                      {offer.status === "offered" ? " · Offer pending" : ""}
                    </span>
                    {offer.message && (
                      <span className="offer-message">{offer.message}</span>
                    )}
                  </span>
                  <SupportTypeBadge type={offer.support_type} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {offerOpen && project && (
        <OfferSupportModal
          project={project}
          onClose={() => setOfferOpen(false)}
          onOffered={() => {
            setOfferOpen(false);
            fetchProject();
          }}
        />
      )}
    </div>
  );
}
