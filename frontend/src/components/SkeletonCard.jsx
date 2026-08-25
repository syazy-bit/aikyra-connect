import React from "react";

/** Card-shaped loading placeholder shown while discovery results load. */
export function SkeletonCard() {
  return (
    <article className="card skeleton-card" aria-hidden="true">
      <div className="skeleton-line skeleton-line-tags" />
      <div className="skeleton-line skeleton-line-title" />
      <div className="skeleton-line skeleton-line-body" />
      <div className="skeleton-line skeleton-line-body short" />
      <div className="skeleton-line skeleton-line-meta" />
    </article>
  );
}

export function SkeletonGrid({ count = 6 }) {
  return (
    <div className="challenges-grid" role="status" aria-label="Loading challenges">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
