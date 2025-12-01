import { describe, it, expect } from 'vitest';
import type { ClassSection, DaysOccurring, OccurrenceData } from './types';
import { hasMeetingTimes } from './types';

function makeDaysOccurring(overrides: Partial<DaysOccurring> = {}): DaysOccurring {
  const emptyDay = [] as { startTime: number; endTime: number }[];
  return {
    M: overrides.M ?? emptyDay,
    Tu: overrides.Tu ?? emptyDay,
    W: overrides.W ?? emptyDay,
    Th: overrides.Th ?? emptyDay,
    F: overrides.F ?? emptyDay,
    Sa: overrides.Sa ?? emptyDay,
    Su: overrides.Su ?? emptyDay,
  };
}

function makeOccurrenceData(days: Partial<DaysOccurring>): OccurrenceData {
  return {
    starts: 0,
    ends: 0,
    daysOccurring: makeDaysOccurring(days),
  };
}

function makeClassSection(occurrenceData: OccurrenceData): ClassSection {
  return {
    id: 'ENGR-698-01',
    code: 'ENGR 698-01',
    subject: 'ENGR',
    number: '698',
    section: '01',
    title: 'Thesis',
    credits: 3,
    displayDays: 'TBA',
    displayTime: 'TBA',
    location: 'TBA',
    professor: 'Test Professor',
    professorRating: null,
    semester: 'spring2026',
    semestersOffered: ['Spring'],
    occurrenceData,
    requirementsSatisfied: [],
  };
}

describe('hasMeetingTimes', () => {
  it('returns true when a class has at least one meeting slot', () => {
    const occ = makeOccurrenceData({
      M: [{ startTime: 600, endTime: 660 }], // 10:00am - 11:00am
    });
    const cls = makeClassSection(occ);
    expect(hasMeetingTimes(cls)).toBe(true);
  });

  it('returns false when a class has no meeting slots on any day (e.g., TBA)', () => {
    const occ = makeOccurrenceData({});
    const cls = makeClassSection(occ);
    expect(hasMeetingTimes(cls)).toBe(false);
  });

  it('returns false when occurrenceData.daysOccurring is null/undefined', () => {
    // Simulate what backend might send for TBA classes
    const cls = makeClassSection({
      starts: 0,
      ends: 0,
      daysOccurring: null as unknown as DaysOccurring,
    });
    expect(hasMeetingTimes(cls)).toBe(false);
  });

  it('returns false when occurrenceData is null/undefined', () => {
    const cls = {
      ...makeClassSection(makeOccurrenceData({})),
      occurrenceData: null as unknown as OccurrenceData,
    };
    expect(hasMeetingTimes(cls)).toBe(false);
  });
});

