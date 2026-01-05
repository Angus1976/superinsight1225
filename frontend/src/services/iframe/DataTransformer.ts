/**
 * DataTransformer - 数据格式转换器
 * 
 * 支持多种数据格式转换和验证，包括 JSON、CSV、XML 等格式
 * 提供自定义转换规则和映射功能
 */

export interface TransformationRule {
  sourceField: string;
  targetField: string;
  transform?: (value: any) => any;
  required?: boolean;
  defaultValue?: any;
}

export interface ValidationRule {
  field: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'date' | 'email' | 'url';
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  pattern?: RegExp;
  validator?: (value: any) => boolean;
  errorMessage?: string;
}

export interface TransformationMappingRule {
  sourceField: string;
  targetField: string;
  condition?: (value: any, item: any) => boolean;
  priority?: number;
}

export interface DataIntegrityCheck {
  name: string;
  check: (data: any) => boolean;
  errorMessage: string;
  severity: 'error' | 'warning';
}

export interface TransformationConfig {
  sourceFormat: DataFormat;
  targetFormat: DataFormat;
  rules: TransformationRule[];
  validationRules?: ValidationRule[];
  mappingRules?: TransformationMappingRule[];
  integrityChecks?: DataIntegrityCheck[];
  preserveOriginal?: boolean;
  strictMode?: boolean;
}

export interface TransformationResult {
  success: boolean;
  data?: any;
  errors?: string[];
  warnings?: string[];
  originalData?: any;
  transformedCount?: number;
}

export const DataFormat = {
  JSON: 'json',
  CSV: 'csv',
  XML: 'xml',
  TSV: 'tsv',
  YAML: 'yaml'
} as const;

export type DataFormat = typeof DataFormat[keyof typeof DataFormat];

export interface DataTransformerOptions {
  enableLogging?: boolean;
  maxFileSize?: number;
  timeout?: number;
  encoding?: string;
}

export class DataTransformer {
  private options: DataTransformerOptions;
  private transformationHistory: Array<{
    timestamp: number;
    config: TransformationConfig;
    result: TransformationResult;
  }> = [];

  constructor(options: DataTransformerOptions = {}) {
    this.options = {
      enableLogging: true,
      maxFileSize: 10 * 1024 * 1024, // 10MB
      timeout: 30000, // 30 seconds
      encoding: 'utf-8',
      ...options
    };
  }

  /**
   * 转换数据格式
   */
  async transform(data: any, config: TransformationConfig): Promise<TransformationResult> {
    try {
      this.log('开始数据转换', { config });

      // 验证输入数据
      const validationResult = this.validateInput(data, config);
      if (!validationResult.success) {
        return validationResult;
      }

      // 解析源数据
      const parsedData = await this.parseSourceData(data, config.sourceFormat);
      if (!parsedData.success) {
        return parsedData;
      }

      // 应用映射规则
      let processedData = parsedData;
      if (config.mappingRules) {
        processedData = this.applyMappingRules(processedData.data!, config.mappingRules);
        if (!processedData.success) {
          return processedData;
        }
      }

      // 应用转换规则
      const transformedData = this.applyTransformationRules(processedData.data!, config.rules);
      if (!transformedData.success) {
        return transformedData;
      }

      // 验证转换后的数据
      if (config.validationRules) {
        const validationResult = this.validateTransformedData(transformedData.data!, config.validationRules);
        if (!validationResult.success) {
          return validationResult;
        }
      }

      // 执行数据完整性检查
      let integrityResult: TransformationResult = { success: true, data: transformedData.data, warnings: [] };
      if (config.integrityChecks) {
        integrityResult = this.performIntegrityChecks(transformedData.data!, config.integrityChecks);
        if (!integrityResult.success && config.strictMode) {
          return integrityResult;
        }
      }

      // 格式化输出数据
      const formattedData = await this.formatOutputData(integrityResult.data!, config.targetFormat, config);
      if (!formattedData.success) {
        return formattedData;
      }

      const result: TransformationResult = {
        success: true,
        data: formattedData.data,
        originalData: config.preserveOriginal ? data : undefined,
        transformedCount: Array.isArray(integrityResult.data) ? integrityResult.data.length : 1,
        warnings: integrityResult.warnings || []
      };

      // 记录转换历史
      this.transformationHistory.push({
        timestamp: Date.now(),
        config,
        result
      });

      this.log('数据转换完成', { result });
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      this.log('数据转换失败', { error: errorMessage });
      
      return {
        success: false,
        errors: [errorMessage]
      };
    }
  }

