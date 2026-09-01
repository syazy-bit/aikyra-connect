import React from "react";
import { AdminSidebar } from "./AdminSidebar.jsx";
import { AdminHeader } from "./AdminHeader.jsx";

export function AdminLayout({ children }) {
  return (
    <div className="admin-app-root">
      <AdminHeader />
      <div className="admin-body">
        <AdminSidebar />
        <main className="admin-main-content" id="admin-main-content" role="main">
          {children}
        </main>
      </div>
    </div>
  );
}