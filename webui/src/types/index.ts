/**
 * MassGen Web UI Type Definitions
 */

// Agent status types
export type AgentStatus = 'waiting' | 'working' | 'voting' | 'completed' | 'failed';

// WebSocket event types (match Python WebDisplay events)
export type WSEventType =
  | 'init'
  | 'agent_content'
  | 'agent_status'
  | 'orchestrator_event'
  | 'vote_cast'
  | 'vote_distribution'
  | 'consensus_reached'
  | 'final_answer'
  | 'new_answer'
  | 'post_evaluation'
  | 'file_change'
  | 'tool_call'
  | 'tool_result'
  | 'restart'
  | 'restart_context'
  | 'error'
  | 'done'
  | 'state_snapshot'
  | 'coordination_started'
  | 'coordination_complete'
  | 'keepalive';

// Base WebSocket message
export interface WSMessage {
  type: WSEventType;
  session_id: string;
  timestamp: number;
  sequence: number;
}

// Agent info with model name
export interface AgentInfo {
  id: string;
  model?: string;  // Model name like "gpt-5", "claude-3.5-sonnet"
}

// Specific event payloads
export interface InitEvent extends WSMessage {
  type: 'init';
  question: string;
  log_filename?: string;
  agents: string[];
  agent_models?: Record<string, string>;  // Map of agent_id -> model name
  theme: string;
}

export interface AgentContentEvent extends WSMessage {
  type: 'agent_content';
  agent_id: string;
  content: string;
  content_type: 'thinking' | 'tool' | 'status';
}

export interface AgentStatusEvent extends WSMessage {
  type: 'agent_status';
  agent_id: string;
  status: AgentStatus;
}

export interface OrchestratorEvent extends WSMessage {
  type: 'orchestrator_event';
  event: string;
}

export interface VoteCastEvent extends WSMessage {
  type: 'vote_cast';
  voter_id: string;
  target_id: string;
  reason: string;
}

export interface VoteDistributionEvent extends WSMessage {
  type: 'vote_distribution';
  votes: Record<string, number>;
}

export interface ConsensusReachedEvent extends WSMessage {
  type: 'consensus_reached';
  winner_id: string;
  vote_distribution: Record<string, number>;
}

export interface FinalAnswerEvent extends WSMessage {
  type: 'final_answer';
  answer: string;
  vote_results: VoteResults;
  selected_agent: string;
}

export interface NewAnswerEvent extends WSMessage {
  type: 'new_answer';
  agent_id: string;
  answer_id: string;
  answer_number: number;
  content: string;
}

export interface FileChangeEvent extends WSMessage {
  type: 'file_change';
  agent_id: string;
  path: string;
  operation: 'create' | 'modify' | 'delete';
  content_preview?: string;
}

export interface ToolCallEvent extends WSMessage {
  type: 'tool_call';
  agent_id: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  tool_id?: string;
}

export interface ToolResultEvent extends WSMessage {
  type: 'tool_result';
  agent_id: string;
  tool_name: string;
  result: string;
  tool_id?: string;
  success: boolean;
}

export interface RestartEvent extends WSMessage {
  type: 'restart';
  reason: string;
  instructions: string;
  attempt: number;
  max_attempts: number;
}

export interface ErrorEvent extends WSMessage {
  type: 'error';
  message: string;
  agent_id?: string;
}

// Vote results structure
export interface VoteResults {
  vote_counts?: Record<string, number>;
  voter_details?: Record<string, { voter: string; reason: string }[]>;
  winner?: string;
  is_tie?: boolean;
  total_votes?: number;
  agents_voted?: number;
}

// Round of agent output (for restart/new answer separation)
export interface AgentRound {
  id: string;
  roundNumber: number;
  type: 'answer' | 'vote' | 'final';
  label: string;  // e.g., "answer1.1", "vote1", or "final"
  content: string;
  startTimestamp: number;
  endTimestamp?: number;
  workspacePath?: string;  // Path to workspace snapshot for this answer
}

// Agent state in store
export interface AgentState {
  id: string;
  modelName?: string;  // e.g., "gpt-5" for display as "agent_a (gpt-5)"
  status: AgentStatus;
  content: string[];
  currentContent: string;
  rounds: AgentRound[];  // History of rounds for dropdown
  currentRoundId: string;  // Where NEW streaming content appends
  displayRoundId: string;  // What the dropdown shows (user-selectable)
  voteTarget?: string;
  voteReason?: string;
  answerCount: number;
  voteCount: number;  // Track votes for labeling
  files: FileInfo[];
  toolCalls: ToolCallInfo[];
}

