import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { getTaxonomy } from "../services/challengeService.js";
import { listInstitutions } from "../services/institutionService.js";
import { InstitutionCard, INSTITUTION_TYPE_LABELS } from "../components/InstitutionCard.jsx";
import { SearchBar } from "../components/SearchBar.jsx";
import { SkeletonGrid } from "../components/SkeletonCard.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const PAGE_SIZE = 12;
const TYPE_KEYS = Object.keys(INSTITUTION_TYPE_LABELS);

function parseQuery(query) {
  const list = (value) =>
    (value ?? "").split(",").map((v) => v.trim()).filter(Boolean);
  return {
    q: query.q ?? "",
    types: list(query.types),
    domains: list(query.domains),
    sort: query.sort || "",
    page: Math.max(1, parseInt(query.page ?? "1", 10) || 1),
  };
}

export function Institutions() {
  const { route, navigate } = useRouter();
  const selected = useMemo(() => parseQuery(route.query), [route.query]);

  const [taxonomy, setTaxonomy] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getTaxonomy()
      .then((data) => !cancelled && setTaxonomy(data))
      .catch(() => !cancelled && setTaxonomy(null));
    return () => {
      cancelled = true;
    };
  }, []);

  const effectiveSort = selected.sort || (selected.q ? "relevance" : "newest");
  const skip = (selected.page - 1) * PAGE_SIZE;

  const { data, loading, error, retry } = useApiResource(
    () =>
      listInstitutions({
        q: selected.q,
        types: selected.types,
        domains: selected.domains,
        sort: effectiveSort === "newest" ? undefined : effectiveSort,
        skip,
        limit: PAGE_SIZE,
      }),
    [selected.q, selected.types.join(","), selected.domains.join(","),
     effectiveSort, selected.page]
  );

  const updateQuery = useCallback(
    (patch, { keepPage = false } = {}) => {
      const next = { ...route.query, ...patch };
      if (!keepPage) next.page = patch.page ?? "1";
      Object.keys(next).forEach((key) => {
        if (next[key] === "" || next[key] === undefined || next[key] === null) delete next[key];
      });
      const params = new URLSearchParams(next).toString();
      navigate(`/institutions${params ? `?${params}` : ""}`);
    },
    [navigate, route.query]
  );

  const setSearch = useCallback((q) => updateQuery({ q }), [updateQuery]);

  const toggleValue = useCallback(
    (field) => (value) => {
      const current = selected[field];
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      updateQuery({ [field]: next.join(",") });
    },
    [selected, updateQuery]
  );

  const clearAllFilters = useCallback(() => {
    updateQuery({ q: "", types: "", domains: "", sort: "" });
  }, [updateQuery]);

  const hasActiveFilters =
    selected.types.length > 0 || selected.domains.length > 0 || Boolean(selected.q);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasNextPage = skip + items.length < total;

  return (
    <div className="institutions-page">
      <div className="container">
        {/* Page header */}
        <div className="challenges-header">
          <div>
            <span className="section-kicker">Institutional Participation</span>
            <h1 className="challenges-title">Universities & Institutions</h1>
            <p className="challenges-subtitle">
              Higher education institutions, research institutes and innovation
              hubs ready to work on real societal challenges. Capability
              profiles are self-declared by each institution.
            </p>
          </div>
          <div>
            <Link href="/institutions/register" className="btn btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Register Institution
            </Link>
          </div>
        </div>

        {/* Toolbar */}
        <div className="discovery-toolbar">
          <SearchBar value={selected.q} onChange={setSearch} />
          <select
            className="sort-select"
            aria-label="Sort institutions"
            value={effectiveSort}
            onChange={(e) => updateQuery({ sort: e.target.value === "newest" ? "" : e.target.value })}
          >
            <option value="newest">Newest first</option>
            <option value="oldest" disabled={!hasActiveFilters && !selected.sort}>Oldest first</option>
            <option value="relevance" disabled={!selected.q}>Relevance{!selected.q ? " (needs search)" : ""}</option>
          </select>
        </div>

        {/* Filter chips row */}
        <div className="inst-filter-row card" aria-label="Institution filters">
          <div className="inst-filter-group">
            <h3 className="inst-filter-label">Type</h3>
            <div className="inst-filter-options">
              {TYPE_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`chip-toggle ${selected.types.includes(key) ? "is-active" : ""}`}
                  onClick={() => toggleValue("types")(key)}
                  aria-pressed={selected.types.includes(key)}
                >
                  {INSTITUTION_TYPE_LABELS[key]}
                </button>
              ))}
            </div>
          </div>
          <div className="inst-filter-group">
            <h3 className="inst-filter-label">
              Domains {taxonomy ? "" : "(loading taxonomy…)"}
            </h3>
            <div className="inst-filter-options">
              {(taxonomy?.domains ?? []).map((domain) => (
                <button
                  key={domain.key}
                  type="button"
                  className={`chip-toggle ${selected.domains.includes(domain.key) ? "is-active" : ""}`}
                  onClick={() => toggleValue("domains")(domain.key)}
                  aria-pressed={selected.domains.includes(domain.key)}
                >
                  {domain.label}
                </button>
              ))}
            </div>
          </div>
          {hasActiveFilters && (
            <button type="button" className="btn btn-secondary btn-sm inst-clear-btn" onClick={clearAllFilters}>
              Clear all filters
            </button>
          )}
        </div>

        {/* Results */}
        <div className="results-meta" aria-live="polite">
          {!loading && !error && (
            <p className="results-count">
              {total === 0
                ? "No matching institutions"
                : `${total} institution${total === 1 ? "" : "s"} found`}
              {hasActiveFilters ? " with current filters" : ""}
            </p>
          )}
        </div>

        {error && (
          <Alert type="danger" title="Could Not Load Institutions">
            <p style={{ marginBottom: "var(--space-3)" }}>
              {error.message || "Something went wrong while loading institutions."}
            </p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={retry}>
              Try Again
            </button>
          </Alert>
        )}

        {loading && <SkeletonGrid count={6} />}

        {!loading && !error && items.length === 0 && (
          <EmptyState
            title={hasActiveFilters ? "No institutions match your filters" : "No institutions registered yet"}
            description={
              hasActiveFilters
                ? "Try removing some filters or using a broader search term."
                : "Is your university, research institute or innovation hub working on societal problems? Join the Aikyra network."
            }
            actionText={hasActiveFilters ? "Clear all filters" : "Register Your Institution"}
            actionHref={hasActiveFilters ? undefined : "/institutions/register"}
            onActionClick={hasActiveFilters ? clearAllFilters : undefined}
          />
        )}

        {!loading && !error && items.length > 0 && (
          <>
            <div className="challenges-grid" role="region" aria-label="Institutions List">
              {items.map((institution) => (
                <InstitutionCard key={institution.id} institution={institution} />
              ))}
            </div>

            <nav className="pagination" role="navigation" aria-label="Institutions Pagination">
              <div className="pagination-info">
                Page <strong>{selected.page}</strong> · {total} result{total === 1 ? "" : "s"}
              </div>
              <div className="pagination-controls">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => updateQuery({ page: String(selected.page - 1) }, { keepPage: true })}
                  disabled={selected.page <= 1 || loading}
                  aria-label="Previous Page"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => updateQuery({ page: String(selected.page + 1) }, { keepPage: true })}
                  disabled={!hasNextPage || loading}
                  aria-label="Next Page"
                >
                  Next →
                </button>
              </div>
            </nav>
          </>
        )}
      </div>
    </div>
  );
}
