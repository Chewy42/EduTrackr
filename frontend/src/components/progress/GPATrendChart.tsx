import React, { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from "recharts";
import type { Course } from "./ProgressPage";

interface GPATrendChartProps {
  courses: Course[];
}

// Grade point mapping
const GRADE_POINTS: Record<string, number> = {
  "A+": 4.0,
  A: 4.0,
  "A-": 3.7,
  "B+": 3.3,
  B: 3.0,
  "B-": 2.7,
  "C+": 2.3,
  C: 2.0,
  "C-": 1.7,
  "D+": 1.3,
  D: 1.0,
  "D-": 0.7,
  F: 0.0,
};

// Parse term into sortable format
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
    display:
      yearRaw && seasonRaw
        ? `${seasonRaw.substring(0, 3)} '${yearRaw.substring(2)}`
        : safeTerm,
  };
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white rounded-lg shadow-lg border border-slate-200 px-4 py-3">
        <p className="text-sm font-semibold text-slate-800 mb-2">{data.fullTerm}</p>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-500">Term GPA</span>
            <span className="text-sm font-bold text-blue-600">{data.termGpa.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-500">Cumulative GPA</span>
            <span className="text-sm font-bold text-emerald-600">{data.cumulativeGpa.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-500">Credits</span>
            <span className="text-sm font-medium text-slate-700">{data.credits}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-slate-500">Courses</span>
            <span className="text-sm font-medium text-slate-700">{data.courseCount}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function GPATrendChart({ courses }: GPATrendChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null);

  const chartData = useMemo(() => {
    // Group courses by term and calculate GPA
    const termMap = new Map<string, { courses: Course[]; order: number; fullTerm: string }>();

    courses.forEach((course) => {
      if (!course.term || !course.grade || !GRADE_POINTS[course.grade]) return;
      
      const parsed = parseTerm(course.term);
      const key = `${parsed.year}-${parsed.season}`;
      
      if (!termMap.has(key)) {
        termMap.set(key, {
          courses: [],
          order: parsed.year * 10 + parsed.season,
          fullTerm: course.term,
        });
      }
      termMap.get(key)!.courses.push(course);
    });

    // Sort by term order and calculate GPAs
    const sortedTerms = Array.from(termMap.entries())
      .sort((a, b) => a[1].order - b[1].order);

    let totalPoints = 0;
    let totalCredits = 0;

    return sortedTerms.map(([key, { courses, fullTerm }]) => {
      // Calculate term GPA
      let termPoints = 0;
      let termCredits = 0;

      courses.forEach((course) => {
        const grade = course.grade;
        if (grade && GRADE_POINTS[grade] !== undefined) {
          termPoints += GRADE_POINTS[grade] * course.credits;
          termCredits += course.credits;
        }
      });

      const termGpa = termCredits > 0 ? termPoints / termCredits : 0;

      // Update cumulative
      totalPoints += termPoints;
      totalCredits += termCredits;
      const cumulativeGpa = totalCredits > 0 ? totalPoints / totalCredits : 0;

      const parsed = parseTerm(fullTerm);

      return {
        term: parsed.display,
        fullTerm,
        termGpa,
        cumulativeGpa,
        credits: termCredits,
        courseCount: courses.length,
      };
    });
  }, [courses]);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">GPA Trend</h3>
        <div className="h-64 flex items-center justify-center text-slate-400 text-sm">
          No grade data available to show trends
        </div>
      </div>
    );
  }

  const minGpa = Math.min(...chartData.map((d) => Math.min(d.termGpa, d.cumulativeGpa))) - 0.3;
  const maxGpa = Math.max(...chartData.map((d) => Math.max(d.termGpa, d.cumulativeGpa))) + 0.2;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">GPA Trend</h3>
          <p className="text-xs text-slate-500 mt-0.5">Term and cumulative GPA over time</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-blue-500 rounded" />
            <span className="text-slate-500">Term</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-emerald-500 rounded" />
            <span className="text-slate-500">Cumulative</span>
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="gpaTrendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="term"
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickLine={false}
              axisLine={{ stroke: "#e2e8f0" }}
            />
            <YAxis
              domain={[Math.max(0, minGpa), Math.min(4.0, maxGpa)]}
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => value.toFixed(1)}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine
              y={3.0}
              stroke="#f59e0b"
              strokeDasharray="5 5"
              strokeOpacity={0.5}
              label={{
                value: "Good Standing",
                position: "right",
                fill: "#f59e0b",
                fontSize: 10,
              }}
            />
            <ReferenceLine
              y={3.5}
              stroke="#10b981"
              strokeDasharray="5 5"
              strokeOpacity={0.5}
              label={{
                value: "Dean's List",
                position: "right",
                fill: "#10b981",
                fontSize: 10,
              }}
            />
            <Area
              type="monotone"
              dataKey="cumulativeGpa"
              fill="url(#gpaTrendGradient)"
              stroke="transparent"
            />
            <Line
              type="monotone"
              dataKey="termGpa"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }}
            />
            <Line
              type="monotone"
              dataKey="cumulativeGpa"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 4, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Stats summary + per-term breakdown */}
      <div className="mt-4 pt-3 border-t border-slate-100 space-y-3">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {chartData.length > 0
                ? (chartData[chartData.length - 1]?.termGpa ?? 0).toFixed(2)
                : "—"}
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">Latest Term</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-emerald-600">
              {chartData.length > 0
                ? (chartData[chartData.length - 1]?.cumulativeGpa ?? 0).toFixed(2)
                : "—"}
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">Cumulative</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-slate-700">
              {chartData.length > 0
                ? Math.max(...chartData.map((d) => d.termGpa)).toFixed(2)
                : "—"}
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide">Best Term</div>
          </div>
        </div>

        {/* Per-term semester summary */}
        <div className="mt-1 flex flex-wrap gap-2">
          {chartData.map((d) => (
            <div
              key={d.fullTerm}
              className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 flex items-center gap-2"
            >
              <span className="font-semibold text-slate-800">{d.fullTerm}</span>
              <span className="h-3 w-px bg-slate-200" />
              <span>
                Term {d.termGpa.toFixed(2)} • Cum {d.cumulativeGpa.toFixed(2)}
              </span>
              <span className="h-3 w-px bg-slate-200" />
              <span>
                {d.credits} cr • {d.courseCount} courses
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