  /**
   * JSON 格式转换
   */
  async transformToJSON(data: any, sourceFormat: DataFormat): Promise<TransformationResult> {
    const config: TransformationConfig = {
      sourceFormat,
      targetFormat: DataFormat.JSON,
      rules: []
    };

    return this.transform(data, config);
  }

  /**
   * CSV 格式转换
   */
  async transformToCSV(data: any, sourceFormat: DataFormat, delimiter: string = ','): Promise<TransformationResult> {
    const config: TransformationConfig = {
      sourceFormat,
      targetFormat: DataFormat.CSV,
      rules: []
    };

    // Store delimiter in config for later use
    (config as any).csvDelimiter = delimiter;

    return this.transform(data, config);
  }

  /**
   * XML 格式转换
   */
  async transformToXML(data: any, sourceFormat: DataFormat, rootElement: string = 'root'): Promise<TransformationResult> {
    const config: TransformationConfig = {
      sourceFormat,
      targetFormat: DataFormat.XML,
      rules: []
    };

    // 设置 XML 根元素
    (config as any).xmlRootElement = rootElement;

    return this.transform(data, config);
  }

  /**
   * 验证输入数据
   */
  private validateInput(data: any, config: TransformationConfig): TransformationResult {
    const errors: string[] = [];

    if (data === null || data === undefined) {
      errors.push('输入数据不能为空');
    }

    if (typeof data === 'string' && data.length > (this.options.maxFileSize || 0)) {
      errors.push(`数据大小超过限制: ${this.options.maxFileSize} bytes`);
    }

    if (!Object.values(DataFormat).includes(config.sourceFormat)) {
      errors.push(`不支持的源数据格式: ${config.sourceFormat}`);
    }

    if (!Object.values(DataFormat).includes(config.targetFormat)) {
      errors.push(`不支持的目标数据格式: ${config.targetFormat}`);
    }

    return {
      success: errors.length === 0,
      errors: errors.length > 0 ? errors : undefined
    };
  }

