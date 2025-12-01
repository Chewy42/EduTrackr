-- Schedule Snapshots Migration
-- Stores saved schedule snapshots for users to load later
-- Run this in the Supabase Dashboard SQL Editor

-- Create schedule_snapshots table
create table if not exists public.schedule_snapshots (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.app_users(id) on delete cascade not null,
  name text not null,
  schedule_data jsonb not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Add unique constraint to prevent duplicate snapshot names per user
create unique index if not exists idx_schedule_snapshots_user_name
  on public.schedule_snapshots(user_id, name);

-- Index for faster lookups by user
create index if not exists idx_schedule_snapshots_user_id
  on public.schedule_snapshots(user_id);

-- Enable Row Level Security
alter table public.schedule_snapshots enable row level security;

-- RLS Policy: Users can only manage their own snapshots
drop policy if exists "Users own schedule snapshots" on public.schedule_snapshots;
create policy "Users own schedule snapshots" 
  on public.schedule_snapshots 
  for all 
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Trigger to automatically update updated_at timestamp
create or replace function public.update_schedule_snapshot_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_schedule_snapshots_updated on public.schedule_snapshots;
create trigger trg_schedule_snapshots_updated
  before update on public.schedule_snapshots
  for each row execute function public.update_schedule_snapshot_updated_at();

-- Comment on table structure
comment on table public.schedule_snapshots is 'Stores saved schedule snapshots for users';
comment on column public.schedule_snapshots.name is 'User-defined name for the snapshot';
comment on column public.schedule_snapshots.schedule_data is 'JSONB containing class_ids array and metadata (total_credits, class_count)';

