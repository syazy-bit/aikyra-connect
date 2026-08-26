import React, { useEffect, useState } from "react";
import { Link } from "../context/RouterContext.jsx";
import { getChallengeMatches } from "../services/challengeService.js";

const FACTOR_LABELS = {
  domain: "Domain relevance",
  expertise: "Expertise overlap",
  research: "Research capability",
  facilities: "Facilities",
  track_record: "Project experience",
  location: "Location relevance",
  urgency: "Urgency context",
};

function matchTier(score) {
  if (score >= 60) return { label: "Strong match", className: "tier-strong" };
  if (score >= 35) return { label: "Promising", className: "tier-promising" };
  return { label: "Exploratory", className: "tier-exploratory" };
}

/**
 * "Recommended institutions" — deterministic rule-based baseline over the
 * challenge's Problem DNA and verified institutions' declared capabilities.
 * Never AI-generated; every score ships with its factor breakdown.
 *
 * Deliberately self-silencing: any failure (409 for unreliable DNA,
 * network errors) simply hides the section — it must never break the
 * challenge detail page.
 */
export function RecommendedInstitutions({ challengeId }) {
  const [state, setState] = useState({ status: "idle" });

  useEffect(() => {
    if (!challengeId) return undefined;
    let cancelled = false;
    setState({ status: "loading" });
    getChallengeMatches(challengeId)
      .then((data) => !cancelled && setState({ status: "ready", data }))
      .catch(() => !cancelled && setState({ status: "error" }));
    return () => {
      cancelled = true;
    };
  }, [challengeId]);

  if (state.status !== "ready") return null;
  const items = state.data?.items ?? [];
  if (!items.length) return null;

  return (
    <section
      className="related-section match-section"
      aria-labelledby="matches-heading"
    >
      <span className="section-kicker">Deterministic Capability Match</span>
      <h2 id="matches-heading" className="related-title">
        Recommended institutions
      </h2>
      <p className="related-subtitle">
        Verified institutions whose declared domains, expertise and facilities
        align with this problem's DNA — ranked by a transparent weighted
        baseline. Recommendations are computed, never assigned; institutions
        decide whether to engage.
      </p>

      <ol className="match-list">
        {items.map(({ institution, score, score_breakdown, reasons }, index) => {
          const tier = matchTier(score);
          return (
            <li key={institution.id} className="card match-card">
              <div className="match-card-main">
                <div className="match-rank" aria-hidden="true">#{index + 1}</div>
                <div className="match-card-body">
                  <Link
                    href={`/institutions/${institution.id}`}
                    className="match-card-title"
                  >
                    {institution.name}
                  </Link>
                  <p className="match-card-location">{institution.location}</p>
                  {(reasons?.length ?? 0) > 0 && (
                    <p className="related-reason">
                      <strong>Why:</strong> {reasons.slice(0, 2).join(" · ")}
                    </p>
                  )}
                  <details className="match-breakdown">
                    <summary>Score breakdown</summary>
                    <ul className="match-breakdown-list">
                      {Object.entries(score_breakdown).map(
                        ([factor, { points, max, detail }]) => (
                          <li key={factor} className={points > 0 ? "" : "is-zero"}>
                            <span className="match-factor-label">
                              {FACTOR_LABELS[factor] ?? factor}
                            </span>
                            <span className="match-factor-points">
                              +{points} / {max}
                              {detail.length > 0 && (
                                <em className="match-factor-detail">
                                  {" "}— {detail.join(", ")}
                                </em>
                              )}
                            </span>
                          </li>
                        )
                      )}
                    </ul>
                  </details>
                </div>
                <div className="match-score-block">
                  <span className="match-score" aria-label={`Match score ${score}`}>
                    {score}
                  </span>
                  <span className={`match-tier ${tier.className}`}>{tier.label}</span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
