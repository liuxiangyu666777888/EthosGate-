import { Component, ErrorInfo, ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import * as echarts from 'echarts'
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Gauge,
  LogOut,
  Network,
  Radar,
  RefreshCcw,
  Save,
  ShieldCheck,
  Sparkles,
  Users,
  Activity,
  ArrowUpRight,
  Clock3,
  FileWarning,
  FlaskConical,
  Database,
  BrainCircuit,
} from 'lucide-react'
import { Audit, Dashboard, Evidence, ModelConnection, ModelTestRun, ModelTestSuite, Project, login, request } from './api'

type Catalog = {
  risk_questions: Array<{ id: string; category: string; label: string }>
  reflexivity_questions: string[]
  monitoring_templates: Array<{ dimension: string; metric: string; threshold: string }>
  compliance_templates: Array<Record<string, unknown>>
}

const moduleLabels: Record<string, string> = {
  anticipation: '预测',
  reflexivity: '反思',
  inclusion: '包容',
  responsiveness: '响应',
}

const gateClass: Record<string, string> = {
  READY: 'ready',
  READY_WITH_CONDITIONS: 'conditional',
  NEEDS_REVIEW: 'review',
  BLOCKED: 'blocked',
}

function Chart({ option }: { option: echarts.EChartsOption }) {
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chart.setOption(option)
    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [option])
  return <div ref={ref} className="chart" />
}

function Field({ label, value, onChange, area = false }: { label: string; value: string; onChange: (v: string) => void; area?: boolean }) {
  return (
    <label className="field">
      <span>{label}</span>
      {area ? <textarea value={value} onChange={(e) => onChange(e.target.value)} /> : <input value={value} onChange={(e) => onChange(e.target.value)} />}
    </label>
  )
}

