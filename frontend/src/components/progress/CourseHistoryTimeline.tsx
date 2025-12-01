import React, { useMemo, useState } from "react";
import { FiChevronLeft, FiChevronRight, FiBook } from "react-icons/fi";
import type { Course } from "./ProgressPage";

interface CourseHistoryTimelineProps {
  courses: Course[];
}

// Grade colors
const GRADE_COLORS: Record<string, string> = {
  "A+": "bg-emerald-500",
  A: "bg-emerald-500",
  "A-": "bg-emerald-400",
  "B+": "bg-blue-500",
  B: "bg-blue-500",
  "B-": "bg-blue-400",
  "C+": "bg-amber-500",
  C: "bg-amber-500",
  "C-": "bg-amber-400",
  "D+": "bg-orange-500",
  D: "bg-orange-500",
  "D-": "bg-orange-400",
  F: "bg-red-500",
  IP: "bg-violet-500",
};

const GRADE_BG: Record<string, string> = {
  "A+": "bg-emerald-50 text-emerald-700 border-emerald-200",
  A: "bg-emerald-50 text-emerald-700 border-emerald-200",
  "A-": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "B+": "bg-blue-50 text-blue-700 border-blue-200",
  B: "bg-blue-50 text-blue-700 border-blue-200",
  "B-": "bg-blue-50 text-blue-700 border-blue-200",
  "C+": "bg-amber-50 text-amber-700 border-amber-200",
  C: "bg-amber-50 text-amber-700 border-amber-200",
  "C-": "bg-amber-50 text-amber-700 border-amber-200",
  "D+": "bg-orange-50 text-orange-700 border-orange-200",
  D: "bg-orange-50 text-orange-700 border-orange-200",
  "D-": "bg-orange-50 text-orange-700 border-orange-200",
  F: "bg-red-50 text-red-700 border-red-200",
  IP: "bg-violet-50 text-violet-700 border-violet-200",
};

// Parse term for sorting
const parseTerm = (term: string | undefined): { year: number; season: number; display: string } => {
  if (!term) return { year: 0, season: 0, display: "Unknown" };

  const safeTerm: string = term ?? "Unknown";
  const match = safeTerm.match(/(\w+)\s*(\d{4})/);
  if (!match) return { year: 0, season: 0, display: safeTerm };

  const [, seasonRaw, yearRaw] = match;
  const seasonOrder: Record<string, number> = {
    Spring: 1,
    Summer: 2,
    Fall: 3,
    Winter: 4,
  };
  
  return {
    year: parseInt(yearRaw ?? "0"),
    season: seasonOrder[seasonRaw ?? ""] || 0,
    display: `${seasonRaw ?? ""} ${yearRaw ?? ""}`.trim() || safeTerm,
  };
};

