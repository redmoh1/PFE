import React from 'react';

interface ClassicAuthLayoutProps {
  title: string;
  description: string;
  children: React.ReactNode;
  highlights?: string[];
  heroDescription?: string;
}

const heroStats = [
  { value: '10M+', label: 'Events Processed' },
  { value: '99.9%', label: 'Uptime SLA' },
];

const ClassicAuthLayout: React.FC<ClassicAuthLayoutProps> = ({
  title,
  description,
  children,
  heroDescription = 'Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard.',
}) => {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.08),_transparent_42%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_45%,_#f8fafc_100%)]">
      <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="flex w-full bg-slate-950 p-8 sm:p-10 lg:w-1/2 lg:p-12 flex-col justify-between relative overflow-hidden min-h-[420px] lg:min-h-screen">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.22),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.18),_transparent_30%)]" />
        <div className="absolute top-0 right-0 w-full h-full opacity-10 pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="classic-auth-grid" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#classic-auth-grid)" />
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
          <p className="text-xl text-slate-400 max-w-md leading-relaxed">{heroDescription}</p>
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
            <h2 className="text-3xl font-bold tracking-tight text-text-primary">{title}</h2>
            <p className="mt-2 text-text-secondary">{description}</p>
          </div>

          {children}
        </div>
      </div>
      </div>
    </div>
  );
};

export default ClassicAuthLayout;