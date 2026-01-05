/**
 * DataTransformer 单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import DataTransformer, {
  DataFormat,
  TransformationConfig,
  TransformationRule,
  ValidationRule,
  TransformationMappingRule,
  DataIntegrityCheck,
  DataValidator,
  DataMapper,
  CommonValidators,
  CommonTransformers,
  ValidationSchema,
  MappingRule
} from './DataTransformer';

describe('DataTransformer', () => {
  let transformer: DataTransformer;

  beforeEach(() => {
    transformer = new DataTransformer({
      enableLogging: false,
      maxFileSize: 1024 * 1024,
      timeout: 5000
    });
  });

  describe('基本转换功能', () => {
    it('应该成功转换 JSON 到 JSON', async () => {
      const data = { name: 'test', value: 123 };
      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: []
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.transformedCount).toBe(1);
    });

    it('应该成功转换 JSON 到 CSV', async () => {
      const data = [
        { name: 'Alice', age: 30, city: 'New York' },
        { name: 'Bob', age: 25, city: 'Los Angeles' }
      ];

      const result = await transformer.transformToCSV(data, DataFormat.JSON);

      expect(result.success).toBe(true);
      expect(result.data).toContain('name,age,city');
      expect(result.data).toContain('Alice,30,New York');
      expect(result.data).toContain('Bob,25,Los Angeles');
    });

    it('应该成功转换 CSV 到 JSON', async () => {
      const csvData = 'name,age,city\nAlice,30,New York\nBob,25,Los Angeles';

      const result = await transformer.transformToJSON(csvData, DataFormat.CSV);

      expect(result.success).toBe(true);
      const parsedData = JSON.parse(result.data);
      expect(Array.isArray(parsedData)).toBe(true);
      expect(parsedData).toHaveLength(2);
      expect(parsedData[0]).toEqual({ name: 'Alice', age: '30', city: 'New York' });
    });

    it('应该成功转换 JSON 到 XML', async () => {
      const data = { user: { name: 'Alice', age: 30 } };

      const result = await transformer.transformToXML(data, DataFormat.JSON, 'users');

      expect(result.success).toBe(true);
      expect(result.data).toContain('<?xml version="1.0" encoding="UTF-8"?>');
      expect(result.data).toContain('<users>');
      expect(result.data).toContain('<user>');
      expect(result.data).toContain('<name>Alice</name>');
    });
  });

  describe('转换规则应用', () => {
    it('应该正确应用字段映射规则', async () => {
      const data = { oldName: 'test', oldValue: 123 };
      const rules: TransformationRule[] = [
        { sourceField: 'oldName', targetField: 'newName' },
        { sourceField: 'oldValue', targetField: 'newValue' }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult).toEqual({ newName: 'test', newValue: 123 });
    });

    it('应该正确应用转换函数', async () => {
      const data = { name: '  ALICE  ', age: '30' };
      const rules: TransformationRule[] = [
        {
          sourceField: 'name',
          targetField: 'name',
          transform: (value: string) => value.trim().toLowerCase()
        },
        {
          sourceField: 'age',
          targetField: 'age',
          transform: (value: string) => parseInt(value, 10)
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult.name).toBe('alice');
      expect(parsedResult.age).toBe(30);
    });

    it('应该正确处理默认值', async () => {
      const data = { name: 'test' };
      const rules: TransformationRule[] = [
        { sourceField: 'name', targetField: 'name' },
        { sourceField: 'missing', targetField: 'value', defaultValue: 'default' }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult.value).toBe('default');
    });

    it('应该正确处理必填字段验证', async () => {
      const data = { name: 'test' };
      const rules: TransformationRule[] = [
        { sourceField: 'name', targetField: 'name' },
        { sourceField: 'required', targetField: 'required', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('必填字段缺失: required');
    });
  });

  describe('数据验证', () => {
    it('应该正确验证数据类型', async () => {
      const data = { name: 'test', age: 30 };
      const validationRules: ValidationRule[] = [
        { field: 'name', type: 'string', required: true },
        { field: 'age', type: 'number', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [
          { sourceField: 'name', targetField: 'name' },
          { sourceField: 'age', targetField: 'age' }
        ],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
    });

    it('应该检测数据类型错误', async () => {
      const data = { name: 123, age: 'thirty' };
      const validationRules: ValidationRule[] = [
        { field: 'name', type: 'string', required: true },
        { field: 'age', type: 'number', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [
          { sourceField: 'name', targetField: 'name' },
          { sourceField: 'age', targetField: 'age' }
        ],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段类型错误 name: 期望 string, 实际 number');
      expect(result.errors).toContain('字段类型错误 age: 期望 number, 实际 string');
    });

    it('应该验证字符串长度', async () => {
      const data = { name: 'ab', description: 'a'.repeat(101) };
      const validationRules: ValidationRule[] = [
        { field: 'name', type: 'string', minLength: 3 },
        { field: 'description', type: 'string', maxLength: 100 }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [
          { sourceField: 'name', targetField: 'name' },
          { sourceField: 'description', targetField: 'description' }
        ],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段长度不足 name: 最小长度 3');
      expect(result.errors).toContain('字段长度超限 description: 最大长度 100');
    });

    it('应该验证正则表达式模式', async () => {
      const data = { email: 'invalid-email' };
      const validationRules: ValidationRule[] = [
        {
          field: 'email',
          type: 'string',
          pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'email', targetField: 'email' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段格式错误 email: 不匹配模式 /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/');
    });

    it('应该执行自定义验证器', async () => {
      const data = { age: 15 };
      const validationRules: ValidationRule[] = [
        {
          field: 'age',
          type: 'number',
          validator: (value: number) => value >= 18
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'age', targetField: 'age' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段验证失败 age: 自定义验证器返回 false');
    });
  });

  describe('错误处理', () => {
    it('应该处理空数据', async () => {
      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: []
      };

      const result = await transformer.transform(null, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('输入数据不能为空');
    });

    it('应该处理不支持的数据格式', async () => {
      const data = { test: 'data' };
      const config: TransformationConfig = {
        sourceFormat: 'unsupported' as DataFormat,
        targetFormat: DataFormat.JSON,
        rules: []
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('不支持的源数据格式: unsupported');
    });

    it('应该处理转换函数异常', async () => {
      const data = { value: 'test' };
      const rules: TransformationRule[] = [
        {
          sourceField: 'value',
          targetField: 'value',
          transform: () => {
            throw new Error('转换失败');
          }
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段转换失败 value: Error: 转换失败');
    });
  });

  describe('CSV 解析和格式化', () => {
    it('应该正确解析 CSV 数据', async () => {
      const csvData = 'name,age,city\nAlice,30,New York\nBob,25,Los Angeles';
      const result = await transformer.transformToJSON(csvData, DataFormat.CSV);

      expect(result.success).toBe(true);
      const parsedData = JSON.parse(result.data);
      expect(Array.isArray(parsedData)).toBe(true);
      expect(parsedData).toHaveLength(2);
      expect(parsedData[0]).toEqual({ name: 'Alice', age: '30', city: 'New York' });
      expect(parsedData[1]).toEqual({ name: 'Bob', age: '25', city: 'Los Angeles' });
    });

    it('应该正确格式化 CSV 数据', async () => {
      const data = [
        { name: 'Alice', age: 30, city: 'New York' },
        { name: 'Bob', age: 25, city: 'Los Angeles' }
      ];

      const result = await transformer.transformToCSV(data, DataFormat.JSON);

      expect(result.success).toBe(true);
      expect(result.data).toBe('name,age,city\nAlice,30,New York\nBob,25,Los Angeles');
    });

    it('应该处理空 CSV 数据', async () => {
      const result = await transformer.transformToJSON('', DataFormat.CSV);

      expect(result.success).toBe(true);
      expect(result.data).toBe('[]');
    });

    it('应该支持自定义分隔符', async () => {
      const data = [{ name: 'Alice', age: 30 }];
      const result = await transformer.transformToCSV(data, DataFormat.JSON, '\t');

      expect(result.success).toBe(true);
      expect(result.data).toBe('name\tage\nAlice\t30');
    });
  });

  describe('XML 解析和格式化', () => {
    it('应该正确解析简单 XML', async () => {
      const xmlData = '<user><name>Alice</name><age>30</age></user>';
      const result = await transformer.transformToJSON(xmlData, DataFormat.XML);

      expect(result.success).toBe(true);
      const parsedData = JSON.parse(result.data);
      
      // The XML parser parses the root element directly
      expect(parsedData.name).toBeDefined();
      expect(parsedData.name['#text']).toBe('Alice');
      expect(parsedData.age).toBeDefined();
      expect(parsedData.age['#text']).toBe('30');
    });

    it('应该正确格式化 XML', async () => {
      const data = { user: { name: 'Alice', age: 30 } };
      const result = await transformer.transformToXML(data, DataFormat.JSON, 'root');

      expect(result.success).toBe(true);
      expect(result.data).toContain('<?xml version="1.0" encoding="UTF-8"?>');
      expect(result.data).toContain('<root>');
      expect(result.data).toContain('<user>');
      expect(result.data).toContain('<name>Alice</name>');
      expect(result.data).toContain('<age>30</age>');
    });
  });

  describe('转换历史', () => {
    it('应该记录转换历史', async () => {
      const data = { test: 'data' };
      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: []
      };

      await transformer.transform(data, config);
      const history = transformer.getTransformationHistory();

      expect(history).toHaveLength(1);
      expect(history[0].config).toEqual(config);
      expect(history[0].result.success).toBe(true);
      expect(history[0].timestamp).toBeTypeOf('number');
    });

    it('应该清除转换历史', async () => {
      const data = { test: 'data' };
      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: []
      };

      await transformer.transform(data, config);
      expect(transformer.getTransformationHistory()).toHaveLength(1);

      transformer.clearHistory();
      expect(transformer.getTransformationHistory()).toHaveLength(0);
    });
  });

  describe('映射规则', () => {
    it('应该应用简单映射规则', async () => {
      const data = { oldField: 'value', anotherField: 'test' };
      const mappingRules: TransformationMappingRule[] = [
        { sourceField: 'oldField', targetField: 'newField' },
        { sourceField: 'anotherField', targetField: 'renamedField' }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        mappingRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult.newField).toBe('value');
      expect(parsedResult.renamedField).toBe('test');
    });

    it('应该应用条件映射规则', async () => {
      const data = [
        { type: 'user', name: 'Alice', age: 30 },
        { type: 'admin', name: 'Bob', role: 'administrator' }
      ];

      const mappingRules: TransformationMappingRule[] = [
        {
          sourceField: 'name',
          targetField: 'userName',
          condition: (value, item) => item.type === 'user'
        },
        {
          sourceField: 'name',
          targetField: 'adminName',
          condition: (value, item) => item.type === 'admin'
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        mappingRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult[0].userName).toBe('Alice');
      expect(parsedResult[0].adminName).toBeUndefined();
      expect(parsedResult[1].adminName).toBe('Bob');
      expect(parsedResult[1].userName).toBeUndefined();
    });

    it('应该按优先级排序映射规则', async () => {
      const data = { field: 'original' };
      const mappingRules: TransformationMappingRule[] = [
        { sourceField: 'field', targetField: 'result', priority: 1 },
        { sourceField: 'field', targetField: 'result', priority: 2 }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        mappingRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      const parsedResult = JSON.parse(result.data);
      expect(parsedResult.result).toBe('original');
    });
  });

  describe('数据完整性检查', () => {
    it('应该执行非空检查', async () => {
      const data: any[] = [];
      const integrityChecks: DataIntegrityCheck[] = [
        {
          name: 'notEmpty',
          check: (data: any) => Array.isArray(data) ? data.length > 0 : data !== null && data !== undefined,
          errorMessage: '数据不能为空',
          severity: 'error'
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        integrityChecks,
        strictMode: true
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('数据不能为空');
    });

    it('应该执行唯一性检查', async () => {
      const data = [
        { id: 1, name: 'Alice' },
        { id: 1, name: 'Bob' }
      ];

      const integrityChecks: DataIntegrityCheck[] = [
        {
          name: 'uniqueId',
          check: (data: any) => {
            if (!Array.isArray(data)) return true;
            const ids = data.map(item => item.id);
            return ids.length === new Set(ids).size;
          },
          errorMessage: 'ID 字段存在重复值',
          severity: 'error'
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        integrityChecks,
        strictMode: true
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('ID 字段存在重复值');
    });

    it('应该在非严格模式下继续处理警告', async () => {
      const data = [{ name: 'Alice' }];
      const integrityChecks: DataIntegrityCheck[] = [
        {
          name: 'minCount',
          check: (data: any) => Array.isArray(data) ? data.length >= 2 : true,
          errorMessage: '数据项数量不足',
          severity: 'warning'
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [],
        integrityChecks,
        strictMode: false
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
      expect(result.warnings).toContain('数据项数量不足');
    });
  });

  describe('增强验证功能', () => {
    it('应该验证邮箱类型', async () => {
      const data = { email: 'test@example.com' };
      const validationRules: ValidationRule[] = [
        { field: 'email', type: 'email', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'email', targetField: 'email' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
    });

    it('应该验证 URL 类型', async () => {
      const data = { website: 'https://example.com' };
      const validationRules: ValidationRule[] = [
        { field: 'website', type: 'url', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'website', targetField: 'website' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
    });

    it('应该验证日期类型', async () => {
      const data = { birthDate: '1990-01-01' };
      const validationRules: ValidationRule[] = [
        { field: 'birthDate', type: 'date', required: true }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'birthDate', targetField: 'birthDate' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
    });

    it('应该验证数值范围', async () => {
      const data = { age: 25, score: 85 };
      const validationRules: ValidationRule[] = [
        { field: 'age', type: 'number', min: 18, max: 65 },
        { field: 'score', type: 'number', min: 0, max: 100 }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [
          { sourceField: 'age', targetField: 'age' },
          { sourceField: 'score', targetField: 'score' }
        ],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(true);
    });

    it('应该使用自定义错误消息', async () => {
      const data = { password: '123' };
      const validationRules: ValidationRule[] = [
        {
          field: 'password',
          type: 'string',
          minLength: 8,
          errorMessage: '密码长度至少需要8位字符'
        }
      ];

      const config: TransformationConfig = {
        sourceFormat: DataFormat.JSON,
        targetFormat: DataFormat.JSON,
        rules: [{ sourceField: 'password', targetField: 'password' }],
        validationRules
      };

      const result = await transformer.transform(data, config);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('密码长度至少需要8位字符');
    });
  });

  describe('静态工厂方法', () => {
    it('应该创建验证规则', () => {
      const rules = DataTransformer.createValidationRules();

      const requiredRule = rules.required('name', '姓名是必填项');
      expect(requiredRule.field).toBe('name');
      expect(requiredRule.required).toBe(true);
      expect(requiredRule.errorMessage).toBe('姓名是必填项');

      const emailRule = rules.email('email', true);
      expect(emailRule.field).toBe('email');
      expect(emailRule.type).toBe('email');
      expect(emailRule.required).toBe(true);

      const lengthRule = rules.stringLength('description', 10, 100);
      expect(lengthRule.minLength).toBe(10);
      expect(lengthRule.maxLength).toBe(100);
    });

    it('应该创建映射规则', () => {
      const rules = DataTransformer.createMappingRules();

      const simpleRule = rules.simple('oldField', 'newField', 1);
      expect(simpleRule.sourceField).toBe('oldField');
      expect(simpleRule.targetField).toBe('newField');
      expect(simpleRule.priority).toBe(1);

      const conditionalRule = rules.conditional('field', 'target', (value) => value !== null);
      expect(conditionalRule.condition).toBeDefined();

      const renameRule = rules.rename('old', 'new');
      expect(renameRule.sourceField).toBe('old');
      expect(renameRule.targetField).toBe('new');
    });

    it('应该创建完整性检查', () => {
      const checks = DataTransformer.createIntegrityChecks();

      const notEmptyCheck = checks.notEmpty('数据不能为空');
      expect(notEmptyCheck.name).toBe('notEmpty');
      expect(notEmptyCheck.errorMessage).toBe('数据不能为空');
      expect(notEmptyCheck.severity).toBe('error');

      const uniqueCheck = checks.uniqueField('id');
      expect(uniqueCheck.name).toBe('uniqueField_id');
      expect(uniqueCheck.severity).toBe('error');

      const minCountCheck = checks.minCount(5);
      expect(minCountCheck.name).toBe('minCount');
      expect(minCountCheck.severity).toBe('warning');
    });
  });
});

describe('DataValidator', () => {
  let validator: DataValidator;

  beforeEach(() => {
    validator = new DataValidator();
  });

  describe('数据完整性验证', () => {
    it('应该验证单个数据项', () => {
      const data = { name: 'Alice', age: 30, email: 'alice@example.com' };
      const schema: ValidationSchema = {
        rules: [
          { field: 'name', type: 'string', required: true, minLength: 2 },
          { field: 'age', type: 'number', required: true, min: 0, max: 120 },
          { field: 'email', type: 'string', pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.validatedCount).toBe(1);
    });

    it('应该验证数组数据', () => {
      const data = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 }
      ];
      const schema: ValidationSchema = {
        rules: [
          { field: 'name', type: 'string', required: true },
          { field: 'age', type: 'number', required: true }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(true);
      expect(result.validatedCount).toBe(2);
    });

    it('应该检测验证错误', () => {
      const data = { name: '', age: -5, email: 'invalid' };
      const schema: ValidationSchema = {
        rules: [
          { field: 'name', type: 'string', required: true, minLength: 1 },
          { field: 'age', type: 'number', min: 0 },
          { field: 'email', type: 'string', pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段长度不足 name: 最小长度 1');
      expect(result.errors).toContain('数值过小 age: 最小值 0');
      expect(result.errors).toContain('字段格式错误 email: 不匹配模式 /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/');
    });

    it('应该支持自定义验证器', () => {
      validator.registerValidator('adult', (age: number) => age >= 18);

      const data = { age: 16 };
      const schema: ValidationSchema = {
        rules: [
          { field: 'age', type: 'number', customValidator: 'adult' }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段验证失败 age: 自定义验证器 adult 返回 false');
    });

    it('应该支持枚举值验证', () => {
      const data = { status: 'invalid' };
      const schema: ValidationSchema = {
        rules: [
          { field: 'status', type: 'string', enum: ['active', 'inactive', 'pending'] }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('字段值不在允许范围内 status: 允许值 [active, inactive, pending]');
    });

    it('应该生成废弃字段警告', () => {
      const data = { oldField: 'value' };
      const schema: ValidationSchema = {
        rules: [
          { field: 'oldField', type: 'string', deprecated: true, deprecatedMessage: '请使用 newField' }
        ]
      };

      const result = validator.validateDataIntegrity(data, schema);

      expect(result.success).toBe(true);
      expect(result.warnings).toContain('字段已废弃 oldField: 请使用 newField');
    });
  });
});

describe('DataMapper', () => {
  let mapper: DataMapper;

  beforeEach(() => {
    mapper = new DataMapper();
  });

  describe('数据映射', () => {
    it('应该应用字段映射', () => {
      const rule: MappingRule = {
        fieldMappings: {
          'old_name': 'name',
          'old_age': 'age'
        }
      };

      mapper.registerMappingRule('userMapping', rule);

      const data = { old_name: 'Alice', old_age: 30 };
      const result = mapper.applyMapping(data, 'userMapping');

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ name: 'Alice', age: 30 });
    });

    it('应该应用转换函数', () => {
      const rule: MappingRule = {
        fieldMappings: {
          'name': 'name',
          'age': 'age'
        },
        transformations: {
          'name': (value: string) => value.toUpperCase(),
          'age': (value: number) => value * 2
        }
      };

      mapper.registerMappingRule('transformMapping', rule);

      const data = { name: 'alice', age: 15 };
      const result = mapper.applyMapping(data, 'transformMapping');

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ name: 'ALICE', age: 30 });
    });

    it('应该应用默认值', () => {
      const rule: MappingRule = {
        fieldMappings: {
          'name': 'name'
        },
        defaults: {
          'age': 0,
          'status': 'active'
        }
      };

      mapper.registerMappingRule('defaultMapping', rule);

      const data = { name: 'Alice' };
      const result = mapper.applyMapping(data, 'defaultMapping');

      expect(result.success).toBe(true);
      expect(result.data).toEqual({ name: 'Alice', age: 0, status: 'active' });
    });

    it('应该应用计算字段', () => {
      const rule: MappingRule = {
        fieldMappings: {
          'firstName': 'firstName',
          'lastName': 'lastName'
        },
        computedFields: {
          'fullName': (mapped: any) => `${mapped.firstName} ${mapped.lastName}`,
          'initials': (mapped: any) => `${mapped.firstName[0]}${mapped.lastName[0]}`
        }
      };

      mapper.registerMappingRule('computedMapping', rule);

      const data = { firstName: 'Alice', lastName: 'Smith' };
      const result = mapper.applyMapping(data, 'computedMapping');

      expect(result.success).toBe(true);
      expect(result.data).toEqual({
        firstName: 'Alice',
        lastName: 'Smith',
        fullName: 'Alice Smith',
        initials: 'AS'
      });
    });

    it('应该处理数组数据', () => {
      const rule: MappingRule = {
        fieldMappings: {
          'old_name': 'name'
        }
      };

      mapper.registerMappingRule('arrayMapping', rule);

      const data = [
        { old_name: 'Alice' },
        { old_name: 'Bob' }
      ];
      const result = mapper.applyMapping(data, 'arrayMapping');

      expect(result.success).toBe(true);
      expect(result.data).toEqual([
        { name: 'Alice' },
        { name: 'Bob' }
      ]);
      expect(result.mappedCount).toBe(2);
    });

    it('应该处理不存在的映射规则', () => {
      const data = { test: 'data' };
      const result = mapper.applyMapping(data, 'nonexistent');

      expect(result.success).toBe(false);
      expect(result.errors).toContain('映射规则不存在: nonexistent');
    });
  });
});

describe('CommonValidators', () => {
  it('应该验证邮箱格式', () => {
    expect(CommonValidators.email('test@example.com')).toBe(true);
    expect(CommonValidators.email('invalid-email')).toBe(false);
  });

  it('应该验证电话号码格式', () => {
    expect(CommonValidators.phone('+1234567890')).toBe(true);
    expect(CommonValidators.phone('1234567890')).toBe(true);
    expect(CommonValidators.phone('invalid-phone')).toBe(false);
  });

  it('应该验证 URL 格式', () => {
    expect(CommonValidators.url('https://example.com')).toBe(true);
    expect(CommonValidators.url('invalid-url')).toBe(false);
  });

  it('应该验证 UUID 格式', () => {
    expect(CommonValidators.uuid('123e4567-e89b-12d3-a456-426614174000')).toBe(true);
    expect(CommonValidators.uuid('invalid-uuid')).toBe(false);
  });

  it('应该验证 IPv4 格式', () => {
    expect(CommonValidators.ipv4('192.168.1.1')).toBe(true);
    expect(CommonValidators.ipv4('256.256.256.256')).toBe(false);
  });

  it('应该验证正数', () => {
    expect(CommonValidators.positiveNumber(5)).toBe(true);
    expect(CommonValidators.positiveNumber(0)).toBe(false);
    expect(CommonValidators.positiveNumber(-5)).toBe(false);
  });

  it('应该验证非空字符串', () => {
    expect(CommonValidators.nonEmptyString('test')).toBe(true);
    expect(CommonValidators.nonEmptyString('')).toBe(false);
    expect(CommonValidators.nonEmptyString('   ')).toBe(false);
  });
});

describe('CommonTransformers', () => {
  it('应该修剪字符串', () => {
    expect(CommonTransformers.trim('  test  ')).toBe('test');
    expect(CommonTransformers.trim(123)).toBe(123);
  });

  it('应该转换为小写', () => {
    expect(CommonTransformers.toLowerCase('TEST')).toBe('test');
    expect(CommonTransformers.toLowerCase(123)).toBe(123);
  });

  it('应该转换为大写', () => {
    expect(CommonTransformers.toUpperCase('test')).toBe('TEST');
    expect(CommonTransformers.toUpperCase(123)).toBe(123);
  });

  it('应该转换为数字', () => {
    expect(CommonTransformers.toNumber('123')).toBe(123);
    expect(CommonTransformers.toNumber('invalid')).toBe('invalid');
  });

  it('应该转换为字符串', () => {
    expect(CommonTransformers.toString(123)).toBe('123');
    expect(CommonTransformers.toString(true)).toBe('true');
  });

  it('应该移除空格', () => {
    expect(CommonTransformers.removeSpaces('a b c')).toBe('abc');
    expect(CommonTransformers.removeSpaces(123)).toBe(123);
  });

  it('应该首字母大写', () => {
    expect(CommonTransformers.capitalizeFirst('hello')).toBe('Hello');
    expect(CommonTransformers.capitalizeFirst('HELLO')).toBe('Hello');
    expect(CommonTransformers.capitalizeFirst('')).toBe('');
    expect(CommonTransformers.capitalizeFirst(123)).toBe(123);
  });
});