import { useState } from 'react'
import './App.css'

const navigationItems = [
  { label: 'Overview', icon: '▦' },
  { label: 'Transactions', icon: '⇄' },
  { label: 'Assessments', icon: '◈' },
  { label: 'Cases', icon: '▤' },
]

function App() {
  const [activePage, setActivePage] = useState('Overview')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon" aria-hidden="true">
            <span>◆</span>
          </div>

          <div className="brand-copy">
            <span className="brand-name">FraudGuard</span>
            <span className="brand-caption">ANALYST WORKSPACE</span>
          </div>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="navigation" aria-label="Main navigation">
          {navigationItems.map((item) => (
            <button
              className={`nav-item ${activePage === item.label ? 'active' : ''}`}
              key={item.label}
              type="button"
              onClick={() => setActivePage(item.label)}
              aria-current={activePage === item.label ? 'page' : undefined}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
              {activePage === item.label && (
                <span className="active-indicator" aria-hidden="true" />
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-dot" />
          <div>
            <p className="status-title">Rule engine</p>
            <p className="status-description">Backend connection not configured</p>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-separator">/</span>
            <strong>{activePage}</strong>
          </div>

          <div className="topbar-right">
            <span className="environment-label">LOCAL ENVIRONMENT</span>
            <div className="avatar" aria-label="Analyst">
              A
            </div>
          </div>
        </header>

        <main className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">RULE-BASED FRAUD DETECTOR</p>
              <h1>{activePage}</h1>
              <p className="page-description">
                {activePage === 'Overview'
                  ? 'Monitor transaction risk and investigate suspicious activity.'
                  : `The ${activePage.toLowerCase()} workspace will be implemented in a subsequent milestone task.`}
              </p>
            </div>

            <div className="heading-badge">
              <span className="heading-badge-dot" />
              Foundation preview
            </div>
          </div>

          {activePage === 'Overview' ? (
            <>
              <section className="metrics-grid" aria-label="Dashboard placeholders">
                <article className="metric-card">
                  <div className="metric-top">
                    <span className="metric-label">Transactions</span>
                    <span className="metric-icon blue">⇄</span>
                  </div>
                  <p className="metric-value">—</p>
                  <p className="metric-note">Awaiting API integration</p>
                </article>

                <article className="metric-card">
                  <div className="metric-top">
                    <span className="metric-label">High-risk alerts</span>
                    <span className="metric-icon red">!</span>
                  </div>
                  <p className="metric-value">—</p>
                  <p className="metric-note">Awaiting assessment data</p>
                </article>

                <article className="metric-card">
                  <div className="metric-top">
                    <span className="metric-label">Assessments</span>
                    <span className="metric-icon purple">◈</span>
                  </div>
                  <p className="metric-value">—</p>
                  <p className="metric-note">Awaiting API integration</p>
                </article>

                <article className="metric-card">
                  <div className="metric-top">
                    <span className="metric-label">Open cases</span>
                    <span className="metric-icon amber">▤</span>
                  </div>
                  <p className="metric-value">—</p>
                  <p className="metric-note">Awaiting investigation data</p>
                </article>
              </section>

              <section className="content-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Analyst workspace</h2>
                    <p>Your shared starting point for fraud monitoring.</p>
                  </div>
                  <span className="panel-tag">INITIAL SETUP</span>
                </div>

                <div className="welcome-content">
                  <div className="welcome-icon" aria-hidden="true">
                    ◆
                  </div>
                  <h3>Your dashboard foundation is ready</h3>
                  <p>
                    The shared layout and navigation are in place. Dashboard
                    metrics, transaction exploration, assessment explanations,
                    and case management will be connected in subsequent tasks.
                  </p>
                  <div className="setup-note">
                    <span className="setup-note-icon" aria-hidden="true">
                      i
                    </span>
                    No live transaction data is connected. Metrics are
                    intentionally shown as placeholders.
                  </div>
                </div>
              </section>
            </>
          ) : (
            <section className="content-panel placeholder-panel">
              <div className="placeholder-icon" aria-hidden="true">
                {navigationItems.find((item) => item.label === activePage)?.icon}
              </div>
              <h2>{activePage} workspace</h2>
              <p>
                This navigation item is working. Its feature content will be
                added by the teammate assigned to that part of the project.
              </p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setActivePage('Overview')}
              >
                Return to Overview
              </button>
            </section>
          )}

          <footer className="page-footer">
            <span>Rule-Based Fraud Detector</span>
            <span>Milestone 5 · Frontend foundation</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App