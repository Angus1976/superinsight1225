/**
 * ChineseBusinessValidatorPanel Component (中国企业标识验证面板)
 * 
 * Panel for testing Chinese business identifier validators with:
 * - Display Chinese business identifier validators
 * - Test validator with sample inputs
 * - Show validation results and error messages
 * 
 * Requirements: 5.1, 5.2, 5.3
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Alert,
  Tag,
  Typography,
  Divider,
  Row,
  Col,
  Spin,
  Result,
  List,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  BankOutlined,
  IdcardOutlined,
  FileProtectOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  ontologyValidationApi,
  type ValidationRule,
  type ValidationResult,
} from '../../services/ontologyExpertApi';

const { Text, Title, Paragraph } = Typography;

interface ValidatorInfo {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  placeholder: string;
  examples: string[];
}

const VALIDATORS: ValidatorInfo[] = [
  {
    key: 'uscc',
    name: 'validation.uscc',
    description: 'validation.usccDesc',
    icon: <SafetyCertificateOutlined style={{ fontSize: 24, color: '#1890ff' }} />,
    placeholder: '91110000100000000X',
    examples: ['91110000100000000X', '91320000MA1XXXXX0X'],
  },
  {
    key: 'org_code',
    name: 'validation.orgCode',
    description: 'validation.orgCodeDesc',
    icon: <BankOutlined style={{ fontSize: 24, color: '#52c41a' }} />,
    placeholder: '12345678-9',
    examples: ['12345678-9', 'A1234567-8'],
  },
  {
    key: 'business_license',
    name: 'validation.businessLicense',
    description: 'validation.businessLicenseDesc',
    icon: <FileProtectOutlined style={{ fontSize: 24, color: '#faad14' }} />,
    placeholder: '110000000000000',
    examples: ['110000000000000', '310000000000000'],
  },
];

const ChineseBusinessValidatorPanel: React.FC = () => {
  const { t } = useTranslation('ontology');
  const [selectedValidator, setSelectedValidator] = useState<string>('uscc');
  const [testInput, setTestInput] = useState('');
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);

  // Load Chinese business validators
  useEffect(() => {
    const loadRules = async () => {
      setLoadingRules(true);
      try {
        const data = await ontologyValidationApi.getChineseBusinessValidators();
        setRules(data);
      } catch (error) {
        console.error('Failed to load validators:', error);
      } finally {
        setLoadingRules(false);
      }
    };
    loadRules();
  }, []);

  const handleValidate = async () => {
    if (!testInput.trim()) {
      message.warning(t('validation.testInputPlaceholder'));
      return;
    }

    setValidating(true);
    setResult(null);

    try {
      // Map validator key to entity type
      const entityTypeMap: Record<string, string> = {
        uscc: 'Company',
        org_code: 'Organization',
        business_license: 'Company',
      };

      // Map validator key to field name
      const fieldMap: Record<string, string> = {
        uscc: 'unified_social_credit_code',
        org_code: 'organization_code',
        business_license: 'business_license_number',
      };

      const entity = {
        [fieldMap[selectedValidator]]: testInput.trim(),
      };

      const validationResult = await ontologyValidationApi.validate(
        entity,
        entityTypeMap[selectedValidator],
        'CN'
      );

      setResult(validationResult);
    } catch (error) {
      console.error('Validation failed:', error);
      message.error(t('validation.testFailed'));
    } finally {
      setValidating(false);
    }
  };

  const currentValidator = VALIDATORS.find((v) => v.key === selectedValidator);

  const renderValidatorCard = (validator: ValidatorInfo) => {
    const isSelected = selectedValidator === validator.key;
    
    return (
      <Card
        key={validator.key}
        size="small"
        hoverable
        style={{
          cursor: 'pointer',
          borderColor: isSelected ? '#1890ff' : undefined,
          backgroundColor: isSelected ? '#e6f7ff' : undefined,
        }}
        onClick={() => {
          setSelectedValidator(validator.key);
          setTestInput('');
          setResult(null);
        }}
      >
        <Space>
          {validator.icon}
          <div>
            <Text strong>{t(validator.name)}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t(validator.description)}
            </Text>
          </div>
        </Space>
      </Card>
    );
  };

  const renderResult = () => {
    if (!result) return null;

    if (result.is_valid) {
      return (
        <Result
          status="success"
          icon={<CheckCircleOutlined />}
          title={t('validation.testSuccess')}
          subTitle={t('validation.isValid')}
        />
      );
    }

    return (
      <div>
        <Alert
          type="error"
          showIcon
          icon={<CloseCircleOutlined />}
          message={t('validation.testFailed')}
          description={t('validation.isInvalid')}
          style={{ marginBottom: 16 }}
        />
        
        {result.errors.length > 0 && (
          <Card size="small" title={t('validation.errorDetails')}>
            <List
              size="small"
              dataSource={result.errors}
              renderItem={(error) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                    title={error.field}
                    description={
                      <Space direction="vertical" size={0}>
                        <Text type="danger">{error.message}</Text>
                        {error.suggestion && (
                          <Text type="secondary">
                            <InfoCircleOutlined /> {t('validation.suggestion')}: {error.suggestion}
                          </Text>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        )}
      </div>
    );
  };

  return (
    <div>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>
          <IdcardOutlined /> {t('validation.chineseBusinessTitle')}
        </Title>
        <Paragraph type="secondary">
          {t('validation.chineseBusinessDesc')}
        </Paragraph>
      </Card>

      <Row gutter={16}>
        {/* Validator Selection */}
        <Col span={8}>
          <Card title={t('validation.selectValidator')} loading={loadingRules}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {VALIDATORS.map(renderValidatorCard)}
            </Space>
          </Card>
        </Col>

        {/* Test Panel */}
        <Col span={16}>
          <Card title={t('validation.testValidator')}>
            {currentValidator && (
              <>
                {/* Validator Info */}
                <Alert
                  type="info"
                  showIcon
                  icon={currentValidator.icon}
                  message={t(currentValidator.name)}
                  description={t(currentValidator.description)}
                  style={{ marginBottom: 16 }}
                />

                {/* Test Input */}
                <Form layout="vertical">
                  <Form.Item label={t('validation.testInput')}>
                    <Space.Compact style={{ width: '100%' }}>
                      <Input
                        value={testInput}
                        onChange={(e) => setTestInput(e.target.value)}
                        placeholder={currentValidator.placeholder}
                        onPressEnter={handleValidate}
                        style={{ fontFamily: 'monospace' }}
                      />
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleValidate}
                        loading={validating}
                      >
                        {t('validation.runTest')}
                      </Button>
                    </Space.Compact>
                  </Form.Item>
                </Form>

                {/* Example Values */}
                <div style={{ marginBottom: 16 }}>
                  <Text type="secondary">{t('common.examples')}: </Text>
                  <Space>
                    {currentValidator.examples.map((example) => (
                      <Tag
                        key={example}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setTestInput(example)}
                      >
                        {example}
                      </Tag>
                    ))}
                  </Space>
                </div>

                <Divider />

                {/* Result */}
                <div style={{ minHeight: 150 }}>
                  {validating ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Spin tip={t('common.validating')} />
                    </div>
                  ) : (
                    renderResult()
                  )}
                </div>
              </>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ChineseBusinessValidatorPanel;
