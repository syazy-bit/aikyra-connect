import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { listAdminInstitutions } from "../services/adminService.js";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";
import { EmptyState } from "../components/EmptyState.jsx";
import { VerificationBadge } from "../components/VerificationBadge.jsx";
import { INSTITUTION_TYPE_LABELS } from "../components/InstitutionCard.jsx";

const VERIFICATION_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "unverified", label: "Unverified" },
  { value: "pending_review", label: "Pending Review" },
  { value: "verified", label: "Verified" },
  { value: "rejected", label: "Rejected" },
  { value: "suspended", label: "Suspended" },
];

const TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "university", label: "University" },
  { value: "college", label: "College" },
  { value: "research_institute", label: "Research Institute" },
  { value: "innovation_hub", label: "Innovation Hub" },
];

const PAGE_SIZE = 20;

function parseQuery(query) {
  return {
    verification_status: query.verification_status ?? "",
    institution_type: query.institution_type ?? "",
    skip: Math.max(0, parseInt(query.skip ?? "0", 10) || 0),
    limit: Math.max(1, parseInt(query.limit ?? String(PAGE_SIZE), 10) || PAGE_SIZE),
  };
}

export function InstitutionReviewQueue() {
  const { route, navigate } = useRouter();
  const { canReviewInstitutions } = useAuth();
  const selected = useMemo(() => parseQuery(route.query), [route.query]);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadInstitutions() {
      try {
        setLoading(true);
        setError(null);
        const result = await listAdminInstitutions({
          verification_status: selected.verification_status || undefined,
          institution_type: selected.institution_type || undefined,
          skip: selected.skip,
          limit: selected.limit,
        });
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load institutions.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadInstitutions();

    return () => {
      mounted = false;
    };
  }, [selected.verification_status, selected.institution_type, selected.skip, selected.limit]);

  const updateQuery = useCallback(
    (patch) => {
      const next = { ...route.query, ...patch };
      next.skip = "0";
      Object.keys(next).forEach((key) => {
        if (next[key] === "" || next[key] === undefined || next[key] === null) delete next[key];
      });
      const params = new URLSearchParams(next).toString();
      navigate(`/admin/institutions${params ? `?${params}` : ""}`);
    },
    [navigate, route.query]
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasNextPage = selected.skip + items.length < total;

  const formatDate = (dateString) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  if (!canReviewInstitutions) {
    return (
      <div className="admin-page">
        <Alert type="warning" title="Access Denied">
          <p>You do not have the required platform capability to access Institution Review.</p>
        </Alert>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Institution Review</h1>
        <p className="admin-page-subtitle">Review and manage institution verification status across the platform.</p>
      </div>

      <div className="admin-filters card">
        <div className="filter-row">
          <select
            value={selected.verification_status}
            onChange={(e) => updateQuery({ verification_status: e.target.value })}
            className="form-control"
            aria-label="Filter by verification status"
          >
            {VERIFICATION_STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            value={selected.institution_type}
            onChange={(e) => updateQuery({ institution_type: e.target.value })}
            className="form-control"
            aria-label="Filter by institution type"
          >
            {TYPE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {(selected.verification_status || selected.institution_type) && (
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => updateQuery({ verification_status: "", institution_type: "" })}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {error && (
        <Alert type="danger" title="Could Not Load Institutions">
          <p>{error}</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>
            Retry
          </button>
        </Alert>
      )}

      {loading && (
        <div className="admin-loading-container">
          <LoadingSpinner size="lg" message="Loading institutions..." />
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <EmptyState
          title={selected.verification_status || selected.institution_type ? "No institutions match your filters" : "No institutions found"}
          description={
            selected.verification_status || selected.institution_type
              ? "Try adjusting your filters."
              : "No institutions have been registered yet."
          }
          actionText={selected.verification_status || selected.institution_type ? "Clear filters" : undefined}
          onActionClick={selected.verification_status || selected.institution_type ? () => updateQuery({ verification_status: "", institution_type: "" }) : undefined}
        />
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <div className="admin-table-wrapper card">
            <table className="admin-table" role="table">
              <thead>
                <tr>
                  <th>Institution</th>
                  <th>Type</th>
                  <th>Location</th>
                  <th>Verification Status</th>
                  <th>Verified</th>
                  <th>Registered</th>
                  <th style={{ width: "140px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((institution) => (
                  <tr key={institution.id}>
                    <td>
                      <Link href={`/admin/institutions/${institution.id}`} className="admin-institution-link font-medium">
                        {institution.name}
                      </Link>
                    </td>
                    <td>
                      <span className="type-chip">
                        {INSTITUTION_TYPE_LABELS[institution.institution_type] ?? institution.institution_type}
                      </span>
                    </td>
                    <td>{institution.location}</td>
                    <td>
                      <VerificationBadge status={institution.verification_status} />
                    </td>
                    <td>{formatDate(institution.verified_at)}</td>
                    <td>{formatDate(institution.created_at)}</td>
                    <td>
                      <Link
                        href={`/admin/institutions/${institution.id}`}
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

          <nav className="admin-pagination" role="navigation" aria-label="Institutions pagination">
            <div className="pagination-info">
              Page {Math.floor(selected.skip / selected.limit) + 1} of {Math.ceil(total / selected.limit)} · {total} total
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