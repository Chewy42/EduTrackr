import React, { useMemo, useState, useEffect, useRef } from 'react';
import { FiX } from 'react-icons/fi';
import { ScheduledClass, SHORT_DAY_NAMES, minutesToTime, hasMeetingTimes } from './types';
import ClassDetailsModal from './ClassDetailsModal';

interface WeeklyCalendarProps {
  classes: ScheduledClass[];
  onRemoveClass: (classId: string) => void;
}

const START_HOUR = 7; // 7 AM
const END_HOUR = 22; // 10 PM
const DEFAULT_HOUR_HEIGHT = 120; // px per hour fallback

const GRID_ROWS = END_HOUR - START_HOUR + 1; // number of hour slots to render

export default function WeeklyCalendar({ classes, onRemoveClass }: WeeklyCalendarProps) {
	  const [selectedClass, setSelectedClass] = useState<ScheduledClass | null>(null);
	  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
	  const [hourHeight, setHourHeight] = useState<number>(DEFAULT_HOUR_HEIGHT);
	  // Only keep classes that have concrete meeting times; TBA/arranged
	  // sections are filtered out entirely so they never appear in the
	  // calendar UI.
	  const scheduledClasses = useMemo(() => {
	    return classes.filter(cls => hasMeetingTimes(cls));
	  }, [classes]);

  // Check if we need weekends based only on classes that actually meet.
  const hasWeekend = useMemo(() => {
    return scheduledClasses.some(c => {
      const days = c.occurrenceData?.daysOccurring;
      return (days?.Sa?.length ?? 0) > 0 || (days?.Su?.length ?? 0) > 0;
    });
  }, [scheduledClasses]);

	  const displayDays = hasWeekend 
	    ? ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su'] as const
	    : ['M', 'Tu', 'W', 'Th', 'F'] as const;

	  // Generate time labels
	  const timeLabels = useMemo(() => {
    const labels = [];
    for (let h = START_HOUR; h <= END_HOUR; h++) {
      labels.push(h);
    }
    return labels;
  }, []);

	  // Dynamically size the calendar so that, when possible, all time slots
	  // from START_HOUR to END_HOUR fit within the visible height of the
	  // scroll container. On very small viewports we fall back to a minimum
	  // hour height and allow vertical scrolling.
	  useEffect(() => {
	    const container = scrollContainerRef.current;
	    if (!container) return;

	    const updateHeights = () => {
	      const available = container.clientHeight;
	      if (!available || Number.isNaN(available)) return;

	      const idealHourHeight = Math.floor(available / GRID_ROWS);
	      // Don't let rows get impossibly tiny; below this we accept vertical scroll.
	      const next = idealHourHeight > 0 ? Math.max(40, idealHourHeight) : DEFAULT_HOUR_HEIGHT;
	      setHourHeight(next);
	    };

	    updateHeights();

	    if (typeof ResizeObserver !== 'undefined') {
	      const observer = new ResizeObserver(() => updateHeights());
	      observer.observe(container);
	      return () => observer.disconnect();
	    }

	    window.addEventListener('resize', updateHeights);
	    return () => window.removeEventListener('resize', updateHeights);
	  }, []);

	  const pixelsPerMinute = hourHeight / 60;

		  return (
		    <div className="flex flex-col h-full min-h-0 bg-white overflow-hidden">
	      {/* Scrollable Container */}
	      <div ref={scrollContainerRef} className="flex-1 overflow-auto relative">
        <div className="min-w-[600px] flex flex-col"> {/* Min width to force horizontal scroll on small screens */}

            {/* Sticky Header */}
            <div className="flex border-b border-slate-200 sticky top-0 z-20 bg-white shadow-sm">
                <div className="w-16 shrink-0 bg-slate-50 border-r border-slate-200 sticky left-0 z-30" /> {/* Corner */}
                {displayDays.map(day => (
                <div key={day} className="flex-1 py-2 text-center border-r border-slate-200 last:border-r-0 bg-slate-50">
                    <span className="text-sm font-semibold text-slate-700">{SHORT_DAY_NAMES[day]}</span>
                </div>
                ))}
            </div>

	            {/* Calendar Body */}
		            <div className="flex" style={{ height: GRID_ROWS * hourHeight }}>
                {/* Time Column - Sticky Left */}
                <div className="w-16 shrink-0 border-r border-slate-200 bg-slate-50 select-none sticky left-0 z-10">
	                    {timeLabels.map(hour => (
                    <div 
                        key={hour} 
                        className="relative border-b border-slate-100 text-xs text-slate-400 text-right pr-2 pt-1 bg-slate-50"
	                        style={{ height: hourHeight }}
                    >
                        {hour > 12 ? hour - 12 : hour} {hour >= 12 ? 'PM' : 'AM'}
                    </div>
                    ))}
                </div>

	                {/* Days Columns */}
	                {displayDays.map(day => (
                    <div key={day} className="flex-1 relative border-r border-slate-200 last:border-r-0 min-w-[100px]">
	                    {/* Grid Lines */}
	                    {timeLabels.map(hour => (
	                        <div 
	                        key={hour} 
	                        className="border-b border-slate-100"
	                        style={{ height: hourHeight }}
	                        />
	                    ))}

                    {/* Class Blocks */}
                    {scheduledClasses.map(cls => {
                        const daySlots = cls.occurrenceData?.daysOccurring?.[day] ?? [];
                        return daySlots.map((slot, idx) => {
                        const startMinutes = slot.startTime;
                        const endMinutes = slot.endTime;
	                        const duration = endMinutes - startMinutes;
                        
	                        // Calculate position
	                        const top = (startMinutes - (START_HOUR * 60)) * pixelsPerMinute;
	                        const height = duration * pixelsPerMinute;

                        return (
                            <div
                            key={`${cls.id}-${day}-${idx}`}
                            onClick={() => setSelectedClass(cls)}
                            className="absolute inset-x-1 rounded-lg border shadow-sm p-2 overflow-hidden hover:z-10 hover:shadow-md transition-all group select-none cursor-pointer"
                            style={{
                                top: `${top}px`,
                                height: `${height}px`,
                                backgroundColor: cls.color,
                                borderColor: cls.color.replace('100', '200'), // Darker border
                            }}
                            >
                                {/* Close Button - Absolute Top Right */}
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onRemoveClass(cls.id);
                                    }}
                                    className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 p-1 hover:bg-black/5 rounded-full text-slate-600 transition-all cursor-pointer z-20"
                                >
                                    <FiX className="w-3.5 h-3.5" />
                                </button>

                                {/* Content - Vertically Centered */}
                                <div className="flex flex-col justify-center items-center h-full gap-0.5 text-center">
                                    <span className="font-bold text-sm text-slate-900 leading-tight">
                                        {cls.code}
                                    </span>
                                    <div className="text-xs text-slate-700 font-medium leading-tight">
                                        {minutesToTime(startMinutes)} - {minutesToTime(endMinutes)}
                                    </div>
                                    <div className="text-xs text-slate-600 truncate w-full px-1">
                                        {cls.location}
                                    </div>
                                </div>
                            </div>
                        );
                        });
	                    })}
                    </div>
                ))}
            </div>
        </div>
      </div>

      {/* Class Details Modal */}
      <ClassDetailsModal
        isOpen={selectedClass !== null}
        onClose={() => setSelectedClass(null)}
        classData={selectedClass}
      />
    </div>
  );
}
