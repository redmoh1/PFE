
import React, { useMemo, useState, useEffect } from 'react';
import { useData } from '../store/DataContext';
import { useAuth } from '../store/AuthContext';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE || '';

const SalesAnalytics: React.FC = () => {
  const { sales } = useData();
  const { user } = useAuth();
  const [productData, setProductData] = useState<any[]>([]);
  const [cityData, setCityData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;
      const headers = { 'X-Company-ID': user.company };

      try {
        const productsRes = await fetch(`${API_BASE}/api/top-products?limit=10`, { headers });
        if (productsRes.ok) {
          const data = await productsRes.json();
          setProductData(data.map((p: any) => ({ name: p.product_id, value: p.revenue })));
        }
      } catch (e) {
        console.error('Failed to fetch products:', e);
      }

      try {
        const citiesRes = await fetch(`${API_BASE}/api/top-cities?limit=10`, { headers });
        if (citiesRes.ok) {
          const data = await citiesRes.json();
          setCityData(data.map((c: any) => ({ name: c.city, value: c.revenue })));
        }
      } catch (e) {
        console.error('Failed to fetch cities:', e);
      }
    };
    fetchData();
  }, [user]);

  const COLORS = ['#2563EB', '#64748B', '#22C55E', '#F59E0B', '#EF4444'];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-2xl font-bold tracking-tight">Sales Analytics</h2>
        <p className="text-text-secondary">Granular breakdown of revenue by product, category, and region.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Product Performance */}
        <div className="lg:col-span-2 bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue by Product</h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={productData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12}} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Regional Breakdown */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="text-lg font-bold mb-6">Revenue by City</h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={cityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {cityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              {cityData.map((city, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                    <span className="text-text-secondary">{city.name}</span>
                  </div>
                  <span className="font-semibold">${(city.value as number).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
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
