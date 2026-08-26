import React from "react";

/** Human-readable labels for the additive capability sections (Phase 4A). */
export const CAPABILITY_SECTION_LABELS = {
  departments: "Departments",
  disciplines: "Academic Disciplines",
  expertise: "Expertise",
  research_areas: "Research Areas",
  technologies: "Technologies",
  facilities: "Facilities & Labs",
  innovation_support: "Innovation & Incubation",
  prototyping: "Prototyping Capabilities",
  project_experience: "Community / Project Experience",
  collaboration_modes: "Collaboration Modes",
};

/**
 * Renders populated capability sections of an institution.
 * All data is human-entered by the institution — nothing here is
 * AI-generated or inferred.
 */
export function CapabilitiesSection({ capabilities }) {
  if (!capabilities) return null;
  const populated = Object.entries(capabilities).filter(
    ([, items]) => Array.isArray(items) && items.length > 0
  );
  if (populated.length === 0) return null;

  return (
    <div className="capabilities-grid">
      {populated.map(([section, items]) => (
        <div key={section} className="capability-block">
          <h3 className="capability-heading">
            {CAPABILITY_SECTION_LABELS[section] ?? section}
          </h3>
          <div className="capability-items">
            {items.map((item) => (
              <span key={item} className="domain-chip">
                {item}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
