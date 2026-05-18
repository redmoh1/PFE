
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye, RefreshCw, Trash2, ArchiveRestore } from 'lucide-react';
import DatasetMappingModal from '../components/DatasetMappingModal';
import { useData } from '../store/DataContext';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import {
  Branch,
  DatasetMappingConfirmResponse,
  DatasetMappingValidationResponse,
  DatasetMeta,
  DatasetPreview,
  DatasetUploadPreparation,
  isCompanyAdminRole,
} from '../types';

type DatasetType = 'sales' | 'customers' | 'reviews';
type UploadStatus = 'idle' | 'preparing' | 'processing' | 'success' | 'error';
type MappingAction = 'idle' | 'validating' | 'confirming';

const allowedDatasetTypes: DatasetType[] = ['sales', 'customers', 'reviews'];

const buildInitialMappingDraft = (session: DatasetUploadPreparation | null): Record<string, string> => {
  if (!session) return {};
  return session.fields.reduce<Record<string, string>>((accumulator, field) => {
    accumulator[field.key] = session.initial_mapping[field.key] ?? '';
    return accumulator;
  }, {});
};

const normalizeMappingDraft = (
  session: DatasetUploadPreparation | null,
  mappingDraft: Record<string, string>,
): Record<string, string | null> => {
  if (!session) return {};
  return session.fields.reduce<Record<string, string | null>>((accumulator, field) => {
    const value = mappingDraft[field.key];
    accumulator[field.key] = value ? value : null;
    return accumulator;
  }, {});
};

const toDatasetType = (value: string): DatasetType => {
  return allowedDatasetTypes.includes(value as DatasetType) ? (value as DatasetType) : 'sales';
};

const extractResponseMessage = async (response: Response): Promise<{ message: string; errors?: string[]; warnings?: string[] }> => {
  const payload = await response.json().catch(() => null) as any;
  const detail = payload?.detail;

  if (typeof detail === 'string') {
    return { message: detail };
  }

  if (detail && typeof detail === 'object') {
    const errors = Array.isArray(detail.errors) ? detail.errors.map((item: unknown) => String(item)) : undefined;
    const warnings = Array.isArray(detail.warnings) ? detail.warnings.map((item: unknown) => String(item)) : undefined;
    if (errors && errors.length > 0) {
      return { message: errors.join(' '), errors, warnings };
    }
    if (typeof detail.message === 'string') {
      return { message: detail.message, errors, warnings };
    }
  }

  if (typeof payload?.message === 'string') {
    return { message: payload.message };
  }

  return { message: `Request failed with status ${response.status}` };
};

