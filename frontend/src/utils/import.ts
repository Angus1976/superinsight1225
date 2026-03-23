/**
 * Import utility functions for task data
 * Supports CSV, JSON, and Excel import with validation and data cleaning
 */

import * as XLSX from 'xlsx';
import type { TaskPriority, AnnotationType } from '@/types';

/**
 * Import result structure
 */
export interface ImportResult<T> {
  success: boolean;
  data: T[];
  errors: ImportError[];
  warnings: ImportWarning[];
  totalRows: number;
  validRows: number;
  invalidRows: number;
}

/**
 * Import error structure
 */
export interface ImportError {
  row: number;
  field?: string;
  message: string;
  value?: unknown;
}

/**
 * Import warning structure
 */
export interface ImportWarning {
  row: number;
  field?: string;
  message: string;
  value?: unknown;
}

/**
 * Imported task data structure (before creating actual task)
 */
export interface ImportedTaskData {
  name: string;
  description?: string;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  due_date?: string;
  tags?: string[];
  assignee_id?: string;
  assignee_name?: string;
}


/**
 * Import options
 */
export interface ImportOptions {
  /** Skip header row (default: true) */
  skipHeader?: boolean;
  /** Strict validation mode (default: false) */
  strictMode?: boolean;
  /** Custom field mapping */
  fieldMapping?: Record<string, string>;
  /** Translation function for error messages */
  t?: (key: string) => string;
  /** Maximum rows to import (default: 1000) */
  maxRows?: number;
}

/**
 * Default import options
 */
const defaultImportOptions: ImportOptions = {
  skipHeader: true,
  strictMode: false,
  maxRows: 1000,
};

/**
 * Valid priority values
 */
const VALID_PRIORITIES: TaskPriority[] = ['low', 'medium', 'high', 'urgent'];

/**
 * Valid annotation types
 */
const VALID_ANNOTATION_TYPES: AnnotationType[] = ['text_classification', 'ner', 'sentiment', 'qa', 'custom'];

/**
 * Priority aliases for flexible import
 */
const PRIORITY_ALIASES: Record<string, TaskPriority> = {
  'low': 'low',
  '低': 'low',
  'l': 'low',
  '1': 'low',
  'medium': 'medium',
  '中': 'medium',
  'm': 'medium',
  '2': 'medium',
  'high': 'high',
  '高': 'high',
  'h': 'high',
  '3': 'high',
  'urgent': 'urgent',
  '紧急': 'urgent',
  'u': 'urgent',
  '4': 'urgent',
};

/**
 * Annotation type aliases for flexible import
 */
const ANNOTATION_TYPE_ALIASES: Record<string, AnnotationType> = {
  'text_classification': 'text_classification',
  'textclassification': 'text_classification',
  'text classification': 'text_classification',
  '文本分类': 'text_classification',
  'classification': 'text_classification',
  'ner': 'ner',
  'named entity recognition': 'ner',
  '命名实体识别': 'ner',
  'entity': 'ner',
  'sentiment': 'sentiment',
  'sentiment analysis': 'sentiment',
  '情感分析': 'sentiment',
  'qa': 'qa',
  'question answer': 'qa',
  'question & answer': 'qa',
  '问答': 'qa',
  'custom': 'custom',
  '自定义': 'custom',
};


/**
 * Default field mapping for CSV/Excel headers
 */
const DEFAULT_FIELD_MAPPING: Record<string, string> = {
  // English headers
  'name': 'name',
  'task name': 'name',
  'taskname': 'name',
  'title': 'name',
  'description': 'description',
  'desc': 'description',
  'priority': 'priority',
  'annotation type': 'annotation_type',
  'annotationtype': 'annotation_type',
  'annotation_type': 'annotation_type',
  'type': 'annotation_type',
  'due date': 'due_date',
  'duedate': 'due_date',
  'due_date': 'due_date',
  'deadline': 'due_date',
  'tags': 'tags',
  'assignee': 'assignee_name',
  'assignee_name': 'assignee_name',
  'assigned to': 'assignee_name',
  // Chinese headers
  '任务名称': 'name',
  '名称': 'name',
  '描述': 'description',
  '优先级': 'priority',
  '标注类型': 'annotation_type',
  '截止日期': 'due_date',
  '标签': 'tags',
  '分配人': 'assignee_name',
  '负责人': 'assignee_name',
};