  /**
   * 解析源数据
   */
  private async parseSourceData(data: any, format: DataFormat): Promise<TransformationResult> {
    try {
      let parsedData: any;

      switch (format) {
        case DataFormat.JSON:
          parsedData = typeof data === 'string' ? JSON.parse(data) : data;
          break;

        case DataFormat.CSV:
          parsedData = this.parseCSV(data);
          break;

        case DataFormat.XML:
          parsedData = this.parseXML(data);
          break;

        case DataFormat.TSV:
          parsedData = this.parseCSV(data, '\t');
          break;

        case DataFormat.YAML:
          parsedData = this.parseYAML(data);
          break;

        default:
          return {
            success: false,
            errors: [`不支持的数据格式: ${format}`]
          };
      }

      return {
        success: true,
        data: parsedData
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '数据解析失败';
      return {
        success: false,
        errors: [errorMessage]
      };
    }
  }

  /**
   * 应用转换规则
   */
  private applyTransformationRules(data: any, rules: TransformationRule[]): TransformationResult {
    try {
      if (rules.length === 0) {
        return { success: true, data };
      }

      const transformedData = Array.isArray(data) 
        ? data.map(item => this.transformItem(item, rules))
        : this.transformItem(data, rules);

      return {
        success: true,
        data: transformedData
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '转换规则应用失败';
      return {
        success: false,
        errors: [errorMessage]
      };
    }
  }

  /**
   * 应用映射规则
   */
  private applyMappingRules(data: any, mappingRules: TransformationMappingRule[]): TransformationResult {
    try {
      if (!mappingRules || mappingRules.length === 0) {
        return { success: true, data };
      }

      // 按优先级排序映射规则
      const sortedRules = mappingRules.sort((a, b) => (b.priority || 0) - (a.priority || 0));

      const mappedData = Array.isArray(data)
        ? data.map(item => this.applyMappingToItem(item, sortedRules))
        : this.applyMappingToItem(data, sortedRules);

      return {
        success: true,
        data: mappedData
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '映射规则应用失败';
      return {
        success: false,
        errors: [errorMessage]
      };
    }
  }

  /**
   * 对单个项目应用映射规则
   */
  private applyMappingToItem(item: any, mappingRules: TransformationMappingRule[]): any {
    const result = { ...item };

    for (const rule of mappingRules) {
      const sourceValue = this.getNestedValue(item, rule.sourceField);
      
      // 检查条件
      if (rule.condition && !rule.condition(sourceValue, item)) {
        continue;
      }

      // 应用映射
      this.setNestedValue(result, rule.targetField, sourceValue);
    }

    return result;
  }

  /**
   * 执行数据完整性检查
   */
  private performIntegrityChecks(data: any, checks: DataIntegrityCheck[]): TransformationResult {
    if (!checks || checks.length === 0) {
      return { success: true, data };
    }

    const errors: string[] = [];
    const warnings: string[] = [];

    for (const check of checks) {
      try {
        const passed = check.check(data);
        if (!passed) {
          if (check.severity === 'error') {
            errors.push(check.errorMessage);
          } else {
            warnings.push(check.errorMessage);
          }
        }
      } catch (error) {
        errors.push(`完整性检查失败 "${check.name}": ${error}`);
      }
    }

    return {
      success: errors.length === 0,
      data,
      errors: errors.length > 0 ? errors : undefined,
      warnings: warnings.length > 0 ? warnings : undefined
    };
  }

  /**
   * 转换单个数据项
   */
  private transformItem(item: any, rules: TransformationRule[]): any {
    const result: any = {};

    for (const rule of rules) {
      let value = this.getNestedValue(item, rule.sourceField);

      // 应用默认值
      if ((value === null || value === undefined) && rule.defaultValue !== undefined) {
        value = rule.defaultValue;
      }

      // 检查必填字段
      if (rule.required && (value === null || value === undefined)) {
        throw new Error(`必填字段缺失: ${rule.sourceField}`);
      }

      // 应用转换函数
      if (rule.transform && value !== null && value !== undefined) {
        try {
          value = rule.transform(value);
        } catch (error) {
          throw new Error(`字段转换失败 ${rule.sourceField}: ${error}`);
        }
      }

      // 设置目标字段值
      this.setNestedValue(result, rule.targetField, value);
    }

    return result;
  }

  /**
   * 验证转换后的数据
   */
  private validateTransformedData(data: any, rules: ValidationRule[]): TransformationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const validateItem = (item: any) => {
      for (const rule of rules) {
        const value = this.getNestedValue(item, rule.field);

        // 检查必填字段
        if (rule.required && (value === null || value === undefined)) {
          const errorMsg = rule.errorMessage || `必填字段缺失: ${rule.field}`;
          errors.push(errorMsg);
          continue;
        }

        if (value === null || value === undefined) {
          continue;
        }

        // 检查数据类型
        if (!this.validateType(value, rule.type)) {
          const errorMsg = rule.errorMessage || `字段类型错误 ${rule.field}: 期望 ${rule.type}, 实际 ${typeof value}`;
          errors.push(errorMsg);
          continue;
        }

        // 检查字符串长度
        if (rule.type === 'string' && typeof value === 'string') {
          if (rule.minLength && value.length < rule.minLength) {
            const errorMsg = rule.errorMessage || `字段长度不足 ${rule.field}: 最小长度 ${rule.minLength}`;
            errors.push(errorMsg);
          }
          if (rule.maxLength && value.length > rule.maxLength) {
            const errorMsg = rule.errorMessage || `字段长度超限 ${rule.field}: 最大长度 ${rule.maxLength}`;
            errors.push(errorMsg);
          }
        }

        // 检查数值范围
        if (rule.type === 'number' && typeof value === 'number') {
          if (rule.min !== undefined && value < rule.min) {
            const errorMsg = rule.errorMessage || `数值过小 ${rule.field}: 最小值 ${rule.min}`;
            errors.push(errorMsg);
          }
          if (rule.max !== undefined && value > rule.max) {
            const errorMsg = rule.errorMessage || `数值过大 ${rule.field}: 最大值 ${rule.max}`;
            errors.push(errorMsg);
          }
        }

        // 检查正则表达式
        if (rule.pattern && typeof value === 'string' && !rule.pattern.test(value)) {
          const errorMsg = rule.errorMessage || `字段格式错误 ${rule.field}: 不匹配模式 ${rule.pattern}`;
          errors.push(errorMsg);
        }

        // 自定义验证器
        if (rule.validator && !rule.validator(value)) {
          const errorMsg = rule.errorMessage || `字段验证失败 ${rule.field}: 自定义验证器返回 false`;
          errors.push(errorMsg);
        }
      }
    };

    if (Array.isArray(data)) {
      data.forEach(validateItem);
    } else {
      validateItem(data);
    }

    return {
      success: errors.length === 0,
      data,
      errors: errors.length > 0 ? errors : undefined,
      warnings: warnings.length > 0 ? warnings : undefined
    };
  }

  /**
   * 格式化输出数据
   */
  private async formatOutputData(data: any, format: DataFormat, config?: any): Promise<TransformationResult> {
    try {
      let formattedData: any;

      switch (format) {
        case DataFormat.JSON:
          formattedData = JSON.stringify(data, null, 2);
          break;

        case DataFormat.CSV:
          const delimiter = config?.csvDelimiter || ',';
          formattedData = this.formatCSV(data, delimiter);
          break;

        case DataFormat.XML:
          const rootElement = config?.xmlRootElement || 'root';
          formattedData = this.formatXML(data, rootElement);
          break;

        case DataFormat.TSV:
          formattedData = this.formatCSV(data, '\t');
          break;

        case DataFormat.YAML:
          formattedData = this.formatYAML(data);
          break;

        default:
          return {
            success: false,
            errors: [`不支持的输出格式: ${format}`]
          };
      }

      return {
        success: true,
        data: formattedData
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '数据格式化失败';
      return {
        success: false,
        errors: [errorMessage]
      };
    }
  }

  /**
   * 解析 CSV 数据
   */
  private parseCSV(data: string, delimiter: string = ','): any[] {
    const lines = data.trim().split('\n');
    if (lines.length === 0) return [];

    const headers = lines[0].split(delimiter).map(h => h.trim());
    const result: any[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(delimiter);
      const row: any = {};

      headers.forEach((header, index) => {
        row[header] = values[index]?.trim() || '';
      });

      result.push(row);
    }

    return result;
  }

  /**
   * 格式化 CSV 数据
   */
  private formatCSV(data: any[], delimiter: string = ','): string {
    if (!Array.isArray(data) || data.length === 0) {
      return '';
    }

    const headers = Object.keys(data[0]);
    const csvLines = [headers.join(delimiter)];

    for (const row of data) {
      const values = headers.map(header => {
        const value = row[header];
        return value !== null && value !== undefined ? String(value) : '';
      });
      csvLines.push(values.join(delimiter));
    }

    return csvLines.join('\n');
  }

  /**
   * 解析 XML 数据 (简化实现)
   */
  private parseXML(data: string): any {
    // 简化的 XML 解析实现
    // 在实际项目中应该使用专业的 XML 解析库
    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(data, 'text/xml');
      return this.xmlToObject(xmlDoc.documentElement);
    } catch (error) {
      throw new Error(`XML 解析失败: ${error}`);
    }
  }

  /**
   * 格式化 XML 数据 (简化实现)
   */
  private formatXML(data: any, rootElement: string = 'root'): string {
    const xmlLines = [`<?xml version="1.0" encoding="UTF-8"?>`];
    xmlLines.push(`<${rootElement}>`);
    xmlLines.push(this.objectToXml(data, 1));
    xmlLines.push(`</${rootElement}>`);
    return xmlLines.join('\n');
  }

  /**
   * 解析 YAML 数据 (简化实现)
   */
  private parseYAML(_data: string): any {
    // 简化的 YAML 解析实现
    // 在实际项目中应该使用专业的 YAML 解析库
    throw new Error('YAML 格式暂不支持，请使用专业的 YAML 解析库');
  }

  /**
   * 格式化 YAML 数据 (简化实现)
   */
  private formatYAML(_data: any): string {
    // 简化的 YAML 格式化实现
    throw new Error('YAML 格式暂不支持，请使用专业的 YAML 解析库');
  }

  /**
   * XML 转对象
   */
  private xmlToObject(element: Element): any {
    const result: any = {};

    // 处理属性
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      result[`@${attr.name}`] = attr.value;
    }

    // 处理子元素
    for (let i = 0; i < element.childNodes.length; i++) {
      const child = element.childNodes[i];

      if (child.nodeType === Node.TEXT_NODE) {
        const text = child.textContent?.trim();
        if (text) {
          result['#text'] = text;
        }
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        const childElement = child as Element;
        const childName = childElement.tagName;
        const childValue = this.xmlToObject(childElement);

        if (result[childName]) {
          if (!Array.isArray(result[childName])) {
            result[childName] = [result[childName]];
          }
          result[childName].push(childValue);
        } else {
          result[childName] = childValue;
        }
      }
    }

    return result;
  }

  /**
   * 对象转 XML
   */
  private objectToXml(obj: any, indent: number = 0): string {
    const spaces = '  '.repeat(indent);
    const lines: string[] = [];

    for (const [key, value] of Object.entries(obj)) {
      if (key.startsWith('@') || key === '#text') {
        continue;
      }

      if (Array.isArray(value)) {
        for (const item of value) {
          lines.push(`${spaces}<${key}>`);
          if (typeof item === 'object') {
            lines.push(this.objectToXml(item, indent + 1));
          } else {
            lines.push(`${spaces}  ${item}`);
          }
          lines.push(`${spaces}</${key}>`);
        }
      } else if (typeof value === 'object') {
        lines.push(`${spaces}<${key}>`);
        lines.push(this.objectToXml(value, indent + 1));
        lines.push(`${spaces}</${key}>`);
      } else {
        lines.push(`${spaces}<${key}>${value}</${key}>`);
      }
    }

    return lines.join('\n');
  }

  /**
   * 获取嵌套对象的值
   */
  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
  }

