
import React, { useMemo, useState, useEffect } from 'react';
import { useData } from '../store/DataContext';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import FiltersBar from '../components/FiltersBar';
import { AlertCircle, Info, Loader2, RefreshCw } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie
} from 'recharts';

type ComparisonDatum = {
  name: string;
  value: number;
  previousValue?: number;
  deltaPct?: number | null;
};

const formatMoney = (n: number) => `$${n.toLocaleString()}`;
const formatDeltaPct = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;

const ComparisonTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0]?.payload as ComparisonDatum | undefined;
  if (!p) return null;

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 shadow-sm">
      <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[240px]">{label ?? p.name}</div>
      <div className="mt-1 text-xs text-slate-700 dark:text-slate-300 space-y-0.5">
        <div className="flex justify-between gap-6"><span>Current</span><span className="font-semibold">{formatMoney(p.value)}</span></div>
        <div className="flex justify-between gap-6"><span>Previous</span><span className="font-semibold">{typeof p.previousValue === 'number' ? formatMoney(p.previousValue) : '—'}</span></div>
        <div className="flex justify-between gap-6"><span>Δ</span><span className="font-semibold">{typeof p.deltaPct === 'number' ? formatDeltaPct(p.deltaPct) : '—'}</span></div>
      </div>
    </div>
  );
};

