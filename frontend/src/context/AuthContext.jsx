import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiRequest, setUnauthenticatedHandler } from "../services/api.js";

const AuthContext = createContext(null);

const TOKEN_KEY = "aikyra_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setError(null);
  }, []);

  const setAuth = useCallback((token, userData) => {
    localStorage.setItem(TOKEN_KEY, token);
    setUser(userData);
    setError(null);
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const token = data.access_token;
      const me = await apiRequest("/api/auth/me");
      setAuth(token, me);
      return { success: true };
    } catch (err) {
      setError(err.message || "Login failed. Please check your credentials.");
      return { success: false, error: err.message };
    }
  }, [setAuth]);

  const register = useCallback(async (email, password, fullName) => {
    setError(null);
    try {
      await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const token = data.access_token;
      const me = await apiRequest("/api/auth/me");
      setAuth(token, me);
      return { success: true };
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
      return { success: false, error: err.message };
    }
  }, [setAuth]);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  const restoreSession = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const me = await apiRequest("/api/auth/me");
      setUser(me);
    } catch (err) {
      if (err.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setUnauthenticatedHandler(() => {
      setUser(null);
      setError("Your session has expired. Please sign in again.");
    });
    restoreSession();
  }, [restoreSession]);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}