import { useState, useEffect, useRef } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import './App.css'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
  ROLLING: '→',
  SMOOTH_ROLL: '→',
  ROUGH_ROLL: '≈',
  TILTED_PUSH: '↗',
  LIFTED: '↑',
  PARKED: '■',
}

// ---------------------------------------------------------------------------
// Stat card — big bold number
// ---------------------------------------------------------------------------

function StatCard({ label, value, unit, mono = true, color, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={color ? { color } : {}}>
        <span className={mono ? 'mono' : ''}>{value ?? '—'}</span>
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Alert pill
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// RSSI bar
// ---------------------------------------------------------------------------

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
      <span className="rssi-val">{v <= -127 ? '—' : `${v} dBm`}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Position SVG trail
// ---------------------------------------------------------------------------

function PositionPlot({ history }) {
  const SIZE = 200
  const PAD = 20
  const PLOT = SIZE - PAD * 2

  const pts = history.filter(d => d.pos_x_m != null && d.pos_y_m != null)
  if (pts.length < 2) {
    return (
      <div className="pos-empty">
        <svg width={SIZE} height={SIZE}>
          <rect width={SIZE} height={SIZE} fill="#0d0d0d" rx="10" />
          <text x={SIZE / 2} y={SIZE / 2 - 8} textAnchor="middle" fill="#333" fontSize="11" fontFamily="Inter">
            Awaiting
          </text>
          <text x={SIZE / 2} y={SIZE / 2 + 8} textAnchor="middle" fill="#333" fontSize="11" fontFamily="Inter">
            position data
          </text>
        </svg>
      </div>
    )
  }

  const xs = pts.map(p => p.pos_x_m)
  const ys = pts.map(p => p.pos_y_m)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const rX = maxX - minX || 0.01
  const rY = maxY - minY || 0.01

  const sv = (px, py) => ({
    x: PAD + ((px - minX) / rX) * PLOT,
    y: SIZE - PAD - ((py - minY) / rY) * PLOT,
  })

  const pathD = pts.map((p, i) => {
    const { x, y } = sv(p.pos_x_m, p.pos_y_m)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  const cur = sv(xs[xs.length - 1], ys[ys.length - 1])
  const start = sv(xs[0], ys[0])

  return (
    <svg width={SIZE} height={SIZE} className="pos-svg">
      <rect width={SIZE} height={SIZE} fill="#0d0d0d" rx="10" />
      {/* Crosshair */}
      <line x1={PAD} y1={SIZE / 2} x2={SIZE - PAD} y2={SIZE / 2} stroke="#1a1a1a" strokeWidth="1" />
      <line x1={SIZE / 2} y1={PAD} x2={SIZE / 2} y2={SIZE - PAD} stroke="#1a1a1a" strokeWidth="1" />
      {/* Trail with gradient opacity */}
      <defs>
        <linearGradient id="trailGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.8" />
        </linearGradient>
      </defs>
      <path d={pathD} fill="none" stroke="url(#trailGrad)" strokeWidth="1.5" />
      {/* Start */}
      <circle cx={start.x} cy={start.y} r="2.5" fill="#333" />
      {/* Current */}
      <circle cx={cur.x} cy={cur.y} r="5" fill="#2563eb" />
      <circle cx={cur.x} cy={cur.y} r="9" fill="none" stroke="#2563eb" strokeWidth="1" opacity="0.35" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Custom chart tooltip
// ---------------------------------------------------------------------------

const ChartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tip">
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.stroke }}>
          {p.name}: <strong>{p.value?.toFixed(3)}</strong>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Config panel
// ---------------------------------------------------------------------------

function ConfigPanel() {
  const [form, setForm] = useState({
    pickupAccelThreshold: '',
    dropImpactThreshold: '',
    queueDwellThreshold: '',
    dwellAlertThreshold: '',
    rssiScanIntervalMs: '',
    actuatorEnabled: '',
    actuatorPulseMs: '',
  })
  const [status, setStatus] = useState(null)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    const intKeys = ['queueDwellThreshold', 'dwellAlertThreshold', 'rssiScanIntervalMs', 'actuatorPulseMs']
    const payload = {}
    for (const [k, v] of Object.entries(form)) {
      if (v === '') continue
      if (k === 'actuatorEnabled') payload[k] = v === 'true'
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

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [live, setLive] = useState(null)
  const [connected, setConnected] = useState(false)
  const [history, setHistory] = useState([])
  const wsRef = useRef(null)

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
        } catch { /* */ }
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const d = live || {}
  const chartData = history.slice(-120)

  return (
    <div className="app">
      {/* ── Navbar ── */}
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
          <div className={`live-chip ${connected ? 'live' : 'dead'}`}>
            <span className="live-dot" />
            {connected ? 'Live' : 'Offline'}
          </div>
        </div>
      </nav>

      <div className="page">
        {/* ── Hero stats row ── */}
        <div className="hero-stats">
          <StatCard
            label="Speed"
            value={d.speed_mps?.toFixed(3)}
            unit="m/s"
          />
          <StatCard
            label="Signed Speed"
            value={d.signed_speed_mps?.toFixed(3)}
            unit="m/s"
            color={d.signed_speed_mps < 0 ? '#f97316' : undefined}
          />
          <StatCard
            label="Distance"
            value={d.distance_m?.toFixed(2)}
            unit="m"
          />
          <StatCard
            label="Step Cadence"
            value={d.step_cadence_spm?.toFixed(1)}
            unit="spm"
          />
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

        {/* ── Middle grid ── */}
        <div className="mid-grid">
          {/* Status + alerts */}
          <div className="panel status-panel">
            <div className="panel-label">Status</div>

            <div className="carry-display">
              <span className="carry-icon">{CARRY_ICONS[d.carry_style] || '·'}</span>
              <div>
                <div className="carry-name">{d.carry_style || '—'}</div>
                <div className="carry-sub">{d.load_proxy || '—'}</div>
              </div>
            </div>

            <div className="divider" />

            <div className="sys-grid">
              <div className="sys-item">
                <span className="sys-key">IMU</span>
                <span className="sys-val" style={{ color: d.imu_ok ? '#22c55e' : '#ef4444' }}>
                  {d.imu_ok == null ? '—' : d.imu_ok ? 'OK' : 'FAIL'}
                </span>
              </div>
              <div className="sys-item">
                <span className="sys-key">MQTT</span>
                <span className="sys-val" style={{ color: d.aws_ok ? '#22c55e' : '#ef4444' }}>
                  {d.aws_ok == null ? '—' : d.aws_ok ? 'OK' : 'OFF'}
                </span>
              </div>
              <div className="sys-item">
                <span className="sys-key">Anchors</span>
                <span className="sys-val">{d.anchors_seen ?? '—'} / 3</span>
              </div>
              <div className="sys-item">
                <span className="sys-key">Hotspot</span>
                <span className="sys-val hotspot">{d.live_hotspot || '—'}</span>
              </div>
            </div>

            <div className="divider" />

            <div className="alerts-row">
              <AlertPill label="Pickup"   active={d.pickup}       icon="↑" color="#f59e0b" />
              <AlertPill label="Drop"     active={d.drop_down}    icon="↓" color="#ef4444" />
              <AlertPill label="Browsing" active={d.browsing}     icon="◎" color="#3b82f6" />
              <AlertPill label="Queue"    active={d.queue_detect} icon="≡" color="#a855f7" />
            </div>
          </div>

          {/* RSSI */}
          <div className="panel rssi-panel">
            <div className="panel-label">Anchor Signal</div>
            <div className="zone-badge" style={{ background: `${ZONE_COLORS[d.zone] || '#525252'}18`, color: ZONE_COLORS[d.zone] || '#525252', borderColor: `${ZONE_COLORS[d.zone] || '#525252'}40` }}>
              {d.zone || 'UNKNOWN'}
            </div>
            <div className="rssi-list">
              <RssiBar label="Anchor A" value={d.anchor_a_rssi} color="#ef4444" />
              <RssiBar label="Anchor B" value={d.anchor_b_rssi} color="#3b82f6" />
              <RssiBar label="Anchor C" value={d.anchor_c_rssi} color="#22c55e" />
            </div>
          </div>

          {/* Position */}
          <div className="panel pos-panel">
            <div className="panel-label">Position Trail</div>
            <PositionPlot history={history} />
            <div className="pos-coords">
              <span>X&thinsp;{d.pos_x_m?.toFixed(2) ?? '—'} m</span>
              <span className="pos-sep">·</span>
              <span>Y&thinsp;{d.pos_y_m?.toFixed(2) ?? '—'} m</span>
            </div>
          </div>
        </div>

        {/* ── Chart ── */}
        <div className="panel chart-panel">
          <div className="chart-header">
            <div>
              <div className="panel-label">Speed</div>
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

        {/* ── Config ── */}
        <ConfigPanel />

        {/* ── Footer ── */}
        <footer className="footer">
          <div className="footer-logo-wrap">
            <img src="/Cartly.png" alt="Cartly" className="footer-logo-img" />
          </div>
          <span>Smart Trolley Intelligence Platform</span>
          <span className="footer-sep">·</span>
          <span>{d.device_id || 'trolley_01'}</span>
        </footer>
      </div>
    </div>
  )
}
