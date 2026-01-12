/**
 * Enhanced API Types
 * 
 * Strict type definitions for API requests and responses.
 * These types ensure type safety for all API interactions.
 */

import type { AxiosRequestConfig, AxiosResponse } from 'axios';

// ============================================================================
// HTTP Method Types
// ============================================================================

/** HTTP methods */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** HTTP status codes */
export type HttpStatusCode = 
  | 200 | 201 | 204  // Success
  | 400 | 401 | 403 | 404 | 409 | 422 | 429  // Client errors
  | 500 | 502 | 503 | 504;  // Server errors

/** Success status codes */
export type SuccessStatusCode = 200 | 201 | 204;

/** Client error status codes */
export type ClientErrorStatusCode = 400 | 401 | 403 | 404 | 409 | 422 | 429;

/** Server error status codes */
export type ServerErrorStatusCode = 500 | 502 | 503 | 504;

// ============================================================================
// Request Types
// ============================================================================

/** Base request config */
export interface ApiRequestConfig<TParams = unknown, TData = unknown> extends Omit<AxiosRequestConfig, 'params' | 'data'> {
  /** URL parameters */
  params?: TParams;
  /** Request body data */
  data?: TData;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Whether to use cache */
  useCache?: boolean;
  /** Cache TTL in milliseconds */
  cacheTtl?: number;
  /** Retry count */
  retryCount?: number;
  /** Retry delay in milliseconds */
  retryDelay?: number;
}

/** GET request config */
export interface GetRequestConfig<TParams = unknown> extends ApiRequestConfig<TParams, never> {
  method?: 'GET';
}

/** POST request config */
export interface PostRequestConfig<TData = unknown> extends ApiRequestConfig<never, TData> {
  method?: 'POST';
}

/** PUT request config */
export interface PutRequestConfig<TData = unknown> extends ApiRequestConfig<never, TData> {
  method?: 'PUT';
}

/** PATCH request config */
export interface PatchRequestConfig<TData = unknown> extends ApiRequestConfig<never, TData> {
  method?: 'PATCH';
}

/** DELETE request config */
export interface DeleteRequestConfig extends ApiRequestConfig<never, never> {
  method?: 'DELETE';
}

// ============================================================================
// Response Types
// ============================================================================

/** Base API response */
export interface ApiResponseBase<T = unknown> {
  /** Response data */
  data: T;
  /** Success flag */
  success: boolean;
  /** Response message */
  message?: string;
  /** Response timestamp */
  timestamp?: string;
  /** Request ID for tracking */
  requestId?: string;
}

/** Success response */
export interface ApiSuccessResponse<T = unknown> extends ApiResponseBase<T> {
  success: true;
  error?: never;
}

/** Error response */
export interface ApiErrorResponse extends ApiResponseBase<null> {
  success: false;
  data: null;
  /** Error details */
  error: {
    /** Error code */
    code: string;
    /** Error message */
    message: string;
    /** Field-level errors */
    fields?: Record<string, string[]>;
    /** Stack trace (development only) */
    stack?: string;
  };
}

/** Union type for API response */
export type ApiResult<T = unknown> = ApiSuccessResponse<T> | ApiErrorResponse;

/** Paginated response */
export interface PaginatedApiResponse<T = unknown> extends ApiSuccessResponse<T[]> {
  /** Pagination metadata */
  pagination: {
    /** Current page number */
    page: number;
    /** Items per page */
    pageSize: number;
    /** Total number of items */
    total: number;
    /** Total number of pages */
    totalPages: number;
    /** Has next page */
    hasNext: boolean;
    /** Has previous page */
    hasPrevious: boolean;
  };
}

/** List response with optional pagination */
export interface ListApiResponse<T = unknown> extends ApiSuccessResponse<T[]> {
  /** Total count */
  total: number;
  /** Pagination info (if paginated) */
  pagination?: PaginatedApiResponse<T>['pagination'];
}

// ============================================================================
// Request Parameter Types
// ============================================================================

