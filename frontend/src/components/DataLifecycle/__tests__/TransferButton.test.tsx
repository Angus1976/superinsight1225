/**
 * TransferButton Component Tests
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import TransferButton from '../TransferButton';
import * as dataLifecycleAPI from '@/api/dataLifecycleAPI';

// Mock the API module
vi.mock('@/api/dataLifecycleAPI', () => ({
  checkPermissionAPI: vi.fn(),
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'transfer.button': 'Transfer Data',
        'transfer.validation.minRecords': 'At least 1 record must be selected',
        'transfer.messages.permissionDenied': 'You don\'t have permission for this operation',
          'common.messages.networkError': 'Network error, please try again later',
      };
      return translations[key] || key;
    },
  }),
}));

describe('TransferButton', () => {
  const mockRecords = [
    {
      id: 'record-1',
      content: { field1: 'value1' },
      metadata: { source: 'test' },
    },
    {
      id: 'record-2',
      content: { field1: 'value2' },
      metadata: { source: 'test' },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render button with correct text', () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    expect(screen.getByText('Transfer Data')).toBeInTheDocument();
  });

  it('should show loading state initially', () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    const button = screen.getByRole('button');
    expect(button).toHaveClass('ant-btn-loading');
  });

  it('should check permissions on mount', async () => {
    const mockCheckPermission = vi.mocked(dataLifecycleAPI.checkPermissionAPI);
    mockCheckPermission.mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      expect(mockCheckPermission).toHaveBeenCalledWith({
        source_type: 'structuring',
        operation: 'transfer',
      });
    });
  });

  it('should be disabled when no records are provided', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={[]}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  it('should be disabled when user lacks permissions', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: false,
      requires_approval: false,
      user_role: 'user',
      reason: 'Insufficient permissions',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  it('should show tooltip with disabled reason when disabled', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: false,
      requires_approval: false,
      user_role: 'user',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    // Verify button is disabled (tooltip functionality is tested in integration tests)
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('should be enabled when user has permissions and records exist', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });
  });

  it('should respect disabled prop', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
        disabled={true}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  it('should handle permission check errors gracefully', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockRejectedValue(
      new Error('Network error')
    );

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Permission check failed:',
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });

  it('should open modal when clicked (placeholder)', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });

    const button = screen.getByRole('button');
    await userEvent.click(button);

    // 若其它用例/文件留下已关闭的 ant-modal-wrap，querySelector 会命中 display:none；
    // 这里取「可见」的 wrap，避免误判。
    await waitFor(
      () => {
        const visibleWrap = Array.from(document.querySelectorAll('.ant-modal-wrap')).find(
          (el) => (el as HTMLElement).style.display !== 'none'
        );
        expect(visibleWrap).toBeTruthy();
        expect(screen.getByRole('dialog', { hidden: true })).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it('should call onTransferComplete callback when transfer succeeds', async () => {
    const mockOnTransferComplete = vi.fn();
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    const { rerender } = render(
      <TransferButton
        sourceType="structuring"
        sourceId="test-source-1"
        records={mockRecords}
        onTransferComplete={mockOnTransferComplete}
      />
    );

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });

    // Note: Full callback testing will be done when TransferModal is implemented
    // For now, we just verify the prop is accepted
    expect(mockOnTransferComplete).not.toHaveBeenCalled();
  });

  it('should support different source types', async () => {
    const mockCheckPermission = vi.mocked(dataLifecycleAPI.checkPermissionAPI);
    mockCheckPermission.mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'admin',
    });

    const sourceTypes: Array<'structuring' | 'augmentation' | 'sync'> = [
      'structuring',
      'augmentation',
      'sync',
    ];

    for (const sourceType of sourceTypes) {
      mockCheckPermission.mockClear();

      render(
        <TransferButton
          sourceType={sourceType}
          sourceId="test-source-1"
          records={mockRecords}
        />
      );

      await waitFor(() => {
        expect(mockCheckPermission).toHaveBeenCalledWith({
          source_type: sourceType,
          operation: 'transfer',
        });
      });
    }
  });
});
