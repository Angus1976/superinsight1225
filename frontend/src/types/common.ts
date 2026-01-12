/**
 * Common Utility Types
 * 
 * Comprehensive type definitions for common patterns used throughout the application.
 * These types ensure type safety and provide better developer experience.
 */

// ============================================================================
// Primitive Type Utilities
// ============================================================================

/** Non-nullable type - removes null and undefined from T */
export type NonNullable<T> = T extends null | undefined ? never : T;

/** Make all properties of T required and non-nullable */
export type RequiredNonNullable<T> = {
  [P in keyof T]-?: NonNullable<T[P]>;
};

/** Make specific properties of T required */
export type RequireFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

/** Make specific properties of T optional */
export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/** Make all properties of T mutable (remove readonly) */
export type Mutable<T> = {
  -readonly [P in keyof T]: T[P];
};

/** Deep partial - makes all nested properties optional */
export type DeepPartial<T> = T extends object ? {
  [P in keyof T]?: DeepPartial<T[P]>;
} : T;

/** Deep required - makes all nested properties required */
export type DeepRequired<T> = T extends object ? {
  [P in keyof T]-?: DeepRequired<T[P]>;
} : T;

/** Deep readonly - makes all nested properties readonly */
export type DeepReadonly<T> = T extends object ? {
  readonly [P in keyof T]: DeepReadonly<T[P]>;
} : T;

// ============================================================================
// Object Type Utilities
// ============================================================================

/** Extract keys of T that have values of type V */
export type KeysOfType<T, V> = {
  [K in keyof T]: T[K] extends V ? K : never;
}[keyof T];

/** Extract keys of T that have values not of type V */
export type KeysNotOfType<T, V> = {
  [K in keyof T]: T[K] extends V ? never : K;
}[keyof T];

/** Pick properties of T that have values of type V */
export type PickByType<T, V> = Pick<T, KeysOfType<T, V>>;

/** Omit properties of T that have values of type V */
export type OmitByType<T, V> = Pick<T, KeysNotOfType<T, V>>;

/** Merge two types, with T2 taking precedence */
export type Merge<T1, T2> = Omit<T1, keyof T2> & T2;

/** Get the value type of an object */
export type ValueOf<T> = T[keyof T];

/** Get the keys of T as a union of string literals */
export type StringKeyOf<T> = Extract<keyof T, string>;

// ============================================================================
// Array Type Utilities
// ============================================================================

/** Get the element type of an array */
export type ArrayElement<T> = T extends readonly (infer E)[] ? E : never;

/** Ensure T is an array */
export type EnsureArray<T> = T extends unknown[] ? T : T[];

/** Non-empty array type */
export type NonEmptyArray<T> = [T, ...T[]];

/** Tuple type with at least N elements */
export type AtLeast<T, N extends number, R extends T[] = []> = 
  R['length'] extends N ? [...R, ...T[]] : AtLeast<T, N, [...R, T]>;

// ============================================================================
// Function Type Utilities
// ============================================================================

/** Extract the return type of an async function */
export type AsyncReturnType<T extends (...args: unknown[]) => Promise<unknown>> = 
  T extends (...args: unknown[]) => Promise<infer R> ? R : never;

/** Extract the parameters of a function as a tuple */
export type Parameters<T extends (...args: unknown[]) => unknown> = 
  T extends (...args: infer P) => unknown ? P : never;

/** Make a function's return type a Promise */
export type Promisify<T extends (...args: unknown[]) => unknown> = 
  (...args: Parameters<T>) => Promise<ReturnType<T>>;

/** Callback function type */
export type Callback<T = void> = (result: T) => void;

/** Error callback function type */
export type ErrorCallback = (error: Error) => void;

/** Generic handler function type */
export type Handler<TInput = void, TOutput = void> = (input: TInput) => TOutput;

/** Async handler function type */
export type AsyncHandler<TInput = void, TOutput = void> = (input: TInput) => Promise<TOutput>;

// ============================================================================
// React Component Type Utilities
// ============================================================================

import type { ReactNode, ComponentType, FC, PropsWithChildren } from 'react';

/** Props with optional children */
export type WithChildren<T = object> = T & { children?: ReactNode };

/** Props with required children */
export type WithRequiredChildren<T = object> = T & { children: ReactNode };

/** Component props with className */
export type WithClassName<T = object> = T & { className?: string };

/** Component props with style */
export type WithStyle<T = object> = T & { style?: React.CSSProperties };

/** Common component props (className + style) */
export type CommonProps<T = object> = WithClassName<WithStyle<T>>;

/** Component props with loading state */
export type WithLoading<T = object> = T & { loading?: boolean };

/** Component props with error state */
export type WithError<T = object> = T & { error?: string | Error | null };

/** Component props with disabled state */
export type WithDisabled<T = object> = T & { disabled?: boolean };

/** Component props with common states */
export type WithCommonStates<T = object> = WithLoading<WithError<WithDisabled<T>>>;

/** Extract props from a component type */
export type PropsOf<T extends ComponentType<unknown>> = 
  T extends ComponentType<infer P> ? P : never;

/** Render prop type */
export type RenderProp<TProps = object> = (props: TProps) => ReactNode;

// ============================================================================
// Event Handler Types
// ============================================================================