const DataUpload: React.FC = () => {
  const { isProcessing, refreshData, resetAllAnalytics } = useData();
  const { user, selectedBranchId, setSelectedBranchId } = useAuth();
  const authFetch = useAuthFetch();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetType, setDatasetType] = useState<DatasetType>('sales');
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [message, setMessage] = useState<string>('');
  const [datasets, setDatasets] = useState<DatasetMeta[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [mappingSession, setMappingSession] = useState<DatasetUploadPreparation | null>(null);
  const [mappingDraft, setMappingDraft] = useState<Record<string, string>>({});
  const [mappingErrors, setMappingErrors] = useState<string[]>([]);
  const [mappingWarnings, setMappingWarnings] = useState<string[]>([]);
  const [mappingAction, setMappingAction] = useState<MappingAction>('idle');
  const [saveMapping, setSaveMapping] = useState<boolean>(true);
  const loadRequestIdRef = useRef(0);
  const activeBranches = branches.filter((branch) => String(branch.status || '').toLowerCase() === 'active');

  const loadBranches = useCallback(async (requestId?: number) => {
    if (!user) return;
    try {
      const res = await authFetch('/api/branches', { cache: 'no-store' });
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      if (!res.ok) {
        setBranches([]);
        return;
      }
      const data = (await res.json()) as Branch[];
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      setBranches(data);
    } catch {
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      setBranches([]);
    }
  }, [user, authFetch]);

  const loadDatasets = useCallback(async (requestId?: number) => {
    if (!user) return;
    setIsLoading(true);
    try {
      const res = await authFetch('/api/datasets', { cache: 'no-store' });
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      if (!res.ok) throw new Error('Failed to load datasets');
      const data = (await res.json()) as DatasetMeta[];
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      setDatasets(data);
    } catch (error) {
      if (requestId !== undefined && loadRequestIdRef.current !== requestId) return;
      console.error(error);
      setMessage('Unable to load datasets');
    } finally {
      if (requestId === undefined || loadRequestIdRef.current === requestId) {
        setIsLoading(false);
      }
    }
  }, [user, authFetch]);

  useEffect(() => {
    if (!user) {
      setDatasets([]);
      setBranches([]);
      return;
    }

    const requestId = loadRequestIdRef.current + 1;
    loadRequestIdRef.current = requestId;
    void loadDatasets(requestId);
    void loadBranches(requestId);
  }, [user, selectedBranchId, loadDatasets, loadBranches]);

  useEffect(() => {
    if (!isCompanyAdminRole(user?.role) || user?.branchId || !selectedBranchId) return;
    const stillActive = activeBranches.some((branch) => String(branch.id) === selectedBranchId);
    if (!stillActive) {
      setSelectedBranchId('');
    }
  }, [user?.role, user?.branchId, selectedBranchId, activeBranches, setSelectedBranchId]);

  const beginMappingFlow = useCallback((session: DatasetUploadPreparation, file: File | null) => {
    setMappingSession(session);
    setMappingDraft(buildInitialMappingDraft(session));
    setMappingErrors([]);
    setMappingWarnings([]);
    setSaveMapping(true);
    setSelectedFile(file);
    setUploadStatus('idle');
    if (session.mapping_source === 'saved_profile') {
      setMessage('A previous mapping was loaded for review. Confirm it manually before processing.');
    } else {
      setMessage('Review the detected columns and confirm the manual mapping to continue.');
    }
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || !event.target.files[0]) return;
    const file = event.target.files[0];
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadStatus('error');
      setMessage('Please upload a CSV file.');
      return;
    }
    setSelectedFile(file);
    setUploadStatus('idle');
    setMessage('');
  };

  const prepareUploadFlow = useCallback(async (file: File, nextDatasetType: DatasetType, replaceDatasetId?: number) => {
    if (!user) return;
    if (isCompanyAdminRole(user.role) && !selectedBranchId && !user.branchId) {
      setUploadStatus('error');
      setMessage('Please select a branch before uploading as admin.');
      return;
    }

    setUploadStatus('preparing');
    setMessage('');
    setMappingErrors([]);
    setMappingWarnings([]);

    const formData = new FormData();
    if (replaceDatasetId === undefined) {
      formData.append('dataset_type', nextDatasetType);
    }
    formData.append('file', file);

    try {
      const endpoint = replaceDatasetId === undefined ? '/api/datasets/upload' : `/api/datasets/${replaceDatasetId}/replace`;
      const res = await authFetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const { message: errorMessage } = await extractResponseMessage(res);
        throw new Error(errorMessage);
      }

      const prepared = (await res.json()) as DatasetUploadPreparation;
      beginMappingFlow(prepared, replaceDatasetId === undefined ? file : null);
    } catch (error) {
      console.error(error);
      setUploadStatus('error');
      setMessage(error instanceof Error ? error.message : 'Upload preparation failed');
    }
  }, [authFetch, beginMappingFlow, selectedBranchId, user, user?.branchId]);

  const validateCurrentMapping = useCallback(async (): Promise<boolean> => {
    if (!mappingSession) return false;
    setMappingAction('validating');
    try {
      const res = await authFetch('/api/datasets/upload/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: mappingSession.upload_id,
          mapping: normalizeMappingDraft(mappingSession, mappingDraft),
        }),
      });

      if (!res.ok) {
        const { message: errorMessage, errors, warnings } = await extractResponseMessage(res);
        setMappingErrors(errors || [errorMessage]);
        setMappingWarnings(warnings || []);
        return false;
      }

      const validation = (await res.json()) as DatasetMappingValidationResponse;
      setMappingErrors(validation.errors || []);
      setMappingWarnings(validation.warnings || []);
      return validation.valid;
    } catch (error) {
      console.error(error);
      setMappingErrors([error instanceof Error ? error.message : 'Mapping validation failed']);
      setMappingWarnings([]);
      return false;
    } finally {
      setMappingAction('idle');
    }
  }, [authFetch, mappingDraft, mappingSession]);

  const handleConfirmMapping = useCallback(async () => {
    if (!mappingSession || !user) return;
    const isValid = await validateCurrentMapping();
    if (!isValid) {
      setUploadStatus('error');
      setMessage('Complete the required mapping fields before processing the dataset.');
      return;
    }

    setUploadStatus('processing');
    setMappingAction('confirming');

    try {
      const res = await authFetch('/api/datasets/upload/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: mappingSession.upload_id,
          mapping: normalizeMappingDraft(mappingSession, mappingDraft),
          save_mapping: saveMapping,
        }),
      });

      if (!res.ok) {
        const { message: errorMessage, errors, warnings } = await extractResponseMessage(res);
        setMappingErrors(errors || []);
        setMappingWarnings(warnings || []);
        throw new Error(errorMessage);
      }

      await res.json() as DatasetMappingConfirmResponse;
      await loadDatasets();
      await refreshData();

      const wasReplace = Boolean(mappingSession.replace_dataset_id);
      setMappingSession(null);
      setMappingDraft({});
      setMappingErrors([]);
      setMappingWarnings([]);
      setSelectedFile(null);
      setUploadStatus('success');
      setMessage(
        wasReplace
          ? 'Dataset replaced after manual mapping confirmation. Analytics were regenerated with the standardized schema.'
          : 'Dataset mapped successfully. Analytics pipeline completed and the dashboard has been refreshed.',
      );
    } catch (error) {
      console.error(error);
      setUploadStatus('error');
      setMessage(error instanceof Error ? error.message : 'Mapping confirmation failed');
    } finally {
      setMappingAction('idle');
    }
  }, [authFetch, loadDatasets, mappingDraft, mappingSession, refreshData, saveMapping, user, validateCurrentMapping]);

  const handleDelete = async () => {
    if (!deleteTarget || !user) return;
    setIsLoading(true);
    setMessage('');
    try {
      const res = await authFetch(`/api/datasets/${deleteTarget}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Delete failed');

      await loadDatasets();
      resetAllAnalytics();
      await refreshData();

      setMessage('Dataset deleted successfully. All derived analytics have been cleared.');
    } catch (error) {
      console.error(error);
      setMessage('Delete failed.');
    } finally {
      setIsLoading(false);
      setDeleteTarget(null);
    }
  };

  const handlePreview = async (datasetId: number) => {
    if (!user) return;
    setPreviewLoading(true);
    try {
      const res = await authFetch(`/api/datasets/${datasetId}/preview`, { cache: 'no-store' });
      if (!res.ok) throw new Error('Preview failed');
      const data = (await res.json()) as DatasetPreview;
      setPreview(data);
    } catch (error) {
      console.error(error);
      setMessage('Preview failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const cancelStagedUpload = useCallback(async (uploadId?: string) => {
    if (!uploadId) return;

    try {
      await authFetch('/api/datasets/upload/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id: uploadId }),
      });
    } catch (error) {
      console.error('Failed to cancel staged upload:', error);
    }
  }, [authFetch]);

  const resetMappingState = useCallback((options?: { preserveSelectedFile?: boolean; nextMessage?: string }) => {
    setMappingSession(null);
    setMappingDraft({});
    setMappingErrors([]);
    setMappingWarnings([]);
    if (!options?.preserveSelectedFile) {
      setSelectedFile(null);
    }
    setUploadStatus('idle');
    if (options?.nextMessage) {
      setMessage(options.nextMessage);
    }
  }, []);

  const handleBackFromMapping = useCallback(async () => {
    const uploadId = mappingSession?.upload_id;
    const canReturnToUpload = Boolean(selectedFile) && !mappingSession?.replace_dataset_id;

    resetMappingState({
      preserveSelectedFile: canReturnToUpload,
      nextMessage: canReturnToUpload
        ? 'Returned to the upload step. You can adjust the file or dataset type and reopen mapping.'
        : 'Returned from mapping review. No processing was started.',
    });

    await cancelStagedUpload(uploadId);
  }, [cancelStagedUpload, mappingSession?.replace_dataset_id, mappingSession?.upload_id, resetMappingState, selectedFile]);

  const handleCancelMapping = useCallback(async () => {
    const uploadId = mappingSession?.upload_id;
    resetMappingState({ nextMessage: 'Upload inspection canceled. No processing was started.' });
    await cancelStagedUpload(uploadId);
  }, [cancelStagedUpload, mappingSession?.upload_id, resetMappingState]);

  const processingState = uploadStatus === 'processing' || isProcessing;
  const preparingState = uploadStatus === 'preparing';

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold tracking-tight">Data Ingestion</h2>
        <p className="text-text-secondary max-w-2xl mx-auto">
          Upload a CSV file, review the detected columns, map them to the platform schema manually, then launch the analytics pipeline.
        </p>
        {message && (
          <div className="mt-4 text-sm bg-slate-900 text-white px-4 py-3 rounded-xl inline-flex items-center gap-2 shadow-md">
            <Sparkles size={16} />
            <span>{message}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { title: 'Sales Activity', file: 'sales.csv', req: 'Required', desc: 'Transaction history, dates, product names, and sales amounts.' },
          { title: 'Customer List', file: 'customers.csv', req: 'Optional', desc: 'Customer identifiers, names, and location data.' },
          { title: 'Product Reviews', file: 'reviews.csv', req: 'Optional', desc: 'Raw review text and optional rating context for sentiment analysis.' },
        ].map((item) => (
          <div key={item.title} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm relative group">
            <div className="absolute -top-2 -right-2 bg-primary text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-sm">
              {item.req}
            </div>
            <h4 className="font-bold mb-1">{item.title}</h4>
            <p className="text-xs text-text-secondary mb-4">Sample: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">{item.file}</code></p>
            <p className="text-sm text-text-secondary">{item.desc}</p>
          </div>
        ))}
      </div>

      <div className={`bg-card-light dark:bg-card-dark p-12 rounded-3xl border-2 border-dashed transition-all ${
        uploadStatus === 'idle' ? 'border-slate-200 dark:border-slate-800' :
        uploadStatus === 'success' ? 'border-success bg-success/5' :
        uploadStatus === 'error' ? 'border-error bg-error/5' : 'border-primary bg-primary/5'
      }`}>
        <div className="flex flex-col items-center justify-center space-y-6">
          {!preparingState && !processingState && uploadStatus === 'idle' && (
            <>
              <div className="p-4 bg-primary/10 rounded-2xl text-primary">
                <Upload size={40} />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold">Upload a CSV, then confirm the mapping</h3>
                <p className="text-text-secondary mt-1">Processing stays locked until the manual mapping step is completed.</p>
                <div className="mt-4 flex flex-col sm:flex-row items-center gap-3 justify-center">
                  <label className="text-sm font-semibold text-text-secondary">Dataset Type</label>
                  <select
                    value={datasetType}
                    onChange={(event) => setDatasetType(event.target.value as DatasetType)}
                    className="border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-transparent"
                  >
                    <option value="sales">Sales</option>
                    <option value="customers">Customers</option>
                    <option value="reviews">Reviews</option>
                  </select>
                  {isCompanyAdminRole(user?.role) && !user?.branchId && (
                    <>
                      <label className="text-sm font-semibold text-text-secondary">Upload CSV for branch</label>
                      <select
                        value={selectedBranchId}
                        onChange={(event) => setSelectedBranchId(event.target.value)}
                        className="border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-transparent"
                      >
                        <option value="">Select Branch</option>
                        {activeBranches.map((branch) => (
                          <option key={branch.id} value={String(branch.id)}>{branch.name}</option>
                        ))}
                      </select>
                    </>
                  )}
                </div>
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="bg-primary text-white px-8 py-3 rounded-xl font-bold hover:bg-primary/90 transition-all cursor-pointer shadow-lg shadow-primary/20"
              >
                Select CSV File
              </label>
              {selectedFile && (
                <div className="flex flex-wrap items-center justify-center gap-3 text-sm font-medium animate-in zoom-in">
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-primary" />
                    <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  <div className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                    Manual mapping required
                  </div>
                  <button
                    onClick={() => void prepareUploadFlow(selectedFile, datasetType)}
                    disabled={isCompanyAdminRole(user?.role) && !selectedBranchId && !user?.branchId}
                    className="bg-slate-900 text-white px-4 py-2 rounded-lg text-xs hover:bg-slate-800 transition-all"
                  >
                    Upload & Map Columns
                  </button>
                </div>
              )}
            </>
          )}

          {preparingState && (
            <div className="text-center space-y-6">
              <Loader2 className="animate-spin text-primary mx-auto" size={48} />
              <div>
                <h3 className="text-xl font-bold">Analyzing CSV Structure...</h3>
                <div className="mt-4 space-y-2 max-w-xs mx-auto">
                  <div className="flex items-center gap-2 text-sm text-text-secondary animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Reading uploaded file safely
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-secondary delay-75 animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Extracting detected columns
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-secondary delay-150 animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Preparing mapping suggestions
                  </div>
                </div>
              </div>
            </div>
          )}

          {processingState && (
            <div className="text-center space-y-6">
              <Loader2 className="animate-spin text-primary mx-auto" size={48} />
              <div>
                <h3 className="text-xl font-bold">Applying Mapping & Processing Dataset...</h3>
                <div className="mt-4 space-y-2 max-w-xs mx-auto">
                  <div className="flex items-center gap-2 text-sm text-text-secondary animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Converting CSV to the standardized internal schema
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-secondary delay-75 animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Running branch-scoped analytics pipeline
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-secondary delay-150 animate-pulse">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                    Refreshing the dashboard with the latest outputs
                  </div>
                </div>
              </div>
            </div>
          )}

          {uploadStatus === 'success' && (
            <div className="text-center space-y-4 animate-in zoom-in">
              <div className="p-4 bg-success/20 rounded-full text-success mx-auto w-fit">
                <CheckCircle2 size={48} />
              </div>
              <div>
                <h3 className="text-2xl font-bold">Mapping Confirmed!</h3>
                <p className="text-text-secondary mt-1">The dataset was standardized and the dashboard has been refreshed.</p>
              </div>
              <button
                onClick={() => {
                  setUploadStatus('idle');
                  setMessage('');
                }}
                className="bg-slate-900 text-white px-8 py-3 rounded-xl font-bold hover:bg-slate-800 transition-all mt-4"
              >
                Upload Another
              </button>
            </div>
          )}

          {uploadStatus === 'error' && (
            <div className="text-center space-y-4 animate-in shake">
              <div className="p-4 bg-error/20 rounded-full text-error mx-auto w-fit">
                <AlertCircle size={48} />
              </div>
              <div>
                <h3 className="text-2xl font-bold">Mapping or Upload Failed</h3>
                <p className="text-text-secondary mt-1 max-w-xl mx-auto">{message || 'The CSV could not be prepared or confirmed for processing.'}</p>
                <p className="text-xs text-text-secondary mt-2 max-w-md mx-auto">
                  Upload inspection, manual mapping, and validation must succeed before the analytics pipeline can start.
                </p>
              </div>
              <button
                onClick={() => setUploadStatus('idle')}
                className="bg-error text-white px-8 py-3 rounded-xl font-bold hover:bg-error/90 transition-all mt-4"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="bg-card-light dark:bg-card-dark p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold">Uploaded Datasets</h3>
            <p className="text-sm text-text-secondary">One active dataset per type per company. Replacements now pass through the same manual mapping workflow.</p>
          </div>
          {isLoading && <Loader2 className="animate-spin text-primary" size={24} />}
        </div>

        <div className="overflow-hidden border border-slate-100 dark:border-slate-800 rounded-2xl">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-900/50 text-left text-xs uppercase tracking-wide text-text-secondary">
              <tr>
                <th className="px-4 py-3">Dataset Type</th>
                <th className="px-4 py-3">File Name</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Uploaded At</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasets.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-text-secondary" colSpan={6}>No datasets uploaded yet.</td>
                </tr>
              )}
              {datasets.map((dataset) => (
                <tr key={dataset.id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors">
                  <td className="px-4 py-3 font-semibold capitalize">{dataset.dataset_type}</td>
                  <td className="px-4 py-3">{dataset.file_name}</td>
                  <td className="px-4 py-3">{dataset.row_count.toLocaleString()}</td>
                  <td className="px-4 py-3 text-text-secondary">{new Date(dataset.uploaded_at).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${dataset.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                      {dataset.is_active ? 'Active' : 'Archived'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handlePreview(dataset.id)}
                        className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary text-sm flex items-center gap-2"
                      >
                        <Eye size={16} /> View
                      </button>
                      <label className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary text-sm flex items-center gap-2 cursor-pointer">
                        <RefreshCw size={16} /> Replace
                        <input
                          type="file"
                          accept=".csv"
                          className="hidden"
                          onChange={(event) => {
                            if (event.target.files && event.target.files[0]) {
                              void prepareUploadFlow(event.target.files[0], toDatasetType(dataset.dataset_type), dataset.id);
                              event.target.value = '';
                            }
                          }}
                        />
                      </label>
                      <button
                        onClick={() => setDeleteTarget(dataset.id)}
                        className="px-3 py-2 rounded-lg border border-error/30 text-error hover:bg-error/5 text-sm flex items-center gap-2"
                      >
                        <Trash2 size={16} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {previewLoading && (
          <div className="mt-4 flex items-center gap-2 text-sm text-text-secondary">
            <Loader2 className="animate-spin text-primary" size={16} /> Loading preview...
          </div>
        )}
      </div>

      {preview && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 w-full max-w-5xl rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xl font-bold">Preview: {preview.file_name}</h4>
                <p className="text-sm text-text-secondary">{preview.row_count.toLocaleString()} rows • {preview.columns.length} columns • {preview.dataset_type}</p>
              </div>
              <button onClick={() => setPreview(null)} className="text-text-secondary hover:text-primary">Close</button>
            </div>
            <div className="overflow-auto border border-slate-200 dark:border-slate-800 rounded-xl max-h-[420px]">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-900/50">
                  <tr>
                    {preview.columns.map((column) => (
                      <th key={column} className="px-3 py-2 text-left text-xs uppercase tracking-wide text-text-secondary">{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-t border-slate-100 dark:border-slate-800">
                      {preview.columns.map((column) => (
                        <td key={column} className="px-3 py-2 whitespace-nowrap text-xs text-text-secondary">{row[column]}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-text-secondary">Showing first {preview.rows.length} rows (max {50}).</p>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <ArchiveRestore className="text-error" />
              <div>
                <h4 className="text-lg font-bold">Delete dataset?</h4>
                <p className="text-sm text-text-secondary">This will archive and remove access. Active datasets deletion will trigger retraining.</p>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded-lg border border-slate-200">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 rounded-lg bg-error text-white hover:bg-error/90">Delete</button>
            </div>
          </div>
        </div>
      )}

      <DatasetMappingModal
        session={mappingSession}
        mappingDraft={mappingDraft}
        validationErrors={mappingErrors}
        validationWarnings={mappingWarnings}
        saveMapping={saveMapping}
        isValidating={mappingAction === 'validating'}
        isConfirming={mappingAction === 'confirming'}
        onMappingChange={(fieldKey, value) => {
          setMappingDraft((current) => ({ ...current, [fieldKey]: value }));
          setMappingErrors([]);
          setMappingWarnings([]);
        }}
        onSaveMappingChange={setSaveMapping}
        onValidate={() => {
          void validateCurrentMapping();
        }}
        onConfirm={() => {
          void handleConfirmMapping();
        }}
        onBack={() => {
          void handleBackFromMapping();
        }}
        onCancel={() => {
          void handleCancelMapping();
        }}
      />
    </div>
  );
};

export default DataUpload;
