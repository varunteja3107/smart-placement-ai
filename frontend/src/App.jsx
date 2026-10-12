import { useEffect, useState } from 'react'
import {
  Activity, ArrowRight, Bell, BriefcaseBusiness, Building2,
  CheckCircle2, FileText, GraduationCap, LayoutDashboard,
  Search, ShieldCheck, Sparkles, Users
} from 'lucide-react'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const demoJobs = [
  { id: 'JOB-001', title: 'Graduate Software Engineer', company: 'TechNova Solutions', location: 'Bengaluru', package: '₹8–12 LPA', skills: ['Python', 'DSA', 'SQL'] },
  { id: 'JOB-002', title: 'AI/ML Engineering Intern', company: 'NeuralWorks', location: 'Remote', package: '₹25,000/month', skills: ['Python', 'Machine Learning'] },
  { id: 'JOB-003', title: 'Frontend Developer', company: 'PixelStack Technologies', location: 'Hyderabad', package: '₹6–9 LPA', skills: ['React', 'JavaScript', 'CSS'] },
  { id: 'JOB-004', title: 'Cloud Engineering Associate', company: 'CloudBridge', location: 'Bengaluru', package: '₹7–10 LPA', skills: ['Linux', 'Networking', 'Cloud'] },
]

export default function App() {
  const [page, setPage] = useState('Overview')
  const [jobs, setJobs] = useState(demoJobs)
  const [applications, setApplications] = useState([])
  const [applicationFilter, setApplicationFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState('')
  const [apiOnline, setApiOnline] = useState(false)
  const [student, setStudent] = useState({ name: '', email: '', cgpa: '8' })
  const [selectedJob, setSelectedJob] = useState(null)
  const [ragResults, setRagResults] = useState([])
  const [ragSources, setRagSources] = useState([])
  const [ragWarnings, setRagWarnings] = useState([])
  const [ragLoading, setRagLoading] = useState(false)
  const [ragSearched, setRagSearched] = useState(false)
  const [importSource, setImportSource] = useState('Other authorized export')
  const [importingFile, setImportingFile] = useState(false)



  useEffect(() => {
    fetch(`${API}/api/jobs`)
      .then(r => { if (!r.ok) throw Error(); return r.json() })
      .then(data => { setJobs(data); setApiOnline(true) })
      .catch(() => { setNotice('Backend offline. Showing sample jobs. Start FastAPI to enable applications.') })
    fetch(`${API}/api/applications`)
      .then(r => r.ok ? r.json() : [])
      .then(setApplications)
      .catch(() => {})
  }, [])

  const filteredJobs = jobs.filter(j =>
    `${j.title} ${j.company} ${j.location} ${(j.skills || []).join(' ')}`
      .toLowerCase().includes(search.toLowerCase())
  )

  async function apply(e) {
    e.preventDefault()
    if (!selectedJob) return
    try {
      const response = await fetch(`${API}/api/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: selectedJob.id,
          student_name: student.name,
          student_email: student.email,
          cgpa: Number(student.cgpa),
        }),
      })
      const data = await response.json()
      if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      setApplications(old => [...old, data])
      setSelectedJob(null)
      setNotice('Application submitted successfully!')
      setPage('Applications')
    } catch (err) {
      setNotice(err.message || 'Could not connect to the backend.')
    }
  }


  async function runRagSearch() {
    const query = search.trim()
    if (query.length < 2) {
      setNotice("Enter at least two characters to search.")
      return
    }

    setRagLoading(true)
    setRagSearched(false)
    setRagWarnings([])
    setNotice("")

    try {
      const response = await fetch(
        `${API}/api/rag/search?query=${encodeURIComponent(query)}&limit=12`
      )
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `Search failed (${response.status})`)
      }

      setRagResults(Array.isArray(data.results) ? data.results : [])
      setRagSources(Array.isArray(data.sources_used) ? data.sources_used : [])
      setRagWarnings(Array.isArray(data.warnings) ? data.warnings : [])
      setRagSearched(true)
    } catch (error) {
      setNotice(`AI search failed: ${error.message || "Could not connect to the backend."}`)
    } finally {
      setRagLoading(false)
    }
  }


  async function importRagFile(event) {
    const input = event.currentTarget
    const file = input.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append("file", file)
    formData.append("source_name", importSource)

    setImportingFile(true)
    setNotice("")

    try {
      const response = await fetch(`${API}/api/integrations/import`, {
        method: "POST",
        body: formData,
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || `Import failed (${response.status})`)
      }
      setNotice(
        `Imported ${data.imported_count} searchable records from ${file.name}. Run AI search to find them.`
      )
    } catch (error) {
      setNotice(`Import failed: ${error.message || "Could not reach the backend."}`)
    } finally {
      setImportingFile(false)
      input.value = ""
    }
  }

  const nav = [
    ['Overview', LayoutDashboard],
    ['Find jobs', BriefcaseBusiness],
    ['Applications', FileText],
    ['AI Career Coach', Sparkles],
    ['Companies', Building2],
  ]

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><GraduationCap /></div><div><b>Smart Placement</b><small>AI CAREER PLATFORM</small></div></div>
      <p className="nav-label">STUDENT WORKSPACE</p>
      {nav.map(([label, Icon]) => <button key={label} className={`nav ${page === label ? 'selected' : ''}`} onClick={() => setPage(label)}><Icon size={18}/>{label}{label === 'AI Career Coach' && <span className="ai-tag">AI</span>}</button>)}
      <div className="sidebar-bottom"><ShieldCheck size={19}/><div><b>Your career, your journey</b><p>Explore opportunities and keep learning.</p></div></div>
    </aside>

    <main className="main">
      <header className="topbar"><span>Workspace / <b>{page}</b></span><div className="status"><i className={apiOnline ? 'online' : ''}/>{apiOnline ? 'API connected' : 'Demo mode'} <Bell size={18}/></div></header>
      <div className="content">
        {notice && <div className="notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}

        {page === 'Overview' && <>
          <div className="welcome"><div><p className="eyebrow"><Sparkles size={15}/> YOUR CAREER, WITH CLARITY</p><h1>Make your next move<span>.</span></h1><p>Discover opportunities, track applications and prepare for your future.</p></div><button className="primary" onClick={() => setPage('Find jobs')}>Explore jobs <ArrowRight size={17}/></button></div>
          <section className="hero"><div><span className="hero-label">YOUR CAREER COPILOT</span><h2>Small steps.<br/>Big career moves.</h2><p>Discover roles that fit your skills. Build confidence for your next opportunity.</p><button className="hero-button" onClick={() => setPage('AI Career Coach')}>Explore career tools <ArrowRight size={16}/></button></div><div className="hero-art"><GraduationCap size={100}/><Sparkles size={28}/></div></section>
          <section className="metrics">
            <Metric icon={BriefcaseBusiness} label="Listed opportunities" value={jobs.length}/>
            <Metric icon={FileText} label="Applications sent" value={applications.length}/>
            <Metric icon={Building2} label="Companies hiring" value={new Set(jobs.map(j => j.company)).size}/>
            <Metric icon={Activity} label="API status" value={apiOnline ? 'Online' : 'Demo'}/>
          </section>
          <section className="panel"><div className="panel-head"><div><h2>Recommended opportunities</h2><p>Explore current demo listings</p></div><button className="link" onClick={() => setPage('Find jobs')}>View all <ArrowRight size={15}/></button></div>{jobs.slice(0,3).map(job => <Job key={job.id} job={job} onApply={setSelectedJob}/>)}</section>
          <section className="panel career-panel"><Sparkles size={22}/><div><h3>Career toolkit</h3><p>Resume feedback, skill-gap analysis and interview practice are planned for the next stage.</p></div><button className="link" onClick={() => setPage('AI Career Coach')}>Explore <ArrowRight size={15}/></button></section>
        </>}

        {page === 'Find jobs' && <>
          <h1>Find your next opportunity</h1>
          <p className="sub">Search roles by title, company, location or skill.</p>

          <div className="search">
            <Search size={19}/>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Try Python, Bengaluru, frontend..."
            />
          </div>

          <div className="rag-search-action">
            <button
              className="primary"
              type="button"
              disabled={ragLoading || search.trim().length < 2}
              onClick={runRagSearch}
            >
              <Sparkles size={16}/>
              {ragLoading ? "Searching sources..." : "Search all sources with AI"}
            </button>
            {ragLoading && <span>Checking jobs and public repositories...</span>}
          </div>

          <section className="rag-import-control">
            <div>
              <b>Import data into AI search</b>
              <p>Use an authorized export or document to add another searchable source.</p>
            </div>
            <select
              aria-label="Imported data source"
              value={importSource}
              onChange={e => setImportSource(e.target.value)}
            >
              <option>Other authorized export</option>
              <option>Google Drive export</option>
              <option>Gmail export</option>
              <option>LinkedIn export</option>
              <option>Naukri export</option>
            </select>
            <input
              aria-label="Choose export file"
              type="file"
              accept=".txt,.md,.csv,.json"
              disabled={importingFile}
              onChange={importRagFile}
            />
            <small>
              Supports TXT, Markdown, CSV and JSON up to 10 MB. Imported records are stored locally.
            </small>
          </section>

          {ragSearched && <section className="panel rag-results-panel">
            <div className="panel-head">
              <div>
                <h2>AI-powered results</h2>
                <p>Ranked by semantic relevance to your query.</p>
                <p className="rag-source-summary">
                  Sources: {ragSources.join(" · ") || "No sources returned"}
                </p>
              </div>
              <button
                className="link"
                type="button"
                onClick={() => setRagSearched(false)}
              >
                Hide results
              </button>
            </div>

            {ragWarnings.map((warning, index) => (
              <p className="rag-warning" key={`${index}-${warning}`}>{warning}</p>
            ))}

            {ragResults.length === 0 ? (
              <p>No matching results were found. Try a broader search.</p>
            ) : ragResults.map((result, index) => (
              <article
                className="job rag-result"
                key={`${result.source}-${result.id || index}`}
              >
                <div className="company-icon">
                  <span>{result.kind === "repository" ? "GH" : "AI"}</span>
                </div>

                <div className="job-info">
                  <h3>{result.title || "Untitled result"}</h3>
                  <p>
                    {[result.company, result.location, result.source]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>

                  {result.description && (
                    <p className="rag-description">
                      {result.description.replace(/<[^>]*>/g, " ").slice(0, 240)}
                      {result.description.length > 240 ? "..." : ""}
                    </p>
                  )}

                  <div className="tags">
                    {(result.skills || result.topics || [])
                      .slice(0, 5)
                      .map((skill, i) => (
                        <span key={`${result.id}-${skill}-${i}`}>{skill}</span>
                      ))}
                  </div>
                </div>

                <div className="job-action">
                  <b>{result.match_score}% match</b>

                  {result.kind === "repository" ? (
                    result.url && (
                      <a
                        className="rag-source-link"
                        href={result.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open repository ↗
                      </a>
                    )
                  ) : result.source === "Smart Placement AI" ? (
                    <button
                      type="button"
                      onClick={() => setSelectedJob({
                        id: result.id,
                        title: result.title,
                        company: result.company,
                        package: result.package || "Not disclosed",
                        location: result.location,
                        skills: result.skills || [],
                      })}
                    >
                      Apply <ArrowRight size={14}/>
                    </button>
                  ) : (
                    result.url && (
                      <a
                        className="rag-source-link"
                        href={result.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View job ↗
                      </a>
                    )
                  )}
                </div>
              </article>
            ))}
          </section>}

          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Local opportunities</h2>
                <p>Jobs available directly through Smart Placement AI.</p>
              </div>
            </div>
            {filteredJobs.map(job => (
              <Job key={job.id} job={job} onApply={setSelectedJob}/>
            ))}
            {!filteredJobs.length && <p>No matching local jobs found.</p>}
          </section>
        </>}

        {page === 'Applications' && <>
          <div className="tracker-heading">
            <p className="eyebrow"><FileText size={15}/> APPLICATION MANAGEMENT</p>
            <h1>Application tracker</h1>
            <p className="sub">Keep an eye on every opportunity you've applied for.</p>
          </div>

          <section className="metrics">
            <Metric
              icon={FileText}
              label="Total applications"
              value={applications.length}
            />
            <Metric
              icon={Activity}
              label="Applied"
              value={applications.filter(a => (a.status || 'Applied') === 'Applied').length}
            />
            <Metric
              icon={Users}
              label="Interviews"
              value={applications.filter(a => a.status === 'Interview').length}
            />
            <Metric
              icon={CheckCircle2}
              label="Selected"
              value={applications.filter(a => a.status === 'Selected').length}
            />
          </section>

          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Your submitted applications</h2>
                <p>Filter applications by their current status.</p>
              </div>
              <button className="link" onClick={() => setApplicationFilter('All')}>
                Reset filters
              </button>
            </div>

            <div className="application-tracker-controls">
              {['All', 'Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected'].map(status => (
                <button
                  key={status}
                  type="button"
                  className={`application-filter ${applicationFilter === status ? 'active' : ''}`}
                  onClick={() => setApplicationFilter(status)}
                >
                  {status}
                  <small>
                    {applications.filter(a =>
                      status === 'All' || (a.status || 'Applied') === status
                    ).length}
                  </small>
                </button>
              ))}
            </div>

            <div className="application-list">
              {applications.filter(a =>
                applicationFilter === 'All' ||
                (a.status || 'Applied') === applicationFilter
              ).length ? (
                applications
                  .filter(a =>
                    applicationFilter === 'All' ||
                    (a.status || 'Applied') === applicationFilter
                  )
                  .map((a, i) => (
                    <article className="application-card" key={a.id || i}>
                      <div className="application-icon">
                        <BriefcaseBusiness size={20} />
                      </div>
                      <div className="application-copy">
                        <b>{a.job_title || a.job_id}</b>
                        <p>{a.company || 'Company information unavailable'}</p>
                        <small>
                          Submitted: {a.created_at
                            ? new Date(a.created_at).toLocaleDateString()
                            : 'Date unavailable'}
                        </small>
                      </div>
                      <span className={`status-pill status-${(a.status || 'Applied').toLowerCase().replace(/\s+/g, '-')}`}>
                        {a.status || 'Applied'}
                      </span>
                    </article>
                  ))
              ) : (
                <div className="empty">
                  <FileText size={35} />
                  <h3>No matching applications</h3>
                  <p>There are no applications with this status yet.</p>
                  <button
                    className="primary"
                    onClick={() => setApplicationFilter('All')}
                  >
                    View all applications
                  </button>
                </div>
              )}
            </div>
          </section>
        </>}
        {page === 'AI Career Coach' && <><h1>Your AI career coach</h1><p className="sub">Career preparation tools in one place.</p><div className="tool-grid"><Tool icon={FileText} title="Resume review" desc="Get your resume ready for applications."/><Tool icon={Sparkles} title="Skill-gap planner" desc="Identify skills to learn for your target role."/><Tool icon={Users} title="Mock interviews" desc="Prepare for technical and behavioural rounds."/></div><section className="panel"><ShieldCheck/><h3>Transparent preview</h3><p>These are planned features. AI analysis is not active yet.</p></section></>}

        {page === 'Companies' && <><h1>Explore companies</h1><p className="sub">Employers represented in the current job listings.</p><div className="tool-grid">{[...new Set(jobs.map(j => j.company))].map(company => <div className="panel" key={company}><Building2/><h3>{company}</h3><p>{jobs.filter(j => j.company === company).length} listed role(s)</p><button className="link" onClick={() => {setSearch(company);setPage('Find jobs')}}>View jobs <ArrowRight size={15}/></button></div>)}</div></>}
      </div>
    </main>

    {selectedJob && <div className="modal-backdrop"><form className="modal" onSubmit={apply}><button type="button" className="close" onClick={() => setSelectedJob(null)}>×</button><p className="eyebrow">JOB APPLICATION</p><h2>{selectedJob.title}</h2><p>{selectedJob.company} · {selectedJob.package}</p><label>Full name<input required minLength="2" value={student.name} onChange={e => setStudent({...student,name:e.target.value})}/></label><label>Email address<input required type="email" value={student.email} onChange={e => setStudent({...student,email:e.target.value})}/></label><label>CGPA (out of 10)<input required type="number" min="0" max="10" step="0.01" value={student.cgpa} onChange={e => setStudent({...student,cgpa:e.target.value})}/></label><button className="primary full" type="submit">Submit application <ArrowRight size={16}/></button><small>Demo only. Do not enter sensitive personal information.</small></form></div>}
  </div>
}

function Metric({icon:Icon,label,value}) {
  return <article className="metric"><div className="metric-icon"><Icon size={20}/></div><p>{label}</p><strong>{value}</strong></article>
}

function Job({job,onApply}) {
  return <article className="job"><div className="company-icon"><BriefcaseBusiness size={22}/></div><div className="job-info"><h3>{job.title}</h3><p>{job.company} · {job.location}</p><div className="tags">{(job.skills || []).map(s => <span key={s}>{s}</span>)}</div></div><div className="job-action"><b>{job.package}</b><button onClick={() => onApply(job)}>Apply <ArrowRight size={14}/></button></div></article>
}

function Tool({icon:Icon,title,desc}) {
  return <article className="panel tool"><Icon size={24}/><h3>{title}</h3><p>{desc}</p><span>Coming in next stage</span></article>
}
