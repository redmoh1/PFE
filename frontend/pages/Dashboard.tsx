
import React, { useEffect, useMemo, useState } from 'react';
import { useData } from '../store/DataContext';
import { useAuthFetch } from '../store/AuthContext';
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
  ShieldCheck,
  ExternalLink
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

type DashboardProps = {
  onNavigate?: (pageId: string) => void;
};

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const authFetch = useAuthFetch();
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
    isLoading,
    error,
    refreshData,
  } = useData();

  type NotificationItem = {
    id: string;
    type: 'ALERT' | 'WARNING' | 'INFO';
    product?: string | null;
    message: string;
    severity: number;
    created_at: string;
    read: boolean;
    meta?: {
      status?: string;
      days_left?: number | null;
      advice?: string;
      suggested_reorder_qty?: number | null;
      current_stock?: number | null;
      avg_daily_sales?: number | null;
      product_name?: string;
    };
  };

  const [alertItems, setAlertItems] = useState<NotificationItem[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);

  const loadActiveAlerts = async () => {
    setAlertsLoading(true);
    try {
      // SINGLE SOURCE OF TRUTH for active alerts.
      const res = await authFetch('/alerts/active', { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        console.error('[Dashboard] /alerts/active failed', { status: res.status, body: text?.slice(0, 300) });
        setAlertItems([]);
        return;
      }
      const payload = await res.json();
      const items = (payload?.items || []) as any[];
      // Map alert schema to the NotificationItem-like shape used by the UI.
      const mapped: NotificationItem[] = items.map((a) => ({
        id: String(a.id || `${a.status}:${a.product}`),
        type: a.status,
        product: a.product,
        message: a.reason || a.message || '',
        severity: a.status === 'ALERT' ? 3 : 2,
        created_at: a.created_at,
        read: false,
        meta: {
          status: a.status,
          days_left: a.days_left,
          advice: a.seller_advice,
          suggested_reorder_qty: a.meta?.suggested_reorder_qty,
          current_stock: a.meta?.current_stock,
          avg_daily_sales: a.meta?.avg_daily_sales,
          product_name: a.product,
        },
      }));
      setAlertItems(mapped);
    } catch {
      setAlertItems([]);
    } finally {
      setAlertsLoading(false);
    }
  };

  useEffect(() => {
    loadActiveAlerts();
    const onInventoryChanged = () => loadActiveAlerts();
    window.addEventListener('inventory:changed', onInventoryChanged);
    const intervalId = window.setInterval(loadActiveAlerts, 30000);
    return () => {
      window.removeEventListener('inventory:changed', onInventoryChanged);
      window.clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeAlertsSorted = useMemo(() => {
    return [...alertItems].sort((a, b) => (b.severity || 1) - (a.severity || 1));
  }, [alertItems]);

  const viewAlert = (n: NotificationItem) => {
    // No automatic redirects; only on user click.
    onNavigate?.('inventory');
    const product = String(n.product || n.meta?.product_name || '').trim();
    const status = String(n.meta?.status || n.type || '').toUpperCase();
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('inventory:focus', { detail: { product, status } }));
    }, 50);
  };

  const getInsightTargetPage = (insight: { title: string; description: string; reason: string; suggested_action: string }) => {
    const haystack = `${insight.title}\n${insight.description}\n${insight.reason}\n${insight.suggested_action}`.toLowerCase();

    if (/(forecast|predict|prediction|project|projection|prophet|توقع|تنبؤ)/.test(haystack)) return 'forecasting';
    if (/(segment|segmentation|rfm|cohort|تجزئة)/.test(haystack)) return 'segmentation';
    if (/(recommend|recommendation|cross-?sell|upsell|basket|apriori|association|توصية)/.test(haystack)) return 'recommendations';
    if (/(sentiment|review|feedback|nlp|مشاعر|آراء)/.test(haystack)) return 'sentiment';

    return 'sales';
  };

  const extractExplicitFilters = (text: string) => {
    const result: Partial<{ startDate: string; endDate: string; city: string; product: string }> = {};

    const cityMatch = text.match(/(?:^|\s)city\s*=\s*([^\s,;]+)/i);
    if (cityMatch?.[1]) result.city = decodeURIComponent(cityMatch[1]);

    const productMatch = text.match(/(?:^|\s)product\s*=\s*([^\s,;]+)/i);
    if (productMatch?.[1]) result.product = decodeURIComponent(productMatch[1]);

    const startMatch = text.match(/(?:^|\s)(?:start_date|startdate)\s*=\s*(\d{4}-\d{2}-\d{2})/i);
    if (startMatch?.[1]) result.startDate = startMatch[1];

    const endMatch = text.match(/(?:^|\s)(?:end_date|enddate)\s*=\s*(\d{4}-\d{2}-\d{2})/i);
    if (endMatch?.[1]) result.endDate = endMatch[1];

    return result;
  };

  const handleInsightInvestigate = (insight: { title: string; description: string; reason: string; suggested_action: string }) => {
    const target = getInsightTargetPage(insight);
    const combinedText = `${insight.title} ${insight.description} ${insight.reason} ${insight.suggested_action}`;
    const explicit = extractExplicitFilters(combinedText);
    if (Object.keys(explicit).length > 0) setFilters(explicit);
    onNavigate?.(target);
  };

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
      </div>

      <FiltersBar
        filters={filters}
        setFilters={setFilters}
        clearFilters={clearFilters}
        cityOptions={cityOptions}
        productOptions={productOptions}
      />

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
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
                    <div className="min-w-0">
                      <h4 className="font-bold leading-snug truncate">{insight.title}</h4>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {onNavigate ? (
                        <button
                          type="button"
                          onClick={() => handleInsightInvestigate(insight)}
                          className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 hover:border-primary/40 hover:text-primary transition-colors"
                        >
                          Investigate
                          <ExternalLink size={14} />
                        </button>
                      ) : null}
                      <span className={`text-[11px] px-2 py-0.5 rounded-full border ${badge}`}>
                        {insight.severity}
                      </span>
                    </div>
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

      {/* Active Alerts (explanation panel, non-intrusive) */}
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="text-lg font-bold">Active Alerts</h3>
            <p className="text-sm text-text-secondary dark:text-text-secondaryDark">
              Clear explanations of current stock risks. Choose what to open.
            </p>
          </div>
          <button
            onClick={loadActiveAlerts}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm"
            type="button"
            disabled={alertsLoading}
          >
            <RefreshCw size={16} /> Refresh
          </button>
        </div>

        {alertsLoading && (
          <p className="text-sm text-text-secondary dark:text-text-secondaryDark">Loading alerts…</p>
        )}

        {!alertsLoading && activeAlertsSorted.length === 0 && (
          <p className="text-sm text-text-secondary dark:text-text-secondaryDark">No active stock alerts.</p>
        )}

        {!alertsLoading && activeAlertsSorted.length > 0 && (
          <div className="space-y-3">
            {activeAlertsSorted.map((n) => {
              const daysLeft = n.meta?.days_left;
              const action = n.meta?.advice || '';
              const qty = n.meta?.suggested_reorder_qty;
              const pill =
                n.type === 'ALERT'
                  ? 'bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300'
                  : 'bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300';

              return (
                <div key={n.id} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${pill}`}>{n.type}</span>
                        <span className="text-sm font-semibold truncate">{n.product || n.meta?.product_name || 'Product'}</span>
                      </div>
                      <p className="text-sm text-text-secondary dark:text-text-secondaryDark">{n.message}</p>
                      <div className="mt-2 flex flex-wrap gap-3 text-xs text-text-secondary dark:text-text-secondaryDark">
                        <span>Why: demand vs stock threshold</span>
                        {daysLeft !== undefined && daysLeft !== null && <span>Days left: {daysLeft}</span>}
                        {qty !== undefined && qty !== null && <span>Suggested reorder: {qty}</span>}
                      </div>
                      {action && (
                        <p className="mt-2 text-xs text-text-secondary dark:text-text-secondaryDark">
                          Suggested action: <span className="font-semibold">{action}</span>
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => viewAlert(n)}
                      className="shrink-0 inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-primary text-white text-sm hover:opacity-90"
                      type="button"
                    >
                      <ExternalLink size={16} /> View
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
