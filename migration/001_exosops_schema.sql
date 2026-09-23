-- ============================================================================
-- ExosOps Schema Migration 001
-- Creates project management tables and extends existing tasks table
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'manager', 'member')),
  avatar_url TEXT,
  teamwork_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. PROJECTS TABLE
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'on_hold', 'completed', 'archived')),
  owner_id UUID REFERENCES users(id),
  start_date DATE,
  end_date DATE,
  category TEXT,
  tags TEXT[] DEFAULT '{}',
  teamwork_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. TASK LISTS TABLE
CREATE TABLE IF NOT EXISTS task_lists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  position INTEGER DEFAULT 0,
  teamwork_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. ADD NEW COLUMNS TO EXISTING TASKS TABLE
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='project_id') THEN
    ALTER TABLE tasks ADD COLUMN project_id UUID REFERENCES projects(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='task_list_id') THEN
    ALTER TABLE tasks ADD COLUMN task_list_id UUID REFERENCES task_lists(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='parent_task_id') THEN
    ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER REFERENCES tasks(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='start_date') THEN
    ALTER TABLE tasks ADD COLUMN start_date DATE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='estimated_hours') THEN
    ALTER TABLE tasks ADD COLUMN estimated_hours NUMERIC;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='logged_hours') THEN
    ALTER TABLE tasks ADD COLUMN logged_hours NUMERIC DEFAULT 0;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='progress') THEN
    ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='position') THEN
    ALTER TABLE tasks ADD COLUMN position INTEGER DEFAULT 0;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='teamwork_id') THEN
    ALTER TABLE tasks ADD COLUMN teamwork_id INTEGER;
  END IF;
END $$;

-- 5. MILESTONES TABLE
CREATE TABLE IF NOT EXISTS milestones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  due_date DATE,
  status TEXT NOT NULL DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'completed', 'overdue')),
  owner_id UUID REFERENCES users(id),
  teamwork_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. TIME ENTRIES TABLE
CREATE TABLE IF NOT EXISTS time_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id INTEGER REFERENCES tasks(id),
  user_id UUID REFERENCES users(id),
  project_id UUID REFERENCES projects(id),
  hours NUMERIC NOT NULL,
  description TEXT,
  date DATE NOT NULL,
  teamwork_id INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. COMMENTS TABLE
CREATE TABLE IF NOT EXISTS comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id),
  user_id UUID REFERENCES users(id),
  body TEXT NOT NULL,
  parent_comment_id UUID REFERENCES comments(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. FILES TABLE
CREATE TABLE IF NOT EXISTS files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  url TEXT,
  size INTEGER,
  mime_type TEXT,
  project_id UUID REFERENCES projects(id),
  task_id INTEGER REFERENCES tasks(id),
  uploaded_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 9. INDEXES
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_task_list_id ON tasks(task_list_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_task_lists_project_id ON task_lists(project_id);
CREATE INDEX IF NOT EXISTS idx_milestones_project_id ON milestones(project_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_task_id ON time_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_user_id ON time_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_comments_task_id ON comments(task_id);
CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id);

-- 9b. DATA API GRANTS (required for tables created on/after 2026-10-30)
-- Supabase stops auto-granting Data API access to NEW public tables from
-- 2026-10-30. Without these grants a table is unreachable via PostgREST /
-- supabase-js even with the service_role key. Explicit + idempotent so this
-- migration is safe on a fresh project, preview branch, or `supabase db reset`.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','projects','task_lists','milestones','time_entries','comments','files']
  LOOP
    EXECUTE format('GRANT SELECT ON public.%I TO anon;', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO authenticated;', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO service_role;', t);
  END LOOP;
END $$;

-- 10. ENABLE RLS (but allow all for now via Tailscale-only access)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;

-- Allow all operations via anon key (Tailscale protects network access)
CREATE POLICY IF NOT EXISTS "Allow all for users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for projects" ON projects FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for task_lists" ON task_lists FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for milestones" ON milestones FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for time_entries" ON time_entries FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for comments" ON comments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Allow all for files" ON files FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- DONE - Tables created. Run migration/import-teamwork.js next.
-- ============================================================================