const SalesAnalytics: React.FC = () => {
  const { sales, filters, setFilters, clearFilters, cityOptions, productOptions, isLoading, error, refreshData } = useData();
  const { user } = useAuth();
  const authFetch = useAuthFetch();
  const [productData, setProductData] = useState<ComparisonDatum[]>([]);
  const [cityData, setCityData] = useState<ComparisonDatum[]>([]);
  const [previousProductData, setPreviousProductData] = useState<ComparisonDatum[]>([]);
  const [previousCityData, setPreviousCityData] = useState<ComparisonDatum[]>([]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={40} className="animate-spin text-primary" />
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
            className="mt-3 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition inline-flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  const canCompare = Boolean(filters.startDate && filters.endDate);
  const previousRange = useMemo(() => {
    if (!canCompare) return null;

    const start = new Date(`${filters.startDate}T00:00:00Z`);
    const end = new Date(`${filters.endDate}T00:00:00Z`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;

    const msPerDay = 24 * 60 * 60 * 1000;
    const periodLengthDays = Math.floor((end.getTime() - start.getTime()) / msPerDay);
    const prevEnd = new Date(start.getTime() - msPerDay);
    const prevStart = new Date(prevEnd.getTime() - periodLengthDays * msPerDay);

    const toYmd = (d: Date) => d.toISOString().slice(0, 10);
    return { startDate: toYmd(prevStart), endDate: toYmd(prevEnd) };
  }, [canCompare, filters.startDate, filters.endDate]);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;

      const params = new URLSearchParams();
      params.set('limit', '10');
      if (filters.startDate) params.set('start_date', filters.startDate);
      if (filters.endDate) params.set('end_date', filters.endDate);
      if (filters.city) params.set('city', filters.city);
      if (filters.product) params.set('product', filters.product);

      try {
        const productsRes = await authFetch(`/api/top-products?${params.toString()}`, { cache: 'no-store' });
        if (productsRes.ok) {
          const data = await productsRes.json();
          setProductData(data.map((p: any) => ({ name: String(p.product_id), value: Number(p.revenue) || 0 })));
        } else if (productsRes.status === 204) {
          setProductData([]);
        }
      } catch (e) {
        console.error('Failed to fetch products:', e);
        setProductData([]);
      }

      try {
        const citiesRes = await authFetch(`/api/top-cities?${params.toString()}`, { cache: 'no-store' });
        if (citiesRes.ok) {
          const data = await citiesRes.json();
          setCityData(data.map((c: any) => ({ name: String(c.city), value: Number(c.revenue) || 0 })));
        } else if (citiesRes.status === 204) {
          setCityData([]);
        }
      } catch (e) {
        console.error('Failed to fetch cities:', e);
        setCityData([]);
      }

      // Previous period fetch (optional)
      if (filters.comparePrevious && canCompare && previousRange) {
        const prevParams = new URLSearchParams();
        prevParams.set('limit', '10');
        prevParams.set('start_date', previousRange.startDate);
        prevParams.set('end_date', previousRange.endDate);
        if (filters.city) prevParams.set('city', filters.city);
        if (filters.product) prevParams.set('product', filters.product);

        try {
          const prevProductsRes = await authFetch(`/api/top-products?${prevParams.toString()}`, { cache: 'no-store' });
          if (prevProductsRes.ok) {
            const data = await prevProductsRes.json();
            setPreviousProductData(data.map((p: any) => ({ name: String(p.product_id), value: Number(p.revenue) || 0 })));
          } else {
            setPreviousProductData([]);
          }
        } catch (e) {
          console.error('Failed to fetch previous products:', e);
          setPreviousProductData([]);
        }

        try {
          const prevCitiesRes = await authFetch(`/api/top-cities?${prevParams.toString()}`, { cache: 'no-store' });
          if (prevCitiesRes.ok) {
            const data = await prevCitiesRes.json();
            setPreviousCityData(data.map((c: any) => ({ name: String(c.city), value: Number(c.revenue) || 0 })));
          } else {
            setPreviousCityData([]);
          }
        } catch (e) {
          console.error('Failed to fetch previous cities:', e);
          setPreviousCityData([]);
        }
      } else {
        setPreviousProductData([]);
        setPreviousCityData([]);
      }
    };
    fetchData();
  }, [user, authFetch, filters, canCompare, previousRange]);

  const productDataWithComparison = useMemo<ComparisonDatum[]>(() => {
    const prevMap = new Map(previousProductData.map((p) => [p.name, p.value] as const));
    return productData.map((p) => {
      const prev = prevMap.get(p.name);
      const deltaPct = typeof prev === 'number' && prev !== 0 ? ((p.value - prev) / prev) * 100 : null;
      return { ...p, previousValue: prev, deltaPct };
    });
  }, [productData, previousProductData]);

  const cityDataWithComparison = useMemo<ComparisonDatum[]>(() => {
    const prevMap = new Map(previousCityData.map((c) => [c.name, c.value] as const));
    return cityData.map((c) => {
      const prev = prevMap.get(c.name);
      const deltaPct = typeof prev === 'number' && prev !== 0 ? ((c.value - prev) / prev) * 100 : null;
      return { ...c, previousValue: prev, deltaPct };
    });
  }, [cityData, previousCityData]);

  const topCityRows = useMemo(() => {
    return [...cityDataWithComparison].sort((a, b) => b.value - a.value).slice(0, 8);
  }, [cityDataWithComparison]);

  const COLORS = ['#2563EB', '#64748B', '#22C55E', '#F59E0B', '#EF4444'];

  const cityColorByName = useMemo(() => {
    const map = new Map<string, string>();
    cityDataWithComparison.forEach((c, idx) => {
      map.set(c.name, COLORS[idx % COLORS.length]);
    });
    return map;
  }, [cityDataWithComparison, COLORS]);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-2xl font-bold tracking-tight">Sales Analytics</h2>
        <p className="text-text-secondary">Granular breakdown of revenue by product, category, and region.</p>
        <div className="mt-2 flex items-start gap-2 text-xs text-text-secondary dark:text-text-secondaryDark max-w-2xl">
          <Info size={14} className="mt-0.5 text-primary/80" />
          <p>Metrics are aggregated from transaction records; comparison mode computes period-over-period deltas for quicker benchmarking.</p>
        </div>
      </div>

      <FiltersBar
        filters={filters}
        setFilters={setFilters}
        clearFilters={clearFilters}
        cityOptions={cityOptions}
        productOptions={productOptions}
      />

      {filters.comparePrevious && canCompare && previousRange && (
        <div className="text-xs text-text-secondary dark:text-text-secondaryDark bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-2">
          Comparison mode is enabled: <span className="font-semibold">{previousRange.startDate}</span> →{' '}
          <span className="font-semibold">{previousRange.endDate}</span>. Tooltips and the city legend show deltas vs the previous period.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Product Performance */}
        <div className="lg:col-span-2 bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue by Product</h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={productDataWithComparison}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                <Tooltip content={<ComparisonTooltip />} />
                <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {filters.comparePrevious && canCompare && previousRange && (
            <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div className="px-4 py-2 text-xs font-semibold bg-slate-50 dark:bg-slate-900/40 text-text-secondary dark:text-text-secondaryDark">
                Top products comparison (current vs previous)
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-text-secondary dark:text-text-secondaryDark bg-white/60 dark:bg-slate-900/10">
                    <tr>
                      <th className="text-left px-4 py-2 font-semibold">Product</th>
                      <th className="text-right px-4 py-2 font-semibold">Current</th>
                      <th className="text-right px-4 py-2 font-semibold">Previous</th>
                      <th className="text-right px-4 py-2 font-semibold">Δ</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {productDataWithComparison.slice(0, 8).map((p) => (
                      <tr key={p.name} className="bg-white/40 dark:bg-transparent">
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: '#2563EB' }}
                            />
                            <span className="truncate max-w-[260px]">{p.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2 text-right font-semibold">{formatMoney(p.value)}</td>
                        <td className="px-4 py-2 text-right">{typeof p.previousValue === 'number' ? formatMoney(p.previousValue) : '—'}</td>
                        <td className={`px-4 py-2 text-right font-semibold ${typeof p.deltaPct === 'number' ? (p.deltaPct >= 0 ? 'text-success' : 'text-error') : 'text-text-secondary dark:text-text-secondaryDark'}`}>
                          {typeof p.deltaPct === 'number' ? formatDeltaPct(p.deltaPct) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Regional Breakdown */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue by City</h3>

          {/* Pie chart (fixed height) */}
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={cityDataWithComparison}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {cityDataWithComparison.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ComparisonTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend (normal flow; card grows to fit) */}
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
            {cityDataWithComparison.map((city, idx) => (
              <div key={`${city.name}-${idx}`} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                  />
                  <div className="min-w-0">
                    <div className="text-text-secondary truncate min-w-0">{city.name}</div>
                    {filters.comparePrevious && canCompare && previousRange && typeof city.deltaPct === 'number' && (
                      <div className={`text-[11px] ${city.deltaPct >= 0 ? 'text-success' : 'text-error'}`}>
                        {formatDeltaPct(city.deltaPct)} vs prev
                      </div>
                    )}
                  </div>
                </div>
                <span className="font-semibold shrink-0">{formatMoney(city.value)}</span>
              </div>
            ))}
          </div>

          {filters.comparePrevious && canCompare && previousRange && (
            <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div className="px-4 py-2 text-xs font-semibold bg-slate-50 dark:bg-slate-900/40 text-text-secondary dark:text-text-secondaryDark">
                Top cities comparison (current vs previous)
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-text-secondary dark:text-text-secondaryDark bg-white/60 dark:bg-slate-900/10">
                    <tr>
                      <th className="text-left px-4 py-2 font-semibold">City</th>
                      <th className="text-right px-4 py-2 font-semibold">Current</th>
                      <th className="text-right px-4 py-2 font-semibold">Previous</th>
                      <th className="text-right px-4 py-2 font-semibold">Δ</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {topCityRows.map((c) => (
                      <tr key={c.name} className="bg-white/40 dark:bg-transparent">
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: cityColorByName.get(c.name) ?? '#94A3B8' }}
                            />
                            <span className="truncate max-w-[260px]">{c.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2 text-right font-semibold">{formatMoney(c.value)}</td>
                        <td className="px-4 py-2 text-right">{typeof c.previousValue === 'number' ? formatMoney(c.previousValue) : '—'}</td>
                        <td className={`px-4 py-2 text-right font-semibold ${typeof c.deltaPct === 'number' ? (c.deltaPct >= 0 ? 'text-success' : 'text-error') : 'text-text-secondary dark:text-text-secondaryDark'}`}>
                          {typeof c.deltaPct === 'number' ? formatDeltaPct(c.deltaPct) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Sales Logs */}
      <div className="bg-card-light dark:bg-card-dark rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
          <h3 className="text-lg font-bold">Transaction History ({sales.length} records)</h3>
          <button className="text-sm text-primary font-medium hover:underline">Export CSV</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900/50 text-text-secondary">
              <tr>
                <th className="p-4 font-semibold">Order ID</th>
                <th className="p-4 font-semibold">Date</th>
                <th className="p-4 font-semibold">Product</th>
                <th className="p-4 font-semibold">City</th>
                <th className="p-4 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {sales.slice(0, 10).map((sale) => (
                <tr key={sale.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="p-4 font-mono text-xs">{sale.id}</td>
                  <td className="p-4">{sale.date}</td>
                  <td className="p-4 font-medium">{sale.product}</td>
                  <td className="p-4">{sale.city}</td>
                  <td className="p-4 text-right font-bold">${sale.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SalesAnalytics;