function Login({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('admin123456')
  const [error, setError] = useState('')
  async function submit() {
    try {
      await login(email, password)
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    }
  }
  return (
    <main className="login-shell">
      <div className="login-rail">
        <span>VALUE ALIGNMENT</span>
        <i />
        <span>RESPONSIBLE INNOVATION</span>
      </div>
      <section className="login-panel">
        <div className="login-kicker"><span className="mark"><ShieldCheck size={24} /></span>Ethics Gatehouse</div>
        <h1>LLM部署伦理评估仪表盘</h1>
        <p>面向模型部署项目的证据链、参与闭环和伦理门禁工作台。</p>
        <Field label="邮箱" value={email} onChange={setEmail} />
        <Field label="密码" value={password} onChange={setPassword} />
        {error && <p className="error">{error}</p>}
        <button className="primary" onClick={submit}>登录工作台</button>
        <div className="login-foot">
          <span>预测</span><span>反思</span><span>包容</span><span>响应</span>
        </div>
      </section>
    </main>
  )
}

export function App() {
  const [authed, setAuthed] = useState(Boolean(localStorage.getItem('ethics_token')))
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<string>('')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [active, setActive] = useState('overview')
  const [message, setMessage] = useState('')

  async function load() {
    const list = await request<Project[]>('/api/projects')
    setProjects(list)
    const id = selected || list[0]?.id
    if (id) {
      setSelected(id)
      const dash = await request<Dashboard>(`/api/projects/${id}/dashboard`)
      setDashboard(dash)
      const cat = await request<Catalog>(`/api/projects/${id}/catalog`)
      setCatalog(cat)
    }
  }

  useEffect(() => {
    if (authed) load().catch((err) => setMessage(err.message))
  }, [authed, selected])

  if (!authed) return <Login onDone={() => setAuthed(true)} />
  const project = dashboard?.project

  async function createProject() {
    const created = await request<Project>('/api/projects', { method: 'POST', body: JSON.stringify({ name: '新的LLM部署评估', description: '待补充' }) })
    setSelected(created.id)
    setMessage('项目已创建')
  }

  function logout() {
    localStorage.removeItem('ethics_token')
    setAuthed(false)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span><ShieldCheck size={21} /></span><strong>伦理评估</strong><small>RI Console</small></div>
        <button className="new" onClick={createProject}>新建项目</button>
        <div className="project-list">
          {projects.map((item) => (
            <button key={item.id} className={item.id === selected ? 'selected' : ''} onClick={() => setSelected(item.id)}>
              <strong>{item.name}</strong>
              <span>{String(item.deployment_context.domain || '未设领域')} · {item.status}</span>
            </button>
          ))}
        </div>
        {dashboard && <SidebarSnapshot dashboard={dashboard} />}
        <button className="logout" onClick={logout}><LogOut size={16} />退出</button>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Responsible Innovation Console</p>
            <h1>{project?.name || '项目工作台'}</h1>
            {project && <p className="subtitle">{String(project.governance.deployment_boundary || '请在项目设置中定义部署边界')}</p>}
          </div>
          <div className="top-actions">
            {dashboard?.gate && <span className={`gate-chip ${gateClass[dashboard.gate.status] || 'review'}`}>{dashboard.gate.status}</span>}
            <button className="ghost" onClick={() => load()}><RefreshCcw size={16} />刷新</button>
          </div>
        </header>
        {message && <div className="notice">{message}</div>}
        <nav className="tabs">
          {[
            ['overview', '总览', Gauge],
            ['setup', '设置', ClipboardCheck],
            ['anticipation', '预测', Radar],
            ['modelTest', '模型实测', FlaskConical],
            ['evidence', '证据中心', Database],
            ['reflexivity', '反思', ShieldCheck],
            ['inclusion', '包容', Users],
            ['responsiveness', '响应', Network],
            ['compliance', '法规', CheckCircle2],
            ['llm', 'LLM审计', Sparkles],
            ['report', '报告', FileText],
          ].map(([key, label, Icon]) => (
            <button key={key as string} className={active === key ? 'active' : ''} onClick={() => setActive(key as string)}>
              <Icon size={16} />{label as string}
            </button>
          ))}
        </nav>
        {project && dashboard && (
          <>
            {active === 'overview' && <Overview dashboard={dashboard} />}
            {active === 'setup' && <Setup project={project} onSaved={load} />}
            {active === 'anticipation' && catalog && <Anticipation projectId={project.id} catalog={catalog} onSaved={load} />}
            {active === 'modelTest' && <ModelTestPanel projectId={project.id} onSaved={load} />}
            {active === 'evidence' && <EvidenceCenter projectId={project.id} />}
            {active === 'reflexivity' && catalog && <SimpleModule projectId={project.id} module="reflexivity" title="价值反思" questions={catalog.reflexivity_questions} onSaved={load} />}
            {active === 'inclusion' && <Inclusion projectId={project.id} onSaved={load} />}
            {active === 'responsiveness' && catalog && <Responsiveness projectId={project.id} catalog={catalog} onSaved={load} />}
            {active === 'compliance' && <Compliance projectId={project.id} onSaved={load} />}
            {active === 'llm' && <LLMPanel projectId={project.id} />}
            {active === 'report' && <Report projectId={project.id} />}
          </>
        )}
      </main>
    </div>
  )
}

function SidebarSnapshot({ dashboard }: { dashboard: Dashboard }) {
  return (
    <div className="sidebar-snapshot">
      <p>当前门禁</p>
      <strong className={gateClass[dashboard.gate?.status || 'NEEDS_REVIEW']}>{dashboard.gate?.status || 'NEEDS_REVIEW'}</strong>
      <div>
        <span>风险</span><b>{dashboard.risk_summary.length}</b>
      </div>
      <div>
        <span>审计草稿</span><b>{dashboard.metrics.audits_draft || 0}</b>
      </div>
    </div>
  )
}

class ErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  state = { error: '' }

  static getDerivedStateFromError(error: Error) {
    return { error: error.message || '页面渲染失败' }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI crashed', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="fatal">
          <ShieldCheck size={34} />
          <h1>工作台加载失败</h1>
          <p>{this.state.error}</p>
          <button className="primary" onClick={() => window.location.reload()}>刷新页面</button>
        </main>
      )
    }
    return this.props.children
  }
}

export function RootApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}

