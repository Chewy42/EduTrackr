import React from "react";

interface DegreeProgressCardProps {
  progress: number;
  totalCredits: number;
  earnedCredits: number;
  inProgressCredits: number;
}

export default function DegreeProgressCard({
  progress,
  totalCredits,
  earnedCredits,
  inProgressCredits,
}: DegreeProgressCardProps) {
  // Calculate stroke properties for circular progress
  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  // Color based on progress
  const getProgressColor = (p: number) => {
    if (p >= 75) return "#10b981"; // green
    if (p >= 50) return "#3b82f6"; // blue
    if (p >= 25) return "#f59e0b"; // amber
    return "#ef4444"; // red
  };

  const progressColor = getProgressColor(progress);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-all duration-300 group">
      <div className="flex items-center gap-4">
        {/* Circular Progress */}
        <div className="relative flex-shrink-0">
          <svg
            width={size}
            height={size}
            className="transform -rotate-90 transition-transform duration-300 group-hover:scale-105"
          >
            {/* Background circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#e2e8f0"
              strokeWidth={strokeWidth}
            />
            {/* Progress circle */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={progressColor}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
              style={{
                filter: `drop-shadow(0 0 6px ${progressColor}40)`,
              }}
            />
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-2xl font-bold transition-colors duration-300"
              style={{ color: progressColor }}
            >
              {progress}%
            </span>
            <span className="text-[10px] text-slate-500 font-medium">Complete</span>
          </div>
        </div>

        {/* Stats */}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Degree Progress</h3>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Earned</span>
              <span className="font-medium text-emerald-600">{earnedCredits.toFixed(1)} cr</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">In Progress</span>
              <span className="font-medium text-blue-600">{inProgressCredits.toFixed(1)} cr</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Total Required</span>
              <span className="font-medium text-slate-700">{totalCredits.toFixed(1)} cr</span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress bar underneath */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{
              width: `${Math.min(progress + (inProgressCredits / totalCredits) * 100, 100)}%`,
              background: `linear-gradient(90deg, ${progressColor} ${(progress / (progress + (inProgressCredits / totalCredits) * 100)) * 100}%, #93c5fd ${(progress / (progress + (inProgressCredits / totalCredits) * 100)) * 100}%)`,
            }}
          />
        </div>
        <div className="flex justify-between mt-1.5 text-[10px] text-slate-400">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
