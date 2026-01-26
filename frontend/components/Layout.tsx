
import React, { useState } from 'react';
import { useAuth } from '../store/AuthContext';
import { 
  LayoutDashboard, 
  BarChart3, 
  TrendingUp, 
  Users, 
  Lightbulb, 
  MessageSquare, 
  Upload, 
  Settings, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  Bell
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  onNavigate: (page: string) => void;
  currentPage: string;
  isDark: boolean;
  onToggleTheme: () => void;
}

const Layout: React.FC<LayoutProps> = ({ children, onNavigate, currentPage, isDark, onToggleTheme }) => {
  const { user, logout } = useAuth();
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'sales', label: 'Sales Analytics', icon: BarChart3 },
    { id: 'forecasting', label: 'Forecasting', icon: TrendingUp },
    { id: 'segmentation', label: 'Segmentation', icon: Users },
    { id: 'recommendations', label: 'Recommendations', icon: Lightbulb },
    { id: 'sentiment', label: 'Sentiment Analysis', icon: MessageSquare },
    { id: 'divider', type: 'divider' },
    { id: 'upload', label: 'Data Ingestion', icon: Upload },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background-light dark:bg-background-dark">
      {/* Sidebar */}
      <aside 
        className={`${isSidebarCollapsed ? 'w-20' : 'w-64'} transition-all duration-300 border-r border-slate-200 dark:border-slate-800 bg-card-light dark:bg-card-dark flex flex-col`}
      >
        <div className="p-6 flex items-center justify-between">
          {!isSidebarCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white font-bold">I</div>
              <span className="font-bold text-xl tracking-tight">InsightPro</span>
            </div>
          )}
          {isSidebarCollapsed && (
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white font-bold mx-auto">I</div>
          )}
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto custom-scrollbar">
          {navItems.map((item, idx) => {
            if (item.type === 'divider') {
              return <div key={`divider-${idx}`} className="h-px bg-slate-200 dark:bg-slate-800 my-4" />;
            }
            const Icon = item.icon!;
            const isActive = currentPage === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id!)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${
                  isActive 
                    ? 'bg-primary/10 text-primary' 
                    : 'text-text-secondary dark:text-text-secondaryDark hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <Icon size={20} className={isActive ? 'text-primary' : ''} />
                {!isSidebarCollapsed && <span className="font-medium text-sm">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800">
          <button 
            onClick={logout}
            className="w-full flex items-center gap-3 p-3 text-error hover:bg-red-50 dark:hover:bg-red-950/20 rounded-xl transition-all"
          >
            <LogOut size={20} />
            {!isSidebarCollapsed && <span className="font-medium text-sm">Logout</span>}
          </button>
          
          <button 
            onClick={() => setSidebarCollapsed(!isSidebarCollapsed)}
            className="mt-2 w-full flex items-center justify-center p-2 text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
          >
            {isSidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-card-light dark:bg-card-dark flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4">
             <h1 className="text-sm font-semibold text-text-secondary dark:text-text-secondaryDark">
              {user?.company} Workspace
             </h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={onToggleTheme}
              className="p-2 text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button className="p-2 text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg relative">
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full"></span>
            </button>
            <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-2" />
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold">{user?.email}</p>
                <p className="text-xs text-text-secondary">{user?.role}</p>
              </div>
              <img 
                src={user?.avatar} 
                className="w-8 h-8 rounded-full border border-slate-200 dark:border-slate-700" 
                alt="Profile"
              />
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
