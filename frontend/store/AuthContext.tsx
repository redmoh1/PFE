
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, canSwitchBranches, normalizeUserRole } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE || '';
const PENDING_VERIFICATION_STORAGE_KEY = 'pending_verification';

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
    branch_id?: number | string | null;
    company_name?: string;
    is_active?: boolean;
    is_email_verified?: boolean;
  };
}

interface VerificationChallengeResponse {
  email: string;
  message: string;
  verification_required: boolean;
  email_sent: boolean;
  expires_in: number;
  resend_available_in: number;
}

interface PendingVerificationState {
  email: string;
  message: string;
  emailSent: boolean;
  expiresIn: number;
  resendAvailableIn: number;
}

interface RegisterPayload {
  companyName: string;
  branchName: string;
  fullName: string;
  email: string;
  password: string;
}

interface ResetTokenValidationResult {
  valid: boolean;
  message?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  pendingVerification: PendingVerificationState | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (payload: RegisterPayload) => Promise<boolean>;
  verifyEmailOTP: (email: string, otp: string) => Promise<boolean>;
  resendVerificationOTP: (email: string) => Promise<boolean>;
  requestPasswordReset: (email: string) => Promise<boolean>;
  validateResetToken: (token: string) => Promise<ResetTokenValidationResult>;
  resetPassword: (token: string, password: string) => Promise<boolean>;
  clearPendingVerification: () => void;
  logout: () => void;
  selectedBranchId: string;
  setSelectedBranchId: (branchId: string) => void;
  isAuthenticated: boolean;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function safeReadJson(response: Response): Promise<any | null> {
  if (response.status === 204 || response.status === 205) return null;

  const contentType = response.headers.get('content-type') || '';
  const text = await response.text();
  if (!text) return null;

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

function normalizeEmail(email: string): string {
  return String(email || '').trim().toLowerCase();
}

function normalizeBranchSelection(branchId: string | number | null | undefined): string {
  const value = String(branchId ?? '').trim();
  if (!value) return '';
  return /^\d+$/.test(value) ? value : '';
}

function normalizeVerificationChallenge(raw: VerificationChallengeResponse): PendingVerificationState {
  return {
    email: normalizeEmail(raw.email),
    message: raw.message,
    emailSent: Boolean(raw.email_sent),
    expiresIn: Math.max(Number(raw.expires_in || 0), 0),
    resendAvailableIn: Math.max(Number(raw.resend_available_in || 0), 0),
  };
}

function loadPendingVerification(): PendingVerificationState | null {
  try {
    const saved = sessionStorage.getItem(PENDING_VERIFICATION_STORAGE_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as PendingVerificationState;
    if (!parsed?.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedBranchId, setSelectedBranchIdState] = useState<string>('');
  const [pendingVerification, setPendingVerification] = useState<PendingVerificationState | null>(() => loadPendingVerification());
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    error: null,
  });

  const savePendingVerification = useCallback((challenge: PendingVerificationState | null) => {
    setPendingVerification(challenge);
    if (challenge) {
      sessionStorage.setItem(PENDING_VERIFICATION_STORAGE_KEY, JSON.stringify(challenge));
    } else {
      sessionStorage.removeItem(PENDING_VERIFICATION_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    const loadSavedAuth = async () => {
      try {
        const savedToken = localStorage.getItem('auth_token');
        const savedUser = localStorage.getItem('auth_user');

        if (savedToken && savedUser) {
          const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
            headers: {
              'Authorization': `Bearer ${savedToken}`,
            },
          });

          if (response.ok) {
            const parsedUser = JSON.parse(savedUser) as User;
            const normalizedUser: User = {
              ...parsedUser,
              role: normalizeUserRole(parsedUser.role),
            };
            const savedBranch = normalizeBranchSelection(localStorage.getItem('selected_branch_id'));
            const userBranch = normalizeBranchSelection(normalizedUser?.branchId);
            localStorage.setItem('auth_user', JSON.stringify(normalizedUser));
            localStorage.setItem('selected_branch_id', savedBranch || userBranch);
            setSelectedBranchIdState(savedBranch || userBranch);
            setState({
              user: normalizedUser,
              token: savedToken,
              isLoading: false,
              error: null,
            });
          } else {
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

  const persistAuthSession = useCallback((data: LoginResponse, flashMessage?: string) => {
    const user: User = {
      id: String(data.user.id),
      email: data.user.email,
      name: data.user.name || data.user.full_name || 'User',
      company: data.user.company || data.user.company_name || 'Company',
      companyId: data.user.company_id,
      branchId: data.user.branch_id,
      role: normalizeUserRole(data.user.role),
      avatar: `https://picsum.photos/seed/${data.user.email}/200`,
    };

    localStorage.setItem('auth_token', data.access_token);
    localStorage.setItem('auth_user', JSON.stringify(user));
    localStorage.setItem('company', user.company);

    const initialBranch = normalizeBranchSelection(user.branchId);
    localStorage.setItem('selected_branch_id', initialBranch);
    setSelectedBranchIdState(initialBranch);

    if (flashMessage) {
      sessionStorage.setItem('auth_success_message', flashMessage);
    } else {
      sessionStorage.removeItem('auth_success_message');
    }

    savePendingVerification(null);
    setState({
      user,
      token: data.access_token,
      isLoading: false,
      error: null,
    });
  }, [savePendingVerification]);

  const clearPendingVerification = useCallback(() => {
    savePendingVerification(null);
  }, [savePendingVerification]);

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
        const message = formatHttpError(response, errorBody, 'Login failed');
        if (response.status === 403 && message.toLowerCase().includes('not verified')) {
          const normalizedEmail = normalizeEmail(email);
          savePendingVerification({
            email: normalizedEmail,
            message,
            emailSent: pendingVerification?.email === normalizedEmail ? pendingVerification.emailSent : false,
            expiresIn: pendingVerification?.email === normalizedEmail ? pendingVerification.expiresIn : 0,
            resendAvailableIn: pendingVerification?.email === normalizedEmail ? pendingVerification.resendAvailableIn : 0,
          });
        }
        throw new Error(message);
      }

      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        throw new Error('Login failed: server returned an unexpected response. Ensure the backend is running and the API URL/proxy is correct.');
      }

      persistAuthSession(body as LoginResponse);
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
  }, [pendingVerification, persistAuthSession, savePendingVerification]);

  const register = useCallback(async ({
    companyName,
    branchName,
    fullName,
    email,
    password,
  }: RegisterPayload): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: companyName,
          branch_name: branchName,
          email,
          password,
          full_name: fullName,
        }),
      });

      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Registration failed'));
      }

      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        throw new Error('Registration failed: server returned an unexpected response.');
      }

      const challenge = normalizeVerificationChallenge(body as VerificationChallengeResponse);
      savePendingVerification(challenge);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: null,
      }));
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, [savePendingVerification]);

  const verifyEmailOTP = useCallback(async (email: string, otp: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, otp }),
      });

      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Verification failed'));
      }

      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        throw new Error('Verification failed: server returned an unexpected response.');
      }

      persistAuthSession(body as LoginResponse, 'Email verified successfully. Your workspace is now active.');
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Verification failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, [persistAuthSession]);

  const resendVerificationOTP = useCallback(async (email: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify-email/resend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Resend failed'));
      }

      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        throw new Error('Resend failed: server returned an unexpected response.');
      }

      savePendingVerification(normalizeVerificationChallenge(body as VerificationChallengeResponse));
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: null,
      }));
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Resend failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, [savePendingVerification]);

  const requestPasswordReset = useCallback(async (email: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Password reset request failed'));
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: null,
      }));
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Password reset request failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const validateResetToken = useCallback(async (token: string): Promise<ResetTokenValidationResult> => {
    if (!token.trim()) {
      return { valid: false, message: 'Reset link is invalid or expired.' };
    }

    try {
      const query = new URLSearchParams({ token }).toString();
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-password/validate?${query}`);
      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        return { valid: false, message: formatHttpError(response, errorBody, 'Reset link validation failed') };
      }

      const body = await safeReadJson(response);
      if (!body || (body as any)._nonJson || (body as any)._invalidJson) {
        return { valid: false, message: 'Reset link is invalid or expired.' };
      }

      return {
        valid: Boolean((body as ResetTokenValidationResult).valid),
        message: (body as ResetTokenValidationResult).message,
      };
    } catch {
      return { valid: false, message: 'Reset link is invalid or expired.' };
    }
  }, []);

  const resetPassword = useCallback(async (token: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        const errorBody = await safeReadJson(response);
        throw new Error(formatHttpError(response, errorBody, 'Password reset failed'));
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: null,
      }));
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Password reset failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('company');
    localStorage.removeItem('selected_branch_id');
    sessionStorage.removeItem('auth_success_message');
    savePendingVerification(null);
    setSelectedBranchIdState('');
    setState({
      user: null,
      token: null,
      isLoading: false,
      error: null,
    });
  }, [savePendingVerification]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const setSelectedBranchId = useCallback((branchId: string) => {
    const value = normalizeBranchSelection(branchId);
    setSelectedBranchIdState(value);
    localStorage.setItem('selected_branch_id', value);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user: state.user,
        token: state.token,
        isLoading: state.isLoading,
        error: state.error,
        pendingVerification,
        login,
        register,
        verifyEmailOTP,
        resendVerificationOTP,
        requestPasswordReset,
        validateResetToken,
        resetPassword,
        clearPendingVerification,
        logout,
        selectedBranchId,
        setSelectedBranchId,
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
  const { token, logout, user, selectedBranchId } = useAuth();
  
  const authFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers);
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const forcedBranch = normalizeBranchSelection(user?.branchId);
    const requestedBranch = normalizeBranchSelection(selectedBranchId);
    const effectiveBranch = canSwitchBranches(user?.role) ? requestedBranch : (forcedBranch || requestedBranch);
    
    // If URL already starts with http, use as-is; otherwise prepend API_BASE_URL
    const fullUrl = (() => {
      const baseUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
      if (!effectiveBranch) return baseUrl;
      try {
        const parsed = new URL(baseUrl, window.location.origin);
        if (!parsed.searchParams.has('branch_id')) {
          parsed.searchParams.set('branch_id', effectiveBranch);
        }
        return parsed.toString();
      } catch {
        const separator = baseUrl.includes('?') ? '&' : '?';
        return `${baseUrl}${separator}branch_id=${encodeURIComponent(effectiveBranch)}`;
      }
    })();
    
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      logout();
      throw new Error('Session expired. Please login again.');
    }
    
    return response;
  }, [token, logout, user, selectedBranchId]);
  
  return authFetch;
};
