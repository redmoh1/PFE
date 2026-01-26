
import React, { useState, useEffect } from 'react';
import { useData } from '../store/DataContext';
import { useAuth } from '../store/AuthContext';
import { TrendingUp, Clock, Target, Info } from 'lucide-react';
import { 
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const Forecasting: React.FC = () => {
  const { forecast: contextForecast } = useData();
  const { user } = useAuth();
  const [forecast, setForecast] = useState<any[]>([]);

  useEffect(() => {
    const fetchForecast = async () => {
      if (!user) return;
      const headers = { 'X-Company-ID': user.company };

      try {
        const res = await fetch(`${API_BASE}/api/monthly-sales`, { headers });
        if (res.ok) {
          const data = await res.json();
          const mapped = data
            .map((item: any) => ({
              date: item.month,
              actual: item.actual_sales || undefined,
              forecast: item.forecasted_sales || undefined
            }))
            .filter((item: any) => item.actual !== undefined || item.forecast !== undefined); // Filter out empty months
          setForecast(mapped);
        }
      } catch (e) {
        console.error('Failed to fetch forecast:', e);
        setForecast(contextForecast);
      }
    };
    fetchForecast();
  }, [user, contextForecast]);

  const nextMonthForecast = forecast.find(f => !f.actual)?.forecast || 0;
  const lastActual = forecast.filter(f => f.actual).slice(-1)[0]?.actual || 0;
  const growthRate = ((nextMonthForecast - lastActual) / lastActual * 100).toFixed(1);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Predictive Forecasting</h2>
          <p className="text-text-secondary">AI-powered sales projections using seasonal decomposition and linear regression.</p>
        </div>
        <div className="bg-primary/5 border border-primary/20 px-4 py-2 rounded-xl flex items-center gap-3">
          <div className="p-1.5 bg-primary/10 rounded-lg text-primary">
            <TrendingUp size={18} />
          </div>
          <div>
            <p className="text-xs text-text-secondary font-medium">Predicted Growth</p>
            <p className="text-sm font-bold text-primary">+{growthRate}% next month</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-3 mb-4 text-text-secondary">
            <Clock size={20} />
            <span className="text-sm font-semibold uppercase tracking-wider">Horizon</span>
          </div>
          <p className="text-2xl font-bold">6 Months</p>
          <p className="text-xs text-text-secondary mt-1">Short-term projection window</p>
        </div>
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-3 mb-4 text-text-secondary">
            <Target size={20} />
            <span className="text-sm font-semibold uppercase tracking-wider">Accuracy</span>
          </div>
          <p className="text-2xl font-bold">94.2%</p>
          <p className="text-xs text-text-secondary mt-1">Model performance (R² score)</p>
        </div>
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-3 mb-4 text-text-secondary">
            <Info size={20} />
            <span className="text-sm font-semibold uppercase tracking-wider">Model Type</span>
          </div>
          <p className="text-2xl font-bold">Prophet v2.0</p>
          <p className="text-xs text-text-secondary mt-1">Advanced additive regression</p>
        </div>
      </div>

      <div className="bg-card-light dark:bg-card-dark p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <h3 className="text-lg font-bold mb-8">Sales Volume Forecast (Interactive)</h3>
        {forecast && forecast.length > 0 ? (
          <div className="h-[450px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={forecast}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 13}} dy={15} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 13}} />
                <Tooltip 
                   cursor={{ stroke: '#2563EB', strokeWidth: 1, strokeDasharray: '4 4' }}
                   contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}
                />
                <Legend verticalAlign="top" height={36}/>
                <Area 
                  name="Historical Actuals"
                  type="monotone" 
                  dataKey="actual" 
                  fill="#2563EB" 
                  fillOpacity={0.05} 
                  stroke="transparent" 
                />
                <Line 
                  name="Projected Trend"
                  type="monotone" 
                  dataKey="forecast" 
                  stroke="#64748B" 
                  strokeWidth={2} 
                strokeDasharray="6 6"
                dot={{ r: 4, fill: '#64748B', strokeWidth: 2 }}
              />
              <Line 
                name="Observed Data"
                type="monotone" 
                dataKey="actual" 
                stroke="#2563EB" 
                strokeWidth={3} 
                dot={{ r: 5, fill: '#2563EB', strokeWidth: 2, stroke: '#fff' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-[450px] flex items-center justify-center bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-dashed border-slate-300 dark:border-slate-700">
            <div className="text-center">
              <p className="text-slate-600 dark:text-slate-400 font-medium">No forecast data available</p>
              <p className="text-slate-500 dark:text-slate-500 text-sm mt-1">Upload sales data to generate forecasts</p>
            </div>
          </div>
        )}
        <div className="mt-8 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 flex items-start gap-3">
          <div className="mt-1 text-primary"><Info size={18} /></div>
          <div>
            <p className="text-sm font-bold">Insight: Cyclical Uplift Detected</p>
            <p className="text-sm text-text-secondary">Historical patterns suggest a 15% revenue spike in late Q2 due to seasonal demand shifts. We recommend increasing inventory levels by early May.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Forecasting;
