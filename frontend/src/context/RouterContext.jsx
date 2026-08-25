import React, { createContext, useContext, useState, useEffect } from "react";

const RouterContext = createContext(null);

/**
 * Lightweight SPA Client Router using native pushState and popstate.
 * Supports path parsing for /, /report, /challenges, and /challenges/:id.
 */
export function RouterProvider({ children }) {
  const [currentPath, setCurrentPath] = useState(
    window.location.pathname || "/"
  );

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || "/");
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (to) => {
    if (to === currentPath) return;
    window.history.pushState({}, "", to);
    setCurrentPath(to);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Route matcher helper
  const getRoute = () => {
    const path = currentPath.replace(/\/+$/, "") || "/";

    if (path === "/") {
      return { name: "home", params: {} };
    }
    if (path === "/report") {
      return { name: "report", params: {} };
    }
    if (path === "/challenges") {
      return { name: "challenges", params: {} };
    }

    const challengeDetailMatch = path.match(/^\/challenges\/([^/]+)$/);
    if (challengeDetailMatch) {
      return {
        name: "challenge-detail",
        params: { id: challengeDetailMatch[1] },
      };
    }

    return { name: "not-found", params: {} };
  };

  const route = getRoute();

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

/**
 * Accessible Link component for SPA navigation.
 */
export function Link({ href, children, className = "", ...props }) {
  const { navigate, currentPath } = useRouter();
  const isActive = currentPath === href;

  const handleClick = (e) => {
    // Let browser handle special key combinations (e.g. cmd/ctrl click for new tab)
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
      return;
    }
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
