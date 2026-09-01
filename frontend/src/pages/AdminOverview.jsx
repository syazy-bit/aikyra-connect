import React, { useEffect, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getAdminOverview } from "../services/adminService.js";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";
import { Alert } from "../components/Alert.jsx";

function QueueIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function DnaIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 15c6.667-6 13.333 0 20-6" />
      <path d="M9 22c1.798-1.998 2.518-3.995 2.807-5.993" />
      <path d="M15 2c-1.798 1.998-2.518 3.995-2.807 5.993" />
      <path d="M17 6l-2.5-2.5" />
      <path d="M14 8l-1-1" />
      <path d="M7 18l2.5 2.5" />
      <path d="M3.5 14.5l.5.5" />
      <path d="M20 9.5l.5.5" />
    </svg>
  );
}

function ClockBuildingIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 21h18" />
      <path d="M5 21V7l8-4v18" />
      <path d="M19 21V11l-6-4" />
      <circle cx="18" cy="6" r="3" />
      <polyline points="18 5 18 6 19 6" />
    </svg>
  );
}

function VerifiedBuildingIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

function StatCard({ label, value, href, icon, colorScheme = "default", hasCapability }) {
  if (!hasCapability) return null;
  return (
    <Link href={href} className={`admin-stat-card admin-stat-card-${colorScheme}`}>
      <div className="admin-stat-header">
        <div className="admin-stat-icon-wrapper">{icon}</div>
        <span className="admin-stat-arrow" aria-hidden="true">→</span>
      </div>
      <div className="admin-stat-body">
        <div className="admin-stat-value">{value}</div>
        <div className="admin-stat-label">{label}</div>
      </div>
    </Link>
  );
}

export function AdminOverview() {
  const { navigate } = useRouter();
  const { canReviewProblems, canReviewInstitutions, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadOverview() {
      try {
        setLoading(true);
        setError(null);
        const result = await getAdminOverview();
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Failed to load admin overview.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadOverview();

    return () => {
      mounted = false;
    };
  }, []);

  if (authLoading || loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading-container">
          <LoadingSpinner size="lg" message="Loading platform overview metrics..." />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <Alert type="danger" title="Could Not Load Overview">
          <p>{error}</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>
            Retry
          </button>
        </Alert>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Admin Overview</h1>
          <p className="admin-page-subtitle">Platform-wide summary of operational review queues and verification pipelines.</p>
        </div>
      </div>

      <div className="admin-stat-grid">
        <StatCard
          label="Problems Awaiting Review"
          value={data?.problems_awaiting_review ?? 0}
          href="/admin/problems"
          icon={<QueueIcon />}
          colorScheme="amber"
          hasCapability={canReviewProblems}
        />
        <StatCard
          label="DNA Needing Validation"
          value={data?.dna_needing_validation ?? 0}
          href="/admin/problems"
          icon={<DnaIcon />}
          colorScheme="teal"
          hasCapability={canReviewProblems}
        />
        <StatCard
          label="Institutions Pending Verification"
          value={data?.institutions_pending_verification ?? 0}
          href="/admin/institutions"
          icon={<ClockBuildingIcon />}
          colorScheme="amber"
          hasCapability={canReviewInstitutions}
        />
        <StatCard
          label="Verified Institutions"
          value={data?.verified_institutions ?? 0}
          href="/admin/institutions"
          icon={<VerifiedBuildingIcon />}
          colorScheme="green"
          hasCapability={canReviewInstitutions}
        />
      </div>

      <div className="admin-section card">
        <h2 className="admin-section-title">Review Actions</h2>
        <p className="admin-section-desc">Quickly jump into active administrative workflows based on your platform capabilities.</p>
        <div className="admin-quick-actions">
          {canReviewProblems && (
            <Link href="/admin/problems" className="btn btn-primary">
              <span style={{ marginRight: "6px" }}>🔍</span> Review Problem Queue
            </Link>
          )}
          {canReviewInstitutions && (
            <Link href="/admin/institutions" className="btn btn-secondary">
              <span style={{ marginRight: "6px" }}>🏛️</span> Review Institution Queue
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}