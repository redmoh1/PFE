import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Loader2, Lock, Mail, ShieldAlert } from 'lucide-react';
import { useAuth } from '../store/AuthContext';

interface LoginPageProps {
  initialEmail?: string;
  onNavigate: (view: string, params?: Record<string, string>) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ initialEmail = '', onNavigate }) => {
  const { login, pendingVerification, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setEmail(initialEmail);
  }, [initialEmail]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const displayError = localError || error;
  const normalizedEmail = email.trim().toLowerCase();
  const pendingMessage = pendingVerification?.email === normalizedEmail ? pendingVerification.message : null;
  const heroStats = [
    { value: '10M+', label: 'Events Processed' },
    { value: '99.9%', label: 'Uptime SLA' },
  ];

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    clearError();

    if (!normalizedEmail || !password) {
      setLocalError('Email and password are required.');
      return;
    }

    const success = await login(normalizedEmail, password);
    if (success) {
      return;
    }

    try {
      const savedChallenge = sessionStorage.getItem('pending_verification');
      if (!savedChallenge) {
        return;
      }
      const parsed = JSON.parse(savedChallenge) as { email?: string };
      if (parsed.email === normalizedEmail) {
        onNavigate('verify-email', { email: normalizedEmail });
      }
    } catch {
      // Ignore malformed session state and keep the user on the login form.
    }
  };

  return (
    <div className="min-h-screen flex bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.08),_transparent_42%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_45%,_#f8fafc_100%)]">
      <div className="hidden lg:flex lg:w-1/2 bg-slate-950 p-12 flex-col justify-between relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.22),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.18),_transparent_30%)]" />
        <div className="absolute top-0 right-0 w-full h-full opacity-10 pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        <div className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-white font-black text-xl">I</div>
          <span className="text-2xl font-bold tracking-tight text-white">InsightPro</span>
        </div>

        <div className="relative z-10">
          <h1 className="text-5xl font-bold text-white leading-tight mb-6">
            Intelligent Sales Overview <br />
            <span className="text-slate-400">Built for Enterprise.</span>
          </h1>
          <p className="text-xl text-slate-400 max-w-md leading-relaxed">
            Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard.
          </p>
        </div>

        <div className="relative z-10 flex items-end gap-10 pt-8">
          {heroStats.map((stat) => (
            <div key={stat.label}>
              <div className="text-5xl font-black tracking-tight text-white">{stat.value}</div>
              <div className="mt-1 text-sm font-medium text-slate-400">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-8">
        <div className="w-full max-w-xl space-y-8 rounded-[32px] border border-white/60 bg-white/90 p-6 shadow-[0_30px_80px_rgba(15,23,42,0.12)] backdrop-blur-xl animate-in fade-in slide-in-from-right-4 duration-500 sm:p-8">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight text-text-primary">Welcome back</h2>
            <p className="mt-2 text-text-secondary">Enter your credentials to access your dashboard.</p>
          </div>

          {displayError && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 animate-in slide-in-from-top-2">
              <AlertCircle size={18} />
              <span className="text-sm">{displayError}</span>
            </div>
          )}

          {pendingMessage ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
              <div className="flex items-start gap-3">
                <ShieldAlert size={18} className="mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold">Verification still required</div>
                  <p className="mt-1 text-sm leading-6">{pendingMessage}</p>
                  <button
                    type="button"
                    onClick={() => onNavigate('verify-email', { email: normalizedEmail })}
                    className="mt-3 text-sm font-semibold text-amber-900 underline decoration-amber-400 underline-offset-4"
                  >
                    Enter verification code
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  placeholder="name@company.com"
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  placeholder="Password"
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-4 text-sm">
              <button
                type="button"
                onClick={() => onNavigate('forgot-password', normalizedEmail ? { email: normalizedEmail } : undefined)}
                className="font-semibold text-slate-600 transition hover:text-slate-900"
                disabled={isLoading}
              >
                Forgot password?
              </button>
              <button
                type="button"
                onClick={() => onNavigate('register')}
                className="font-semibold text-primary hover:underline"
                disabled={isLoading}
              >
                Don&apos;t have an account? Sign up
              </button>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 px-4 rounded-2xl font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Signing In...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
