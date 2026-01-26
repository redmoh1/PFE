
import React from 'react';
import { useAuth } from '../store/AuthContext';
import { Key, Shield, Bell, Globe, Database, ExternalLink } from 'lucide-react';

const Settings: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Organization Settings</h2>
        <p className="text-text-secondary">Manage your company profile, security policies, and automation webhooks.</p>
      </div>

      <div className="bg-card-light dark:bg-card-dark rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm divide-y divide-slate-100 dark:divide-slate-800">
        {/* Profile */}
        <div className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-400">
              <Globe size={20} />
            </div>
            <div>
              <h3 className="font-bold">Company Profile</h3>
              <p className="text-sm text-text-secondary">General information about your organization.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase text-text-secondary mb-1">Company Name</label>
              <input 
                type="text" 
                defaultValue={user?.company}
                className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary/10 transition-all bg-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-text-secondary mb-1">Organization ID</label>
              <input 
                type="text" 
                readOnly 
                value={`org_${btoa(user?.company || '').substring(0, 12)}`}
                className="w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-text-secondary font-mono text-xs cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* Webhooks / Automation */}
        <div className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary">
              <Key size={20} />
            </div>
            <div>
              <h3 className="font-bold">API & Automation Hooks</h3>
              <p className="text-sm text-text-secondary">Integrate InsightPro with external tools like n8n or Zapier.</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-bold">Data Upload Webhook</span>
                <span className="text-[10px] font-bold bg-success text-white px-1.5 py-0.5 rounded">ACTIVE</span>
              </div>
              <div className="flex gap-2">
                <code className="flex-1 bg-white dark:bg-slate-800 px-3 py-2 rounded border border-slate-200 dark:border-slate-700 text-xs text-text-secondary truncate">
                  https://api.insightpro.com/v1/hooks/ingest?token=sk_live_...
                </code>
                <button className="text-xs font-bold text-primary hover:underline px-2">Copy</button>
              </div>
            </div>
            <p className="text-xs text-text-secondary flex items-center gap-1">
              <ExternalLink size={12} />
              Read documentation on <a href="#" className="text-primary hover:underline">Automated ML Triggers</a>
            </p>
          </div>
        </div>

        {/* Data Persistence */}
        <div className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-400">
              <Database size={20} />
            </div>
            <div>
              <h3 className="font-bold">Data Management</h3>
              <p className="text-sm text-text-secondary">Control how long your historical data is retained.</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">Data Retention Policy</p>
              <p className="text-xs text-text-secondary">Current: 24 Months (Enterprise Standard)</p>
            </div>
            <select className="bg-transparent border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm">
               <option>12 Months</option>
               <option>24 Months</option>
               <option>36 Months</option>
               <option>Indefinite</option>
            </select>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end gap-3">
         <button className="px-6 py-2 rounded-xl text-sm font-bold text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 transition-all">Cancel</button>
         <button className="px-6 py-2 rounded-xl text-sm font-bold bg-primary text-white shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all">Save Changes</button>
      </div>
    </div>
  );
};

export default Settings;
