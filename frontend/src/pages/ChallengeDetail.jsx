import React, { useState, useEffect } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import {
  getChallenge,
  getRelatedChallenges,
  getDna,
} from "../services/challengeService.js";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { DnaPanel } from "../components/DnaPanel.jsx";
import { RelatedChallenges } from "../components/RelatedChallenges.jsx";
import { RecommendedInstitutions } from "../components/RecommendedInstitutions.jsx";

export function ChallengeDetail() {
  const { route } = useRouter();
  const challengeId = route.params.id;

  const [challenge, setChallenge] = useState(null);
  const [fullDna, setFullDna] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetails = async () => {
    if (!challengeId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await getChallenge(challengeId);
      setChallenge(data);

      // Full DNA (with signals/provenance) + related challenges are loaded
      // only when analysis actually exists — no wasted requests.
      if (data?.dna) {
        try {
          const [dnaDetail, relatedData] = await Promise.all([
            getDna(challengeId),
            getRelatedChallenges(challengeId),
          ]);
          setFullDna(dnaDetail);
          setRelated(relatedData?.items ?? []);
        } catch {
          // Secondary data is non-critical; the challenge itself is shown.
          setFullDna(null);
          setRelated([]);
        }
      } else {
        setFullDna(null);
        setRelated([]);
      }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          <LoadingSpinner size="lg" message="Loading challenge details..." />
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
                <button type="button" className="btn btn-secondary btn-sm" onClick={fetchDetails}>
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
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <span><strong>Location:</strong> {challenge.location}</span>
              </div>

              <div className="detail-meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <span><strong>Submitted:</strong> {formatDate(challenge.created_at)}</span>
              </div>
            </div>
          </div>

          <div className="detail-body">
            <h2 className="detail-section-heading">Ground Reality & Problem Description</h2>
            <div className="detail-description-content">
              {challenge.description.split("\n\n").map((para, idx) => (
                <p key={idx}>{para}</p>
              ))}
            </div>
          </div>
        </article>

        {/* Problem DNA / intelligence view */}
        <div style={{ marginTop: "var(--space-6)" }}>
          <DnaPanel dna={fullDna ?? challenge.dna ?? null} />
        </div>

        {/* Solution journey */}
        <section className="card journey-section" aria-labelledby="journey-heading" style={{ marginTop: "var(--space-6)" }}>
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
                  The challenge has been safely recorded and published to the open
                  community problem discovery board.
                </p>
              </div>
            </div>

            <div className={`journey-step ${challenge.dna ? "is-current" : "is-upcoming"}`}>
              <div className="step-indicator" aria-hidden="true">
                {challenge.dna ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span className="step-upcoming-dot" />
                )}
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className={`step-status-tag ${challenge.dna ? "current-tag" : "upcoming-tag"}`}>
                    {challenge.dna ? "Active State" : "Upcoming for this problem"}
                  </span>
                  <span className="step-phase">Phase 2</span>
                </div>
                <h3 className="step-title">Problem DNA & Structured Understanding</h3>
                <p className="step-desc">
                  Structured decomposition of this problem — its area, urgency,
                  affected stakeholders and expertise needed. See the Problem DNA
                  section above{challenge.dna ? "" : "; it will appear once analysis runs"}.
                </p>
              </div>
            </div>

            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming</span>
                  <span className="step-phase">Next</span>
                </div>
                <h3 className="step-title">University Lab & Expert Matching</h3>
                <p className="step-desc">
                  Academic faculties, student research labs and domain experts will be
                  recommended based on the expertise this problem needs — with explainable
                  match reasoning.
                </p>
              </div>
            </div>

            <div className="journey-step is-upcoming">
              <div className="step-indicator" aria-hidden="true">
                <span className="step-upcoming-dot" />
              </div>
              <div className="step-content">
                <div className="step-badge-row">
                  <span className="step-status-tag upcoming-tag">Upcoming</span>
                  <span className="step-phase">Then</span>
                </div>
                <h3 className="step-title">Collaborative Prototyping & Impact</h3>
                <p className="step-desc">
                  Student teams, industry mentors and communities build, pilot and deploy
                  solutions — with outcomes measured as real impact.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Related problems — only rendered when reliable relationships exist */}
        <RelatedChallenges items={related} />

        {/* Recommended institutions — deterministic baseline over Problem DNA;
            self-silencing when DNA is unreliable or no matches exist */}
        <div style={{ marginTop: "var(--space-6)" }}>
          <RecommendedInstitutions challengeId={challengeId} />
        </div>
      </div>
    </div>
  );
}