export interface FileInfo {
  path: string;
  operation: 'create' | 'modify' | 'delete';
  timestamp: number;
  contentPreview?: string;
}

export interface ToolCallInfo {
  id?: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  success?: boolean;
  timestamp: number;
}

// Answer from an agent
export interface Answer {
  id: string;
  agentId: string;
  answerNumber: number;
  content: string;
  timestamp: number;
  votes: number;
  isWinner?: boolean;
  workspacePath?: string;  // Path to workspace snapshot for this answer
}

// Workspace linked to specific answer version
export interface AnswerWorkspace {
  answerId: string;
  agentId: string;
  answerNumber: number;
  answerLabel: string;
  timestamp: string;
  workspacePath: string;
}

// View mode for UI
// - 'coordination': Shows all agents in carousel during coordination
// - 'finalStreaming': Shows winner agent streaming final answer after consensus
// - 'finalComplete': Shows full-screen final answer view when complete
export type ViewMode = 'coordination' | 'finalStreaming' | 'finalComplete';

// Per-agent UI state (stored in Zustand for persistence across re-renders)
export interface AgentUIState {
  dropdownOpen: boolean;
}

// Conversation message for multi-turn
export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  turn?: number;
}

// Full session state
export interface SessionState {
  sessionId: string;
  question: string;
  agents: Record<string, AgentState>;
  agentOrder: string[];
  answers: Answer[];
  voteDistribution: Record<string, number>;
  selectedAgent?: string;
  finalAnswer?: string;
  orchestratorEvents: string[];
  isComplete: boolean;
  selectingWinner: boolean;  // True when all votes are in but winner not yet selected
  error?: string;
  theme: string;
  viewMode: ViewMode;  // 'coordination' shows all agents, 'winner' shows only winner
  // Multi-turn conversation state
  turnNumber: number;
  conversationHistory: ConversationMessage[];
  // Per-agent UI state for dropdown tracking
  agentUIState: Record<string, AgentUIState>;
  // Skip animation when restoring from snapshot
  restoredFromSnapshot: boolean;
  // Automation mode: shows simplified timeline view for LLM/automation usage
  automationMode: boolean;
  // Log directory path for status.json monitoring
  logDir?: string;
}

// Union type for all WebSocket events
export type WSEvent =
  | InitEvent
  | AgentContentEvent
  | AgentStatusEvent
  | OrchestratorEvent
  | VoteCastEvent
  | VoteDistributionEvent
  | ConsensusReachedEvent
  | FinalAnswerEvent
  | NewAnswerEvent
  | FileChangeEvent
  | ToolCallEvent
  | ToolResultEvent
  | RestartEvent
  | ErrorEvent
  | WSMessage;

// Config file info from API
export interface ConfigInfo {
  name: string;
  path: string;
  category: string;
  relative: string;
}

// Session info from API
export interface SessionInfo {
  session_id: string;
  connections: number;
  has_display: boolean;
  is_running: boolean;
  question?: string;
  status?: 'active' | 'completed';
  completed_at?: number;
}

// ============================================================================
// Timeline Types (for Answer Timeline visualization)
// ============================================================================

// Timeline node types
export type TimelineNodeType = 'answer' | 'vote' | 'final';

// A single node on the timeline
export interface TimelineNode {
  id: string;
  type: TimelineNodeType;
  agentId: string;
  label: string;           // e.g., "answer1.1", "vote1.1", "final"
  timestamp: number;
  round: number;
  contextSources: string[];  // Labels of answers used as context
  votedFor?: string;         // For vote nodes: which agent was voted for
}

// Timeline data for visualization
export interface TimelineData {
  nodes: TimelineNode[];
  agents: string[];
  startTime: number;
  endTime?: number;
}

// ============================================================================
// File Viewer Types (for Workspace File Viewer)
// ============================================================================

// Response from /api/workspace/file endpoint
export interface FileContentResponse {
  content: string;
  binary: boolean;
  size: number;
  mimeType: string;
  language: string;  // For syntax highlighting (e.g., "python", "typescript")
  error?: string;
}
