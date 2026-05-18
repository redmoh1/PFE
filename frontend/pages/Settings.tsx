
import React, { useEffect, useState } from 'react';
import { useAuth, useAuthFetch } from '../store/AuthContext';
import { Branch, isBranchAdminRole, isCompanyAdminRole } from '../types';

type UserOption = { id: string; name: string; role: string };

const Settings: React.FC = () => {
  const { user } = useAuth();
  const authFetch = useAuthFetch();
  const isAdmin = isCompanyAdminRole(user?.role);
  const isBranchAdmin = isBranchAdminRole(user?.role);

  const [branches, setBranches] = useState<Branch[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Branch | null>(null);
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [phone, setPhone] = useState('');
  const [branchStatus, setBranchStatus] = useState('Active');

  // Edit Manager state
  const [emOpen, setEmOpen] = useState(false);
  const [emUserId, setEmUserId] = useState('');
  const [emName, setEmName] = useState('');
  const [emEmail, setEmEmail] = useState('');
  const [emPhone, setEmPhone] = useState('');
  const [emPassword, setEmPassword] = useState('');

  // Branch Manager creation state
  const [bmOpen, setBmOpen] = useState(false);
  const [bmName, setBmName] = useState('');
  const [bmEmail, setBmEmail] = useState('');
  const [bmPhone, setBmPhone] = useState('');
  const [bmPassword, setBmPassword] = useState('');
  const [bmBranchId, setBmBranchId] = useState('');

  if (!isAdmin) {
    return (
      <div className="max-w-3xl mx-auto rounded-3xl border border-slate-200 dark:border-slate-800 bg-card-light dark:bg-card-dark p-8">
        <h2 className="text-2xl font-bold tracking-tight">Branch Management</h2>
        <p className="mt-3 text-sm text-text-secondary">
          Company settings are available to company administrators only. Branch administrators remain limited to branch-scoped operations.
        </p>
      </div>
    );
  }

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [branchesRes, usersRes] = await Promise.all([
        authFetch('/api/branches', { cache: 'no-store' }),
        authFetch('/api/users', { cache: 'no-store' }),
      ]);

      if (!branchesRes.ok) throw new Error('Failed to load branches');
      const branchesPayload = (await branchesRes.json()) as Branch[];
      setBranches(Array.isArray(branchesPayload) ? branchesPayload : []);

      if (usersRes.ok) {
        const usersPayload = (await usersRes.json()) as UserOption[];
        setUsers(Array.isArray(usersPayload) ? usersPayload : []);
      } else {
        setUsers([]);
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load branch data');
      setBranches([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => {
    setEditing(null);
    setName('');
    setCity('');
    setPhone('');
    setBranchStatus('Active');
    setOpen(true);
  };

  const openEdit = (branch: Branch) => {
    setEditing(branch);
    setName(branch.name || '');
    setCity(branch.city || '');
    setPhone(branch.phone || '');
    setBranchStatus(branch.status || 'Active');
    setOpen(true);
  };

  const saveBranch = async () => {
    const payload: Record<string, any> = {
      name: name.trim(),
      city: city.trim(),
      phone: phone.trim() || null,
      is_active: branchStatus === 'Active',
    };
    if (!payload.name || !payload.city) {
      setError('Branch name and city are required');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const endpoint = editing ? `/api/branches/${editing.id}` : '/api/branches';
      const method = editing ? 'PUT' : 'POST';
      const res = await authFetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'Failed to save branch');
      }
      setOpen(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to save branch');
    } finally {
      setLoading(false);
    }
  };

  const deleteBranch = async (branchId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/branches/${branchId}`, { method: 'DELETE' });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'Failed to delete branch');
      }
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete branch');
    } finally {
      setLoading(false);
    }
  };

  const openEditManager = (branch: Branch) => {
    if (!branch.manager) return;
    setEmUserId(branch.manager.id);
    setEmName(branch.manager.name || '');
    setEmEmail(branch.manager.email || '');
    setEmPhone(branch.manager.phone || '');
    setEmPassword('');
    setEmOpen(true);
  };

  const saveEditManager = async () => {
    if (!emName.trim() || !emEmail.trim()) {
      setError('Name and email are required');
      return;
    }
    if (emPassword && emPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, string> = {
        name: emName.trim(),
        email: emEmail.trim(),
      };
      if (emPhone.trim()) body.phone = emPhone.trim();
      if (emPassword) body.password = emPassword;
      const res = await authFetch(`/api/users/${emUserId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const txt = await res.text();
        let msg = 'Failed to update manager';
        try { msg = JSON.parse(txt).detail || msg; } catch {}
        throw new Error(msg);
      }
      setEmOpen(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to update manager');
    } finally {
      setLoading(false);
    }
  };

  const openBmModal = () => {
    setBmName('');
    setBmEmail('');
    setBmPhone('');
    setBmPassword('');
    setBmBranchId('');
    setBmOpen(true);
  };

  const saveBranchManager = async () => {
    if (!bmName.trim() || !bmEmail.trim() || !bmPassword || !bmBranchId) {
      setError('All fields are required');
      return;
    }
    if (bmPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/users/create-branch-manager', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: bmName.trim(),
          email: bmEmail.trim(),
          phone: bmPhone.trim() || undefined,
          password: bmPassword,
          branch_id: Number(bmBranchId),
        }),
      });
      if (!res.ok) {
        const txt = await res.text();
        let msg = 'Failed to create branch manager';
        try { msg = JSON.parse(txt).detail || msg; } catch {}
        throw new Error(msg);
      }
      setBmOpen(false);
      await loadData();
    } catch (e: any) {
      setError(e?.message || 'Failed to create branch manager');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Branch Management</h2>
          <p className="text-sm text-text-secondary">Manage company branches and managers.</p>
        </div>
        {isAdmin && (
          <div className="inline-flex gap-2">
            <button
              onClick={openBmModal}
              className="px-4 py-2 rounded-xl bg-green-600 text-white text-sm font-semibold hover:bg-green-700"
            >
              Add Branch Manager
            </button>
            <button
              onClick={openCreate}
              className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary/90"
            >
              Add Branch
            </button>
          </div>
        )}
      </div>

      {isBranchAdmin && !isAdmin && (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-text-secondary">
          Branch administrators can manage branch-scoped data only. Company-wide branch settings are hidden.
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-error/30 bg-error/5 text-error px-4 py-3 text-sm">{error}</div>
      )}

      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-card-light dark:bg-card-dark shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-900/50 text-left text-xs uppercase tracking-wide text-text-secondary">
            <tr>
              <th className="px-4 py-3">Branch</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Branch Phone</th>
              <th className="px-4 py-3">Manager Name</th>
              <th className="px-4 py-3">Manager Email</th>
              <th className="px-4 py-3">Manager Phone</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {branches.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-text-secondary" colSpan={8}>
                  {loading ? 'Loading branches…' : 'No branches found.'}
                </td>
              </tr>
            )}
            {branches.map((branch) => (
              <tr key={branch.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-4 py-3 font-semibold">{branch.name}</td>
                <td className="px-4 py-3">{branch.city}</td>
                <td className="px-4 py-3 text-xs text-text-secondary">{branch.phone || '—'}</td>
                <td className="px-4 py-3 font-medium">{branch.manager?.name || branch.manager_name || <span className="text-text-secondary">—</span>}</td>
                <td className="px-4 py-3 text-xs text-text-secondary">{branch.manager?.email ? <a href={`mailto:${branch.manager.email}`} className="hover:text-primary transition-colors">{branch.manager.email}</a> : '—'}</td>
                <td className="px-4 py-3 text-xs text-text-secondary">{branch.manager?.phone || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${branch.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                    {branch.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {isAdmin ? (
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        onClick={() => openEdit(branch)}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:border-primary hover:text-primary transition-colors"
                      >
                        Edit Branch
                      </button>
                      {branch.manager && (
                        <button
                          onClick={() => openEditManager(branch)}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 hover:border-primary hover:text-primary transition-colors"
                        >
                          Edit Manager
                        </button>
                      )}
                      <button
                        onClick={() => deleteBranch(branch.id)}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium border border-error/30 text-error hover:bg-error/5 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  ) : (
                    <span className="text-text-secondary text-xs">View only</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="w-full max-w-lg rounded-2xl bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 p-6 space-y-4">
            <h3 className="text-lg font-bold">{editing ? 'Edit Branch' : 'Add Branch'}</h3>
            {editing?.manager && (
              <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2 text-sm">
                <span className="text-text-secondary">Manager:</span>{' '}
                <span className="font-medium">{editing.manager.name}</span>
              </div>
            )}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">Branch Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">City</label>
                <input
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Phone <span className="opacity-60">(optional)</span></label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="+213555111222"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Status</label>
                <select
                  value={branchStatus}
                  onChange={(e) => setBranchStatus(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                >
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={saveBranch}
                className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {emOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="w-full max-w-lg rounded-2xl bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 p-6 space-y-4">
            <h3 className="text-lg font-bold">Edit Branch Manager</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">Name</label>
                <input
                  value={emName}
                  onChange={(e) => setEmName(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Email</label>
                <input
                  type="email"
                  value={emEmail}
                  onChange={(e) => setEmEmail(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Phone <span className="opacity-60">(optional)</span></label>
                <input
                  type="tel"
                  value={emPhone}
                  onChange={(e) => setEmPhone(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="+213555111222"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Password <span className="opacity-60">(leave blank to keep current)</span></label>
                <input
                  type="password"
                  value={emPassword}
                  onChange={(e) => setEmPassword(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="Min 8 characters"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEmOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={saveEditManager}
                className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {bmOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="w-full max-w-lg rounded-2xl bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 p-6 space-y-4">
            <h3 className="text-lg font-bold">Add Branch Manager</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">Name</label>
                <input
                  value={bmName}
                  onChange={(e) => setBmName(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Email</label>
                <input
                  type="email"
                  value={bmEmail}
                  onChange={(e) => setBmEmail(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="email@company.com"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Phone <span className="opacity-60">(optional)</span></label>
                <input
                  type="tel"
                  value={bmPhone}
                  onChange={(e) => setBmPhone(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="+213555111222"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Password</label>
                <input
                  type="password"
                  value={bmPassword}
                  onChange={(e) => setBmPassword(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                  placeholder="Min 8 characters"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">Assign Branch</label>
                <select
                  value={bmBranchId}
                  onChange={(e) => setBmBranchId(e.target.value)}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-transparent"
                >
                  <option value="">Select branch</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>{b.name} — {b.city}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setBmOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={saveBranchManager}
                className="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700"
              >
                Create Manager
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
