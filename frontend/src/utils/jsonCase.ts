/**
 * 将典型 FastAPI/Pydantic JSON（snake_case 键）与前端 TS/React（camelCase）互转。
 * 仅处理纯 JSON 结构：plain object、数组、原始值；跳过 Date 等非 JSON 类型。
 */

function isPlainObject(v: unknown): v is Record<string, unknown> {
  if (v === null || typeof v !== 'object') return false;
  if (Array.isArray(v)) return false;
  const proto = Object.getPrototypeOf(v);
  return proto === Object.prototype || proto === null;
}

function toCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function toSnakeKey(key: string): string {
  if (key.includes('_')) return key;
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1_$2')
    .toLowerCase();
}

export function keysToCamelDeep(input: unknown): unknown {
  if (input instanceof Date) return input;
  if (Array.isArray(input)) {
    return input.map((item) => keysToCamelDeep(item));
  }
  if (isPlainObject(input)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(input)) {
      out[toCamelKey(k)] = keysToCamelDeep(v);
    }
    return out;
  }
  return input;
}

/**
 * 将 JSON 规范为 snake_case（与 FastAPI 默认及本仓库 admin/multi-tenant 的 TS 类型一致）。
 * 读取侧可兼容返回 camelCase 的后端；写入侧可兼容表单传入的 camelCase。
 */
export function keysToSnakeDeep(input: unknown): unknown {
  if (input instanceof Date) return input;
  if (Array.isArray(input)) {
    return input.map((item) => keysToSnakeDeep(item));
  }
  if (isPlainObject(input)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(input)) {
      out[toSnakeKey(k)] = keysToSnakeDeep(v);
    }
    return out;
  }
  return input;
}

/** 列表或 { items: [] } 分页中的项转为 { id, name }，键名先 camelCase 再取值 */
/**
 * HTTP JSON 响应：统一为 snake_case，兼容后端或网关返回 camelCase。
 * 跳过 Blob / ArrayBuffer（文件下载等）。
 */
export function apiResponseToSnake<T = unknown>(data: unknown): T {
  if (data === null || data === undefined) return data as T;
  if (typeof Blob !== 'undefined' && data instanceof Blob) return data as T;
  if (data instanceof ArrayBuffer) return data as T;
  return keysToSnakeDeep(data) as T;
}

/** HTTP JSON 请求体：转为 snake_case，兼容表单 camelCase。 */
export function apiRequestToSnake(data: unknown): unknown {
  return keysToSnakeDeep(data);
}

/** `fetch` 的 JSON body：`JSON.stringify(apiRequestToSnake(payload))`。 */
export function fetchJsonBody(payload: unknown): string {
  return JSON.stringify(apiRequestToSnake(payload));
}

/** `fetch` 读 JSON：`await response.json()` 后经 `apiResponseToSnake`（与 axios 响应一致）。 */
export async function fetchJsonResponseToSnake<T = unknown>(response: Response): Promise<T> {
  const raw: unknown = await response.json();
  return apiResponseToSnake<T>(raw);
}

/**
 * 解包常见 `{ data: payload }` / `ApiResponse<T>` 信封：内外各做一次 snake 规范化。
 */
export function unwrapApiEnvelope<T>(responseData: unknown): T {
  const outer = keysToSnakeDeep(responseData) as Record<string, unknown>;
  return keysToSnakeDeep(outer?.data) as T;
}

export function mapListToIdName(raw: unknown): { id: string; name: string }[] {
  if (raw === null || raw === undefined) return [];
  const arr = Array.isArray(raw)
    ? raw
    : isPlainObject(raw) && Array.isArray((raw as Record<string, unknown>).items)
      ? (raw as Record<string, unknown>).items
      : null;
  if (!Array.isArray(arr)) return [];
  return arr.map((d) => {
    const row = keysToCamelDeep(d) as Record<string, unknown>;
    const id = String(row.id ?? '');
    const name = String(row.name ?? row.title ?? id);
    return { id, name };
  });
}
