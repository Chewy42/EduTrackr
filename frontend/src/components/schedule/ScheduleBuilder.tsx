import React, { useState, useEffect, useCallback } from 'react';
import { FiAlertTriangle, FiCheckCircle, FiInfo } from 'react-icons/fi';
import { validateSchedule, getUserRequirements, generateAutoSchedule, getClassById, createScheduleSnapshot, listScheduleSnapshots, deleteScheduleSnapshot } from '../../lib/scheduleApi';
import { 
	  ScheduledClass, 
	  ClassSection, 
	  ScheduleValidation, 
	  getClassColor,
	  ConflictInfo,
	  RequirementsSummary,
	  hasMeetingTimes,
	  ScheduleSnapshot,
	} from './types';
import ClassSearchSidebar from './ClassSearchSidebar';
import WeeklyCalendar from './WeeklyCalendar';
import WarningModal from './WarningModal';
import ScheduleImpactModal from './ScheduleImpactModal';
import SnapshotManagerModal from './SnapshotManagerModal';
import { useAuth } from '../../auth/AuthContext';
import { FiTrendingUp, FiCpu, FiLoader, FiSave } from 'react-icons/fi';

export default function ScheduleBuilder() {
  const { jwt } = useAuth();
  const [scheduledClasses, setScheduledClasses] = useState<ScheduledClass[]>([]);
  const [validation, setValidation] = useState<ScheduleValidation>({
    valid: true,
    conflicts: [],
    totalCredits: 0,
    warnings: [],
  });
  const [baseRequirements, setBaseRequirements] = useState<RequirementsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<'calendar' | 'search'>('calendar');
  const [showWarnings, setShowWarnings] = useState(false);
  const [showImpact, setShowImpact] = useState(false);
	const [showSnapshots, setShowSnapshots] = useState(false);
	const [snapshots, setSnapshots] = useState<ScheduleSnapshot[]>([]);
	const [snapshotsLoading, setSnapshotsLoading] = useState(false);
	const [snapshotSaving, setSnapshotSaving] = useState(false);
	const [snapshotError, setSnapshotError] = useState<string | null>(null);

  // Load user requirements on mount
  useEffect(() => {
    if (jwt) {
      getUserRequirements(jwt)
        .then(setBaseRequirements)
        .catch(console.error);
    }
  }, [jwt]);

  // Derived state for quick lookups
  const addedClassIds = new Set(scheduledClasses.map(c => c.id));
  const conflictMap = validation.conflicts.reduce((acc, c) => {
    acc[c.classId1] = c.message;
    acc[c.classId2] = c.message;
    return acc;
  }, {} as Record<string, string>);

  // Validate whenever classes change
  useEffect(() => {
    const validate = async () => {
      if (scheduledClasses.length === 0) {
        setValidation({ valid: true, conflicts: [], totalCredits: 0, warnings: [] });
        return;
      }

      try {
        const result = await validateSchedule(scheduledClasses.map(c => c.id));
        
        // Add client-side warnings for classes that don't count
        const requirementWarnings: string[] = [];
        scheduledClasses.forEach(cls => {
          if (cls.requirementsSatisfied.length === 0) {
            requirementWarnings.push(`Class ${cls.code} does not satisfy any known degree requirements.`);
          }
        });

        setValidation({
          ...result,
          warnings: [...result.warnings, ...requirementWarnings],
        });
      } catch (err) {
        console.error('Validation failed:', err);
      }
    };

    validate();
  }, [scheduledClasses]);

	  const handleAddClass = useCallback((classData: ClassSection) => {
	    // Never allow TBA / arranged sections (no concrete meeting times)
	    if (!hasMeetingTimes(classData)) return;
	    if (addedClassIds.has(classData.id)) return;

	    setScheduledClasses(prev => {
	      const newClass: ScheduledClass = {
	        ...classData,
	        color: getClassColor(prev.length),
	      };
	      return [...prev, newClass];
	    });
	  }, [addedClassIds]);

  const handleRemoveClass = useCallback((classId: string) => {
    setScheduledClasses(prev => prev.filter(c => c.id !== classId));
  }, []);

  const handleAutoGenerate = async () => {
    if (!jwt) {
      setGenerateError('Please log in to generate a schedule');
      return;
    }
    
    setGenerating(true);
    setGenerateError(null);
    
    try {
      const { class_ids, message } = await generateAutoSchedule(jwt);
      
      if (!class_ids || class_ids.length === 0) {
        setGenerateError(message || 'No classes could be generated. Try adjusting your preferences.');
        return;
      }
      
      // Fetch full class details in parallel for better performance
      const classPromises = class_ids.map(id => 
        getClassById(id, jwt).catch(e => {
          console.error(`Failed to load class ${id}:`, e);
          return null;
        })
      );
      
	      const fetchedClasses = await Promise.all(classPromises);
	      const validClasses = fetchedClasses.filter((cls): cls is ClassSection => cls !== null);
	      
	      // Filter out any TBA / arranged sections with no concrete meeting times
	      const schedulableClasses = validClasses.filter(cls => hasMeetingTimes(cls));
	      
	      const newClasses: ScheduledClass[] = schedulableClasses.map((cls, index) => ({
	        ...cls,
	        color: getClassColor(index),
	      }));
      
	      setScheduledClasses(newClasses);
      // Switch to calendar view on mobile to show results
      setMobileView('calendar');
      
      // Show warning if not all classes loaded
      if (validClasses.length < class_ids.length) {
        console.warn(`Only loaded ${validClasses.length} of ${class_ids.length} generated classes`);
      }
      
    } catch (err) {
      console.error('Failed to generate schedule:', err);
      setGenerateError(err instanceof Error ? err.message : 'Failed to generate schedule');
    } finally {
      setGenerating(false);
    }
  };

	const refreshSnapshots = useCallback(async () => {
	  if (!jwt) return;
	  setSnapshotsLoading(true);
	  setSnapshotError(null);

	  try {
	    const data = await listScheduleSnapshots(jwt);
	    const sorted = [...data].sort(
	      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
	    );
	    setSnapshots(sorted);
	  } catch (err) {
	    console.error('Failed to load schedule snapshots:', err);
	    setSnapshotError('Failed to load schedule snapshots. Please try again.');
	  } finally {
	    setSnapshotsLoading(false);
	  }
	}, [jwt]);

	const handleOpenSnapshots = useCallback(() => {
	  if (!jwt) {
	    setSnapshotError('Please log in to save and load schedule snapshots.');
	    return;
	  }
	  setShowSnapshots(true);
	  void refreshSnapshots();
	}, [jwt, refreshSnapshots]);

	const handleSaveSnapshot = async (name: string) => {
	  if (!jwt) {
	    setSnapshotError('Please log in to save schedule snapshots.');
	    return;
	  }
	  if (scheduledClasses.length === 0) {
	    setSnapshotError('Add at least one class before saving a snapshot.');
	    return;
	  }

	  const classIds = scheduledClasses.map(c => c.id);
	  const totalCredits = validation.totalCredits;

	  setSnapshotSaving(true);
	  setSnapshotError(null);

	  try {
	    await createScheduleSnapshot(name, classIds, totalCredits, jwt);
	    await refreshSnapshots();
	  } catch (err) {
	    console.error('Failed to save schedule snapshot:', err);
	    setSnapshotError(
	      err instanceof Error ? err.message : 'Failed to save schedule snapshot.',
	    );
	  } finally {
	    setSnapshotSaving(false);
	  }
	};

	const handleLoadSnapshot = async (snapshot: ScheduleSnapshot) => {
	  if (!jwt) {
	    setSnapshotError('Please log in to load schedule snapshots.');
	    return;
	  }

	  if (!snapshot.classIds || snapshot.classIds.length === 0) {
	    setScheduledClasses([]);
	    setShowSnapshots(false);
	    return;
	  }

	  setSnapshotsLoading(true);
	  setSnapshotError(null);

	  try {
	    const classPromises = snapshot.classIds.map(id =>
	      getClassById(id, jwt).catch(err => {
	        console.error(
	          `Failed to load class ${id} from snapshot ${snapshot.id}:`,
	          err,
	        );
	        return null;
	      }),
	    );

	    const fetchedClasses = await Promise.all(classPromises);
	    const validClasses = fetchedClasses.filter(
	      (cls): cls is ClassSection => cls !== null,
	    );
	    const schedulableClasses = validClasses.filter(cls => hasMeetingTimes(cls));

	    const newClasses: ScheduledClass[] = schedulableClasses.map((cls, index) => ({
	      ...cls,
	      color: getClassColor(index),
	    }));

	    setScheduledClasses(newClasses);
	    setMobileView('calendar');
	    setShowSnapshots(false);

	    if (validClasses.length < snapshot.classIds.length) {
	      setSnapshotError(
	        'Some classes from this snapshot could not be loaded because they are no longer available.',
	      );
	    } else {
	      setSnapshotError(null);
	    }
	  } catch (err) {
	    console.error('Failed to load schedule snapshot:', err);
	    setSnapshotError('Failed to load this snapshot. Please try again.');
	  } finally {
	    setSnapshotsLoading(false);
	  }
	};

	const handleDeleteSnapshot = async (snapshot: ScheduleSnapshot) => {
	  if (!jwt) {
	    setSnapshotError('Please log in to delete schedule snapshots.');
	    return;
	  }

	  const confirmed = window.confirm(
	    `Delete snapshot "${snapshot.name}"? This cannot be undone.`,
	  );
	  if (!confirmed) return;

	  setSnapshotError(null);
	  setSnapshotsLoading(true);

	  try {
	    await deleteScheduleSnapshot(snapshot.id, jwt);
	    await refreshSnapshots();
	  } catch (err) {
	    console.error('Failed to delete schedule snapshot:', err);
	    setSnapshotError('Failed to delete snapshot. Please try again.');
	  } finally {
	    setSnapshotsLoading(false);
	  }
	};

	const handleClearSchedule = useCallback(() => {
	  if (scheduledClasses.length === 0) return;
	  const confirmed = window.confirm(
	    'Clear all classes from your current schedule? This cannot be undone.',
	  );
	  if (!confirmed) return;
	  setScheduledClasses([]);
	}, [scheduledClasses.length]);

	  return (
	    <div className="flex flex-col lg:flex-row h-full min-h-0 bg-slate-50 overflow-hidden relative">
      {/* Loading Overlay */}
      {generating && (
        <div className="absolute inset-0 z-50 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center animate-in fade-in duration-300">
          <div className="bg-white p-8 rounded-2xl shadow-2xl border border-slate-100 flex flex-col items-center max-w-sm text-center">
            <div className="relative w-16 h-16 mb-6">
              <div className="absolute inset-0 border-4 border-blue-100 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
              <FiCpu className="absolute inset-0 m-auto text-blue-600 w-6 h-6 animate-pulse" />
            </div>
            <h3 className="text-xl font-bold text-slate-800 mb-2">Generating Schedule</h3>
            <p className="text-slate-500 text-sm">
              Analyzing your requirements, preferences, and available classes to build the perfect schedule...
            </p>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {generateError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-top duration-300">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-md">
            <FiAlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{generateError}</span>
            <button 
              onClick={() => setGenerateError(null)}
              className="ml-2 text-red-500 hover:text-red-700 font-bold"
            >
              ×
            </button>
          </div>
        </div>
	      )}

	      {snapshotError && !showSnapshots && (
	        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 animate-in slide-in-from-top duration-300">
	          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-md">
	            <FiAlertTriangle className="w-5 h-5 flex-shrink-0" />
	            <span className="text-sm">{snapshotError}</span>
	            <button
	              onClick={() => setSnapshotError(null)}
	              className="ml-2 text-red-500 hover:text-red-700 font-bold"
	            >
	              ×
	            </button>
	          </div>
	        </div>
	      )}

	      {/* Mobile View Toggle */}
      <div className="lg:hidden bg-white border-b border-slate-200 p-2 flex justify-center gap-2 shrink-0">
        <button 
          onClick={() => setMobileView('calendar')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            mobileView === 'calendar' 
              ? 'bg-blue-100 text-blue-700' 
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Calendar
        </button>
        <button 
          onClick={() => setMobileView('search')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            mobileView === 'search' 
              ? 'bg-blue-100 text-blue-700' 
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Add Classes
        </button>
	        <button
	          onClick={handleAutoGenerate}
	          disabled={generating || !jwt}
	          className="px-4 py-1.5 rounded-full text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
	        >
	          {generating ? <FiLoader className="animate-spin w-3.5 h-3.5" /> : <FiCpu className="w-3.5 h-3.5" />}
	          <span>Auto</span>
	        </button>
	        <button
	          onClick={handleOpenSnapshots}
	          disabled={!jwt}
	          className="px-3 py-1.5 rounded-full text-sm font-medium border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
	          title={!jwt ? 'Please log in to save and load schedule snapshots' : 'Save and load schedule snapshots'}
	        >
	          <FiSave className="w-3.5 h-3.5" />
	          <span className="sr-only">Snapshots</span>
	        </button>
      </div>

	      {/* Main Content */}
	      <div className={`flex-1 flex flex-col min-w-0 min-h-0 ${mobileView === 'search' ? 'hidden lg:flex' : 'flex'}`}>
        {/* Toolbar / Status Bar */}
        <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center shadow-sm z-10">
          <div>
            <h1 className="text-lg font-bold text-slate-800">Spring 2026 Schedule</h1>
            <div className="flex items-center gap-4 text-sm text-slate-500 mt-0.5">
              <span className="flex items-center gap-1.5">
                <span className="font-medium text-slate-700">{scheduledClasses.length}</span> Classes
              </span>
              <span className="w-px h-3 bg-slate-300" />
              <span className="flex items-center gap-1.5">
                <span className="font-medium text-slate-700">{validation.totalCredits}</span> Credits
              </span>
              
              {/* Impact Button */}
              <button
                onClick={() => setShowImpact(true)}
                className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2 py-1 rounded transition-colors text-xs font-medium"
              >
                <FiTrendingUp className="w-3.5 h-3.5" />
                View Impact
              </button>
            </div>
          </div>

	          {/* Actions & Validation Status */}
	          <div className="flex items-center gap-3">
	            <button
	              onClick={handleAutoGenerate}
	              disabled={generating || !jwt}
	              title={!jwt ? 'Please log in to use this feature' : 'Generate a schedule based on your preferences'}
	              className="hidden md:flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-full text-sm font-medium transition-all shadow-sm hover:shadow hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
	            >
	              {generating ? <FiLoader className="animate-spin" /> : <FiCpu />}
	              <span>Auto Generate</span>
	            </button>

	            <button
	              onClick={handleOpenSnapshots}
	              disabled={!jwt}
	              title={!jwt ? 'Please log in to save and load schedule snapshots' : 'Save and load schedule snapshots'}
	              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
	            >
	              <FiSave className="w-4 h-4" />
	              <span>Snapshots</span>
	            </button>

	            <button
	              onClick={handleClearSchedule}
	              disabled={scheduledClasses.length === 0}
	              title={
	                scheduledClasses.length === 0
	                  ? 'No classes to clear'
	                  : 'Clear all classes from the current schedule'
	              }
	              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border border-slate-200 text-slate-600 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
	            >
	              <span>Clear</span>
	            </button>
	
	            {!validation.valid ? (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 px-3 py-1.5 rounded-full text-sm font-medium border border-red-100">
                <FiAlertTriangle className="w-4 h-4" />
                <span className="hidden sm:inline">{validation.conflicts.length} Conflict{validation.conflicts.length !== 1 ? 's' : ''}</span>
                <span className="sm:hidden">{validation.conflicts.length}</span>
              </div>
            ) : validation.warnings.length > 0 ? (
              <button 
                onClick={() => setShowWarnings(true)}
                className="flex items-center gap-2 text-amber-600 bg-amber-50 px-3 py-1.5 rounded-full text-sm font-medium border border-amber-100 hover:bg-amber-100 transition-colors cursor-pointer"
              >
                <FiInfo className="w-4 h-4" />
                <span className="hidden sm:inline">{validation.warnings.length} Warning{validation.warnings.length !== 1 ? 's' : ''}</span>
                <span className="sm:hidden">{validation.warnings.length}</span>
              </button>
            ) : scheduledClasses.length > 0 ? (
              <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full text-sm font-medium border border-emerald-100">
                <FiCheckCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Schedule Valid</span>
              </div>
            ) : null}
          </div>
        </div>

	        {/* Calendar View */}
	        <div className="flex-1 relative min-h-0">
          <WeeklyCalendar 
            classes={scheduledClasses}
            onRemoveClass={handleRemoveClass}
          />
        </div>
      </div>

      {/* Sidebar */}
	      <div className={`${mobileView === 'calendar' ? 'hidden lg:block' : 'block'} h-full lg:w-96 shrink-0`}>
	        <ClassSearchSidebar 
	          onAddClass={handleAddClass}
	          onRemoveClass={handleRemoveClass}
	          addedClassIds={addedClassIds}
	          conflicts={conflictMap}
	        />
	      </div>

      <WarningModal 
        isOpen={showWarnings} 
        onClose={() => setShowWarnings(false)} 
        warnings={validation.warnings} 
      />

      <ScheduleImpactModal
        isOpen={showImpact}
        onClose={() => setShowImpact(false)}
        scheduledClasses={scheduledClasses}
        baseRequirements={baseRequirements}
      />

	      <SnapshotManagerModal
	        isOpen={showSnapshots}
	        onClose={() => setShowSnapshots(false)}
	        snapshots={snapshots}
	        loading={snapshotsLoading}
	        saving={snapshotSaving}
	        error={snapshotError}
	        onRefresh={refreshSnapshots}
	        onSave={handleSaveSnapshot}
	        onLoad={handleLoadSnapshot}
	        onDelete={handleDeleteSnapshot}
	      />
    </div>
  );
}
