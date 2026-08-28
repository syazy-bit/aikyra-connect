import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export function UserMenu() {
  const { navigate, currentPath } = useRouter();
  const { user, logout, isAuthenticated } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  const handleLogout = () => {
    closeMenu();
    logout();
    navigate("/");
  };

  // Close when navigation occurs (e.g. clicking the Workspace entry).
  useEffect(() => {
    setMenuOpen(false);
  }, [currentPath]);

  // Close on Escape or outside pointer-down while the menu is open.
  useEffect(() => {
    if (!menuOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") closeMenu();
    };
    const handlePointerDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) closeMenu();
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [menuOpen, closeMenu]);

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
    <div className={`nav-actions nav-user-menu${menuOpen ? " is-open" : ""}`} ref={menuRef}>
      <div
        className="user-menu-trigger"
        role="button"
        tabIndex={0}
        aria-expanded={menuOpen}
        aria-haspopup="true"
        onClick={() => setMenuOpen((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setMenuOpen((prev) => !prev);
          }
        }}
      >
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
        <Link
          href="/workspace"
          className="user-dropdown-item btn btn-secondary btn-block"
          role="menuitem"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ marginRight: "var(--space-2)" }}>
            <rect x="2" y="7" width="20" height="14" rx="2" />
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
          </svg>
          Workspace
        </Link>
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