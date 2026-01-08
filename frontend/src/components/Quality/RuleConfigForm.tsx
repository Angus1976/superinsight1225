import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Switch,
  Button,
  Space,
  Card,
  Divider,
  InputNumber,
  Checkbox,
  Radio,
  Alert,
  Tabs,
  Typography,
  message,
} from 'antd';
import {
  SettingOutlined,
  PlayCircleOutlined,
  SaveOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { QualityRule } from '@/services/quality';

const { TextArea } = Input;
const { Text } = Typography;

interface RuleConfigFormProps {
  rule?: QualityRule;
  onSave: (ruleData: Partial<QualityRule>) => Promise<void>;
  onTest?: (ruleData: Partial<QualityRule>) => Promise<{ success: boolean; message: string }>;
  loading?: boolean;
}

interface RuleConfig {
  // Format rules
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  allowEmpty?: boolean;
  
  // Content rules
  requiredFields?: string[];
  forbiddenWords?: string[];
  qualityThreshold?: number;
  
  // Consistency rules
  similarityThreshold?: number;
  checkDuplicates?: boolean;
  crossValidation?: boolean;
  
  // Custom rules
  customLogic?: string;
  parameters?: Record<string, unknown>;
}

const RuleConfigForm: React.FC<RuleConfigFormProps> = ({
  rule,
  onSave,
  onTest,
  loading = false,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [ruleType, setRuleType] = useState<string>(rule?.type || 'format');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (rule) {
      form.setFieldsValue({
        name: rule.name,
        type: rule.type,
        description: rule.description,
        severity: rule.severity,
        enabled: rule.enabled,
        ...rule.config,
      });
      setRuleType(rule.type);
    }
  }, [rule, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const { name, type, description, severity, enabled, ...config } = values;
      
      const ruleData: Partial<QualityRule> = {
        name: name as string,
        type: type as QualityRule['type'],
        description: description as string,
        severity: severity as QualityRule['severity'],
        enabled: enabled as boolean,
        config: config as Record<string, unknown>,
      };

      await onSave(ruleData);
      message.success(t('quality.messages.ruleUpdated'));
    } catch (error) {
      message.error(t('quality.messages.validationFailed'));
    }
  };

  const handleTest = async () => {
    if (!onTest) return;
    
    setTesting(true);
    try {
      const values = await form.validateFields();
      const { name, type, description, severity, enabled, ...config } = values;
      
      const ruleData: Partial<QualityRule> = {
        name: name as string,
        type: type as QualityRule['type'],
        description: description as string,
        severity: severity as QualityRule['severity'],
        enabled: enabled as boolean,
        config: config as Record<string, unknown>,
      };

      const result = await onTest(ruleData);
      setTestResult(result);
      
      if (result.success) {
        message.success(t('quality.messages.testPassed'));
      } else {
        message.error(t('quality.messages.testFailed'));
      }
    } catch (error) {
      message.error(t('quality.messages.validationFailed'));
    } finally {
      setTesting(false);
    }
  };

  const renderFormatConfig = () => (
    <Card size="small" title={t('quality.rules.types.format')}>
      <Form.Item
        name="minLength"
        label={t('common.minLength')}
      >
        <InputNumber min={0} placeholder="0" style={{ width: '100%' }} />
      </Form.Item>
      
      <Form.Item
        name="maxLength"
        label={t('common.maxLength')}
      >
        <InputNumber min={1} placeholder="1000" style={{ width: '100%' }} />
      </Form.Item>
      
      <Form.Item
        name="pattern"
        label={t('quality.rules.pattern')}
        help={t('quality.rules.regex')}
      >
        <Input placeholder="^[A-Za-z0-9]+$" />
      </Form.Item>
      
      <Form.Item
        name="allowEmpty"
        label={t('common.allowEmpty')}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>
    </Card>
  );

  const renderContentConfig = () => (
    <Card size="small" title={t('quality.rules.types.content')}>
      <Form.Item
        name="requiredFields"
        label={t('common.requiredFields')}
      >
        <Select
          mode="tags"
          placeholder={t('common.selectFields')}
          style={{ width: '100%' }}
        >
          <Select.Option value="label">Label</Select.Option>
          <Select.Option value="text">Text</Select.Option>
          <Select.Option value="category">Category</Select.Option>
        </Select>
      </Form.Item>
      
      <Form.Item
        name="forbiddenWords"
        label={t('common.forbiddenWords')}
      >
        <Select
          mode="tags"
          placeholder={t('common.enterWords')}
          style={{ width: '100%' }}
        />
      </Form.Item>
      
      <Form.Item
        name="qualityThreshold"
        label={t('quality.rules.threshold')}
      >
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          placeholder="0.8"
          style={{ width: '100%' }}
        />
      </Form.Item>
    </Card>
  );

  const renderConsistencyConfig = () => (
    <Card size="small" title={t('quality.rules.types.consistency')}>
      <Form.Item
        name="similarityThreshold"
        label={t('common.similarityThreshold')}
      >
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          placeholder="0.9"
          style={{ width: '100%' }}
        />
      </Form.Item>
      
      <Form.Item
        name="checkDuplicates"
        label={t('common.checkDuplicates')}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>
      
      <Form.Item
        name="crossValidation"
        label={t('common.crossValidation')}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>
    </Card>
  );

  const renderCustomConfig = () => (
    <Card size="small" title={t('quality.rules.types.custom')}>
      <Form.Item
        name="customLogic"
        label={t('quality.rules.customLogic')}
        help={t('common.pythonCode')}
      >
        <TextArea
          rows={8}
          placeholder="def validate(annotation, context):\n    # Your custom validation logic\n    return True, 'Valid'"
        />
      </Form.Item>
      
      <Form.Item
        name="parameters"
        label={t('quality.rules.parameters')}
        help={t('common.jsonFormat')}
      >
        <TextArea
          rows={4}
          placeholder='{"param1": "value1", "param2": 123}'
        />
      </Form.Item>
    </Card>
  );

  const renderConfigByType = () => {
    switch (ruleType) {
      case 'format':
        return renderFormatConfig();
      case 'content':
        return renderContentConfig();
      case 'consistency':
        return renderConsistencyConfig();
      case 'custom':
        return renderCustomConfig();
      default:
        return null;
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        severity: 'warning',
        enabled: true,
      }}
    >
      <Tabs
        defaultActiveKey="basic"
        items={[
          {
            key: 'basic',
            label: t('common.basicInfo'),
            children: (
              <div>
                <Form.Item
                  name="name"
                  label={t('quality.rules.name')}
                  rules={[{ required: true, message: t('common.required') }]}
                >
                  <Input placeholder={t('quality.rules.name')} />
                </Form.Item>

                <Form.Item
                  name="type"
                  label={t('quality.rules.type')}
                  rules={[{ required: true, message: t('common.required') }]}
                >
                  <Select
                    placeholder={t('quality.rules.type')}
                    onChange={setRuleType}
                  >
                    <Select.Option value="format">{t('quality.rules.types.format')}</Select.Option>
                    <Select.Option value="content">{t('quality.rules.types.content')}</Select.Option>
                    <Select.Option value="consistency">{t('quality.rules.types.consistency')}</Select.Option>
                    <Select.Option value="custom">{t('quality.rules.types.custom')}</Select.Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  name="severity"
                  label={t('quality.rules.severity')}
                  rules={[{ required: true, message: t('common.required') }]}
                >
                  <Radio.Group>
                    <Radio value="warning">{t('quality.rules.severities.warning')}</Radio>
                    <Radio value="error">{t('quality.rules.severities.error')}</Radio>
                  </Radio.Group>
                </Form.Item>

                <Form.Item
                  name="description"
                  label={t('quality.rules.description')}
                >
                  <TextArea rows={3} placeholder={t('quality.rules.description')} />
                </Form.Item>

                <Form.Item
                  name="enabled"
                  label={t('quality.rules.enabled')}
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </div>
            ),
          },
          {
            key: 'config',
            label: (
              <Space>
                <SettingOutlined />
                {t('quality.rules.config')}
              </Space>
            ),
            children: (
              <div>
                {renderConfigByType()}
              </div>
            ),
          },
        ]}
      />

      {testResult && (
        <Alert
          type={testResult.success ? 'success' : 'error'}
          message={testResult.message}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setTestResult(null)}
        />
      )}

      <Divider />

      <Space>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          htmlType="submit"
          loading={loading}
        >
          {t('common.save')}
        </Button>
        
        {onTest && (
          <Button
            icon={<PlayCircleOutlined />}
            onClick={handleTest}
            loading={testing}
          >
            {t('quality.rules.test')}
          </Button>
        )}
        
        <Button
          icon={<ReloadOutlined />}
          onClick={() => form.resetFields()}
        >
          {t('common.reset')}
        </Button>
      </Space>
    </Form>
  );
};

export default RuleConfigForm;