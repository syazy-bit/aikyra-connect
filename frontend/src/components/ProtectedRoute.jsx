import React, { useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { LoadingSpinner } from "./LoadingSpinner.jsx";
import { useRouter } from "../context/RouterContext.jsx";

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const { navigate } = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate("/login");
    }
  }, [loading, isAuthenticated, navigate]);

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