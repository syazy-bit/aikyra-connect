import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getProject, getProjectFunding } from "../services/projectService.js";
import { FundingProgress } from "../components/FundingProgress.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
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

/**
 * Dedicated, public funding page for one approved solution.
 *
 * Reached from the approved-solutions cards and the project detail. It is
 * intentionally read-only: totals come from the funding endpoint (server
 * integer minor units), nothing here is ever sent back to the API, and the
 * honest, non-fake "secure online support is coming soon" note replaces any
 * payment flow until a real integration exists.
 */
export function ProjectFunding() {
  const { route } = useRouter();
  const projectId = route.params.id;

  const [project, setProject] = useState(null);
  const [fundingSummary, setFundingSummary] = useState(null);
  const [hasCampaign, setHasCampaign] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(projectId), getProjectFunding(projectId)])
      .then(([projectData, fundingBody]) => {
        setProject(projectData);
        setHasCampaign(Boolean(fundingBody?.funding));
        setFundingSummary(fundingBody?.funding ?? null);
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

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => fetchAll(), [projectId]);

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading funding..." />
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
                  onClick={fetchAll}
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

  const isOpen = hasCampaign && fundingSummary?.status === "OPEN";
  const isFullyFunded = hasCampaign && fundingSummary?.status === "FULLY_FUNDED";
  const isClosed = hasCampaign && fundingSummary?.status === "CLOSED";

  return (
    <div className="detail-page">
      <div className="container-narrow">
        <Link href={`/projects/${project.id}`} className="back-link">
          ← Back to this solution
        </Link>

        {/* Hero */}
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
            {formatDate(project.created_at) && (
              <span className="detail-meta-item">
                Approved {formatDate(project.created_at)}
              </span>
            )}
          </div>
          <p className="proposal-section-text">{project.challenge_title}</p>
        </section>

        {!hasCampaign || !fundingSummary ? (
          <div className="card" style={{ padding: "var(--space-5)" }}>
            <EmptyState
              title="No verified funding goal yet"
              description="This approved solution has not published a verified funding goal yet. When one is published by the AIKYRA team, this page will show its goal, progress and supporter count — always computed from completed contributions."
            />
          </div>
        ) : (
          <>
            <section className="card" style={{ padding: "var(--space-6)" }}>
              <FundingProgress funding={fundingSummary} />
              <div className="funding-facts">
                <div className="funding-fact">
                  <span className="funding-fact-value">
                    {Math.round(fundingSummary.progress_bp / 100)}%
                  </span>
                  <span className="funding-fact-label">Funding goal progress</span>
                </div>
                <div className="funding-fact">
                  <span className="funding-fact-value">
                    {fundingSummary.supporter_count}
                  </span>
                  <span className="funding-fact-label">
                    Supporter
                    {fundingSummary.supporter_count === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="funding-fact">
                  <span className="funding-fact-value">
                    {fundingSummary.currency}
                  </span>
                  <span className="funding-fact-label">Verified currency</span>
                </div>
              </div>
            </section>

            <section className="card" style={{ padding: "var(--space-6)" }}>
              <h2 className="related-title">What this funding means</h2>
              <p className="funding-note">
                This goal is a verified, official funding target for this
                approved solution, published only after the project has passed
                the platform&apos;s acceptance review. It is not a general
                crowdfunding appeal: totals reflect completed contributions
                only, and the number is always derived from the database, never
                from a browser.
              </p>
              <p className="funding-note" style={{ marginTop: "var(--space-3)" }}>
                Individual supporter identities and amounts remain private. The
                public surface shows only the aggregate goal, the amount
                raised, and the number of supporters — everything required for
                transparency without exposing people.
              </p>

              {isOpen && (
                <div
                  className="funding-coming-soon"
                  style={{ marginTop: "var(--space-5)" }}
                >
                  <h3 className="funding-coming-soon-title">
                    Secure online support is coming soon
                  </h3>
                  <p>
                    Online contributions are not enabled yet. AIKYRA is not a
                    payment processor — when support opens, you will be taken
                    through a verified payment flow, and no money is ever
                    requested on this page today.
                  </p>
                </div>
              )}
              {isFullyFunded && (
                <div
                  className="funding-coming-soon"
                  style={{ marginTop: "var(--space-5)" }}
                >
                  <h3 className="funding-coming-soon-title">
                    Goal reached
                  </h3>
                  <p>
                    This approved solution&apos;s verified funding goal has been
                    reached. Support beyond the goal is subject to the
                    platform&apos;s verified contribution flow once it opens.
                  </p>
                </div>
              )}
              {isClosed && (
                <div
                  className="funding-coming-soon"
                  style={{ marginTop: "var(--space-5)" }}
                >
                  <h3 className="funding-coming-soon-title">
                    This funding round is closed
                  </h3>
                  <p>
                    This funding goal is no longer accepting support. The
                    amounts below reflect the completed contributions already
                    recorded.
                  </p>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}