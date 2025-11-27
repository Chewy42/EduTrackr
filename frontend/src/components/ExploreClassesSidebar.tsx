import React, { useMemo, useState } from "react";
import { FiSearch, FiBookOpen, FiUser } from "react-icons/fi";
import type { Course } from "./progress/ProgressPage";

// TODO: Replace with real upcoming-classes API once available
const MOCK_CLASSES: Array<{
  id: string;
  code: string;
  title: string;
  professor: string;
  term: string;
}> = [
  { id: "cs510", code: "CS 510", title: "Advanced Algorithms", professor: "Dr. Lee", term: "Spring 2026" },
  { id: "engr520", code: "ENGR 520", title: "Embedded Systems Design", professor: "Dr. Patel", term: "Spring 2026" },
  { id: "cs530", code: "CS 530", title: "Machine Learning", professor: "Dr. Kim", term: "Fall 2026" },
  { id: "engr501", code: "ENGR 501", title: "Graduate Seminar", professor: "Staff", term: "Fall 2026" },
];

export default function ExploreClassesSidebar() {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return MOCK_CLASSES;
    return MOCK_CLASSES.filter((cls) => {
      return (
        cls.code.toLowerCase().includes(q) ||
        cls.title.toLowerCase().includes(q) ||
        cls.professor.toLowerCase().includes(q) ||
        cls.term.toLowerCase().includes(q)
      );
    });
  }, [query]);

  return (
    <aside className="flex-1 flex flex-col h-full">
      <div className="px-4 pt-4 pb-3 border-b border-slate-100">
        <h2 className="text-sm font-semibold text-slate-800 mb-2 text-center">
          Explore Upcoming Classes
        </h2>
        <div className="relative">
          <FiSearch className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by course, prof, or term"
            className="w-full rounded-full border border-slate-200 bg-slate-50 pl-9 pr-3 py-2 text-xs text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:bg-white focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-2">
        {filtered.map((cls) => (
          <div
            key={cls.id}
            className="rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/60 hover:border-blue-200 transition-colors p-3 text-xs cursor-pointer"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-slate-800 flex items-center gap-1">
                <FiBookOpen className="h-3.5 w-3.5 text-blue-500" />
                {cls.code}
              </span>
              <span className="text-[10px] text-slate-500">{cls.term}</span>
            </div>
            <div className="text-[11px] text-slate-600 mb-1 line-clamp-2">{cls.title}</div>
            <div className="flex items-center gap-1 text-[11px] text-slate-500">
              <FiUser className="h-3 w-3" />
              <span>{cls.professor}</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-[11px] text-slate-400 text-center mt-6">
            No matching classes found.
          </div>
        )}
      </div>
    </aside>
  );
}
