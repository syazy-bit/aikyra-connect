import React, { createContext, useCallback, useContext, useState, useEffect } from "react";

const RouterContext = createContext(null);

function readLocation() {
  return {
    path: window.location.pathname || "/",
    search: window.location.search || "",
  };
}

/**
 * Lightweight SPA client router using native pushState and popstate.
 * Routes are matched on the pathname; query strings are exposed as a plain
 * object so view state (search, filters, sort, page) survives refresh,
 * deep links and back/forward navigation.
 */
export function RouterProvider({ children }) {
  const [location, setLocation] = useState(readLocation);

  useEffect(() => {
    const handlePopState = () => setLocation(readLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((to) => {
    const target = to.startsWith("/") ? to : `/${to}`;
    if (target === `${window.location.pathname}${window.location.search}`) return;
    window.history.pushState({}, "", target);
    setLocation(readLocation());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const getRoute = () => {
    const path = location.path.replace(/\/+$/, "") || "/";
    const params = Object.fromEntries(new URLSearchParams(location.search));

    if (path === "/") return { name: "home", params: {}, query: {} };
    if (path === "/login") return { name: "login", params: {}, query: params };
    if (path === "/register") return { name: "register", params: {}, query: params };
    if (path === "/report") return { name: "report", params: {}, query: {} };
    if (path === "/challenges") return { name: "challenges", params: {}, query: params };
    if (path === "/workspace") return { name: "workspace", params: {}, query: {} };

    const challengeDetailMatch = path.match(/^\/challenges\/([^/]+)$/);
    if (challengeDetailMatch) {
      return {
        name: "challenge-detail",
        params: { id: challengeDetailMatch[1] },
        query: params,
      };
    }

    const teamDetailMatch = path.match(/^\/teams\/([^/]+)$/);
    if (teamDetailMatch) {
      return {
        name: "team-detail",
        params: { id: teamDetailMatch[1] },
        query: {},
      };
    }

    const proposalDetailMatch = path.match(/^\/proposals\/([^/]+)$/);
    if (proposalDetailMatch) {
      return {
        name: "proposal-detail",
        params: { id: proposalDetailMatch[1] },
        query: {},
      };
    }

    if (path === "/institutions") return { name: "institutions", params: {}, query: params };
    if (path === "/institutions/register") return { name: "institution-register", params: {}, query: {} };

    const institutionDetailMatch = path.match(/^\/institutions\/([^/]+)$/);
    if (institutionDetailMatch) {
      return {
        name: "institution-detail",
        params: { id: institutionDetailMatch[1] },
        query: params,
      };
    }

    return { name: "not-found", params: {}, query: {} };
  };

  const route = getRoute();
  const currentPath = location.path;

  return (
    <RouterContext.Provider value={{ currentPath, navigate, route }}>
      {children}
    </RouterContext.Provider>
  );
}

export function useRouter() {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useRouter must be used within a RouterProvider");
  }
  return context;
}

/** Accessible Link component for SPA navigation. */
export function Link({ href, children, className = "", ...props }) {
  const { navigate, currentPath } = useRouter();
  const isActive = currentPath === href.split("?")[0];

  const handleClick = (e) => {
    // Let the browser handle modifier-clicks (open in new tab etc.)
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(href);
  };

  return (
    <a
      href={href}
      onClick={handleClick}
      className={`${className} ${isActive ? "active" : ""}`}
      aria-current={isActive ? "page" : undefined}
      {...props}
    >
      {children}
    </a>
  );
}