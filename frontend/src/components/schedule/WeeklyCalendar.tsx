import React, { useMemo } from 'react';
import { FiX } from 'react-icons/fi';
import { ScheduledClass, SHORT_DAY_NAMES, minutesToTime, hasMeetingTimes } from './types';

interface WeeklyCalendarProps {
  classes: ScheduledClass[];
  onRemoveClass: (classId: string) => void;
}

const START_HOUR = 7; // 7 AM
const END_HOUR = 22; // 10 PM
const HOUR_HEIGHT = 60; // px per hour
const PIXELS_PER_MINUTE = HOUR_HEIGHT / 60;

export default function WeeklyCalendar({ classes, onRemoveClass }: WeeklyCalendarProps) {
	  // Separate classes that have concrete meeting times from TBA/arranged ones.
	  const { scheduledClasses, tbaClasses } = useMemo(() => {
	    const scheduled: ScheduledClass[] = [];
	    const tba: ScheduledClass[] = [];
	    for (const cls of classes) {
	      if (hasMeetingTimes(cls)) {
	        scheduled.push(cls);
	      } else {
	        tba.push(cls);
	      }
	    }
	    return { scheduledClasses: scheduled, tbaClasses: tba };
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

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      {/* TBA / Arranged Classes - shown at TOP for visibility */}
      {tbaClasses.length > 0 && (
        <div className="border-b border-slate-200 bg-amber-50 px-4 py-3 text-xs text-slate-700 shrink-0">
          <div className="flex flex-col gap-1 mb-2 sm:flex-row sm:items-center sm:justify-between">
            <span className="font-semibold text-amber-800">
              📅 TBA / Arranged Classes ({tbaClasses.length})
            </span>
            <span className="text-[11px] text-amber-700">
              These classes don't have set meeting times
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {tbaClasses.map(cls => (
              <div
                key={cls.id}
                className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-white px-2.5 py-1 shadow-sm"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: cls.color }}
                />
                <span className="text-xs font-medium text-slate-800 truncate max-w-[140px] sm:max-w-[180px]">
                  {cls.code}
                </span>
                <span className="hidden text-[11px] text-slate-500 sm:inline truncate max-w-[160px]">
                  {cls.title}
                </span>
                <button
                  onClick={() => onRemoveClass(cls.id)}
                  className="ml-1 text-[11px] text-amber-600 hover:text-red-600 cursor-pointer"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scrollable Container */}
      <div className="flex-1 overflow-auto relative">
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
	            <div className="flex min-h-[900px]">
                {/* Time Column - Sticky Left */}
                <div className="w-16 shrink-0 border-r border-slate-200 bg-slate-50 select-none sticky left-0 z-10">
                    {timeLabels.map(hour => (
                    <div 
                        key={hour} 
                        className="relative border-b border-slate-100 text-xs text-slate-400 text-right pr-2 pt-1 bg-slate-50"
                        style={{ height: HOUR_HEIGHT }}
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
                        style={{ height: HOUR_HEIGHT }}
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
                        const top = (startMinutes - (START_HOUR * 60)) * PIXELS_PER_MINUTE;
                        const height = duration * PIXELS_PER_MINUTE;

                        return (
                            <div
                            key={`${cls.id}-${day}-${idx}`}
                            className="absolute inset-x-1 rounded-md border shadow-sm p-1.5 overflow-hidden hover:z-10 hover:shadow-md transition-all group select-none cursor-default"
                            style={{
                                top: `${top}px`,
                                height: `${height}px`,
                                backgroundColor: cls.color,
                                borderColor: cls.color.replace('100', '200'), // Darker border
                            }}
                            >
                            <div className="flex justify-between items-start">
                                <span className="font-semibold text-xs text-slate-800 leading-tight">
                                {cls.code}
                                </span>
                                <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onRemoveClass(cls.id);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-white/50 rounded text-slate-600 transition-opacity cursor-pointer"
                                >
                                <FiX className="w-3 h-3" />
                                </button>
                            </div>
                            <div className="text-[10px] text-slate-600 leading-tight mt-0.5">
                                {minutesToTime(startMinutes)} - {minutesToTime(endMinutes)}
                            </div>
                            <div className="text-[10px] text-slate-500 truncate mt-0.5">
                                {cls.location}
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
    </div>
  );
}
