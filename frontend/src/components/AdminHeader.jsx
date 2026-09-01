import React from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function AdminHeader() {
  const { user, logout } = useAuth();
  const { navigate } = useRouter();

  const displayName = user?.full_name || user?.email?.split("@")[0] || "Administrator";
  const email = user?.email || "";

  const handleLogout = () => {
    logout();
    navigate("/admin/login");
  };

  return (
    <header className="admin-header" role="banner">
      <div className="admin-header-inner">
        <div className="admin-header-left">
          <Link href="/admin" className="admin-brand" aria-label="Aikyra Admin Console">
            <span className="admin-brand-mark" aria-hidden="true">A</span>
            <span className="admin-brand-title">Aikyra Admin</span>
          </Link>
          <span className="admin-badge admin-badge-console">Platform Console</span>
        </div>
        
        <div className="admin-header-actions">
          <div className="admin-user-profile" title={email}>
            <div className="admin-user-avatar" aria-hidden="true">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="admin-user-meta">
              <span className="admin-user-name">{displayName}</span>
              <span className="admin-user-role">Administrator</span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-outline btn-sm admin-logout-btn"
            onClick={handleLogout}
            aria-label="Sign out of Admin Console"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ marginRight: "6px" }}>
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}