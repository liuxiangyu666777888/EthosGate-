const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export type Project = {
  id: string
  name: string
  description: string
  status: string
  model_info: Record<string, unknown>
  deployment_context: Record<string, unknown>
  team_info: Record<string, unknown>
  governance: Record<string, unknown>
}

export type Gate = {
  status: string
  reasons: string[]
  required_actions: string[]
  unresolved_high_risks: number
  low_confidence_items: number
}

export type Dashboard = {
  project: Project
  gate: Gate | null
  progress: Record<string, boolean>
  metrics: Record<string, number>
  risk_summary: Array<{ category: string; raw: number; residual: number; count: number }>
}

export type Evidence = {
  id: string
  source_type: string
  source_id: string
  title: string
  summary: string
  status: string
  confidence: string
  reviewer: string
  report_section: string
  created_at: string
}

export type Audit = {
  id: string
  llm_task: string
  model: string
  output: string
  human_status: string
  human_reviewer: string
  review_notes: string
  created_at: string
}

export type ModelConnection = {
  id: string
  name: string
  base_url: string
  model_name: string
  request_style: string
  auth_header: string
  auth_scheme: string
  api_key_hint: string
  timeout_seconds: number
}

export type ModelTestResult = {
  id: string
  case_id: string | null
  category: string
  prompt: string
  expected_behavior: string
  output: string
  risk_signal: string
  severity: number
  rationale: string
  judge_status: string
  judge_rationale: string
  human_status: string
  human_reviewer: string
  human_notes: string
  latency_ms: number
  error: string
}

export type ModelTestRun = {
  id: string
  suite_id: string | null
  suite_version: string
  model_name: string
  endpoint_fingerprint: string
  status: string
  suite_name: string
  total_cases: number
  flagged_cases: number
  reviewer_status: string
  notes: string
  results: ModelTestResult[]
}

export type ModelTestSuite = {
  id: string
  domain: string
  name: string
  version: string
  scenario: string
  is_active: boolean
  cases: Array<{
    id: string
    suite_id: string
    category: string
    prompt: string
    expected_behavior: string
    severity: number
    tags: string[]
    target_group: string
    enabled: boolean
  }>
}

function token() {
  return localStorage.getItem('ethics_token')
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token()) headers.Authorization = `Bearer ${token()}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...headers, ...(options.headers || {}) } })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('text/')) return (await response.text()) as T
  return response.json() as Promise<T>
}

export async function login(email: string, password: string) {
  const data = await request<{ access_token: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  localStorage.setItem('ethics_token', data.access_token)
  return data
}