function Overview({ dashboard }: { dashboard: Dashboard }) {
  const hasRiskData = dashboard.risk_summary.length > 0
  const radar = useMemo<echarts.EChartsOption>(() => ({
    radar: { indicator: dashboard.risk_summary.map((r) => ({ name: r.category, max: Math.max(80, r.raw, r.residual) })) },
    series: [{ type: 'radar' as const, data: [{ value: dashboard.risk_summary.map((r) => r.residual), name: '剩余风险' }], areaStyle: { opacity: 0.2 } }],
    color: ['#b54c2f'],
  }), [dashboard])
  const gate = dashboard.gate?.status || 'NEEDS_REVIEW'
  return (
    <section className="overview-grid">
      <div className="hero-band command-card">
        <div>
          <p className="eyebrow">门禁状态</p>
          <h2 className={gateClass[gate] || 'review'}>{gate}</h2>
          <p className="hero-copy">以部署边界、证据链、参与闭环和复审机制共同决定当前项目是否可推进。</p>
        </div>
        <div className="metric-row">
          <Metric icon={<FileWarning size={17} />} label="高风险项" value={dashboard.metrics.high_risks || 0} />
          <Metric icon={<AlertTriangle size={17} />} label="证据不足" value={dashboard.metrics.low_confidence || 0} />
          <Metric icon={<Users size={17} />} label="利益相关者" value={dashboard.metrics.stakeholders || 0} />
          <Metric icon={<Sparkles size={17} />} label="AI草稿" value={dashboard.metrics.audits_draft || 0} />
          <Metric icon={<FlaskConical size={17} />} label="模型实测" value={dashboard.metrics.model_test_runs || 0} />
        </div>
      </div>
      <div className="panel phase-panel">
        <h3>四维治理轨道</h3>
        {Object.entries(dashboard.progress).map(([key, done]) => (
          <div className={`progress-line ${done ? 'done' : ''}`} key={key}><span>{moduleLabels[key]}</span><b>{done ? '已完成' : '待完成'}</b></div>
        ))}
      </div>
      <div className="panel wide">
        <h3>风险雷达</h3>
        {hasRiskData ? <Chart option={radar} /> : <EmptyState title="暂无风险数据" text="进入预测模块保存至少一条风险项后，这里会显示风险雷达图。" />}
      </div>
      <div className="panel wide docket">
        <h3>门禁理由</h3>
        {(dashboard.gate?.reasons || ['尚未执行门禁评估']).map((r) => <p className="list-item" key={r}><AlertTriangle size={15} />{r}</p>)}
      </div>
      <div className="panel wide docket">
        <h3>下一步行动</h3>
        {(dashboard.gate?.required_actions || ['完成项目设置、模型实测和人工复核后重新执行门禁。']).map((r) => <p className="list-item" key={r}><Clock3 size={15} />{r}</p>)}
      </div>
      <div className="panel wide risk-ledger">
        <h3>风险台账</h3>
        {dashboard.risk_summary.length ? dashboard.risk_summary.map((item) => (
          <div className="risk-row" key={item.category}>
            <span>{item.category}</span>
            <meter min={0} max={80} value={item.residual} />
            <b>{item.residual}</b>
          </div>
        )) : <EmptyState title="台账为空" text="保存风险项后，系统会按风险类别汇总剩余风险。" />}
      </div>
    </section>
  )
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <Radar size={28} />
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  )
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return <div className="metric"><i>{icon}</i><span>{label}</span><strong>{value}</strong></div>
}

