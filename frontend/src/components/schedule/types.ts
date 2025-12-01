/**
 * TypeScript types for the Schedule Builder feature.
 * These types match the backend API responses for class search,
 * schedule validation, and degree requirements.
 */

// Time slot within a single day
export interface TimeSlot {
  startTime: number; // Minutes from midnight (e.g., 540 = 9:00 AM)
  endTime: number;   // Minutes from midnight
}

// Days occurring structure
export interface DaysOccurring {
  M: TimeSlot[];
  Tu: TimeSlot[];
  W: TimeSlot[];
  Th: TimeSlot[];
  F: TimeSlot[];
  Sa: TimeSlot[];
  Su: TimeSlot[];
}

// Full occurrence data for a class
export interface OccurrenceData {
  starts: number;   // Unix timestamp
  ends: number;     // Unix timestamp
  daysOccurring: DaysOccurring;
}

// Requirement badge shown on class cards
export interface RequirementBadge {
  type: 'major_core' | 'major_elective' | 'ge' | 'minor' | 'concentration' | 'other';
  label: string;      // Full label
  shortLabel: string; // Short label for badge (e.g., "Core", "GE-WI")
  color: string;      // Color name
}

// A single class section (e.g., CPSC 350-03)
export interface ClassSection {
  id: string;                        // Unique ID: "CPSC-350-03"
  code: string;                      // Display code: "CPSC 350-03"
  subject: string;                   // Subject: "CPSC"
  number: string;                    // Course number: "350"
  section: string;                   // Section: "03"
  title: string;                     // Course title
  credits: number;                   // Credit hours
  displayDays: string;               // e.g., "MWF", "TuTh"
  displayTime: string;               // e.g., "10:00am - 10:50am"
  location: string;                  // Room/building
  professor: string;                 // Instructor name
  professorRating: number | null;    // RateMyProfessor rating
  semester: string;                  // e.g., "spring2026"
  semestersOffered: string[];        // e.g., ["Spring", "Fall"]
  occurrenceData: OccurrenceData;    // Time slot data
  requirementsSatisfied: RequirementBadge[]; // Matching requirements
}

// Conflict information
export interface ConflictInfo {
  classId1: string;
  classId2: string;
  day: string;
  timeRange: string;
  message: string;
}

// Schedule validation result
export interface ScheduleValidation {
  valid: boolean;
  conflicts: ConflictInfo[];
  totalCredits: number;
  warnings: string[];
}

// Degree requirement
export interface DegreeRequirement {
  type: 'major_core' | 'major_elective' | 'ge' | 'minor' | 'concentration' | 'other';
  label: string;
  subject?: string;
  number?: string;
  title?: string;
  creditsNeeded: number;
  area?: string;
}

// User requirements summary
export interface RequirementsSummary {
  total: number;
  byType: Record<string, number>;
  requirements: DegreeRequirement[];
}

// Classes search response
export interface ClassesSearchResponse {
  classes: ClassSection[];
  total: number;
  limit: number;
  offset: number;
}

// Subjects response
export interface SubjectsResponse {
  subjects: string[];
}

// Stats response
export interface StatsResponse {
  totalClasses: number;
  subjects: number;
  avgCredits: number;
}

// Search/filter parameters
export interface ClassSearchParams {
  search?: string;
  days?: string[];
  timeStart?: number;
  timeEnd?: number;
  creditsMin?: number;
  creditsMax?: number;
  subject?: string;
  limit?: number;
  offset?: number;
  includeRequirements?: boolean;
}

// Scheduled class with additional display properties
export interface ScheduledClass extends ClassSection {
  color: string; // For calendar display
}

// Schedule state
export interface ScheduleState {
  classes: ScheduledClass[];
  totalCredits: number;
  conflicts: ConflictInfo[];
  warnings: string[];
}

// Persisted schedule snapshot (matches backend ScheduleSnapshot.to_dict)
export interface ScheduleSnapshot {
  id: string;
  userId: string;
  name: string;
  classIds: string[];
  totalCredits: number;
  classCount: number;
  createdAt: string;
  updatedAt: string;
}

// Color palette for classes on calendar
export const CLASS_COLORS = [
  '#FEE2E2', // red-100
  '#FEF3C7', // amber-100
  '#D1FAE5', // emerald-100
  '#DBEAFE', // blue-100
  '#E9D5FF', // purple-100
  '#FCE7F3', // pink-100
  '#CFFAFE', // cyan-100
  '#FEF9C3', // yellow-100
] as const;

// Requirement badge colors mapping
export const REQUIREMENT_BADGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  blue: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-200' },
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-200' },
  green: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-200' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-200' },
  gray: { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200' },
};

// Day display names
export const DAY_NAMES: Record<keyof DaysOccurring, string> = {
  M: 'Monday',
  Tu: 'Tuesday',
  W: 'Wednesday',
  Th: 'Thursday',
  F: 'Friday',
  Sa: 'Saturday',
  Su: 'Sunday',
};

// Short day names for calendar header
export const SHORT_DAY_NAMES: Record<keyof DaysOccurring, string> = {
  M: 'Mon',
  Tu: 'Tue',
  W: 'Wed',
  Th: 'Thu',
  F: 'Fri',
  Sa: 'Sat',
  Su: 'Sun',
};

// Helper: Convert minutes from midnight to display time
export function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  const period = hours < 12 ? 'AM' : 'PM';
  const displayHour = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
  return `${displayHour}:${mins.toString().padStart(2, '0')} ${period}`;
}

// Helper: Check if two time slots overlap
export function timeSlotsOverlap(slot1: TimeSlot, slot2: TimeSlot): boolean {
  return slot1.startTime < slot2.endTime && slot1.endTime > slot2.startTime;
}

// Helper: Check if two classes have a time conflict
export function hasTimeConflict(class1: ClassSection, class2: ClassSection): boolean {
  const days = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su'] as const;
  
  for (const day of days) {
    const slots1 = class1.occurrenceData.daysOccurring[day];
    const slots2 = class2.occurrenceData.daysOccurring[day];
    
    for (const slot1 of slots1) {
      for (const slot2 of slots2) {
        if (timeSlotsOverlap(slot1, slot2)) {
          return true;
        }
      }
    }
  }
  
  return false;
}

// Helper: Get active days for a class
export function getActiveDays(cls: ClassSection): (keyof DaysOccurring)[] {
  const days = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su'] as const;
  const daysOccurring = cls.occurrenceData?.daysOccurring;
  if (!daysOccurring) return [];
  return days.filter(day => {
    const slots = daysOccurring[day];
    return slots && slots.length > 0;
  });
}

// Helper: Determine if a class has any scheduled meeting times
// Classes like thesis / TBA sections will have empty day slots and should
// be treated as "unscheduled" in the weekly calendar view.
export function hasMeetingTimes(cls: ClassSection): boolean {
  return getActiveDays(cls).length > 0;
}
	
// Helper: Assign a color to a class based on its index
export function getClassColor(index: number): string {
	  return CLASS_COLORS[index % CLASS_COLORS.length] ?? CLASS_COLORS[0];
	}
	