  /**
   * 设置嵌套对象的值
   */
  private setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    
    const target = keys.reduce((current, key) => {
      if (!current[key] || typeof current[key] !== 'object') {
        current[key] = {};
      }
      return current[key];
    }, obj);

    target[lastKey] = value;
  }

  /**
   * 验证数据类型
   */
  private validateType(value: any, expectedType: string): boolean {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string';
      case 'number':
        return typeof value === 'number' && !isNaN(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'array':
        return Array.isArray(value);
      case 'object':
        return typeof value === 'object' && value !== null && !Array.isArray(value);
      case 'date':
        return value instanceof Date || (typeof value === 'string' && !isNaN(Date.parse(value)));
      case 'email':
        return typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      case 'url':
        try {
          new URL(value);
          return true;
        } catch {
          return false;
        }
      default:
        return false;
    }
  }

  /**
   * 获取转换历史
   */
  getTransformationHistory(): Array<{
    timestamp: number;
    config: TransformationConfig;
    result: TransformationResult;
  }> {
    return [...this.transformationHistory];
  }

  /**
   * 清除转换历史
   */
  clearHistory(): void {
    this.transformationHistory = [];
  }

  /**
   * 记录日志
   */
  private log(message: string, data?: any): void {
    if (this.options.enableLogging) {
      console.log(`[DataTransformer] ${message}`, data);
    }
  }

  /**
   * 创建常用验证规则
   */
  static createValidationRules() {
    return {
      required: (field: string, errorMessage?: string): ValidationRule => ({
        field,
        type: 'string',
        required: true,
        errorMessage
      }),

      email: (field: string, required = false, errorMessage?: string): ValidationRule => ({
        field,
        type: 'email',
        required,
        errorMessage
      }),

      url: (field: string, required = false, errorMessage?: string): ValidationRule => ({
        field,
        type: 'url',
        required,
        errorMessage
      }),

      stringLength: (field: string, minLength?: number, maxLength?: number, errorMessage?: string): ValidationRule => ({
        field,
        type: 'string',
        minLength,
        maxLength,
        errorMessage
      }),

      numberRange: (field: string, min?: number, max?: number, errorMessage?: string): ValidationRule => ({
        field,
        type: 'number',
        min,
        max,
        errorMessage
      }),

      pattern: (field: string, pattern: RegExp, errorMessage?: string): ValidationRule => ({
        field,
        type: 'string',
        pattern,
        errorMessage
      })
    };
  }

  /**
   * 创建常用映射规则
   */
  static createMappingRules() {
    return {
      simple: (sourceField: string, targetField: string, priority = 0): TransformationMappingRule => ({
        sourceField,
        targetField,
        priority
      }),

      conditional: (
        sourceField: string, 
        targetField: string, 
        condition: (value: any, item: any) => boolean,
        priority = 0
      ): TransformationMappingRule => ({
        sourceField,
        targetField,
        condition,
        priority
      }),

      rename: (oldName: string, newName: string): TransformationMappingRule => ({
        sourceField: oldName,
        targetField: newName,
        priority: 1
      })
    };
  }

  /**
   * 创建常用完整性检查
   */
  static createIntegrityChecks() {
    return {
      notEmpty: (errorMessage = '数据不能为空'): DataIntegrityCheck => ({
        name: 'notEmpty',
        check: (data: any) => {
          if (Array.isArray(data)) {
            return data.length > 0;
          }
          return data !== null && data !== undefined;
        },
        errorMessage,
        severity: 'error' as const
      }),

      uniqueField: (field: string, errorMessage?: string): DataIntegrityCheck => ({
        name: `uniqueField_${field}`,
        check: (data: any) => {
          if (!Array.isArray(data)) return true;
          const values = data.map(item => item[field]).filter(v => v !== null && v !== undefined);
          return values.length === new Set(values).size;
        },
        errorMessage: errorMessage || `字段 ${field} 存在重复值`,
        severity: 'error' as const
      }),

      minCount: (minCount: number, errorMessage?: string): DataIntegrityCheck => ({
        name: 'minCount',
        check: (data: any) => {
          const count = Array.isArray(data) ? data.length : 1;
          return count >= minCount;
        },
        errorMessage: errorMessage || `数据项数量不足，最少需要 ${minCount} 项`,
        severity: 'warning' as const
      })
    };
  }
}

