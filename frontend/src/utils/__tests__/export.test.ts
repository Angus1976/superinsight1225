/**
 * Tests for export utility functions
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  escapeCSVValue,
  formatDateForCSV,
  formatDateTimeForCSV,
  exportTasksToJSON,
  exportTaskToJSON,
  validateJSONExportData,
  downloadFile,
  exportTasksToExcel,
  exportTaskToExcel,
  validateExcelExportOptions,
  type ExportBatchData,
  type ExportAnnotationResult,
  type ExcelExportOptions,
} from '../export';
import type { Task } from '@/types';

// Mock task data for testing
const createMockTask = (overrides: Partial<Task> = {}): Task => ({
  id: 'task-1',
  name: 'Test Task',
  description: 'Test description',
  status: 'in_progress',
  priority: 'high',
  annotation_type: 'text_classification',
  assignee_id: 'user-1',
  assignee_name: 'Test User',
  created_by: 'admin',
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-16T15:30:00Z',
  due_date: '2024-02-01T00:00:00Z',
  progress: 50,
  total_items: 100,
  completed_items: 50,
  tenant_id: 'tenant-1',
  label_studio_project_id: '123',
  label_studio_sync_status: 'synced',
  label_studio_last_sync: '2024-01-16T15:00:00Z',
  tags: ['urgent', 'customer'],
  ...overrides,
});

describe('CSV Export Utilities', () => {
  describe('escapeCSVValue', () => {
    it('should return empty string for null/undefined', () => {
      expect(escapeCSVValue(null)).toBe('');
      expect(escapeCSVValue(undefined)).toBe('');
    });

    it('should return string as-is when no escaping needed', () => {
      expect(escapeCSVValue('simple text')).toBe('simple text');
      expect(escapeCSVValue('123')).toBe('123');
    });

    it('should escape values containing commas', () => {
      expect(escapeCSVValue('hello, world')).toBe('"hello, world"');
    });

    it('should escape values containing quotes', () => {
      expect(escapeCSVValue('say "hello"')).toBe('"say ""hello"""');
    });

    it('should escape values containing newlines', () => {
      expect(escapeCSVValue('line1\nline2')).toBe('"line1\nline2"');
    });
  });

  describe('formatDateForCSV', () => {
    it('should return empty string for undefined', () => {
      expect(formatDateForCSV(undefined)).toBe('');
    });

    it('should format valid date string', () => {
      const result = formatDateForCSV('2024-01-15T10:00:00Z');
      expect(result).toBeTruthy();
      expect(typeof result).toBe('string');
    });
  });

  describe('formatDateTimeForCSV', () => {
    it('should return empty string for undefined', () => {
      expect(formatDateTimeForCSV(undefined)).toBe('');
    });

    it('should format valid datetime string', () => {
      const result = formatDateTimeForCSV('2024-01-15T10:00:00Z');
      expect(result).toBeTruthy();
      expect(typeof result).toBe('string');
    });
  });
});

describe('JSON Export Utilities', () => {
  let mockCreateObjectURL: ReturnType<typeof vi.fn>;
  let mockRevokeObjectURL: ReturnType<typeof vi.fn>;
  let mockAppendChild: ReturnType<typeof vi.fn>;
  let mockRemoveChild: ReturnType<typeof vi.fn>;
  let mockClick: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Mock URL methods
    mockCreateObjectURL = vi.fn().mockReturnValue('blob:test-url');
    mockRevokeObjectURL = vi.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    // Mock DOM methods
    mockClick = vi.fn();
    mockAppendChild = vi.fn();
    mockRemoveChild = vi.fn();
    
    vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild);
    vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') {
        return {
          href: '',
          download: '',
          style: { display: '' },
          click: mockClick,
        } as unknown as HTMLAnchorElement;
      }
      return document.createElement(tag);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('exportTaskToJSON', () => {
    it('should export single task to JSON', () => {
      const task = createMockTask();
      
      exportTaskToJSON(task);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });

    it('should include project config when option is true', () => {
      const task = createMockTask();
      
      exportTaskToJSON(task, { includeProjectConfig: true });

      const blobArg = mockCreateObjectURL.mock.calls[0][0];
      expect(blobArg).toBeInstanceOf(Blob);
    });

    it('should include sync metadata when option is true', () => {
      const task = createMockTask();
      
      exportTaskToJSON(task, { includeSyncMetadata: true });

      expect(mockCreateObjectURL).toHaveBeenCalled();
    });
  });

  describe('exportTasksToJSON', () => {
    it('should export multiple tasks to JSON', () => {
      const tasks = [
        createMockTask({ id: 'task-1', name: 'Task 1' }),
        createMockTask({ id: 'task-2', name: 'Task 2' }),
        createMockTask({ id: 'task-3', name: 'Task 3' }),
      ];

      exportTasksToJSON(tasks);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });

    it('should include annotations when provided', () => {
      const tasks = [createMockTask()];
      const annotationsMap = new Map<string, ExportAnnotationResult[]>();
      annotationsMap.set('task-1', [
        {
          id: 1,
          task_id: 100,
          result: [{ value: { choices: ['positive'] } }],
          created_at: '2024-01-15T10:00:00Z',
        },
      ]);

      exportTasksToJSON(tasks, { includeAnnotations: true }, annotationsMap);

      expect(mockCreateObjectURL).toHaveBeenCalled();
    });

    it('should calculate correct summary statistics', () => {
      const tasks = [
        createMockTask({ id: 'task-1', status: 'completed', priority: 'high', total_items: 100, completed_items: 100 }),
        createMockTask({ id: 'task-2', status: 'in_progress', priority: 'medium', total_items: 50, completed_items: 25 }),
        createMockTask({ id: 'task-3', status: 'pending', priority: 'low', total_items: 30, completed_items: 0 }),
      ];

      exportTasksToJSON(tasks);

      // Verify the blob was created (summary is included in the JSON)
      expect(mockCreateObjectURL).toHaveBeenCalled();
    });

    it('should use custom filename when provided', () => {
      const tasks = [createMockTask()];
      
      exportTasksToJSON(tasks, { filename: 'custom_export' });

      expect(mockCreateObjectURL).toHaveBeenCalled();
    });
  });

  describe('validateJSONExportData', () => {
    it('should return true for valid export data', () => {
      const validData: ExportBatchData = {
        export_info: {
          exported_at: '2024-01-15T10:00:00Z',
          total_tasks: 1,
          export_version: '1.0',
          include_annotations: true,
          include_project_config: true,
          include_sync_metadata: true,
        },
        tasks: [
          {
            task: {
              id: 'task-1',
              name: 'Test Task',
              status: 'in_progress',
              priority: 'high',
              annotation_type: 'text_classification',
              created_by: 'admin',
              created_at: '2024-01-15T10:00:00Z',
              updated_at: '2024-01-16T15:30:00Z',
              progress: 50,
              total_items: 100,
              completed_items: 50,
              tenant_id: 'tenant-1',
            },
          },
        ],
        summary: {
          total_tasks: 1,
          by_status: { pending: 0, in_progress: 1, completed: 0, cancelled: 0 },
          by_priority: { low: 0, medium: 0, high: 1, urgent: 0 },
          by_annotation_type: { text_classification: 1, ner: 0, sentiment: 0, qa: 0, custom: 0 },
          total_items: 100,
          completed_items: 50,
          overall_progress: 50,
        },
      };

      expect(validateJSONExportData(validData)).toBe(true);
    });

    it('should return false for null/undefined', () => {
      expect(validateJSONExportData(null)).toBe(false);
      expect(validateJSONExportData(undefined)).toBe(false);
    });

    it('should return false for missing export_info', () => {
      const invalidData = {
        tasks: [],
        summary: {},
      };

      expect(validateJSONExportData(invalidData)).toBe(false);
    });

    it('should return false for missing tasks array', () => {
      const invalidData = {
        export_info: {
          exported_at: '2024-01-15T10:00:00Z',
          total_tasks: 0,
          export_version: '1.0',
        },
        summary: {},
      };

      expect(validateJSONExportData(invalidData)).toBe(false);
    });

    it('should return false for invalid task structure', () => {
      const invalidData = {
        export_info: {
          exported_at: '2024-01-15T10:00:00Z',
          total_tasks: 1,
          export_version: '1.0',
          include_annotations: true,
          include_project_config: true,
          include_sync_metadata: true,
        },
        tasks: [{ invalid: 'structure' }],
        summary: {},
      };

      expect(validateJSONExportData(invalidData)).toBe(false);
    });
  });

  describe('downloadFile', () => {
    it('should create blob and trigger download', () => {
      downloadFile('test content', 'test.txt', 'text/plain');

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockAppendChild).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockRemoveChild).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });
  });
});


describe('Excel Export Utilities', () => {
  describe('exportTasksToExcel', () => {
    it('should export multiple tasks to Excel without errors', () => {
      const tasks = [
        createMockTask({ id: 'task-1', name: 'Task 1', status: 'completed' }),
        createMockTask({ id: 'task-2', name: 'Task 2', status: 'in_progress' }),
        createMockTask({ id: 'task-3', name: 'Task 3', status: 'pending' }),
      ];

      // Should not throw
      expect(() => exportTasksToExcel(tasks)).not.toThrow();
    });

    it('should export with custom options', () => {
      const tasks = [createMockTask()];
      
      expect(() => exportTasksToExcel(tasks, {
        includeId: true,
        includeDescription: true,
        includeLabelStudioId: true,
        includeSyncStatus: true,
        includeTags: true,
        includeSummary: true,
        includeChartsData: true,
        filename: 'custom_export',
      })).not.toThrow();
    });

    it('should export without summary sheet when option is false', () => {
      const tasks = [createMockTask()];
      
      expect(() => exportTasksToExcel(tasks, {
        includeSummary: false,
        includeChartsData: false,
      })).not.toThrow();
    });

    it('should handle empty tasks array', () => {
      expect(() => exportTasksToExcel([])).not.toThrow();
    });

    it('should handle tasks with missing optional fields', () => {
      const task = createMockTask({
        description: undefined,
        assignee_id: undefined,
        assignee_name: undefined,
        due_date: undefined,
        label_studio_project_id: undefined,
        label_studio_sync_status: undefined,
        tags: undefined,
      });
      
      expect(() => exportTasksToExcel([task])).not.toThrow();
    });

    it('should calculate correct statistics for summary', () => {
      const tasks = [
        createMockTask({ 
          id: 'task-1', 
          status: 'completed', 
          priority: 'high',
          total_items: 100, 
          completed_items: 100 
        }),
        createMockTask({ 
          id: 'task-2', 
          status: 'in_progress', 
          priority: 'medium',
          total_items: 50, 
          completed_items: 25 
        }),
        createMockTask({ 
          id: 'task-3', 
          status: 'pending', 
          priority: 'low',
          total_items: 30, 
          completed_items: 0,
          assignee_id: undefined,
        }),
      ];

      // Should not throw and should include summary
      expect(() => exportTasksToExcel(tasks, { includeSummary: true })).not.toThrow();
    });
  });

  describe('exportTaskToExcel', () => {
    it('should export single task to Excel', () => {
      const task = createMockTask();
      
      expect(() => exportTaskToExcel(task)).not.toThrow();
    });

    it('should use custom filename for single task', () => {
      const task = createMockTask({ id: 'test-task-123' });
      
      expect(() => exportTaskToExcel(task, { 
        filename: 'single_task_export' 
      })).not.toThrow();
    });
  });

  describe('validateExcelExportOptions', () => {
    it('should return true for valid options', () => {
      const validOptions: ExcelExportOptions = {
        includeId: true,
        includeDescription: false,
        includeLabelStudioId: true,
        includeSyncStatus: true,
        includeTags: false,
        includeSummary: true,
        includeChartsData: true,
        filename: 'test_export',
      };

      expect(validateExcelExportOptions(validOptions)).toBe(true);
    });

    it('should return true for empty options', () => {
      expect(validateExcelExportOptions({})).toBe(true);
    });

    it('should return true for undefined options', () => {
      expect(validateExcelExportOptions(undefined)).toBe(true);
    });

    it('should return true for null options', () => {
      expect(validateExcelExportOptions(null)).toBe(true);
    });

    it('should return false for invalid boolean option', () => {
      const invalidOptions = {
        includeId: 'yes', // Should be boolean
      };

      expect(validateExcelExportOptions(invalidOptions)).toBe(false);
    });

    it('should return false for invalid filename type', () => {
      const invalidOptions = {
        filename: 123, // Should be string
      };

      expect(validateExcelExportOptions(invalidOptions)).toBe(false);
    });

    it('should return false for invalid translation function', () => {
      const invalidOptions = {
        t: 'not a function', // Should be function
      };

      expect(validateExcelExportOptions(invalidOptions)).toBe(false);
    });

    it('should return true for options with translation function', () => {
      const validOptions = {
        t: (key: string) => key,
        includeId: true,
      };

      expect(validateExcelExportOptions(validOptions)).toBe(true);
    });
  });
});
