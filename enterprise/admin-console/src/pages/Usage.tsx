import { useState } from 'react';
import Chart from 'react-apexcharts';
import type { ApexOptions } from 'apexcharts';
import { DollarSign, TrendingUp, TrendingDown, Users, Bot, AlertTriangle, Download, Calendar, Info, Cpu, Plus, Trash2 } from 'lucide-react';
import { Card, StatCard, Badge, Button, PageHeader, Table, Tabs, Select, Modal } from '../components/ui';
import { useUsageSummary, useUsageByDepartment, useUsageByAgent, useUsageBudgets, useUsageTrend, useUsageByModel, useModelConfig, useUpdateModelConfig, useUpdateFallbackModel, useSetPositionModel, useRemovePositionModel, usePositions } from '../hooks/useApi';

const costTrendOpts: ApexOptions = {
  chart: { type: 'area', toolbar: { show: false }, background: 'transparent' },
  colors: ['#22c55e', '#6366f1'],
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { opacityFrom: 0.3, opacityTo: 0.05 } },
  grid: { borderColor: '#2e3039', strokeDashArray: 4 },
  xaxis: { labels: { style: { colors: '#64748b', fontSize: '12px' } }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { labels: { style: { colors: '#64748b', fontSize: '12px' }, formatter: (v: number) => `$${v.toFixed(2)}` } },
  tooltip: { theme: 'dark' },
  legend: { position: 'top', horizontalAlign: 'right', labels: { colors: '#94a3b8' } },
  dataLabels: { enabled: false },
};

