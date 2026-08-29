import React, { useMemo } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { listProjects } from "../services/projectService.js";
import { SkeletonGrid } from "../components/SkeletonCard.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

function formatDate(dateString) {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const PAGE_SIZE = 12;

function parseQuery(query) {
  return {
    page: Math.max(1, parseInt(query.page ?? "1", 10) || 1),
  };
}

export function Projects() {
  const { route } = useRouter();
  const selected = useMemo(() => parseQuery(route.query), [route.query]);
  const skip = (selected.page - 1) * PAGE_SIZE;

  const { data, loading, error, retry } = useApiResource(
    () => listProjects({ skip, limit: PAGE_SIZE }),
    [selected.page]
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasNextPage = skip + items.length < total;

  return (
    <div className="projects-page">
      <div className="container">
        {/* Page header */}
        <header className="challenges-header">
          <div>
            <span className="section-kicker">Approved Solutions</span>
            <h1 className="challenges-title">Projects</h1>
            <p className="challenges-subtitle">
              Approved university solutions ready for real-world support. An
              industry organization or NGO can offer funding, equipment,
              mentorship, or pilot support to help an idea reach impact.
            </p>
          </div>
        </header>

        {error && (
          <Alert type="danger" title="Could Not Load Projects">
            <p style={{ marginBottom: "var(--space-3)" }}>
              {error.message || "Something went wrong while loading projects."}
            </p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={retry}>
              Try Again
            </button>
          </Alert>
        )}

        {loading && <SkeletonGrid count={6} />}

        {!loading && !error && items.length === 0 && (
          <EmptyState
            title="No approved solutions yet"
            description="When a university team's proposal is accepted, it appears here as a project that organizations can support."
            actionText="Explore challenges"
            actionHref="/challenges"
          />
        )}

        {!loading && !error && items.length > 0 && (
          <>
            <p className="results-count" aria-live="polite">
              {total} approved solution{total === 1 ? "" : "s"}
            </p>
            <div className="projects-grid" role="region" aria-label="Projects List">
              {items.map((project) => (
                <article
                  key={project.id}
                  className="card card-interactive"
                  aria-labelledby={`project-title-${project.id}`}
                >
                  <Link
                    href={`/projects/${project.id}`}
                    className="card-header"
                    aria-label={`View project ${project.title}`}
                  >
                    <h3 id={`project-title-${project.id}`} className="card-title">
                      {project.title}
                    </h3>
                  </Link>

                  <div className="card-meta">
                    <div className="meta-item" title="Institution">
                      <span>{project.institution_name}</span>
                    </div>
                    <div className="meta-item" title="Team">
                      <span>Team · {project.team_name}</span>
                    </div>
                    <div className="meta-item" title="Challenge">
                      <span>{project.challenge_title}</span>
                    </div>
                  </div>

                  <div className="card-meta card-meta-secondary">
                    <span className="support-count">
                      {project.offer_count === 0
                        ? "No support offers yet"
                        : `${project.offer_count} support offer${
                            project.offer_count === 1 ? "" : "s"
                          }`}
                    </span>
                    <span>{formatDate(project.created_at)}</span>
                  </div>
                </article>
              ))}
            </div>

            {hasNextPage && (
              <nav className="pagination" role="navigation" aria-label="Projects Pagination">
                <div className="pagination-info">
                  Page <strong>{selected.page}</strong> · {total} project{total === 1 ? "" : "s"}
                </div>
                <div className="pagination-controls">
                  <Link
                    href={`/projects?page=${Math.max(1, selected.page - 1)}`}
                    className={`btn btn-secondary btn-sm ${selected.page <= 1 ? "disabled" : ""}`}
                  >
                    ← Previous
                  </Link>
                  <Link
                    href={`/projects?page=${selected.page + 1}`}
                    className={`btn btn-secondary btn-sm ${hasNextPage ? "" : "disabled"}`}
                  >
                    Next →
                  </Link>
                </div>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}
