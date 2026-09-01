import React, { useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { LoadingSpinner } from "./LoadingSpinner.jsx";
import { useRouter } from "../context/RouterContext.jsx";

export function AdminProtectedRoute({ children, requiredCapability }) {
  const { isAuthenticated, loading, canReviewProblems, canReviewInstitutions, logout } = useAuth();
  const { navigate, currentPath } = useRouter();

  const hasCapability = () => {
    if (!requiredCapability || requiredCapability === "any") {
      return canReviewProblems || canReviewInstitutions;
    }
    if (requiredCapability === "can_review_problems") return canReviewProblems;
    if (requiredCapability === "can_review_institutions") return canReviewInstitutions;
    return false;
  };

  useEffect(() => {
    if (
      !loading &&
      !isAuthenticated
    ) {
      navigate(`/admin/login?next=${encodeURIComponent(currentPath)}`);
    }
  }, [loading, isAuthenticated, navigate, currentPath]);

  if (loading) {
    return (
      <div className="admin-loading-container">
        <LoadingSpinner size="lg" message="Restoring admin session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!hasCapability()) {
    return (
      <div className="admin-access-denied-container">
        <div className="admin-access-denied-card card">
          <div className="admin-access-denied-icon" aria-hidden="true">🔒</div>
          <h2 className="admin-access-denied-title">Admin Access Required</h2>
          <p className="admin-access-denied-desc">
            Your account does not have the required platform capability to access this administration section.
          </p>
          <div className="admin-access-denied-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                logout();
                navigate("/admin/login");
              }}
            >
              Sign in to Admin Portal
            </button>
          </div>
        </div>
      </div>
    );
  }

  return children;
}