import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getProject } from "../services/projectService.js";
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

export function ProjectDetail() {
  const { route } = useRouter();
  const { isAuthenticated } = useAuth();
  const projectId = route.params.id;

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [offerOpen, setOfferOpen] = useState(false);

  const fetchProject = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    getProject(projectId)
      .then(setProject)
      .catch((err) => {
        setError(
          err.message ||
            "This project could not be loaded. It may not exist."
        );
        setProject(null);
      })
      .finally(() => setLoading(false));
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