export default function CourseHistoryTimeline({ courses }: CourseHistoryTimelineProps) {
  const [selectedTermIndex, setSelectedTermIndex] = useState(0);
  const [hoveredCourse, setHoveredCourse] = useState<string | null>(null);

  // Group courses by term
  const termGroups = useMemo(() => {
    const groups = new Map<string, { courses: Course[]; parsed: ReturnType<typeof parseTerm> }>();

    courses.forEach((course) => {
      const term = course.term ?? "Unknown";
      if (!groups.has(term)) {
        groups.set(term, { courses: [], parsed: parseTerm(term) });
      }
      groups.get(term)!.courses.push(course);
    });

    // Sort by term
    return Array.from(groups.entries())
      .sort((a, b) => {
        const aOrder = a[1].parsed.year * 10 + a[1].parsed.season;
        const bOrder = b[1].parsed.year * 10 + b[1].parsed.season;
        return bOrder - aOrder; // Most recent first
      })
      .map(([term, data]) => ({
        term,
        display: data.parsed.display,
        courses: data.courses.sort((a, b) => (b.credits || 0) - (a.credits || 0)),
        totalCredits: data.courses.reduce((sum, c) => sum + (c.credits || 0), 0),
      }));
  }, [courses]);

  const currentTerm = termGroups[selectedTermIndex];

  if (termGroups.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">Course History</h3>
        <div className="h-64 flex items-center justify-center text-slate-400 text-sm">
          No course history available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Course History</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {termGroups.length} terms • {courses.length} courses
          </p>
        </div>
      </div>

      {/* Term selector */}
      <div className="flex items-center justify-between mb-4 bg-slate-50 rounded-xl p-2">
        <button
          onClick={() => setSelectedTermIndex((prev) => Math.max(prev - 1, 0))}
          disabled={selectedTermIndex <= 0}
          className="p-1.5 rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <FiChevronLeft className="text-slate-600" />
        </button>

        <div className="text-center">
          <div className="text-sm font-semibold text-slate-800">{currentTerm?.display}</div>
          <div className="text-xs text-slate-500">
            {currentTerm?.courses.length} courses • {currentTerm?.totalCredits} credits
          </div>
        </div>

        <button
          onClick={() => setSelectedTermIndex((prev) => Math.min(prev + 1, termGroups.length - 1))}
          disabled={selectedTermIndex >= termGroups.length - 1}
          className="p-1.5 rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <FiChevronRight className="text-slate-600" />
        </button>
      </div>

      {/* Timeline dots */}
      <div className="flex items-center justify-center gap-1.5 mb-4">
        {termGroups.slice(0, 10).map((_, index) => (
          <button
            key={index}
            onClick={() => setSelectedTermIndex(index)}
            className={`w-2 h-2 rounded-full transition-all ${
              index === selectedTermIndex
                ? "bg-blue-500 w-4"
                : "bg-slate-300 hover:bg-slate-400"
            }`}
          />
        ))}
        {termGroups.length > 10 && (
          <span className="text-xs text-slate-400 ml-1">+{termGroups.length - 10}</span>
        )}
      </div>

      {/* Course list */}
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {currentTerm?.courses.map((course, index) => {
          const courseId = `${course.subject}-${course.number}-${index}`;
          const isHovered = hoveredCourse === courseId;
          const gradeColor = GRADE_COLORS[course.grade || ""] || "bg-slate-400";
          const gradeBg = GRADE_BG[course.grade || ""] || "bg-slate-50 text-slate-600 border-slate-200";

          return (
            <div
              key={courseId}
              onMouseEnter={() => setHoveredCourse(courseId)}
              onMouseLeave={() => setHoveredCourse(null)}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 cursor-pointer ${
                isHovered
                  ? "border-blue-200 bg-blue-50/50 shadow-sm"
                  : "border-slate-100 bg-slate-50/50 hover:border-slate-200"
              }`}
            >
              {/* Course icon with grade color */}
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${gradeColor} text-white flex-shrink-0`}>
                <FiBook className="text-lg" />
              </div>

              {/* Course info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-800">
                    {course.subject} {course.number}
                  </span>
                  <span className="text-xs text-slate-400">•</span>
                  <span className="text-xs text-slate-500">{course.credits} cr</span>
                </div>
                <div className="text-xs text-slate-500 truncate mt-0.5">
                  {course.title || "No title"}
                </div>
              </div>

              {/* Grade badge */}
              <div
                className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${gradeBg} flex-shrink-0`}
              >
                {course.grade || "—"}
              </div>
            </div>
          );
        })}
      </div>

      {/* Grade legend */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="flex flex-wrap gap-2 justify-center">
          {[
            { grade: "A", label: "Excellent", color: "bg-emerald-500" },
            { grade: "B", label: "Good", color: "bg-blue-500" },
            { grade: "C", label: "Average", color: "bg-amber-500" },
            { grade: "IP", label: "In Progress", color: "bg-violet-500" },
          ].map(({ grade, label, color }) => (
            <div key={grade} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
              <span className="text-[10px] text-slate-500">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
