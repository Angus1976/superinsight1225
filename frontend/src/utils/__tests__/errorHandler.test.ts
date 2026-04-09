import { describe, it, expect } from 'vitest';
import type { AxiosError } from 'axios';
import {
  getErrorCategory,
  getErrorSeverity,
  generateErrorCode,
  getDefaultRecoveryActions,
  isRetryableError,
  parseFieldErrors,
  transformAxiosError,
  transformError,
} from '../errorHandler';

describe('errorHandler', () => {
  it('getErrorCategory maps status and fallbacks', () => {
    expect(getErrorCategory(undefined)).toBe('unknown');
    expect(getErrorCategory(404)).toBe('notFound');
    expect(getErrorCategory(401)).toBe('auth');
    expect(getErrorCategory(503)).toBe('maintenance');
    expect(getErrorCategory(418)).toBe('unknown');
    expect(getErrorCategory(502)).toBe('server');
  });

  it('getErrorSeverity covers categories', () => {
    expect(getErrorSeverity('auth')).toBe('warning');
    expect(getErrorSeverity('server')).toBe('error');
    expect(getErrorSeverity('notFound')).toBe('info');
  });

  it('generateErrorCode uses prefix and status', () => {
    expect(generateErrorCode('notFound', 404)).toMatch(/^NF_404$/);
    expect(generateErrorCode('auth')).toMatch(/^AUTH_/);
  });

  it('getDefaultRecoveryActions returns entries', () => {
    expect(getDefaultRecoveryActions('network').length).toBeGreaterThan(0);
    expect(getDefaultRecoveryActions('unknown').length).toBeGreaterThan(0);
  });

  it('isRetryableError', () => {
    expect(isRetryableError('network')).toBe(true);
    expect(isRetryableError('auth')).toBe(false);
  });

  it('parseFieldErrors handles shapes', () => {
    expect(parseFieldErrors(null)).toEqual([]);
    expect(
      parseFieldErrors({
        errors: [{ field: 'email', message: 'bad' }],
      })
    ).toEqual([expect.objectContaining({ field: 'email', message: 'bad' })]);
    expect(
      parseFieldErrors({
        detail: [{ loc: ['body', 'x'], msg: 'required', type: 'missing' }],
      })
    ).toEqual([expect.objectContaining({ field: 'x' })]);
  });

  it('transformAxiosError builds AppError', () => {
    const err = {
      isAxiosError: true,
      message: 'Request failed',
      response: {
        status: 422,
        data: { detail: 'Invalid' },
      },
      config: { url: '/api/x', method: 'post' },
    } as AxiosError;
    const app = transformAxiosError(err);
    expect(app.category).toBe('validation');
    expect(app.statusCode).toBe(422);
    expect(app.endpoint).toBe('/api/x');
  });

  it('transformError dispatches by input type', () => {
    const fromErr = transformError(new Error('boom'));
    expect(fromErr.category).toBe('client');
    const fromStr = transformError('plain');
    expect(fromStr.technicalMessage).toBe('plain');
    const fromAxios = transformError({
      isAxiosError: true,
      message: 'm',
      response: { status: 500, data: {} },
    } as AxiosError);
    expect(fromAxios.category).toBe('server');
    const unknown = transformError({ weird: 1 });
    expect(unknown.category).toBe('unknown');
  });
});