/**
 * Normalize a string value (trim, lowercase)
 */
const normalizeString = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  return String(value).trim().toLowerCase();
};

/**
 * Parse priority value with alias support
 */
export const parsePriority = (value: unknown): TaskPriority | null => {
  const normalized = normalizeString(value);
  if (!normalized) return null;
  return PRIORITY_ALIASES[normalized] || null;
};

/**
 * Parse annotation type value with alias support
 */
export const parseAnnotationType = (value: unknown): AnnotationType | null => {
  const normalized = normalizeString(value);
  if (!normalized) return null;
  return ANNOTATION_TYPE_ALIASES[normalized] || null;
};

/**
 * Parse date value to ISO string
 */
export const parseDate = (value: unknown): string | null => {
  if (!value) return null;
  
  // Handle Excel date serial numbers
  if (typeof value === 'number') {
    const date = XLSX.SSF.parse_date_code(value);
    if (date) {
      return new Date(date.y, date.m - 1, date.d).toISOString();
    }
  }
  
  // Handle string dates
  const strValue = String(value).trim();
  if (!strValue) return null;
  
  const parsed = new Date(strValue);
  if (!isNaN(parsed.getTime())) {
    return parsed.toISOString();
  }
  
  return null;
};

/**
 * Parse tags value (comma-separated string or array)
 */
export const parseTags = (value: unknown): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(v => String(v).trim()).filter(Boolean);
  return String(value).split(',').map(t => t.trim()).filter(Boolean);
};


/**
 * Validate a single task row
 */
const validateTaskRow = (
  row: Record<string, unknown>,
  rowIndex: number,
  options: ImportOptions
): { data: ImportedTaskData | null; errors: ImportError[]; warnings: ImportWarning[] } => {
  const errors: ImportError[] = [];
  const warnings: ImportWarning[] = [];
  const t = options.t || ((key: string) => key);
  
  // Get name (required)
  const name = row.name ? String(row.name).trim() : '';
  if (!name) {
    errors.push({ row: rowIndex, field: 'name', message: t('import.errors.nameRequired') || 'Task name is required' });
  } else if (name.length > 100) {
    errors.push({ row: rowIndex, field: 'name', message: t('import.errors.nameTooLong') || 'Task name exceeds 100 characters', value: name });
  }
  
  // Get description (optional)
  const description = row.description ? String(row.description).trim() : undefined;
  if (description && description.length > 500) {
    warnings.push({ row: rowIndex, field: 'description', message: t('import.errors.descriptionTooLong') || 'Description truncated to 500 characters' });
  }
  
  // Get priority (required, with default)
  let priority: TaskPriority = 'medium';
  if (row.priority) {
    const parsed = parsePriority(row.priority);
    if (parsed) {
      priority = parsed;
    } else if (options.strictMode) {
      errors.push({ row: rowIndex, field: 'priority', message: t('import.errors.invalidPriority') || 'Invalid priority value', value: row.priority });
    } else {
      warnings.push({ row: rowIndex, field: 'priority', message: t('import.warnings.defaultPriority') || 'Using default priority: medium', value: row.priority });
    }
  }
  
  // Get annotation type (required, with default)
  let annotationType: AnnotationType = 'text_classification';
  if (row.annotation_type) {
    const parsed = parseAnnotationType(row.annotation_type);
    if (parsed) {
      annotationType = parsed;
    } else if (options.strictMode) {
      errors.push({ row: rowIndex, field: 'annotation_type', message: t('import.errors.invalidAnnotationType') || 'Invalid annotation type', value: row.annotation_type });
    } else {
      warnings.push({ row: rowIndex, field: 'annotation_type', message: t('import.warnings.defaultAnnotationType') || 'Using default: text_classification', value: row.annotation_type });
    }
  }
  
  // Get due date (optional)
  let dueDate: string | undefined;
  if (row.due_date) {
    const parsed = parseDate(row.due_date);
    if (parsed) {
      dueDate = parsed;
    } else {
      warnings.push({ row: rowIndex, field: 'due_date', message: t('import.warnings.invalidDate') || 'Invalid date format, skipped', value: row.due_date });
    }
  }
  
  // Get tags (optional)
  const tags = parseTags(row.tags);
  
  // Get assignee name (optional)
  const assigneeName = row.assignee_name ? String(row.assignee_name).trim() : undefined;
  
  // Return null if there are errors
  if (errors.length > 0) {
    return { data: null, errors, warnings };
  }
  
  return {
    data: {
      name,
      description: description?.substring(0, 500),
      priority,
      annotation_type: annotationType,
      due_date: dueDate,
      tags: tags.length > 0 ? tags : undefined,
      assignee_name: assigneeName,
    },
    errors,
    warnings,
  };
};


