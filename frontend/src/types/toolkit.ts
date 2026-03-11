/**
 * TypeScript type definitions for Toolkit smart processing routing.
 * Mirrors backend Pydantic schemas: StrategyCandidateDTO, RouteResponse, ExecuteRequest.
 */

// ============================================================================
// Processing Mode
// ============================================================================

/** Processing mode: auto (system-recommended) or manual (user-selected) */
export type ProcessingMode = 'auto' | 'manual';

// ============================================================================
// Strategy
// ============================================================================

/** A candidate strategy returned by StrategyRouter.evaluate_strategies() */
export interface StrategyCandidate {
  name: string;
  score: number;
  explanation: string;
  primaryStorage: string;
}

// ============================================================================
// Execution Status
// ============================================================================

/** Pipeline execution status, polled from /api/toolkit/execute/{id} */
export interface ExecutionStatus {
  executionId: string;
  status: 'running' | 'completed' | 'failed' | 'paused';
  progress: number;
  currentStage?: string;
  error?: string;
  storageLocation?: string;
}
