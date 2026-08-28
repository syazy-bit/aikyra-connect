import React from "react";
import { Link } from "../context/RouterContext.jsx";
import { StatusBadge } from "./StatusBadge.jsx";
import { matchTier } from "./RecommendedInstitutions.jsx";

const URGENCY_LABELS = {
  low: "Low urgency",
  medium: "Medium urgency",
  high: "High urgency",
  critical: "Critical urgency",
};

/**
 * Compact challenge card.
 * Optional additive props (unused elsewhere, default-off):
 *  - `match`     { institution, score } shown as a "match for your
 *                institution" badge (used by the workspace rail).
 *  - `footerAction`   extra node rendered below the meta row (e.g. a
 *                "Create a team" button in the workspace).
 */
export function ChallengeCard({ challenge, match = null, footerAction }) {
  if (!challenge) return null;
  const dna = challenge.dna ?? null;

  const formattedDate = challenge.created_at
    ? new Date(challenge.created_at).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <article className="card card-interactive" aria-labelledby={`challenge-title-${challenge.id}`}>
      <Link
        href={`/challenges/${challenge.id}`}
        className="card-header"
        aria-label={`View details for ${challenge.title}`}
      >
        <h3 id={`challenge-title-${challenge.id}`} className="card-title">
          {challenge.title}
        </h3>
      </Link>

      {/* Understanding state line — never fabricated */}
      {dna ? (
        <div className="card-dna-row">
          {dna.primary_domain_label && (
            <span className="domain-chip">{dna.primary_domain_label}</span>
          )}
          <span className={`urgency-badge urgency-${dna.urgency}`}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            {URGENCY_LABELS[dna.urgency] ?? dna.urgency}
          </span>
        </div>
      ) : (
        <div className="card-dna-row">
          <span className="analysis-pending-tag">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            Analysis pending
          </span>
        </div>
      )}

      {match && (
        <div className="card-match-row">
          <span className={`match-tier ${matchTier(match.score).className}`}>
            {matchTier(match.score).label}
          </span>
          <span className="card-match-text">
            Match for{" "}
            <Link href={`/institutions/${match.institution.id}`} className="card-match-link">
              {match.institution.name}
            </Link>
          </span>
          <span className="card-match-score" aria-label={`Match score ${match.score}`}>
            {match.score}
          </span>
        </div>
      )}

      <p className="card-description">{challenge.description}</p>

      <div className="card-meta">
        <div className="meta-item" title="Location">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span>{challenge.location}</span>
        </div>

        {formattedDate && (
          <div className="meta-item" title="Submitted Date">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <time dateTime={challenge.created_at}>{formattedDate}</time>
          </div>
        )}

        <div style={{ marginLeft: "auto" }}>
          <StatusBadge status={challenge.status} />
        </div>
      </div>

      {footerAction && <div className="card-footer-action">{footerAction}</div>}
    </article>
  );
}