/**
 * Map raw row data to normalized field names
 */
const mapRowFields = (
  row: Record<string, unknown>,
  fieldMapping: Record<string, string>
): Record<string, unknown> => {
  const mapped: Record<string, unknown> = {};
  
  for (const [key, value] of Object.entries(row)) {
    const normalizedKey = key.toLowerCase().trim();
    const mappedField = fieldMapping[normalizedKey];
    if (mappedField) {
      mapped[mappedField] = value;
    }
  }
  
  return mapped;
};

/**
 * Parse CSV content string
 */
export const parseCSVContent = (content: string): string[][] => {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = '';
  let inQuotes = false;
  
  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    const nextChar = content[i + 1];
    
    if (inQuotes) {
      if (char === '"' && nextChar === '"') {
        currentCell += '"';
        i++; // Skip next quote
      } else if (char === '"') {
        inQuotes = false;
      } else {
        currentCell += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ',') {
        currentRow.push(currentCell.trim());
        currentCell = '';
      } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
        currentRow.push(currentCell.trim());
        if (currentRow.some(cell => cell !== '')) {
          rows.push(currentRow);
        }
        currentRow = [];
        currentCell = '';
        if (char === '\r') i++; // Skip \n after \r
      } else if (char !== '\r') {
        currentCell += char;
      }
    }
  }
  
  // Handle last row
  if (currentCell || currentRow.length > 0) {
    currentRow.push(currentCell.trim());
    if (currentRow.some(cell => cell !== '')) {
      rows.push(currentRow);
    }
  }
  
  return rows;
};

/**
 * Import tasks from CSV file content
 */
export const importTasksFromCSV = (
  content: string,
  options: ImportOptions = {}
): ImportResult<ImportedTaskData> => {
  const mergedOptions = { ...defaultImportOptions, ...options };
  const fieldMapping = { ...DEFAULT_FIELD_MAPPING, ...mergedOptions.fieldMapping };
  
  const result: ImportResult<ImportedTaskData> = {
    success: false,
    data: [],
    errors: [],
    warnings: [],
    totalRows: 0,
    validRows: 0,
    invalidRows: 0,
  };
  
  try {
    const rows = parseCSVContent(content);
    if (rows.length === 0) {
      result.errors.push({ row: 0, message: 'Empty CSV file' });
      return result;
    }
    
    // Get headers from first row
    const headers = rows[0].map(h => h.toLowerCase().trim());
    const startRow = mergedOptions.skipHeader ? 1 : 0;
    
    result.totalRows = rows.length - startRow;
    
    // Check max rows limit
    const maxRows = mergedOptions.maxRows || 1000;
    if (result.totalRows > maxRows) {
      result.warnings.push({ row: 0, message: `Only first ${maxRows} rows will be imported` });
    }
    
    // Process each row
    for (let i = startRow; i < Math.min(rows.length, startRow + maxRows); i++) {
      const row = rows[i];
      const rowData: Record<string, unknown> = {};
      
      // Map columns to headers
      headers.forEach((header, index) => {
        if (index < row.length) {
          rowData[header] = row[index];
        }
      });
      
      // Map to normalized field names
      const mappedRow = mapRowFields(rowData, fieldMapping);
      
      // Validate row
      const validation = validateTaskRow(mappedRow, i + 1, mergedOptions);
      result.errors.push(...validation.errors);
      result.warnings.push(...validation.warnings);
      
      if (validation.data) {
        result.data.push(validation.data);
        result.validRows++;
      } else {
        result.invalidRows++;
      }
    }
    
    result.success = result.validRows > 0;
  } catch (error) {
    result.errors.push({ row: 0, message: `CSV parsing error: ${error instanceof Error ? error.message : 'Unknown error'}` });
  }
  
  return result;
};


/**
 * Import tasks from JSON content
 */