/** Base pagination parameters */
export interface PaginationParams {
  /** Page number (1-indexed) */
  page?: number;
  /** Items per page */
  pageSize?: number;
  /** Alias for pageSize */
  page_size?: number;
  /** Limit (alias for pageSize) */
  limit?: number;
  /** Offset (alternative to page) */
  offset?: number;
}

/** Sort parameters */
export interface SortParams {
  /** Sort field */
  sortBy?: string;
  /** Alias for sortBy */
  sort_by?: string;
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
  /** Alias for sortOrder */
  sort_order?: 'asc' | 'desc';
  /** Combined sort string (e.g., '-created_at') */
  sort?: string;
}

/** Search parameters */
export interface SearchParams {
  /** Search query */
  search?: string;
  /** Search query alias */
  q?: string;
  /** Search fields */
  searchFields?: string[];
}

/** Filter parameters */
export interface FilterParams {
  /** Generic filters */
  filters?: Record<string, unknown>;
  /** Date range start */
  startDate?: string;
  /** Date range end */
  endDate?: string;
  /** Alias for startDate */
  start_date?: string;
  /** Alias for endDate */
  end_date?: string;
}

/** Combined list parameters */
export interface ListParams extends PaginationParams, SortParams, SearchParams, FilterParams {
  /** Include related data */
  include?: string[];
  /** Exclude fields */
  exclude?: string[];
  /** Select specific fields */
  fields?: string[];
}

// ============================================================================
// Typed API Client Interface
// ============================================================================

/** Typed API client interface */
export interface TypedApiClient {
  /** GET request */
  get<TResponse, TParams = unknown>(
    url: string,
    config?: GetRequestConfig<TParams>
  ): Promise<AxiosResponse<TResponse>>;

  /** POST request */
  post<TResponse, TData = unknown>(
    url: string,
    data?: TData,
    config?: PostRequestConfig<TData>
  ): Promise<AxiosResponse<TResponse>>;

  /** PUT request */
  put<TResponse, TData = unknown>(
    url: string,
    data?: TData,
    config?: PutRequestConfig<TData>
  ): Promise<AxiosResponse<TResponse>>;

  /** PATCH request */
  patch<TResponse, TData = unknown>(
    url: string,
    data?: TData,
    config?: PatchRequestConfig<TData>
  ): Promise<AxiosResponse<TResponse>>;

  /** DELETE request */
  delete<TResponse>(
    url: string,
    config?: DeleteRequestConfig
  ): Promise<AxiosResponse<TResponse>>;
}

// ============================================================================
// API Endpoint Types
// ============================================================================

/** API endpoint definition */
export interface ApiEndpoint<
  TResponse = unknown,
  TParams = unknown,
  TData = unknown
> {
  /** Endpoint URL or URL builder */
  url: string | ((...args: string[]) => string);
  /** HTTP method */
  method: HttpMethod;
  /** Response type (for documentation) */
  responseType?: TResponse;
  /** Parameters type (for documentation) */
  paramsType?: TParams;
  /** Request body type (for documentation) */
  dataType?: TData;
}

/** API endpoint group */
export interface ApiEndpointGroup {
  [key: string]: ApiEndpoint | string | ((...args: string[]) => string);
}

// ============================================================================
// Request/Response Transformers
// ============================================================================

/** Request transformer function */
export type RequestTransformer<TInput, TOutput> = (data: TInput) => TOutput;

/** Response transformer function */
export type ResponseTransformer<TInput, TOutput> = (data: TInput) => TOutput;

/** Transform snake_case to camelCase */
export const snakeToCamel = <T extends Record<string, unknown>>(obj: T): T => {
  const result: Record<string, unknown> = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      const value = obj[key];
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        result[camelKey] = snakeToCamel(value as Record<string, unknown>);
      } else if (Array.isArray(value)) {
        result[camelKey] = value.map(item => 
          item && typeof item === 'object' ? snakeToCamel(item as Record<string, unknown>) : item
        );
      } else {
        result[camelKey] = value;
      }
    }
  }
  return result as T;
};