function Setup({ project, onSaved }: { project: Project; onSaved: () => void }) {
  const [name, setName] = useState(project.name)
  const [domain, setDomain] = useState(String(project.deployment_context.domain || '教育'))
  const [users, setUsers] = useState(String(project.deployment_context.users || ''))
  const [boundary, setBoundary] = useState(String(project.governance.deployment_boundary || ''))
  const [review, setReview] = useState(String(project.governance.human_review || ''))
  const [exit, setExit] = useState(String(project.governance.user_exit || ''))
  const [incident, setIncident] = useState(String(project.governance.incident_response || ''))
  async function save() {
    await request(`/api/projects/${project.id}/setup`, {
      method: 'PATCH',
      body: JSON.stringify({
        name,
        deployment_context: { ...project.deployment_context, domain, users, languages: '中文', interface: '聊天界面' },
        governance: { ...project.governance, deployment_boundary: boundary, decision_impact: '建议', human_review: review, user_exit: exit, incident_response: incident },
      }),
    })
    onSaved()
  }
  return (
    <section className="form-panel">
      <PanelHeader icon={<ClipboardCheck size={19} />} title="项目设置向导" text="先限定模型被评估的部署边界，再记录复核、申诉和事故响应责任。" />
      <Field label="项目名称" value={name} onChange={setName} />
      <Field label="部署领域" value={domain} onChange={setDomain} />
      <Field label="目标用户" value={users} onChange={setUsers} area />
      <Field label="部署边界" value={boundary} onChange={setBoundary} area />
      <Field label="人工复核机制" value={review} onChange={setReview} area />
      <Field label="用户退出/申诉机制" value={exit} onChange={setExit} area />
      <Field label="事故响应协议" value={incident} onChange={setIncident} area />
      <button className="primary" onClick={save}><Save size={16} />保存设置</button>
    </section>
  )
}

function Anticipation({ projectId, catalog, onSaved }: { projectId: string; catalog: Catalog; onSaved: () => void }) {
  const [selected, setSelected] = useState(catalog.risk_questions[0])
  const [rationale, setRationale] = useState('待补充证据')
  async function saveRisk() {
    await request(`/api/projects/${projectId}/anticipation/risks`, {
      method: 'POST',
      body: JSON.stringify({
        question_id: selected.id,
        category: selected.category,
        answer: 4,
        severity: 4,
        likelihood: 3,
        exposure: 3,
        vulnerability_weight: 1.2,
        mitigation_confidence: 0.35,
        mitigation_owner: '风险负责人',
        rationale,
        evidence_type: 'audit_record',
        evidence_link: 'internal://evidence',
        confidence: 'medium',
        assessor: '技术评估者',
        reviewer: '伦理顾问',
      }),
    })
    await request(`/api/projects/${projectId}/anticipation`, { method: 'PATCH', body: JSON.stringify({ data: { red_team: '已生成红队清单' }, human_review_notes: '预测模块已审阅', completed: true }) })
    onSaved()
  }
  return (
    <section className="form-panel">
      <PanelHeader icon={<Radar size={19} />} title="预测模块：风险与证据链" text="将抽象伦理担忧拆为严重性、可能性、暴露规模、脆弱性权重和缓解可信度。" />
      <select value={selected.id} onChange={(e) => setSelected(catalog.risk_questions.find((q) => q.id === e.target.value)!)}>{catalog.risk_questions.map((q) => <option key={q.id} value={q.id}>{q.label}</option>)}</select>
      <p className="hint">{selected.category}</p>
      <Field label="判断理由与证据说明" value={rationale} onChange={setRationale} area />
      <button className="primary" onClick={saveRisk}><Save size={16} />保存风险项并完成预测模块</button>
    </section>
  )
}

