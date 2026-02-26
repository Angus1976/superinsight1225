/**
 * AI 标注执行增强 — 纯工具函数
 *
 * 所有函数均为纯函数，无副作用。
 */
import type {
  DesensitizationRule,
  AuditLogEntry,
  AuditFilter,
} from '@/services/aiAnnotationApi'

// ─── 1. clampSampleSize ────────────────────────────────────────────
/** 将试算样本数约束到 [10, 100] 区间 */
export function clampSampleSize(n: number): number {
  if (!Number.isFinite(n)) return 10
  return Math.min(100, Math.max(10, Math.round(n)))
}

// ─── 2. checkBatchQuality ──────────────────────────────────────────
/** 当准确率低于阈值时返回 shouldPause = true */
export function checkBatchQuality(
  accuracy: number,
  threshold: number,
): { shouldPause: boolean } {
  return { shouldPause: accuracy < threshold }
}

// ─── 3. calculateEstimatedTime ─────────────────────────────────────
/** 计算预估完成时间（分钟）。速率 ≤ 0 时返回 Infinity */
export function calculateEstimatedTime(
  remaining: number,
  ratePerMinute: number,
): number {
  if (ratePerMinute <= 0) return Infinity
  return remaining / ratePerMinute
}

// ─── 4. sortByPriority ────────────────────────────────────────────
/**
 * 按 priority 降序稳定排序。
 * 高优先级在前，相同优先级保持原始顺序。
 */
export function sortByPriority<T extends { priority: number }>(
  items: T[],
): T[] {
  // Array.prototype.sort 在现代引擎中是稳定排序（ES2019 规范要求）
  // 为确保跨环境稳定性，使用索引作为二级排序键
  const indexed = items.map((item, i) => ({ item, index: i }))
  indexed.sort((a, b) => {
    const diff = b.item.priority - a.item.priority
    return diff !== 0 ? diff : a.index - b.index
  })
  return indexed.map((entry) => entry.item)
}

// ─── 5. applyDesensitizationRule ───────────────────────────────────
/**
 * 根据脱敏规则对输入字符串进行脱敏处理。
 * 规则未启用时原样返回。
 */
export function applyDesensitizationRule(
  input: string,
  rule: DesensitizationRule,
): string {
  if (!rule.enabled) return input

  switch (rule.type) {
    case 'phone':
      // 匹配中国手机号格式：1xx-xxxx-xxxx 或连续 11 位
      return input.replace(
        /(1\d{2})\d{4}(\d{4})/g,
        `$1${rule.replacement}$2`,
      )

    case 'email':
      // 将邮箱 local 部分替换
      return input.replace(
        /[a-zA-Z0-9._%+-]+(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
        `${rule.replacement}$1`,
      )

    case 'name':
      // 匹配 2-4 个中文字符组成的姓名
      return input.replace(/[\u4e00-\u9fa5]{2,4}/g, rule.replacement)

    case 'address':
      // 匹配包含省/市/区/县/街/路/号/栋/楼等地址关键词的片段
      return input.replace(
        /[\u4e00-\u9fa5]*(省|市|区|县|街|路|道|号|栋|楼|村|镇|乡)[\u4e00-\u9fa5\d]*/g,
        rule.replacement,
      )

    case 'regex':
      if (!rule.pattern) return input
      return input.replace(new RegExp(rule.pattern, 'g'), rule.replacement)

    default:
      return input
  }
}

// ─── 6. filterAuditLogs ───────────────────────────────────────────
/** 按日期范围和操作人筛选审计日志 */
export function filterAuditLogs(
  logs: AuditLogEntry[],
  filter: AuditFilter,
): AuditLogEntry[] {
  return logs.filter((log) => {
    if (filter.dateRange) {
      const ts = log.timestamp
      if (ts < filter.dateRange[0] || ts > filter.dateRange[1]) return false
    }
    if (filter.operator && log.operator !== filter.operator) return false
    return true
  })
}

// ─── 7. desensitizeAndMapBack ─────────────────────────────────────
/**
 * 脱敏标注映射往返。
 *
 * 1. 对数据记录的敏感字段应用脱敏规则，生成脱敏副本并保留 id 映射
 * 2. 模拟标注后，通过映射将标注结果关联回原始 id
 *
 * 核心不变量：mapBack(desensitize(data)).id === data.id
 */
export interface DataRecord {
  id: string
  [key: string]: string
}

export interface DesensitizedRecord {
  maskedId: string
  originalId: string
  fields: Record<string, string>
}

export function desensitizeRecords(
  records: DataRecord[],
  sensitiveFields: string[],
  rules: DesensitizationRule[],
): DesensitizedRecord[] {
  return records.map((record, index) => {
    const maskedId = `masked_${index}`
    const fields: Record<string, string> = {}

    for (const key of Object.keys(record)) {
      if (key === 'id') continue
      if (sensitiveFields.includes(key)) {
        let value = record[key]
        for (const rule of rules) {
          value = applyDesensitizationRule(value, rule)
        }
        fields[key] = value
      } else {
        fields[key] = record[key]
      }
    }

    return { maskedId, originalId: record.id, fields }
  })
}

export function mapBackToOriginalIds(
  desensitized: DesensitizedRecord[],
): { id: string; fields: Record<string, string> }[] {
  return desensitized.map((d) => ({
    id: d.originalId,
    fields: d.fields,
  }))
}
