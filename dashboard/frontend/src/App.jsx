import { useState, useEffect, useRef } from 'react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import './App.css'

const ZONE_COLORS = {
  ZONE_A: '#ef4444',
  ZONE_B: '#3b82f6',
  ZONE_C: '#22c55e',
  BETWEEN_A_B: '#a855f7',
  BETWEEN_B_C: '#06b6d4',
  BETWEEN_A_C: '#f59e0b',
  UNKNOWN: '#525252',
}

const STATE_COLORS = {
  NORMAL: '#22c55e',
  DEGRADED: '#f59e0b',
  CLOUD_OFFLINE: '#f97316',
  NO_ANCHOR: '#ef4444',
  IMU_FAIL: '#dc2626',
  INIT: '#525252',
}

const CARRY_ICONS = {
  ROLLING: '->',
  SMOOTH_ROLL: '->',
  ROUGH_ROLL: '~',
  TILTED_PUSH: '/',
  LIFTED: '^',
  PARKED: '[]',
}

const POSITION_SIZE = 220
const POSITION_PAD = 22
const POSITION_WORLD = { width: 6, height: 6 }
const ANCHORS = [
  { key: 'anchor_a_rssi', label: 'A', color: '#22c55e', x: 0.7, y: 0.7 },
  { key: 'anchor_b_rssi', label: 'B', color: '#3b82f6', x: 5.3, y: 0.7 },
  { key: 'anchor_c_rssi', label: 'C', color: '#f59e0b', x: 3.0, y: 5.3 },
]
const RSSI_REFERENCE_DBM = -56
const RSSI_PATH_LOSS = 2.2

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function rssiToDistance(rssi) {
  if (rssi == null || rssi <= -120) return null
  const meters = 10 ** ((RSSI_REFERENCE_DBM - rssi) / (10 * RSSI_PATH_LOSS))
  return clamp(meters, 0.25, 8)
}

function worldToSvg(x, y) {
  const plot = POSITION_SIZE - POSITION_PAD * 2
  return {
    x: POSITION_PAD + (x / POSITION_WORLD.width) * plot,
    y: POSITION_PAD + (y / POSITION_WORLD.height) * plot,
  }
}

function estimatePointFromRssi(sample) {
  const visible = ANCHORS
    .map(anchor => ({
      ...anchor,
      rssi: sample?.[anchor.key],
      distance: rssiToDistance(sample?.[anchor.key]),
    }))
    .filter(anchor => anchor.distance != null)

  if (visible.length < 2) return null

  if (visible.length === 2) {
    const [a, b] = visible
    const total = a.distance + b.distance || 1
    const weightA = b.distance / total
    const weightB = a.distance / total
    return {
      x: clamp(a.x * weightA + b.x * weightB, 0, POSITION_WORLD.width),
      y: clamp(a.y * weightA + b.y * weightB, 0, POSITION_WORLD.height),
      anchors: visible,
    }
  }

  const [a, b, c] = visible
  const A = 2 * (b.x - a.x)
  const B = 2 * (b.y - a.y)
  const C = a.distance ** 2 - b.distance ** 2 - a.x ** 2 + b.x ** 2 - a.y ** 2 + b.y ** 2
  const D = 2 * (c.x - a.x)
  const E = 2 * (c.y - a.y)
  const F = a.distance ** 2 - c.distance ** 2 - a.x ** 2 + c.x ** 2 - a.y ** 2 + c.y ** 2
  const det = A * E - B * D

  if (Math.abs(det) < 1e-6) return null

  return {
    x: clamp((C * E - B * F) / det, 0, POSITION_WORLD.width),
    y: clamp((A * F - C * D) / det, 0, POSITION_WORLD.height),
    anchors: visible,
  }
}

function fmtTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleTimeString()
}

function fmtDateTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString()
}

