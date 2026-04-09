/** Property 19: measured load time must be ≤ budget (ms). */
export function isWithinLoadBudget(measuredMs: number, budgetMs: number): boolean {
  return measuredMs >= 0 && budgetMs >= 0 && measuredMs <= budgetMs
}
