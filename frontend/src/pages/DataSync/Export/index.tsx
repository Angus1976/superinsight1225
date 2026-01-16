import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Progress,
  Typography,
  Row,
  Col,
  Statistic,
  Slider,
  Divider,
  Alert,
} from 'antd';
import {
  ExportOutlined,
  DownloadOutlined,
  FileTextOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface ExportRecord {
  id: string;
  sourceId: string | null;
  sourceName: string;
  format: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  totalRows: number;
  totalSizeBytes: number;
  files: string[];
  createdAt: string;
  completedAt: string | null;
  errorMessage: string | null;
}

const ExportConfig: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [exports, setExports] = useState<ExportRecord[]>([
    {
      id: 'exp_1',
      sourceId: 'ds_1',
      sourceName: 'Production DB',
      format: 'json',
      status: 'completed',
      progress: 100,
      totalRows: 50000,
      totalSizeBytes: 15728640,
      files: ['exp_1_train.json', 'exp_1_val.json', 'exp_1_test.json'],
      createdAt: '2026-01-13T09:00:00Z',
      completedAt: '2026-01-13T09:05:30Z',
      errorMessage: null,
    },
    {
      id: 'exp_2',
      sourceId: 'ds_2',
      sourceName: 'Orders DB',
      format: 'csv',
      status: 'processing',
      progress: 65,
      totalRows: 0,
      totalSizeBytes: 0,
      files: [],
      createdAt: '2026-01-13T10:30:00Z',
      completedAt: null,
      errorMessage: null,
    },
  ]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [splitRatios, setSplitRatios] = useState({ train: 80, val: 10, test: 10 });

  const statusColors: Record<string, string> = {
    pending: 'default',
    processing: 'processing',
    completed: 'success',
    failed: 'error',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    pending: <LoadingOutlined />,
    processing: <LoadingOutlined spin />,
    completed: <CheckCircleOutlined />,
    failed: <CloseCircleOutlined />,
  };

  const formatLabels: Record<string, string> = {
    json: 'JSON',
    csv: 'CSV',
    jsonl: 'JSON Lines',
    coco: 'COCO',
    pascal_voc: 'Pascal VOC',
  };

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(2)} ${units[i]}`;
  };

  const columns: ColumnsType<ExportRecord> = [
    {
      title: t('export.exportId'),
      dataIndex: 'id',
      key: 'id',
      render: (text) => <code>{text}</code>,
    },
    {
      title: t('export.dataSource'),
      dataIndex: 'sourceName',
      key: 'sourceName',
    },
    {
      title: t('export.format'),
      dataIndex: 'format',
      key: 'format',
      render: (format) => <Tag>{formatLabels[format] || format}</Tag>,
    },
    {
      title: t('export.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => (
        <Space direction="vertical" size="small">
          <Tag icon={statusIcons[status]} color={statusColors[status]}>
            {status.toUpperCase()}
          </Tag>
          {status === 'processing' && (
            <Progress percent={record.progress} size="small" style={{ width: 100 }} />
          )}
        </Space>
      ),
    },
    {
      title: t('export.rows'),
      dataIndex: 'totalRows',
      key: 'totalRows',
      render: (count) => count > 0 ? count.toLocaleString() : '-',
    },
    {
      title: t('export.size'),
      dataIndex: 'totalSizeBytes',
      key: 'totalSizeBytes',
      render: formatSize,
    },
    {
      title: t('export.files'),
      dataIndex: 'files',
      key: 'files',
      render: (files) => files.length || '-',
    },
    {
      title: t('export.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: t('export.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'completed' && (
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.id)}
            >
              {t('export.download')}
            </Button>
          )}
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          />
        </Space>
      ),
    },
  ];

  const handleDownload = (exportId: string) => {
    message.success(t('export.downloadStarted'));
  };

  const handleDelete = (exportId: string) => {
    setExports(exports.filter(e => e.id !== exportId));
    message.success(t('export.deleted'));
  };

  const handleCreateExport = (values: any) => {
    const newExport: ExportRecord = {
      id: `exp_${Date.now()}`,
      sourceId: values.sourceId,
      sourceName: 'Selected Source',
      format: values.format,
      status: 'pending',
      progress: 0,
      totalRows: 0,
      totalSizeBytes: 0,
      files: [],
      createdAt: new Date().toISOString(),
      completedAt: null,
      errorMessage: null,
    };
    setExports([newExport, ...exports]);
    setIsModalVisible(false);
    form.resetFields();
    message.success(t('export.created'));

    // Simulate progress
    setTimeout(() => {
      setExports(prev => prev.map(e =>
        e.id === newExport.id ? { ...e, status: 'processing', progress: 30 } : e
      ));
    }, 1000);
  };

  const handleSplitChange = (type: 'train' | 'val' | 'test', value: number) => {
    const remaining = 100 - value;
    const otherTypes = ['train', 'val', 'test'].filter(t => t !== type) as ('train' | 'val' | 'test')[];
    const currentOther = splitRatios[otherTypes[0]] + splitRatios[otherTypes[1]];
    
    if (currentOther > 0) {
      const ratio = remaining / currentOther;
      setSplitRatios({
        ...splitRatios,
        [type]: value,
        [otherTypes[0]]: Math.round(splitRatios[otherTypes[0]] * ratio),
        [otherTypes[1]]: Math.round(splitRatios[otherTypes[1]] * ratio),
      });
    } else {
      setSplitRatios({
        ...splitRatios,
        [type]: value,
      });
    }
  };

  const completedExports = exports.filter(e => e.status === 'completed').length;
  const totalRows = exports.reduce((sum, e) => sum + e.totalRows, 0);
  const totalSize = exports.reduce((sum, e) => sum + e.totalSizeBytes, 0);

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <ExportOutlined style={{ marginRight: 8 }} />
        {t('export.title')}
      </Title>

      <Alert
        message={t('export.alertTitle')}
        description={t('export.alertDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('export.totalExports')} value={exports.length} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('export.completed')} value={completedExports} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('export.totalRows')} value={totalRows} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('export.totalSize')} value={formatSize(totalSize)} />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('export.records')}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />}>{t('common:refresh')}</Button>
            <Button type="primary" icon={<ExportOutlined />} onClick={() => setIsModalVisible(true)}>
              {t('export.createExport')}
            </Button>
          </Space>
        }
      >
        <Table columns={columns} dataSource={exports} rowKey="id" />
      </Card>

      <Modal
        title={t('export.createTitle')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateExport}>
          <Form.Item name="sourceId" label={t('export.dataSource')}>
            <Select placeholder={t('export.selectSource')} allowClear>
              <Option value="ds_1">Production DB</Option>
              <Option value="ds_2">Orders DB</Option>
            </Select>
          </Form.Item>

          <Form.Item name="format" label={t('export.format')} rules={[{ required: true }]}>
            <Select placeholder={t('export.selectFormat')}>
              <Option value="json">{t('export.formatJson')}</Option>
              <Option value="csv">{t('export.formatCsv')}</Option>
              <Option value="jsonl">{t('export.formatJsonl')}</Option>
              <Option value="coco">{t('export.formatCoco')}</Option>
              <Option value="pascal_voc">{t('export.formatPascalVoc')}</Option>
            </Select>
          </Form.Item>

          <Divider>{t('export.splitConfig')}</Divider>

          <Form.Item name="enableSplit" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren={t('export.enableSplit')} unCheckedChildren={t('export.noSplit')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label={`${t('export.trainSet')} (${splitRatios.train}%)`}>
                <Slider
                  value={splitRatios.train}
                  onChange={(v) => handleSplitChange('train', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={`${t('export.valSet')} (${splitRatios.val}%)`}>
                <Slider
                  value={splitRatios.val}
                  onChange={(v) => handleSplitChange('val', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={`${t('export.testSet')} (${splitRatios.test}%)`}>
                <Slider
                  value={splitRatios.test}
                  onChange={(v) => handleSplitChange('test', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider>{t('export.advancedOptions')}</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="includeSemantics" valuePropName="checked" initialValue={true}>
                <Switch checkedChildren={t('export.includeSemantics')} unCheckedChildren={t('export.noSemantics')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="desensitize" valuePropName="checked" initialValue={false}>
                <Switch checkedChildren={t('export.enableDesensitize')} unCheckedChildren={t('export.noDesensitize')} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="shuffle" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren={t('export.shuffle')} unCheckedChildren={t('export.keepOrder')} />
          </Form.Item>

          <Form.Item name="seed" label={t('export.randomSeed')} initialValue={42}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<ExportOutlined />}>
                {t('export.startExport')}
              </Button>
              <Button onClick={() => setIsModalVisible(false)}>{t('common:cancel')}</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ExportConfig;
