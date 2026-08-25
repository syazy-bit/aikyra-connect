import React from "react";
import { Link } from "../context/RouterContext.jsx";

/**
 * "Related community problems" — only rendered when the backend returned
 * reliable, explainable relationships (never filled with weak suggestions).
 */
export function RelatedChallenges({ items }) {
  if (!items?.length) return null;

  return (
    <section className="related-section" aria-labelledby="related-heading">
      <span className="section-kicker">Explore Further</span>
      <h2 id="related-heading" className="related-title">Related community problems</h2>
      <p className="related-subtitle">
        Other reported problems connected through shared problem areas, themes and locations,
        based on their Problem DNA.
      </p>

      <ul className="related-list">
        {items.map(({ challenge, dna, reasons }) => (
          <li key={challenge.id}>
            <Link href={`/challenges/${challenge.id}`} className="card related-card">
              <div className="related-card-top">
                {dna?.primary_domain_label && (
                  <span className="domain-chip">{dna.primary_domain_label}</span>
                )}
                {dna?.urgency && (
                  <span className={`urgency-badge urgency-${dna.urgency}`}>
                    {dna.urgency === "critical" ? "Critical" : dna.urgency.charAt(0).toUpperCase() + dna.urgency.slice(1)} urgency
                  </span>
                )}
              </div>
              <h3 className="related-card-title">{challenge.title}</h3>
              <p className="related-card-location">{challenge.location}</p>
              {reasons?.length > 0 && (
                <p className="related-reason">
                  <strong>Related because:</strong> {reasons.slice(0, 2).join(" · ")}
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
