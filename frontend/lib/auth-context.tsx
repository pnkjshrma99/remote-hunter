"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";

// Types
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
}

export interface VerificationData {
  email: string;
  code: string;
}

export interface OAuthCredentials {
  access_token: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthTokens>;
  register: (data: RegisterData) => Promise<User>;
  logout: () => Promise<void>;
  verifyEmail: (data: VerificationData) => Promise<void>;
  refreshToken: (refreshToken: string) => Promise<AuthTokens>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
  error: string | null;
  loginWithGoogle: (accessToken: string) => Promise<AuthTokens>;
  loginWithGitHub: (accessToken: string) => Promise<AuthTokens>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tokenRefreshTimer, setTokenRefreshTimer] = useState<NodeJS.Timeout | null>(null);

  // Get stored tokens
  const getTokens = useCallback((): { accessToken: string | null; refreshToken: string | null } => {
    if (typeof window === "undefined") return { accessToken: null, refreshToken: null };
    return {
      accessToken: localStorage.getItem("access_token"),
      refreshToken: localStorage.getItem("refresh_token"),
    };
  }, []);

  // Store tokens
  const storeTokens = useCallback((tokens: AuthTokens) => {
    if (typeof window === "undefined") return;
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
  }, []);

  // Clear tokens
  const clearTokens = useCallback(() => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }, []);

  // Get auth headers
  const getAuthHeaders = useCallback(() => {
    const { accessToken } = getTokens();
    return {
      "Content-Type": "application/json",
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    };
  }, [getTokens]);

  // Setup proactive token refresh
  const setupTokenRefresh = useCallback((tokens: AuthTokens) => {
    if (tokenRefreshTimer) {
      clearTimeout(tokenRefreshTimer);
    }
    
    // Refresh 5 minutes before expiration
    const refreshInMs = (tokens.expires_in - 300) * 1000;
    if (refreshInMs > 0) {
      const timer = setTimeout(async () => {
        const { refreshToken: rt } = getTokens();
        if (rt) {
          try {
            await refreshToken(rt);
          } catch (err) {
            console.error("Proactive token refresh failed:", err);
          }
        }
      }, refreshInMs);
      setTokenRefreshTimer(timer);
    }
  }, [getTokens, tokenRefreshTimer]);

  // Check authentication status
  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    const { accessToken } = getTokens();
    if (!accessToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token might be expired, try refresh
        const { refreshToken } = getTokens();
        if (refreshToken) {
          try {
            const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (refreshResponse.ok) {
              const newTokens = await refreshResponse.json();
              storeTokens(newTokens);
              setupTokenRefresh(newTokens);
              // Retry getting user
              const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
                headers: getAuthHeaders(),
              });
              if (userResponse.ok) {
                const userData = await userResponse.json();
                setUser(userData);
              } else {
                clearTokens();
                setUser(null);
              }
            } else {
              clearTokens();
              setUser(null);
            }
          } catch {
            clearTokens();
            setUser(null);
          }
        } else {
          clearTokens();
          setUser(null);
        }
      }
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [getTokens, getAuthHeaders, storeTokens, clearTokens, setupTokenRefresh]);

  // Login
  const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Login failed");
      }

      const tokens = await response.json();
      storeTokens(tokens);
      setupTokenRefresh(tokens);

      // Get user data
      const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
      }

      return tokens;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      throw err;
    }
  };

  // Register
  const register = async (data: RegisterData): Promise<User> => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Registration failed");
      }

      const userData = await response.json();
      return userData;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      throw err;
    }
  };

  // Logout
  const logout = async () => {
    try {
      const { accessToken } = getTokens();
      if (accessToken) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
        });
      }
    } catch {
      // Ignore errors
    } finally {
      if (tokenRefreshTimer) {
        clearTimeout(tokenRefreshTimer);
        setTokenRefreshTimer(null);
      }
      clearTokens();
      setUser(null);
    }
  };

  // Verify email
  const verifyEmail = async (data: VerificationData): Promise<void> => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Verification failed");
      }

      // Update user verification status
      if (user) {
        setUser({ ...user, is_verified: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
      throw err;
    }
  };

  // Refresh token
  const refreshToken = async (refreshTokenStr: string): Promise<AuthTokens> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshTokenStr }),
      });

      if (!response.ok) {
        throw new Error("Token refresh failed");
      }

      const tokens = await response.json();
      storeTokens(tokens);
      return tokens;
    } catch (err) {
      clearTokens();
      setUser(null);
      throw err;
    }
  };

  // Login with Google
  const loginWithGoogle = async (accessToken: string): Promise<AuthTokens> => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: accessToken }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Google OAuth login failed");
      }

      const tokens = await response.json();
      storeTokens(tokens);
      setupTokenRefresh(tokens);

      // Get user data
      const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
      }

      return tokens;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google OAuth login failed");
      throw err;
    }
  };

  // Login with GitHub
  const loginWithGitHub = async (code: string): Promise<AuthTokens> => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "GitHub OAuth login failed");
      }

      const tokens = await response.json();
      storeTokens(tokens);
      setupTokenRefresh(tokens);

      // Get user data
      const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
      }

      return tokens;
    } catch (err) {
      setError(err instanceof Error ? err.message : "GitHub OAuth login failed");
      throw err;
    }
  };

  // Clear error
  const clearError = useCallback(() => setError(null), []);

  // Initial auth check
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        verifyEmail,
        refreshToken,
        checkAuth,
        clearError,
        error,
        loginWithGoogle,
        loginWithGitHub,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}