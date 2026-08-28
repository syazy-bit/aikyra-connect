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
 * Proposal summary row — used in the workspace (grouped by team) and on the
 * team detail page. One click opens the full proposal.
 */
export function ProposalRow({ proposal, team, showTeam = true }) {
  if (!proposal) return null;
  const date = proposal.submitted_at || proposal.created_at;
  const dateText = formatDate(date);

  return (
    <Link
      href={`/proposals/${proposal.id}`}
      className="proposal-row"
      aria-label={`Open proposal: ${proposal.title}`}
    >
      <span className="proposal-row-main">
        <span className="proposal-row-title">{proposal.title}</span>
        <span className="proposal-row-meta">
          {showTeam && team ? `${team.name} · ` : ""}
          {dateText ? `Updated ${dateText}` : "Draft"}
        </span>
      </span>
      <StatusBadge status={proposal.status} />
    </Link>
  );
}