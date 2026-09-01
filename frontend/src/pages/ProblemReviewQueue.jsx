import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { listAdminChallenges } from "../services/adminService.js";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "submitted", label: "Submitted" },
  { value: "under_review", label: "Under Review" },
  { value: "validated", label: "Validated" },
  { value: "rejected", label: "Rejected" },
];

const DNA_STATUS_OPTIONS = [
  { value: "", label: "All DNA Statuses" },
  { value: "needs_review", label: "Needs Review" },
  { value: "pending_validation", label: "Pending Validation" },
  { value: "validated", label: "Validated" },
];

const PAGE_SIZE = 20;

function parseQuery(query) {
  const list = (value) =>
    (value ?? "").split(",").map((v) => v.trim()).filter(Boolean);
  return {
    status: query.status ?? "",
    dna_validation_status: query.dna_validation_status ?? "",
    skip: Math.max(0, parseInt(query.skip ?? "0", 10) || 0),
    limit: Math.max(1, parseInt(query.limit ?? String(PAGE_SIZE), 10) || PAGE_SIZE),
  };
}

export function ProblemReviewQueue() {
  const { route, navigate } = useRouter();
  const { canReviewProblems } = useAuth();
  const selected = useMemo(() => parseQuery(route.query), [route.query]);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadChallenges() {
      try {
        setLoading(true);
        setError(null);
        const result = await listAdminChallenges({
          status: selected.status || undefined,
          dna_validation_status: selected.dna_validation_status || undefined,
          skip: selected.skip,
          limit: selected.limit,
        });
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load problems.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadChallenges();

    return () => {
      mounted = false;
    };
  }, [selected.status, selected.dna_validation_status, selected.skip, selected.limit]);

  const updateQuery = useCallback(
    (patch) => {
      const next = { ...route.query, ...patch };
      next.skip = "0"; // Reset to first page on filter change
      Object.keys(next).forEach((key) => {
        if (next[key] === "" || next[key] === undefined || next[key] === null) delete next[key];
      });
      const params = new URLSearchParams(next).toString();
      navigate(`/admin/problems${params ? `?${params}` : ""}`);
    },
    [navigate, route.query]
  );

  const items = data ?? [];
  const hasNextPage = items.length === selected.limit;

  const formatDate = (dateString) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getStatusClass = (status) => {
    switch (status) {
      case "submitted": return "status-submitted";
      case "under_review": return "status-under_review";
      case "validated": return "status-validated";
      case "rejected": return "status-rejected";
      default: return "";
    }
  };

  const getDnaStatusClass = (status) => {
    switch (status) {
      case "needs_review": return "dna-needs_review";
      case "pending_validation": return "dna-pending_validation";
      case "validated": return "dna-validated";
      default: return "";
    }
  };

  if (!canReviewProblems) {
    return (
      <div className="admin-page">
        <Alert type="warning" title="Access Denied">
          <p>You do not have the required platform capability to access Problem Review.</p>
        </Alert>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Problem Review</h1>
        <p className="admin-page-subtitle">Review and validate community-submitted problems and their automated analysis.</p>
      </div>

      <div className="admin-filters card">
        <div className="filter-row">
          <select
            value={selected.status}
            onChange={(e) => updateQuery({ status: e.target.value })}
            className="form-control"
            aria-label="Filter by challenge status"
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            value={selected.dna_validation_status}
            onChange={(e) => updateQuery({ dna_validation_status: e.target.value })}
            className="form-control"
            aria-label="Filter by DNA validation status"
          >
            {DNA_STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {(selected.status || selected.dna_validation_status) && (
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => updateQuery({ status: "", dna_validation_status: "" })}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {error && (
        <Alert type="danger" title="Could Not Load Problems">
          <p>{error}</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>
            Retry
          </button>
        </Alert>
      )}

      {loading && (
        <div className="admin-loading-container">
          <LoadingSpinner size="lg" message="Loading problems..." />
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <EmptyState
          title={selected.status || selected.dna_validation_status ? "No problems match your filters" : "No problems awaiting review"}
          description={
            selected.status || selected.dna_validation_status
              ? "Try adjusting your filters."
              : "All problems have been reviewed."
          }
          actionText={selected.status || selected.dna_validation_status ? "Clear filters" : undefined}
          onActionClick={selected.status || selected.dna_validation_status ? () => updateQuery({ status: "", dna_validation_status: "" }) : undefined}
        />
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <div className="admin-table-wrapper card">
            <table className="admin-table" role="table">
              <thead>
                <tr>
                  <th>Problem</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>DNA Status</th>
                  <th>Domain</th>
                  <th>Urgency</th>
                  <th>Submitted</th>
                  <th style={{ width: "80px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((challenge) => (
                  <tr key={challenge.id}>
                    <td>
                      <Link href={`/admin/problems/${challenge.id}`} className="admin-problem-link">
                        {challenge.title}
                      </Link>
                    </td>
                    <td>{challenge.location}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(challenge.status)}`}>
                        {challenge.status.replace("_", " ")}
                      </span>
                    </td>
                    <td>
                      {challenge.dna ? (
                        <span className={`dna-status-badge ${getDnaStatusClass(challenge.dna.validation_status)}`}>
                          {challenge.dna.validation_status.replace("_", " ")}
                        </span>
                      ) : (
                        <span className="text-muted">Not analyzed</span>
                      )}
                    </td>
                    <td>{challenge.dna?.primary_domain ?? "—"}</td>
                    <td>{challenge.dna?.urgency ?? "—"}</td>
                    <td>{formatDate(challenge.created_at)}</td>
                    <td>
                      <Link
                        href={`/admin/problems/${challenge.id}`}
                        className="btn btn-secondary btn-sm"
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <nav className="admin-pagination" role="navigation" aria-label="Problems pagination">
            <div className="pagination-info">
              Page {Math.floor(selected.skip / selected.limit) + 1}
            </div>
            <div className="pagination-controls">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => updateQuery({ skip: String(Math.max(0, selected.skip - selected.limit)) })}
                disabled={selected.skip === 0 || loading}
                aria-label="Previous Page"
              >
                ← Previous
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => updateQuery({ skip: String(selected.skip + selected.limit) })}
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
  );
}