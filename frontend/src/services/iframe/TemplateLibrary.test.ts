/**
 * Template Library Tests
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { TemplateLibrary, TemplateConfig, TemplateCategory } from './TemplateLibrary';

describe('TemplateLibrary', () => {
  let library: TemplateLibrary;

  beforeEach(() => {
    library = new TemplateLibrary();
  });

  describe('Built-in Templates', () => {
    it('should have NER template', () => {
      const template = library.getTemplate('ner-basic');
      expect(template).toBeDefined();
      expect(template?.name).toBe('Named Entity Recognition (NER)');
      expect(template?.category).toBe('nlp');
      expect(template?.xml).toContain('<Labels');
      expect(template?.xml).toContain('PER');
      expect(template?.xml).toContain('ORG');
      expect(template?.xml).toContain('LOC');
    });

    it('should have text classification template', () => {
      const template = library.getTemplate('text-classification');
      expect(template).toBeDefined();
      expect(template?.category).toBe('nlp');
      expect(template?.xml).toContain('<Choices');
    });

    it('should have image bbox template', () => {
      const template = library.getTemplate('image-bbox');
      expect(template).toBeDefined();
      expect(template?.category).toBe('computer_vision');
      expect(template?.xml).toContain('<RectangleLabels');
    });

    it('should have audio transcription template', () => {
      const template = library.getTemplate('audio-transcription');
      expect(template).toBeDefined();
      expect(template?.category).toBe('audio');
      expect(template?.xml).toContain('<Audio');
      expect(template?.xml).toContain('<TextArea');
    });

    it('should have LLM response ranking template', () => {
      const template = library.getTemplate('llm-response-ranking');
      expect(template).toBeDefined();
      expect(template?.category).toBe('llm');
      expect(template?.xml).toContain('Response A');
      expect(template?.xml).toContain('Response B');
    });

    it('should have video classification template', () => {
      const template = library.getTemplate('video-classification');
      expect(template).toBeDefined();
      expect(template?.category).toBe('video');
      expect(template?.xml).toContain('<Video');
    });
  });

  describe('getAllTemplates', () => {
    it('should return all built-in templates', () => {
      const templates = library.getAllTemplates();
      expect(templates.length).toBeGreaterThan(10);
    });

    it('should include templates from all categories', () => {
      const templates = library.getAllTemplates();
      const categories = new Set(templates.map(t => t.category));
      expect(categories.has('nlp')).toBe(true);
      expect(categories.has('computer_vision')).toBe(true);
      expect(categories.has('audio')).toBe(true);
      expect(categories.has('llm')).toBe(true);
    });
  });

  describe('getTemplatesByCategory', () => {
    it('should filter templates by NLP category', () => {
      const templates = library.getTemplatesByCategory('nlp');
      expect(templates.length).toBeGreaterThan(0);
      templates.forEach(t => {
        expect(t.category).toBe('nlp');
      });
    });

    it('should filter templates by computer vision category', () => {
      const templates = library.getTemplatesByCategory('computer_vision');
      expect(templates.length).toBeGreaterThan(0);
      templates.forEach(t => {
        expect(t.category).toBe('computer_vision');
      });
    });

    it('should return empty array for unknown category', () => {
      const templates = library.getTemplatesByCategory('unknown' as TemplateCategory);
      expect(templates.length).toBe(0);
    });
  });

  describe('searchTemplates', () => {
    it('should find templates by name', () => {
      const results = library.searchTemplates('NER');
      expect(results.length).toBeGreaterThan(0);
      expect(results.some(t => t.id === 'ner-basic')).toBe(true);
    });

    it('should find templates by Chinese name', () => {
      const results = library.searchTemplates('命名实体');
      expect(results.length).toBeGreaterThan(0);
    });

    it('should find templates by tag', () => {
      const results = library.searchTemplates('classification');
      expect(results.length).toBeGreaterThan(0);
    });

    it('should find templates by description', () => {
      const results = library.searchTemplates('bounding box');
      expect(results.length).toBeGreaterThan(0);
    });

    it('should return empty array for no matches', () => {
      const results = library.searchTemplates('xyznonexistent');
      expect(results.length).toBe(0);
    });
  });

  describe('getCategories', () => {
    it('should return all categories with names', () => {
      const categories = library.getCategories();
      expect(categories.length).toBeGreaterThan(5);
      
      const nlp = categories.find(c => c.id === 'nlp');
      expect(nlp).toBeDefined();
      expect(nlp?.name).toBe('Natural Language Processing');
      expect(nlp?.nameZh).toBe('自然语言处理');
    });
  });

  describe('Custom Templates', () => {
    it('should register custom template', () => {
      const customTemplate: TemplateConfig = {
        id: 'custom-test',
        name: 'Custom Test Template',
        nameZh: '自定义测试模板',
        category: 'nlp',
        description: 'A custom test template',
        descriptionZh: '自定义测试模板',
        xml: '<View><Text name="text" value="$text"/></View>',
        sampleData: { text: 'Sample' },
        tags: ['custom', 'test'],
        version: '1.0.0',
      };

      library.registerCustomTemplate(customTemplate);
      
      const retrieved = library.getTemplate('custom-test');
      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe('Custom Test Template');
    });

    it('should include custom templates in getAllTemplates', () => {
      const customTemplate: TemplateConfig = {
        id: 'custom-included',
        name: 'Custom Included',
        nameZh: '自定义包含',
        category: 'nlp',
        description: 'Test',
        descriptionZh: '测试',
        xml: '<View/>',
        sampleData: {},
        tags: ['custom'],
        version: '1.0.0',
      };

      const beforeCount = library.getAllTemplates().length;
      library.registerCustomTemplate(customTemplate);
      const afterCount = library.getAllTemplates().length;

      expect(afterCount).toBe(beforeCount + 1);
    });

    it('should throw when custom templates disabled', () => {
      const restrictedLibrary = new TemplateLibrary({ enableCustomTemplates: false });
      
      expect(() => {
        restrictedLibrary.registerCustomTemplate({
          id: 'blocked',
          name: 'Blocked',
          nameZh: '阻止',
          category: 'nlp',
          description: 'Test',
          descriptionZh: '测试',
          xml: '<View/>',
          sampleData: {},
          tags: [],
          version: '1.0.0',
        });
      }).toThrow('Custom templates are disabled');
    });
  });

  describe('customizeTemplate', () => {
    it('should customize template labels', () => {
      const customized = library.customizeTemplate('ner-basic', [
        { value: 'PERSON', background: '#FF0000' },
        { value: 'COMPANY', background: '#00FF00' },
        { value: 'PRODUCT', background: '#0000FF' },
      ]);

      expect(customized).toContain('PERSON');
      expect(customized).toContain('COMPANY');
      expect(customized).toContain('PRODUCT');
      expect(customized).toContain('#FF0000');
    });

    it('should throw for unknown template', () => {
      expect(() => {
        library.customizeTemplate('nonexistent', []);
      }).toThrow('Template not found');
    });
  });

  describe('Export/Import', () => {
    it('should export template as JSON', () => {
      const json = library.exportTemplate('ner-basic');
      const parsed = JSON.parse(json);
      
      expect(parsed.id).toBe('ner-basic');
      expect(parsed.xml).toBeDefined();
    });

    it('should import template from JSON', () => {
      const templateJson = JSON.stringify({
        id: 'imported-template',
        name: 'Imported Template',
        nameZh: '导入模板',
        category: 'nlp',
        description: 'Imported',
        descriptionZh: '导入的',
        xml: '<View/>',
        sampleData: {},
        tags: ['imported'],
        version: '1.0.0',
      });

      const imported = library.importTemplate(templateJson);
      expect(imported.id).toBe('imported-template');
      
      const retrieved = library.getTemplate('imported-template');
      expect(retrieved).toBeDefined();
    });
  });

  describe('Template XML Validity', () => {
    it('all templates should have valid XML structure', () => {
      const templates = library.getAllTemplates();
      
      templates.forEach(template => {
        expect(template.xml).toContain('<View');
        expect(template.xml).toContain('</View>');
        expect(template.xml.match(/<View/g)?.length).toBe(
          template.xml.match(/<\/View>/g)?.length
        );
      });
    });

    it('all templates should have sample data', () => {
      const templates = library.getAllTemplates();
      
      templates.forEach(template => {
        expect(template.sampleData).toBeDefined();
        expect(Object.keys(template.sampleData).length).toBeGreaterThan(0);
      });
    });

    it('all templates should have Chinese translations', () => {
      const templates = library.getAllTemplates();
      
      templates.forEach(template => {
        expect(template.nameZh).toBeDefined();
        expect(template.nameZh.length).toBeGreaterThan(0);
        expect(template.descriptionZh).toBeDefined();
      });
    });
  });
});
