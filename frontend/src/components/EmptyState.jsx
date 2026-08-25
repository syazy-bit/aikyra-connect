import React from "react";
import { Link } from "../context/RouterContext.jsx";

export function EmptyState({
  title = "No community challenges yet",
  description = "Be the first to bring a real problem in your community to the Aikyra network.",
  actionText = "Report a Problem",
  actionHref = "/report",
  onActionClick,
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>

      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-text">{description}</p>

      {actionHref && !onActionClick && (
        <Link href={actionHref} className="btn btn-primary">
          {actionText}
        </Link>
      )}

      {onActionClick && (
        <button type="button" onClick={onActionClick} className="btn btn-primary">
          {actionText}
        </button>
      )}
    </div>
  );
}
