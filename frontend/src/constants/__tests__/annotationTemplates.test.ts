/**
 * Unit tests for annotation templates
 */
import { describe, it, expect } from 'vitest';
import {
  getAnnotationTemplate,
  generateClassificationTemplate,
  generateNERTemplate,
  generateSentimentTemplate,
  TEXT_CLASSIFICATION_TEMPLATE,
  NER_TEMPLATE,
  SENTIMENT_TEMPLATE,
  QA_TEMPLATE,
  CUSTOM_TEMPLATE,
} from '../annotationTemplates';

describe('annotationTemplates', () => {
  describe('getAnnotationTemplate', () => {
    it('should return text classification template for text_classification type', () => {
      const template = getAnnotationTemplate('text_classification');
      expect(template).toBe(TEXT_CLASSIFICATION_TEMPLATE);
      expect(template).toContain('<Choices');
      expect(template).toContain('toName="text"');
    });

    it('should return NER template for ner type', () => {
      const template = getAnnotationTemplate('ner');
      expect(template).toBe(NER_TEMPLATE);
      expect(template).toContain('<Labels');
      expect(template).toContain('Person');
      expect(template).toContain('Organization');
    });

    it('should return sentiment template for sentiment type', () => {
      const template = getAnnotationTemplate('sentiment');
      expect(template).toBe(SENTIMENT_TEMPLATE);
      expect(template).toContain('Very Positive');
      expect(template).toContain('Very Negative');
    });

    it('should return QA template for qa type', () => {
      const template = getAnnotationTemplate('qa');
      expect(template).toBe(QA_TEMPLATE);
      expect(template).toContain('<TextArea');
      expect(template).toContain('question');
      expect(template).toContain('answer');
    });

    it('should return custom template for custom type', () => {
      const template = getAnnotationTemplate('custom');
      expect(template).toBe(CUSTOM_TEMPLATE);
      expect(template).toContain('<TextArea');
    });

    it('should return custom template for unknown type', () => {
      // @ts-expect-error Testing unknown type
      const template = getAnnotationTemplate('unknown');
      expect(template).toBe(CUSTOM_TEMPLATE);
    });
  });

  describe('generateClassificationTemplate', () => {
    it('should generate template with provided categories', () => {
      const categories = ['Category A', 'Category B', 'Category C'];
      const template = generateClassificationTemplate(categories);
      
      expect(template).toContain('Category A');
      expect(template).toContain('Category B');
      expect(template).toContain('Category C');
      expect(template).toContain('choice="single-radio"');
    });

    it('should generate multi-label template when multiLabel is true', () => {
      const categories = ['Tag1', 'Tag2'];
      const template = generateClassificationTemplate(categories, true);
      
      expect(template).toContain('choice="multiple"');
      expect(template).toContain('Tag1');
      expect(template).toContain('Tag2');
    });

    it('should generate single-radio template when multiLabel is false', () => {
      const categories = ['Option1', 'Option2'];
      const template = generateClassificationTemplate(categories, false);
      
      expect(template).toContain('choice="single-radio"');
    });
  });

  describe('generateNERTemplate', () => {
    it('should generate template with provided entity types', () => {
      const entityTypes = ['Product', 'Brand', 'Price'];
      const template = generateNERTemplate(entityTypes);
      
      expect(template).toContain('Product');
      expect(template).toContain('Brand');
      expect(template).toContain('Price');
      expect(template).toContain('<Labels');
    });

    it('should assign different colors to entity types', () => {
      const entityTypes = ['Entity1', 'Entity2', 'Entity3'];
      const template = generateNERTemplate(entityTypes);
      
      expect(template).toContain('background="red"');
      expect(template).toContain('background="blue"');
      expect(template).toContain('background="green"');
    });

    it('should cycle colors for more than 8 entity types', () => {
      const entityTypes = Array.from({ length: 10 }, (_, i) => `Entity${i + 1}`);
      const template = generateNERTemplate(entityTypes);
      
      // Should contain all entities
      entityTypes.forEach(entity => {
        expect(template).toContain(entity);
      });
    });
  });

  describe('generateSentimentTemplate', () => {
    it('should generate binary scale template', () => {
      const template = generateSentimentTemplate('binary');
      
      expect(template).toContain('Positive');
      expect(template).toContain('Negative');
      expect(template).not.toContain('Neutral');
      expect(template).not.toContain('Very');
    });

    it('should generate ternary scale template', () => {
      const template = generateSentimentTemplate('ternary');
      
      expect(template).toContain('Positive');
      expect(template).toContain('Neutral');
      expect(template).toContain('Negative');
      expect(template).not.toContain('Very');
    });

    it('should generate five-point scale template', () => {
      const template = generateSentimentTemplate('five_point');
      
      expect(template).toContain('Very Positive');
      expect(template).toContain('Positive');
      expect(template).toContain('Neutral');
      expect(template).toContain('Negative');
      expect(template).toContain('Very Negative');
    });
  });

  describe('template structure validation', () => {
    it('all templates should have valid XML structure', () => {
      const templates = [
        TEXT_CLASSIFICATION_TEMPLATE,
        NER_TEMPLATE,
        SENTIMENT_TEMPLATE,
        QA_TEMPLATE,
        CUSTOM_TEMPLATE,
      ];

      templates.forEach(template => {
        expect(template).toContain('<View>');
        expect(template).toContain('</View>');
        expect(template).toContain('name=');
      });
    });

    it('all templates should reference $text data field', () => {
      const templates = [
        TEXT_CLASSIFICATION_TEMPLATE,
        NER_TEMPLATE,
        SENTIMENT_TEMPLATE,
        QA_TEMPLATE,
        CUSTOM_TEMPLATE,
      ];

      templates.forEach(template => {
        expect(template).toContain('$text');
      });
    });
  });
});
