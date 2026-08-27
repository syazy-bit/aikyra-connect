import React from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function UserMenu() {
  const { navigate } = useRouter();
  const { user, logout, isAuthenticated } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const displayName = user?.full_name || user?.email || "User";

  if (!isAuthenticated) {
    return (
      <div className="nav-actions">
        <Link href="/login" className="btn btn-outline">
          Login
        </Link>
        <Link href="/register" className="btn btn-primary">
          Register
        </Link>
      </div>
    );
  }

  return (
    <div className="nav-actions nav-user-menu">
      <div className="user-menu-trigger" role="button" tabIndex={0} aria-expanded="false" aria-haspopup="true">
        <span className="user-avatar" aria-hidden="true">
          {displayName.charAt(0).toUpperCase()}
        </span>
        <span className="user-name">{displayName}</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="18 15 12 9 6 15" />
        </svg>
      </div>
      <div className="user-dropdown" role="menu">
        <div className="user-dropdown-header">
          <span className="user-dropdown-name">{displayName}</span>
          {user?.email && <span className="user-dropdown-email">{user.email}</span>}
        </div>
        <button
          type="button"
          className="user-dropdown-item btn btn-secondary btn-block"
          role="menuitem"
          onClick={handleLogout}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ marginRight: "var(--space-2)" }}>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Logout
        </button>
      </div>
    </div>
  );
}