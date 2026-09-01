import React from "react";
import { Link, useRouter } from "../context/RouterContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

function OverviewIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

function ProblemIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function InstitutionIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 21h18" />
      <path d="M3 10h18" />
      <path d="M5 6l7-3 7 3" />
      <path d="M4 10v11" />
      <path d="M20 10v11" />
      <path d="M8 14v4" />
      <path d="M12 14v4" />
      <path d="M16 14v4" />
    </svg>
  );
}

export function AdminSidebar() {
  const { currentPath } = useRouter();
  const { canReviewProblems, canReviewInstitutions } = useAuth();

  const navItems = [
    {
      path: "/admin",
      label: "Overview",
      icon: <OverviewIcon />,
      requires: "any",
      isActive: currentPath === "/admin",
    },
    {
      path: "/admin/problems",
      label: "Problem Review",
      icon: <ProblemIcon />,
      requires: "can_review_problems",
      isActive: currentPath === "/admin/problems" || currentPath.startsWith("/admin/problems/"),
    },
    {
      path: "/admin/institutions",
      label: "Institution Review",
      icon: <InstitutionIcon />,
      requires: "can_review_institutions",
      isActive: currentPath === "/admin/institutions" || currentPath.startsWith("/admin/institutions/"),
    },
  ];

  const filteredItems = navItems.filter((item) => {
    if (item.requires === "any") return canReviewProblems || canReviewInstitutions;
    if (item.requires === "can_review_problems") return canReviewProblems;
    if (item.requires === "can_review_institutions") return canReviewInstitutions;
    return false;
  });

  return (
    <aside className="admin-sidebar" role="navigation" aria-label="Admin Navigation">
      <div className="admin-sidebar-section-title">Operations</div>
      <nav className="admin-nav">
        <ul className="admin-nav-list">
          {filteredItems.map((item) => (
            <li key={item.path} className="admin-nav-item">
              <Link
                href={item.path}
                className={`admin-nav-link ${item.isActive ? "active" : ""}`}
                aria-current={item.isActive ? "page" : undefined}
              >
                <span className="admin-nav-icon">{item.icon}</span>
                <span className="admin-nav-label">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}