
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole } from '../types';

// API Configuration
// API Configuration - Use VITE_API_BASE for consistency across all components
const API_BASE_URL = import.meta.env.VITE_API_BASE || '';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  user: {
    id: string | number;
    email: string;
    name?: string;
    full_name?: string;
    role: string;
    company?: string;
    company_id?: number;
    company_name?: string;
    is_active?: boolean;
  };
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, fullName: string, companyId: number, role?: UserRole) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function safeReadJson(response: Response): Promise<any | null> {
  // 204/205 have no body by definition
  if (response.status === 204 || response.status === 205) return null;

  const contentType = response.headers.get('content-type') || '';
  const text = await response.text();
  if (!text) return null;

  // Prefer JSON only when it looks like JSON (avoids HTML parsing issues)
  const looksJson = contentType.includes('application/json') || text.trim().startsWith('{') || text.trim().startsWith('[');
  if (!looksJson) return { _nonJson: true, text, contentType };

  try {
    return JSON.parse(text);
  } catch {
    return { _invalidJson: true, text, contentType };
  }
}

function formatHttpError(response: Response, body: any | null, fallback: string): string {
  const base = `${fallback} (HTTP ${response.status})`;
  if (!body) return base;
  if (typeof body === 'object') {
    const detail = (body as any).detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if ((body as any)._nonJson) return `${base}: Non-JSON response from server. Check API URL/proxy and backend status.`;
    if ((body as any)._invalidJson) return `${base}: Invalid JSON response from server. Check backend logs.`;
  }
  return base;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    error: null,
  });

  // Load saved authentication on mount
  useEffect(() => {
    const loadSavedAuth = async () => {
      try {
        const savedToken = localStorage.getItem('auth_token');
        const savedUser = localStorage.getItem('auth_user');
        
        if (savedToken && savedUser) {
          // Verify token is still valid
          const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
            headers: {
              'Authorization': `Bearer ${savedToken}`,
            },
          });
          
          if (response.ok) {
            setState({
              user: JSON.parse(savedUser),
              token: savedToken,
              isLoading: false,
              error: null,
            });
          } else {
            // Token expired or invalid
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            setState({
              user: null,
              token: null,
              isLoading: false,
              error: null,
            });
          }
        } else {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Auth verification failed:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };
    
    loadSavedAuth();
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });
      
      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Login failed'));
      }
      
      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        throw new Error('Login failed: server returned an unexpected response. Ensure the backend is running and the API URL/proxy is correct.');
      }

      const data: LoginResponse = body as LoginResponse;
      
      const user: User = {
        id: String(data.user.id),
        email: data.user.email,
        name: data.user.name || data.user.full_name || 'User',
        company: data.user.company || data.user.company_name || 'Company',
        companyId: data.user.company_id,
        role: data.user.role as UserRole,
        avatar: `https://picsum.photos/seed/${data.user.email}/200`,
      };
      
      // Save to localStorage
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_user', JSON.stringify(user));
      // Convenience: some components read the active tenant from localStorage
      localStorage.setItem('company', user.company);
      
      setState({
        user,
        token: data.access_token,
        isLoading: false,
        error: null,
      });
      
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const register = useCallback(async (
    email: string,
    password: string,
    fullName: string,
    companyId: number,
    role: UserRole = UserRole.VIEWER
  ): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          company_id: companyId,
          role,
        }),
      });
      
      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Registration failed'));
      }
      
      // Registration successful, now login
      return await login(email, password);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('company');
    setState({
      user: null,
      token: null,
      isLoading: false,
      error: null,
    });
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return (
    <AuthContext.Provider 
      value={{ 
        user: state.user,
        token: state.token,
        isLoading: state.isLoading,
        error: state.error,
        login, 
        register, 
        logout, 
        isAuthenticated: !!state.user && !!state.token,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

// Utility hook for making authenticated API requests
export const useAuthFetch = () => {
  const { token, logout, user } = useAuth();
  
  const authFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers);
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // Multi-tenant routing: backend selects the active dataset by company
    if (user?.company && !headers.has('X-Company-ID')) {
      headers.set('X-Company-ID', user.company);
    }
    
    // If URL already starts with http, use as-is; otherwise prepend API_BASE_URL
    const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
    
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      logout();
      throw new Error('Session expired. Please login again.');
    }
    
    return response;
  }, [token, logout, user]);
  
  return authFetch;
};
