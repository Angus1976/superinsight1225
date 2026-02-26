import { describe, it, expect } from 'vitest'
import {
  clampSampleSize,
  checkBatchQuality,
  calculateEstimatedTime,
  sortByPriority,
  applyDesensitizationRule,
  filterAuditLogs,
} from './annotationHelpers'
import type {
  DesensitizationRule,
  AuditLogEntry,
  AuditFilter,
} from '@/services/aiAnnotationApi'

// ─── clampSampleSize ───────────────────────────────────────────────
describe('clampSampleSize', () => {
  it('clamps values below 10 to 10', () => {
    expect(clampSampleSize(0)).toBe(10)
    expect(clampSampleSize(-5)).toBe(10)
    expect(clampSampleSize(1)).toBe(10)
  })

  it('clamps values above 100 to 100', () => {
    expect(clampSampleSize(200)).toBe(100)
    expect(clampSampleSize(101)).toBe(100)
  })

  it('keeps values within [10, 100]', () => {
    expect(clampSampleSize(50)).toBe(50)
    expect(clampSampleSize(10)).toBe(10)
    expect(clampSampleSize(100)).toBe(100)
  })

  it('handles NaN and Infinity as invalid input (defensive)', () => {
    expect(clampSampleSize(NaN)).toBe(10)
    expect(clampSampleSize(Infinity)).toBe(10)
    expect(clampSampleSize(-Infinity)).toBe(10)
  })
})

// ─── checkBatchQuality ─────────────────────────────────────────────
describe('checkBatchQuality', () => {
  it('returns shouldPause=true when accuracy < threshold', () => {
    expect(checkBatchQuality(0.7, 0.8)).toEqual({ shouldPause: true })
  })

  it('returns shouldPause=false when accuracy >= threshold', () => {
    expect(checkBatchQuality(0.8, 0.8)).toEqual({ shouldPause: false })
    expect(checkBatchQuality(0.9, 0.8)).toEqual({ shouldPause: false })
  })
})

// ─── calculateEstimatedTime ────────────────────────────────────────
describe('calculateEstimatedTime', () => {
  it('calculates remaining / ratePerMinute', () => {
    expect(calculateEstimatedTime(100, 10)).toBe(10)
    expect(calculateEstimatedTime(50, 25)).toBe(2)
  })

  it('returns Infinity when ratePerMinute <= 0', () => {
    expect(calculateEstimatedTime(100, 0)).toBe(Infinity)
    expect(calculateEstimatedTime(100, -5)).toBe(Infinity)
  })
})

// ─── sortByPriority ───────────────────────────────────────────────
describe('sortByPriority', () => {
  it('sorts by priority descending', () => {
    const items = [
      { id: 'a', priority: 1 },
      { id: 'b', priority: 3 },
      { id: 'c', priority: 2 },
    ]
    const sorted = sortByPriority(items)
    expect(sorted.map((i) => i.id)).toEqual(['b', 'c', 'a'])
  })

  it('preserves original order for same priority (stable)', () => {
    const items = [
      { id: 'x', priority: 5 },
      { id: 'y', priority: 5 },
      { id: 'z', priority: 5 },
    ]
    const sorted = sortByPriority(items)
    expect(sorted.map((i) => i.id)).toEqual(['x', 'y', 'z'])
  })

  it('returns empty array for empty input', () => {
    expect(sortByPriority([])).toEqual([])
  })

  it('does not mutate the original array', () => {
    const items = [{ priority: 2 }, { priority: 1 }]
    const copy = [...items]
    sortByPriority(items)
    expect(items).toEqual(copy)
  })
})

// ─── applyDesensitizationRule ─────────────────────────────────────
describe('applyDesensitizationRule', () => {
  it('returns input unchanged when rule is disabled', () => {
    const rule: DesensitizationRule = {
      id: '1', type: 'phone', replacement: '****', enabled: false,
    }
    expect(applyDesensitizationRule('13812345678', rule)).toBe('13812345678')
  })

  it('masks phone numbers', () => {
    const rule: DesensitizationRule = {
      id: '1', type: 'phone', replacement: '****', enabled: true,
    }
    const result = applyDesensitizationRule('联系电话 13812345678', rule)
    expect(result).toBe('联系电话 138****5678')
    expect(result).not.toContain('1234')
  })

  it('masks email local part', () => {
    const rule: DesensitizationRule = {
      id: '2', type: 'email', replacement: '***', enabled: true,
    }
    const result = applyDesensitizationRule('邮箱 test@example.com', rule)
    expect(result).toBe('邮箱 ***@example.com')
    expect(result).not.toContain('test@')
  })

  it('masks Chinese names', () => {
    const rule: DesensitizationRule = {
      id: '3', type: 'name', replacement: '**', enabled: true,
    }
    const result = applyDesensitizationRule('姓名：张三', rule)
    expect(result).toContain('**')
  })

  it('masks address content', () => {
    const rule: DesensitizationRule = {
      id: '4', type: 'address', replacement: '[地址已隐藏]', enabled: true,
    }
    const result = applyDesensitizationRule('地址：北京市朝阳区', rule)
    expect(result).toContain('[地址已隐藏]')
  })

  it('applies custom regex', () => {
    const rule: DesensitizationRule = {
      id: '5', type: 'regex', pattern: '\\d{6}', replacement: '******', enabled: true,
    }
    expect(applyDesensitizationRule('身份证 110101', rule)).toBe('身份证 ******')
  })

  it('returns input when regex rule has no pattern', () => {
    const rule: DesensitizationRule = {
      id: '6', type: 'regex', replacement: '***', enabled: true,
    }
    expect(applyDesensitizationRule('hello', rule)).toBe('hello')
  })
})

// ─── filterAuditLogs ──────────────────────────────────────────────
describe('filterAuditLogs', () => {
  const logs: AuditLogEntry[] = [
    { id: '1', operator: 'alice', timestamp: '2024-01-15', rules: [], affectedCount: 10, taskId: 't1' },
    { id: '2', operator: 'bob', timestamp: '2024-02-20', rules: [], affectedCount: 5, taskId: 't2' },
    { id: '3', operator: 'alice', timestamp: '2024-03-10', rules: [], affectedCount: 8, taskId: 't3' },
  ]

  it('filters by operator', () => {
    const result = filterAuditLogs(logs, { operator: 'alice' })
    expect(result).toHaveLength(2)
    expect(result.every((l) => l.operator === 'alice')).toBe(true)
  })

  it('filters by dateRange', () => {
    const filter: AuditFilter = { dateRange: ['2024-01-01', '2024-02-28'] }
    const result = filterAuditLogs(logs, filter)
    expect(result).toHaveLength(2)
    expect(result.map((l) => l.id)).toEqual(['1', '2'])
  })

  it('filters by both operator and dateRange', () => {
    const filter: AuditFilter = { dateRange: ['2024-01-01', '2024-02-28'], operator: 'alice' }
    const result = filterAuditLogs(logs, filter)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('1')
  })

  it('returns all logs when filter is empty', () => {
    expect(filterAuditLogs(logs, {})).toHaveLength(3)
  })
})
