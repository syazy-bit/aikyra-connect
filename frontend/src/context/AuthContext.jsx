import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiRequest, setUnauthenticatedHandler } from "../services/api.js";

const AuthContext = createContext(null);

const TOKEN_KEY = "aikyra_token";

export const SESSION_EXPIRED_MESSAGE = "Your session has expired. Please sign in again.";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearAuth = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setError(null);
  }, []);

  const setAuth = useCallback((token, userData) => {
    sessionStorage.setItem(TOKEN_KEY, token);
    setUser(userData);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const token = data.access_token;
      sessionStorage.setItem(TOKEN_KEY, token);
      const me = await apiRequest("/api/auth/me");
      setAuth(token, me);
      return { success: true };
    } catch (err) {
      const message = err.message || "Login failed. Please check your credentials.";
      setError(message);
      return { success: false, error: message, status: err.status ?? null };
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
      sessionStorage.setItem(TOKEN_KEY, token);
      const me = await apiRequest("/api/auth/me");
      setAuth(token, me);
      return { success: true };
    } catch (err) {
      const message = err.message || "Registration failed. Please try again.";
      setError(message);
      return { success: false, error: message, status: err.status ?? null };
    }
  }, [setAuth]);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  const restoreSession = useCallback(async () => {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const me = await apiRequest("/api/auth/me");
      setUser(me);
    } catch (err) {
      if (err.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setUnauthenticatedHandler(() => {
      setUser(null);
      setError(SESSION_EXPIRED_MESSAGE);
    });
    restoreSession();
  }, [restoreSession]);

  const value = {
    user,
    loading,
    error,
    clearError,
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