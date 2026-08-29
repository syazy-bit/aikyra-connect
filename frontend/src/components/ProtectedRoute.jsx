import React, { useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { LoadingSpinner } from "./LoadingSpinner.jsx";
import { useRouter } from "../context/RouterContext.jsx";

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const { navigate, currentPath } = useRouter();

  useEffect(() => {
    // Preserve the requested internal path so the user can return to it
    // after signing in (/login?next=/workspace).
    if (
      !loading &&
      !isAuthenticated &&
      currentPath !== "/login" &&
      currentPath !== "/register"
    ) {
      navigate(`/login?next=${encodeURIComponent(currentPath)}`);
    }
  }, [loading, isAuthenticated, navigate, currentPath]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-12) 0" }}>
        <LoadingSpinner size="lg" message="Restoring session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return children;
}