/**
 * Zustand Store for MassGen Agent State Management
 *
 * Manages all agent state, votes, and coordination events.
 * Updates from WebSocket events are processed here.
 */

import { create } from 'zustand';
import type {
  AgentRound,
  AgentState,
  AgentStatus,
  Answer,
  FileInfo,
  SessionState,
  ToolCallInfo,
  ViewMode,
  VoteResults,
  WSEvent,
} from '../types';

interface AgentStore extends SessionState {
  // Actions
  initSession: (sessionId: string, question: string, agents: string[], theme: string, agentModels?: Record<string, string>) => void;
  updateAgentContent: (agentId: string, content: string, contentType: string) => void;
  updateAgentStatus: (agentId: string, status: AgentStatus) => void;
  addOrchestratorEvent: (event: string) => void;
  updateVoteDistribution: (votes: Record<string, number>) => void;
  recordVote: (voterId: string, targetId: string, reason: string) => void;
  setConsensus: (winnerId: string) => void;
  setFinalAnswer: (answer: string, voteResults: VoteResults, selectedAgent: string) => void;
  addAnswer: (answer: Answer) => void;
  addFileChange: (agentId: string, file: FileInfo) => void;
  addToolCall: (agentId: string, toolCall: ToolCallInfo) => void;
  updateToolResult: (agentId: string, toolId: string | undefined, result: string, success: boolean) => void;
  setError: (message: string) => void;
  setComplete: (isComplete: boolean) => void;
  setViewMode: (mode: ViewMode) => void;
  startNewRound: (agentId: string, roundType: 'answer' | 'vote' | 'final', customLabel?: string) => void;
  finalizeRoundWithLabel: (agentId: string, label: string, createNewRound?: boolean) => void;
  setAgentRound: (agentId: string, roundId: string) => void;
  reset: () => void;
  processWSEvent: (event: WSEvent) => void;
}

const initialState: SessionState = {
  sessionId: '',
  question: '',
  agents: {},
  agentOrder: [],
  answers: [],
  voteDistribution: {},
  selectedAgent: undefined,
  finalAnswer: undefined,
  orchestratorEvents: [],
  isComplete: false,
  error: undefined,
  theme: 'dark',
  viewMode: 'coordination',
};

const createAgentState = (id: string, modelName?: string): AgentState => {
  const initialRoundId = `${id}-round-0`;
  return {
    id,
    modelName,
    status: 'waiting',
    content: [],
    currentContent: '',
    rounds: [{
      id: initialRoundId,
      roundNumber: 0,
      type: 'answer',
      label: 'current',
      content: '',
      startTimestamp: Date.now(),
    }],
    currentRoundId: initialRoundId,
    displayRoundId: initialRoundId,
    answerCount: 0,
    voteCount: 0,
    files: [],
    toolCalls: [],
  };
};

