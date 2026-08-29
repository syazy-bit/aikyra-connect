import React, { useState, useEffect } from "react";
import { Link } from "../context/RouterContext.jsx";
import { getDashboard } from "../services/dashboardService.js";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { StatusBadge } from "../components/StatusBadge.jsx";
import { SupportTypeBadge } from "../components/SupportTypeBadge.jsx";

const CHALLENGE_STATUS_ROWS = [
  { label: "Submitted", key: "submitted" },
  { label: "Under Review", key: "under_review" },
  { label: "Validated", key: "validated" },
  { label: "Rejected", key: "rejected" },
];

const PROJECT_STATUS_ROWS = [
  { label: "Prototype", key: "prototype" },
  { label: "Pilot", key: "pilot" },
  { label: "Implemented", key: "implemented" },
];

const SUPPORT_TYPE_ROWS = [
  { label: "Funding", key: "funding" },
  { label: "Equipment", key: "equipment" },
  { label: "Mentorship", key: "mentorship" },
  { label: "Pilot Support", key: "pilot_support" },
];

// Narrative impact must never imply that "no data" means "zero impact".
// Absent allowlisted results show these explicit empty messages instead.
const KEY_RESULTS = [
  {
    name: "Households reached",
    empty: "No household impact reported yet.",
  },
  {
    name: "Villages covered",
    empty: "No villages covered data reported yet.",
  },
  {
    name: "Pilot participants",
    empty: "No participants reported yet.",
  },
];

