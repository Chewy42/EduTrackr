import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../../auth/AuthContext";
import DegreeProgressCard from "./DegreeProgressCard";
import CreditBreakdownChart from "./CreditBreakdownChart";
import GPATrendChart from "./GPATrendChart";
import RequirementsChecklist from "./RequirementsChecklist";
import CourseHistoryTimeline from "./CourseHistoryTimeline";
import UpcomingMilestones from "./UpcomingMilestones";
import { FiRefreshCw, FiAlertCircle } from "react-icons/fi";

// Types for parsed program evaluation data
export interface StudentInfo {
  name?: string;
  id?: string;
  expected_graduation?: string;
  program?: string;
  catalog_year?: string;
}

export interface Course {
  term?: string;
  subject?: string;
  number?: string;
  title?: string;
  grade?: string | null;
  credits: number;
  type?: string | null;
}

export interface CreditRequirement {
  label: string;
  required: number;
  earned: number;
  in_progress: number;
  needed: number;
}

export interface GPA {
  overall?: number;
  major?: number;
}

/**
 * Formats a GPA value for display with appropriate precision.
 * Shows 3 decimal places if needed to distinguish similar values,
 * otherwise shows 2 decimal places.
 */
function formatGPA(value: number | undefined, otherValue?: number): string {
  if (value === undefined || value === null) return "—";

  // If both values exist and round to the same 2-decimal value but are actually different,
  // show 3 decimal places to distinguish them
  if (otherValue !== undefined && otherValue !== null) {
    const rounded2 = value.toFixed(2);
    const otherRounded2 = otherValue.toFixed(2);
    if (rounded2 === otherRounded2 && value !== otherValue) {
      return value.toFixed(3);
    }
  }

  return value.toFixed(2);
}

export interface ParsedData {
  student_info?: StudentInfo;
  gpa?: GPA;
  courses?: {
    all_found: Course[];
    in_progress: Course[];
    completed: Course[];
  };
  credit_requirements?: CreditRequirement[];
  mastery_demonstration?: { type?: string };
}

export interface ProgressData {
  parsed_data?: ParsedData;
  email?: string;
  uploaded_at?: string;
  original_filename?: string;
}

type LoadState = "idle" | "loading" | "ready" | "empty" | "error";