export const importTasksFromJSON = (
  content: string,
  options: ImportOptions = {}
): ImportResult<ImportedTaskData> => {
  const mergedOptions = { ...defaultImportOptions, ...options };
  const fieldMapping = { ...DEFAULT_FIELD_MAPPING, ...mergedOptions.fieldMapping };
  
  const result: ImportResult<ImportedTaskData> = {
    success: false,
    data: [],
    errors: [],
    warnings: [],
    totalRows: 0,
    validRows: 0,
    invalidRows: 0,
  };
  
  try {
    const parsed = JSON.parse(content);
    
    // Handle both array and object with tasks array
    let tasks: unknown[];
    if (Array.isArray(parsed)) {
      tasks = parsed;
    } else if (parsed.tasks && Array.isArray(parsed.tasks)) {
      tasks = parsed.tasks;
    } else if (parsed.data && Array.isArray(parsed.data)) {
      tasks = parsed.data;
    } else if (typeof parsed === 'object' && parsed !== null) {
      // Single task object
      tasks = [parsed];
    } else {
      result.errors.push({ row: 0, message: 'Invalid JSON structure: expected array or object with tasks' });
      return result;
    }
    
    result.totalRows = tasks.length;
    
    // Check max rows limit
    const maxRows = mergedOptions.maxRows || 1000;
    if (result.totalRows > maxRows) {
      result.warnings.push({ row: 0, message: `Only first ${maxRows} items will be imported` });
      tasks = tasks.slice(0, maxRows);
    }
    
    // Process each task
    tasks.forEach((task, index) => {
      if (typeof task !== 'object' || task === null) {
        result.errors.push({ row: index + 1, message: 'Invalid task: expected object' });
        result.invalidRows++;
        return;
      }
      
      // Map to normalized field names
      const mappedRow = mapRowFields(task as Record<string, unknown>, fieldMapping);
      
      // Also check for direct field names
      const taskObj = task as Record<string, unknown>;
      if (!mappedRow.name && taskObj.name) mappedRow.name = taskObj.name;
      if (!mappedRow.description && taskObj.description) mappedRow.description = taskObj.description;
      if (!mappedRow.priority && taskObj.priority) mappedRow.priority = taskObj.priority;
      if (!mappedRow.annotation_type && taskObj.annotation_type) mappedRow.annotation_type = taskObj.annotation_type;
      if (!mappedRow.due_date && taskObj.due_date) mappedRow.due_date = taskObj.due_date;
      if (!mappedRow.tags && taskObj.tags) mappedRow.tags = taskObj.tags;
      
      // Validate row
      const validation = validateTaskRow(mappedRow, index + 1, mergedOptions);
      result.errors.push(...validation.errors);
      result.warnings.push(...validation.warnings);
      
      if (validation.data) {
        result.data.push(validation.data);
        result.validRows++;
      } else {
        result.invalidRows++;
      }
    });
    
    result.success = result.validRows > 0;
  } catch (error) {
    result.errors.push({ row: 0, message: `JSON parsing error: ${error instanceof Error ? error.message : 'Unknown error'}` });
  }
  
  return result;
};


/**
 * Import tasks from Excel file (ArrayBuffer)
 */
export const importTasksFromExcel = (
  data: ArrayBuffer,
  options: ImportOptions = {}
): ImportResult<ImportedTaskData> => {
  const mergedOptions = { ...defaultImportOptions, ...options };
  const fieldMapping = { ...DEFAULT_FIELD_MAPPING, ...mergedOptions.fieldMapping };
  
  const result: ImportResult<ImportedTaskData> = {
    success: false,
    data: [],
    errors: [],
    warnings: [],
    totalRows: 0,
    validRows: 0,
    invalidRows: 0,
  };
  
  try {
    const workbook = XLSX.read(data, { type: 'array', cellDates: true });
    
    // Get first sheet
    const sheetName = workbook.SheetNames[0];
    if (!sheetName) {
      result.errors.push({ row: 0, message: 'Excel file has no sheets' });
      return result;
    }
    
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as unknown[][];
    
    if (rows.length === 0) {
      result.errors.push({ row: 0, message: 'Empty Excel sheet' });
      return result;
    }
    
    // Get headers from first row
    const headerRow = rows[0] as unknown[];
    const headers = headerRow.map(h => String(h || '').toLowerCase().trim());
    const startRow = mergedOptions.skipHeader ? 1 : 0;
    
    result.totalRows = rows.length - startRow;
    
    // Check max rows limit
    const maxRows = mergedOptions.maxRows || 1000;
    if (result.totalRows > maxRows) {
      result.warnings.push({ row: 0, message: `Only first ${maxRows} rows will be imported` });
    }
    
    // Process each row
    for (let i = startRow; i < Math.min(rows.length, startRow + maxRows); i++) {
      const row = rows[i] as unknown[];
      if (!row || row.length === 0) continue;
      
      const rowData: Record<string, unknown> = {};
      
      // Map columns to headers
      headers.forEach((header, index) => {
        if (index < row.length && row[index] !== undefined && row[index] !== null) {
          rowData[header] = row[index];
        }
      });
      
      // Skip empty rows
      if (Object.keys(rowData).length === 0) continue;
      
      // Map to normalized field names
      const mappedRow = mapRowFields(rowData, fieldMapping);
      
      // Validate row
      const validation = validateTaskRow(mappedRow, i + 1, mergedOptions);
      result.errors.push(...validation.errors);
      result.warnings.push(...validation.warnings);
      
      if (validation.data) {
        result.data.push(validation.data);
        result.validRows++;
      } else {
        result.invalidRows++;
      }
    }
    
    result.success = result.validRows > 0;
  } catch (error) {
    result.errors.push({ row: 0, message: `Excel parsing error: ${error instanceof Error ? error.message : 'Unknown error'}` });
  }
  
  return result;
};

