import React from 'react';
import { Building2, KeyRound, ShieldCheck, Sparkles } from 'lucide-react';

interface AuthShellProps {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const highlights = [
  {
    icon: Building2,
    title: 'Tenant isolation by default',
    description: 'Each company starts with a dedicated workspace, scoped data paths, and its own admin entry point.',
  },
  {
    icon: ShieldCheck,
    title: 'Verification before activation',
    description: 'New workspaces stay protected until the email owner confirms the OTP sent during registration.',
  },
  {
    icon: KeyRound,
    title: 'Recovery without support delays',
    description: 'Password reset links and verification resends are built into the same account lifecycle.',
  },
];

const AuthShell: React.FC<AuthShellProps> = ({ eyebrow, title, description, children, footer }) => {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(217,119,6,0.12),_transparent_28%),linear-gradient(135deg,_#f8fafc_0%,_#fffaf0_45%,_#f8fafc_100%)]">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col lg:flex-row">
        <aside className="relative overflow-hidden bg-slate-950 px-6 py-8 sm:px-10 lg:flex lg:w-[48%] lg:flex-col lg:justify-between lg:px-12 lg:py-12">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(13,148,136,0.26),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.18),_transparent_26%)]" />
          <div className="absolute inset-0 opacity-10">
            <svg className="h-full w-full" viewBox="0 0 120 120" preserveAspectRatio="none">
              <defs>
                <pattern id="auth-grid" width="12" height="12" patternUnits="userSpaceOnUse">
                  <path d="M 12 0 L 0 0 0 12" fill="none" stroke="white" strokeWidth="0.6" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#auth-grid)" />
            </svg>
          </div>

          <div className="relative z-10 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-white shadow-lg shadow-black/20 backdrop-blur">
              <Sparkles size={20} />
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.32em] text-teal-200/80">InsightPro SaaS</div>
              <div className="text-2xl font-black tracking-tight text-white">Identity Workspace</div>
            </div>
          </div>

          <div className="relative z-10 mt-12 lg:mt-0">
            <div className="mb-4 inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-amber-200/80 backdrop-blur">
              Secure onboarding pipeline
            </div>
            <h1 className="max-w-xl text-4xl font-black leading-tight text-white sm:text-5xl">
              Tenant creation, verification, and recovery in one account flow.
            </h1>
            <p className="mt-6 max-w-lg text-base leading-7 text-slate-300 sm:text-lg">
              Your workspace now supports professional registration with OTP verification, delayed activation, and recovery paths that respect the same multi-tenant boundaries.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                <div className="text-2xl font-black text-white">1</div>
                <div className="mt-2 text-sm text-slate-300">Provision company and branch</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                <div className="text-2xl font-black text-white">2</div>
                <div className="mt-2 text-sm text-slate-300">Verify ownership with OTP</div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                <div className="text-2xl font-black text-white">3</div>
                <div className="mt-2 text-sm text-slate-300">Recover access without support</div>
              </div>
            </div>
          </div>

          <div className="relative z-10 mt-8 grid gap-4 lg:mt-12">
            {highlights.map(({ icon: Icon, title: highlightTitle, description: highlightDescription }) => (
              <div key={highlightTitle} className="rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                <div className="flex items-start gap-4">
                  <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-teal-200">
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white/80">{highlightTitle}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{highlightDescription}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <main className="flex w-full items-center justify-center px-4 py-8 sm:px-6 lg:w-[52%] lg:px-10">
          <div className="w-full max-w-2xl rounded-[32px] border border-white/70 bg-white/90 p-6 shadow-[0_30px_90px_rgba(15,23,42,0.12)] backdrop-blur-xl sm:p-8 lg:p-10">
            <div className="mb-8">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-teal-700">{eyebrow}</div>
              <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">{title}</h2>
              <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{description}</p>
            </div>

            <div>{children}</div>

            {footer ? <div className="mt-8 border-t border-slate-200/80 pt-6">{footer}</div> : null}
          </div>
        </main>
      </div>
    </div>
  );
};

export default AuthShell;
