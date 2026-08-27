import React, { useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert } from "../components/Alert.jsx";
import { LoadingSpinner } from "../components/LoadingSpinner.jsx";

const PASSWORD_MIN = 8;
const PASSWORD_MAX = 128;

export function Register() {
  const { navigate } = useRouter();
  const { register, error: authError } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Please enter your email address.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      nextErrors.email = "Please enter a valid email address.";
    }
    if (!password) nextErrors.password = "Please create a password.";
    else if (password.length < PASSWORD_MIN) {
      nextErrors.password = `Password must be at least ${PASSWORD_MIN} characters.`;
    } else if (password.length > PASSWORD_MAX) {
      nextErrors.password = `Password must not exceed ${PASSWORD_MAX} characters.`;
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    const result = await register(email.trim(), password, fullName.trim() || undefined);
    setSubmitting(false);

    if (result.success) {
      navigate("/login");
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
            <h1 className="auth-title">Create Your Account</h1>
            <p className="auth-subtitle">Join Aikyra to connect with community challenges</p>
          </div>

          {(authError || errors.general) && (
            <Alert type="danger" title="Registration Failed">
              <p>{authError || errors.general}</p>
            </Alert>
          )}

          <form onSubmit={handleSubmit} noValidate className="auth-form">
            <div className="form-group">
              <label htmlFor="reg-email" className="form-label">
                Email <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="reg-email"
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
              <label htmlFor="reg-fullname" className="form-label">Full Name (optional)</label>
              <input
                id="reg-fullname"
                name="full_name"
                type="text"
                className="form-control"
                placeholder="Your name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={submitting}
                maxLength={250}
                autoComplete="name"
              />
            </div>

            <div className="form-group">
              <label htmlFor="reg-password" className="form-label">
                Password <span className="form-label-required" aria-hidden="true">*</span>
              </label>
              <input
                id="reg-password"
                name="password"
                type="password"
                className={`form-control ${errors.password ? "has-error" : ""}`}
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
                required
                autoComplete="new-password"
                minLength={PASSWORD_MIN}
                maxLength={PASSWORD_MAX}
              />
              {errors.password && <div className="form-error-msg" role="alert">⚠️ {errors.password}</div>}
              <p className="form-helper" style={{ marginTop: "var(--space-1)" }}>
                Minimum {PASSWORD_MIN} characters, maximum {PASSWORD_MAX} characters.
              </p>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" message="" center={false} />
                  <span>Creating account...</span>
                </>
              ) : (
                <span>Create Account</span>
              )}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Already have an account? <Link href="/login" className="auth-link">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}