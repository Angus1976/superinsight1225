/**
 * Code Quality Utilities
 * 
 * This module provides utilities for maintaining code quality, including:
 * - Type guards for runtime type checking
 * - Assertion functions for invariant checking
 * - Utility types for better type safety
 * - Validation helpers for data integrity
 * 
 * @module utils/codeQuality
 * @version 1.0.0
 */

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Type guard to check if a value is defined (not null or undefined)
 * @param value - The value to check
 * @returns True if the value is defined
 * @example
 * ```typescript
 * const value: string | null = getValue();
 * if (isDefined(value)) {
 *   // value is now typed as string
 *   console.log(value.toUpperCase());
 * }
 * ```
 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * Type guard to check if a value is a non-empty string
 * @param value - The value to check
 * @returns True if the value is a non-empty string
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Type guard to check if a value is a valid number (not NaN)
 * @param value - The value to check
 * @returns True if the value is a valid number
 */
export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && !Number.isNaN(value) && Number.isFinite(value);
}

/**
 * Type guard to check if a value is a non-empty array
 * @param value - The value to check
 * @returns True if the value is a non-empty array
 */
export function isNonEmptyArray<T>(value: unknown): value is T[] {
  return Array.isArray(value) && value.length > 0;
}

/**
 * Type guard to check if a value is a plain object
 * @param value - The value to check
 * @returns True if the value is a plain object
 */
export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Type guard to check if a value is a function
 * @param value - The value to check
 * @returns True if the value is a function
 */
export function isFunction(value: unknown): value is (...args: unknown[]) => unknown {
  return typeof value === 'function';
}

/**
 * Type guard to check if a value is a valid Date
 * @param value - The value to check
 * @returns True if the value is a valid Date
 */
export function isValidDate(value: unknown): value is Date {
  return value instanceof Date && !Number.isNaN(value.getTime());
}

// ============================================================================
// Assertion Functions
// ============================================================================

/**
 * Asserts that a condition is true, throwing an error if not
 * @param condition - The condition to check
 * @param message - The error message if the assertion fails
 * @throws Error if the condition is false
 * @example
 * ```typescript
 * assert(user.id > 0, 'User ID must be positive');
 * ```
 */
