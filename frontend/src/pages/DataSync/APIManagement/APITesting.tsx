import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Table,
  Tag,
  Typography,
  message,
  Divider,
  Alert
} from 'antd';
import { SendOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

const { Option } = Select;
const { TextArea } = Input;
const { Text, Paragraph } = Typography;

interface QueryParam {
  key: string;
  value: string;
}

interface TestResponse {
  status: number;
  statusText: string;
  data: any;
  responseTime: number;
}

const APITesting: React.FC = () => {
  const { t } = useTranslation('dataSync');
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<TestResponse | null>(null);
  const [params, setParams] = useState<QueryParam[]>([]);

  const endpoints = [
    {
      value: '/api/v1/external/annotations',
      label: t('apiManagement.endpointAnnotations')
    },
    {
      value: '/api/v1/external/augmented-data',
      label: t('apiManagement.endpointAugmentedData')
    },
    {
      value: '/api/v1/external/quality-reports',
      label: t('apiManagement.endpointQualityReports')
    },
    {
      value: '/api/v1/external/experiments',
      label: t('apiManagement.endpointExperiments')
    }
  ];

  const addParam = () => {
    setParams([...params, { key: '', value: '' }]);
  };

  const removeParam = (index: number) => {
    setParams(params.filter((_, i) => i !== index));
  };

  const updateParam = (index: number, field: 'key' | 'value', value: string) => {
    const newParams = [...params];
    newParams[index][field] = value;
    setParams(newParams);
  };

  const handleTest = async (values: any) => {
    setLoading(true);
    const startTime = Date.now();

    try {
      // Build query parameters
      const queryParams: Record<string, string> = {};
      params.forEach((param) => {
        if (param.key && param.value) {
          queryParams[param.key] = param.value;
        }
      });

      // Make request with API key in header
      const response = await axios.get(values.endpoint, {
        headers: {
          'X-API-Key': values.apiKey
        },
        params: queryParams
      });

      const responseTime = Date.now() - startTime;

      setResponse({
        status: response.status,
        statusText: response.statusText,
        data: response.data,
        responseTime
      });

      message.success(t('apiManagement.testSuccess'));
    } catch (error: any) {
      const responseTime = Date.now() - startTime;

      setResponse({
        status: error.response?.status || 500,
        statusText: error.response?.statusText || 'Error',
        data: error.response?.data || { error: error.message },
        responseTime
      });

      message.error(t('apiManagement.testError'));
    } finally {
      setLoading(false);
    }
  };

  const getStatusTag = (status: number) => {
    if (status >= 200 && status < 300) {
      return <Tag color="success">{status}</Tag>;
    } else if (status >= 400 && status < 500) {
      return <Tag color="warning">{status}</Tag>;
    } else {
      return <Tag color="error">{status}</Tag>;
    }
  };

  const paramColumns = [
    {
      title: t('apiManagement.paramKey'),
      dataIndex: 'key',
      key: 'key',
      render: (_: any, record: QueryParam, index: number) => (
        <Input
          value={record.key}
          onChange={(e) => updateParam(index, 'key', e.target.value)}
          placeholder="page"
        />
      )
    },
    {
      title: t('apiManagement.paramValue'),
      dataIndex: 'value',
      key: 'value',
      render: (_: any, record: QueryParam, index: number) => (
        <Input
          value={record.value}
          onChange={(e) => updateParam(index, 'value', e.target.value)}
          placeholder="1"
        />
      )
    },
    {
      title: t('apiManagement.actions'),
      key: 'actions',
      width: 80,
      render: (_: any, record: QueryParam, index: number) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeParam(index)}
        />
      )
    }
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Alert
          message={t('apiManagement.apiTestingTitle')}
          description={t('apiManagement.description')}
          type="info"
          showIcon
        />

        <Card title={t('apiManagement.sendRequest')}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleTest}
          >
            <Form.Item
              name="endpoint"
              label={t('apiManagement.selectEndpoint')}
              rules={[{ required: true }]}
            >
              <Select placeholder={t('apiManagement.selectEndpoint')}>
                {endpoints.map((endpoint) => (
                  <Option key={endpoint.value} value={endpoint.value}>
                    {endpoint.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="apiKey"
              label={t('apiManagement.enterApiKey')}
              rules={[{ required: true }]}
            >
              <Input.Password
                placeholder={t('apiManagement.apiKeyPlaceholder')}
              />
            </Form.Item>

            <Divider>{t('apiManagement.queryParams')}</Divider>

            <Table
              columns={paramColumns}
              dataSource={params}
              pagination={false}
              size="small"
              locale={{ emptyText: t('apiManagement.noData') }}
            />

            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={addParam}
              style={{ marginTop: 16, width: '100%' }}
            >
              {t('apiManagement.addParam')}
            </Button>

            <Form.Item style={{ marginTop: 24 }}>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SendOutlined />}
                loading={loading}
                block
              >
                {t('apiManagement.sendRequest')}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {response && (
          <Card title={t('apiManagement.response')}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Space>
                  <Text strong>{t('apiManagement.statusCode')}:</Text>
                  {getStatusTag(response.status)}
                  <Text type="secondary">{response.statusText}</Text>
                </Space>
              </div>

              <div>
                <Space>
                  <Text strong>{t('apiManagement.responseTime')}:</Text>
                  <Tag color="blue">{response.responseTime}ms</Tag>
                </Space>
              </div>

              <Divider>{t('apiManagement.responseBody')}</Divider>

              <Paragraph>
                <pre
                  style={{
                    backgroundColor: '#f5f5f5',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                    maxHeight: 400
                  }}
                >
                  {JSON.stringify(response.data, null, 2)}
                </pre>
              </Paragraph>
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
};

export default APITesting;