/**
 * Read file as text
 */
export const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
};

/**
 * Read file as ArrayBuffer
 */
export const readFileAsArrayBuffer = (file: File): Promise<ArrayBuffer> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsArrayBuffer(file);
  });
};


/**
 * Detect file type from file extension
 */
export const detectFileType = (filename: string): 'csv' | 'json' | 'excel' | 'unknown' => {
  const ext = filename.toLowerCase().split('.').pop();
  switch (ext) {
    case 'csv':
      return 'csv';
    case 'json':
      return 'json';
    case 'xlsx':
    case 'xls':
      return 'excel';
    default:
      return 'unknown';
  }
};

/**
 * Import tasks from file (auto-detect format)
 */
export const importTasksFromFile = async (
  file: File,
  options: ImportOptions = {}
): Promise<ImportResult<ImportedTaskData>> => {
  const fileType = detectFileType(file.name);
  
  switch (fileType) {
    case 'csv': {
      const content = await readFileAsText(file);
      return importTasksFromCSV(content, options);
    }
    case 'json': {
      const content = await readFileAsText(file);
      return importTasksFromJSON(content, options);
    }
    case 'excel': {
      const data = await readFileAsArrayBuffer(file);
      return importTasksFromExcel(data, options);
    }
    default:
      return {
        success: false,
        data: [],
        errors: [{ row: 0, message: `Unsupported file type: ${file.name}` }],
        warnings: [],
        totalRows: 0,
        validRows: 0,
        invalidRows: 0,
      };
  }
};

/**
 * Generate sample CSV template
 */
export const generateCSVTemplate = (t?: (key: string) => string): string => {
  const headers = [
    t?.('import.template.name') || 'Task Name',
    t?.('import.template.description') || 'Description',
    t?.('import.template.priority') || 'Priority',
    t?.('import.template.annotationType') || 'Annotation Type',
    t?.('import.template.dueDate') || 'Due Date',
    t?.('import.template.tags') || 'Tags',
  ];
  
  const sampleRows = [
    ['Sample Task 1', 'Description for task 1', 'high', 'text_classification', '2024-12-31', 'tag1,tag2'],
    ['Sample Task 2', 'Description for task 2', 'medium', 'ner', '2024-12-31', 'tag3'],
  ];
  
  const BOM = '\uFEFF';
  return BOM + [headers.join(','), ...sampleRows.map(row => row.join(','))].join('\n');
};

/**
 * Download CSV template
 */
export const downloadCSVTemplate = (t?: (key: string) => string): void => {
  const content = generateCSVTemplate(t);
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = 'task_import_template.csv';
  link.style.display = 'none';
  
  document.body.appendChild(link);
  link.click();
  
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Validate import result has minimum required data
 */
export const validateImportResult = (result: ImportResult<ImportedTaskData>): boolean => {
  return result.success && result.data.length > 0 && result.data.every(task => 
    task.name && 
    task.name.length > 0 && 
    VALID_PRIORITIES.includes(task.priority) &&
    VALID_ANNOTATION_TYPES.includes(task.annotation_type)
  );
};
