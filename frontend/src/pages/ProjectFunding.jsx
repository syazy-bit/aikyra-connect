import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getProject, getProjectFunding } from "../services/projectService.js";
import { FundingProgress } from "../components/FundingProgress.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { rupeesToMinor } from "../utils/money.js";

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
 * Reached from the approved-solutions cards and the project detail. It
 * displays the verified funding goal and its DB-derived progress (server
 * integer minor units). When funding is OPEN, a supporter can enter a demo
 * support amount and is taken to the demo-payment page. The support flow is
 * explicitly a presentation/demo simulation — no real money is processed.
 * CLOSED, FULLY_FUNDED and no-goal states retain their existing behavior.
 */
export function ProjectFunding() {
  const { route, navigate } = useRouter();
  const projectId = route.params.id;

  const [project, setProject] = useState(null);
  const [fundingSummary, setFundingSummary] = useState(null);
  const [hasCampaign, setHasCampaign] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [amount, setAmount] = useState("500");
  const [amountError, setAmountError] = useState(null);

  const QUICK_AMOUNTS = [100, 500, 1000];

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

  const setAmountAndError = (value) => {
    setAmount(value);
    if (rupeesToMinor(value) === null && String(value ?? "").trim() !== "") {
      setAmountError(
        "Enter a positive amount of at least ₹0.01, e.g. 500 for ₹500 or 500.50 for ₹500.50."
      );
    } else {
      setAmountError(null);
    }
  };

  const continueToDemoPayment = () => {
    const minor = rupeesToMinor(amount);
    if (minor === null) {
      setAmountError(
        "Enter a valid amount first — at least ₹0.01, as whole rupees with up to two decimals."
      );
      return;
    }
    // The amount travels as a decimal rupee string; the server receives only
    // integer minor units computed on the demo-payment page.
    navigate(`/projects/${projectId}/funding/demo-payment?amount=${encodeURIComponent(amount)}`);
  };

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
                <section className="demo-support" style={{ marginTop: "var(--space-5)" }}>
                  <div className="demo-support-head">
                    <span className="section-kicker">Demo support</span>
                    <span className="badge-demo">Demo</span>
                  </div>
                  <h3 className="related-title">Support this solution</h3>
                  <p className="funding-note">
                    Help demonstrate how community support will work for
                    verified solutions. This is a presentation demo — no real
                    money is charged.
                  </p>

                  <div className="funding-amount-input demo-amount-input">
                    <span className="funding-amount-prefix" aria-hidden="true">
                      ₹
                    </span>
                    <input
                      id="demo-support-amount"
                      className={`form-control${amountError ? " has-error" : ""}`}
                      type="number"
                      inputMode="decimal"
                      min="0.01"
                      step="0.01"
                      value={amount}
                      onChange={(e) => setAmountAndError(e.target.value)}
                      placeholder="e.g. 500"
                      aria-invalid={amountError ? "true" : undefined}
                    />
                  </div>
                  {amountError && (
                    <span className="form-helper is-invalid" role="alert">
                      {amountError}
                    </span>
                  )}

                  <div className="demo-quick-amounts" aria-label="Quick amounts">
                    {QUICK_AMOUNTS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        className={`demo-quick-btn${amount === String(q) ? " is-active" : ""}`}
                        onClick={() => setAmountAndError(String(q))}
                      >
                        ₹{q.toLocaleString("en-IN")}
                      </button>
                    ))}
                  </div>

                  <div className="demo-support-actions">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={continueToDemoPayment}
                    >
                      Continue to demo payment
                    </button>
                  </div>

                  <p className="demo-support-note">
                    ℹ Demo only — no real money is charged. Online contributions
                    are coming soon.
                  </p>
                </section>
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