import React from "react";
import { Link } from "../context/RouterContext.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

export function ChallengeCard({ challenge }) {
  if (!challenge) return null;

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

      <p className="card-description">{challenge.description}</p>

      <div className="card-meta">
        <div className="meta-item" title="Location">
          <svg
            width="14"
            height="14"
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
          <span>{challenge.location}</span>
        </div>

        {formattedDate && (
          <div className="meta-item" title="Submitted Date">
            <svg
              width="14"
              height="14"
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
            <time dateTime={challenge.created_at}>{formattedDate}</time>
          </div>
        )}

        <div style={{ marginLeft: "auto" }}>
          <StatusBadge status={challenge.status} />
        </div>
      </div>
    </article>
  );
}