export default DataTransformer;

/**
 * 数据验证器 - 扩展验证功能
 */
export class DataValidator {
  private customValidators: Map<string, (value: any) => boolean> = new Map();

  /**
   * 注册自定义验证器
   */
  registerValidator(name: string, validator: (value: any) => boolean): void {
    this.customValidators.set(name, validator);
  }

  /**
   * 验证数据完整性
   */
  validateDataIntegrity(data: any, schema: ValidationSchema): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      if (Array.isArray(data)) {
        data.forEach((item, index) => {
          const itemResult = this.validateItem(item, schema, `[${index}]`);
          errors.push(...itemResult.errors);
          warnings.push(...itemResult.warnings);
        });
      } else {
        const itemResult = this.validateItem(data, schema);
        errors.push(...itemResult.errors);
        warnings.push(...itemResult.warnings);
      }

      return {
        success: errors.length === 0,
        errors,
        warnings,
        validatedCount: Array.isArray(data) ? data.length : 1
      };

    } catch (error) {
      return {
        success: false,
        errors: [error instanceof Error ? error.message : '验证过程中发生未知错误'],
        warnings: [],
        validatedCount: 0
      };
    }
  }

  /**
   * 验证单个数据项
   */
  private validateItem(item: any, schema: ValidationSchema, prefix: string = ''): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    for (const rule of schema.rules) {
      const fieldPath = prefix ? `${prefix}.${rule.field}` : rule.field;
      const value = this.getNestedValue(item, rule.field);

      // 检查必填字段
      if (rule.required && (value === null || value === undefined)) {
        errors.push(`必填字段缺失: ${fieldPath}`);
        continue;
      }

      if (value === null || value === undefined) {
        continue;
      }

      // 数据类型验证
      if (rule.type && !this.validateType(value, rule.type)) {
        errors.push(`字段类型错误 ${fieldPath}: 期望 ${rule.type}, 实际 ${typeof value}`);
      }

      // 字符串验证
      if (rule.type === 'string' && typeof value === 'string') {
        if (rule.minLength && value.length < rule.minLength) {
          errors.push(`字段长度不足 ${fieldPath}: 最小长度 ${rule.minLength}`);
        }
        if (rule.maxLength && value.length > rule.maxLength) {
          errors.push(`字段长度超限 ${fieldPath}: 最大长度 ${rule.maxLength}`);
        }
        if (rule.pattern && !rule.pattern.test(value)) {
          errors.push(`字段格式错误 ${fieldPath}: 不匹配模式 ${rule.pattern}`);
        }
      }

      // 数值验证
      if (rule.type === 'number' && typeof value === 'number') {
        if (rule.min !== undefined && value < rule.min) {
          errors.push(`数值过小 ${fieldPath}: 最小值 ${rule.min}`);
        }
        if (rule.max !== undefined && value > rule.max) {
          errors.push(`数值过大 ${fieldPath}: 最大值 ${rule.max}`);
        }
      }

      // 数组验证
      if (rule.type === 'array' && Array.isArray(value)) {
        if (rule.minItems && value.length < rule.minItems) {
          errors.push(`数组元素不足 ${fieldPath}: 最少 ${rule.minItems} 个元素`);
        }
        if (rule.maxItems && value.length > rule.maxItems) {
          errors.push(`数组元素过多 ${fieldPath}: 最多 ${rule.maxItems} 个元素`);
        }
      }

      // 自定义验证器
      if (rule.validator) {
        try {
          if (!rule.validator(value)) {
            errors.push(`字段验证失败 ${fieldPath}: 自定义验证器返回 false`);
          }
        } catch (error) {
          errors.push(`字段验证异常 ${fieldPath}: ${error}`);
        }
      }

      // 注册的自定义验证器
      if (rule.customValidator && this.customValidators.has(rule.customValidator)) {
        const validator = this.customValidators.get(rule.customValidator)!;
        try {
          if (!validator(value)) {
            errors.push(`字段验证失败 ${fieldPath}: 自定义验证器 ${rule.customValidator} 返回 false`);
          }
        } catch (error) {
          errors.push(`字段验证异常 ${fieldPath}: 自定义验证器 ${rule.customValidator} 抛出异常`);
        }
      }

      // 枚举值验证
      if (rule.enum && !rule.enum.includes(value)) {
        errors.push(`字段值不在允许范围内 ${fieldPath}: 允许值 [${rule.enum.join(', ')}]`);
      }

      // 警告检查
      if (rule.deprecated) {
        warnings.push(`字段已废弃 ${fieldPath}: ${rule.deprecatedMessage || '建议使用其他字段'}`);
      }
    }

    return {
      success: errors.length === 0,
      errors,
      warnings,
      validatedCount: 1
    };
  }

  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
  }

  private validateType(value: any, expectedType: string): boolean {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string';
      case 'number':
        return typeof value === 'number' && !isNaN(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'array':
        return Array.isArray(value);
      case 'object':
        return typeof value === 'object' && value !== null && !Array.isArray(value);
      case 'date':
        return value instanceof Date || !isNaN(Date.parse(value));
      case 'email':
        return typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      case 'url':
        try {
          new URL(value);
          return true;
        } catch {
          return false;
        }
      default:
        return false;
    }
  }
}

