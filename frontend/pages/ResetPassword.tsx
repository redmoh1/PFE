import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, CheckCircle2, KeyRound, Loader2, Lock } from 'lucide-react';
import ClassicAuthLayout from '../components/ClassicAuthLayout';
import { useAuth } from '../store/AuthContext';

interface ResetPasswordPageProps {
  token?: string;
  onNavigate: (view: string, params?: Record<string, string>) => void;
}

const ResetPasswordPage: React.FC<ResetPasswordPageProps> = ({ token = '', onNavigate }) => {
  const { validateResetToken, resetPassword, isLoading, error, clearError } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isCheckingToken, setIsCheckingToken] = useState(true);
  const [tokenIsValid, setTokenIsValid] = useState(false);
  const [tokenMessage, setTokenMessage] = useState('Checking reset link...');
  const [resetComplete, setResetComplete] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const runValidation = async () => {
      clearError();
      setIsCheckingToken(true);
      const result = await validateResetToken(token);
      if (cancelled) {
        return;
      }
      setTokenIsValid(result.valid);
      setTokenMessage(result.message || (result.valid ? 'Reset link accepted. Choose a new password.' : 'Reset link is invalid or expired.'));
      setIsCheckingToken(false);
    };

    runValidation();

    return () => {
      cancelled = true;
    };
  }, [clearError, token, validateResetToken]);

  const displayError = localError || error;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    clearError();

    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    const success = await resetPassword(token, password);
    if (success) {
      setResetComplete(true);
    }
  };

  return (
    <ClassicAuthLayout
      title="Choose a new password"
      description="Reset links are validated before the form is shown. Once the password is updated, the link cannot be reused."
      heroDescription="Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard."
      highlights={[
        'Dedicated company workspace with isolated tenant data.',
        'Reset links are validated before a new password is accepted.',
        'Password recovery stays consistent with the same secure auth flow.',
      ]}
    >
      <div className="space-y-6">
        {displayError ? (
          <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 animate-in slide-in-from-top-2">
            <AlertCircle size={18} />
            <span className="text-sm">{displayError}</span>
          </div>
        ) : null}

        {isCheckingToken ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-slate-700">
            <div className="flex items-center gap-3">
              <Loader2 size={20} className="animate-spin" />
              <span className="font-semibold">Checking reset link</span>
            </div>
          </div>
        ) : resetComplete ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-6 text-emerald-950">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
              <div>
                <div className="text-base font-bold">Password updated</div>
                <p className="mt-2 text-sm leading-6">
                  Your password has been reset successfully. Return to sign in using the new password.
                </p>
                <button
                  type="button"
                  onClick={() => onNavigate('login')}
                  className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
                >
                  <ArrowLeft size={16} />
                  Go to sign in
                </button>
              </div>
            </div>
          </div>
        ) : !tokenIsValid ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="mt-0.5 shrink-0" />
              <div>
                <div className="text-base font-bold">Reset link unavailable</div>
                <p className="mt-2 text-sm leading-6">{tokenMessage}</p>
                <button
                  type="button"
                  onClick={() => onNavigate('forgot-password')}
                  className="mt-4 text-sm font-semibold text-primary hover:underline"
                >
                  Request a new reset email
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-5 text-emerald-950">
              <div className="flex items-start gap-3">
                <KeyRound size={18} className="mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold">Link accepted</div>
                  <p className="mt-1 text-sm leading-6">{tokenMessage}</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="New password"
                  disabled={isLoading}
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                />
              </div>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="Confirm new password"
                  disabled={isLoading}
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 px-4 rounded-2xl font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Updating password...
                  </>
                ) : (
                  <>
                    Save new password
                    <CheckCircle2 size={18} />
                  </>
                )}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => onNavigate('login')}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
                >
                  <ArrowLeft size={16} />
                  Back to sign in
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </ClassicAuthLayout>
  );
};

export default ResetPasswordPage;
