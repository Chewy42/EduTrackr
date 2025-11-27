-- Core Identity
create table if not exists public.app_users (
  id uuid references auth.users on delete cascade not null primary key,
  email text,
  first_name text,
  last_name text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Trigger to sync auth.users to public.app_users
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.app_users (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

-- Trigger setup
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- User Preferences
create table if not exists public.user_preferences (
  user_id uuid references public.app_users(id) on delete cascade primary key,
  theme text default 'dark',
  landing_view text default 'dashboard',
  stay_logged_in boolean default false,
  updated_at timestamptz default now()
);

-- Program Evaluations
create table if not exists public.program_evaluations (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.app_users(id) on delete cascade not null,
  original_filename text,
  storage_path text,
  file_size_bytes bigint,
  parsing_status text default 'pending',
  processed_at timestamptz,
  created_at timestamptz default now()
);

-- Evaluation Content (JSONB)
create table if not exists public.program_evaluation_sections (
  id bigserial primary key,
  evaluation_id uuid references public.program_evaluations(id) on delete cascade not null,
  section_name text,
  content jsonb,
  created_at timestamptz default now()
);

-- Progress Tracking
create table if not exists public.student_progress_snapshots (
  id bigserial primary key,
  user_id uuid references public.app_users(id) on delete cascade not null,
  evaluation_id uuid references public.program_evaluations(id) on delete set null,
  snapshot_date date not null,
  metric_key text not null,
  metric_value jsonb not null,
  created_at timestamptz default now()
);
create unique index if not exists idx_progress_user_metric_date 
  on public.student_progress_snapshots(user_id, metric_key, snapshot_date);

-- Chat System
create table if not exists public.chat_sessions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.app_users(id) on delete cascade not null,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

do $$
begin
  if not exists (select 1 from pg_type where typname = 'chat_sender_type') then
    create type chat_sender_type as enum ('user', 'assistant', 'system');
  end if;
end$$;

create table if not exists public.chat_messages (
  id bigserial primary key,
  session_id uuid references public.chat_sessions(id) on delete cascade not null,
  sender chat_sender_type not null,
  message_text text not null,
  created_at timestamptz default now()
);

-- RLS Policies
alter table public.app_users enable row level security;
alter table public.user_preferences enable row level security;
alter table public.program_evaluations enable row level security;
alter table public.program_evaluation_sections enable row level security;
alter table public.student_progress_snapshots enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

-- Clear existing policies to avoid conflicts if re-running
drop policy if exists "Users can view own profile" on public.app_users;
drop policy if exists "Users can update own profile" on public.app_users;
drop policy if exists "Users own preferences" on public.user_preferences;
drop policy if exists "Users own evaluations" on public.program_evaluations;
drop policy if exists "Users own evaluation sections" on public.program_evaluation_sections;
drop policy if exists "Users own progress" on public.student_progress_snapshots;
drop policy if exists "Users own chat sessions" on public.chat_sessions;
drop policy if exists "Users own chat messages" on public.chat_messages;

create policy "Users can view own profile" on public.app_users for select using (auth.uid() = id);
create policy "Users can update own profile" on public.app_users for update using (auth.uid() = id);

create policy "Users own preferences" on public.user_preferences for all using (auth.uid() = user_id);
create policy "Users own evaluations" on public.program_evaluations for all using (auth.uid() = user_id);

create policy "Users own evaluation sections" on public.program_evaluation_sections for all using (
  exists (select 1 from public.program_evaluations where id = evaluation_id and user_id = auth.uid())
);

create policy "Users own progress" on public.student_progress_snapshots for all using (auth.uid() = user_id);
create policy "Users own chat sessions" on public.chat_sessions for all using (auth.uid() = user_id);

create policy "Users own chat messages" on public.chat_messages for all using (
  exists (select 1 from public.chat_sessions where id = session_id and user_id = auth.uid())
);