/** Generic event handler */
export type EventHandler<E = Event> = (event: E) => void;

/** Click event handler */
export type ClickHandler<T = HTMLElement> = React.MouseEventHandler<T>;

/** Change event handler */
export type ChangeHandler<T = HTMLInputElement> = React.ChangeEventHandler<T>;

/** Submit event handler */
export type SubmitHandler<T = HTMLFormElement> = React.FormEventHandler<T>;

/** Keyboard event handler */
export type KeyboardHandler<T = HTMLElement> = React.KeyboardEventHandler<T>;

/** Focus event handler */
export type FocusHandler<T = HTMLElement> = React.FocusEventHandler<T>;

// ============================================================================
// Data Types
// ============================================================================

/** ID type - can be string or number */
export type ID = string | number;

/** Timestamp type */
export type Timestamp = number | string | Date;

/** ISO date string type */
export type ISODateString = string;

/** UUID type (branded string for type safety) */
export type UUID = string & { readonly __brand: 'UUID' };

/** Email type (branded string for type safety) */
export type Email = string & { readonly __brand: 'Email' };

/** URL type (branded string for type safety) */
export type URLString = string & { readonly __brand: 'URL' };

/** JSON value type */
export type JSONValue = 
  | string 
  | number 
  | boolean 
  | null 
  | JSONValue[] 
  | { [key: string]: JSONValue };

/** JSON object type */
export type JSONObject = { [key: string]: JSONValue };

/** Record with string keys */
export type StringRecord<T> = Record<string, T>;

/** Record with number keys */
export type NumberRecord<T> = Record<number, T>;

// ============================================================================
// State Types
// ============================================================================

/** Loading state */
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

/** Async state wrapper */
export interface AsyncState<T, E = Error> {
  data: T | null;
  loading: boolean;
  error: E | null;
  status: LoadingState;
}

/** Create initial async state */
export const createInitialAsyncState = <T>(): AsyncState<T> => ({
  data: null,
  loading: false,
  error: null,
  status: 'idle',
});

/** Pagination state */
export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

/** Sort state */
export interface SortState<T = string> {
  field: T;
  order: 'asc' | 'desc';
}

/** Filter state */
export interface FilterState<T = Record<string, unknown>> {
  filters: T;
  activeFilters: (keyof T)[];
}

// ============================================================================
// Form Types
// ============================================================================

/** Form field state */
export interface FieldState<T = string> {
  value: T;
  error?: string;
  touched: boolean;
  dirty: boolean;
}

/** Form state */
export interface FormState<T extends Record<string, unknown>> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  dirty: boolean;
  valid: boolean;
  submitting: boolean;
}

/** Form field config */
export interface FieldConfig<T = string> {
  name: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  defaultValue?: T;
  validate?: (value: T) => string | undefined;
}

// ============================================================================
// Selection Types
// ============================================================================

/** Single selection state */
export interface SingleSelection<T = string> {
  selected: T | null;
  select: (item: T) => void;
  clear: () => void;
}

/** Multiple selection state */
export interface MultipleSelection<T = string> {
  selected: T[];
  select: (item: T) => void;
  deselect: (item: T) => void;
  toggle: (item: T) => void;
  selectAll: (items: T[]) => void;
  clear: () => void;
  isSelected: (item: T) => boolean;
}

// ============================================================================
// Theme Types
// ============================================================================

/** Theme mode */
export type ThemeMode = 'light' | 'dark' | 'system';

/** Color scheme */
export type ColorScheme = 'default' | 'blue' | 'green' | 'purple' | 'orange';

/** Size variants */
export type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

/** Spacing variants */
export type Spacing = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

/** Border radius variants */
export type BorderRadius = 'none' | 'sm' | 'md' | 'lg' | 'full';

// ============================================================================
// Utility Functions
// ============================================================================

/** Type guard for checking if value is defined */
export const isDefined = <T>(value: T | undefined | null): value is T => {
  return value !== undefined && value !== null;
};

/** Type guard for checking if value is a string */
export const isString = (value: unknown): value is string => {
  return typeof value === 'string';
};

/** Type guard for checking if value is a number */
export const isNumber = (value: unknown): value is number => {
  return typeof value === 'number' && !isNaN(value);
};

/** Type guard for checking if value is a boolean */
export const isBoolean = (value: unknown): value is boolean => {
  return typeof value === 'boolean';
};

/** Type guard for checking if value is an object */
export const isObject = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
};

/** Type guard for checking if value is an array */
export const isArray = <T>(value: unknown): value is T[] => {
  return Array.isArray(value);
};

/** Type guard for checking if value is a function */
export const isFunction = (value: unknown): value is Function => {
  return typeof value === 'function';
};

/** Type guard for checking if value is a Promise */
export const isPromise = <T>(value: unknown): value is Promise<T> => {
  return value instanceof Promise;
};

/** Type guard for checking if value is an Error */
export const isError = (value: unknown): value is Error => {
  return value instanceof Error;
};

/** Assert that a value is never (for exhaustive checks) */
export const assertNever = (value: never): never => {
  throw new Error(`Unexpected value: ${value}`);
};

/** Create a branded type */
export const brand = <T, B extends string>(value: T): T & { readonly __brand: B } => {
  return value as T & { readonly __brand: B };
};
