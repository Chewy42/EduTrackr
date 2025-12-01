import React from 'react';
import { FiClock, FiUser, FiMapPin, FiPlus, FiTrash2, FiAlertCircle, FiCheck } from 'react-icons/fi';
import { ClassSection, REQUIREMENT_BADGE_COLORS } from './types';

interface ClassCardProps {
  classData: ClassSection;
  onAdd?: (classData: ClassSection) => void;
  onRemove?: (classId: string) => void;
  isAdded?: boolean;
  conflictMessage?: string;
  compact?: boolean;
  disabled?: boolean;
}

export default function ClassCard({
  classData,
  onAdd,
  onRemove,
  isAdded = false,
  conflictMessage,
  compact = false,
  disabled = false,
}: ClassCardProps) {
  const {
    id,
    code,
    title,
    credits,
    displayDays,
    displayTime,
    location,
    professor,
    requirementsSatisfied,
  } = classData;

  const handleCardClick = () => {
    if (!isAdded && !disabled && !conflictMessage && onAdd) {
      onAdd(classData);
    }
  };

  return (
    <div
      onClick={handleCardClick}
      className={`
        relative rounded-xl border transition-all duration-200 group
        ${conflictMessage 
          ? 'border-red-200 bg-red-50' 
          : isAdded 
            ? 'border-blue-200 bg-blue-50/50' 
            : 'border-slate-200 bg-white hover:border-blue-300 hover:shadow-md hover:scale-[1.02] active:scale-[0.98] cursor-pointer'
        }
        ${compact ? 'p-3' : 'p-4'}
      `}
    >
      {/* Header */}
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-800 text-sm">{code}</h3>
            <span className="text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {credits} cr
            </span>
          </div>
          <h4 className={`text-xs text-slate-600 line-clamp-1 ${compact ? '' : 'mt-0.5'}`}>
            {title}
          </h4>
        </div>
        
        {/* Action Button */}
        <div className="shrink-0">
          {isAdded ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRemove?.(id);
              }}
              disabled={disabled}
              className="p-1.5 text-red-500 hover:bg-red-100 rounded-lg transition-colors cursor-pointer"
              title="Remove from schedule"
            >
              <FiTrash2 className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAdd?.(classData);
              }}
              disabled={disabled || !!conflictMessage}
              className={`
                p-1.5 rounded-lg transition-colors
                ${conflictMessage 
                  ? 'text-slate-400 cursor-not-allowed' 
                  : 'text-blue-600 hover:bg-blue-100 cursor-pointer'
                }
              `}
              title={conflictMessage || "Add to schedule"}
            >
              <FiPlus className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <FiClock className="w-3.5 h-3.5 shrink-0 text-slate-400" />
          <span>
            {displayDays} {displayTime}
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <FiUser className="w-3.5 h-3.5 shrink-0 text-slate-400" />
          <span className="truncate">{professor}</span>
        </div>

        {!compact && location && (
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <FiMapPin className="w-3.5 h-3.5 shrink-0 text-slate-400" />
            <span className="truncate">{location}</span>
          </div>
        )}
      </div>

      {/* Requirements Badges */}
      {requirementsSatisfied.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {requirementsSatisfied.map((req, idx) => {
            const colors = REQUIREMENT_BADGE_COLORS[req.color] ?? REQUIREMENT_BADGE_COLORS.gray;
            if (!colors) return null;
            return (
              <span
                key={idx}
                className={`
                  text-[10px] px-1.5 py-0.5 rounded border
                  ${colors.bg} ${colors.text} ${colors.border}
                `}
                title={req.label}
              >
                {req.shortLabel}
              </span>
            );
          })}
        </div>
      )}

      {/* Conflict Warning */}
      {conflictMessage && (
        <div className="mt-2 flex items-start gap-1.5 text-xs text-red-600 bg-red-50 p-2 rounded border border-red-100">
          <FiAlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{conflictMessage}</span>
        </div>
      )}
    </div>
  );
}
