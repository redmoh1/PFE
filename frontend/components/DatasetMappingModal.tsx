import React from 'react';
import { Loader2 } from 'lucide-react';
import { DatasetUploadPreparation, MappingFieldDefinition } from '../types';

interface DatasetMappingModalProps {
  session: DatasetUploadPreparation | null;
  mappingDraft: Record<string, string>;
  validationErrors: string[];
  validationWarnings: string[];
  saveMapping: boolean;
  isValidating: boolean;
  isConfirming: boolean;
  onMappingChange: (fieldKey: string, value: string) => void;
  onSaveMappingChange: (next: boolean) => void;
  onValidate: () => void;
  onConfirm: () => void;
  onBack: () => void;
  onCancel: () => void;
}


interface MappingFieldRowProps {
  field: MappingFieldDefinition;
  currentValue: string;
  columns: string[];
  takenColumns: Set<string>;
  disabled: boolean;
  onChange: (value: string) => void;
}

interface PreviewTableProps {
  columns: string[];
  rows: Record<string, any>[];
}

const RequiredBadge: React.FC<{ required: boolean }> = ({ required }) => {
  if (!required) {
    return <span className="text-xs font-medium text-slate-400 dark:text-slate-500">Optional</span>;
  }

  return (
    <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-600 dark:bg-rose-500/10 dark:text-rose-200">
      Required
    </span>
  );
};

const MappingFieldRow: React.FC<MappingFieldRowProps> = ({
  field,
  currentValue,
  columns,
  takenColumns,
  disabled,
  onChange,
}) => {
  return (
    <tr className="border-t border-slate-200 dark:border-slate-800">
      <td className="px-4 py-3.5 align-middle sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{field.label}</span>
          <RequiredBadge required={field.required} />
        </div>
      </td>
      <td className="px-4 py-3.5 sm:px-5">
        <select
          value={currentValue}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none transition-colors focus:border-slate-400 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        >
          <option value="">Select a column</option>
          {columns.map((column) => (
            <option key={column} value={column} disabled={takenColumns.has(column)}>
              {column}
            </option>
          ))}
        </select>
      </td>
    </tr>
  );
};

const PreviewTable: React.FC<PreviewTableProps> = ({ columns, rows }) => {
  const visibleColumns = columns;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50/80 dark:bg-slate-900/70">
            <tr>
              {visibleColumns.map((column) => (
                <th
                  key={column}
                  className="px-4 py-2.5 text-left text-xs font-medium text-slate-500 dark:text-slate-400"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr className="border-t border-slate-200 dark:border-slate-800">
                <td
                  colSpan={Math.max(visibleColumns.length, 1)}
                  className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400"
                >
                  No preview rows available.
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-t border-slate-200 dark:border-slate-800">
                  {visibleColumns.map((column) => (
                    <td
                      key={`${column}-${rowIndex}`}
                      className="max-w-[180px] px-4 py-2.5 text-sm text-slate-600 dark:text-slate-300"
                    >
                      <div className="truncate">{String(row[column] ?? '')}</div>
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const DatasetMappingModal: React.FC<DatasetMappingModalProps> = ({
  session,
  mappingDraft,
  validationErrors,
  validationWarnings,
  saveMapping,
  isValidating,
  isConfirming,
  onMappingChange,
  onSaveMappingChange,
  onConfirm,
  onCancel,
}) => {
  if (!session) return null;

  const previewRows = session.preview_rows.slice(0, 5);
  const requiredFields = session.fields.filter((field) => field.required);
  const mappedRequiredCount = requiredFields.filter((field) => Boolean(mappingDraft[field.key])).length;
  const requiredRemaining = Math.max(requiredFields.length - mappedRequiredCount, 0);
  const hasBlockingIssues = validationErrors.length > 0 || requiredRemaining > 0;
  const isBusy = isValidating || isConfirming;
  const confirmLabel = isConfirming ? 'Confirming...' : isValidating ? 'Checking...' : 'Confirm Mapping';
  const remainingMessage = requiredRemaining === 0
    ? 'All required fields are mapped.'
    : `Map ${requiredRemaining} more required field${requiredRemaining === 1 ? '' : 's'} to continue.`;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-[2px]">
      <div className="flex min-h-full items-center justify-center p-4 sm:p-6">
        <div className="flex max-h-[90vh] w-full max-w-[860px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.08)] dark:border-slate-800 dark:bg-slate-950">
          <div className="border-b border-slate-200 px-5 py-5 sm:px-6 dark:border-slate-800">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <h3 className="text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                  Map CSV Columns
                </h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Match each column from your file to the correct field in the platform schema.
                </p>
                <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{remainingMessage}</p>
              </div>

              <div className="shrink-0 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left sm:text-right dark:border-slate-800 dark:bg-slate-900">
                <div className="max-w-[240px] truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                  {session.file_name}
                </div>
                <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  {session.columns.length} columns • {previewRows.length} preview rows
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">
            <div className="space-y-5">
              {(validationErrors.length > 0 || validationWarnings.length > 0) && (
                <div className="space-y-3">
                  {validationErrors.length > 0 && (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-200">
                      <p className="font-medium">Please fix the following before continuing:</p>
                      <ul className="mt-2 space-y-1">
                        {validationErrors.map((error) => (
                          <li key={error}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {validationWarnings.length > 0 && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
                      <p className="font-medium">Notes</p>
                      <ul className="mt-2 space-y-1">
                        {validationWarnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <section className="space-y-3">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Mapping</h4>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {mappedRequiredCount}/{requiredFields.length} required fields mapped
                    </p>
                  </div>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-slate-50/80 dark:bg-slate-900/70">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 sm:px-5">
                            System Field
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 sm:px-5">
                            CSV Column
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {session.fields.map((field) => {
                          const currentValue = mappingDraft[field.key] || '';
                          const takenColumns = new Set(
                            Object.entries(mappingDraft)
                              .filter(([key, value]) => key !== field.key && Boolean(value))
                              .map(([, value]) => value),
                          );

                          return (
                            <MappingFieldRow
                              key={field.key}
                              field={field}
                              currentValue={currentValue}
                              columns={session.columns}
                              takenColumns={takenColumns}
                              disabled={isBusy}
                              onChange={(value) => onMappingChange(field.key, value)}
                            />
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </section>

              <section className="space-y-3">
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Preview</h4>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Showing the first {previewRows.length} rows from the uploaded file.
                  </p>
                </div>
                <PreviewTable columns={session.columns} rows={previewRows} />
              </section>

              <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
                <input
                  type="checkbox"
                  checked={saveMapping}
                  onChange={(event) => onSaveMappingChange(event.target.checked)}
                  disabled={isBusy}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
                />
                <span>Save this mapping for future uploads from the same company.</span>
              </label>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-5 py-4 sm:px-6 dark:border-slate-800">
            <button
              type="button"
              onClick={onCancel}
              disabled={isBusy}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isBusy || hasBlockingIssues}
              className="inline-flex min-w-[160px] items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              {isBusy && <Loader2 size={16} className="animate-spin" />}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DatasetMappingModal;
