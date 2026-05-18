import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail, RefreshCw } from 'lucide-react';
import ClassicAuthLayout from '../components/ClassicAuthLayout';
import OtpInput from '../components/OtpInput';
import { useAuth } from '../store/AuthContext';

interface VerifyEmailPageProps {
  initialEmail?: string;
  onNavigate: (view: string, params?: Record<string, string>) => void;
}

function formatDuration(totalSeconds: number): string {
  const safeSeconds = Math.max(totalSeconds, 0);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

const VerifyEmailPage: React.FC<VerifyEmailPageProps> = ({ initialEmail = '', onNavigate }) => {
  const {
    verifyEmailOTP,
    resendVerificationOTP,
    pendingVerification,
    isLoading,
    error,
    clearError,
  } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [otp, setOtp] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(pendingVerification?.message || null);
  const [resendRemaining, setResendRemaining] = useState(pendingVerification?.resendAvailableIn || 0);
  const [expiryRemaining, setExpiryRemaining] = useState(pendingVerification?.expiresIn || 0);

  useEffect(() => {
    if (pendingVerification?.email) {
      setEmail(pendingVerification.email);
      setNotice(pendingVerification.message);
      setResendRemaining(pendingVerification.resendAvailableIn);
      setExpiryRemaining(pendingVerification.expiresIn);
    } else if (initialEmail) {
      setEmail(initialEmail);
    }
  }, [initialEmail, pendingVerification]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setResendRemaining((current) => (current > 0 ? current - 1 : 0));
      setExpiryRemaining((current) => (current > 0 ? current - 1 : 0));
    }, 1000);

    return () => {
      window.clearInterval(timerId);
    };
  }, []);

  const displayError = localError || error;
  const normalizedEmail = email.trim().toLowerCase();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    clearError();

    if (!normalizedEmail) {
      setLocalError('Email is required to verify the account.');
      return;
    }

    if (otp.length !== 6) {
      setLocalError('Enter the 6-digit verification code.');
      return;
    }

    const success = await verifyEmailOTP(normalizedEmail, otp);
    if (success) {
      return;
    }
  };

  const handleResend = async () => {
    setLocalError(null);
    clearError();

    if (!normalizedEmail) {
      setLocalError('Email is required to resend a code.');
      return;
    }

    const success = await resendVerificationOTP(normalizedEmail);
    if (success) {
      setOtp('');
      setNotice('A fresh verification code has been sent to your inbox.');
    }
  };

  return (
    <ClassicAuthLayout
      title="Activate the tenant admin account"
      description="Enter the one-time password we sent to the account email. The workspace remains inactive until the OTP is confirmed."
      heroDescription="Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard."
      highlights={[
        'Dedicated company workspace with isolated tenant data.',
        'New workspaces are activated only after OTP verification.',
        'Verification codes can be resent without breaking tenant isolation.',
      ]}
    >
      <div className="space-y-6">
        {displayError ? (
          <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 animate-in slide-in-from-top-2">
            <AlertCircle size={18} />
            <span className="text-sm">{displayError}</span>
          </div>
        ) : null}

        {notice ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-4 text-emerald-950">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold">Verification in progress</div>
                <p className="mt-1 text-sm leading-6">{notice}</p>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:grid-cols-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Email</div>
            <div className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Mail size={16} />
              <span>{normalizedEmail || 'Enter your email below'}</span>
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Code expires in</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{formatDuration(expiryRemaining)}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Resend available</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{formatDuration(resendRemaining)}</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {!normalizedEmail ? (
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Mail size={18} />
              </div>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.com"
                disabled={isLoading}
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
              />
            </div>
          ) : null}

          <div>
            <div className="mb-3 text-sm font-semibold text-slate-700">One-time password</div>
            <OtpInput value={otp} onChange={setOtp} disabled={isLoading} />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 px-4 rounded-2xl font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Verifying code...
              </>
            ) : (
              <>
                Confirm and activate workspace
                <CheckCircle2 size={18} />
              </>
            )}
          </button>
        </form>

        <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-900">Did not receive the code?</div>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Use resend after the cooldown reaches 00:00. The latest code will replace older ones.
            </p>
          </div>
          <button
            type="button"
            onClick={handleResend}
            disabled={isLoading || resendRemaining > 0 || !normalizedEmail}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-900 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Resend code
          </button>
        </div>

        <div className="flex items-center justify-between gap-4 text-sm">
          <button
            type="button"
            onClick={() => onNavigate('login', normalizedEmail ? { email: normalizedEmail } : undefined)}
            className="inline-flex items-center gap-2 font-semibold text-slate-600 transition hover:text-slate-900"
            disabled={isLoading}
          >
            <ArrowLeft size={16} />
            Back to sign in
          </button>
          <button
            type="button"
            onClick={() => onNavigate('register', normalizedEmail ? { email: normalizedEmail } : undefined)}
            className="font-semibold text-primary hover:underline"
            disabled={isLoading}
          >
            Edit registration details
          </button>
        </div>
      </div>
    </ClassicAuthLayout>
  );
};

export default VerifyEmailPage;
