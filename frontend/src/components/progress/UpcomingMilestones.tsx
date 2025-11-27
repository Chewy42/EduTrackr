import React, { useMemo } from "react";
import { FiTarget, FiAward, FiCalendar, FiTrendingUp, FiBookOpen } from "react-icons/fi";
import type { CreditRequirement, Course, StudentInfo } from "./ProgressPage";

interface UpcomingMilestonesProps {
  creditRequirements: CreditRequirement[];
  courses?: {
    all_found: Course[];
    in_progress: Course[];
    completed: Course[];
  };
  studentInfo?: StudentInfo;
}

interface Milestone {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  progress?: number;
  target?: string;
  priority: "high" | "medium" | "low";
}

export default function UpcomingMilestones({
  creditRequirements,
  courses,
  studentInfo,
}: UpcomingMilestonesProps) {
  const milestones = useMemo(() => {
    const items: Milestone[] = [];

    // Calculate totals
    const totalRequired = creditRequirements.reduce((sum, r) => sum + r.required, 0);
    const totalEarned = creditRequirements.reduce((sum, r) => sum + r.earned, 0);
    const totalInProgress = creditRequirements.reduce((sum, r) => sum + r.in_progress, 0);
    const overallProgress = totalRequired > 0 ? (totalEarned / totalRequired) * 100 : 0;

    // Find requirements closest to completion
    const nearCompletion = creditRequirements
      .filter((r) => r.needed > 0 && r.needed <= 6)
      .sort((a, b) => a.needed - b.needed);

    // 1. Next requirement to complete
    const next = nearCompletion[0];
    if (next) {
      items.push({
        id: "next-requirement",
        title: `Complete ${next.label}`,
        description: `Only ${next.needed.toFixed(0)} more credits needed!`,
        icon: FiTarget,
        color: "text-emerald-600 bg-emerald-50",
        progress: ((next.earned + next.in_progress) / next.required) * 100,
        priority: "high",
      });
    }

    // 2. Major milestone progress
    if (overallProgress >= 25 && overallProgress < 50) {
      items.push({
        id: "halfway",
        title: "Reach 50% Completion",
        description: `You're ${(50 - overallProgress).toFixed(0)}% away from the halfway point!`,
        icon: FiTrendingUp,
        color: "text-blue-600 bg-blue-50",
        progress: overallProgress,
        target: "50%",
        priority: "medium",
      });
    } else if (overallProgress >= 50 && overallProgress < 75) {
      items.push({
        id: "three-quarters",
        title: "Reach 75% Completion",
        description: `${(75 - overallProgress).toFixed(0)}% to go until you're in the home stretch!`,
        icon: FiTrendingUp,
        color: "text-violet-600 bg-violet-50",
        progress: overallProgress,
        target: "75%",
        priority: "medium",
      });
    } else if (overallProgress >= 75 && overallProgress < 100) {
      items.push({
        id: "graduation",
        title: "Complete Your Degree! 🎓",
        description: `Only ${(100 - overallProgress).toFixed(0)}% remaining until graduation!`,
        icon: FiAward,
        color: "text-amber-600 bg-amber-50",
        progress: overallProgress,
        target: "100%",
        priority: "high",
      });
    }

    // 3. In-progress courses
    if (courses?.in_progress && courses.in_progress.length > 0) {
      const inProgressCredits = courses.in_progress.reduce((sum, c) => sum + c.credits, 0);
      items.push({
        id: "current-courses",
        title: "Complete Current Courses",
        description: `${courses.in_progress.length} courses (${inProgressCredits} credits) in progress`,
        icon: FiBookOpen,
        color: "text-indigo-600 bg-indigo-50",
        priority: "high",
      });
    }

    // 4. Graduation timeline
    if (studentInfo?.expected_graduation) {
      items.push({
        id: "graduation-date",
        title: "Expected Graduation",
        description: studentInfo.expected_graduation,
        icon: FiCalendar,
        color: "text-rose-600 bg-rose-50",
        priority: "low",
      });
    }

    // Sort by priority
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return items.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]).slice(0, 4);
  }, [creditRequirements, courses, studentInfo]);

  if (milestones.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Upcoming Milestones</h3>
          <p className="text-xs text-slate-500 mt-0.5">Key achievements on your path to graduation</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {milestones.map((milestone) => {
          const Icon = milestone.icon;
          
          return (
            <div
              key={milestone.id}
              className="group relative p-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-gradient-to-br from-white to-slate-50/50 hover:shadow-md transition-all duration-300 cursor-pointer"
            >
              {/* Priority indicator */}
              {milestone.priority === "high" && (
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              )}

              {/* Icon */}
              <div
                className={`w-10 h-10 rounded-xl ${milestone.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300`}
              >
                <Icon className="text-lg" />
              </div>

              {/* Content */}
              <h4 className="text-sm font-semibold text-slate-800 mb-1 group-hover:text-blue-600 transition-colors">
                {milestone.title}
              </h4>
              <p className="text-xs text-slate-500 line-clamp-2">{milestone.description}</p>

              {/* Progress bar (if applicable) */}
              {milestone.progress !== undefined && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <span className="text-slate-400">Progress</span>
                    <span className="font-medium text-slate-600">
                      {milestone.progress.toFixed(0)}%{milestone.target && ` → ${milestone.target}`}
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full transition-all duration-700 ease-out"
                      style={{ width: `${Math.min(milestone.progress, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Motivational footer */}
      <div className="mt-4 pt-4 border-t border-slate-100 text-center">
        <p className="text-xs text-slate-400 italic">
          "Every course completed is a step closer to your goals." 🌟
        </p>
      </div>
    </div>
  );
}
