import React, { useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

export function Login() {
  const { navigate } = useRouter();
  const { login, error: authError } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Please enter your email address.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!password) nextErrors.password = "Please enter your password.";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    const result = await login(email.trim(), password);
    setSubmitting(false);

    if (result.success) {
      navigate("/");
    }
  };

  return (
    <div className="auth-page">
      <div className="container-narrow">
        <div className="auth-card card">
          <div className="auth-header">
            <Link href="/" className="back-link" style={{ marginBottom: "var(--space-6)" }}>
              ← Back to Home
            </Link>
            <h1 className="auth-title">Welcome Back</h1>
            <p className="auth-subtitle">Sign in to your Aikyra account</p>
          </div>

          {(authError || errors.general) && (
            <Alert type="danger" title="Sign In Failed">
              <p>{authError || errors.general}</p>
            </Alert>
          )}

          <form onSubmit={handleSubmit} noValidate className="auth-form">
            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                Email <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="login-email"
                name="email"
                type="email"
                className={`form-control ${errors.email ? "has-error" : ""}`}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
                required
                autoComplete="email"
                autoFocus
              />
              {errors.email && <div className="form-error-msg" role="alert">⚠️ {errors.email}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="login-password" className="form-label">
                Password <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="login-password"
                name="password"
                type="password"
                className={`form-control ${errors.password ? "has-error" : ""}`}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
                required
                autoComplete="current-password"
              />
              {errors.password && <div className="form-error-msg" role="alert">⚠️ {errors.password}</div>}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Don't have an account? <Link href="/register" className="auth-link">Create one</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}