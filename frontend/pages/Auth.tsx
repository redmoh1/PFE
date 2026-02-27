
import React, { useState, useEffect } from 'react';
import { useAuth } from '../store/AuthContext';
import { Lock, Mail, Building, ArrowRight, User, AlertCircle, Loader2 } from 'lucide-react';
import { UserRole } from '../types';

const AuthPage: React.FC = () => {
  const { login, register, isLoading, error, clearError } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [companyId, setCompanyId] = useState<number>(1); // Default to first company
  const [localError, setLocalError] = useState<string | null>(null);

  // Clear errors when switching between login/register
  useEffect(() => {
    setLocalError(null);
    clearError?.();
  }, [isLogin, clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    // Validation
    if (password.length < 8 && !isLogin) {
      setLocalError('Password must be at least 8 characters');
      return;
    }

    try {
      let success: boolean;
      if (isLogin) {
        success = await login(email, password);
      } else {
        success = await register(email, password, fullName, companyId, UserRole.ANALYST);
      }
      
      if (!success) {
        // Error is handled by context
      }
    } catch (err) {
      setLocalError('An unexpected error occurred');
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen flex">
      {/* Left Column: Visual/Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-950 p-12 flex-col justify-between relative overflow-hidden">
        <div className="absolute top-0 right-0 w-full h-full opacity-10 pointer-events-none">
           <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
             <defs>
               <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                 <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" strokeWidth="0.5"/>
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
            <span className="text-slate-500">Built for Enterprise.</span>
          </h1>
          <p className="text-xl text-slate-400 max-w-md leading-relaxed">
            Harness the power of machine learning to forecast sales, segment customers, and analyze sentiment in one unified dashboard.
          </p>
        </div>

        <div className="relative z-10 flex gap-12">
           <div>
              <p className="text-3xl font-bold text-white">10M+</p>
              <p className="text-slate-500 text-sm font-medium">Events Processed</p>
           </div>
           <div>
              <p className="text-3xl font-bold text-white">99.9%</p>
              <p className="text-slate-500 text-sm font-medium">Uptime SLA</p>
           </div>
        </div>
      </div>

      {/* Right Column: Auth Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-background-light">
        <div className="w-full max-w-md space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight text-text-primary">
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="mt-2 text-text-secondary">
              {isLogin ? 'Enter your credentials to access your dashboard' : 'Start your 14-day free trial today'}
            </p>
          </div>

          {/* Error Display */}
          {displayError && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 animate-in slide-in-from-top-2">
              <AlertCircle size={18} />
              <span className="text-sm">{displayError}</span>
            </div>
          )}

          {/* Demo Credentials Info */}
          {isLogin && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-blue-700 text-sm">
              <p className="font-semibold mb-1">Demo Credentials:</p>
              <p>Admin: <code className="bg-blue-100 px-1 rounded">admin@acme.com</code> / <code className="bg-blue-100 px-1 rounded">admin123</code></p>
              <p>Analyst: <code className="bg-blue-100 px-1 rounded">analyst@acme.com</code> / <code className="bg-blue-100 px-1 rounded">analyst123</code></p>
            </div>
          )}

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
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              {!isLogin && (
                <>
                  <div className="relative animate-in slide-in-from-top-2">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <User size={18} />
                    </div>
                    <input
                      type="text"
                      required
                      placeholder="Full Name"
                      className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      disabled={isLoading}
                    />
                  </div>
                  
                  <div className="relative animate-in slide-in-from-top-2">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Building size={18} />
                    </div>
                    <select
                      required
                      className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white appearance-none"
                      value={companyId}
                      onChange={(e) => setCompanyId(parseInt(e.target.value))}
                      disabled={isLoading}
                    >
                      <option value={1}>Acme Corp</option>
                      <option value={2}>TechCo Industries</option>
                    </select>
                  </div>
                </>
              )}

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  placeholder="Password (min 8 characters)"
                  minLength={isLogin ? undefined : 8}
                  className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all bg-white"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 px-4 rounded-xl font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {isLogin ? 'Signing In...' : 'Creating Account...'}
                </>
              ) : (
                <>
                  {isLogin ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="text-center">
            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm font-semibold text-primary hover:underline"
              disabled={isLoading}
            >
              {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
            </button>
          </div>


        </div>
      </div>
    </div>
  );
};

export default AuthPage;
