import React, { useState, useEffect } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getChallenge } from "../services/challengeService.js";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";

export function ChallengeDetail() {
  const { route } = useRouter();
  const challengeId = route.params.id;

  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetails = async () => {
    if (!challengeId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await getChallenge(challengeId);
      setChallenge(data);
    } catch (err) {
      setError(
        err.message ||
          "Could not retrieve this challenge. It may not exist or the server is unavailable."
      );
      setChallenge(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [challengeId]);

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <LoadingSpinner size="lg" message="Loading challenge details from database..." />
        </div>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="detail-page">
        <div className="container-narrow">
          <Link href="/challenges" className="back-link">
            ← Back to All Challenges
          </Link>
          <div className="card" style={{ marginTop: "var(--space-4)" }}>
            <Alert type="danger" title="Challenge Not Found">
              <p style={{ marginBottom: "var(--space-3)" }}>
                {error || "We could not find the challenge with the requested identifier."}
              </p>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={fetchDetails}
                >
                  Retry
                </button>
                <Link href="/challenges" className="btn btn-primary btn-sm">
                  Return to Community Challenges
                </Link>
              </div>
            </Alert>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="container-narrow">
        {/* Navigation Breadcrumb */}
        <Link href="/challenges" className="back-link">
          ← Back to Community Challenges
        </Link>

        {/* Main Challenge Card */}
        <article className="card detail-card" aria-labelledby="challenge-title">
          {/* Header */}
          <div className="detail-header">
            <div className="detail-status-row">
              <StatusBadge status={challenge.status} />
              <span className="detail-id" title="Challenge UUID">
                ID: {challenge.id}
              </span>
            </div>

            <h1 id="challenge-title" className="detail-title">
              {challenge.title}
            </h1>

            <div className="detail-meta-bar">
              <div className="detail-meta-item">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <span><strong>Location:</strong> {challenge.location}</span>
              </div>

              <div className="detail-meta-item">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <span><strong>Submitted:</strong> {formatDate(challenge.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Description Section */}
          <div className="detail-body">
            <h2 className="detail-section-heading">Ground Reality & Problem Description</h2>
            <div className="detail-description-content">
              {challenge.description.split("\n\n").map((para, idx) => (
                <p key={idx}>{para}</p>
              ))}
            </div>
          </div>
        </article>

        {/* ====================================================================
            Aikyra Solution Journey Architecture (CURRENT vs UPCOMING)
            Clearly demarcates what is currently active vs future roadmap phases.
            ==================================================================== */}
        <section
          className="card journey-section"
          aria-labelledby="journey-heading"
          style={{ marginTop: "var(--space-8)" }}
        >
          <div className="journey-header">
            <span className="section-kicker">Solution Journey Architecture</span>
            <h2 id="journey-heading" className="journey-title">
              How This Problem Advances
            </h2>
            <p className="journey-subtitle">
              Aikyra connects community submissions with a transparent development lifecycle.
              Below is the structured path this challenge takes toward a deployed solution.
            </p>
          </div>

          <div className="journey-timeline">
            {/* Step 1: CURRENT */}
            <div className="journey-step is-current">
              <div className="step-indicator" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag current-tag">Active State</span>
                  <span className="step-phase">Phase 1</span>
                </div>
                <h3 className="step-title">Problem Submitted & Recorded</h3>
                <p className="step-desc">
                  The challenge has been safely recorded in the Aikyra PostgreSQL database and
                  is published to the open community problem discovery board.
                </p>
              </div>
            </div>

            {/* Step 2: UPCOMING */}
            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming Phase</span>
                  <span className="step-phase">Phase 2</span>
                </div>
                <h3 className="step-title">Problem DNA & Root Cause Analysis</h3>
                <p className="step-desc">
                  Structured problem decomposition identifying severity, affected demographics,
                  SDG alignment, and core engineering requirements for prospective research teams.
                </p>
              </div>
            </div>

            {/* Step 3: UPCOMING */}
            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming Phase</span>
                  <span className="step-phase">Phase 3</span>
                </div>
                <h3 className="step-title">University Lab & Student Matching</h3>
                <p className="step-desc">
                  Academic faculties, student research labs, and multidisciplinary innovators
                  are recommended challenges based on departmental expertise and student skills.
                </p>
              </div>
            </div>

            {/* Step 4: UPCOMING */}
            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming Phase</span>
                  <span className="step-phase">Phase 4</span>
                </div>
                <h3 className="step-title">Collaborative Prototyping</h3>
                <p className="step-desc">
                  Student teams and industry mentors collaborate to build, test, and iterate
                  on viable engineering prototypes with community feedback.
                </p>
              </div>
            </div>

            {/* Step 5: UPCOMING */}
            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming Phase</span>
                  <span className="step-phase">Phase 5</span>
                </div>
                <h3 className="step-title">Deployment & Measurable Impact</h3>
                <p className="step-desc">
                  Validation in the field with measurable social impact metrics reported back
                  to the citizen and stakeholders.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
