
import React, { useEffect, useMemo, useState } from 'react';
import { useData } from '../store/DataContext';
import { useAuth } from '../store/AuthContext';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye, RefreshCw, Trash2, ArchiveRestore } from 'lucide-react';
import { DatasetMeta, DatasetPreview } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '';

const DataUpload: React.FC = () => {
  const { uploadData, isProcessing, refreshData, resetAllAnalytics } = useData();
  const { user } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetType, setDatasetType] = useState<'sales' | 'customers' | 'reviews'>('sales');
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string>('');
  const [datasets, setDatasets] = useState<DatasetMeta[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);

  const companyHeaders = useMemo(() => {
    if (!user) return {};
    return { 'X-Company-ID': user.company };
  }, [user]);

  const loadDatasets = async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/datasets`, { headers: { ...companyHeaders } });
      if (!res.ok) throw new Error('Failed to load datasets');
      const data = (await res.json()) as DatasetMeta[];
      setDatasets(data);
    } catch (error) {
      console.error(error);
      setMessage('Unable to load datasets');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, [user]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.csv')) {
        setSelectedFile(file);
        setUploadStatus('idle');
      } else {
        alert('Please upload a CSV file.');
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !user) return;
    setUploadStatus('uploading');
    setMessage('');

    const formData = new FormData();
    formData.append('dataset_type', datasetType);
    formData.append('file', selectedFile);

    try {
      const res = await fetch(`${API_BASE}/api/datasets/upload`, {
        method: 'POST',
        headers: { ...companyHeaders },
        body: formData
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
      }

      // Reload dataset list
      await loadDatasets();
      
      // CRITICAL: Refresh all analytics data from server to get fresh pipeline results
      console.log('[DataUpload] Upload complete - refreshing all analytics data...');
      await refreshData();
      
      setUploadStatus('success');
      setMessage('Dataset uploaded successfully. Analytics pipeline completed. Dashboard updated with fresh data.');
      setSelectedFile(null);
    } catch (error) {
      console.error(error);
      setUploadStatus('error');
      const errorMsg = error instanceof Error ? error.message : 'Upload failed';
      setMessage(errorMsg);
    }
  };

  const handleReplace = async (datasetId: number, file: File) => {
    if (!user) return;
    setIsLoading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/replace`, {
        method: 'POST',
        headers: { ...companyHeaders },
        body: formData
      });
      if (!res.ok) throw new Error('Replace failed');
      
      // Reload dataset list
      await loadDatasets();
      
      // CRITICAL: Refresh all analytics data from server
      console.log('[DataUpload] Replace complete - refreshing all analytics data...');
      await refreshData();
      
      setMessage('Dataset replaced. Previous version archived. Analytics regenerated with new data.');
    } catch (error) {
      console.error(error);
      setMessage('Replace failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget || !user) return;
    setIsLoading(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${deleteTarget}`, {
        method: 'DELETE',
        headers: { ...companyHeaders },
      });
      if (!res.ok) throw new Error('Delete failed');
      
      // Reload dataset list
      await loadDatasets();
      
      // CRITICAL: Reset all analytics state immediately (no stale data)
      resetAllAnalytics();
      
      // Refresh analytics data from server (will get 204s for empty state)
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
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/preview`, {
        headers: { ...companyHeaders },
      });
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

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-bold tracking-tight">Data Ingestion</h2>
        <p className="text-text-secondary max-w-xl mx-auto">
          Upload your business datasets to trigger the automated ML pipeline. Our system handles cleaning, feature engineering, and retraining automatically.
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
          { title: 'Sales Activity', file: 'sales.csv', req: 'Required', desc: 'Transaction history, dates, and amounts.' },
          { title: 'Customer List', file: 'customers.csv', req: 'Optional', desc: 'Demographics and profile information.' },
          { title: 'Product Reviews', file: 'reviews.csv', req: 'Optional', desc: 'Raw text for Customer Feedback.' },
        ].map((item, i) => (
          <div key={i} className="bg-card-light dark:bg-card-dark p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm relative group">
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
          {uploadStatus === 'idle' && (
            <>
              <div className="p-4 bg-primary/10 rounded-2xl text-primary">
                <Upload size={40} />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold">Drag and drop your file</h3>
                <p className="text-text-secondary mt-1">or click to browse from computer (CSV only)</p>
                <div className="mt-4 flex flex-col sm:flex-row items-center gap-3 justify-center">
                  <label className="text-sm font-semibold text-text-secondary">Dataset Type</label>
                  <select
                    value={datasetType}
                    onChange={(e) => setDatasetType(e.target.value as 'sales' | 'customers' | 'reviews')}
                    className="border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm bg-transparent"
                  >
                    <option value="sales">Sales</option>
                    <option value="customers">Customers</option>
                    <option value="reviews">Reviews</option>
                  </select>
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
                <div className="flex items-center gap-2 text-sm font-medium animate-in zoom-in">
                  <FileText size={16} className="text-primary" />
                  <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                  <button 
                    onClick={handleUpload}
                    className="ml-4 bg-slate-900 text-white px-4 py-2 rounded-lg text-xs hover:bg-slate-800 transition-all"
                  >
                    Upload & Process
                  </button>
                </div>
              )}
            </>
          )}

          {(uploadStatus === 'uploading' || isProcessing) && (
            <div className="text-center space-y-6">
              <Loader2 className="animate-spin text-primary mx-auto" size={48} />
              <div>
                <h3 className="text-xl font-bold">Processing Dataset...</h3>
                <div className="mt-4 space-y-2 max-w-xs mx-auto">
                   <div className="flex items-center gap-2 text-sm text-text-secondary animate-pulse">
                     <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                     Cleaning inconsistent data
                   </div>
                   <div className="flex items-center gap-2 text-sm text-text-secondary delay-75 animate-pulse">
                     <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                     Engineering RFM features
                   </div>
                   <div className="flex items-center gap-2 text-sm text-text-secondary delay-150 animate-pulse">
                     <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                     Retraining Forecast models
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
                <h3 className="text-2xl font-bold">Pipeline Complete!</h3>
                <p className="text-text-secondary mt-1">Your dashboard has been updated with new insights.</p>
              </div>
              <button 
                onClick={() => setUploadStatus('idle')}
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
                <h3 className="text-2xl font-bold">Validation Failed</h3>
                <p className="text-text-secondary mt-1">{message || 'Your CSV is missing required columns.'}</p>
                <p className="text-xs text-text-secondary mt-2 max-w-md mx-auto">
                  Required: <strong>id/orderid</strong>, <strong>date/orderdate</strong>, <strong>amount/totalprice</strong>, <strong>product</strong>, <strong>city/location</strong>
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
            <p className="text-sm text-text-secondary">One active dataset per type per company. Replacements archive the previous version automatically.</p>
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
              {datasets.map((ds) => (
                <tr key={ds.id} className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors">
                  <td className="px-4 py-3 font-semibold capitalize">{ds.dataset_type}</td>
                  <td className="px-4 py-3">{ds.file_name}</td>
                  <td className="px-4 py-3">{ds.row_count.toLocaleString()}</td>
                  <td className="px-4 py-3 text-text-secondary">{new Date(ds.uploaded_at).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${ds.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                      {ds.is_active ? 'Active' : 'Archived'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handlePreview(ds.id)}
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
                          onChange={(e) => {
                            if (e.target.files && e.target.files[0]) {
                              handleReplace(ds.id, e.target.files[0]);
                              e.target.value = '';
                            }
                          }}
                        />
                      </label>
                      <button
                        onClick={() => setDeleteTarget(ds.id)}
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
                    {preview.columns.map((col) => (
                      <th key={col} className="px-3 py-2 text-left text-xs uppercase tracking-wide text-text-secondary">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, idx) => (
                    <tr key={idx} className="border-t border-slate-100 dark:border-slate-800">
                      {preview.columns.map((col) => (
                        <td key={col} className="px-3 py-2 whitespace-nowrap text-xs text-text-secondary">{row[col]}</td>
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
    </div>
  );
};

export default DataUpload;