function StatCard({ label, value, unit, mono = true, color, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={color ? { color } : {}}>
        <span className={mono ? 'mono' : ''}>{value ?? '-'}</span>
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function AlertPill({ label, active, color = '#ef4444', icon }) {
  return (
    <div
      className={`alert-pill${active ? ' alert-pill-active' : ''}`}
      style={active ? {
        background: `${color}28`,
        borderColor: `${color}99`,
        color,
        boxShadow: `0 0 12px ${color}30`,
      } : {}}
    >
      {icon && <span>{icon}</span>}
      {label}
    </div>
  )
}

function RssiBar({ label, value, color }) {
  const v = value ?? -127
  const pct = v <= -127 ? 0 : Math.max(0, Math.min(100, ((v + 100) / 60) * 100))
  const strength = v > -65 ? 'Strong' : v > -80 ? 'Medium' : v > -127 ? 'Weak' : 'None'

  return (
    <div className="rssi-row">
      <div className="rssi-meta">
        <span className="rssi-anchor" style={{ color }}>{label}</span>
        <span className="rssi-strength">{strength}</span>
      </div>
      <div className="rssi-track">
        <div className="rssi-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="rssi-val">{v <= -127 ? '-' : `${v} dBm`}</span>
    </div>
  )
}

function PositionPlot({ history, currentEstimate }) {
  const pts = history
    .map(sample => estimatePointFromRssi(sample))
    .filter(Boolean)

  const renderAnchors = () => (
    <>
      {ANCHORS.map(anchor => {
        const point = worldToSvg(anchor.x, anchor.y)
        return (
          <g key={anchor.label}>
            <circle cx={point.x} cy={point.y} r="11" fill={`${anchor.color}14`} stroke={`${anchor.color}45`} />
            <circle cx={point.x} cy={point.y} r="3" fill={anchor.color} />
            <text x={point.x} y={point.y - 16} textAnchor="middle" fill={anchor.color} fontSize="12" fontWeight="700">
              {anchor.label}
            </text>
          </g>
        )
      })}
    </>
  )

  if (pts.length < 2) {
    return (
      <div className="pos-empty">
        <svg width={POSITION_SIZE} height={POSITION_SIZE} className="pos-svg">
          <rect width={POSITION_SIZE} height={POSITION_SIZE} fill="#0d0d0d" rx="12" />
          <line x1={POSITION_PAD} y1={POSITION_SIZE / 2} x2={POSITION_SIZE - POSITION_PAD} y2={POSITION_SIZE / 2} stroke="#1a1a1a" strokeWidth="1" />
          <line x1={POSITION_SIZE / 2} y1={POSITION_PAD} x2={POSITION_SIZE / 2} y2={POSITION_SIZE - POSITION_PAD} stroke="#1a1a1a" strokeWidth="1" />
          {renderAnchors()}
          <text x={POSITION_SIZE / 2} y={POSITION_SIZE / 2 - 10} textAnchor="middle" fill="#333" fontSize="11" fontFamily="Inter">
            Awaiting anchor RSSI
          </text>
          <text x={POSITION_SIZE / 2} y={POSITION_SIZE / 2 + 8} textAnchor="middle" fill="#333" fontSize="11" fontFamily="Inter">
            at least 2 anchors needed
          </text>
        </svg>
      </div>
    )
  }

  const latest = currentEstimate || pts[pts.length - 1]
  const pathD = pts.map((p, i) => {
    const { x, y } = worldToSvg(p.x, p.y)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const start = worldToSvg(pts[0].x, pts[0].y)
  const cur = worldToSvg(latest.x, latest.y)
  const plot = POSITION_SIZE - POSITION_PAD * 2

  return (
    <svg width={POSITION_SIZE} height={POSITION_SIZE} className="pos-svg">
      <rect width={POSITION_SIZE} height={POSITION_SIZE} fill="#0d0d0d" rx="12" />
      <line x1={POSITION_PAD} y1={POSITION_SIZE / 2} x2={POSITION_SIZE - POSITION_PAD} y2={POSITION_SIZE / 2} stroke="#1a1a1a" strokeWidth="1" />
      <line x1={POSITION_SIZE / 2} y1={POSITION_PAD} x2={POSITION_SIZE / 2} y2={POSITION_SIZE - POSITION_PAD} stroke="#1a1a1a" strokeWidth="1" />
      <defs>
        <linearGradient id="trailGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.8" />
        </linearGradient>
      </defs>
      {renderAnchors()}
      <path d={pathD} fill="none" stroke="url(#trailGrad)" strokeWidth="1.5" />
      <circle cx={start.x} cy={start.y} r="2.5" fill="#333" />
      {latest.anchors?.map(anchor => {
        const center = worldToSvg(anchor.x, anchor.y)
        return (
          <circle
            key={`ring-${anchor.label}`}
            cx={center.x}
            cy={center.y}
            r={(anchor.distance / POSITION_WORLD.width) * plot}
            fill="none"
            stroke={`${anchor.color}28`}
            strokeWidth="1"
            strokeDasharray="4 6"
          />
        )
      })}
      <circle cx={cur.x} cy={cur.y} r="5" fill="#2563eb" />
      <circle cx={cur.x} cy={cur.y} r="9" fill="none" stroke="#2563eb" strokeWidth="1" opacity="0.35" />
    </svg>
  )
}

const ChartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tip">
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.stroke || p.fill }}>
          {p.name}: <strong>{typeof p.value === 'number' ? p.value.toFixed(3) : p.value}</strong>
        </div>
      ))}
    </div>
  )
}

