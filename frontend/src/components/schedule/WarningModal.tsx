import React from 'react';
import { FiX, FiAlertTriangle } from 'react-icons/fi';

interface WarningModalProps {
  isOpen: boolean;
  onClose: () => void;
  warnings: string[];
}

export default function WarningModal({ isOpen, onClose, warnings }: WarningModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-amber-50/50">
          <div className="flex items-center gap-2 text-amber-600">
            <FiAlertTriangle className="w-5 h-5" />
            <h3 className="font-semibold">Schedule Warnings</h3>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-100 rounded-lg"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {warnings.length === 0 ? (
            <p className="text-slate-500 text-center">No warnings to display.</p>
          ) : (
            <ul className="space-y-3">
              {warnings.map((warning, idx) => (
                <li key={idx} className="flex gap-3 text-sm text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-amber-500 font-bold select-none">•</span>
                  {warning}
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-slate-200 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
