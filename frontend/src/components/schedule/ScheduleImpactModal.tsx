import React, { useMemo } from 'react';
import { FiX, FiTrendingUp, FiCheck } from 'react-icons/fi';
import { ScheduledClass, DegreeRequirement, RequirementsSummary } from './types';

interface ScheduleImpactModalProps {
  isOpen: boolean;
  onClose: () => void;
  scheduledClasses: ScheduledClass[];
  baseRequirements: RequirementsSummary | null;
}

export default function ScheduleImpactModal({
  isOpen,
  onClose,
  scheduledClasses,
  baseRequirements,
}: ScheduleImpactModalProps) {
  if (!isOpen) return null;

  // Calculate impact
  const impactData = useMemo(() => {
    if (!baseRequirements) return [];

    // Group scheduled classes by requirement type/label
    const impactMap = new Map<string, {
      req: DegreeRequirement;
      addedCredits: number;
      contributingClasses: ScheduledClass[];
    }>();

    // Initialize with base requirements
    baseRequirements.requirements.forEach(req => {
      const key = `${req.type}-${req.label}`;
      impactMap.set(key, {
        req,
        addedCredits: 0,
        contributingClasses: [],
      });
    });

    // Add scheduled classes impact
    scheduledClasses.forEach(cls => {
      cls.requirementsSatisfied.forEach(badge => {
        // Find matching requirement
        // Note: This is a simplified matching. In a real app, we'd need robust ID matching.
        // Here we match by label/type which should be consistent.
        const key = `${badge.type}-${badge.label}`;
        const entry = impactMap.get(key);
        
        if (entry) {
          entry.addedCredits += cls.credits;
          entry.contributingClasses.push(cls);
        }
      });
    });

    // Filter to only show requirements that are affected or still needed
    return Array.from(impactMap.values())
      .filter(item => item.addedCredits > 0 || item.req.creditsNeeded > 0)
      .sort((a, b) => {
        // Sort by: Affected first, then by type
        if (a.addedCredits > 0 && b.addedCredits === 0) return -1;
        if (a.addedCredits === 0 && b.addedCredits > 0) return 1;
        return a.req.type.localeCompare(b.req.type);
      });

  }, [scheduledClasses, baseRequirements]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2 text-blue-600">
            <FiTrendingUp className="w-5 h-5" />
            <h3 className="font-semibold text-lg">Projected Progress</h3>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-100 rounded-lg"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!baseRequirements ? (
            <div className="text-center py-12 text-slate-400">
              Loading requirements...
            </div>
          ) : impactData.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              No remaining requirements found. You might be all set!
            </div>
          ) : (
            <div className="space-y-6">
              {impactData.map((item, idx) => {
                const { req, addedCredits, contributingClasses } = item;
                const currentNeeded = req.creditsNeeded;
                const newNeeded = Math.max(0, currentNeeded - addedCredits);
                const progressPercent = Math.min(100, (addedCredits / currentNeeded) * 100);
                const isFullyMet = newNeeded === 0;

                return (
                  <div key={idx} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-slate-800">{req.label}</h4>
                          {isFullyMet && (
                            <span className="text-[10px] font-bold px-1.5 py-0.5 bg-green-100 text-green-700 rounded-full flex items-center gap-1">
                              <FiCheck className="w-3 h-3" /> Met
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5 capitalize">{req.type.replace('_', ' ')}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-slate-700">
                          <span className={addedCredits > 0 ? "text-green-600 font-bold" : ""}>
                            {addedCredits > 0 ? `+${addedCredits}` : "0"}
                          </span>
                          <span className="text-slate-400 mx-1">/</span>
                          {currentNeeded} cr needed
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          {newNeeded} remaining
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden flex mb-3">
                      {/* Existing progress would go here if we had total credits, but we only have 'needed'. 
                          So we visualize 'progress towards satisfying the remaining need'. */}
                      <div 
                        className="bg-green-500 relative transition-all duration-500 ease-out"
                        style={{ width: `${progressPercent}%` }}
                      >
                        {addedCredits > 0 && (
                          <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite] skew-x-12" />
                        )}
                      </div>
                    </div>

                    {/* Contributing Classes */}
                    {contributingClasses.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {contributingClasses.map(cls => (
                          <div key={cls.id} className="text-xs px-2 py-1 bg-white border border-slate-200 rounded text-slate-600 flex items-center gap-1.5 shadow-sm">
                            <span className="font-medium text-slate-800">{cls.code}</span>
                            <span className="text-slate-400">({cls.credits} cr)</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Footer */}
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
