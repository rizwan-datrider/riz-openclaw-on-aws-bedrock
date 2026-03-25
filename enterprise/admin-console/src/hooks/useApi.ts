/**
 * React Query hooks for all API endpoints.
 * Each hook wraps a useQuery/useMutation call to the FastAPI backend.
 * When the backend is running, data comes from DynamoDB.
 * When it's not, the API calls fail and we fall back gracefully.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Department, Position, Employee, Agent, Binding, LiveSession, AuditEntry, SoulLayer } from '../types';

// === Organization ===

export function useDepartments() {
  return useQuery<Department[]>({
    queryKey: ['departments'],
    queryFn: () => api.get('/org/departments'),
  });
}

export function usePositions() {
  return useQuery<Position[]>({
    queryKey: ['positions'],
    queryFn: () => api.get('/org/positions'),
  });
}

export function useCreatePosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Position>) => api.post<Position>('/org/positions', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['positions'] }),
  });
}

export function useEmployees() {
  return useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: () => api.get('/org/employees'),
  });
}

export function useEmployeeActivities() {
  return useQuery<Record<string, any>[]>({
    queryKey: ['employee-activities'],
    queryFn: () => api.get('/org/employees/activity'),
  });
}

export function useUsageTrend() {
  return useQuery<{ date: string; openclawCost: number; chatgptEquivalent: number; totalRequests: number }[]>({
    queryKey: ['usage-trend'],
    queryFn: () => api.get('/usage/trend'),
  });
}

export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Employee>) => api.post<Employee>('/org/employees', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employees'] }),
  });
}

// === Agents ===

export function useAgents() {
  return useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => api.get('/agents'),
  });
}

export function useAgent(agentId: string) {
  return useQuery<Agent>({
    queryKey: ['agent', agentId],
    queryFn: () => api.get(`/agents/${agentId}`),
    enabled: !!agentId,
  });
}

export function useAgentSoul(agentId: string) {
  return useQuery<SoulLayer[]>({
    queryKey: ['agent-soul', agentId],
    queryFn: () => api.get(`/agents/${agentId}/soul`),
    enabled: !!agentId,
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Agent>) => api.post<Agent>('/agents', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

// === Bindings ===

export function useBindings() {
  return useQuery<Binding[]>({
    queryKey: ['bindings'],
    queryFn: () => api.get('/bindings'),
  });
}

export function useCreateBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Binding>) => api.post<Binding>('/bindings', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bindings'] }),
  });
}

export function useBulkProvision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { positionId: string; defaultChannel: string }) =>
      api.post<{ position: string; provisioned: number; details: { employee: string; agent: string; channel: string }[]; alreadyBound: number }>('/bindings/provision-by-position', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bindings'] });
      qc.invalidateQueries({ queryKey: ['agents'] });
      qc.invalidateQueries({ queryKey: ['employees'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// === Monitor ===

export function useSessions() {
  return useQuery<LiveSession[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/monitor/sessions'),
    refetchInterval: 10_000,
  });
}

export function useSessionDetail(sessionId: string) {
  return useQuery<{
    session: LiveSession;
    conversation: { role: string; content: string; ts: string; toolCall?: { tool: string; status: string; duration: string } }[];
    quality: Record<string, number>;
    planE: { turn: number; result: string; detail: string }[];
  }>({
    queryKey: ['session-detail', sessionId],
    queryFn: () => api.get(`/monitor/sessions/${sessionId}`),
    enabled: !!sessionId,
  });
}

export interface AlertRule {
  id: string; type: string; condition: string; action: string;
  status: 'ok' | 'warning' | 'info'; lastChecked: string; detail: string;
}

export function useAlertRules() {
  return useQuery<AlertRule[]>({
    queryKey: ['alert-rules'],
    queryFn: () => api.get('/monitor/alerts'),
    refetchInterval: 30_000,
  });
}

export interface RuntimeEvent {
  type: string; message: string; timestamp: string; tenant?: string; raw?: string;
}

export function useRuntimeEvents(minutes: number = 30) {
  return useQuery<{ events: RuntimeEvent[]; summary: Record<string, number> }>({
    queryKey: ['runtime-events', minutes],
    queryFn: () => api.get(`/monitor/runtime-events?minutes=${minutes}`),
    refetchInterval: 15_000,
  });
}

// === Audit ===

export function useAuditEntries(params?: { limit?: number; eventType?: string }) {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.eventType && params.eventType !== 'all') qs.set('eventType', params.eventType);
  return useQuery<AuditEntry[]>({
    queryKey: ['audit', params],
    queryFn: () => api.get(`/audit/entries?${qs}`),
  });
}

export interface AuditInsight {
  id: string; severity: 'high' | 'medium' | 'low'; category: string;
  title: string; description: string; recommendation: string;
  affectedUsers: string[]; detectedAt: string; source: string;
}

export function useAuditInsights() {
  return useQuery<{ insights: AuditInsight[]; summary: { totalInsights: number; high: number; medium: number; low: number; lastScanAt: string; scanSources: string[] } }>({
    queryKey: ['audit-insights'],
    queryFn: () => api.get('/audit/insights'),
  });
}

export interface AgentHealthItem {
  agentId: string; agentName: string; employeeName: string; positionName: string;
  status: string; qualityScore: number | null; channels: string[]; skillCount: number;
  requestsToday: number; costToday: number; avgResponseSec: number; toolSuccessRate: number;
  soulVersion: string; lastActive: string; uptime: string;
}

export function useMonitorHealth() {
  return useQuery<{ agents: AgentHealthItem[]; system: Record<string, any> }>({
    queryKey: ['monitor-health'],
    queryFn: () => api.get('/monitor/health'),
    refetchInterval: 30_000,
  });
}

// === Dashboard ===

export interface DashboardData {
  departments: number; positions: number; employees: number;
  agents: number; activeAgents: number; bindings: number;
  sessions: number; totalTurns: number;
}

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard'),
  });
}


// === Usage (multi-dimension) ===

export function useUsageSummary() {
  return useQuery<{ totalInputTokens: number; totalOutputTokens: number; totalCost: number; totalRequests: number; tenantCount: number; chatgptEquivalent: number }>({
    queryKey: ['usage-summary'],
    queryFn: () => api.get('/usage/summary'),
  });
}

export function useUsageByDepartment() {
  return useQuery<{ department: string; inputTokens: number; outputTokens: number; requests: number; cost: number; agents: number }[]>({
    queryKey: ['usage-by-dept'],
    queryFn: () => api.get('/usage/by-department'),
  });
}

export function useUsageByAgent() {
  return useQuery<{ agentId: string; agentName: string; employeeName: string; positionName: string; inputTokens: number; outputTokens: number; requests: number; cost: number }[]>({
    queryKey: ['usage-by-agent'],
    queryFn: () => api.get('/usage/by-agent'),
  });
}

export function useAgentDailyUsage(agentId: string) {
  return useQuery<{ date: string; inputTokens: number; outputTokens: number; requests: number; cost: number }[]>({
    queryKey: ['agent-daily-usage', agentId],
    queryFn: () => api.get(`/usage/agent/${agentId}`),
    enabled: !!agentId,
  });
}

export function useUsageBudgets() {
  return useQuery<{ department: string; budget: number; used: number; projected: number; status: string }[]>({
    queryKey: ['usage-budgets'],
    queryFn: () => api.get('/usage/budgets'),
  });
}

// === Settings ===

export function useModelConfig() {
  return useQuery<{
    default: { modelId: string; modelName: string; inputRate: number; outputRate: number };
    fallback: { modelId: string; modelName: string; inputRate: number; outputRate: number };
    positionOverrides: Record<string, { modelId: string; modelName: string; inputRate: number; outputRate: number; reason: string }>;
    availableModels: { modelId: string; modelName: string; inputRate: number; outputRate: number; enabled: boolean }[];
  }>({
    queryKey: ['model-config'],
    queryFn: () => api.get('/settings/model'),
  });
}

export function useSecurityConfig() {
  return useQuery<{
    alwaysBlocked: string[]; piiDetection: { enabled: boolean; mode: string };
    dataSovereignty: { enabled: boolean; region: string }; conversationRetention: { days: number };
    dockerSandbox: boolean; fastPathRouting: boolean; verboseAudit: boolean;
  }>({
    queryKey: ['security-config'],
    queryFn: () => api.get('/settings/security'),
  });
}

export function useUpdateModelConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, any>) => api.put('/settings/model/default', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['model-config'] }),
  });
}

export function useUpdateSecurityConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, any>) => api.put('/settings/security', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['security-config'] }),
  });
}

export function useServiceStatus() {
  return useQuery<{
    gateway: { status: string; port: number; uptime: string; requestsToday: number };
    auth_agent: { status: string; uptime: string; approvalsProcessed: number };
    bedrock: { status: string; region: string; latencyMs: number; vpcEndpoint: boolean };
    dynamodb: { status: string; table: string; itemCount: number };
    s3: { status: string; bucket: string };
  }>({
    queryKey: ['service-status'],
    queryFn: () => api.get('/settings/services'),
  });
}

// === SOUL save ===

export function useSaveSoul() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, layer, content }: { agentId: string; layer: string; content: string }) =>
      api.put<{ saved: boolean; layer: string; version: number }>(`/agents/${agentId}/soul`, { layer, content }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['agent-soul', vars.agentId] });
      qc.invalidateQueries({ queryKey: ['agent', vars.agentId] });
    },
  });
}

// === Workspace file operations ===

export function useWorkspaceTree(agentId: string) {
  return useQuery({
    queryKey: ['workspace-tree', agentId],
    queryFn: () => api.get(`/workspace/tree?agent_id=${agentId}`),
    enabled: !!agentId,
  });
}

export function useWorkspaceFile(key: string) {
  return useQuery<{ key: string; content: string; size: number }>({
    queryKey: ['workspace-file', key],
    queryFn: () => api.get(`/workspace/file?key=${encodeURIComponent(key)}`),
    enabled: !!key,
  });
}


// === Skills ===

export interface SkillManifest {
  id: string; name: string; version: string; description: string; author: string;
  layer: 1 | 2 | 3; category: string; scope: string;
  status?: string; bundleSizeMB?: number; approvalRequired?: boolean; approvalNote?: string;
  requires: { env: string[]; tools: string[] };
  permissions: { allowedRoles: string[]; blockedRoles: string[] };
}

export interface SkillApiKey {
  id: string; skillName: string; envVar: string; ssmPath: string;
  status: string; lastRotated: string; createdBy: string;
}

export function useSkills() {
  return useQuery<SkillManifest[]>({
    queryKey: ['skills'],
    queryFn: () => api.get('/skills'),
  });
}

export function useSkillKeys() {
  return useQuery<SkillApiKey[]>({
    queryKey: ['skill-keys'],
    queryFn: () => api.get('/skills/keys/all'),
  });
}


// === Approvals ===

export interface ApprovalRequest {
  id: string; tenant: string; tenantId: string; tool: string; reason: string;
  risk: 'high' | 'medium' | 'low'; timestamp: string; status: 'pending' | 'approved' | 'denied';
  reviewer?: string; resolvedAt?: string;
}

export function useApprovals() {
  return useQuery<{ pending: ApprovalRequest[]; resolved: ApprovalRequest[] }>({
    queryKey: ['approvals'],
    queryFn: () => api.get('/approvals'),
  });
}

export function useApproveRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/approvals/${id}/approve`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals'] }),
  });
}

export function useDenyRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/approvals/${id}/deny`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals'] }),
  });
}


// === Knowledge Base ===

export interface KnowledgeBaseItem {
  id: string; name: string; scope: string; scopeName: string;
  docCount: number; sizeMB: number; sizeBytes: number;
  status: string; lastUpdated: string; accessibleBy: string;
  s3Prefix: string;
  files?: { name: string; size: number; key: string }[];
}

export function useKnowledgeBases() {
  return useQuery<KnowledgeBaseItem[]>({
    queryKey: ['knowledge'],
    queryFn: () => api.get('/knowledge'),
  });
}

export function useKnowledgeSearch(query: string) {
  return useQuery<{ doc: string; kb: string; kbName: string; score: number; snippet: string; key: string }[]>({
    queryKey: ['knowledge-search', query],
    queryFn: () => api.get(`/knowledge/search?query=${encodeURIComponent(query)}`),
    enabled: !!query,
  });
}

export function useUploadKnowledgeDoc() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { kbId: string; filename: string; content: string }) =>
      api.post<{ key: string; saved: boolean }>('/knowledge/upload', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge'] }),
  });
}

// === Playground ===

export function usePlaygroundProfiles() {
  return useQuery<Record<string, { role: string; tools: string[]; planA: string; planE: string }>>({
    queryKey: ['playground-profiles'],
    queryFn: () => api.get('/playground/profiles'),
  });
}

export function usePlaygroundSend() {
  return useMutation({
    mutationFn: (data: { tenant_id: string; message: string; mode?: string }) =>
      api.post<{ response: string; tenant_id: string; profile: Record<string, unknown>; plan_a: string; plan_e: string; source?: string }>('/playground/send', data),
  });
}


// === Routing Rules ===

export interface RoutingRule {
  id: string; priority: number; name: string;
  condition: Record<string, string>; action: string;
  agentId?: string; description: string;
}

export function useRoutingRules() {
  return useQuery<RoutingRule[]>({
    queryKey: ['routing-rules'],
    queryFn: () => api.get('/routing/rules'),
  });
}

// === IM User Mappings ===

export interface UserMapping {
  channel: string;
  channelUserId: string;
  employeeId: string;
  ssmPath?: string;
}

export function useUserMappings() {
  return useQuery<UserMapping[]>({
    queryKey: ['user-mappings'],
    queryFn: () => api.get('/bindings/user-mappings'),
  });
}

export function useCreateUserMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { channel: string; channelUserId: string; employeeId: string }) =>
      api.post<{ saved: boolean }>('/bindings/user-mappings', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-mappings'] }),
  });
}

export function useDeleteUserMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { channel: string; channelUserId: string }) =>
      api.del<{ deleted: boolean }>(`/bindings/user-mappings?channel=${data.channel}&channelUserId=${data.channelUserId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-mappings'] }),
  });
}
