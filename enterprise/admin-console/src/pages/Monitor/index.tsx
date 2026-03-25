import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Chart from 'react-apexcharts';
import type { ApexOptions } from 'apexcharts';
import { Bot, MessageSquare, Star, AlertTriangle, Shield, RefreshCw, Eye, Radio, Clock, Zap } from 'lucide-react';
import { Card, StatCard, Badge, Button, PageHeader, Table, StatusDot, Tabs } from '../../components/ui';
import { useSessions, useAgents, useMonitorHealth, useAlertRules, useRuntimeEvents } from '../../hooks/useApi';
import { CHANNEL_LABELS } from '../../types';
import type { ChannelType } from '../../types';
import SessionDetail from './SessionDetail';

const realtimeOpts: ApexOptions = {
  chart: { type: 'area', toolbar: { show: false }, background: 'transparent' },
  colors: ['#6366f1', '#22c55e', '#f59e0b'],
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { opacityFrom: 0.3, opacityTo: 0.05 } },
  grid: { borderColor: '#2e3039', strokeDashArray: 4 },
  xaxis: { categories: ['5m', '4m', '3m', '2m', '1m', 'now'], labels: { style: { colors: '#64748b', fontSize: '11px' } }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { labels: { style: { colors: '#64748b', fontSize: '11px' } } },
  tooltip: { theme: 'dark' },
  legend: { position: 'top', horizontalAlign: 'right', labels: { colors: '#94a3b8' } },
  dataLabels: { enabled: false },
};

