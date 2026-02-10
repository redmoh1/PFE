import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useAuthFetch } from '../store/AuthContext';
import { Plus, UploadCloud, Save, RefreshCw, Download } from 'lucide-react';

type InventoryItem = {
  product_name: string;
  current_stock: number | null;
  avg_daily_sales: number;
  days_left: number | null;
  status: 'OK' | 'WARNING' | 'ALERT' | 'DORMANT' | 'UNKNOWN' | string;
  advice: string;
  suggested_reorder_qty?: number | null;
};

type InventoryStatusResponse = {
  ok: boolean;
  source_file: string;
  count: number;
  items: InventoryItem[];
  thresholds?: {
    warning_days?: number;
    alert_days?: number;
    lead_time_days?: number;
    safety_days?: number;
  };
};

const pillClass = (status: string) => {
  switch (status) {
    case 'ALERT':
      return 'bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300';
    case 'WARNING':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300';
    case 'OK':
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300';
    case 'DORMANT':
      return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200';
    default:
      return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200';
  }
};

const Inventory: React.FC = () => {
  const authFetch = useAuthFetch();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const topRef = useRef<HTMLDivElement | null>(null);

  const notifyInventoryChanged = () => {
    // Allows Layout header badge to refresh immediately.
    window.dispatchEvent(new Event('inventory:changed'));
  };

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sourceFile, setSourceFile] = useState<string>('');
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [editedStock, setEditedStock] = useState<Record<string, string>>({});

  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'RISK' | 'ALERT' | 'WARNING' | 'OK' | 'DORMANT' | 'UNKNOWN'>('ALL');
  const [leadTimeDays, setLeadTimeDays] = useState('7');
  const [warningDays, setWarningDays] = useState('7');
  const [alertDays, setAlertDays] = useState('3');
  const [safetyDays, setSafetyDays] = useState('0');

  const [isAddOpen, setAddOpen] = useState(false);
  const [newProductName, setNewProductName] = useState('');
  const [newProductStock, setNewProductStock] = useState('0');

  const loadStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      const ld = Number(leadTimeDays);
      const wd = Number(warningDays);
      const ad = Number(alertDays);
      const sd = Number(safetyDays);
      if (Number.isFinite(ld)) params.set('lead_time_days', String(Math.max(0, Math.floor(ld))));
      if (Number.isFinite(wd)) params.set('warning_days', String(Math.max(0, Math.floor(wd))));
      if (Number.isFinite(ad)) params.set('alert_days', String(Math.max(0, Math.floor(ad))));
      if (Number.isFinite(sd)) params.set('safety_days', String(Math.max(0, Math.floor(sd))));

      const qs = params.toString();
      const res = await authFetch(`/inventory/status${qs ? `?${qs}` : ''}`, { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        console.error('[Inventory] /inventory/status failed', {
          url: res.url,
          status: res.status,
          contentType: res.headers.get('content-type'),
          body: text?.slice(0, 500),
        });
        throw new Error(text || 'Failed to load inventory status');
      }

      // Defensive: avoid "Unexpected token '<'" when server returns HTML.
      const raw = await res.text();
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('text/html') || raw.trim().startsWith('<!DOCTYPE') || raw.trim().startsWith('<html')) {
        console.error('[Inventory] Expected JSON but received HTML', {
          url: res.url,
          status: res.status,
          headers: Object.fromEntries(res.headers.entries()),
          body: raw.slice(0, 500),
        });
        throw new Error('Inventory API returned HTML instead of JSON. Check Vite proxy / API base URL.');
      }

      let payload: InventoryStatusResponse;
      try {
        payload = JSON.parse(raw) as InventoryStatusResponse;
      } catch (e) {
        console.error('[Inventory] Failed to parse JSON', {
          url: res.url,
          status: res.status,
          contentType,
          body: raw.slice(0, 500),
        });
        throw e;
      }
      setItems(payload.items || []);
      setSourceFile(payload.source_file || '');

      // If backend returns thresholds, reflect them.
      if (payload.thresholds) {
        if (payload.thresholds.lead_time_days !== undefined) setLeadTimeDays(String(payload.thresholds.lead_time_days));
        if (payload.thresholds.warning_days !== undefined) setWarningDays(String(payload.thresholds.warning_days));
        if (payload.thresholds.alert_days !== undefined) setAlertDays(String(payload.thresholds.alert_days));
        if (payload.thresholds.safety_days !== undefined) setSafetyDays(String(payload.thresholds.safety_days));
      }

      // Initialize edited values from persisted stock.
      const nextEdited: Record<string, string> = {};
      (payload.items || []).forEach((it) => {
        nextEdited[it.product_name] = it.current_stock === null || it.current_stock === undefined ? '' : String(it.current_stock);
      });
      setEditedStock(nextEdited);
    } catch (e: any) {
      setError(e?.message || 'Failed to load inventory');
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onFocus = (e: Event) => {
      const detail = (e as CustomEvent<any>)?.detail || {};
      const product = String(detail.product || '').trim();
      const status = String(detail.status || '').toUpperCase();

      if (product) setQuery(product);
      // If the notification is risk-oriented, show risk by default.
      if (status === 'ALERT' || status === 'WARNING') setStatusFilter('RISK');
      else setStatusFilter('ALL');

      window.setTimeout(() => {
        topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 0);
    };

    window.addEventListener('inventory:focus', onFocus as any);
    return () => window.removeEventListener('inventory:focus', onFocus as any);
  }, []);

  const filteredItems = useMemo(() => {
    const q = query.trim().toUpperCase();
    return items.filter((it) => {
      if (q && !it.product_name.toUpperCase().includes(q)) return false;
      if (statusFilter === 'ALL') return true;
      if (statusFilter === 'RISK') return it.status === 'ALERT' || it.status === 'WARNING';
      return it.status === statusFilter;
    });
  }, [items, query, statusFilter]);

  const hasChanges = useMemo(() => {
    // Compare editedStock with current items.
    const map = new Map(items.map((i) => [i.product_name, i.current_stock] as const));
    for (const [product, value] of Object.entries(editedStock) as Array<[string, string]>) {
      const current = map.get(product);
      const trimmed = value.trim();
      const parsed = trimmed === '' ? null : Number(trimmed);
      if (trimmed !== '' && (Number.isNaN(parsed) || parsed < 0)) return true; // invalid input counts as a change
      if ((current ?? null) !== (trimmed === '' ? null : parsed)) return true;
    }
    return false;
  }, [editedStock, items]);

  const saveStock = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const updateItems = (Object.entries(editedStock) as Array<[string, string]>)
        .map(([product_name, v]) => ({ product_name, v: v.trim() }))
        .filter((x) => x.v !== '')
        .map((x) => ({
          product_name: x.product_name,
          current_stock: Math.max(0, Math.floor(Number(x.v))),
        }))
        .filter((x) => Number.isFinite(x.current_stock));

      const res = await authFetch('/inventory/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: updateItems }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to update stock');
      }

      await loadStatus();
      notifyInventoryChanged();
    } catch (e: any) {
      setError(e?.message || 'Failed to update stock');
    } finally {
      setIsSaving(false);
    }
  };

  const addProduct = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const name = newProductName.trim();
      if (!name) throw new Error('Product name is required');

      const initial = Math.max(0, Math.floor(Number(newProductStock.trim() || '0')));
      if (!Number.isFinite(initial)) throw new Error('Initial stock must be a number');

      const res = await authFetch('/inventory/add-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_name: name, initial_stock: initial }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to add product');
      }

      setAddOpen(false);
      setNewProductName('');
      setNewProductStock('0');
      await loadStatus();
      notifyInventoryChanged();
    } catch (e: any) {
      setError(e?.message || 'Failed to add product');
    } finally {
      setIsSaving(false);
    }
  };

  const uploadInvoice = async (file: File) => {
    setIsSaving(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);

      const res = await authFetch('/inventory/upload-invoice', {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to upload invoice');
      }

      await loadStatus();
      notifyInventoryChanged();
    } catch (e: any) {
      setError(e?.message || 'Failed to upload invoice');
    } finally {
      setIsSaving(false);
    }
  };

  const exportReorderCsv = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('scope', 'RISK');
      params.set('lead_time_days', String(Math.max(0, Math.floor(Number(leadTimeDays) || 0))));
      params.set('warning_days', String(Math.max(0, Math.floor(Number(warningDays) || 0))));
      params.set('alert_days', String(Math.max(0, Math.floor(Number(alertDays) || 0))));
      params.set('safety_days', String(Math.max(0, Math.floor(Number(safetyDays) || 0))));

      const res = await authFetch(`/inventory/reorder-export?${params.toString()}`, { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to export CSV');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      a.download = `reorder_suggestions_${ts}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.message || 'Failed to export CSV');
    } finally {
      setIsSaving(false);
    }
  };

  const exportPurchaseOrderTemplate = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('scope', 'RISK');
      params.set('lead_time_days', String(Math.max(0, Math.floor(Number(leadTimeDays) || 0))));
      params.set('warning_days', String(Math.max(0, Math.floor(Number(warningDays) || 0))));
      params.set('alert_days', String(Math.max(0, Math.floor(Number(alertDays) || 0))));
      params.set('safety_days', String(Math.max(0, Math.floor(Number(safetyDays) || 0))));

      const res = await authFetch(`/inventory/purchase-order-template?${params.toString()}`, { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to export purchase order template');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      a.download = `purchase_order_template_${ts}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.message || 'Failed to export purchase order template');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6" ref={topRef}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Inventory Management</h2>
          <p className="text-sm text-text-secondary dark:text-text-secondaryDark">
            Detected products from sales + manual additions. Source: {sourceFile || '—'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 rounded-xl px-3 py-2">
            <span className="text-xs text-text-secondary dark:text-text-secondaryDark">Lead</span>
            <input
              value={leadTimeDays}
              onChange={(e) => setLeadTimeDays(e.target.value)}
              onBlur={() => loadStatus()}
              inputMode="numeric"
              className="w-14 bg-transparent outline-none text-sm"
              title="Lead time days"
            />
            <span className="text-xs text-text-secondary dark:text-text-secondaryDark">Warn</span>
            <input
              value={warningDays}
              onChange={(e) => setWarningDays(e.target.value)}
              onBlur={() => loadStatus()}
              inputMode="numeric"
              className="w-14 bg-transparent outline-none text-sm"
              title="Warning threshold days"
            />
            <span className="text-xs text-text-secondary dark:text-text-secondaryDark">Alert</span>
            <input
              value={alertDays}
              onChange={(e) => setAlertDays(e.target.value)}
              onBlur={() => loadStatus()}
              inputMode="numeric"
              className="w-14 bg-transparent outline-none text-sm"
              title="Alert threshold days"
            />
            <span className="text-xs text-text-secondary dark:text-text-secondaryDark">Safety</span>
            <input
              value={safetyDays}
              onChange={(e) => setSafetyDays(e.target.value)}
              onBlur={() => loadStatus()}
              inputMode="numeric"
              className="w-14 bg-transparent outline-none text-sm"
              title="Safety days"
            />
          </div>

          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/30 text-sm"
            placeholder="Search product…"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/30 text-sm"
            title="Filter by status"
          >
            <option value="RISK">ALERT + WARNING</option>
            <option value="ALL">All</option>
            <option value="ALERT">ALERT</option>
            <option value="WARNING">WARNING</option>
            <option value="OK">OK</option>
            <option value="DORMANT">DORMANT</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
          <button
            onClick={() => loadStatus()}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm"
            disabled={isLoading || isSaving}
          >
            <RefreshCw size={16} /> Refresh
          </button>

          <button
            onClick={() => setAddOpen(true)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-primary text-white text-sm hover:opacity-90"
            disabled={isSaving}
          >
            <Plus size={16} /> Add Product
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) uploadInvoice(f);
              e.target.value = '';
            }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-900 text-white text-sm hover:opacity-90 dark:bg-slate-100 dark:text-slate-900"
            disabled={isSaving}
          >
            <UploadCloud size={16} /> Upload Invoice
          </button>

          <button
            onClick={exportReorderCsv}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm"
            disabled={isSaving || isLoading}
            title="Download CSV of reorder suggestions (ALERT + WARNING)"
          >
            <Download size={16} /> Export Reorder CSV
          </button>

          <button
            onClick={exportPurchaseOrderTemplate}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm"
            disabled={isSaving || isLoading}
            title="Download a Purchase Order CSV template (add supplier & costs)"
          >
            <Download size={16} /> PO Template
          </button>

          <button
            onClick={saveStock}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-600 text-white text-sm hover:opacity-90 disabled:opacity-60"
            disabled={isSaving || isLoading || !hasChanges}
          >
            <Save size={16} /> Save / Update Stock
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900/30 text-text-secondary dark:text-text-secondaryDark">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Product</th>
                <th className="text-left px-4 py-3 font-semibold w-44">Current Stock</th>
                <th className="text-left px-4 py-3 font-semibold w-40">Avg Daily Sales</th>
                <th className="text-left px-4 py-3 font-semibold w-32">Days Left</th>
                <th className="text-left px-4 py-3 font-semibold w-44">Suggested Reorder</th>
                <th className="text-left px-4 py-3 font-semibold w-28">Status</th>
                <th className="text-left px-4 py-3 font-semibold">Seller Advice</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {isLoading ? (
                <tr>
                  <td className="px-4 py-6" colSpan={7}>
                    Loading inventory…
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td className="px-4 py-6" colSpan={7}>
                    No products match your filters. Upload sales data or add a product.
                  </td>
                </tr>
              ) : (
                filteredItems.map((it) => (
                  <tr key={it.product_name} className="hover:bg-slate-50 dark:hover:bg-slate-900/20">
                    <td className="px-4 py-3 font-medium">{it.product_name}</td>
                    <td className="px-4 py-3">
                      <input
                        value={editedStock[it.product_name] ?? ''}
                        onChange={(e) =>
                          setEditedStock((prev) => ({ ...prev, [it.product_name]: e.target.value }))
                        }
                        inputMode="numeric"
                        className="w-32 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/30"
                        placeholder="e.g. 25"
                      />
                    </td>
                    <td className="px-4 py-3">{Number(it.avg_daily_sales || 0).toFixed(2)}</td>
                    <td className="px-4 py-3">
                      {it.days_left === null || it.days_left === undefined ? '—' : it.days_left.toFixed(1)}
                    </td>
                    <td className="px-4 py-3">
                      {it.suggested_reorder_qty === null || it.suggested_reorder_qty === undefined
                        ? '—'
                        : it.suggested_reorder_qty}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${pillClass(it.status)}`}>
                        {it.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-secondary dark:text-text-secondaryDark">{it.advice}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setAddOpen(false)} />
          <div className="relative w-full max-w-lg bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 rounded-2xl p-5">
            <h3 className="text-lg font-bold">Add Product</h3>
            <p className="text-sm text-text-secondary dark:text-text-secondaryDark">
              Manually add a product if it’s not present in sales data.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Product name</label>
                <input
                  value={newProductName}
                  onChange={(e) => setNewProductName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/30"
                  placeholder="e.g. WHITE METAL LANTERN"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Initial stock</label>
                <input
                  value={newProductStock}
                  onChange={(e) => setNewProductStock(e.target.value)}
                  inputMode="numeric"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/30"
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                onClick={() => setAddOpen(false)}
                className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm"
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                onClick={addProduct}
                className="px-3 py-2 rounded-xl bg-primary text-white text-sm hover:opacity-90 disabled:opacity-60"
                disabled={isSaving}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {(isSaving || isLoading) && (
        <div className="text-xs text-text-secondary dark:text-text-secondaryDark">
          {isSaving ? 'Applying changes…' : ''}
        </div>
      )}
    </div>
  );
};

export default Inventory;