async function postConfig(payload) {
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

function QuickActions() {
  const [busy, setBusy] = useState(null)

  const action = (key, payload) => async () => {
    setBusy(key)
    await postConfig(payload).catch(() => {})
    setTimeout(() => setBusy(null), 1500)
  }

  const actions = [
    {
      key: 'locate',
      label: 'Locate Trolley',
      sub: 'Short buzz and screen pulse',
      color: '#3b82f6',
      payload: { actuatorEnabled: true, actuatorPulseMs: 400, displayFlashMs: 800 },
    },
    {
      key: 'alert',
      label: 'Alert Customer',
      sub: 'Flash screen and alert',
      color: '#f59e0b',
      payload: { actuatorEnabled: true, actuatorPulseMs: 2000, displayFlashMs: 3000 },
    },
    {
      key: 'stop',
      label: 'Silence Actuator',
      sub: 'Disable buzzer/motor',
      color: '#ef4444',
      payload: { actuatorEnabled: false },
    },
    {
      key: 'slow',
      label: 'Sensitivity: Low',
      sub: 'Busy store — fewer alerts',
      color: '#a855f7',
      payload: { pickupAccelThreshold: 3.5, dropImpactThreshold: 5.5, queueDwellThreshold: 6000 },
    },
    {
      key: 'normal',
      label: 'Sensitivity: Normal',
      sub: 'Default thresholds',
      color: '#22c55e',
      payload: { pickupAccelThreshold: 2.5, dropImpactThreshold: 4.0, queueDwellThreshold: 3000 },
    },
    {
      key: 'high',
      label: 'Sensitivity: High',
      sub: 'Quiet store — more alerts',
      color: '#06b6d4',
      payload: { pickupAccelThreshold: 1.5, dropImpactThreshold: 2.5, queueDwellThreshold: 1500 },
    },
  ]

  return (
    <div className="quick-actions">
      <div className="section-eyebrow" style={{ marginBottom: 14 }}>Quick Actions</div>
      <div className="qa-grid">
        {actions.map(a => (
          <button
            key={a.key}
            className={`qa-btn${busy === a.key ? ' qa-btn-busy' : ''}`}
            style={{ '--qa-color': a.color }}
            onClick={action(a.key, a.payload)}
            disabled={busy !== null}
          >
            <span className="qa-label">{a.label}</span>
            <span className="qa-sub">{busy === a.key ? 'Sent' : a.sub}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function ConfigPanel() {
  const [form, setForm] = useState({
    pickupAccelThreshold: '',
    dropImpactThreshold: '',
    queueDwellThreshold: '',
    dwellAlertThreshold: '',
    rssiScanIntervalMs: '',
    actuatorEnabled: '',
    actuatorPulseMs: '',
    displayFlashMs: '',
    directHost: '',
    directEnabled: '',
  })
  const [status, setStatus] = useState(null)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    const intKeys = ['queueDwellThreshold', 'dwellAlertThreshold', 'rssiScanIntervalMs', 'actuatorPulseMs', 'displayFlashMs']
    const strKeys = ['directHost']
    const boolKeys = ['actuatorEnabled', 'directEnabled']
    const payload = {}
    for (const [k, v] of Object.entries(form)) {
      if (v === '') continue
      if (boolKeys.includes(k)) payload[k] = v === 'true'
      else if (strKeys.includes(k)) payload[k] = v
      else if (intKeys.includes(k)) payload[k] = parseInt(v, 10)
      else payload[k] = parseFloat(v)
    }
    if (!Object.keys(payload).length) return

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      setStatus(data.status === 'published' ? 'Published' : data.message)
    } catch (err) {
      setStatus(err.message)
    }
    setTimeout(() => setStatus(null), 3000)
  }

  const fields = [
    { key: 'pickupAccelThreshold', label: 'Pickup Accel', placeholder: '2.5' },
    { key: 'dropImpactThreshold', label: 'Drop Impact', placeholder: '4.0' },
    { key: 'queueDwellThreshold', label: 'Queue Dwell (ms)', placeholder: '3000' },
    { key: 'dwellAlertThreshold', label: 'Dwell Alert (ms)', placeholder: '4000' },
    { key: 'rssiScanIntervalMs', label: 'RSSI Interval (ms)', placeholder: '5000' },
    { key: 'actuatorPulseMs', label: 'Actuator Pulse (ms)', placeholder: '200' },
    { key: 'displayFlashMs', label: 'Display Flash (ms)', placeholder: '1500' },
  ]

  return (
    <section className="config-section">
      <div className="config-header">
        <div>
          <div className="section-eyebrow">Remote Configuration</div>
          <h2 className="section-heading">Device Controls</h2>
        </div>
        <div className="config-target">trolley_01</div>
      </div>

      <QuickActions />

      <div className="divider" style={{ margin: '20px 0' }} />

      <div className="section-eyebrow" style={{ marginBottom: 14 }}>Advanced Settings</div>
      <form onSubmit={handleSubmit}>
        <div className="config-grid">
          {fields.map(f => (
            <div key={f.key} className="config-field">
              <label>{f.label}</label>
              <input
                type="number"
                step="any"
                placeholder={f.placeholder}
                value={form[f.key]}
                onChange={set(f.key)}
              />
            </div>
          ))}
          <div className="config-field">
            <label>Actuator</label>
            <select value={form.actuatorEnabled} onChange={set('actuatorEnabled')}>
              <option value="">No change</option>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>
          <div className="config-field config-field-wide">
            <label>Direct Stream Host (IP of backend, port 4210)</label>
            <input
              type="text"
              placeholder="192.168.x.x"
              value={form.directHost}
              onChange={set('directHost')}
            />
          </div>
          <div className="config-field">
            <label>Direct Stream</label>
            <select value={form.directEnabled} onChange={set('directEnabled')}>
              <option value="">No change</option>
              <option value="true">Enable (50 ms)</option>
              <option value="false">Disable</option>
            </select>
          </div>
        </div>
        <div className="config-actions">
          <button type="submit" className="btn-primary">
            Publish Config
          </button>
          {status && (
            <span className="config-feedback">
              <span className="feedback-dot" />
              {status}
            </span>
          )}
        </div>
      </form>
    </section>
  )
}

// ── Event type helpers ──────────────────────────────────────────────────────
function getEventTypes(row) {
  const types = []
  if (row.pickup) types.push({ label: 'Pickup', color: '#f59e0b' })
  if (row.drop_down) types.push({ label: 'Drop', color: '#ef4444' })
  if (row.queue_detect) types.push({ label: 'Queue', color: '#a855f7' })
  if (row.browsing) types.push({ label: 'Browsing', color: '#3b82f6' })
  return types
}

// ── History & Analytics section ─────────────────────────────────────────────
function HistorySection() {
  const [tab, setTab] = useState('charts')
  const [limit, setLimit] = useState(200)
  const [data, setData] = useState([])
  const [stats, setStats] = useState(null)
  const [loadingData, setLoadingData] = useState(false)

  useEffect(() => {
    setLoadingData(true)
    fetch(`/api/telemetry/history?limit=${limit}`)
      .then(r => r.json())
      .then(rows => setData([...rows].reverse()))
      .catch(() => {})
      .finally(() => setLoadingData(false))
  }, [limit])

  useEffect(() => {
    fetch('/api/telemetry/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  // Derived: zone distribution
  const zoneCounts = {}
  data.forEach(r => { if (r.zone) zoneCounts[r.zone] = (zoneCounts[r.zone] || 0) + 1 })
  const zoneData = Object.entries(zoneCounts)
    .map(([zone, count]) => ({ zone, count }))
    .sort((a, b) => b.count - a.count)

  // Derived: events list
  const events = data
    .filter(r => r.pickup || r.drop_down || r.queue_detect || r.browsing)
    .slice().reverse().slice(0, 100)

  // Chart data (sample every N for performance if large)
  const step = data.length > 500 ? Math.ceil(data.length / 500) : 1
  const chartData = data.filter((_, i) => i % step === 0)

  return (
    <section className="history-section">
      {/* DB Stats row */}
      {stats && stats.total > 0 && (
        <div className="db-stats-row">
          <div className="db-badge">MySQL RDS</div>
          <div className="db-stat"><span className="db-stat-val">{stats.total.toLocaleString()}</span><span className="db-stat-key">Records</span></div>
          <div className="db-stat"><span className="db-stat-val">{stats.avg_speed_mps}</span><span className="db-stat-key">Avg Speed m/s</span></div>
          <div className="db-stat"><span className="db-stat-val">{stats.avg_cadence_spm}</span><span className="db-stat-key">Avg Cadence spm</span></div>
          <div className="db-stat"><span className="db-stat-val">{stats.max_distance_m}</span><span className="db-stat-key">Max Distance m</span></div>
          <div className="db-stat"><span className="db-stat-val" style={{ color: '#f59e0b' }}>{stats.pickup_count}</span><span className="db-stat-key">Pickups</span></div>
          <div className="db-stat"><span className="db-stat-val" style={{ color: '#ef4444' }}>{stats.drop_count}</span><span className="db-stat-key">Drops</span></div>
          <div className="db-stat"><span className="db-stat-val" style={{ color: '#a855f7' }}>{stats.queue_count}</span><span className="db-stat-key">Queue Events</span></div>
        </div>
      )}

      <div className="history-header">
        <div>
          <div className="section-eyebrow">Historical Analysis</div>
          <h2 className="section-heading">Data History</h2>
        </div>
        <div className="history-controls">
          <div className="limit-select">
            <span className="limit-label">Show</span>
            {[100, 200, 500, 1000].map(n => (
              <button
                key={n}
                className={`limit-btn${limit === n ? ' active' : ''}`}
                onClick={() => setLimit(n)}
              >
                {n}
              </button>
            ))}
          </div>
          <a href="/api/telemetry/export?format=csv" className="btn-download" download="telemetry.csv">
            Download CSV
          </a>
          <a href="/api/telemetry/export?format=json" className="btn-download btn-download-sec" download="telemetry.json">
            Download JSON
          </a>
        </div>
      </div>

      <div className="tab-bar">
        {[
          { key: 'charts', label: 'Charts' },
          { key: 'events', label: `Events${events.length ? ` (${events.length})` : ''}` },
          { key: 'table', label: 'Data Table' },
        ].map(t => (
          <button
            key={t.key}
            className={`tab-btn${tab === t.key ? ' active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loadingData && <div className="hist-loading">Loading…</div>}

      {!loadingData && tab === 'charts' && (
        <div className="hist-charts">
          <div className="panel hist-chart-panel">
            <div className="chart-header">
              <div>
                <div className="panel-label">Step Cadence</div>
                <div className="chart-sub">{chartData.length} readings</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="cadGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 6" stroke="#1a1a1a" />
                <XAxis dataKey="id" hide />
                <YAxis stroke="#333" fontSize={10} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="step_cadence_spm"
                  stroke="#7c3aed"
                  fill="url(#cadGrad)"
                  strokeWidth={1.5}
                  dot={false}
                  name="Cadence (spm)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="panel hist-chart-panel">
            <div className="chart-header">
              <div>
                <div className="panel-label">Distance Over Time</div>
                <div className="chart-sub">{chartData.length} readings</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="distGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 6" stroke="#1a1a1a" />
                <XAxis dataKey="id" hide />
                <YAxis stroke="#333" fontSize={10} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="distance_m"
                  stroke="#22c55e"
                  fill="url(#distGrad)"
                  strokeWidth={1.5}
                  dot={false}
                  name="Distance (m)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="panel hist-chart-panel">
            <div className="panel-label">Zone Distribution</div>
            {zoneData.length === 0 ? (
              <div className="hist-empty">No zone data</div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={zoneData} margin={{ top: 4, right: 4, bottom: 20, left: -20 }}>
                  <CartesianGrid strokeDasharray="2 6" stroke="#1a1a1a" vertical={false} />
                  <XAxis dataKey="zone" stroke="#333" fontSize={9} tick={{ fill: '#525252' }} angle={-15} textAnchor="end" />
                  <YAxis stroke="#333" fontSize={10} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Readings" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                    {zoneData.map(entry => (
                      <Cell key={entry.zone} fill={ZONE_COLORS[entry.zone] || '#525252'} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}

      {!loadingData && tab === 'events' && (
        <div className="hist-events">
          {events.length === 0 ? (
            <div className="hist-empty">No events recorded in this range</div>
          ) : (
            <div className="event-list">
              <div className="event-list-header">
                <span>Time</span>
                <span>Event</span>
                <span>Zone</span>
                <span>Speed</span>
                <span>Carry</span>
              </div>
              {events.map(row => {
                const types = getEventTypes(row)
                return (
                  <div key={row.id} className="event-row">
                    <span className="event-time">{fmtTime(row.received_at)}</span>
                    <span className="event-types">
                      {types.map(t => (
                        <span key={t.label} className="event-pill" style={{ background: `${t.color}22`, color: t.color, borderColor: `${t.color}55` }}>
                          {t.label}
                        </span>
                      ))}
                    </span>
                    <span className="event-zone" style={{ color: ZONE_COLORS[row.zone] || '#525252' }}>
                      {row.zone || '-'}
                    </span>
                    <span className="event-speed">{row.speed_mps != null ? row.speed_mps.toFixed(3) + ' m/s' : '-'}</span>
                    <span className="event-carry">{row.carry_style || '-'}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {!loadingData && tab === 'table' && (
        <div className="hist-table-wrap">
          <div className="table-info">
            Showing {data.length} records from MySQL RDS
            <span className="table-note">Download all records using the buttons above</span>
          </div>
          <div className="data-table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Device</th>
                  <th>Speed</th>
                  <th>Cadence</th>
                  <th>Distance</th>
                  <th>Zone</th>
                  <th>Carry</th>
                  <th>Events</th>
                  <th>Anchors</th>
                  <th>IMU</th>
                </tr>
              </thead>
              <tbody>
                {data.slice().reverse().map(row => {
                  const evts = getEventTypes(row)
                  return (
                    <tr key={row.id}>
                      <td className="td-time">{fmtTime(row.received_at)}</td>
                      <td className="td-mono">{row.device_id || '-'}</td>
                      <td className="td-mono">{row.speed_mps != null ? row.speed_mps.toFixed(3) : '-'}</td>
                      <td className="td-mono">{row.step_cadence_spm != null ? row.step_cadence_spm.toFixed(1) : '-'}</td>
                      <td className="td-mono">{row.distance_m != null ? row.distance_m.toFixed(2) : '-'}</td>
                      <td style={{ color: ZONE_COLORS[row.zone] || '#525252' }}>{row.zone || '-'}</td>
                      <td>{row.carry_style || '-'}</td>
                      <td>
                        {evts.length > 0
                          ? evts.map(t => (
                            <span key={t.label} className="tbl-pill" style={{ color: t.color }}>
                              {t.label[0]}
                            </span>
                          ))
                          : <span className="td-none">-</span>
                        }
                      </td>
                      <td className="td-mono">{row.anchors_seen ?? '-'}/3</td>
                      <td style={{ color: row.imu_ok ? '#22c55e' : row.imu_ok === false ? '#ef4444' : '#525252' }}>
                        {row.imu_ok == null ? '-' : row.imu_ok ? 'OK' : 'FAIL'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}

export default function App() {
  const [live, setLive] = useState(null)
  const [connected, setConnected] = useState(false)
  const [history, setHistory] = useState([])
  const [updateRateMs, setUpdateRateMs] = useState(null)
  const wsRef = useRef(null)
  const lastMsgRef = useRef(null)

  useEffect(() => {
    fetch('/api/telemetry/history?limit=200')
      .then(r => r.json())
      .then(data => setHistory([...data].reverse()))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
    const connect = () => {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      ws.onopen = () => setConnected(true)
      ws.onclose = () => { setConnected(false); setTimeout(connect, 3000) }
      ws.onerror = () => ws.close()
      ws.onmessage = e => {
        try {
          const data = JSON.parse(e.data)
          setLive(data)
          setHistory(h => [...h, data].slice(-300))
          const now = Date.now()
          if (lastMsgRef.current) setUpdateRateMs(now - lastMsgRef.current)
          lastMsgRef.current = now
        } catch {
          // ignore malformed websocket payloads
        }
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const d = live || {}
  const chartData = history.slice(-120)
  const currentEstimate = estimatePointFromRssi(d)

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-left">
          <div className="nav-logo-wrap">
            <img src="/Cartly.png" alt="Cartly" className="nav-logo" />
          </div>
          <div className="nav-divider" />
          <span className="nav-product">SmartTrolley</span>
        </div>
        <div className="nav-right">
          {d.system_state && (
            <div
              className="state-chip"
              style={{
                '--state-color': STATE_COLORS[d.system_state] || '#525252',
                background: `${STATE_COLORS[d.system_state] || '#525252'}18`,
                borderColor: `${STATE_COLORS[d.system_state] || '#525252'}50`,
              }}
            >
              <span className={`state-dot${['DEGRADED', 'NO_ANCHOR', 'IMU_FAIL', 'CLOUD_OFFLINE'].includes(d.system_state) ? ' state-dot-warn' : ''}`} />
              {d.system_state}
            </div>
          )}
          {d._direct && (
            <div className="direct-chip">
              <span className="direct-dot" />
              Direct
            </div>
          )}
          <div className={`live-chip ${connected ? 'live' : 'dead'}`}>
            <span className="live-dot" />
            {connected ? 'Live' : 'Offline'}
          </div>
        </div>
      </nav>

      <div className="page">
        <div className="hero-stats">
          <StatCard label="Speed" value={d.speed_mps?.toFixed(3)} unit="m/s" />
          <StatCard
            label="Signed Speed"
            value={d.signed_speed_mps?.toFixed(3)}
            unit="m/s"
            color={d.signed_speed_mps < 0 ? '#f97316' : undefined}
          />
          <StatCard label="Distance" value={d.distance_m?.toFixed(2)} unit="m" />
          <StatCard label="Step Cadence" value={d.step_cadence_spm?.toFixed(1)} unit="spm" />
          <StatCard
            label="Dwell Time"
            value={d.dwell_time_ms != null ? (d.dwell_time_ms / 1000).toFixed(1) : null}
            unit="s"
          />
          <StatCard
            label="Zone"
            value={d.zone}
            mono={false}
            color={ZONE_COLORS[d.zone]}
          />
        </div>

        <div className="mid-grid">
          <div className="panel status-panel">
            <div className="panel-label">Status</div>

            <div className="carry-display">
              <span className="carry-icon">{CARRY_ICONS[d.carry_style] || '.'}</span>
              <div>
                <div className="carry-name">{d.carry_style || '-'}</div>
                <div className="carry-sub">{d.load_proxy || '-'}</div>
              </div>
            </div>

            <div className="divider" />

            <div className="sys-grid">
              <div className="sys-item">
                <span className="sys-key">IMU</span>
                <span className="sys-val" style={{ color: d.imu_ok ? '#22c55e' : '#ef4444' }}>
                  {d.imu_ok == null ? '-' : d.imu_ok ? 'OK' : 'FAIL'}
                </span>
              </div>
              <div className="sys-item">
                <span className="sys-key">MQTT</span>
                <span className="sys-val" style={{ color: d.aws_ok ? '#22c55e' : '#ef4444' }}>
                  {d.aws_ok == null ? '-' : d.aws_ok ? 'OK' : 'OFF'}
                </span>
              </div>
              <div className="sys-item">
                <span className="sys-key">Anchors</span>
                <span className="sys-val">{d.anchors_seen ?? '-'} / 3</span>
              </div>
              <div className="sys-item">
                <span className="sys-key">Hotspot</span>
                <span className="sys-val hotspot">{d.live_hotspot || '-'}</span>
              </div>
            </div>

            <div className="divider" />

            <div className="conn-mode-row">
              <div className="conn-mode-via">
                <span className="conn-dot" style={{ background: d._direct ? '#f59e0b' : '#3b82f6' }} />
                <span className="conn-label">Via {d._direct ? 'Direct UDP' : 'MQTT'}</span>
              </div>
              {updateRateMs != null && (
                <span className="conn-rate">{updateRateMs} ms</span>
              )}
            </div>

            <div className="divider" />

            <div className="alerts-row">
              <AlertPill label="Pickup" active={d.pickup} icon="^" color="#f59e0b" />
              <AlertPill label="Drop" active={d.drop_down} icon="v" color="#ef4444" />
              <AlertPill label="Browsing" active={d.browsing} icon="o" color="#3b82f6" />
              <AlertPill label="Queue" active={d.queue_detect} icon="=" color="#a855f7" />
            </div>
          </div>

          <div className="panel rssi-panel">
            <div className="panel-label">Anchor Signal</div>
            <div
              className="zone-badge"
              style={{
                background: `${ZONE_COLORS[d.zone] || '#525252'}18`,
                color: ZONE_COLORS[d.zone] || '#525252',
                borderColor: `${ZONE_COLORS[d.zone] || '#525252'}40`,
              }}
            >
              {d.zone || 'UNKNOWN'}
            </div>
            <div className="rssi-list">
              <RssiBar label="Anchor A" value={d.anchor_a_rssi} color="#22c55e" />
              <RssiBar label="Anchor B" value={d.anchor_b_rssi} color="#3b82f6" />
              <RssiBar label="Anchor C" value={d.anchor_c_rssi} color="#f59e0b" />
            </div>
          </div>

          <div className="panel pos-panel">
            <div className="panel-label">Position Trail</div>
            <PositionPlot history={history} currentEstimate={currentEstimate} />
            <div className="pos-coords">
              <span>X {currentEstimate?.x?.toFixed(2) ?? '-'} m</span>
              <span className="pos-sep">.</span>
              <span>Y {currentEstimate?.y?.toFixed(2) ?? '-'} m</span>
            </div>
            <div className="pos-note">Estimated from live anchor RSSI</div>
          </div>
        </div>

        <div className="panel chart-panel">
          <div className="chart-header">
            <div>
              <div className="panel-label">Speed — Live</div>
              <div className="chart-sub">Last {chartData.length} readings</div>
            </div>
            <div className="chart-legend">
              <span><span className="leg-dot" style={{ background: '#2563eb' }} />Speed</span>
              <span><span className="leg-dot" style={{ background: '#7c3aed' }} />Signed</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="2 6" stroke="#1a1a1a" />
              <XAxis dataKey="id" hide />
              <YAxis stroke="#333" fontSize={10} tickFormatter={v => v.toFixed(1)} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={0} stroke="#333" strokeWidth={1} />
              <Line
                type="monotone"
                dataKey="speed_mps"
                stroke="#2563eb"
                dot={false}
                strokeWidth={1.5}
                name="Speed"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="signed_speed_mps"
                stroke="#7c3aed"
                dot={false}
                strokeWidth={1.5}
                name="Signed"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <HistorySection />

        <ConfigPanel />

        <footer className="footer">
          <div className="footer-logo-wrap">
            <img src="/Cartly.png" alt="Cartly" className="footer-logo-img" />
          </div>
          <span>Smart Trolley Intelligence Platform</span>
          <span className="footer-sep">.</span>
          <span>{d.device_id || 'trolley_01'}</span>
        </footer>
      </div>
    </div>
  )
}
