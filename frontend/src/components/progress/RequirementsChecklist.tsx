import React, { useState } from "react";
import { FiCheck, FiClock, FiCircle, FiChevronDown, FiChevronUp } from "react-icons/fi";
import type { CreditRequirement } from "./ProgressPage";

interface RequirementsChecklistProps {
  requirements: CreditRequirement[];
}

interface RequirementItemProps {
  requirement: CreditRequirement;
  index: number;
}

function RequirementItem({ requirement, index }: RequirementItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const progress = requirement.required > 0 
    ? ((requirement.earned + requirement.in_progress) / requirement.required) * 100 
    : 0;
  const earnedProgress = requirement.required > 0 
    ? (requirement.earned / requirement.required) * 100 
    : 0;

  const isComplete = requirement.needed === 0;
  const hasInProgress = requirement.in_progress > 0;

  // Status icon and color
  const getStatus = () => {
    if (isComplete) {
      return { icon: FiCheck, color: "text-emerald-500", bg: "bg-emerald-50", label: "Complete" };
    }
    if (hasInProgress) {
      return { icon: FiClock, color: "text-blue-500", bg: "bg-blue-50", label: "In Progress" };
    }
    return { icon: FiCircle, color: "text-slate-400", bg: "bg-slate-50", label: "Not Started" };
  };

  const status = getStatus();
  const StatusIcon = status.icon;

  // Get progress bar color
  const getProgressColor = () => {
    if (isComplete) return "bg-emerald-500";
    if (progress >= 75) return "bg-blue-500";
    if (progress >= 50) return "bg-amber-500";
    return "bg-slate-300";
  };

  return (
    <div 
      className={`border rounded-xl transition-all duration-200 ${
        isExpanded ? "border-blue-200 bg-blue-50/30" : "border-slate-200 hover:border-slate-300"
      }`}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center gap-3"
      >
        {/* Status icon */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full ${status.bg} flex items-center justify-center`}>
          <StatusIcon className={`text-sm ${status.color}`} />
        </div>

        {/* Label and progress */}
        <div className="flex-1 min-w-0 text-left">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800 truncate">
              {requirement.label}
            </span>
            <span className="text-xs font-medium text-slate-600 flex-shrink-0">
              {requirement.earned.toFixed(0)}/{requirement.required.toFixed(0)}
            </span>
          </div>
          
          {/* Progress bar */}
          <div className="mt-2 h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div className="h-full flex">
              <div
                className={`${getProgressColor()} transition-all duration-500`}
                style={{ width: `${Math.min(earnedProgress, 100)}%` }}
              />
              {hasInProgress && (
                <div
                  className="bg-blue-300 transition-all duration-500"
                  style={{ width: `${Math.min(progress - earnedProgress, 100 - earnedProgress)}%` }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Expand icon */}
        <div className="flex-shrink-0 text-slate-400">
          {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-3 pt-0 border-t border-slate-200/50 mt-0">
          <div className="grid grid-cols-2 gap-3 pt-3">
            <div className="bg-white rounded-lg p-2.5 border border-slate-100">
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">Earned</div>
              <div className="text-lg font-bold text-emerald-600">{requirement.earned.toFixed(1)}</div>
            </div>
            <div className="bg-white rounded-lg p-2.5 border border-slate-100">
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">In Progress</div>
              <div className="text-lg font-bold text-blue-600">{requirement.in_progress.toFixed(1)}</div>
            </div>
            <div className="bg-white rounded-lg p-2.5 border border-slate-100">
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">Required</div>
              <div className="text-lg font-bold text-slate-700">{requirement.required.toFixed(1)}</div>
            </div>
            <div className="bg-white rounded-lg p-2.5 border border-slate-100">
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">Still Needed</div>
              <div className={`text-lg font-bold ${requirement.needed > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                {requirement.needed.toFixed(1)}
              </div>
            </div>
          </div>

          {/* Visual representation */}
          <div className="mt-3 flex items-center gap-1">
            {Array.from({ length: Math.ceil(requirement.required / 3) }).map((_, i) => {
              const creditPosition = i * 3;
              let status = "empty";
              if (creditPosition < requirement.earned) {
                status = "earned";
              } else if (creditPosition < requirement.earned + requirement.in_progress) {
                status = "inProgress";
              }

              return (
                <div
                  key={i}
                  className={`h-2 flex-1 rounded-sm transition-colors ${
                    status === "earned"
                      ? "bg-emerald-500"
                      : status === "inProgress"
                      ? "bg-blue-400"
                      : "bg-slate-200"
                  }`}
                  title={`Credits ${creditPosition}-${creditPosition + 3}`}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RequirementsChecklist({ requirements }: RequirementsChecklistProps) {
  const [filter, setFilter] = useState<"all" | "incomplete" | "complete">("all");

  const filteredRequirements = requirements.filter((req) => {
    if (filter === "complete") return req.needed === 0;
    if (filter === "incomplete") return req.needed > 0;
    return true;
  });

  const completedCount = requirements.filter((r) => r.needed === 0).length;
  const totalCount = requirements.length;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Requirements Checklist</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {completedCount} of {totalCount} categories complete
          </p>
        </div>
        <div className="flex bg-slate-100 rounded-lg p-0.5">
          <button
            onClick={() => setFilter("all")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === "all"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter("incomplete")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === "incomplete"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Incomplete
          </button>
          <button
            onClick={() => setFilter("complete")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === "complete"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Done
          </button>
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="mb-4">
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-700 ease-out"
            style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Requirements list */}
      <div className="space-y-2 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
        {filteredRequirements.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-sm">
            {filter === "complete" ? "No completed requirements yet" : 
             filter === "incomplete" ? "All requirements complete! 🎉" : 
             "No requirements found"}
          </div>
        ) : (
          filteredRequirements.map((requirement, index) => (
            <RequirementItem key={index} requirement={requirement} index={index} />
          ))
        )}
      </div>

      {/* Summary footer */}
      {requirements.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-500">
            {requirements.reduce((sum, r) => sum + r.needed, 0).toFixed(0)} credits remaining
          </span>
          <span className="text-emerald-600 font-medium">
            {Math.round((completedCount / totalCount) * 100)}% complete
          </span>
        </div>
      )}
    </div>
  );
}
