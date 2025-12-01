import React, { useState, useEffect, useCallback } from 'react';
import { FiSearch, FiFilter, FiX, FiLoader, FiChevronDown } from 'react-icons/fi';
import { searchClasses, getSubjects } from '../../lib/scheduleApi';
import { ClassSection, ClassSearchParams, hasMeetingTimes } from './types';
import ClassCard from './ClassCard';
import { useAuth } from '../../auth/AuthContext';

interface ClassSearchSidebarProps {
	onAddClass: (classData: ClassSection) => void;
	onRemoveClass: (classId: string) => void;
	addedClassIds: Set<string>;
	conflicts: Record<string, string>; // classId -> conflict message
}

export default function ClassSearchSidebar({
	onAddClass,
	onRemoveClass,
	addedClassIds,
	conflicts,
}: ClassSearchSidebarProps) {
  const { jwt } = useAuth();
  const [query, setQuery] = useState('');
  const [subject, setSubject] = useState('');
  const [subjects, setSubjects] = useState<string[]>([]);
  const [results, setResults] = useState<ClassSection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // Load subjects on mount
  useEffect(() => {
    getSubjects()
      .then(data => setSubjects(data.subjects))
      .catch(console.error);
  }, []);

  // Search function
	  const handleSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: ClassSearchParams = {
        search: query,
        subject: subject || undefined,
        limit: 50,
        includeRequirements: true,
      };
	      
	      const response = await searchClasses(params, jwt || undefined);
	      // Exclude TBA / arranged sections that lack concrete meeting times
	      const filtered = response.classes.filter(cls => hasMeetingTimes(cls));
	      setResults(filtered);
    } catch (err) {
      setError('Failed to load classes. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [query, subject, jwt]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      handleSearch();
    }, 500);
    return () => clearTimeout(timer);
  }, [handleSearch]);

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-200 w-full lg:w-96 shrink-0">
      {/* Header & Search */}
      <div className="p-4 border-b border-slate-200 bg-white space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-1 h-5 bg-blue-600 rounded-full" />
          <h2 className="font-semibold text-slate-800">Find Classes</h2>
        </div>
        
        <div className="relative group">
          <FiSearch className="absolute left-3 top-2.5 text-slate-400 group-focus-within:text-blue-500 w-4 h-4 transition-colors" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by code, title, or prof..."
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all"
          />
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1 group">
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full appearance-none px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:bg-white transition-all pr-8 cursor-pointer"
            >
              <option value="">All Subjects</option>
              {subjects.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <FiChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 pointer-events-none w-4 h-4 transition-colors" />
          </div>
          
          {/* Future: More filters toggle */}
          {/* <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 border rounded-lg transition-colors ${showFilters ? 'bg-blue-50 border-blue-200 text-blue-600' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
          >
            <FiFilter className="w-4 h-4" />
          </button> */}
        </div>
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <div className="flex justify-center py-8 text-slate-400">
            <FiLoader className="w-6 h-6 animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-500 text-sm">
            {error}
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-sm">
            No classes found matching your criteria.
          </div>
	        ) : (
	          results.map(cls => (
	            <ClassCard
	              key={cls.id}
	              classData={cls}
	              onAdd={onAddClass}
	              onRemove={onRemoveClass}
	              isAdded={addedClassIds.has(cls.id)}
	              conflictMessage={conflicts[cls.id]}
	              compact
	            />
	          ))
	        )}
      </div>
      
      {/* Footer Stats */}
      <div className="p-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-500 text-center">
        Showing {results.length} classes
      </div>
    </div>
  );
}
