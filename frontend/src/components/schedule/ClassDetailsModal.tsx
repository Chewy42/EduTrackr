import React from 'react';
import { FiX, FiClock, FiMapPin, FiUser, FiBook, FiCalendar, FiAward } from 'react-icons/fi';
import { ScheduledClass } from './types';

interface ClassDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  classData: ScheduledClass | null;
}

export default function ClassDetailsModal({ isOpen, onClose, classData }: ClassDetailsModalProps) {
  if (!isOpen || !classData) return null;

  const {
    code,
    title,
    credits,
    displayDays,
    displayTime,
    location,
    professor,
    professorRating,
    requirementsSatisfied,
    color,
  } = classData;

  // Handle click on backdrop (outside modal content)
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Header with class color */}
        <div 
          className="px-6 py-4 border-b flex justify-between items-start"
          style={{ backgroundColor: color, borderColor: color.replace('100', '200') }}
        >
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-lg text-slate-800">{code}</h3>
            <p className="text-sm text-slate-600 mt-0.5 leading-snug">{title}</p>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-500 hover:text-slate-700 transition-colors p-1 hover:bg-white/50 rounded-lg ml-2 shrink-0"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Credits */}
          <div className="flex items-center gap-3 text-slate-700">
            <FiBook className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-sm">
              <span className="font-medium">{credits}</span> credit{credits !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Schedule */}
          <div className="flex items-center gap-3 text-slate-700">
            <FiCalendar className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-sm">{displayDays || 'TBA'}</span>
          </div>

          {/* Time */}
          <div className="flex items-center gap-3 text-slate-700">
            <FiClock className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-sm">{displayTime || 'TBA'}</span>
          </div>

          {/* Location */}
          <div className="flex items-center gap-3 text-slate-700">
            <FiMapPin className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-sm">{location || 'TBA'}</span>
          </div>

          {/* Professor */}
          <div className="flex items-center gap-3 text-slate-700">
            <FiUser className="w-4 h-4 text-slate-400 shrink-0" />
            <div className="text-sm">
              <span>{professor || 'TBA'}</span>
              {professorRating && (
                <span className="ml-2 text-xs text-slate-500">
                  ({professorRating.toFixed(1)} rating)
                </span>
              )}
            </div>
          </div>

          {/* Requirements Satisfied */}
          {requirementsSatisfied && requirementsSatisfied.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2 text-slate-600 mb-2">
                <FiAward className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-medium">Satisfies Requirements</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {requirementsSatisfied.map((req, idx) => (
                  <span 
                    key={idx}
                    className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100"
                  >
                    {req.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-slate-200 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

