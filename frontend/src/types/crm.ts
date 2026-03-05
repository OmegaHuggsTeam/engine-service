// CRM Contract Types — shared between frontend modules and gateway API.

// ---------------------------------------------------------------------------
// Node types
// ---------------------------------------------------------------------------

export interface CrmLead {
  id: string;
  name: string;
  email?: string;
  company?: string;
  trust: number; // 0-1
  interaction_count: number;
  source_channel: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface CrmFlow {
  id: string;
  name: string;
  objective: string;
  n8n_workflow_id?: string;
  status: "draft" | "active" | "paused" | "completed";
  lead_count: number;
  created_at: string;
}

export interface CrmInteraction {
  id: string;
  lead_id: string;
  agent_id?: string;
  channel: string;
  action: string;
  detail: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Graph visualization
// ---------------------------------------------------------------------------

export interface CrmGraphNode {
  id: string;
  type: "lead" | "flow" | "agent" | "interaction";
  label: string;
  properties: Record<string, unknown>;
}

export interface CrmGraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface CrmGraph {
  nodes: CrmGraphNode[];
  edges: CrmGraphEdge[];
}

// ---------------------------------------------------------------------------
// WebSocket events
// ---------------------------------------------------------------------------

export interface CrmEvent {
  type:
    | "lead_created"
    | "lead_updated"
    | "interaction_recorded"
    | "flow_status_changed";
  payload: Record<string, unknown>;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// API request bodies
// ---------------------------------------------------------------------------

export interface CrmLeadCreate {
  name: string;
  email?: string;
  company?: string;
  source_channel?: string;
  tags?: string[];
}

export interface CrmLeadUpdate {
  name?: string;
  email?: string;
  company?: string;
  tags?: string[];
  trust?: number;
}

export interface CrmFlowCreate {
  name: string;
  objective: string;
  n8n_workflow_id?: string;
}

export interface CrmFlowUpdate {
  name?: string;
  objective?: string;
  status?: "draft" | "active" | "paused" | "completed";
}

export interface CrmInteractionCreate {
  lead_id: string;
  agent_id?: string;
  channel: string;
  action: string;
  detail: string;
}

export interface CrmLeadScore {
  lead_id: string;
  trust: number;
  interaction_count: number;
  last_interaction: string | null;
  flow_count: number;
  interaction_score: number;
  recency_score: number;
  flow_score: number;
}

// ---------------------------------------------------------------------------
// Dashboard stats
// ---------------------------------------------------------------------------

export interface CrmStats {
  total_leads: number;
  total_flows: number;
  total_interactions: number;
  avg_trust: number;
}