/**
 * 数据映射器 - 处理复杂的数据映射逻辑
 */
export class DataMapper {
  private mappingRules: Map<string, MappingRule> = new Map();

  /**
   * 注册映射规则
   */
  registerMappingRule(name: string, rule: MappingRule): void {
    this.mappingRules.set(name, rule);
  }

  /**
   * 应用映射规则
   */
  applyMapping(data: any, mappingName: string): MappingResult {
    const rule = this.mappingRules.get(mappingName);
    if (!rule) {
      return {
        success: false,
        errors: [`映射规则不存在: ${mappingName}`]
      };
    }

    try {
      const mappedData = Array.isArray(data)
        ? data.map(item => this.mapItem(item, rule))
        : this.mapItem(data, rule);

      return {
        success: true,
        data: mappedData,
        mappedCount: Array.isArray(data) ? data.length : 1
      };

    } catch (error) {
      return {
        success: false,
        errors: [error instanceof Error ? error.message : '映射过程中发生未知错误']
      };
    }
  }

  /**
   * 映射单个数据项
   */
  private mapItem(item: any, rule: MappingRule): any {
    const result: any = {};

    // 应用字段映射
    for (const [sourceField, targetField] of Object.entries(rule.fieldMappings)) {
      const value = this.getNestedValue(item, sourceField);
      if (value !== undefined) {
        this.setNestedValue(result, targetField, value);
      }
    }

    // 应用转换函数
    if (rule.transformations) {
      for (const [field, transformer] of Object.entries(rule.transformations)) {
        const value = this.getNestedValue(result, field);
        if (value !== undefined) {
          try {
            const transformedValue = transformer(value, item);
            this.setNestedValue(result, field, transformedValue);
          } catch (error) {
            throw new Error(`字段转换失败 ${field}: ${error}`);
          }
        }
      }
    }

    // 应用默认值
    if (rule.defaults) {
      for (const [field, defaultValue] of Object.entries(rule.defaults)) {
        const value = this.getNestedValue(result, field);
        if (value === undefined || value === null) {
          this.setNestedValue(result, field, defaultValue);
        }
      }
    }

    // 应用计算字段
    if (rule.computedFields) {
      for (const [field, computer] of Object.entries(rule.computedFields)) {
        try {
          const computedValue = computer(result, item);
          this.setNestedValue(result, field, computedValue);
        } catch (error) {
          throw new Error(`计算字段失败 ${field}: ${error}`);
        }
      }
    }

    return result;
  }

  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined;
    }, obj);
  }

  private setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    
    const target = keys.reduce((current, key) => {
      if (!current[key] || typeof current[key] !== 'object') {
        current[key] = {};
      }
      return current[key];
    }, obj);

    target[lastKey] = value;
  }
}

