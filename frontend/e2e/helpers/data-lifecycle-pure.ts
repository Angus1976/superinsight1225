/**
 * Data lifecycle count invariant (Property 10) — pure pipeline semantics.
 */
export interface PipelineStageCounts {
  acquisition: number
  annotationTask: number
  exportRecord: number
}

/** Requirement 3.6: counts stay aligned across stages when pipeline is consistent. */
export function assertLifecycleCountInvariant(c: PipelineStageCounts): boolean {
  return c.acquisition === c.annotationTask && c.annotationTask === c.exportRecord
}

/** Sum of per-stage deltas should equal export when no loss/gain (simplified model). */
export function pipelineTotalMatchesExport(
  rowsImported: number,
  rowsTasked: number,
  rowsExported: number,
): boolean {
  return rowsImported === rowsTasked && rowsTasked === rowsExported
}