/** Transform camelCase to snake_case */
export const camelToSnake = <T extends Record<string, unknown>>(obj: T): T => {
  const result: Record<string, unknown> = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
      const value = obj[key];
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        result[snakeKey] = camelToSnake(value as Record<string, unknown>);
      } else if (Array.isArray(value)) {
        result[snakeKey] = value.map(item => 
          item && typeof item === 'object' ? camelToSnake(item as Record<string, unknown>) : item
        );
      } else {
        result[snakeKey] = value;
      }
    }
  }
  return result as T;
};

// ============================================================================
// Error Types
// ============================================================================

/** API error class */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: HttpStatusCode,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** Check if error is a client error */
  isClientError(): boolean {
    return this.statusCode >= 400 && this.statusCode < 500;
  }

  /** Check if error is a server error */
  isServerError(): boolean {
    return this.statusCode >= 500;
  }

  /** Check if error is an authentication error */
  isAuthError(): boolean {
    return this.statusCode === 401;
  }

  /** Check if error is a permission error */
  isPermissionError(): boolean {
    return this.statusCode === 403;
  }

  /** Check if error is a not found error */
  isNotFoundError(): boolean {
    return this.statusCode === 404;
  }

  /** Check if error is a validation error */
  isValidationError(): boolean {
    return this.statusCode === 400 || this.statusCode === 422;
  }

  /** Check if error is a rate limit error */
  isRateLimitError(): boolean {
    return this.statusCode === 429;
  }

  /** Convert to JSON */
  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      statusCode: this.statusCode,
      details: this.details,
    };
  }
}

/** Validation error class */
export class ValidationError extends ApiError {
  constructor(
    message: string,
    public readonly fieldErrors: Record<string, string[]>
  ) {
    super(message, 'VALIDATION_ERROR', 422, { fieldErrors });
    this.name = 'ValidationError';
  }

  /** Get errors for a specific field */
  getFieldErrors(field: string): string[] {
    return this.fieldErrors[field] || [];
  }

  /** Check if a field has errors */
  hasFieldError(field: string): boolean {
    return field in this.fieldErrors && this.fieldErrors[field].length > 0;
  }

  /** Get all field names with errors */
  getErrorFields(): string[] {
    return Object.keys(this.fieldErrors);
  }
}

/** Network error class */
export class NetworkError extends ApiError {
  constructor(message: string = 'Network error occurred') {
    super(message, 'NETWORK_ERROR', 500);
    this.name = 'NetworkError';
  }
}

/** Timeout error class */
export class TimeoutError extends ApiError {
  constructor(message: string = 'Request timed out') {
    super(message, 'TIMEOUT_ERROR', 504);
    this.name = 'TimeoutError';
  }
}

// ============================================================================
// Type Helpers
// ============================================================================

/** Extract response type from API endpoint */
export type ExtractResponse<T> = T extends ApiEndpoint<infer R, unknown, unknown> ? R : never;

/** Extract params type from API endpoint */
export type ExtractParams<T> = T extends ApiEndpoint<unknown, infer P, unknown> ? P : never;

/** Extract data type from API endpoint */
export type ExtractData<T> = T extends ApiEndpoint<unknown, unknown, infer D> ? D : never;

/** Make all properties of T optional except for K */
export type PartialExcept<T, K extends keyof T> = Partial<Omit<T, K>> & Pick<T, K>;

/** Make all properties of T required except for K */
export type RequiredExcept<T, K extends keyof T> = Required<Omit<T, K>> & Partial<Pick<T, K>>;

/** Create a type for creating a new entity (without id and timestamps) */
export type CreatePayload<T> = Omit<T, 'id' | 'created_at' | 'updated_at' | 'createdAt' | 'updatedAt'>;

/** Create a type for updating an entity (all fields optional except id) */
export type UpdatePayload<T> = Partial<Omit<T, 'id' | 'created_at' | 'updated_at' | 'createdAt' | 'updatedAt'>>;

/** Create a type for entity with required id */
export type WithId<T> = T & { id: string };

/** Create a type for entity with timestamps */
export type WithTimestamps<T> = T & {
  created_at: string;
  updated_at: string;
};
