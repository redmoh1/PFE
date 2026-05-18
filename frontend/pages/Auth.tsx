import React, { useCallback, useEffect, useState } from 'react';
import ForgotPasswordPage from './ForgotPassword';
import LoginPage from './Login';
import RegisterPage from './Register';
import ResetPasswordPage from './ResetPassword';
import VerifyEmailPage from './VerifyEmail';
import { useAuth } from '../store/AuthContext';

type AuthView = 'login' | 'register' | 'verify-email' | 'forgot-password' | 'reset-password';

interface AuthRouteState {
  view: AuthView;
  email: string;
  token: string;
}

function parseAuthRoute(): AuthRouteState {
  const url = new URL(window.location.href);
  const requestedView = url.searchParams.get('auth');
  const email = (url.searchParams.get('email') || '').trim().toLowerCase();
  const token = (url.searchParams.get('token') || '').trim();

  if (token) {
    return { view: 'reset-password', email, token };
  }

  switch (requestedView) {
    case 'register':
    case 'verify-email':
    case 'forgot-password':
    case 'login':
      return { view: requestedView, email, token: '' };
    case 'reset-password':
      return { view: 'forgot-password', email, token: '' };
    default:
      return { view: 'login', email, token: '' };
  }
}

const AuthPage: React.FC = () => {
  const { clearError } = useAuth();
  const [route, setRoute] = useState<AuthRouteState>(() => parseAuthRoute());

  const syncRouteFromLocation = useCallback(() => {
    setRoute(parseAuthRoute());
  }, []);

  useEffect(() => {
    window.addEventListener('popstate', syncRouteFromLocation);
    return () => {
      window.removeEventListener('popstate', syncRouteFromLocation);
    };
  }, [syncRouteFromLocation]);

  const navigate = useCallback((view: string, params?: Record<string, string>) => {
    const nextView = (['login', 'register', 'verify-email', 'forgot-password', 'reset-password'] as AuthView[]).includes(view as AuthView)
      ? (view as AuthView)
      : 'login';

    const url = new URL(window.location.href);
    url.searchParams.delete('auth');
    url.searchParams.delete('email');
    url.searchParams.delete('token');

    const email = (params?.email || '').trim().toLowerCase();
    const token = (params?.token || '').trim();

    if (nextView !== 'login') {
      url.searchParams.set('auth', nextView);
    }

    if (email) {
      url.searchParams.set('email', email);
    }

    if (token) {
      url.searchParams.set('token', token);
    }

    const nextUrl = `${url.pathname}${url.search}${url.hash}`;
    window.history.pushState(null, '', nextUrl);
    clearError();
    setRoute(parseAuthRoute());
  }, [clearError]);

  switch (route.view) {
    case 'register':
      return <RegisterPage initialEmail={route.email} onNavigate={navigate} />;
    case 'verify-email':
      return <VerifyEmailPage initialEmail={route.email} onNavigate={navigate} />;
    case 'forgot-password':
      return <ForgotPasswordPage initialEmail={route.email} onNavigate={navigate} />;
    case 'reset-password':
      return <ResetPasswordPage token={route.token} onNavigate={navigate} />;
    case 'login':
    default:
      return <LoginPage initialEmail={route.email} onNavigate={navigate} />;
  }
};

export default AuthPage;
