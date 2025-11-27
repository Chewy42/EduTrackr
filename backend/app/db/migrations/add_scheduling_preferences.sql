-- Scheduling Preferences Table
-- Stores user preferences collected during onboarding for schedule generation

create table if not exists public.scheduling_preferences (
  user_id uuid references public.app_users(id) on delete cascade primary key,
  
  -- Planning mode: 'upcoming_semester', 'four_year_plan', 'view_progress'
  planning_mode text,
  
  -- Credit preferences
  preferred_credits_min int,  -- e.g., 12
  preferred_credits_max int,  -- e.g., 15
  
  -- Schedule preferences
  preferred_time_of_day text,  -- 'morning', 'afternoon', 'evening', 'flexible'
  days_to_avoid text[],        -- e.g., ['Friday', 'Saturday']
  
  -- Work/life constraints
  work_status text,            -- 'none', 'part_time', 'full_time'
  work_hours_per_week int,
  
  -- Summer preferences
  summer_availability text,    -- 'yes', 'no', 'maybe'
  
  -- Academic focus
  priority_focus text,         -- 'major_requirements', 'electives', 'graduation_timeline'
  interest_areas text[],       -- e.g., ['AI', 'Security', 'Systems']
  
  -- Target graduation
  target_graduation_term text, -- e.g., 'Spring 2026'
  
  -- Metadata
  onboarding_complete boolean default false,
  collected_fields text[],     -- Track which fields have been collected
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- RLS Policy
alter table public.scheduling_preferences enable row level security;

drop policy if exists "Users own scheduling preferences" on public.scheduling_preferences;
create policy "Users own scheduling preferences" on public.scheduling_preferences 
  for all using (auth.uid() = user_id);

-- Index for quick lookups
create index if not exists idx_scheduling_prefs_user on public.scheduling_preferences(user_id);
