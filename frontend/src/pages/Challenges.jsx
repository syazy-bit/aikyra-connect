import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import {
  getTaxonomy,
  listChallenges,
} from "../services/challengeService.js";
import { ChallengeCard } from "../components/ChallengeCard.jsx";
import { SearchBar } from "../components/SearchBar.jsx";
import { FilterControls } from "../components/Filters.jsx";
import { ActiveFilterChips } from "../components/ActiveFilterChips.jsx";
import { SortSelect } from "../components/SortSelect.jsx";
import { SkeletonGrid } from "../components/SkeletonCard.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { useApiResource } from "../hooks/useApiResource.js";

const PAGE_SIZE = 12;

function parseQuery(query) {
  const list = (value) =>
    (value ?? "").split(",").map((v) => v.trim()).filter(Boolean);
  return {
    q: query.q ?? "",
    domains: list(query.domains),
    urgencies: list(query.urgencies),
    location: query.location ?? "",
    sort: query.sort || "",
    page: Math.max(1, parseInt(query.page ?? "1", 10) || 1),
  };
}

export function Challenges() {
  const { route, navigate } = useRouter();
  const selected = useMemo(() => parseQuery(route.query), [route.query]);

  const [filtersOpen, setFiltersOpen] = useState(false);
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

  // Relevance becomes the default ordering while searching (deterministic
  // lexical ranking — the honest Phase 3 baseline).
  const effectiveSort =
    selected.sort ||
    (selected.q ? "relevance" : "newest");

  const skip = (selected.page - 1) * PAGE_SIZE;
  const { data, loading, error, retry } = useApiResource(
    () =>
      listChallenges({
        q: selected.q,
        domains: selected.domains,
        urgencies: selected.urgencies,
        location: selected.location,
        sort: effectiveSort === "newest" ? undefined : effectiveSort,
        skip,
        limit: PAGE_SIZE,
      }),
    [selected.q, selected.domains.join(","), selected.urgencies.join(","),
     selected.location, effectiveSort, selected.page]
  );

  const updateQuery = useCallback(
    (patch, { keepPage = false } = {}) => {
      const next = { ...route.query, ...patch };
      if (!keepPage) next.page = patch.page ?? "1";
      Object.keys(next).forEach((key) => {
        if (next[key] === "" || next[key] === undefined || next[key] === null) delete next[key];
      });
      const params = new URLSearchParams(next).toString();
      navigate(`/challenges${params ? `?${params}` : ""}`);
    },
    [navigate, route.query]
  );

  const setSearch = useCallback((q) => updateQuery({ q }), [updateQuery]);

  const toggleDomain = useCallback(
    (key) => {
      const domains = selected.domains.includes(key)
        ? selected.domains.filter((d) => d !== key)
        : [...selected.domains, key];
      updateQuery({ domains: domains.join(",") });
    },
    [selected.domains, updateQuery]
  );

  const toggleUrgency = useCallback(
    (level) => {
      const urgencies = selected.urgencies.includes(level)
        ? selected.urgencies.filter((u) => u !== level)
        : [...selected.urgencies, level];
      updateQuery({ urgencies: urgencies.join(",") });
    },
    [selected.urgencies, updateQuery]
  );

  const setLocation = useCallback(
    (value) => {
      // Debounce-free: committed on Enter or blur to avoid a request per keystroke.
      updateQuery({ location: value.trim() }, { keepPage: true });
    },
    [updateQuery]
  );

  const clearAllFilters = useCallback(() => {
    updateQuery({ q: "", domains: "", urgencies: "", location: "", sort: "" });
  }, [updateQuery]);

  const hasActiveFilters =
    selected.domains.length > 0 ||
    selected.urgencies.length > 0 ||
    Boolean(selected.location) ||
    Boolean(selected.q);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasNextPage = skip + items.length < total;
  const isFiltering = hasActiveFilters;

  const goToPage = (page) => {
    updateQuery({ page: String(page) }, { keepPage: true });
  };

  return (
    <div className="challenges-page">
      <div className="container">
        {/* Page Header */}
        <div className="challenges-header">
          <div>
            <span className="section-kicker">Community Problem Discovery</span>
            <h1 className="challenges-title">What are communities facing?</h1>
            <p className="challenges-subtitle">
              A living board of ground-level societal problems reported by citizens.
              Each challenge carries structured understanding to help students,
              researchers and organizations find problems worth solving.
            </p>
          </div>
          <div>
            <Link href="/report" className="btn btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Report a Problem
            </Link>
          </div>
        </div>

        {/* Search + sort toolbar */}
        <div className="discovery-toolbar">
          <SearchBar value={selected.q} onChange={setSearch} />
          <SortSelect
            value={effectiveSort}
            hasQuery={Boolean(selected.q)}
            onChange={(sort) => updateQuery({ sort })}
          />
          <button
            type="button"
            className="btn btn-secondary filters-toggle"
            aria-expanded={filtersOpen}
            onClick={() => setFiltersOpen(true)}
          >
            Filters{hasActiveFilters ? ` (${selected.domains.length + selected.urgencies.length + (selected.location ? 1 : 0)})` : ""}
          </button>
        </div>

        <div className="discovery-layout">
          {/* Desktop filter rail */}
          <aside className="filters-rail card" aria-label="Discovery filters">
            <h2 className="filters-title">Refine</h2>
            <FilterControls
              taxonomy={taxonomy}
              selected={selected}
              onToggleDomain={toggleDomain}
              onToggleUrgency={toggleUrgency}
              onLocationChange={setLocation}
              location={selected.location}
            />
            {hasActiveFilters && (
              <button type="button" className="btn btn-secondary btn-sm clear-filters-btn" onClick={clearAllFilters}>
                Clear all filters
              </button>
            )}
          </aside>

          {/* Results column */}
          <div className="discovery-results">
            <div className="results-meta" aria-live="polite">
              {!loading && !error && (
                <p className="results-count">
                  {total === 0
                    ? "No matching problems"
                    : `${total} problem${total === 1 ? "" : "s"} found`}
                  {isFiltering ? " with current filters" : ""}
                </p>
              )}
            </div>

            <ActiveFilterChips
              selected={selected}
              taxonomy={taxonomy}
              onRemoveDomain={toggleDomain}
              onRemoveUrgency={toggleUrgency}
              onClearLocation={() => updateQuery({ location: "" })}
              onRemoveSearch={() => setSearch("")}
              onClearAll={clearAllFilters}
            />

            {error && (
              <Alert type="danger" title="Could Not Load Challenges">
                <p style={{ marginBottom: "var(--space-3)" }}>
                  {error.message || "Something went wrong while loading community challenges."}
                </p>
                <button type="button" className="btn btn-secondary btn-sm" onClick={retry}>
                  Try Again
                </button>
              </Alert>
            )}

            {loading && <SkeletonGrid count={6} />}

            {!loading && !error && items.length === 0 && (
              <EmptyState
                title={isFiltering ? "No problems match your filters" : "No community challenges yet"}
                description={
                  isFiltering
                    ? "Try removing some filters, checking your spelling, or using a broader search term."
                    : "Be the first to bring a real problem in your community to the Aikyra network."
                }
                actionText={isFiltering ? "Clear all filters" : "Report a Community Problem"}
                actionHref={isFiltering ? undefined : "/report"}
                onActionClick={isFiltering ? clearAllFilters : undefined}
              />
            )}

            {!loading && !error && items.length > 0 && (
              <>
                <div className="challenges-grid" role="region" aria-label="Challenges List">
                  {items.map((challenge) => (
                    <ChallengeCard key={challenge.id} challenge={challenge} />
                  ))}
                </div>

                <nav className="pagination" role="navigation" aria-label="Challenges Pagination">
                  <div className="pagination-info">
                    Page <strong>{selected.page}</strong> · {total} result{total === 1 ? "" : "s"}
                  </div>
                  <div className="pagination-controls">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => goToPage(selected.page - 1)}
                      disabled={selected.page <= 1 || loading}
                      aria-label="Previous Page"
                    >
                      ← Previous
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => goToPage(selected.page + 1)}
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
      </div>

      {/* Mobile filter sheet */}
      {filtersOpen && (
        <div className="filter-sheet-overlay" onClick={() => setFiltersOpen(false)}>
          <div
            className="filter-sheet"
            role="dialog"
            aria-modal="true"
            aria-label="Discovery filters"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="filter-sheet-header">
              <h2>Refine</h2>
              <button
                type="button"
                ref={(el) => el && el.focus()}
                className="filter-sheet-close"
                aria-label="Close filters"
                onClick={() => setFiltersOpen(false)}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <FilterControls
              taxonomy={taxonomy}
              selected={selected}
              onToggleDomain={toggleDomain}
              onToggleUrgency={toggleUrgency}
              onLocationChange={setLocation}
              location={selected.location}
            />
            <div className="filter-sheet-footer">
              {hasActiveFilters && (
                <button type="button" className="btn btn-secondary" onClick={clearAllFilters}>
                  Clear all
                </button>
              )}
              <button type="button" className="btn btn-primary" onClick={() => setFiltersOpen(false)}>
                Show results{!loading && total > 0 ? ` (${total})` : ""}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
