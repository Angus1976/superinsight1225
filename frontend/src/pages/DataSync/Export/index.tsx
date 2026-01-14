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
      title: '导出ID',
      dataIndex: 'id',
      key: 'id',
      render: (text) => <code>{text}</code>,
    },
    {
      title: '数据源',
      dataIndex: 'sourceName',
      key: 'sourceName',
    },
    {
      title: '格式',
      dataIndex: 'format',
      key: 'format',
      render: (format) => <Tag>{formatLabels[format] || format}</Tag>,
    },
    {
      title: '状态',
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
      title: '行数',
      dataIndex: 'totalRows',
      key: 'totalRows',
      render: (count) => count > 0 ? count.toLocaleString() : '-',
    },
    {
      title: '大小',
      dataIndex: 'totalSizeBytes',
      key: 'totalSizeBytes',
      render: formatSize,
    },
    {
      title: '文件数',
      dataIndex: 'files',
      key: 'files',
      render: (files) => files.length || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
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
              下载
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
    message.success('开始下载导出文件');
  };

  const handleDelete = (exportId: string) => {
    setExports(exports.filter(e => e.id !== exportId));
    message.success('导出记录已删除');
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
    message.success('导出任务已创建');

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
        AI 友好数据导出
      </Title>

      <Alert
        message="AI 友好导出"
        description="支持多种 AI/ML 训练格式，包括数据分割、语义增强和自动脱敏功能。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总导出数" value={exports.length} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已完成" value={completedExports} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总行数" value={totalRows} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总大小" value={formatSize(totalSize)} />
          </Card>
        </Col>
      </Row>

      <Card
        title="导出记录"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />}>刷新</Button>
            <Button type="primary" icon={<ExportOutlined />} onClick={() => setIsModalVisible(true)}>
              新建导出
            </Button>
          </Space>
        }
      >
        <Table columns={columns} dataSource={exports} rowKey="id" />
      </Card>

      <Modal
        title="创建数据导出"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateExport}>
          <Form.Item name="sourceId" label="数据源">
            <Select placeholder="选择数据源（可选，不选则导出全部）" allowClear>
              <Option value="ds_1">Production DB</Option>
              <Option value="ds_2">Orders DB</Option>
            </Select>
          </Form.Item>

          <Form.Item name="format" label="导出格式" rules={[{ required: true }]}>
            <Select placeholder="选择导出格式">
              <Option value="json">JSON - 通用格式</Option>
              <Option value="csv">CSV - 表格格式</Option>
              <Option value="jsonl">JSON Lines - 流式处理</Option>
              <Option value="coco">COCO - 目标检测</Option>
              <Option value="pascal_voc">Pascal VOC - 图像标注</Option>
            </Select>
          </Form.Item>

          <Divider>数据分割配置</Divider>

          <Form.Item name="enableSplit" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="启用分割" unCheckedChildren="不分割" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label={`训练集 (${splitRatios.train}%)`}>
                <Slider
                  value={splitRatios.train}
                  onChange={(v) => handleSplitChange('train', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={`验证集 (${splitRatios.val}%)`}>
                <Slider
                  value={splitRatios.val}
                  onChange={(v) => handleSplitChange('val', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label={`测试集 (${splitRatios.test}%)`}>
                <Slider
                  value={splitRatios.test}
                  onChange={(v) => handleSplitChange('test', v)}
                  max={100}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider>高级选项</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="includeSemantics" valuePropName="checked" initialValue={true}>
                <Switch checkedChildren="包含语义信息" unCheckedChildren="不包含" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="desensitize" valuePropName="checked" initialValue={false}>
                <Switch checkedChildren="启用脱敏" unCheckedChildren="不脱敏" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="shuffle" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="随机打乱" unCheckedChildren="保持顺序" />
          </Form.Item>

          <Form.Item name="seed" label="随机种子" initialValue={42}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<ExportOutlined />}>
                开始导出
              </Button>
              <Button onClick={() => setIsModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ExportConfig;