// 扩展接口定义
export interface ValidationSchema {
  rules: ExtendedValidationRule[];
  strict?: boolean;
}

export interface ExtendedValidationRule extends ValidationRule {
  min?: number;
  max?: number;
  minItems?: number;
  maxItems?: number;
  enum?: any[];
  customValidator?: string;
  deprecated?: boolean;
  deprecatedMessage?: string;
}

export interface ValidationResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  validatedCount: number;
}

export interface MappingRule {
  fieldMappings: Record<string, string>;
  transformations?: Record<string, (value: any, originalItem: any) => any>;
  defaults?: Record<string, any>;
  computedFields?: Record<string, (mappedItem: any, originalItem: any) => any>;
}

export interface MappingResult {
  success: boolean;
  data?: any;
  errors?: string[];
  mappedCount?: number;
}

// 预定义的常用验证器
export const CommonValidators = {
  email: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
  phone: (value: string) => /^[\+]?[1-9][\d]{0,15}$/.test(value),
  url: (value: string) => {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  },
  uuid: (value: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value),
  ipv4: (value: string) => /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(value),
  date: (value: string) => !isNaN(Date.parse(value)),
  positiveNumber: (value: number) => typeof value === 'number' && value > 0,
  nonEmptyString: (value: string) => typeof value === 'string' && value.trim().length > 0
};

// 预定义的常用转换器
export const CommonTransformers = {
  trim: (value: string) => typeof value === 'string' ? value.trim() : value,
  toLowerCase: (value: string) => typeof value === 'string' ? value.toLowerCase() : value,
  toUpperCase: (value: string) => typeof value === 'string' ? value.toUpperCase() : value,
  toNumber: (value: any) => {
    const num = Number(value);
    return isNaN(num) ? value : num;
  },
  toString: (value: any) => String(value),
  toDate: (value: any) => {
    if (value instanceof Date) return value;
    const date = new Date(value);
    return isNaN(date.getTime()) ? value : date;
  },
  removeSpaces: (value: string) => typeof value === 'string' ? value.replace(/\s+/g, '') : value,
  capitalizeFirst: (value: string) => typeof value === 'string' && value.length > 0 
    ? value.charAt(0).toUpperCase() + value.slice(1).toLowerCase() 
    : value
};