function formatGeneratedAt(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function SectionHeading({ kicker, title, description }) {
  return (
    <div className="section-header">
      {kicker && <span className="section-kicker">{kicker}</span>}
      <h2 className="section-title">{title}</h2>
      {description && <p className="section-description">{description}</p>}
    </div>
  );
}

function StatCards({ items }) {
  return (
    <div className="stat-grid">
      {items.map((item) => (
        <div className="stat-card" key={item.label}>
          <span className="stat-value">{item.value}</span>
          <span className="stat-label">{item.label}</span>
          {item.value === 0 && item.zeroHint && (
            <span className="stat-hint">{item.zeroHint}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function PipelineCard({ index, title, accent, rows }) {
  return (
    <div className={`pipeline-card${accent ? " pipeline-card-accent" : ""}`}>
      {index && <div className="pipeline-step">{index}</div>}
      <h3 className="card-title pipeline-card-title">{title}</h3>
      <div className="pipeline-rows">
        {rows.map((row) => (
          <div className="summary-row" key={row.label}>
            <span className="summary-label">{row.label}</span>
            {row.status ? (
              <StatusBadge status={row.status} />
            ) : (
              <span className="summary-value">{row.value}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function EcosystemSection({ ecosystem }) {
  return (
    <section className="dashboard-section" aria-labelledby="dashboard-ecosystem-el">
      <div className="container">
        <SectionHeading
          kicker="The Ecosystem"
          title="Aikyra at a Glance"
          description="The institutions, communities, teams and people working together on real societal problems."
        />
        <StatCards
          items={[
            {
              label: "Institutions",
              value: ecosystem.institutions,
              zeroHint: "No institutions yet",
            },
            {
              label: "Challenges Reported",
              value: ecosystem.challenges_reported,
              zeroHint: "No challenges reported yet",
            },
            {
              label: "Teams Formed",
              value: ecosystem.teams_formed,
              zeroHint: "No teams formed yet",
            },
            {
              label: "People Engaged",
              value: ecosystem.people_engaged,
              zeroHint: "No participants yet",
            },
          ]}
        />
      </div>
    </section>
  );
}

function PipelineSection({ pipeline }) {
  const { challenges_by_status, projects_by_status } = pipeline;
  return (
    <section className="dashboard-section" aria-labelledby="dashboard-pipeline-el">
      <div className="container">
        <SectionHeading
          kicker="The Aikyra Pipeline"
          title="From Problem to Outcome"
          description="Every community problem that enters Aikyra moves through a transparent path: challenges, proposals, approved solutions, and finally documented outcomes."
        />

        <div className="pipeline-flow">
          <PipelineCard
            index="01"
            title="Community Problems"
            rows={[
              { label: "Total reported", value: pipeline.challenges_reported },
              ...CHALLENGE_STATUS_ROWS.map(({ label, key }) => ({
                label,
                value: challenges_by_status[key] ?? 0,
              })),
            ]}
          />
          <div className="pipeline-arrow" aria-hidden="true">→</div>

          <PipelineCard
            index="02"
            title="Proposals"
            rows={[
              { label: "Submitted", value: pipeline.proposals_submitted },
              { label: "Accepted", value: pipeline.proposals_accepted },
            ]}
          />
          <div className="pipeline-arrow" aria-hidden="true">→</div>

          <PipelineCard
            index="03"
            title="Approved Solutions"
            accent
            rows={[
              ...PROJECT_STATUS_ROWS.map(({ label, key }) => ({
                label,
                value: projects_by_status[key] ?? 0,
              })),
              { label: "Total", value: pipeline.projects_total },
            ]}
          />
          <div className="pipeline-arrow" aria-hidden="true">→</div>

          <PipelineCard
            index="04"
            title="Measurable Outcome"
            rows={[
              { label: "Implemented", value: projects_by_status.implemented ?? 0 },
              { label: "Reports published", value: pipeline.outcome_reports },
            ]}
          />
        </div>
      </div>
    </section>
  );
}

function SupportSection({ support }) {
  return (
    <section className="dashboard-section" aria-labelledby="dashboard-support-el">
      <div className="container">
        <SectionHeading
          kicker="Industry & NGOs"
          title="Support Ecosystem"
          description="Organizations that stand behind approved solutions with funding, equipment, mentorship and pilot support."
        />

        <div className="stat-grid stat-grid-slim">
          <div className="stat-card">
            <span className="stat-value">{support.organizations}</span>
            <span className="stat-label">Organizations Joined</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{support.offers_total}</span>
            <span className="stat-label">Support Offers Made</span>
          </div>
        </div>

        <div className="card support-types-card">
          <h3 className="card-title support-types-title">Support by Type</h3>
          <div className="pipeline-rows">
            {SUPPORT_TYPE_ROWS.map(({ label, key }) => (
              <div className="summary-row" key={key}>
                <SupportTypeBadge type={key} />
                <span className="summary-value">{support.offers_by_type[key] ?? 0}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function ImpactSection({ impact }) {
  const reportedByName = Object.fromEntries(
    (impact.reported_metrics ?? []).map((m) => [m.name, m])
  );

  return (
    <section className="dashboard-section" aria-labelledby="dashboard-impact-el">
      <div className="container">
        <SectionHeading
          kicker="Measurable Social Impact"
          title="Reported Impact"
          description="Real impact evidence teams have recorded for their approved solutions."
        />

        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-value">{impact.metrics_total}</span>
            <span className="stat-label">Metrics Reported</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{impact.projects_reporting}</span>
            <span className="stat-label">Projects Reporting Impact</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{impact.projects_with_report}</span>
            <span className="stat-label">Projects With Outcome Reports</span>
          </div>
        </div>

        <div className="card key-results-card">
          <h3 className="card-title key-results-title">Key results to date</h3>
          <div className="pipeline-rows">
            {KEY_RESULTS.map(({ name, empty }) => {
              const entry = reportedByName[name];
              return (
                <div className="summary-row" key={name}>
                  <span className="summary-label">{name}</span>
                  {entry ? (
                    <span className="key-result-value">
                      {entry.total} {entry.unit}
                    </span>
                  ) : (
                    <span className="dashboard-empty-note">{empty}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function RecentImplemented({ recent }) {
  return (
    <section className="dashboard-section" aria-labelledby="dashboard-recent-el">
      <div className="container">
        <SectionHeading
          kicker="Deployed in Communities"
          title="Recently Implemented"
          description="Approved solutions that completed the full lifecycle, with the impact evidence reported by their teams."
        />

        {recent.length === 0 ? (
          <EmptyState
            title="No implemented projects yet"
            description="Approved solutions that complete the full life cycle will appear here with their reported impact."
            actionText="View Approved Solutions"
            actionHref="/projects"
          />
        ) : (
          <div className="recent-grid">
            {recent.map((project) => (
              <Link
                key={project.project_id}
                href={`/projects/${project.project_id}`}
                className="card card-interactive recent-card"
              >
                <div className="card-header recent-card-head">
                  <h3 className="card-title recent-card-title">{project.title}</h3>
                </div>
                <div className="recent-card-status">
                  <StatusBadge status={project.status} />
                </div>
                <div className="metric-chips" aria-label="Reported impact metrics">
                  {project.metrics.length === 0 ? (
                    <span className="dashboard-empty-note">
                      No impact metrics reported yet.
                    </span>
                  ) : (
                    project.metrics.map((metric, index) => (
                      <span className="metric-chip" key={`${metric.name}-${index}`}>
                        {metric.value}
                        {metric.unit ? ` ${metric.unit}` : ""}
                      </span>
                    ))
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError(null);
        const payload = await getDashboard();
        if (mounted) {
          setData(payload);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load the impact dashboard.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero" aria-labelledby="dashboard-heading">
        <div className="container">
          <span className="section-kicker">Impact Dashboard</span>
          <h1 id="dashboard-heading" className="dashboard-title">
            From Community Problems to Measurable Impact
          </h1>
          <p className="dashboard-lead">
            Live figures from the Aikyra ecosystem.
          </p>
          {data?.generated_at && (
            <span className="dashboard-generated">
              Updated {formatGeneratedAt(data.generated_at)}
            </span>
          )}
        </div>
      </section>

      {loading && (
        <div className="container">
          <LoadingSpinner message="Aggregating live ecosystem data from the database..." />
        </div>
      )}

      {error && (
        <div className="container" role="status">
          <Alert type="danger" title="Could not load the dashboard">
            {error}
          </Alert>
        </div>
      )}

      {!loading && !error && data && (
        <>
          <EcosystemSection ecosystem={data.ecosystem} />
          <PipelineSection pipeline={data.pipeline} />
          <SupportSection support={data.support} />
          <ImpactSection impact={data.impact} />
          <RecentImplemented recent={data.impact.recent_implemented} />
        </>
      )}
    </div>
  );
}