export default function ProgressPage() {
  const { jwt } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [data, setData] = useState<ProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchProgress = useCallback(async () => {
    if (!jwt) return;
    setLoadState("loading");
    setError(null);

    try {
      const res = await fetch("/api/program-evaluations/parsed", {
        headers: {
          Authorization: `Bearer ${jwt}`,
          Accept: "application/json",
        },
      });

      if (res.status === 404) {
        setData(null);
        setLoadState("empty");
        return;
      }

      if (!res.ok) {
        throw new Error("Unable to load progress data.");
      }

      const responseData = await res.json();
      setData(responseData);
      setLoadState("ready");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load progress data.";
      setError(message);
      setLoadState("error");
    }
  }, [jwt]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  // Extract data for components
  const parsed = data?.parsed_data;
  const studentInfo = parsed?.student_info;
  const gpa = parsed?.gpa;
  const courses = parsed?.courses;
  const creditRequirements = parsed?.credit_requirements || [];

  // Calculate overall progress from the primary "Degree credit"-style requirement
  // Other requirements (Residency, Upper Division, GE areas, etc.) overlap with Degree credit,
  // so we identify a single primary requirement to avoid double-counting aggregate credits.
  //
  // Heuristic:
  //   1. Prefer an item whose label mentions "Degree credit" (or similar), if present
  //   2. Otherwise, fall back to the requirement with the largest `required` value
  //      (overall program credit requirement is almost always the maximum).
  let primaryRequirement: CreditRequirement | undefined = creditRequirements.find(
    (req) => req.label.toLowerCase().includes("degree credit")
  );

  if (!primaryRequirement && creditRequirements.length > 0) {
    primaryRequirement = creditRequirements.reduce<CreditRequirement | undefined>((max, req) => {
      if (!max) return req;
      return req.required > max.required ? req : max;
    }, undefined);
  }
  const totalRequired = primaryRequirement?.required ?? 0;
  const totalEarned = primaryRequirement?.earned ?? 0;
  const totalInProgress = primaryRequirement?.in_progress ?? 0;
  const totalNeeded = primaryRequirement?.needed ?? 0;
  const overallProgress = totalRequired > 0 ? Math.round((totalEarned / totalRequired) * 100) : 0;

  if (loadState === "loading" || loadState === "idle") {
    return (
      <div className="w-full max-w-7xl mx-auto p-4 md:p-6">
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-slate-500">
            <FiRefreshCw className="animate-spin text-xl" />
            <span className="text-sm font-medium">Loading your progress...</span>
          </div>
        </div>
      </div>
    );
  }

  if (loadState === "empty") {
    return (
      <div className="w-full max-w-7xl mx-auto p-4 md:p-6">
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <FiAlertCircle className="text-4xl text-slate-400 mb-3" />
          <h3 className="text-lg font-semibold text-slate-700 mb-1">No Progress Data Available</h3>
          <p className="text-sm text-slate-500 max-w-md">
            Upload your program evaluation PDF first to see your academic progress visualized here.
          </p>
        </div>
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="w-full max-w-7xl mx-auto p-4 md:p-6">
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <FiAlertCircle className="text-4xl text-red-400 mb-3" />
          <h3 className="text-lg font-semibold text-slate-700 mb-1">Error Loading Progress</h3>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={fetchProgress}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition-colors"
          >
            <FiRefreshCw className="text-base" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {/* Header with student info */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-800">
            {studentInfo?.name ? `${studentInfo.name.split(",").reverse().join(" ").trim()}'s Progress` : "Your Progress"}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {studentInfo?.program || "Computer Science"} 
            {studentInfo?.expected_graduation && ` • Expected Graduation: ${studentInfo.expected_graduation}`}
          </p>
        </div>
        <button
          onClick={fetchProgress}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          <FiRefreshCw className="text-base" />
          Refresh Data
        </button>
      </div>

      {/* Top row - Key metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <DegreeProgressCard
          progress={overallProgress}
          totalCredits={totalRequired}
          earnedCredits={totalEarned}
          inProgressCredits={totalInProgress}
        />
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Overall GPA</div>
          <div className="text-3xl font-bold text-slate-800">
            {formatGPA(gpa?.overall, gpa?.major)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {gpa?.overall && gpa.overall >= 3.5 ? "🌟 Dean's List eligible" : gpa?.overall && gpa.overall >= 3.0 ? "✅ Good standing" : ""}
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Major GPA</div>
          <div className="text-3xl font-bold text-slate-800">
            {formatGPA(gpa?.major, gpa?.overall)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {gpa?.major && gpa.major >= 3.7 ? "🏆 Excellent" : gpa?.major && gpa.major >= 3.0 ? "👍 Solid performance" : ""}
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Credits Remaining</div>
          <div className="text-3xl font-bold text-slate-800">
            {totalNeeded.toFixed(0)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {totalInProgress > 0 && `📚 ${totalInProgress} in progress`}
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CreditBreakdownChart
          earned={totalEarned}
          inProgress={totalInProgress}
          needed={totalNeeded}
          requirements={creditRequirements}
        />
        <GPATrendChart courses={courses?.completed || []} />
      </div>

      {/* Requirements and Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RequirementsChecklist requirements={creditRequirements} />
        <CourseHistoryTimeline courses={courses?.all_found || []} />
      </div>

      {/* Milestones */}
      <UpcomingMilestones
        creditRequirements={creditRequirements}
        courses={courses}
        studentInfo={studentInfo}
      />
    </div>
  );
}