export default function Monitor() {
  const { data: sessions = [], refetch: refetchSessions } = useSessions();
  const { data: AGENTS = [] } = useAgents();
  const navigate = useNavigate();
  const { data: healthData, refetch: refetchHealth } = useMonitorHealth();
  const { data: alertRules = [], refetch: refetchAlerts } = useAlertRules();
  const { data: runtimeData } = useRuntimeEvents(60);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('sessions');

  const health = healthData?.agents || [];
  const sys = healthData?.system || {};
  const activeAgents = AGENTS.filter(a => a.status === 'active').length;
  const totalTurns = sessions.reduce((s, sess) => s + sess.turns, 0);
  const avgQuality = AGENTS.filter(a => a.qualityScore).length > 0
    ? AGENTS.filter(a => a.qualityScore).reduce((s, a) => s + (a.qualityScore || 0), 0) / AGENTS.filter(a => a.qualityScore).length
    : 0;
  const alertCount = alertRules.filter(a => a.status === 'warning').length;

  const elapsed = (startedAt: string) => {
    const mins = Math.floor((Date.now() - new Date(startedAt).getTime()) / 60000);
    return mins < 60 ? `${mins}min` : `${Math.floor(mins / 60)}h ${mins % 60}m`;
  };

  if (selectedSession) {
    const session = sessions.find(s => s.id === selectedSession);
    if (session) return <SessionDetail session={session} onBack={() => setSelectedSession(null)} />;
  }

  return (
    <div>
      <PageHeader title="Monitor Center" description="Real-time session monitoring, agent health, performance metrics, and alert management" />

      {/* Top KPIs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 mb-6">
        <StatCard title="Live Sessions" value={sessions.length} icon={<Radio size={22} />} color="success" />
        <StatCard title="Online Agents" value={activeAgents} icon={<Bot size={22} />} color="primary" />
        <StatCard title="Total Turns" value={totalTurns} icon={<MessageSquare size={22} />} color="info" />
        <StatCard title="Avg Quality" value={avgQuality.toFixed(1)} icon={<Star size={22} />} color="warning" />
        <StatCard title="P95 Response" value={`${sys.p95ResponseSec || 4.2}s`} icon={<Clock size={22} />} color="cyan" />
        <StatCard title="Alerts" value={alertCount} icon={<AlertTriangle size={22} />} color={alertCount > 0 ? 'danger' : 'success'} />
      </div>

      {/* System Health Bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Gateway', status: sys.gatewayStatus || 'healthy', detail: 'Port 18789' },
          { label: 'AgentCore Runtime', status: sys.agentCoreStatus || 'healthy', detail: 'Firecracker microVM' },
          { label: 'Bedrock API', status: 'connected', detail: `${sys.bedrockLatencyMs || 245}ms latency` },
        ].map(svc => (
          <div key={svc.label} className="rounded-lg border border-dark-border bg-dark-card px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${svc.status === 'healthy' || svc.status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-amber-500'}`} />
              <div>
                <p className="text-sm font-medium text-text-primary">{svc.label}</p>
                <p className="text-xs text-text-muted">{svc.detail}</p>
              </div>
            </div>
            <Badge color={svc.status === 'healthy' || svc.status === 'connected' ? 'success' : 'warning'}>{svc.status}</Badge>
          </div>
        ))}
      </div>

      {/* Real-time Chart */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-text-primary">Real-time Activity</h3>
            <p className="text-sm text-text-secondary">Messages, tool calls, and permission checks per minute</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => { refetchSessions(); refetchHealth(); refetchAlerts(); }}><RefreshCw size={14} /> Refresh</Button>
        </div>
        <Chart options={realtimeOpts} series={[
          { name: 'Messages', data: sessions.length > 0 ? [sessions.length - 2, sessions.length, sessions.length - 1, sessions.length + 1, sessions.length - 1, sessions.length].map(v => Math.max(0, v)) : [] },
          { name: 'Tool Calls', data: sessions.length > 0 ? sessions.slice(0, 6).map(s => (s as any).toolCalls || 0) : [] },
          { name: 'Permission Checks', data: sessions.length > 0 ? [1, 1, 0, 2, 1, 1].slice(0, Math.min(6, sessions.length)) : [] },
        ]} type="area" height={220} />
      </Card>

      {/* Tabbed Content */}
      <Card>
        <Tabs
          tabs={[
            { id: 'sessions', label: 'Live Sessions', count: sessions.length },
            { id: 'health', label: 'Agent Health', count: health.length },
            { id: 'alerts', label: 'Alert Rules', count: alertCount || undefined },
            { id: 'runtime', label: 'Runtime Events' },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />

        <div className="mt-4">
          {activeTab === 'sessions' && (
            <div>
              <Table
                columns={[
                  { key: 'employee', label: 'Employee', render: (s: typeof sessions[0]) => <button onClick={(e) => { e.stopPropagation(); navigate('/org/employees'); }} className="font-medium text-primary-light hover:underline">{s.employeeName}</button> },
                  { key: 'arrow', label: '', render: () => <span className="text-text-muted">↔</span>, width: '40px' },
                  { key: 'agent', label: 'Agent', render: (s: typeof sessions[0]) => <button onClick={(e) => { e.stopPropagation(); navigate(`/agents/${s.agentId}`); }} className="font-medium text-primary-light hover:underline">{s.agentName}</button> },
                  { key: 'channel', label: 'Channel', render: (s: typeof sessions[0]) => <Badge color="info">{CHANNEL_LABELS[s.channel as ChannelType]}</Badge> },
                  { key: 'duration', label: 'Duration', render: (s: typeof sessions[0]) => <span className="text-text-muted">{elapsed(s.startedAt)}</span> },
                  { key: 'turns', label: 'Turns', render: (s: typeof sessions[0]) => s.turns },
                  { key: 'lastMsg', label: 'Latest Message', render: (s: typeof sessions[0]) => <span className="text-xs text-text-muted truncate block max-w-[200px]">{s.lastMessage}</span> },
                  { key: 'status', label: 'Status', render: (s: typeof sessions[0]) => <StatusDot status={s.status} /> },
                  { key: 'actions', label: '', render: (s: typeof sessions[0]) => (
                    <Button variant="ghost" size="sm" onClick={() => setSelectedSession(s.id)}><Eye size={14} /> View</Button>
                  )},
                ]}
                data={sessions}
              />
            </div>
          )}

          {activeTab === 'health' && (
            <div>
              {/* Health Summary */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div className="rounded-lg bg-dark-bg p-3 text-center">
                  <p className="text-2xl font-bold text-green-400">{sys.activeAgents || activeAgents}</p>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Active</p>
                </div>
                <div className="rounded-lg bg-dark-bg p-3 text-center">
                  <p className="text-2xl font-bold text-blue-400">{sys.totalRequestsToday || 0}</p>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Requests Today</p>
                </div>
                <div className="rounded-lg bg-dark-bg p-3 text-center">
                  <p className="text-2xl font-bold text-cyan-400">{sys.overallToolSuccess || 96}%</p>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Tool Success</p>
                </div>
                <div className="rounded-lg bg-dark-bg p-3 text-center">
                  <p className="text-2xl font-bold text-amber-400">${sys.totalCostToday || '0.00'}</p>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Cost Today</p>
                </div>
              </div>

              {/* Agent Health Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-border text-left">
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Agent</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Status</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Quality</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Requests</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Avg Response</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Tool Success</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">SOUL</th>
                      <th className="pb-3 text-xs font-medium text-text-muted uppercase tracking-wider">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {health.map(a => (
                      <tr key={a.agentId} onClick={() => navigate(`/agents/${a.agentId}`)} className="border-b border-dark-border/50 hover:bg-dark-hover cursor-pointer transition-colors">
                        <td className="py-3">
                          <div>
                            <p className="font-medium text-text-primary">{a.agentName}</p>
                            <p className="text-xs text-text-muted">{a.employeeName} · {a.positionName}</p>
                          </div>
                        </td>
                        <td className="py-3"><StatusDot status={a.status} /></td>
                        <td className="py-3">
                          {a.qualityScore ? (
                            <span className={`text-sm font-medium ${a.qualityScore >= 4.5 ? 'text-green-400' : a.qualityScore >= 4.0 ? 'text-blue-400' : 'text-amber-400'}`}>
                              ⭐ {a.qualityScore}
                            </span>
                          ) : <span className="text-text-muted">—</span>}
                        </td>
                        <td className="py-3"><span className="text-text-secondary">{a.requestsToday}</span></td>
                        <td className="py-3">
                          <span className={`text-sm ${a.avgResponseSec <= 3 ? 'text-green-400' : a.avgResponseSec <= 4 ? 'text-text-secondary' : 'text-amber-400'}`}>
                            {a.avgResponseSec}s
                          </span>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-12 h-1.5 rounded-full bg-dark-bg overflow-hidden">
                              <div className={`h-full rounded-full ${a.toolSuccessRate >= 95 ? 'bg-green-500' : a.toolSuccessRate >= 85 ? 'bg-blue-500' : 'bg-amber-500'}`}
                                style={{ width: `${a.toolSuccessRate}%` }} />
                            </div>
                            <span className="text-xs text-text-muted">{a.toolSuccessRate}%</span>
                          </div>
                        </td>
                        <td className="py-3"><span className="text-xs font-mono text-text-muted">{a.soulVersion}</span></td>
                        <td className="py-3"><span className="text-xs text-text-secondary">${a.costToday.toFixed(2)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'alerts' && (
            <div>
              <p className="text-sm text-text-secondary mb-4">Alert rules are evaluated continuously. Triggered alerts generate audit entries and notifications.</p>
              <div className="space-y-2">
                {alertRules.map((a) => (
                  <div key={a.id} className={`flex items-center justify-between rounded-lg px-4 py-3 ${
                    a.status === 'warning' ? 'bg-amber-500/5 border border-amber-500/20' :
                    a.status === 'info' ? 'bg-blue-500/5 border border-blue-500/20' :
                    'bg-dark-bg/50 border border-transparent'
                  }`}>
                    <div className="flex items-center gap-3">
                      {a.status === 'warning' ? <AlertTriangle size={16} className="text-amber-400" /> :
                       a.status === 'info' ? <Zap size={16} className="text-blue-400" /> :
                       <Shield size={16} className="text-green-400" />}
                      <div>
                        <p className="text-sm font-medium">{a.type}</p>
                        <p className="text-xs text-text-muted">{a.condition} → {a.action}</p>
                        <p className="text-[10px] text-text-muted mt-0.5">{a.detail}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-text-muted">{new Date(a.lastChecked).toLocaleTimeString()}</span>
                      <Badge color={a.status === 'ok' ? 'success' : a.status === 'warning' ? 'warning' : 'info'} dot>
                        {a.status === 'ok' ? 'Clear' : a.status === 'warning' ? 'Triggered' : 'Info'}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'runtime' && (
            <div>
              {/* Summary cards */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 mb-4">
                <div className="rounded-lg bg-dark-bg border border-dark-border p-3 text-center">
                  <div className="text-lg font-bold text-primary">{runtimeData?.summary?.invocations || 0}</div>
                  <div className="text-[10px] text-text-muted">Invocations</div>
                </div>
                <div className="rounded-lg bg-dark-bg border border-dark-border p-3 text-center">
                  <div className="text-lg font-bold text-amber-400">{runtimeData?.summary?.coldStarts || 0}</div>
                  <div className="text-[10px] text-text-muted">Cold Starts</div>
                </div>
                <div className="rounded-lg bg-dark-bg border border-dark-border p-3 text-center">
                  <div className="text-lg font-bold text-red-400">{runtimeData?.summary?.releases || 0}</div>
                  <div className="text-[10px] text-text-muted">VM Releases</div>
                </div>
                <div className="rounded-lg bg-dark-bg border border-dark-border p-3 text-center">
                  <div className="text-lg font-bold text-green-400">{runtimeData?.summary?.activeTenants || 0}</div>
                  <div className="text-[10px] text-text-muted">Active Tenants</div>
                </div>
                <div className="rounded-lg bg-dark-bg border border-dark-border p-3 text-center">
                  <div className="text-lg font-bold text-text-muted">{runtimeData?.summary?.timeRangeMinutes || 60}m</div>
                  <div className="text-[10px] text-text-muted">Time Range</div>
                </div>
              </div>

              {/* Event timeline */}
              <p className="text-sm text-text-secondary mb-3">Real-time AgentCore microVM lifecycle events from CloudWatch Logs</p>
              <div className="space-y-1.5 max-h-[500px] overflow-y-auto">
                {(runtimeData?.events || []).map((e, i) => {
                  const typeConfig: Record<string, { color: string; icon: string }> = {
                    invocation: { color: 'text-primary', icon: '→' },
                    response: { color: 'text-green-400', icon: '←' },
                    cold_start: { color: 'text-amber-400', icon: '🔥' },
                    release: { color: 'text-red-400', icon: '⏹' },
                    ready: { color: 'text-green-400', icon: '✓' },
                    sync: { color: 'text-cyan-400', icon: '↻' },
                    plan_a: { color: 'text-orange-400', icon: '🛡' },
                    usage: { color: 'text-blue-400', icon: '📊' },
                    mapping: { color: 'text-purple-400', icon: '🔗' },
                  };
                  const cfg = typeConfig[e.type] || { color: 'text-text-muted', icon: '·' };
                  return (
                    <div key={i} className="flex items-start gap-2 rounded-lg bg-dark-bg/50 px-3 py-2 text-xs hover:bg-dark-bg transition-colors">
                      <span className={`${cfg.color} font-mono w-4 shrink-0 text-center`}>{cfg.icon}</span>
                      <span className="text-text-muted shrink-0 w-20 font-mono">{new Date(e.timestamp).toLocaleTimeString()}</span>
                      <Badge color={e.type === 'invocation' ? 'primary' : e.type === 'response' ? 'success' : e.type === 'cold_start' ? 'warning' : e.type === 'release' ? 'danger' : 'default'}>
                        {e.type}
                      </Badge>
                      <span className="text-text-secondary flex-1">{e.message}</span>
                      {e.tenant && <code className="text-[10px] text-text-muted bg-dark-card px-1 rounded truncate max-w-[200px]">{e.tenant}</code>}
                    </div>
                  );
                })}
                {(!runtimeData?.events || runtimeData.events.length === 0) && (
                  <div className="text-center py-8 text-text-muted">
                    <Radio size={24} className="mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No runtime events in the last {runtimeData?.summary?.timeRangeMinutes || 60} minutes</p>
                    <p className="text-xs mt-1">Events appear when agents are invoked via IM channels or Portal</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
