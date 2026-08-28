import React from "react";
import { Link } from "../context/RouterContext.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Team card for the university workspace. Shows the team's identity,
 * status, home institution and the number of proposals it has drafted —
 * so the challenge → team → proposal relationship stays visible at a glance.
 */
export function TeamCard({ team, institution, proposalCount = 0 }) {
  if (!team) return null;

  const formattedDate = formatDate(team.created_at);

  return (
    <article
      className="card card-interactive team-card"
      aria-labelledby={`team-title-${team.id}`}
    >
      <div className="team-card-header">
        <Link
          href={`/teams/${team.id}`}
          className="card-header team-card-link"
          aria-label={`Open team ${team.name}`}
        >
          <h3 id={`team-title-${team.id}`} className="card-title">
            {team.name}
          </h3>
        </Link>
        <StatusBadge status={team.status} />
      </div>

      <div className="team-card-meta">
        {institution && (
          <Link
            href={`/institutions/${institution.id}`}
            className="type-chip"
            style={{ textDecoration: "none" }}
          >
            {institution.name}
          </Link>
        )}
        {formattedDate && (
          <span className="meta-item" title="Team created">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <time dateTime={team.created_at}>{formattedDate}</time>
          </span>
        )}
      </div>

      {team.description && (
        <p className="card-description team-card-description">{team.description}</p>
      )}

      <div className="team-card-footer">
        <span className="proposal-count-chip">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          {proposalCount === 0
            ? "No proposals yet"
            : `${proposalCount} proposal${proposalCount === 1 ? "" : "s"}`}
        </span>
        <Link href={`/teams/${team.id}`} className="btn btn-secondary btn-sm">
          View team →
        </Link>
      </div>
    </article>
  );
}