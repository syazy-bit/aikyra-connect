import React, { useState, useEffect } from "react";
import { Link } from "../context/RouterContext.jsx";
import { getChallenges } from "../services/challengeService.js";
import { ChallengeCard } from "../components/ChallengeCard.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";

const PAGE_SIZE = 12;

export function Challenges() {
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);

  const fetchPage = async (pageNumber) => {
    try {
      setLoading(true);
      setError(null);

      const skip = (pageNumber - 1) * PAGE_SIZE;
      // Fetch one extra item to check if there is a next page
      const data = await getChallenges({ skip, limit: PAGE_SIZE + 1 });

      if (data && data.length > PAGE_SIZE) {
        setHasNextPage(true);
        setChallenges(data.slice(0, PAGE_SIZE));
      } else {
        setHasNextPage(false);
        setChallenges(data || []);
      }
    } catch (err) {
      setError(
        err.message ||
          "Unable to load community challenges from the database. Please try again."
      );
      setChallenges([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPage(page);
  }, [page]);

  const handlePrevPage = () => {
    if (page > 1) {
      setPage((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleNextPage = () => {
    if (hasNextPage) {
      setPage((prev) => prev + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="challenges-page">
      <div className="container">
        {/* Page Header */}
        <div className="challenges-header">
          <div>
            <span className="section-kicker">Community Problem Discovery</span>
            <h1 className="challenges-title">Community Challenges</h1>
            <p className="challenges-subtitle">
              Explore ground-level societal problems submitted by citizens across
              communities. Each challenge represents a real opportunity for academic and
              industry innovation.
            </p>
          </div>

          <div>
            <Link href="/report" className="btn btn-primary">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Report a Problem
            </Link>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <Alert type="danger" title="Database Connection Issue">
            <p style={{ marginBottom: "var(--space-3)" }}>{error}</p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => fetchPage(page)}
            >
              Try Again
            </button>
          </Alert>
        )}

        {/* Loading State */}
        {loading && (
          <LoadingSpinner
            size="lg"
            message="Loading community challenges from PostgreSQL..."
          />
        )}

        {/* Empty State */}
        {!loading && !error && challenges.length === 0 && (
          <EmptyState
            title="No community challenges yet"
            description="Be the first to bring a real problem in your community to the Aikyra network. Your voice helps researchers and students know where to focus."
            actionText="Report a Community Problem"
            actionHref="/report"
          />
        )}

        {/* Challenges Grid */}
        {!loading && !error && challenges.length > 0 && (
          <>
            <div className="challenges-grid" role="region" aria-label="Challenges List">
              {challenges.map((challenge) => (
                <ChallengeCard key={challenge.id} challenge={challenge} />
              ))}
            </div>

            {/* Pagination Controls */}
            <nav
              className="pagination"
              role="navigation"
              aria-label="Challenges Pagination"
            >
              <div className="pagination-info">
                Showing page <strong>{page}</strong>
              </div>

              <div className="pagination-controls">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handlePrevPage}
                  disabled={page <= 1 || loading}
                  aria-label="Previous Page"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleNextPage}
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
