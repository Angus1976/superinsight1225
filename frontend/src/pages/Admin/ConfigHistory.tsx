/**
 * Admin Configuration History Page
 * 
 * Provides interface for viewing configuration change history,
 * comparing differences, and rolling back to previous versions.
 * 
 * **Requirement 6.1, 6.2, 6.3, 6.4, 6.5: Configuration History**
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Tag,
  Tooltip,
  message,
  Typography,
  Alert,
  DatePicker,
  Select,
  Row,
  Col,
  Descriptions,
  Popconfirm,
  Input,
  Empty,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  DiffOutlined,
  SearchOutlined,
  ReloadOutlined,
  UserOutlined,
  ClockCircleOutlined,
  PlusOutlined,
  MinusOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useTranslation } from 'react-i18next';
import {
  adminApi,
  ConfigHistoryResponse,
  ConfigDiff,
  ConfigType,
  getConfigTypeName,
} from '@/services/adminApi';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

const CONFIG_TYPES: ConfigType[] = ['llm', 'database', 'sync_strategy', 'third_party'];

const ConfigHistory: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [filters, setFilters] = useState<{
    config_type?: ConfigType;
    start_time?: string;
    end_time?: string;
  }>({});
  const [diffModalVisible, setDiffModalVisible] = useState(false);
  const [rollbackModalVisible, setRollbackModalVisible] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState<ConfigHistoryResponse | null>(null);
  const [selectedDiff, setSelectedDiff] = useState<ConfigDiff | null>(null);
  const [rollbackReason, setRollbackReason] = useState('');

  // Fetch history
  const { data: history = [], isLoading, refetch } = useQuery({
    queryKey: ['admin-config-history', filters],
    queryFn: () => adminApi.getConfigHistory({
      ...filters,
      limit: 100,
    }),
  });

  // Fetch diff
  const fetchDiff = async (historyId: string) => {
    try {
      const diff = await adminApi.getConfigDiff(historyId);
      setSelectedDiff(diff);
      setDiffModalVisible(true);
    } catch (error) {
      message.error(t('configHistory.loadDiffFailed'));
    }
  };

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: () => {
      if (!selectedHistory) throw new Error(t('configHistory.rollbackConfirm'));
      return adminApi.rollbackConfig(
        selectedHistory.id,
        user?.id || '',
        user?.username || '',
        rollbackReason
      );
    },
    onSuccess: () => {
      message.success(t('configHistory.rollbackSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-config-history'] });
      setRollbackModalVisible(false);
      setSelectedHistory(null);
      setRollbackReason('');
    },
    onError: (error: Error) => {
      message.error(t('configHistory.rollbackFailed', { error: error.message }));
    },
  });

  const handleViewDiff = (record: ConfigHistoryResponse) => {
    setSelectedHistory(record);
    fetchDiff(record.id);
  };

  const handleRollback = (record: ConfigHistoryResponse) => {
    setSelectedHistory(record);
    setRollbackModalVisible(true);
  };

  const handleDateRangeChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setFilters(prev => ({
        ...prev,
        start_time: dates[0]!.toISOString(),
        end_time: dates[1]!.toISOString(),
      }));
    } else {
      setFilters(prev => {
        const { start_time, end_time, ...rest } = prev;
        return rest;
      });
    }
  };

  const renderDiffValue = (value: unknown): React.ReactNode => {
    if (value === null || value === undefined) {
      return <Text type="secondary">null</Text>;
    }
    if (typeof value === 'object') {
      return (
        <pre style={{ margin: 0, fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    return <Text code>{String(value)}</Text>;
  };

  const columns = [
    {
      title: t('configHistory.columns.time'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => (
        <Space>
          <ClockCircleOutlined />
          {new Date(time).toLocaleString()}
        </Space>
      ),
    },
    {
      title: t('configHistory.columns.configType'),
      dataIndex: 'config_type',
      key: 'config_type',
      width: 120,
      render: (type: ConfigType) => {
        const colors: Record<ConfigType, string> = {
          llm: 'blue',
          database: 'green',
          sync_strategy: 'purple',
          third_party: 'orange',
        };
        return <Tag color={colors[type]}>{getConfigTypeName(type)}</Tag>;
      },
    },
    {
      title: t('configHistory.columns.operationType'),
      key: 'operation',
      width: 100,
      render: (_: unknown, record: ConfigHistoryResponse) => {
        if (!record.old_value) {
          return <Tag icon={<PlusOutlined />} color="success">{t('configHistory.operations.create')}</Tag>;
        }
        return <Tag icon={<EditOutlined />} color="processing">{t('configHistory.operations.modify')}</Tag>;
      },
    },
    {
      title: t('configHistory.columns.operator'),
      dataIndex: 'user_name',
      key: 'user_name',
      width: 120,
      render: (name: string) => (
        <Space>
          <UserOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: t('configHistory.columns.summary'),
      key: 'summary',
      ellipsis: true,
      render: (_: unknown, record: ConfigHistoryResponse) => {
        const newValue = record.new_value;
        const name = newValue.name || newValue.id || t('configHistory.unnamed');
        return <Text>{name}</Text>;
      },
    },
    {
      title: t('configHistory.columns.actions'),
      key: 'actions',
      width: 150,
      render: (_: unknown, record: ConfigHistoryResponse) => (
        <Space>
          <Tooltip title={t('configHistory.tooltips.viewDiff')}>
            <Button
              type="text"
              icon={<DiffOutlined />}
              onClick={() => handleViewDiff(record)}
            />
          </Tooltip>
          <Tooltip title={t('configHistory.tooltips.rollback')}>
            <Popconfirm
              title={t('configHistory.confirm.rollback')}
              description={t('configHistory.confirm.rollbackDescription')}
              onConfirm={() => handleRollback(record)}
              okText={t('configHistory.confirm.ok')}
              cancelText={t('configHistory.confirm.cancel')}
            >
              <Button
                type="text"
                icon={<RollbackOutlined />}
                disabled={!record.old_value}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>{t('configHistory.title')}</span>
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            {t('configHistory.refresh')}
          </Button>
        }
      >
        <Alert
          message={t('configHistory.alert.description')}
          description={t('configHistory.alert.descriptionText')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Filters */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <Select
              placeholder={t('configHistory.filters.configType')}
              allowClear
              style={{ width: '100%' }}
              value={filters.config_type}
              onChange={(v) => setFilters(prev => ({ ...prev, config_type: v }))}
            >
              {CONFIG_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getConfigTypeName(type)}
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={16}>
            <RangePicker
              style={{ width: '100%' }}
              showTime
              onChange={handleDateRangeChange}
              placeholder={[t('configHistory.filters.startTime'), t('configHistory.filters.endTime')]}
            />
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={history}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      {/* Diff Modal */}
      <Modal
        title={t('configHistory.modal.diff')}
        open={diffModalVisible}
        onCancel={() => {
          setDiffModalVisible(false);
          setSelectedDiff(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDiffModalVisible(false)}>
            {t('configHistory.modal.close')}
          </Button>,
        ]}
        width={800}
      >
        {selectedDiff ? (
          <div>
            {/* Added */}
            {Object.keys(selectedDiff.added).length > 0 && (
              <Card
                size="small"
                title={<Text type="success"><PlusOutlined /> {t('configHistory.diff.added')}</Text>}
                style={{ marginBottom: 16 }}
              >
                <Descriptions column={1} size="small">
                  {Object.entries(selectedDiff.added).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {renderDiffValue(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            )}

            {/* Removed */}
            {Object.keys(selectedDiff.removed).length > 0 && (
              <Card
                size="small"
                title={<Text type="danger"><MinusOutlined /> {t('configHistory.diff.removed')}</Text>}
                style={{ marginBottom: 16 }}
              >
                <Descriptions column={1} size="small">
                  {Object.entries(selectedDiff.removed).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {renderDiffValue(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            )}

            {/* Modified */}
            {Object.keys(selectedDiff.modified).length > 0 && (
              <Card
                size="small"
                title={<Text type="warning"><EditOutlined /> {t('configHistory.diff.modified')}</Text>}
              >
                <Descriptions column={1} size="small">
                  {Object.entries(selectedDiff.modified).map(([key, value]) => {
                    const modValue = value as { old: unknown; new: unknown };
                    return (
                      <Descriptions.Item key={key} label={key}>
                        <Row gutter={16}>
                          <Col span={12}>
                            <Text type="secondary">{t('configHistory.diff.oldValue')}</Text>
                            <div>{renderDiffValue(modValue.old)}</div>
                          </Col>
                          <Col span={12}>
                            <Text type="success">{t('configHistory.diff.newValue')}</Text>
                            <div>{renderDiffValue(modValue.new)}</div>
                          </Col>
                        </Row>
                      </Descriptions.Item>
                    );
                  })}
                </Descriptions>
              </Card>
            )}

            {Object.keys(selectedDiff.added).length === 0 &&
             Object.keys(selectedDiff.removed).length === 0 &&
             Object.keys(selectedDiff.modified).length === 0 && (
              <Empty description={t('configHistory.diff.noDiff')} />
            )}
          </div>
        ) : (
          <Empty description={t('configHistory.diff.loading')} />
        )}
      </Modal>

      {/* Rollback Modal */}
      <Modal
        title={t('configHistory.modal.rollback')}
        open={rollbackModalVisible}
        onOk={() => rollbackMutation.mutate()}
        onCancel={() => {
          setRollbackModalVisible(false);
          setSelectedHistory(null);
          setRollbackReason('');
        }}
        confirmLoading={rollbackMutation.isPending}
      >
        <Alert
          message={t('configHistory.modal.rollbackWarning')}
          description={t('configHistory.modal.rollbackWarningText')}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {selectedHistory && (
          <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label={t('configHistory.rollbackInfo.configType')}>
              {getConfigTypeName(selectedHistory.config_type)}
            </Descriptions.Item>
            <Descriptions.Item label={t('configHistory.rollbackInfo.changeTime')}>
              {new Date(selectedHistory.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label={t('configHistory.rollbackInfo.operator')}>
              {selectedHistory.user_name}
            </Descriptions.Item>
          </Descriptions>
        )}

        <TextArea
          placeholder={t('configHistory.rollbackInfo.reasonPlaceholder')}
          value={rollbackReason}
          onChange={(e) => setRollbackReason(e.target.value)}
          rows={3}
        />
      </Modal>
    </div>
  );
};

export default ConfigHistory;