export const useAgentStore = create<AgentStore>((set, get) => ({
  ...initialState,

  initSession: (sessionId, question, agents, theme, agentModels) => {
    const agentStates: Record<string, AgentState> = {};
    agents.forEach((id) => {
      agentStates[id] = createAgentState(id, agentModels?.[id]);
    });

    set({
      sessionId,
      question,
      agents: agentStates,
      agentOrder: agents,
      answers: [],
      theme,
      isComplete: false,
      error: undefined,
      voteDistribution: {},
      selectedAgent: undefined,
      finalAnswer: undefined,
      orchestratorEvents: [],
      viewMode: 'coordination',
    });
  },

  updateAgentContent: (agentId, content, contentType) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      // Increment answer count if this looks like a new answer
      const newAnswerCount =
        contentType === 'status' && content.includes('new_answer')
          ? agent.answerCount + 1
          : agent.answerCount;

      // Update current round's content
      const updatedRounds = agent.rounds.map((round) =>
        round.id === agent.currentRoundId
          ? { ...round, content: round.content + content }
          : round
      );

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            content: [...agent.content, content],
            currentContent: agent.currentContent + content,
            rounds: updatedRounds,
            answerCount: newAnswerCount,
          },
        },
      };
    });
  },

  updateAgentStatus: (agentId, status) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            status,
          },
        },
      };
    });
  },

  addOrchestratorEvent: (event) => {
    set((state) => ({
      orchestratorEvents: [...state.orchestratorEvents, event],
    }));
  },

  updateVoteDistribution: (votes) => {
    set({ voteDistribution: votes });
  },

  recordVote: (voterId, targetId, reason) => {
    set((state) => {
      const agent = state.agents[voterId];
      if (!agent) return state;

      // Update vote distribution
      const newDistribution = { ...state.voteDistribution };
      newDistribution[targetId] = (newDistribution[targetId] || 0) + 1;

      return {
        agents: {
          ...state.agents,
          [voterId]: {
            ...agent,
            voteTarget: targetId,
            voteReason: reason,
            voteCount: agent.voteCount + 1,
          },
        },
        voteDistribution: newDistribution,
      };
    });
  },

  setConsensus: (winnerId) => {
    const store = get();

    // Start a "final" round for the winner to give their final answer
    // This will automatically rename the previous "current" round to the proper answer label
    store.startNewRound(winnerId, 'final', 'final');
    // Auto-switch to winner view
    set({ selectedAgent: winnerId, viewMode: 'winner' });
  },

  setFinalAnswer: (answer, _voteResults, selectedAgent) => {
    set({
      finalAnswer: answer,
      selectedAgent,
      isComplete: true,
    });
  },

  addAnswer: (answer) => {
    set((state) => {
      // Also update the agent's answer count
      const agent = state.agents[answer.agentId];
      const updatedAgents = agent
        ? {
            ...state.agents,
            [answer.agentId]: {
              ...agent,
              answerCount: Math.max(agent.answerCount, answer.answerNumber),
            },
          }
        : state.agents;

      return {
        answers: [...state.answers, answer],
        agents: updatedAgents,
      };
    });
  },

  addFileChange: (agentId, file) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            files: [...agent.files, file],
          },
        },
      };
    });
  },

  addToolCall: (agentId, toolCall) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            toolCalls: [...agent.toolCalls, toolCall],
          },
        },
      };
    });
  },

  updateToolResult: (agentId, toolId, result, success) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      const toolCalls = agent.toolCalls.map((tc) => {
        if (tc.id === toolId || (!toolId && tc.result === undefined)) {
          return { ...tc, result, success };
        }
        return tc;
      });

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            toolCalls,
          },
        },
      };
    });
  },

  setError: (message) => {
    set({ error: message });
  },

  setComplete: (isComplete) => {
    set({ isComplete });
  },

  setViewMode: (mode) => {
    set({ viewMode: mode });
  },

  startNewRound: (agentId, roundType, customLabel) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      const agentIndex = state.agentOrder.indexOf(agentId) + 1;

      // Calculate the answer number for the PREVIOUS round (it's getting closed/completed)
      // Count existing labeled answer rounds (not "current")
      const existingAnswerRounds = agent.rounds.filter(
        r => r.type === 'answer' && r.label !== 'current'
      ).length;
      const previousAnswerNumber = existingAnswerRounds + 1;

      // Generate label for the PREVIOUS round (the completed answer)
      // Always use proper answer label format for the previous round
      const previousRoundLabel = `answer${agentIndex}.${previousAnswerNumber}`;

      // Close previous round and rename it from "current" to the proper label
      const now = Date.now();
      const newRoundId = `${agentId}-round-${agent.rounds.length}`;

      const updatedRounds = agent.rounds.map((round) => {
        if (round.id === agent.currentRoundId && !round.endTimestamp) {
          // Rename the previous "current" round to the answer label (e.g., "answer2.1")
          const newLabel = round.label === 'current' ? previousRoundLabel : round.label;
          return { ...round, endTimestamp: now, label: newLabel };
        }
        return round;
      });

      // Determine the new round's label
      // - If customLabel is 'final', this is the final round
      // - Otherwise it's "current" (active/in-progress work)
      const newRoundLabel = customLabel === 'final' ? 'final' : 'current';

      // Calculate round number for the new round
      const newRoundNumber = roundType === 'answer'
        ? previousAnswerNumber + 1
        : agent.rounds.filter(r => r.type === roundType && r.label !== 'current').length + 1;

      // Create new round
      const newRound: AgentRound = {
        id: newRoundId,
        roundNumber: newRoundNumber,
        type: roundType,
        label: newRoundLabel,
        content: '',
        startTimestamp: now,
      };

      // Store the previous round ID before creating new round
      const previousRoundId = agent.currentRoundId;

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            rounds: [...updatedRounds, newRound],
            currentRoundId: newRoundId,           // New streaming goes here
            displayRoundId: previousRoundId,      // Show completed answer in UI
            currentContent: '', // Reset current content for new round
            voteCount: roundType === 'vote' ? agent.voteCount + 1 : agent.voteCount,
          },
        },
      };
    });
  },

  finalizeRoundWithLabel: (agentId, label, createNewRound = true) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      const now = Date.now();

      // DEBUG: Log the finalization
      const currentRound = agent.rounds.find(r => r.id === agent.currentRoundId);
      console.log(`[DEBUG] finalizeRoundWithLabel called:`, {
        agentId,
        label,
        createNewRound,
        currentRoundId: agent.currentRoundId,
        currentRoundLabel: currentRound?.label,
        currentRoundContentPreview: currentRound?.content?.substring(0, 100),
        allRounds: agent.rounds.map(r => ({ id: r.id, label: r.label, contentLen: r.content?.length })),
      });

      // Close current round with the provided label
      const updatedRounds = agent.rounds.map((round) => {
        if (round.id === agent.currentRoundId && round.label === 'current') {
          return { ...round, endTimestamp: now, label: label };
        }
        return round;
      });

      // Store the previous round ID (the one we just labeled)
      const previousRoundId = agent.currentRoundId;

      // Optionally create new "current" round for future content
      if (createNewRound) {
        const newRoundId = `${agentId}-round-${agent.rounds.length}`;
        const newRound: AgentRound = {
          id: newRoundId,
          roundNumber: agent.rounds.length,
          type: 'answer',
          label: 'current',
          content: '',
          startTimestamp: now,
        };

        return {
          agents: {
            ...state.agents,
            [agentId]: {
              ...agent,
              rounds: [...updatedRounds, newRound],
              currentRoundId: newRoundId,
              displayRoundId: previousRoundId,
              currentContent: '',
            },
          },
        };
      }

      // Just finalize without creating new round
      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            rounds: updatedRounds,
            displayRoundId: previousRoundId,
            currentContent: currentRound?.content || '',
          },
        },
      };
    });
  },

  setAgentRound: (agentId, roundId) => {
    set((state) => {
      const agent = state.agents[agentId];
      if (!agent) return state;

      const round = agent.rounds.find(r => r.id === roundId);
      if (!round) return state;

      return {
        agents: {
          ...state.agents,
          [agentId]: {
            ...agent,
            displayRoundId: roundId,      // User selects display round
            currentContent: round.content, // Show that round's content
          },
        },
      };
    });
  },

  reset: () => {
    set(initialState);
  },

  // Process WebSocket events
  processWSEvent: (event) => {
    const store = get();

    // DEBUG: Log all WebSocket events (except high-frequency ones)
    if (event.type !== 'agent_content' && event.type !== 'keepalive') {
      console.log(`[DEBUG] WebSocket event:`, event.type, event);
    }

    switch (event.type) {
      case 'init':
        if ('agents' in event && 'question' in event) {
          store.initSession(
            event.session_id,
            event.question,
            event.agents,
            'theme' in event ? event.theme : 'dark',
            'agent_models' in event ? (event as { agent_models: Record<string, string> }).agent_models : undefined
          );
        }
        break;

      case 'agent_content':
        if ('agent_id' in event && 'content' in event) {
          store.updateAgentContent(
            event.agent_id,
            event.content,
            'content_type' in event ? event.content_type : 'thinking'
          );
        }
        break;

      case 'agent_status':
        if ('agent_id' in event && 'status' in event) {
          store.updateAgentStatus(event.agent_id, event.status as AgentStatus);
        }
        break;

      case 'orchestrator_event':
        if ('event' in event) {
          store.addOrchestratorEvent(event.event);
        }
        break;

      case 'vote_cast':
        console.log(`[DEBUG] vote_cast event received:`, event);
        if ('voter_id' in event && 'target_id' in event) {
          // Get the agent to calculate vote number
          const votingAgent = get().agents[event.voter_id];
          const voteNumber = votingAgent ? votingAgent.voteCount + 1 : 1;

          console.log(`[DEBUG] Processing vote_cast for ${event.voter_id}, voteNumber=${voteNumber}`);

          // Finalize current round as a vote round - don't create new round since voting is done
          store.finalizeRoundWithLabel(event.voter_id, `vote${voteNumber}`, false);

          store.recordVote(
            event.voter_id,
            event.target_id,
            'reason' in event ? event.reason : ''
          );
        }
        break;

      case 'vote_distribution':
        if ('votes' in event) {
          store.updateVoteDistribution(event.votes);
        }
        break;

      case 'consensus_reached':
        if ('winner_id' in event) {
          store.setConsensus(event.winner_id);
        }
        break;

      case 'final_answer':
        if ('answer' in event) {
          store.setFinalAnswer(
            event.answer,
            'vote_results' in event ? event.vote_results : {},
            'selected_agent' in event ? event.selected_agent : ''
          );
        }
        break;

      case 'new_answer':
        console.log(`[DEBUG] new_answer event received:`, event);
        if ('agent_id' in event && 'content' in event) {
          const newAnswerEvent = event as {
            agent_id: string;
            content: string;
            answer_id?: string;
            answer_number?: number;
            answer_label?: string;  // e.g., "agent2.1" from backend
            timestamp: number;
          };

          // Check if this agent has already voted - if so, this is the "final" answer
          // which will be handled by consensus_reached, so skip creating a new round
          const agentState = get().agents[newAnswerEvent.agent_id];
          if (agentState && agentState.voteCount > 0) {
            console.log(`[DEBUG] Skipping new_answer for ${newAnswerEvent.agent_id} - agent has already voted (voteCount=${agentState.voteCount}), final answer handled by consensus_reached`);
            break;
          }

          // Get the agent index for generating label if not provided
          const agentIndex = get().agentOrder.indexOf(newAnswerEvent.agent_id) + 1;
          const answerNumber = newAnswerEvent.answer_number ?? 1;

          // Use backend label if provided, otherwise generate one
          const answerLabel = newAnswerEvent.answer_label
            || `answer${agentIndex}.${answerNumber}`;

          console.log(`[DEBUG] Processing new_answer for ${newAnswerEvent.agent_id}, label=${answerLabel}, answerNumber=${answerNumber}`);

          // Finalize the current round with the proper answer label
          store.finalizeRoundWithLabel(newAnswerEvent.agent_id, answerLabel);

          store.addAnswer({
            id: newAnswerEvent.answer_id ?? `${newAnswerEvent.agent_id}-${Date.now()}`,
            agentId: newAnswerEvent.agent_id,
            answerNumber: answerNumber,
            content: newAnswerEvent.content,
            timestamp: newAnswerEvent.timestamp,
            votes: 0,
          });
        }
        break;

      case 'restart':
        // When an agent restarts, start a new answer round
        if ('reason' in event) {
          // The restart affects all agents - start new rounds for each
          const agentOrder = get().agentOrder;
          agentOrder.forEach((agentId) => {
            store.startNewRound(agentId, 'answer');
          });
        }
        break;

      case 'file_change':
        if ('agent_id' in event && 'path' in event) {
          store.addFileChange(event.agent_id, {
            path: event.path,
            operation: 'operation' in event ? event.operation : 'create',
            timestamp: event.timestamp,
            contentPreview: 'content_preview' in event ? event.content_preview : undefined,
          });
        }
        break;

      case 'tool_call':
        if ('agent_id' in event && 'tool_name' in event) {
          store.addToolCall(event.agent_id, {
            id: 'tool_id' in event ? event.tool_id : undefined,
            name: event.tool_name,
            args: 'tool_args' in event ? event.tool_args : {},
            timestamp: event.timestamp,
          });
        }
        break;

      case 'tool_result':
        if ('agent_id' in event && 'result' in event) {
          store.updateToolResult(
            event.agent_id,
            'tool_id' in event ? event.tool_id : undefined,
            event.result,
            'success' in event ? event.success : true
          );
        }
        break;

      case 'error':
        if ('message' in event) {
          store.setError(event.message);
        }
        break;

      case 'done':
      case 'coordination_complete':
        store.setComplete(true);
        break;

      case 'state_snapshot':
        // Handle full state snapshot for late-joining clients
        if ('agents' in event && Array.isArray(event.agents)) {
          store.initSession(
            event.session_id,
            'question' in event ? (event as { question: string }).question : '',
            event.agents,
            'theme' in event ? (event as { theme: string }).theme : 'dark'
          );
        }
        break;

      default:
        // Ignore unknown events (like keepalive)
        break;
    }
  },
}));

// Selectors
export const selectAgents = (state: AgentStore) => state.agents;
export const selectAgentOrder = (state: AgentStore) => state.agentOrder;
export const selectAnswers = (state: AgentStore) => state.answers;
export const selectVoteDistribution = (state: AgentStore) => state.voteDistribution;
export const selectSelectedAgent = (state: AgentStore) => state.selectedAgent;
export const selectFinalAnswer = (state: AgentStore) => state.finalAnswer;
export const selectIsComplete = (state: AgentStore) => state.isComplete;
export const selectQuestion = (state: AgentStore) => state.question;
export const selectOrchestratorEvents = (state: AgentStore) => state.orchestratorEvents;
export const selectViewMode = (state: AgentStore) => state.viewMode;