function ModelTestPanel({ projectId, onSaved }: { projectId: string; onSaved: () => void }) {
  const [connection, setConnection] = useState<ModelConnection | null>(null)
  const [runs, setRuns] = useState<ModelTestRun[]>([])
  const [suites, setSuites] = useState<ModelTestSuite[]>([])
  const [suiteId, setSuiteId] = useState('')
  const [name, setName] = useState('被测模型')
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1')
  const [modelName, setModelName] = useState('')
  const [requestStyle, setRequestStyle] = useState('openai_chat')
  const [authHeader, setAuthHeader] = useState('Authorization')
  const [authScheme, setAuthScheme] = useState('Bearer')
  const [apiKey, setApiKey] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    const conn = await request<ModelConnection | null>(`/api/projects/${projectId}/model-connection`)
    const history = await request<ModelTestRun[]>(`/api/projects/${projectId}/model-tests`)
    const testSuites = await request<ModelTestSuite[]>(`/api/projects/${projectId}/test-suites`)
    setConnection(conn)
    setRuns(history)
    setSuites(testSuites)
    setSuiteId((current) => current || testSuites[0]?.id || '')
    if (conn) {
      setName(conn.name)
      setBaseUrl(conn.base_url)
      setModelName(conn.model_name)
      setRequestStyle(conn.request_style)
      setAuthHeader(conn.auth_header)
      setAuthScheme(conn.auth_scheme)
    }
  }

  useEffect(() => { load().catch((err) => setError(err.message)) }, [projectId])

  async function saveConnection() {
    setError('')
    const saved = await request<ModelConnection>(`/api/projects/${projectId}/model-connection`, {
      method: 'PATCH',
      body: JSON.stringify({
        name,
        base_url: baseUrl,
        model_name: modelName,
        request_style: requestStyle,
        auth_header: authHeader,
        auth_scheme: authScheme,
        api_key: apiKey,
        timeout_seconds: 30,
      }),
    })
    setConnection(saved)
    await load()
  }

  async function runSuite() {
    setRunning(true)
    setError('')
    try {
      if (!connection) await saveConnection()
      const run = await request<ModelTestRun>(`/api/projects/${projectId}/model-tests/run`, {
        method: 'POST',
        body: JSON.stringify({ api_key: apiKey, suite_id: suiteId || null, suite_name: suites.find((s) => s.id === suiteId)?.name || '教育辅导LLM伦理红队测试' }),
      })
      setRuns([run, ...runs])
      await onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : '模型实测失败')
    } finally {
      setRunning(false)
    }
  }

  async function judge(run: ModelTestRun) {
    setRunning(true)
    setError('')
    try {
      const judged = await request<ModelTestRun>(`/api/projects/${projectId}/model-tests/${run.id}/judge`, { method: 'POST' })
      setRuns(runs.map((item) => (item.id === judged.id ? judged : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'LLM辅助评审失败')
    } finally {
      setRunning(false)
    }
  }

  async function review(run: ModelTestRun, reviewer_status: string) {
    await request<ModelTestRun>(`/api/projects/${projectId}/model-tests/${run.id}/review`, {
      method: 'PATCH',
      body: JSON.stringify({ reviewer_status, notes: reviewer_status === 'accepted' ? '已人工复核，可进入报告证据链。' : '已复核，需补充缓解措施后再评估。' }),
    })
    await load()
    await onSaved()
  }

  async function reviewResult(run: ModelTestRun, resultId: string, human_status: string) {
    const updated = await request<ModelTestRun>(`/api/projects/${projectId}/model-tests/${run.id}/results/${resultId}/review`, {
      method: 'PATCH',
      body: JSON.stringify({
        human_status,
        human_reviewer: '伦理顾问',
        human_notes: human_status === 'accepted' ? '已确认可作为正式证据。' : human_status === 'revised' ? '已确认存在风险或需补充缓解措施。' : '不采纳为正式证据。',
      }),
    })
    setRuns(runs.map((item) => (item.id === updated.id ? updated : item)))
    await onSaved()
  }

  const latest = runs[0]
  const selectedSuite = suites.find((suite) => suite.id === suiteId)
  return (
    <section className="model-test-grid">
      <div className="form-panel">
        <PanelHeader icon={<FlaskConical size={19} />} title="模型实测 / 红队测试" text="连接被部署模型 URL，运行基础伦理测试集，并把模型真实输出纳入证据链和门禁判断。" />
        <Field label="连接名称" value={name} onChange={setName} />
        <Field label="部署模型 Base URL" value={baseUrl} onChange={setBaseUrl} />
        <Field label="模型名称" value={modelName} onChange={setModelName} />
        <label className="field">
          <span>请求格式</span>
          <select value={requestStyle} onChange={(e) => setRequestStyle(e.target.value)}>
            <option value="openai_chat">OpenAI-compatible /chat/completions</option>
            <option value="plain_rest">普通 REST JSON</option>
          </select>
        </label>
        <div className="two-col">
          <Field label="鉴权 Header" value={authHeader} onChange={setAuthHeader} />
          <Field label="鉴权 Scheme" value={authScheme} onChange={setAuthScheme} />
        </div>
        <Field label={`API Key${connection?.api_key_hint ? `（已保存提示：${connection.api_key_hint}）` : ''}`} value={apiKey} onChange={setApiKey} />
        <label className="field">
          <span>测试套件</span>
          <select value={suiteId} onChange={(e) => setSuiteId(e.target.value)}>
            {suites.map((suite) => <option key={suite.id} value={suite.id}>{suite.name} v{suite.version}</option>)}
          </select>
        </label>
        {selectedSuite && (
          <div className="suite-card">
            <strong>{selectedSuite.domain} · {selectedSuite.cases.length} 条用例</strong>
            <span>{selectedSuite.scenario}</span>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        <div className="button-row">
          <button className="secondary" onClick={saveConnection}>保存连接</button>
          <button className="primary" disabled={running} onClick={runSuite}><FlaskConical size={16} />{running ? '测试中...' : '运行红队测试'}</button>
        </div>
      </div>
      <div className="panel model-results">
        <PanelHeader icon={<FileWarning size={19} />} title="实测结果" text="自动标记只作为初筛，最终仍需要人工复核。" />
        {!latest && <EmptyState title="尚无测试记录" text="配置 endpoint 和 API key 后运行红队测试集。" />}
        {latest && (
          <>
            <div className="run-summary">
              <Metric icon={<FlaskConical size={17} />} label="测试用例" value={latest.total_cases} />
              <Metric icon={<AlertTriangle size={17} />} label="需复核" value={latest.flagged_cases} />
            </div>
            <div className="fingerprint">
              <span>模型：{latest.model_name || modelName || '未命名'}</span>
              <span>端点指纹：{latest.endpoint_fingerprint}</span>
              <span>套件版本：{latest.suite_version}</span>
            </div>
            <p className="review-strip">人工状态：<b>{latest.reviewer_status}</b></p>
            <div className="button-row">
              <button className="secondary" disabled={running} onClick={() => judge(latest)}><BrainCircuit size={15} />LLM辅助评审草稿</button>
              <button className="secondary" onClick={() => review(latest, 'accepted')}>标记已复核</button>
              <button className="secondary" onClick={() => review(latest, 'revised')}>标记需缓解</button>
            </div>
            {latest.results.map((result) => (
              <article className={`test-result ${result.risk_signal}`} key={result.id}>
                <header><strong>{result.category}</strong><span>{result.risk_signal} · S{result.severity} · {result.human_status}</span></header>
                <p className="prompt">{result.prompt}</p>
                <p className="expected">预期安全行为：{result.expected_behavior}</p>
                <p>{result.rationale}</p>
                {result.judge_rationale && <p className="judge-draft">LLM评审草稿：{result.judge_rationale.slice(0, 360)}</p>}
                <blockquote>{result.output || result.error || '无输出'}</blockquote>
                <div className="button-row compact">
                  <button className="secondary" onClick={() => reviewResult(latest, result.id, 'accepted')}>采纳证据</button>
                  <button className="secondary" onClick={() => reviewResult(latest, result.id, 'revised')}>确认风险</button>
                  <button className="secondary" onClick={() => reviewResult(latest, result.id, 'rejected')}>不采纳</button>
                </div>
              </article>
            ))}
          </>
        )}
      </div>
    </section>
  )
}

function SimpleModule({ projectId, module, title, questions, onSaved }: { projectId: string; module: string; title: string; questions: string[]; onSaved: () => void }) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  async function save() {
    await request(`/api/projects/${projectId}/${module}`, { method: 'PATCH', body: JSON.stringify({ data: { answers }, human_review_notes: `${title}已人工确认`, completed: true }) })
    onSaved()
  }
  return (
    <section className="form-panel">
      <PanelHeader icon={<ShieldCheck size={19} />} title={title} text="记录团队的价值预设、盲点和仍未解决的价值冲突。" />
      {questions.map((q) => <Field key={q} label={q} value={answers[q] || ''} onChange={(v) => setAnswers({ ...answers, [q]: v })} area />)}
      <button className="primary" onClick={save}><Save size={16} />保存并完成人工确认</button>
    </section>
  )
}

function EvidenceCenter({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<Evidence[]>([])
  const [error, setError] = useState('')
  async function load() {
    try {
      setError('')
      setItems(await request<Evidence[]>(`/api/projects/${projectId}/evidence`))
    } catch (err) {
      setError(err instanceof Error ? err.message : '证据加载失败')
    }
  }
  useEffect(() => { load() }, [projectId])
  const formal = items.filter((item) => ['accepted', 'revised', 'documented'].includes(item.status))
  const drafts = items.filter((item) => !['accepted', 'revised', 'documented'].includes(item.status))
  return (
    <section className="evidence-grid">
      <div className="panel evidence-hero">
        <PanelHeader icon={<Database size={19} />} title="证据中心" text="把团队自评、参与闭环、模型实测和AI辅助草稿统一为可复核证据链。" />
        <div className="metric-row">
          <Metric icon={<CheckCircle2 size={17} />} label="正式证据" value={formal.length} />
          <Metric icon={<Clock3 size={17} />} label="待复核" value={drafts.length} />
        </div>
      </div>
      <div className="panel">
        <h3>正式报告证据</h3>
        {formal.length ? formal.map((item) => <EvidenceRow key={item.id} item={item} />) : <EmptyState title="暂无正式证据" text="逐条复核模型实测或完善评估证据后，这里会显示可进入报告的材料。" />}
      </div>
      <div className="panel">
        <h3>待复核材料</h3>
        {drafts.length ? drafts.map((item) => <EvidenceRow key={item.id} item={item} />) : <EmptyState title="无待复核材料" text="当前没有草稿或未确认的证据项。" />}
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  )
}

function EvidenceRow({ item }: { item: Evidence }) {
  return (
    <article className="evidence-row">
      <header><strong>{item.title}</strong><span>{item.status} · {item.confidence}</span></header>
      <p>{item.summary || '暂无摘要'}</p>
      <small>{item.source_type} · {item.report_section || '未指定报告章节'} · {item.reviewer || '未审阅'}</small>
    </article>
  )
}

function Inclusion({ projectId, onSaved }: { projectId: string; onSaved: () => void }) {
  const [concerns, setConcerns] = useState('担心模型反馈被误认为正式评价')
  async function save() {
    await request(`/api/projects/${projectId}/inclusion`, {
      method: 'PATCH',
      body: JSON.stringify({
        stakeholders: [{ name: '低权力高影响学生群体', power: 1, impact: 5, vulnerability: true, exit_difficulty: 4, priority: 'suggested', notes: '需持续参与' }],
        engagements: [{ stakeholder_group: '低权力高影响学生群体', participation_method: '访谈', key_concerns: concerns, design_response: '增加人工教师复核和申诉入口', accepted_or_rejected: 'accepted', follow_up_owner: '产品负责人' }],
        participation_plan: { cadence: '上线前、3个月、年度复审' },
        human_review_notes: '包容模块已完成',
        completed: true,
      }),
    })
    onSaved()
  }
  return (
    <section className="form-panel">
      <PanelHeader icon={<Users size={19} />} title="包容模块：参与闭环" text="把低权力高影响群体的担忧转化为可追踪的设计回应。" />
      <Field label="利益相关者主要担忧" value={concerns} onChange={setConcerns} area />
      <button className="primary" onClick={save}><Save size={16} />保存参与闭环</button>
    </section>
  )
}

function Responsiveness({ projectId, catalog, onSaved }: { projectId: string; catalog: Catalog; onSaved: () => void }) {
  async function save() {
    await request(`/api/projects/${projectId}/responsiveness`, { method: 'PATCH', body: JSON.stringify({ data: { monitoring: catalog.monitoring_templates, timeline: ['T0', 'T+1月', 'T+3月', 'T+12月'] }, human_review_notes: '响应机制已配置', completed: true }) })
    onSaved()
  }
  return (
    <section className="panel">
      <PanelHeader icon={<Activity size={19} />} title="响应模块：部署后治理" text="用监控指标、复审节奏和事故分级支撑持续校正。" />
      {catalog.monitoring_templates.map((m) => <p className="list-item" key={m.dimension}><Gauge size={15} />{m.dimension}：{m.metric}；阈值：{m.threshold}</p>)}
      <button className="primary" onClick={save}><Save size={16} />保存监控与复审计划</button>
    </section>
  )
}

function Compliance({ projectId, onSaved }: { projectId: string; onSaved: () => void }) {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([])
  useEffect(() => { request<Array<Record<string, unknown>>>(`/api/projects/${projectId}/compliance`).then(setRows) }, [projectId])
  async function save() {
    await request(`/api/projects/${projectId}/compliance`, { method: 'PATCH', body: JSON.stringify(rows.map((r) => ({ ...r, status: 'documented', reviewer_notes: r.reviewer_notes || '已记录证据状态' }))) })
    onSaved()
  }
  return (
    <section className="panel">
      <PanelHeader icon={<CheckCircle2 size={19} />} title="法规与规范映射" text="显示项目与伦理规范、监管要求之间的证据对应关系。" />
      {rows.map((r, index) => <p className="list-item" key={String(r.id || index)}><CheckCircle2 size={15} />{String(r.norm_reference)}：{String(r.status)}</p>)}
      <button className="primary" onClick={save}><Save size={16} />标记为已记录</button>
    </section>
  )
}

function LLMPanel({ projectId }: { projectId: string }) {
  const [audits, setAudits] = useState<Audit[]>([])
  const [error, setError] = useState('')
  async function load() {
    setAudits(await request<Audit[]>(`/api/projects/${projectId}/audit-log`))
  }
  useEffect(() => { load() }, [projectId])
  async function run(task: string) {
    try {
      setError('')
      await request(`/api/projects/${projectId}/llm/${task}`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'LLM调用失败')
    }
  }
  async function review(audit: Audit, status: string) {
    await request(`/api/projects/${projectId}/audit-log/${audit.id}`, { method: 'PATCH', body: JSON.stringify({ human_status: status, human_reviewer: '伦理顾问', review_notes: '已人工审阅' }) })
    await load()
  }
  return (
    <section className="panel">
      <PanelHeader icon={<Sparkles size={19} />} title="LLM辅助与审计" text="AI只提供草稿和盲点提示，所有输出必须经过人工接受、修改或拒绝。" />
      <div className="button-row">
        {['scenarios', 'blindspots', 'participation', 'report_narrative'].map((task) => <button className="secondary" key={task} onClick={() => run(task)}><Sparkles size={15} />{task}</button>)}
      </div>
      {error && <p className="error">{error}</p>}
      {audits.map((audit) => (
        <article className="audit" key={audit.id}>
          <header><strong>{audit.llm_task}</strong><span>{audit.human_status}</span></header>
          <p>{audit.output.slice(0, 420)}</p>
          <button onClick={() => review(audit, 'accepted')}>接受</button>
          <button onClick={() => review(audit, 'revised')}>标记已修改</button>
          <button onClick={() => review(audit, 'rejected')}>拒绝</button>
        </article>
      ))}
    </section>
  )
}

function Report({ projectId }: { projectId: string }) {
  const [text, setText] = useState('')
  async function load() {
    await request(`/api/projects/${projectId}/gate/evaluate`, { method: 'POST' })
    setText(await request<string>(`/api/projects/${projectId}/report/markdown`))
  }
  useEffect(() => { load() }, [projectId])
  return (
    <section className="panel">
      <PanelHeader icon={<FileText size={19} />} title="报告预览" text="报告明确区分正式证据、待复核附件和AI辅助草稿，不把未复核材料写入最终结论。" />
      <a className="secondary link" href={`http://localhost:8000/api/projects/${projectId}/report/html`} target="_blank">打开HTML报告 <ArrowUpRight size={15} /></a>
      <pre className="report">{text}</pre>
    </section>
  )
}

function PanelHeader({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="panel-header">
      <i>{icon}</i>
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
    </div>
  )
}
