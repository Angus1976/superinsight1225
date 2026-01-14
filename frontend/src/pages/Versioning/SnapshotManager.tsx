/**
 * Snapshot Manager Component
 * 
 * Manages data snapshots:
 * - Snapshot list and creation
 * - Snapshot restoration
 * - Scheduled snapshots
 * - Retention policy configuration
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  message,
  Tag,
  Tooltip,
  Popconfirm,
  Typography,
  Statistic,
  Row,
  Col,
  Tabs,
  Switch,
} from 'antd';
import {
  CameraOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CloudDownloadOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  PlusOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  snapshotApi,
  Snapshot,
  SnapshotSchedule,
  SnapshotStatistics,
} from '../../services/snapshotApi';

const { Text, Title } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface SnapshotManagerProps {
  entityType?: string;
  entityId?: string;
  tenantId?: string;
  data?: Record<string, unknown>;
}

const SnapshotManager: React.FC<SnapshotManagerProps> = ({
  entityType,
  entityId,
  tenantId,
  data,
}) => {
  const { t } = useTranslation();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [statistics, setStatistics] = useState<SnapshotStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [retentionModalVisible, setRetentionModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [scheduleForm] = Form.useForm();
  const [retentionForm] = Form.useForm();

  useEffect(() => {
    loadSnapshots();
    loadStatistics();
  }, [entityType, entityId, tenantId]);

  const loadSnapshots = async () => {
    setLoading(true);
    try {
      const result = await snapshotApi.listSnapshots({
        entity_type: entityType,
        entity_id: entityId,
        tenant_id: tenantId,
        limit: 50,
      });
      setSnapshots(result.snapshots);
    } catch (error) {
      message.error(t('snapshot.loadError', 'Failed to load snapshots'));
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const result = await snapshotApi.getStatistics(tenantId);
      setStatistics(result.statistics);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  const handleCreateSnapshot = async (values: {
    snapshot_type: 'full' | 'incremental';
    expires_at?: string;
  }) => {
    if (!entityType || !entityId || !data) {
      message.error(t('snapshot.missingData', 'Entity type, ID, and data are required'));
      return;
    }

    try {
      await snapshotApi.createSnapshot(
        entityType,
        entityId,
        data,
        values.snapshot_type,
        undefined,
        values.expires_at,
        undefined,
        tenantId
      );
      message.success(t('snapshot.created', 'Snapshot created successfully'));
      setCreateModalVisible(false);
      form.resetFields();
      loadSnapshots();
      loadStatistics();
    } catch (error) {
      message.error(t('snapshot.createError', 'Failed to create snapshot'));
    }
  };

  const handleRestore = async (snapshot: Snapshot) => {
    try {
      const result = await snapshotApi.restoreSnapshot(
        snapshot.id,
        undefined,
        tenantId
      );
      message.success(t('snapshot.restored', 'Snapshot restored successfully'));
      console.log('Restored data:', result.data);
    } catch (error) {
      message.error(t('snapshot.restoreError', 'Failed to restore snapshot'));
    }
  };

  const handleDelete = async (snapshotId: string) => {
    try {
      await snapshotApi.deleteSnapshot(snapshotId, tenantId);
      message.success(t('snapshot.deleted', 'Snapshot deleted'));
      loadSnapshots();
      loadStatistics();
    } catch (error) {
      message.error(t('snapshot.deleteError', 'Failed to delete snapshot'));
    }
  };

  const handleCreateSchedule = async (values: {
    schedule: string;
    snapshot_type: 'full' | 'incremental';
    retention_days: number;
    max_snapshots: number;
  }) => {
    if (!entityType || !entityId) {
      message.error(t('snapshot.missingEntity', 'Entity type and ID are required'));
      return;
    }

    try {
      await snapshotApi.createSchedule(
        entityType,
        entityId,
        values.schedule,
        values.snapshot_type,
        values.retention_days,
        values.max_snapshots,
        undefined,
        tenantId
      );
      message.success(t('snapshot.scheduleCreated', 'Schedule created successfully'));
      setScheduleModalVisible(false);
      scheduleForm.resetFields();
    } catch (error) {
      message.error(t('snapshot.scheduleError', 'Failed to create schedule'));
    }
  };

  const handleApplyRetention = async (values: {
    max_age_days: number;
    max_count: number;
    keep_tagged: boolean;
  }) => {
    if (!entityType || !entityId) {
      message.error(t('snapshot.missingEntity', 'Entity type and ID are required'));
      return;
    }

    try {
      const result = await snapshotApi.applyRetentionPolicy(
        entityType,
        entityId,
        values,
        tenantId
      );
      message.success(
        t('snapshot.retentionApplied', `Deleted ${result.deleted_count} snapshots`)
      );
      setRetentionModalVisible(false);
      retentionForm.resetFields();
      loadSnapshots();
      loadStatistics();
    } catch (error) {
      message.error(t('snapshot.retentionError', 'Failed to apply retention policy'));
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const columns = [
    {
      title: t('snapshot.id', 'ID'),
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text copyable={{ text: id }}>{id.slice(0, 8)}...</Text>
        </Tooltip>
      ),
    },
    {
      title: t('snapshot.type', 'Type'),
      dataIndex: 'snapshot_type',
      key: 'snapshot_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'full' ? 'blue' : 'green'}>{type}</Tag>
      ),
    },
    {
      title: t('snapshot.entity', 'Entity'),
      key: 'entity',
      width: 200,
      render: (_: unknown, record: Snapshot) => (
        <Text>{`${record.entity_type}:${record.entity_id.slice(0, 8)}`}</Text>
      ),
    },
    {
      title: t('snapshot.size', 'Size'),
      dataIndex: 'size_bytes',
      key: 'size_bytes',
      width: 100,
      render: (size: number) => formatBytes(size),
    },
    {
      title: t('snapshot.createdAt', 'Created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDate(date),
    },
    {
      title: t('snapshot.expiresAt', 'Expires'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 180,
      render: (date: string | null) =>
        date ? (
          <Text type={new Date(date) < new Date() ? 'danger' : 'secondary'}>
            {formatDate(date)}
          </Text>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: t('snapshot.actions', 'Actions'),
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Snapshot) => (
        <Space>
          <Tooltip title={t('snapshot.restore', 'Restore')}>
            <Popconfirm
              title={t('snapshot.restoreConfirm', 'Restore this snapshot?')}
              onConfirm={() => handleRestore(record)}
            >
              <Button size="small" icon={<CloudDownloadOutlined />} />
            </Popconfirm>
          </Tooltip>
          <Tooltip title={t('snapshot.delete', 'Delete')}>
            <Popconfirm
              title={t('snapshot.deleteConfirm', 'Delete this snapshot?')}
              onConfirm={() => handleDelete(record.id)}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <CameraOutlined />
          <span>{t('snapshot.manager', 'Snapshot Manager')}</span>
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
            disabled={!entityType || !entityId || !data}
          >
            {t('snapshot.create', 'Create')}
          </Button>
          <Button
            icon={<ClockCircleOutlined />}
            onClick={() => setScheduleModalVisible(true)}
            disabled={!entityType || !entityId}
          >
            {t('snapshot.schedule', 'Schedule')}
          </Button>
          <Button
            icon={<SettingOutlined />}
            onClick={() => setRetentionModalVisible(true)}
            disabled={!entityType || !entityId}
          >
            {t('snapshot.retention', 'Retention')}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadSnapshots}>
            {t('common.refresh', 'Refresh')}
          </Button>
        </Space>
      }
    >
      {/* Statistics */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('snapshot.totalSnapshots', 'Total Snapshots')}
                value={statistics.total_snapshots}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('snapshot.totalSize', 'Total Size')}
                value={formatBytes(statistics.total_size_bytes)}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Space>
                {Object.entries(statistics.by_type || {}).map(([type, count]) => (
                  <Tag key={type} color={type === 'full' ? 'blue' : 'green'}>
                    {type}: {count}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      {/* Snapshots Table */}
      <Table
        dataSource={snapshots}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        size="small"
      />

      {/* Create Snapshot Modal */}
      <Modal
        title={t('snapshot.createSnapshot', 'Create Snapshot')}
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleCreateSnapshot} layout="vertical">
          <Form.Item
            name="snapshot_type"
            label={t('snapshot.type', 'Type')}
            initialValue="full"
          >
            <Select>
              <Option value="full">{t('snapshot.full', 'Full')}</Option>
              <Option value="incremental">{t('snapshot.incremental', 'Incremental')}</Option>
            </Select>
          </Form.Item>
          <Form.Item name="expires_at" label={t('snapshot.expiresAt', 'Expires At')}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {t('snapshot.create', 'Create')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Schedule Modal */}
      <Modal
        title={t('snapshot.createSchedule', 'Create Schedule')}
        open={scheduleModalVisible}
        onCancel={() => setScheduleModalVisible(false)}
        footer={null}
      >
        <Form form={scheduleForm} onFinish={handleCreateSchedule} layout="vertical">
          <Form.Item
            name="schedule"
            label={t('snapshot.cronExpression', 'Cron Expression')}
            rules={[{ required: true }]}
            extra={t('snapshot.cronHelp', 'e.g., 0 0 * * * (daily at midnight)')}
          >
            <Input placeholder="0 0 * * *" />
          </Form.Item>
          <Form.Item
            name="snapshot_type"
            label={t('snapshot.type', 'Type')}
            initialValue="full"
          >
            <Select>
              <Option value="full">{t('snapshot.full', 'Full')}</Option>
              <Option value="incremental">{t('snapshot.incremental', 'Incremental')}</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="retention_days"
            label={t('snapshot.retentionDays', 'Retention Days')}
            initialValue={90}
          >
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="max_snapshots"
            label={t('snapshot.maxSnapshots', 'Max Snapshots')}
            initialValue={100}
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {t('snapshot.createSchedule', 'Create Schedule')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Retention Policy Modal */}
      <Modal
        title={t('snapshot.applyRetention', 'Apply Retention Policy')}
        open={retentionModalVisible}
        onCancel={() => setRetentionModalVisible(false)}
        footer={null}
      >
        <Form form={retentionForm} onFinish={handleApplyRetention} layout="vertical">
          <Form.Item
            name="max_age_days"
            label={t('snapshot.maxAgeDays', 'Max Age (Days)')}
            initialValue={90}
          >
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="max_count"
            label={t('snapshot.maxCount', 'Max Count')}
            initialValue={100}
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="keep_tagged"
            label={t('snapshot.keepTagged', 'Keep Tagged')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block danger>
              {t('snapshot.applyRetention', 'Apply Retention Policy')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default SnapshotManager;
