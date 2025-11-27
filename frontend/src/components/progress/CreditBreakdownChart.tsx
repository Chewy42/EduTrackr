import React, { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  Sector,
} from "recharts";
import type { CreditRequirement } from "./ProgressPage";

interface CreditBreakdownChartProps {
  earned: number;
  inProgress: number;
  needed: number;
  requirements: CreditRequirement[];
}

const COLORS = {
  earned: "#10b981",
  inProgress: "#3b82f6",
  needed: "#e2e8f0",
};

const REQUIREMENT_COLORS = [
  "#10b981", // emerald
  "#3b82f6", // blue
  "#8b5cf6", // violet
  "#f59e0b", // amber
  "#ef4444", // red
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
];

// Custom active shape for hover effect
const renderActiveShape = (props: any) => {
  const {
    cx,
    cy,
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
    fill,
    payload,
    value,
  } = props;

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        style={{ filter: `drop-shadow(0 4px 12px ${fill}50)` }}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 12}
        outerRadius={outerRadius + 16}
        fill={fill}
      />
      <text
        x={cx}
        y={cy - 8}
        textAnchor="middle"
        fill="#1e293b"
        className="text-sm font-semibold"
      >
        {payload.name}
      </text>
      <text
        x={cx}
        y={cy + 12}
        textAnchor="middle"
        fill="#64748b"
        className="text-xs"
      >
        {value.toFixed(1)} credits
      </text>
    </g>
  );
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white rounded-lg shadow-lg border border-slate-200 px-3 py-2">
        <p className="text-sm font-medium text-slate-800">{data.name}</p>
        <p className="text-xs text-slate-500">
          {data.value.toFixed(1)} credits ({data.percentage}%)
        </p>
      </div>
    );
  }
  return null;
};

export default function CreditBreakdownChart({
  earned,
  inProgress,
  needed,
  requirements,
}: CreditBreakdownChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const [viewMode, setViewMode] = useState<"status" | "category">("status");

  const total = earned + inProgress + needed;

  // Status-based data
  const statusData = [
    {
      name: "Earned",
      value: earned,
      percentage: total > 0 ? Math.round((earned / total) * 100) : 0,
      fill: COLORS.earned,
    },
    {
      name: "In Progress",
      value: inProgress,
      percentage: total > 0 ? Math.round((inProgress / total) * 100) : 0,
      fill: COLORS.inProgress,
    },
    {
      name: "Remaining",
      value: needed,
      percentage: total > 0 ? Math.round((needed / total) * 100) : 0,
      fill: COLORS.needed,
    },
  ].filter((d) => d.value > 0);

  // Category-based data
  const categoryData = requirements.map((req, index) => {
    const completed = req.earned + req.in_progress;
    const rawPct = req.required > 0 ? (completed / req.required) * 100 : 0;
    const clampedPct = Math.min(100, Math.round(rawPct));

    return {
      name: req.label.length > 25 ? req.label.substring(0, 22) + "..." : req.label,
      fullName: req.label,
      value: completed,
      required: req.required,
      percentage: clampedPct,
      fill: REQUIREMENT_COLORS[index % REQUIREMENT_COLORS.length],
      overage: rawPct > 100 ? Math.round(rawPct - 100) : 0,
    };
  });

  const data = viewMode === "status" ? statusData : categoryData;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Credit Distribution</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {viewMode === "status" ? "By completion status" : "By requirement category"}
          </p>
        </div>
        <div className="flex bg-slate-100 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode("status")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === "status"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Status
          </button>
          <button
            onClick={() => setViewMode("category")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              viewMode === "category"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Category
          </button>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              // TS typings for recharts Pie omit activeIndex; supported at runtime
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              {...({
                activeIndex,
                activeShape: renderActiveShape,
              } as any)}
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(undefined)}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.fill}
                  className="cursor-pointer transition-opacity hover:opacity-80"
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="mt-4 grid grid-cols-2 gap-2">
        {data.slice(0, 6).map((item, index) => (
          <div
            key={index}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
            onMouseEnter={() => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(undefined)}
          >
            <div
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: item.fill }}
            />
            <span className="text-xs text-slate-600 truncate">{item.name}</span>
            <span className="text-xs font-medium text-slate-800 ml-auto">
              {item.percentage}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
