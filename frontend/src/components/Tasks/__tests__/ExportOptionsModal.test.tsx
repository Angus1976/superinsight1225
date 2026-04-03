/**
 * Tests for ExportOptionsModal component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportOptionsModal, addExportHistoryEntry } from '../ExportOptionsModal';
import type { ExportOptions } from '../ExportOptionsModal';

// Mock react-i18next — useTranslation(['tasks','common']) 传入的 key 为 export.* / columns.* 等（无前缀）
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'export.title': 'Export Tasks',
        'export.history': 'History',
        'export.exportButton': 'Export',
        'export.selectFormat': 'Select export format:',
        'export.csv': 'CSV (Simple Data)',
        'export.json': 'JSON (Complete Data)',
        'export.excelFormat': 'Excel (Report)',
        'export.selectRange': 'Export Range',
        'export.allTasks': 'All Tasks',
        'export.selectedTasks': 'Selected Tasks',
        'export.filteredTasks': 'Filtered Tasks',
        'export.selectFields': 'Select Fields',
        'export.exportHistory': 'Export History',
        'export.syncTimeJustNow': 'Just now',
        'syncTimeJustNow': 'Just now',
        'syncTimeMinutesAgo': '{{count}} min ago',
        'syncTimeHoursAgo': '{{count}} h ago',
        'syncTimeDaysAgo': '{{count}} d ago',
        'columns.id': 'ID',
        'columns.name': 'Name',
        'columns.status': 'Status',
        'description': 'Description',
        'columns.priority': 'Priority',
        'columns.annotationType': 'Annotation Type',
        'columns.progress': 'Progress',
        'columns.completedItems': 'Completed',
        'columns.totalItems': 'Total',
        'columns.assignee': 'Assignee',
        'columns.createdAt': 'Created',
        'columns.dueDate': 'Due',
        'detail.projectId': 'Project ID',
        'syncStatus': 'Sync',
        'tagsLabel': 'Tags',
        'cancel': 'Cancel',
        'selectAll': 'Select All',
        'selectNone': 'Deselect All',
      };
      let result = translations[key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
      }
      return result;
    },
  }),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('ExportOptionsModal', () => {
  const defaultProps = {
    open: true,
    onCancel: vi.fn(),
    onExport: vi.fn(),
    selectedCount: 0,
    filteredCount: 10,
    totalCount: 100,
    loading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it('renders modal when open', () => {
    render(<ExportOptionsModal {...defaultProps} />);
    
    expect(screen.getByText('Export Tasks')).toBeInTheDocument();
    expect(screen.getByText('Select export format:')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<ExportOptionsModal {...defaultProps} open={false} />);
    
    expect(screen.queryByText('Export Tasks')).not.toBeInTheDocument();
  });

  it('shows format options', () => {
    render(<ExportOptionsModal {...defaultProps} />);
    
    expect(screen.getByText('CSV (Simple Data)')).toBeInTheDocument();
    expect(screen.getByText('JSON (Complete Data)')).toBeInTheDocument();
    expect(screen.getByText('Excel (Report)')).toBeInTheDocument();
  });

  it('shows range options with correct counts', () => {
    render(<ExportOptionsModal {...defaultProps} selectedCount={5} />);
    
    expect(screen.getByText(/All Tasks.*100/)).toBeInTheDocument();
    expect(screen.getByText(/Selected Tasks.*5/)).toBeInTheDocument();
  });

  it('calls onCancel when cancel button clicked', async () => {
    const user = userEvent.setup();
    render(<ExportOptionsModal {...defaultProps} />);
    
    await user.click(screen.getByText('Cancel'));
    
    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('calls onExport with correct options when export clicked', async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    render(<ExportOptionsModal {...defaultProps} onExport={onExport} />);
    
    // Click export button
    const exportButton = screen.getByRole('button', { name: /Export.*100/ });
    await user.click(exportButton);
    
    expect(onExport).toHaveBeenCalledWith(
      expect.objectContaining({
        format: 'csv',
        range: 'all',
        fields: expect.arrayContaining(['id', 'name', 'status']),
      })
    );
  });

  it('changes format when radio selected', async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    render(<ExportOptionsModal {...defaultProps} onExport={onExport} />);
    
    // Select JSON format
    await user.click(screen.getByText('JSON (Complete Data)'));
    
    // Click export
    const exportButton = screen.getByRole('button', { name: /Export/ });
    await user.click(exportButton);
    
    expect(onExport).toHaveBeenCalledWith(
      expect.objectContaining({
        format: 'json',
      })
    );
  });

  it('defaults to selected range when tasks are selected', () => {
    render(<ExportOptionsModal {...defaultProps} selectedCount={5} />);
    
    // The selected radio should be checked
    const selectedRadio = screen.getByRole('radio', { name: /Selected Tasks/ });
    expect(selectedRadio).toBeChecked();
  });

  it('disables export button when no fields selected', async () => {
    const user = userEvent.setup();
    render(<ExportOptionsModal {...defaultProps} />);
    
    // Click deselect all
    await user.click(screen.getByText('Deselect All'));
    
    // Export button should be disabled
    const exportButton = screen.getByRole('button', { name: /Export/ });
    expect(exportButton).toBeDisabled();
  });

  it('shows loading state', () => {
    render(<ExportOptionsModal {...defaultProps} loading={true} />);
    
    const exportButton = screen.getByRole('button', { name: /Export/ });
    expect(exportButton).toHaveClass('ant-btn-loading');
  });

  it('shows history button', () => {
    render(<ExportOptionsModal {...defaultProps} />);
    
    expect(screen.getByText('History')).toBeInTheDocument();
  });
});

describe('addExportHistoryEntry', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('adds entry to localStorage', () => {
    addExportHistoryEntry({
      format: 'csv',
      range: 'all',
      taskCount: 10,
      fields: ['id', 'name'],
      filename: 'test.csv',
    });

    expect(localStorageMock.setItem).toHaveBeenCalled();
    
    const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
    expect(savedData).toHaveLength(1);
    expect(savedData[0]).toMatchObject({
      format: 'csv',
      range: 'all',
      taskCount: 10,
    });
  });

  it('limits history to 10 entries', () => {
    // Add 12 entries
    for (let i = 0; i < 12; i++) {
      localStorageMock.getItem.mockReturnValueOnce(
        JSON.stringify(Array(i).fill({ id: `entry_${i}` }))
      );
      addExportHistoryEntry({
        format: 'csv',
        range: 'all',
        taskCount: i,
        fields: ['id'],
        filename: `test_${i}.csv`,
      });
    }

    // Last call should have max 10 entries
    const lastCall = localStorageMock.setItem.mock.calls[localStorageMock.setItem.mock.calls.length - 1];
    const savedData = JSON.parse(lastCall[1]);
    expect(savedData.length).toBeLessThanOrEqual(10);
  });
});