export function assert(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

/**
 * Asserts that a value is defined (not null or undefined)
 * @param value - The value to check
 * @param message - The error message if the assertion fails
 * @throws Error if the value is null or undefined
 */
export function assertDefined<T>(
  value: T | null | undefined,
  message = 'Value is null or undefined'
): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

/**
 * Asserts that a value is never reached (for exhaustive type checking)
 * @param value - The value that should never be reached
 * @param message - Optional error message
 * @throws Error always
 * @example
 * ```typescript
 * type Status = 'active' | 'inactive';
 * function handleStatus(status: Status) {
 *   switch (status) {
 *     case 'active': return 'Active';
 *     case 'inactive': return 'Inactive';
 *     default: assertNever(status);
 *   }
 * }
 * ```
 */
export function assertNever(value: never, message?: string): never {
  throw new Error(message || `Unexpected value: ${JSON.stringify(value)}`);
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Makes all properties of T required and non-nullable
 */
export type RequiredNonNullable<T> = {
  [P in keyof T]-?: NonNullable<T[P]>;
};

/**
 * Makes specified keys K of T required
 */
export type RequireKeys<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Makes specified keys K of T optional
 */
export type OptionalKeys<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/**
 * Extracts the type of array elements
 */
export type ArrayElement<T> = T extends readonly (infer E)[] ? E : never;

/**
 * Creates a type with all properties of T set to readonly
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * Creates a type with all properties of T set to mutable
 */
export type Mutable<T> = {
  -readonly [P in keyof T]: T[P];
};

/**
 * Extracts the resolved type of a Promise
 */
export type Awaited<T> = T extends Promise<infer U> ? U : T;

/**
 * Creates a branded type for nominal typing
 * @example
 * ```typescript
 * type UserId = Brand<number, 'UserId'>;
 * type OrderId = Brand<number, 'OrderId'>;
 * 
 * const userId: UserId = 1 as UserId;
 * const orderId: OrderId = 1 as OrderId;
 * // userId !== orderId (type error)
 * ```
 */
export type Brand<T, B> = T & { __brand: B };

// ============================================================================
// Validation Helpers
// ============================================================================

/**
 * Result type for validation operations
 */
export type ValidationResult<T> = 
  | { success: true; data: T }
  | { success: false; errors: string[] };

/**
 * Creates a successful validation result
 * @param data - The validated data
 * @returns A successful validation result
 */
export function validationSuccess<T>(data: T): ValidationResult<T> {
  return { success: true, data };
}

/**
 * Creates a failed validation result
 * @param errors - The validation errors
 * @returns A failed validation result
 */
export function validationFailure<T>(errors: string[]): ValidationResult<T> {
  return { success: false, errors };
}

/**
 * Validates an email address format
 * @param email - The email to validate
 * @returns True if the email format is valid
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validates a URL format
 * @param url - The URL to validate
 * @returns True if the URL format is valid
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validates that a string matches a minimum length
 * @param value - The string to validate
 * @param minLength - The minimum length
 * @returns True if the string meets the minimum length
 */
export function hasMinLength(value: string, minLength: number): boolean {
  return value.length >= minLength;
}

/**
 * Validates that a string matches a maximum length
 * @param value - The string to validate
 * @param maxLength - The maximum length
 * @returns True if the string meets the maximum length
 */
export function hasMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength;
}

/**
 * Validates that a number is within a range
 * @param value - The number to validate
 * @param min - The minimum value (inclusive)
 * @param max - The maximum value (inclusive)
 * @returns True if the number is within the range
 */
export function isInRange(value: number, min: number, max: number): boolean {
  return value >= min && value <= max;
}

// ============================================================================
// Safe Operations
// ============================================================================

/**
 * Safely parses JSON with error handling
 * @param json - The JSON string to parse
 * @returns The parsed object or null if parsing fails
 */
export function safeJsonParse<T>(json: string): T | null {
  try {
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

/**
 * Safely stringifies an object to JSON
 * @param value - The value to stringify
 * @param space - Optional indentation
 * @returns The JSON string or null if stringification fails
 */
export function safeJsonStringify(value: unknown, space?: number): string | null {
  try {
    return JSON.stringify(value, null, space);
  } catch {
    return null;
  }
}

/**
 * Safely accesses a nested property using a path
 * @param obj - The object to access
 * @param path - The property path (e.g., 'user.profile.name')
 * @returns The value at the path or undefined
 */
export function safeGet<T>(obj: unknown, path: string): T | undefined {
  const keys = path.split('.');
  let current: unknown = obj;
  
  for (const key of keys) {
    if (current === null || current === undefined) {
      return undefined;
    }
    current = (current as Record<string, unknown>)[key];
  }
  
  return current as T | undefined;
}

/**
 * Creates a debounced version of a function
 * @param fn - The function to debounce
 * @param delay - The debounce delay in milliseconds
 * @returns The debounced function
 */
export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Creates a throttled version of a function
 * @param fn - The function to throttle
 * @param limit - The throttle limit in milliseconds
 * @returns The throttled function
 */
export function throttle<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Retries an async operation with exponential backoff
 * @param operation - The async operation to retry
 * @param maxRetries - Maximum number of retries
 * @param baseDelay - Base delay in milliseconds
 * @returns The result of the operation
 * @throws The last error if all retries fail
 */
export async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  let lastError: Error | undefined;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}

// ============================================================================
// Object Utilities
// ============================================================================

/**
 * Creates a shallow clone of an object with specified keys omitted
 * @param obj - The source object
 * @param keys - The keys to omit
 * @returns A new object without the specified keys
 */
export function omit<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

/**
 * Creates a shallow clone of an object with only specified keys
 * @param obj - The source object
 * @param keys - The keys to pick
 * @returns A new object with only the specified keys
 */
export function pick<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}

/**
 * Deep merges two objects
 * @param target - The target object
 * @param source - The source object
 * @returns The merged object
 */
export function deepMerge<T extends Record<string, unknown>>(
  target: T,
  source: Partial<T>
): T {
  const result = { ...target };
  
  for (const key in source) {
    const sourceValue = source[key];
    const targetValue = result[key];
    
    if (isPlainObject(sourceValue) && isPlainObject(targetValue)) {
      result[key] = deepMerge(
        targetValue as Record<string, unknown>,
        sourceValue as Record<string, unknown>
      ) as T[Extract<keyof T, string>];
    } else if (sourceValue !== undefined) {
      result[key] = sourceValue as T[Extract<keyof T, string>];
    }
  }
  
  return result;
}

/**
 * Checks if two values are deeply equal
 * @param a - First value
 * @param b - Second value
 * @returns True if the values are deeply equal
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  
  if (typeof a !== typeof b) return false;
  
  if (a === null || b === null) return a === b;
  
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, index) => deepEqual(item, b[index]));
  }
  
  if (isPlainObject(a) && isPlainObject(b)) {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    
    if (keysA.length !== keysB.length) return false;
    
    return keysA.every(key => deepEqual(a[key], b[key]));
  }
  
  return false;
}
