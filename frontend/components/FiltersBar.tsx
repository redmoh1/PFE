import React from 'react';
import { Filter, RotateCcw, GitCompare } from 'lucide-react';
import { AnalyticsFilters } from '../types';

interface FiltersBarProps {
  filters: AnalyticsFilters;
  setFilters: (next: Partial<AnalyticsFilters>) => void;
  clearFilters: () => void;
  cityOptions: string[];
  productOptions: string[];
}

const FiltersBar: React.FC<FiltersBarProps> = ({
  filters,
  setFilters,
  clearFilters,
  cityOptions,
  productOptions,
}) => {
  const canCompare = Boolean(filters.startDate && filters.endDate);

  const previousRange = React.useMemo(() => {
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

  return (
    <div className="bg-card-light dark:bg-card-dark p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-secondary dark:text-text-secondaryDark">
          <Filter size={18} />
          Filters
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 flex-1">
          <label className="text-xs text-text-secondary dark:text-text-secondaryDark">
            Start date
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ startDate: e.target.value })}
              className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm"
            />
          </label>

          <label className="text-xs text-text-secondary dark:text-text-secondaryDark">
            End date
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ endDate: e.target.value })}
              className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm"
            />
          </label>

          <label className="text-xs text-text-secondary dark:text-text-secondaryDark">
            City
            <select
              value={filters.city}
              onChange={(e) => setFilters({ city: e.target.value })}
              className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm"
            >
              <option value="">All</option>
              {cityOptions.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs text-text-secondary dark:text-text-secondaryDark">
            Product
            <select
              value={filters.product}
              onChange={(e) => setFilters({ product: e.target.value })}
              className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm"
            >
              <option value="">All</option>
              {productOptions.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs text-text-secondary dark:text-text-secondaryDark">
            Compare
            <button
              type="button"
              disabled={!canCompare}
              onClick={() => setFilters({ comparePrevious: !filters.comparePrevious })}
              className={`mt-1 w-full px-3 py-2 rounded-xl border text-sm flex items-center justify-center gap-2 transition\
                ${canCompare
                  ? 'border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 hover:bg-slate-50 dark:hover:bg-slate-900/40'
                  : 'border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/10 text-slate-400 cursor-not-allowed'}`}
              title={canCompare ? 'Toggle previous-period comparison' : 'Select start and end dates to compare'}
            >
              <GitCompare size={16} />
              {filters.comparePrevious ? 'On' : 'Off'}
            </button>
          </label>
        </div>

        <button
          type="button"
          onClick={clearFilters}
          className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-800 text-sm font-semibold text-text-secondary hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center gap-2"
        >
          <RotateCcw size={16} />
          Reset
        </button>
      </div>

      {!canCompare && filters.comparePrevious && (
        <div className="mt-3 text-xs text-warning">
          Comparison requires both start and end dates.
        </div>
      )}

      {filters.comparePrevious && canCompare && previousRange && (
        <div className="mt-3 text-xs text-text-secondary dark:text-text-secondaryDark">
          Comparing to previous period: <span className="font-semibold">{previousRange.startDate}</span> →{' '}
          <span className="font-semibold">{previousRange.endDate}</span>
        </div>
      )}
    </div>
  );
};

export default FiltersBar;
