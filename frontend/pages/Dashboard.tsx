
import React from 'react';
import { useData } from '../store/DataContext';
import { 
  TrendingUp, 
  Users, 
  ShoppingBag, 
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';

const Dashboard: React.FC = () => {
  const { sales, forecast, segments, kpis, lastTrainingDate, isLoading, error, refreshData } = useData();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4 text-primary" size={48} />
          <p className="text-text-secondary">Loading data from server...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-error/10 border border-error/20 rounded-2xl p-6 flex items-start gap-4">
        <AlertCircle className="text-error flex-shrink-0" size={24} />
        <div>
          <h3 className="font-bold text-error mb-1">Data Loading Error</h3>
          <p className="text-sm text-text-secondary">{error}</p>
          <button 
            onClick={refreshData}
            className="mt-3 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const kpiCards = [
    { label: 'Total Revenue', value: `$${kpis?.total_revenue?.toLocaleString() || '0'}`, icon: DollarSign, trend: '+12.5%', isUp: true },
    { label: 'Total Orders', value: kpis?.total_orders?.toLocaleString() || '0', icon: ShoppingBag, trend: '+5.2%', isUp: true },
    { label: 'Avg. Order Value', value: `$${kpis?.average_order_value?.toFixed(2) || '0.00'}`, icon: TrendingUp, trend: '-2.1%', isUp: false },
    { label: 'Top City', value: kpis?.top_city || 'N/A', icon: Users, trend: 'N/A', isUp: true },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Executive Overview</h2>
          <p className="text-text-secondary dark:text-text-secondaryDark">Real-time performance metrics and ML-driven summaries.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-text-secondary bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Last updated: {lastTrainingDate ? new Date(lastTrainingDate).toLocaleString() : 'Never'}
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((kpi, idx) => (
          <div key={idx} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className="p-2.5 bg-primary/10 rounded-xl">
                <kpi.icon className="text-primary" size={24} />
              </div>
              {kpi.trend !== 'N/A' && (
                <div className={`flex items-center text-xs font-bold px-2 py-1 rounded-full ${kpi.isUp ? 'text-success bg-success/10' : 'text-error bg-error/10'}`}>
                  {kpi.isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  {kpi.trend}
                </div>
              )}
            </div>
            <p className="text-sm font-medium text-text-secondary dark:text-text-secondaryDark mb-1">{kpi.label}</p>
            <h3 className="text-2xl font-bold">{kpi.value}</h3>
          </div>
        ))}
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Revenue Trends with Forecast */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue Growth & Forecast</h3>
          {forecast && forecast.length > 0 ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={240}>
                <AreaChart data={forecast}>
                  <defs>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#64748B" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#64748B" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" opacity={0.5} />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 12}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                      borderRadius: '12px',
                      border: 'none',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' 
                    }}
                  />
                  <Area type="monotone" dataKey="actual" stroke="#2563EB" strokeWidth={3} fillOpacity={1} fill="url(#colorActual)" />
                  <Area type="monotone" dataKey="forecast" stroke="#64748B" strokeWidth={2} strokeDasharray="5 5" fillOpacity={1} fill="url(#colorForecast)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-text-secondary">
              <p>No forecast data available yet. Upload data to see projections.</p>
            </div>
          )}
        </div>

        {/* Customer Segmentation Summary */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Customer Segment Distribution</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={240}>
              <BarChart data={segments} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" opacity={0.5} />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} width={120} tick={{fontSize: 12}} />
                <Tooltip cursor={{fill: 'transparent'}} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={32}>
                  {segments.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
