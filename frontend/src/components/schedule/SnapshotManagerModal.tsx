import React, { useState, useEffect } from 'react';
import { FiX, FiSave, FiRefreshCw, FiTrash2, FiDownload } from 'react-icons/fi';
import type { ScheduleSnapshot } from './types';

interface SnapshotManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  snapshots: ScheduleSnapshot[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  onRefresh: () => void;
  onSave: (name: string) => void;
  onLoad: (snapshot: ScheduleSnapshot) => void;
  onDelete: (snapshot: ScheduleSnapshot) => void;
}

export default function SnapshotManagerModal({
  isOpen,
  onClose,
  snapshots,
  loading,
  saving,
  error,
  onRefresh,
  onSave,
  onLoad,
  onDelete,
}: SnapshotManagerModalProps) {
  const [name, setName] = useState('');

  useEffect(() => {
    if (isOpen) {
      setName('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onSave(trimmed);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Schedule Snapshots</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Save and restore different versions of your schedule.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-700"
            aria-label="Close"
          >
            <FiX className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="px-4 pt-3">
            <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="px-4 pt-3 pb-2 flex flex-col gap-2">
          <label className="text-xs font-medium text-slate-700 flex flex-col gap-1">
            Snapshot name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Morning classes only"
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={saving}
            />
          </label>
          <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
            <span>Snapshots are saved to your account and can be loaded on any device.</span>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-1.5 rounded-full bg-blue-600 text-white text-xs font-medium px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <FiSave className="w-3 h-3 animate-pulse" />
              ) : (
                <FiSave className="w-3 h-3" />
              )}
              <span>Save snapshot</span>
            </button>
          </div>
        </form>

        <div className="px-4 pb-3 flex items-center justify-between text-[11px] text-slate-500">
          <span>
            {loading ? 'Loading snapshots…' : `${snapshots.length} saved snapshot${snapshots.length === 1 ? '' : 's'}`}
          </span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 text-slate-600 text-[11px] px-2 py-1 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiRefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="px-4 pb-4 overflow-y-auto flex-1">
          {snapshots.length === 0 && !loading ? (
            <div className="text-xs text-slate-500 text-center py-6">
              No snapshots yet. Create your first snapshot using the form above.
            </div>
          ) : (
            <ul className="space-y-2 text-xs">
              {snapshots.map((snapshot) => (
                <li
                  key={snapshot.id}
                  className="border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between gap-2 hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 truncate" title={snapshot.name}>
                        {snapshot.name}
                      </span>
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px]">
                        {snapshot.classCount} classes · {snapshot.totalCredits} credits
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      Saved {new Date(snapshot.updatedAt || snapshot.createdAt).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => onLoad(snapshot)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 text-white text-[11px] px-2.5 py-1 hover:bg-emerald-700"
                    >
                      <FiDownload className="w-3 h-3" />
                      <span>Load</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(snapshot)}
                      className="p-1 rounded-full text-slate-400 hover:text-red-600 hover:bg-red-50"
                      aria-label={`Delete snapshot ${snapshot.name}`}
                    >
                      <FiTrash2 className="w-3 h-3" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

