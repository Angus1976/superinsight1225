/**
 * Unit tests for import utilities
 */

import { describe, it, expect } from 'vitest';
import {
  parsePriority,
  parseAnnotationType,
  parseDate,
  parseTags,
  parseCSVContent,
  importTasksFromCSV,
  importTasksFromJSON,
  detectFileType,
  generateCSVTemplate,
  validateImportResult,
} from '../import';

describe('Import Utilities', () => {
  describe('parsePriority', () => {
    it('should parse valid priority values', () => {
      expect(parsePriority('low')).toBe('low');
      expect(parsePriority('medium')).toBe('medium');
      expect(parsePriority('high')).toBe('high');
      expect(parsePriority('urgent')).toBe('urgent');
    });

    it('should parse Chinese priority values', () => {
      expect(parsePriority('低')).toBe('low');
      expect(parsePriority('中')).toBe('medium');
      expect(parsePriority('高')).toBe('high');
      expect(parsePriority('紧急')).toBe('urgent');
    });

    it('should parse shorthand priority values', () => {
      expect(parsePriority('l')).toBe('low');
      expect(parsePriority('m')).toBe('medium');
      expect(parsePriority('h')).toBe('high');
      expect(parsePriority('u')).toBe('urgent');
    });

    it('should return null for invalid values', () => {
      expect(parsePriority('invalid')).toBeNull();
      expect(parsePriority('')).toBeNull();
      expect(parsePriority(null)).toBeNull();
    });
  });


  describe('parseAnnotationType', () => {
    it('should parse valid annotation types', () => {
      expect(parseAnnotationType('text_classification')).toBe('text_classification');
      expect(parseAnnotationType('ner')).toBe('ner');
      expect(parseAnnotationType('sentiment')).toBe('sentiment');
      expect(parseAnnotationType('qa')).toBe('qa');
      expect(parseAnnotationType('custom')).toBe('custom');
    });

    it('should parse Chinese annotation types', () => {
      expect(parseAnnotationType('文本分类')).toBe('text_classification');
      expect(parseAnnotationType('命名实体识别')).toBe('ner');
      expect(parseAnnotationType('情感分析')).toBe('sentiment');
      expect(parseAnnotationType('问答')).toBe('qa');
      expect(parseAnnotationType('自定义')).toBe('custom');
    });

    it('should parse alternative formats', () => {
      expect(parseAnnotationType('text classification')).toBe('text_classification');
      expect(parseAnnotationType('named entity recognition')).toBe('ner');
      expect(parseAnnotationType('sentiment analysis')).toBe('sentiment');
    });

    it('should return null for invalid values', () => {
      expect(parseAnnotationType('invalid')).toBeNull();
      expect(parseAnnotationType('')).toBeNull();
    });
  });

  describe('parseDate', () => {
    it('should parse ISO date strings', () => {
      const result = parseDate('2024-12-31');
      expect(result).toBeTruthy();
      expect(new Date(result!).getFullYear()).toBe(2024);
    });

    it('should parse various date formats', () => {
      expect(parseDate('2024/12/31')).toBeTruthy();
      expect(parseDate('Dec 31, 2024')).toBeTruthy();
    });

    it('should return null for invalid dates', () => {
      expect(parseDate('invalid')).toBeNull();
      expect(parseDate('')).toBeNull();
      expect(parseDate(null)).toBeNull();
    });
  });

  describe('parseTags', () => {
    it('should parse comma-separated tags', () => {
      expect(parseTags('tag1,tag2,tag3')).toEqual(['tag1', 'tag2', 'tag3']);
    });

    it('should trim whitespace', () => {
      expect(parseTags(' tag1 , tag2 , tag3 ')).toEqual(['tag1', 'tag2', 'tag3']);
    });

    it('should handle arrays', () => {
      expect(parseTags(['tag1', 'tag2'])).toEqual(['tag1', 'tag2']);
    });

    it('should filter empty values', () => {
      expect(parseTags('tag1,,tag2,')).toEqual(['tag1', 'tag2']);
    });

    it('should return empty array for null/undefined', () => {
      expect(parseTags(null)).toEqual([]);
      expect(parseTags(undefined)).toEqual([]);
      expect(parseTags('')).toEqual([]);
    });
  });


  describe('parseCSVContent', () => {
    it('should parse simple CSV', () => {
      const csv = 'name,priority\nTask 1,high\nTask 2,low';
      const result = parseCSVContent(csv);
      expect(result).toHaveLength(3);
      expect(result[0]).toEqual(['name', 'priority']);
      expect(result[1]).toEqual(['Task 1', 'high']);
    });

    it('should handle quoted values with commas', () => {
      const csv = 'name,description\n"Task 1","Description, with comma"';
      const result = parseCSVContent(csv);
      expect(result[1][1]).toBe('Description, with comma');
    });

    it('should handle escaped quotes', () => {
      const csv = 'name,description\n"Task 1","Say ""Hello"""';
      const result = parseCSVContent(csv);
      expect(result[1][1]).toBe('Say "Hello"');
    });

    it('should handle empty lines', () => {
      const csv = 'name\nTask 1\n\nTask 2';
      const result = parseCSVContent(csv);
      expect(result).toHaveLength(3);
    });
  });

  describe('importTasksFromCSV', () => {
    it('should import valid CSV data', () => {
      const csv = 'name,priority,annotation_type\nTask 1,high,ner\nTask 2,low,sentiment';
      const result = importTasksFromCSV(csv);
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
      expect(result.data[0].name).toBe('Task 1');
      expect(result.data[0].priority).toBe('high');
      expect(result.data[0].annotation_type).toBe('ner');
    });

    it('should use default values for missing fields', () => {
      const csv = 'name\nTask 1';
      const result = importTasksFromCSV(csv);
      
      expect(result.success).toBe(true);
      expect(result.data[0].priority).toBe('medium');
      expect(result.data[0].annotation_type).toBe('text_classification');
    });

    it('should report errors for missing required fields', () => {
      const csv = 'priority\nhigh';
      const result = importTasksFromCSV(csv);
      
      expect(result.invalidRows).toBe(1);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should handle Chinese headers', () => {
      const csv = '任务名称,优先级,标注类型\n测试任务,高,文本分类';
      const result = importTasksFromCSV(csv);
      
      expect(result.success).toBe(true);
      expect(result.data[0].name).toBe('测试任务');
      expect(result.data[0].priority).toBe('high');
    });

    it('should respect maxRows option', () => {
      const csv = 'name\nTask 1\nTask 2\nTask 3\nTask 4\nTask 5';
      const result = importTasksFromCSV(csv, { maxRows: 2 });
      
      expect(result.data).toHaveLength(2);
      expect(result.warnings.length).toBeGreaterThan(0);
    });
  });


  describe('importTasksFromJSON', () => {
    it('should import array of tasks', () => {
      const json = JSON.stringify([
        { name: 'Task 1', priority: 'high', annotation_type: 'ner' },
        { name: 'Task 2', priority: 'low', annotation_type: 'sentiment' },
      ]);
      const result = importTasksFromJSON(json);
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
    });

    it('should import object with tasks array', () => {
      const json = JSON.stringify({
        tasks: [{ name: 'Task 1', priority: 'high' }],
      });
      const result = importTasksFromJSON(json);
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1);
    });

    it('should import single task object', () => {
      const json = JSON.stringify({ name: 'Task 1', priority: 'high' });
      const result = importTasksFromJSON(json);
      
      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1);
    });

    it('should report error for invalid JSON', () => {
      const result = importTasksFromJSON('invalid json');
      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('detectFileType', () => {
    it('should detect CSV files', () => {
      expect(detectFileType('data.csv')).toBe('csv');
      expect(detectFileType('DATA.CSV')).toBe('csv');
    });

    it('should detect JSON files', () => {
      expect(detectFileType('data.json')).toBe('json');
    });

    it('should detect Excel files', () => {
      expect(detectFileType('data.xlsx')).toBe('excel');
      expect(detectFileType('data.xls')).toBe('excel');
    });

    it('should return unknown for unsupported formats', () => {
      expect(detectFileType('data.txt')).toBe('unknown');
      expect(detectFileType('data.pdf')).toBe('unknown');
    });
  });

  describe('generateCSVTemplate', () => {
    it('should generate valid CSV template', () => {
      const template = generateCSVTemplate();
      expect(template).toContain('Task Name');
      expect(template).toContain('Priority');
      expect(template).toContain('Sample Task 1');
    });
  });

  describe('validateImportResult', () => {
    it('should validate successful import', () => {
      const result = {
        success: true,
        data: [{ name: 'Task', priority: 'high' as const, annotation_type: 'ner' as const }],
        errors: [],
        warnings: [],
        totalRows: 1,
        validRows: 1,
        invalidRows: 0,
      };
      expect(validateImportResult(result)).toBe(true);
    });

    it('should reject empty data', () => {
      const result = {
        success: true,
        data: [],
        errors: [],
        warnings: [],
        totalRows: 0,
        validRows: 0,
        invalidRows: 0,
      };
      expect(validateImportResult(result)).toBe(false);
    });
  });
});