export default function Usage() {
  const { data: summary } = useUsageSummary();
  const { data: byDept = [] } = useUsageByDepartment();
  const { data: byAgent = [] } = useUsageByAgent();
  const { data: byModel = [] } = useUsageByModel();
  const { data: budgets = [] } = useUsageBudgets();
  const { data: trend = [] } = useUsageTrend();
  const { data: mc } = useModelConfig();
  const { data: positions = [] } = usePositions();
  const updateDefault = useUpdateModelConfig();
  const updateFallback = useUpdateFallbackModel();
  const setPositionModel = useSetPositionModel();
  const removePositionModel = useRemovePositionModel();
  const [activeTab, setActiveTab] = useState('department');
  const [timeRange, setTimeRange] = useState('7d');
  const [modelModal, setModelModal] = useState<'default' | 'fallback' | 'override' | null>(null);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [overridePosId, setOverridePosId] = useState('');
  const [overrideReason, setOverrideReason] = useState('');

  const s = summary || { totalInputTokens: 0, totalOutputTokens: 0, totalCost: 0, totalRequests: 0, tenantCount: 0, chatgptEquivalent: 5 };
  const m = mc || { default: { modelId: '', modelName: '—', inputRate: 0, outputRate: 0 }, fallback: { modelId: '', modelName: '', inputRate: 0, outputRate: 0 }, positionOverrides: {}, availableModels: [] };
  const modelOptions = m.availableModels.map((mo: any) => ({ label: `${mo.modelName}  ($${mo.inputRate} in / $${mo.outputRate} out per 1M tokens)`, value: mo.modelId }));
  const findModel = (id: string) => m.availableModels.find((mo: any) => mo.modelId === id);
  const handleModelSave = () => {
    const model = findModel(selectedModelId); if (!model) return;
    if (modelModal === 'default') updateDefault.mutate({ modelId: model.modelId, modelName: model.modelName, inputRate: model.inputRate, outputRate: model.outputRate });
    else if (modelModal === 'fallback') updateFallback.mutate({ modelId: model.modelId, modelName: model.modelName, inputRate: model.inputRate, outputRate: model.outputRate });
    else if (modelModal === 'override' && overridePosId) setPositionModel.mutate({ posId: overridePosId, modelId: model.modelId, modelName: model.modelName, inputRate: model.inputRate, outputRate: model.outputRate, reason: overrideReason || 'Custom model' });
    setModelModal(null); setSelectedModelId(''); setOverridePosId(''); setOverrideReason('');
  };

  const buildDeptBarOpts = (depts: typeof byDept): ApexOptions => ({
    chart: { type: 'bar', toolbar: { show: false }, background: 'transparent', stacked: true },
    colors: ['#6366f1', '#22c55e'],
    plotOptions: { bar: { borderRadius: 3, barHeight: '60%', horizontal: true } },
    grid: { borderColor: '#2e3039', strokeDashArray: 4, padding: { left: 10 } },
    xaxis: {
      categories: depts.map(d => d.department),   // ← department names on y-axis
      labels: { style: { colors: '#64748b', fontSize: '11px' }, formatter: (v: string) => `${(Number(v) / 1000).toFixed(0)}k` },
      axisBorder: { show: false }, axisTicks: { show: false },
    },
    yaxis: { labels: { style: { colors: '#94a3b8', fontSize: '12px' }, maxWidth: 130 } },
    tooltip: {
      theme: 'dark',
      custom: ({ seriesIndex, dataPointIndex }: { seriesIndex: number; dataPointIndex: number }) => {
        const d = depts[dataPointIndex];
        if (!d) return '';
        return `<div class="p-2 text-xs bg-dark-card border border-dark-border rounded-lg shadow-lg">
          <p class="font-semibold mb-1">${d.department}</p>
          <p>Input: ${(d.inputTokens/1000).toFixed(1)}k tokens</p>
          <p>Output: ${(d.outputTokens/1000).toFixed(1)}k tokens</p>
          <p class="text-green-400 mt-1">Cost: $${d.cost.toFixed(2)}</p>
        </div>`;
      },
    },
    legend: { position: 'top', horizontalAlign: 'right', labels: { colors: '#94a3b8' } },
    dataLabels: { enabled: false },
  });

  return (
    <div>
      <PageHeader
        title="Usage & Cost"
        description="Token consumption, cost tracking, budget management, and multi-dimension analysis"
        actions={
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-dark-border overflow-hidden">
              {[
                { label: 'Today', value: '1d' },
                { label: '7 Days', value: '7d' },
                { label: '30 Days', value: '30d' },
                { label: 'MTD', value: 'mtd' },
              ].map(r => (
                <button key={r.value} onClick={() => setTimeRange(r.value)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${timeRange === r.value ? 'bg-primary text-white' : 'bg-dark-card text-text-muted hover:text-text-primary'}`}>
                  {r.label}
                </button>
              ))}
            </div>
            <Button variant="default" size="sm" onClick={() => {
              const csv = ['Agent,Employee,Position,Requests,Input Tokens,Output Tokens,Cost', ...byAgent.map(a =>
                `"${a.agentName}","${a.employeeName}","${a.positionName}",${a.requests},${a.inputTokens},${a.outputTokens},${a.cost}`)].join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url; a.download = `usage-export-${new Date().toISOString().slice(0,10)}.csv`; a.click();
              URL.revokeObjectURL(url);
            }}><Download size={14} /> Export</Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5 mb-6">
        <StatCard title="Input Tokens" value={`${(s.totalInputTokens / 1000).toFixed(0)}k`} subtitle="Today" icon={<TrendingUp size={22} />} color="primary" />
        <StatCard title="Output Tokens" value={`${(s.totalOutputTokens / 1000).toFixed(0)}k`} subtitle="Today" icon={<TrendingDown size={22} />} color="info" />
        <StatCard title="Cost Today" value={`$${s.totalCost.toFixed(2)}`} subtitle={`${s.totalRequests} requests`} icon={<DollarSign size={22} />} color="success" />
        <StatCard title="Active Tenants" value={s.tenantCount} subtitle="With agents" icon={<Users size={22} />} color="cyan" />
        <StatCard title="vs ChatGPT" value={`$${s.chatgptEquivalent}/day`} subtitle={`Save $${(s.chatgptEquivalent - s.totalCost).toFixed(2)}/day`} icon={<DollarSign size={22} />} color="warning" />
      </div>

      {/* Cost trend chart */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-1">Cost Trend</h3>
        <p className="text-sm text-text-secondary mb-4">OpenClaw vs ChatGPT equivalent cost ({timeRange === '1d' ? 'Today' : timeRange === '7d' ? 'Last 7 days' : timeRange === '30d' ? 'Last 30 days' : 'Month to date'})</p>
        {(() => {
          const filtered = timeRange === '1d' ? trend.slice(-1) : timeRange === '7d' ? trend : trend;
          return (
            <Chart
              options={{...costTrendOpts, xaxis: { ...costTrendOpts.xaxis, categories: filtered.map(t => t.date.slice(5)) }}}
              series={[
                { name: 'OpenClaw Cost', data: filtered.map(t => t.openclawCost) },
                { name: 'ChatGPT Equivalent', data: filtered.map(t => t.chatgptEquivalent) },
              ]}
              type="area" height={280}
            />
          );
        })()}
      </Card>

      <Card>
        <Tabs
          tabs={[
            { id: 'department', label: 'By Department', count: byDept.length },
            { id: 'agent', label: 'By Agent', count: byAgent.length },
            { id: 'model', label: 'By Model' },
            { id: 'pricing', label: 'Models & Pricing' },
            { id: 'budget', label: 'Budget Management', count: budgets.filter(b => b.status !== 'ok').length || undefined },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />

        <div className="mt-4">
          {activeTab === 'department' && (
            <div className="space-y-6">
              {/* Full-width chart — department names now visible on y-axis */}
              <Chart
                options={buildDeptBarOpts(byDept)}
                series={[
                  { name: 'Input Tokens', data: byDept.map(d => d.inputTokens) },
                  { name: 'Output Tokens', data: byDept.map(d => d.outputTokens) },
                ]}
                type="bar" height={Math.max(byDept.length * 44 + 80, 300)}
              />
              {/* Table with inline cost share bar — visual without needing the chart */}
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-border text-left">
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider">Department</th>
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider text-right">Agents</th>
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider text-right">Requests</th>
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider text-right">Tokens</th>
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider text-right">Cost</th>
                    <th className="pb-2 text-xs font-medium text-text-muted uppercase tracking-wider w-36">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {byDept.map((d, i) => {
                    const pct = s.totalCost > 0 ? (d.cost / s.totalCost * 100) : 0;
                    const maxCost = byDept[0]?.cost || 1;
                    return (
                      <tr key={d.department} className="border-b border-dark-border/40 hover:bg-dark-hover transition-colors">
                        <td className="py-2.5 font-medium text-text-primary">{d.department}</td>
                        <td className="py-2.5 text-right text-text-secondary">{d.agents}</td>
                        <td className="py-2.5 text-right text-text-secondary">{d.requests}</td>
                        <td className="py-2.5 text-right text-text-secondary">{((d.inputTokens + d.outputTokens) / 1000).toFixed(0)}k</td>
                        <td className="py-2.5 text-right font-medium text-text-primary">${d.cost.toFixed(2)}</td>
                        <td className="py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 rounded-full bg-dark-bg overflow-hidden">
                              <div className="h-full rounded-full bg-primary/70" style={{ width: `${(d.cost / maxCost) * 100}%` }} />
                            </div>
                            <span className="text-xs text-text-muted w-8 text-right">{pct.toFixed(0)}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'agent' && (
            <Table
              columns={[
                { key: 'agent', label: 'Agent', render: (a: typeof byAgent[0]) => (
                  <div><p className="font-medium">{a.agentName}</p><p className="text-xs text-text-muted">{a.employeeName}</p></div>
                )},
                { key: 'position', label: 'Position', render: (a: typeof byAgent[0]) => <Badge>{a.positionName}</Badge> },
                { key: 'requests', label: 'Requests', render: (a: typeof byAgent[0]) => a.requests },
                { key: 'input', label: 'Input', render: (a: typeof byAgent[0]) => `${(a.inputTokens / 1000).toFixed(1)}k` },
                { key: 'output', label: 'Output', render: (a: typeof byAgent[0]) => `${(a.outputTokens / 1000).toFixed(1)}k` },
                { key: 'cost', label: 'Cost', render: (a: typeof byAgent[0]) => `$${a.cost.toFixed(2)}` },
                { key: 'share', label: 'Share', render: (a: typeof byAgent[0]) => {
                  const pct = s.totalCost > 0 ? (a.cost / s.totalCost * 100).toFixed(1) : '0';
                  return <Badge color="info">{pct}%</Badge>;
                }},
              ]}
              data={byAgent}
            />
          )}

          {activeTab === 'model' && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-4">Token Distribution by Model</h3>
                <Chart
                  options={{
                    chart: { type: 'donut', background: 'transparent' },
                    colors: ['#22c55e', '#6366f1', '#f59e0b', '#06b6d4', '#ef4444'],
                    labels: byModel.map(m => m.model.split('/').pop()?.split(':')[0] || m.model),
                    legend: { position: 'bottom', labels: { colors: '#94a3b8' } },
                    plotOptions: { pie: { donut: { size: '65%', labels: { show: true, total: { show: true, label: 'Total Tokens', color: '#94a3b8', formatter: () => `${(byModel.reduce((s, m) => s + m.inputTokens + m.outputTokens, 0) / 1000).toFixed(0)}k` } } } } },
                    dataLabels: { enabled: false },
                    tooltip: { theme: 'dark' },
                  }}
                  series={byModel.map(m => m.inputTokens + m.outputTokens)}
                  type="donut" height={300}
                />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-4">Cost by Model</h3>
                <div className="space-y-4">
                  {(() => {
                    const colors = ['#22c55e', '#6366f1', '#f59e0b', '#06b6d4', '#ef4444'];
                    const modelRates: Record<string, { input: number; output: number }> = {
                      'nova-2-lite': { input: 0.30, output: 2.50 },
                      'nova-pro': { input: 0.80, output: 3.20 },
                      'claude-sonnet': { input: 3.00, output: 15.00 },
                      'claude-haiku': { input: 0.25, output: 1.25 },
                    };
                    const totalModelCost = byModel.reduce((s, m) => s + m.cost, 0);
                    return byModel.map((m, i) => {
                      const shortName = m.model.split('/').pop()?.split(':')[0] || m.model;
                      const rateKey = Object.keys(modelRates).find(k => shortName.toLowerCase().includes(k)) || '';
                      const rates = modelRates[rateKey] || { input: 0.30, output: 2.50 };
                      const pct = totalModelCost > 0 ? Math.round(m.cost / totalModelCost * 100) : 0;
                      return (
                        <div key={m.model} className="rounded-lg bg-dark-bg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors[i % colors.length] }} />
                              <span className="text-sm font-medium">{shortName}</span>
                            </div>
                            <span className="text-sm font-semibold" style={{ color: colors[i % colors.length] }}>${m.cost.toFixed(4)}</span>
                          </div>
                          <div className="grid grid-cols-3 gap-3 text-xs text-text-muted">
                            <div><span className="block text-text-secondary">{m.requests}</span>requests</div>
                            <div><span className="block text-text-secondary">${rates.input}/${rates.output}</span>per 1M tokens</div>
                            <div><span className="block text-text-secondary">{pct}%</span>of total cost</div>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
                {byModel.length === 0 && (
                  <p className="text-sm text-text-muted text-center py-8">No model usage data available</p>
                )}
                {byModel.length > 0 && (
                  <div className="mt-4 rounded-lg bg-success/5 border border-success/20 p-3 text-xs text-success">
                    💡 Data from DynamoDB usage records. Real token counts from AgentCore invocations.
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'budget' && (
            <div>
              <div className="rounded-xl bg-warning/10 border border-warning/30 px-4 py-3 mb-4 flex items-start gap-2">
                <AlertTriangle size={15} className="text-warning mt-0.5 shrink-0" />
                <p className="text-xs text-warning">
                  <strong>Tracking only — budgets are not enforced.</strong> Agents will not be paused or restricted when a budget is exceeded. These figures are for monitoring and planning only.
                </p>
              </div>
              <p className="text-sm text-text-secondary mb-4">Monthly budget tracking by department. Projected cost based on current daily usage × 30 days.</p>
              <Table
                columns={[
                  { key: 'dept', label: 'Department', render: (b: typeof budgets[0]) => <span className="font-medium">{b.department}</span> },
                  { key: 'budget', label: 'Monthly Budget', render: (b: typeof budgets[0]) => `$${b.budget.toFixed(0)}` },
                  { key: 'used', label: 'Used Today', render: (b: typeof budgets[0]) => `$${b.used.toFixed(2)}` },
                  { key: 'projected', label: 'Projected Monthly', render: (b: typeof budgets[0]) => `$${b.projected.toFixed(2)}` },
                  { key: 'utilization', label: 'Utilization', render: (b: typeof budgets[0]) => {
                    const pct = Math.round(b.projected / b.budget * 100);
                    return (
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-24 rounded-full bg-dark-bg">
                          <div className={`h-full rounded-full ${pct > 100 ? 'bg-danger' : pct > 80 ? 'bg-warning' : 'bg-success'}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                        </div>
                        <span className="text-xs text-text-muted">{pct}%</span>
                      </div>
                    );
                  }},
                  { key: 'status', label: 'Status', render: (b: typeof budgets[0]) => (
                    <Badge color={b.status === 'ok' ? 'success' : b.status === 'warning' ? 'warning' : 'danger'} dot>
                      {b.status === 'ok' ? 'On track' : b.status === 'warning' ? 'Near limit' : 'Over budget'}
                    </Badge>
                  )},
                ]}
                data={budgets}
              />
              <div className="mt-4 rounded-lg bg-info/5 border border-info/20 p-3 text-xs text-info">
                Over-budget actions: Alert → Downgrade model (Sonnet→Nova) → Rate limit → Pause agent
              </div>
            </div>
          )}
          {/* ── Models & Pricing ── */}
          {activeTab === 'pricing' && (
            <div className="space-y-6">
              {/* Current default + actual spend */}
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {[
                  { label: 'Default Model', model: m.default, action: () => { setModelModal('default'); setSelectedModelId(m.default.modelId); }, badge: 'primary' as const },
                  { label: 'Fallback Model', model: m.fallback, action: () => { setModelModal('fallback'); setSelectedModelId(m.fallback.modelId); }, badge: 'warning' as const },
                ].map(r => (
                  <Card key={r.label}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2"><Cpu size={15} className="text-primary" />{r.label}</h3>
                      <Button variant="default" size="sm" onClick={r.action}>Change</Button>
                    </div>
                    <div className="rounded-xl bg-surface-dim p-3 space-y-1.5">
                      <p className="text-base font-semibold text-text-primary">{r.model.modelName || '—'}</p>
                      <p className="text-[10px] font-mono text-text-muted">{r.model.modelId}</p>
                      <div className="flex gap-2">
                        <Badge color={r.badge}>In: ${r.model.inputRate}/1M tokens</Badge>
                        <Badge color={r.badge}>Out: ${r.model.outputRate}/1M tokens</Badge>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Per-position overrides */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary">Per-Position Model Overrides</h3>
                    <p className="text-xs text-text-muted">Assign a different model (and cost tier) to specific positions</p>
                  </div>
                  <Button variant="primary" size="sm" onClick={() => setModelModal('override')}><Plus size={13} /> Add Override</Button>
                </div>
                {Object.keys(m.positionOverrides).length === 0 ? (
                  <p className="text-sm text-text-muted text-center py-6">All positions use the default model</p>
                ) : (
                  <div className="divide-y divide-dark-border/30">
                    {Object.entries(m.positionOverrides).map(([posId, ov]: [string, any]) => (
                      <div key={posId} className="flex items-center justify-between py-3">
                        <div>
                          <p className="text-sm font-medium text-text-primary">{positions.find(p => p.id === posId)?.name || posId}</p>
                          <p className="text-xs text-text-muted">{ov.modelName} · ${ov.inputRate}/${ov.outputRate} per 1M · {ov.reason}</p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => removePositionModel.mutate(posId)}><Trash2 size={13} /></Button>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* All available models as a pricing card */}
              <Card>
                <h3 className="text-sm font-semibold text-text-primary mb-1">Available Models — Unit Pricing</h3>
                <p className="text-xs text-text-muted mb-4">Prices per 1 million tokens. Switch default model from the cards above.</p>
                <div className="space-y-2">
                  {m.availableModels.map((mo: any) => {
                    const isDefault = mo.modelId === m.default.modelId;
                    const isFallback = mo.modelId === m.fallback.modelId;
                    // Find actual spend for this model from byModel data
                    const modelSpend = byModel.find(bm => bm.model?.includes(mo.modelId?.split('/').pop()?.split(':')[0] || '??'));
                    return (
                      <div key={mo.modelId} className={`flex items-center gap-4 rounded-xl px-4 py-3 ${isDefault ? 'bg-primary/5 border border-primary/20' : isFallback ? 'bg-warning/5 border border-warning/20' : 'bg-surface-dim'}`}>
                        <div className={`w-2 h-2 rounded-full shrink-0 ${mo.enabled ? 'bg-success' : 'bg-text-muted'}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary">{mo.modelName}</p>
                          <p className="text-[10px] font-mono text-text-muted">{mo.modelId}</p>
                        </div>
                        <div className="text-right shrink-0 space-y-0.5">
                          <p className="text-xs text-text-muted">${mo.inputRate} in · ${mo.outputRate} out <span className="text-text-muted/60">per 1M</span></p>
                          {modelSpend && <p className="text-xs text-success font-medium">${modelSpend.cost?.toFixed(4)} spent · {(modelSpend.inputTokens+modelSpend.outputTokens)/1000}k tokens</p>}
                        </div>
                        {isDefault && <Badge color="primary">Default</Badge>}
                        {isFallback && <Badge color="warning">Fallback</Badge>}
                        {!isDefault && !isFallback && mo.enabled && (
                          <Button variant="ghost" size="sm" onClick={() => updateDefault.mutate({ modelId: mo.modelId, modelName: mo.modelName, inputRate: mo.inputRate, outputRate: mo.outputRate })}>Set Default</Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </Card>

              <div className="rounded-xl bg-info/5 border border-info/20 px-4 py-3 text-xs text-info">
                Model changes take effect on the next agent cold start (~15 min idle timeout). Actual Bedrock billing may differ slightly from estimated costs above.
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Model change modal */}
      {modelModal && (
        <Modal open={true} onClose={() => setModelModal(null)}
          title={modelModal === 'default' ? 'Change Default Model' : modelModal === 'fallback' ? 'Change Fallback Model' : 'Add Position Override'}
          footer={<div className="flex justify-end gap-3"><Button variant="default" onClick={() => setModelModal(null)}>Cancel</Button><Button variant="primary" onClick={handleModelSave}>Apply</Button></div>}>
          <div className="space-y-4">
            {modelModal === 'override' && (
              <Select label="Position" value={overridePosId} onChange={setOverridePosId}
                options={positions.filter(p => !m.positionOverrides[p.id]).map(p => ({ label: p.name, value: p.id }))}
                placeholder="Select position..." />
            )}
            <Select label="Model" value={selectedModelId} onChange={setSelectedModelId} options={modelOptions} placeholder="Select model..." />
            {modelModal === 'override' && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-text-secondary">Reason</label>
                <input value={overrideReason} onChange={e => setOverrideReason(e.target.value)}
                  className="w-full rounded-xl border border-dark-border/60 bg-surface-dim px-4 py-2.5 text-sm text-text-primary focus:border-primary/60 focus:outline-none"
                  placeholder="e.g. Higher capability needed for executive decisions" />
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
