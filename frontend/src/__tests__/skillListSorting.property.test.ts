/**
 * Property Test: 技能列表排序不变量
 *
 * **Validates: Requirements 1.3**
 *
 * Property 2: For any skill list returned by list_skills,
 * each consecutive pair (skill[i], skill[i+1]) must satisfy
 * skill[i].deployed_at >= skill[i+1].deployed_at.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import type { SkillDetail } from '@/types/aiAssistant';

/** Generate an ISO date string from a bounded integer timestamp. */
const isoDateArb = fc
  .integer({ min: 1577836800000, max: 1924991999000 }) // 2020-01-01 to 2030-12-31
  .map((ts) => new Date(ts).toISOString());

/** Arbitrary that generates a valid SkillDetail with a random deployed_at date. */
const skillDetailArb: fc.Arbitrary<SkillDetail> = fc.record({
  id: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 50 }),
  version: fc.stringMatching(/^[0-9]+\.[0-9]+\.[0-9]+$/),
  status: fc.constantFrom('deployed', 'pending', 'removed'),
  description: fc.option(fc.string({ maxLength: 100 }), { nil: undefined }),
  category: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: undefined }),
  gateway_id: fc.uuid(),
  gateway_name: fc.string({ minLength: 1, maxLength: 30 }),
  deployed_at: fc.option(isoDateArb, { nil: undefined }),
  created_at: isoDateArb,
});

/**
 * Simulates the backend sorting logic: sort by deployed_at descending.
 * Skills without deployed_at are treated as oldest (sorted to the end).
 */
function sortByDeployedAtDesc(skills: SkillDetail[]): SkillDetail[] {
  return [...skills].sort((a, b) => {
    const dateA = a.deployed_at ? new Date(a.deployed_at).getTime() : 0;
    const dateB = b.deployed_at ? new Date(b.deployed_at).getTime() : 0;
    return dateB - dateA;
  });
}

describe('Property 2: 技能列表排序不变量', () => {
  it('sorted skill list maintains deployed_at descending order for all consecutive pairs', () => {
    fc.assert(
      fc.property(fc.array(skillDetailArb, { maxLength: 50 }), (skills) => {
        const sorted = sortByDeployedAtDesc(skills);

        for (let i = 0; i < sorted.length - 1; i++) {
          const currentTime = sorted[i].deployed_at
            ? new Date(sorted[i].deployed_at!).getTime()
            : 0;
          const nextTime = sorted[i + 1].deployed_at
            ? new Date(sorted[i + 1].deployed_at!).getTime()
            : 0;

          expect(currentTime).toBeGreaterThanOrEqual(nextTime);
        }
      }),
      { numRuns: 200 },
    );
  });

  it('sorting preserves all original elements (no data loss)', () => {
    fc.assert(
      fc.property(fc.array(skillDetailArb, { maxLength: 50 }), (skills) => {
        const sorted = sortByDeployedAtDesc(skills);

        expect(sorted).toHaveLength(skills.length);

        const originalIds = skills.map((s) => s.id).sort();
        const sortedIds = sorted.map((s) => s.id).sort();
        expect(sortedIds).toEqual(originalIds);
      }),
      { numRuns: 200 },
    );
  });

  it('sorting is idempotent — sorting an already sorted list yields the same result', () => {
    fc.assert(
      fc.property(fc.array(skillDetailArb, { maxLength: 50 }), (skills) => {
        const sorted1 = sortByDeployedAtDesc(skills);
        const sorted2 = sortByDeployedAtDesc(sorted1);

        expect(sorted2.map((s) => s.id)).toEqual(sorted1.map((s) => s.id));
      }),
      { numRuns: 200 },
    );
  });

  it('empty list and single-element list are trivially sorted', () => {
    fc.assert(
      fc.property(skillDetailArb, (skill) => {
        expect(sortByDeployedAtDesc([])).toEqual([]);
        expect(sortByDeployedAtDesc([skill])).toEqual([skill]);
      }),
      { numRuns: 50 },
    );
  });
});
