
import React from 'react';
import { useData } from '../store/DataContext';
import FiltersBar from '../components/FiltersBar';
import { 
  TrendingUp, 
  Users, 
  ShoppingBag, 
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  RefreshCw,
  AlertCircle,
  Lightbulb,
  ShieldCheck
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
  const {
    sales,
    forecast,
    segments,
    kpis,
    insights,
    dataQuality,
    filters,
    setFilters,
    clearFilters,
    cityOptions,
    productOptions,
    lastTrainingDate,
    isLoading,
    error,
    refreshData,
  } = useData();

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

  // Helper function to format percentage change
  const formatChange = (change: number | null | undefined): string => {
    if (change === null || change === undefined) return '—';
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  };

  // Helper function to determine if change is positive, negative, or neutral
  const getChangeType = (change: number | null | undefined): 'up' | 'down' | 'neutral' => {
    if (change === null || change === undefined) return 'neutral';
    if (change > 0) return 'up';
    if (change < 0) return 'down';
    return 'neutral';
  };

  const kpiCards = [
    { 
      label: 'Total Revenue', 
      value: `$${kpis?.total_revenue?.toLocaleString() || '0'}`, 
      icon: DollarSign, 
      change: kpis?.revenue_change 
    },
    { 
      label: 'Total Orders', 
      value: kpis?.total_orders?.toLocaleString() || '0', 
      icon: ShoppingBag, 
      change: kpis?.orders_change 
    },
    { 
      label: 'Avg. Order Value', 
      value: `$${kpis?.average_order_value?.toFixed(2) || '0.00'}`, 
      icon: TrendingUp, 
      change: kpis?.aov_change 
    },
    { 
      label: 'Top City', 
      value: kpis?.top_city || 'N/A', 
      icon: Users, 
      change: null // Top city doesn't have a percentage change
    },
  ];

  const hasComparison = forecast?.some((p) => p.previous_actual !== undefined && p.previous_actual !== null);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Executive Overview</h2>
          <p className="text-text-secondary dark:text-text-secondaryDark">Real-time performance metrics and ML-driven insights.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-text-secondary bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Last updated: {lastTrainingDate ? new Date(lastTrainingDate).toLocaleString() : 'Never'}
        </div>
      </div>

      <FiltersBar
        filters={filters}
        setFilters={setFilters}
        clearFilters={clearFilters}
        cityOptions={cityOptions}
        productOptions={productOptions}
      />

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((kpi, idx) => {
          const changeType = getChangeType(kpi.change);
          const changeText = formatChange(kpi.change);
          
          return (
            <div key={idx} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2.5 bg-primary/10 rounded-xl">
                  <kpi.icon className="text-primary" size={24} />
                </div>
                {changeText !== '—' ? (
                  <div className={`flex items-center text-xs font-bold px-2 py-1 rounded-full ${
                    changeType === 'up' 
                      ? 'text-success bg-success/10' 
                      : changeType === 'down' 
                        ? 'text-error bg-error/10' 
                        : 'text-slate-500 bg-slate-100 dark:bg-slate-700'
                  }`}>
                    {changeType === 'up' && <ArrowUpRight size={14} />}
                    {changeType === 'down' && <ArrowDownRight size={14} />}
                    {changeType === 'neutral' && <Minus size={14} />}
                    {changeText}
                  </div>
                ) : kpi.label !== 'Top City' ? (
                  <div className="flex items-center text-xs font-bold px-2 py-1 rounded-full text-slate-400 bg-slate-100 dark:bg-slate-700">
                    <Minus size={14} />
                    —
                  </div>
                ) : null}
              </div>
              <p className="text-sm font-medium text-text-secondary dark:text-text-secondaryDark mb-1">{kpi.label}</p>
              <h3 className="text-2xl font-bold">{kpi.value}</h3>
            </div>
          );
        })}
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Revenue Trends with Forecast */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue Growth & Forecast</h3>
          <div className="flex flex-wrap gap-3 text-xs text-text-secondary dark:text-text-secondaryDark mb-4">
            {hasComparison && (
              <div className="flex items-center gap-2">
                <span className="w-6 h-[2px] bg-slate-400" style={{ borderTop: '2px dashed #94A3B8' }} />
                Previous period
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="w-6 h-[2px] bg-primary" />
              Actual
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-[2px]" style={{ borderTop: '2px dashed #64748B' }} />
              Forecast
            </div>
          </div>
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
                  {hasComparison && (
                    <Area
                      type="monotone"
                      dataKey="previous_actual"
                      name="Previous Period"
                      stroke="#94A3B8"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fillOpacity={0}
                    />
                  )}
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

      {/* Decision Insights */}
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Lightbulb className="text-primary" size={20} />
            <h3 className="text-lg font-bold">Decision Insights</h3>
          </div>
          <span className="text-xs text-text-secondary">Rule-based</span>
        </div>

        {insights && insights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((insight) => {
              const badge =
                insight.severity === 'critical'
                  ? 'bg-error/10 text-error border-error/20'
                  : insight.severity === 'warning'
                    ? 'bg-warning/10 text-warning border-warning/20'
                    : 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';

              return (
                <div
                  key={insight.id}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/20"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h4 className="font-bold leading-snug">{insight.title}</h4>
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${badge}`}>
                      {insight.severity}
                    </span>
                  </div>

                  <p className="text-sm text-text-secondary mb-3">{insight.description}</p>

                  <div className="text-sm">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">Reason</p>
                    <p className="text-text-secondary mb-3">{insight.reason}</p>

                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">Suggested action</p>
                    <p className="text-text-secondary">{insight.suggested_action}</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-sm text-text-secondary">
            No insights available yet. Upload data and run the pipeline.
          </div>
        )}
      </div>

      {/* Data Quality */}
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-primary" size={20} />
            <h3 className="text-lg font-bold">Data Quality</h3>
          </div>
          {dataQuality ? (
            <span className="text-xs text-text-secondary">
              Updated: {new Date(dataQuality.generated_at).toLocaleString()}
            </span>
          ) : null}
        </div>

        {dataQuality ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800">
              <p className="text-sm text-text-secondary mb-1">Quality score</p>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold">{dataQuality.quality_score}</span>
                <span className="text-sm text-text-secondary">/ 100</span>
              </div>
              <div className="mt-3 text-xs text-text-secondary space-y-1">
                <div>Rows: {dataQuality.row_count.toLocaleString()}</div>
                <div>Columns: {dataQuality.column_count.toLocaleString()}</div>
                {dataQuality.date_column ? (
                  <div>Date column: {dataQuality.date_column}</div>
                ) : (
                  <div>Date column: not detected</div>
                )}
              </div>
            </div>

            <div className="lg:col-span-2 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
              <p className="text-sm font-bold mb-3">Issues</p>
              <div className="space-y-3">
                {dataQuality.issues.map((issue) => {
                  const levelClass =
                    issue.level === 'critical'
                      ? 'text-error bg-error/10 border-error/20'
                      : issue.level === 'warning'
                        ? 'text-warning bg-warning/10 border-warning/20'
                        : 'text-slate-500 bg-slate-100 border-slate-200 dark:text-slate-300 dark:bg-slate-800 dark:border-slate-700';

                  return (
                    <div key={issue.id} className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{issue.message}</p>
                        {issue.affected_columns && issue.affected_columns.length > 0 ? (
                          <p className="text-xs text-text-secondary mt-1 truncate">
                            Columns: {issue.affected_columns.join(', ')}
                          </p>
                        ) : null}
                      </div>
                      <span className={`text-[11px] px-2 py-0.5 rounded-full border shrink-0 ${levelClass}`}>
                        {issue.level}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-text-secondary">
            No report available yet. Upload data to generate a quality report.
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
