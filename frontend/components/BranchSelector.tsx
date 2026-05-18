import React, { useEffect, useState } from 'react';
import { useAuth } from '../store/AuthContext';
import { Branch, canSwitchBranches } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE || '';

const BranchSelector: React.FC = () => {
  const { user, token, selectedBranchId, setSelectedBranchId } = useAuth();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [hasFreshBranchList, setHasFreshBranchList] = useState(false);

  useEffect(() => {
    if (!user || !token) {
      setBranches([]);
      setHasFreshBranchList(false);
      return;
    }

    let isCancelled = false;

    const load = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/branches`, {
          cache: 'no-store',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (isCancelled) return;
        if (!res.ok) {
          setHasFreshBranchList(false);
          return;
        }
        const data = (await res.json()) as Branch[];
        if (isCancelled) return;
        setBranches(Array.isArray(data) ? data : []);
        setHasFreshBranchList(true);
      } catch {
        if (isCancelled) return;
        setHasFreshBranchList(false);
      }
    };

    void load();

    return () => {
      isCancelled = true;
    };
  }, [token, user]);

  const userBranch = user?.branchId !== undefined && user?.branchId !== null ? String(user.branchId) : '';
  const canSelectBranch = canSwitchBranches(user?.role);
  const effective = canSelectBranch ? selectedBranchId : userBranch;
  const activeBranches = branches.filter((branch) => String(branch.status || '').toLowerCase() === 'active');

  useEffect(() => {
    if (!canSelectBranch || !selectedBranchId || !hasFreshBranchList) return;
    const stillActive = activeBranches.some((branch) => String(branch.id) === selectedBranchId);
    if (!stillActive) {
      setSelectedBranchId('');
    }
  }, [activeBranches, canSelectBranch, hasFreshBranchList, selectedBranchId, setSelectedBranchId]);

  if (!user) return null;

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-text-secondary dark:text-text-secondaryDark">Branch</label>
      <select
        value={effective}
        disabled={!canSelectBranch}
        onChange={(e) => setSelectedBranchId(e.target.value)}
        className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-card-light dark:bg-card-dark text-sm"
      >
        {canSelectBranch && <option value="">All Branches</option>}
        {activeBranches.map((branch) => (
          <option key={branch.id} value={String(branch.id)}>
            {branch.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default BranchSelector;
