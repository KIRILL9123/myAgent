import { apiRequest } from './client';

export type GoalStatus = 'ACTIVE' | 'COMPLETED' | 'PAUSED' | 'ARCHIVED';
export type ProjectStatus = 'PLANNED' | 'ACTIVE' | 'COMPLETED' | 'PAUSED' | 'ARCHIVED';

export interface Goal { id: string; title: string; description: string | null; status: GoalStatus; target_date: string | null; created_at: string; updated_at: string; completed_at: string | null; }
export interface Project { id: string; goal_id: string | null; title: string; description: string | null; status: ProjectStatus; start_date: string | null; target_date: string | null; created_at: string; updated_at: string; completed_at: string | null; }
export interface ProjectTask { id: string; title: string; description: string | null; status: string; project_id: string; deadline_at: string | null; reminder_at: string | null; }

export const fetchGoals = (status?: GoalStatus) => apiRequest<{ goals: Goal[] }>(`/api/planning/goals${status ? `?status=${status}` : ''}`);
export const createGoal = (input: Pick<Goal, 'title' | 'description' | 'target_date'>) => apiRequest<Goal>('/api/planning/goals', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const updateGoal = (id: string, input: Partial<Pick<Goal, 'title' | 'description' | 'target_date' | 'status'>>) => apiRequest<Goal>(`/api/planning/goals/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });

export const fetchProjects = (goalId?: string) => apiRequest<{ projects: Project[] }>(`/api/planning/projects${goalId ? `?goal_id=${goalId}` : ''}`);
export const createProject = (input: { title: string; goal_id?: string | null; description?: string; status?: ProjectStatus; start_date?: string | null; target_date?: string | null }) => apiRequest<Project>('/api/planning/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const updateProject = (id: string, input: Partial<Pick<Project, 'goal_id' | 'title' | 'description' | 'status' | 'start_date' | 'target_date'>>) => apiRequest<Project>(`/api/planning/projects/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const fetchProjectTasks = (id: string) => apiRequest<{ tasks: ProjectTask[] }>(`/api/planning/projects/${id}/tasks`);
export const linkTaskToProject = (projectId: string, taskId: string) => apiRequest<ProjectTask>(`/api/planning/projects/${projectId}/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId }) });
