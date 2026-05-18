import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, Mail, Send } from 'lucide-react';
import ClassicAuthLayout from '../components/ClassicAuthLayout';
import { useAuth } from '../store/AuthContext';

interface ForgotPasswordPageProps {
  initialEmail?: string;
  onNavigate: (view: string, params?: Record<string, string>) => void;
}

const ForgotPasswordPage: React.FC<ForgotPasswordPageProps> = ({ initialEmail = '', onNavigate }) => {
  const { requestPasswordReset, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [localError, setLocalError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setEmail(initialEmail);
  }, [initialEmail]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const normalizedEmail = email.trim().toLowerCase();
  const displayError = localError || error;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);
    clearError();

    if (!normalizedEmail) {
      setLocalError('Email is required.');
      return;
    }

    const success = await requestPasswordReset(normalizedEmail);
    if (success) {
      setSubmitted(true);
    }
  };

  return (
    <ClassicAuthLayout
      title="Send a password reset link"
      description="We will email a reset link if the account exists. The response stays generic so the flow does not leak whether an address is registered."
      heroDescription="Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard."
      highlights={[
        'Dedicated company workspace with isolated tenant data.',
        'Secure email-based account recovery for existing users.',
        'Password reset links stay time-limited and single-use.',
      ]}
    >
      <div className="space-y-6">
        {displayError ? (
          <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 animate-in slide-in-from-top-2">
            <AlertCircle size={18} />
            <span className="text-sm">{displayError}</span>
          </div>
        ) : null}

        {submitted ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-5 text-emerald-950">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <div>
                <div className="text-base font-bold">Check your inbox</div>
                <p className="mt-2 text-sm leading-6">
                  If an account exists for {normalizedEmail || 'that email address'}, a password reset link has been sent. Open the link in the email to continue.
                </p>
                <button
                  type="button"
                  onClick={() => onNavigate('login', normalizedEmail ? { email: normalizedEmail } : undefined)}
                  className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
                >
                  <ArrowLeft size={16} />
                  Return to sign in
                </button>
              </div>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
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

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              Reset links are time-limited and intended for the account owner only. Use the same email address you used during registration.
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 px-4 rounded-2xl font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Sending reset link...
                </>
              ) : (
                <>
                  Send reset link
                  <Send size={18} />
                </>
              )}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => onNavigate('login', normalizedEmail ? { email: normalizedEmail } : undefined)}
                className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
                disabled={isLoading}
              >
                <ArrowLeft size={16} />
                Back to sign in
              </button>
            </div>
          </form>
        )}
      </div>
    </ClassicAuthLayout>
  );
};

export default ForgotPasswordPage;
