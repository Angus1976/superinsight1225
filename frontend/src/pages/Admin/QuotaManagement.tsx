/**
 * Quota Management Page
 * 
 * Provides quota management including:
 * - Quota dashboard
 * - Usage trend charts
 * - Alert configuration
 * - Quota adjustment
 */

import React, { useState } from 'react';
import { 
  Card, Table, Button, Space, Tag, Modal, Form, InputNumber, Select, 
  message, Progress, Row, Col, Statistic, Alert, Tabs
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  DatabaseOutlined, CloudOutlined, TeamOutlined, ApiOutlined,
  ReloadOutlined, SettingOutlined, WarningOutlined, EditOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  quotaApi, tenantApi,
  Tenant, QuotaResponse, QuotaUsage, QuotaConfig, EntityType
} from '@/services/multiTenantApi';

const QuotaManagement: React.FC = () => {
  const { t } = useTranslation('admin');
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<{ id: string; type: EntityType; name: string } | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch tenants
  const { data: tenants, isLoading: tenantsLoading, refetch } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantApi.list().then(res => res.data),
  });

  // Fetch quota and usage for each tenant
  const tenantQuotas = useQuery({
    queryKey: ['tenant-quotas', tenants?.map(t => t.id)],
    queryFn: async () => {
      if (!tenants) return [];
      const results = await Promise.all(
        tenants.map(async (tenant) => {
          try {
            const [quotaRes, usageRes] = await Promise.all([
              quotaApi.get('tenant', tenant.id),
              quotaApi.getUsage('tenant', tenant.id),
            ]);
            return {
              tenant,
              quota: quotaRes.data,
              usage: usageRes.data,
            };
          } catch {
            return { tenant, quota: null, usage: null };
          }
        })
      );
      return results;
    },
    enabled: !!tenants && tenants.length > 0,
  });

  // Update quota mutation
  const updateQuotaMutation = useMutation({
    mutationFn: ({ entityType, entityId, data }: { entityType: EntityType; entityId: string; data: QuotaConfig }) =>
      quotaApi.set(entityType, entityId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-quotas'] });
      setIsEditModalVisible(false);
      form.resetFields();
      message.success(t('quotaManagement.updateSuccess'));
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || t('quotaManagement.updateFailed'));
    },
  });

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const getUsagePercent = (used: number, total: number) => {
    if (!total) return 0;
    return Math.round((used / total) * 100);
  };

  const getProgressStatus = (percent: number): 'success' | 'normal' | 'exception' => {
    if (percent >= 90) return 'exception';
    if (percent >= 70) return 'normal';
    return 'success';
  };


  const columns: ColumnsType<any> = [
    {
      title: t('quotaManagement.columns.tenant'),
      key: 'tenant',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.tenant.name}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            {record.tenant.plan}
          </div>
        </div>
      ),
    },
    {
      title: t('quotaManagement.columns.storage'),
      key: 'storage',
      render: (_, record) => {
        if (!record.quota || !record.usage) return '-';
        const percent = getUsagePercent(record.usage.storage_bytes, record.quota.storage_bytes);
        return (
          <div style={{ width: 150 }}>
            <Progress
              percent={percent}
              size="small"
              status={getProgressStatus(percent)}
            />
            <div style={{ fontSize: 11, color: '#666' }}>
              {formatBytes(record.usage.storage_bytes)} / {formatBytes(record.quota.storage_bytes)}
            </div>
          </div>
        );
      },
    },
    {
      title: t('quotaManagement.columns.projects'),
      key: 'projects',
      render: (_, record) => {
        if (!record.quota || !record.usage) return '-';
        const percent = getUsagePercent(record.usage.project_count, record.quota.project_count);
        return (
          <div style={{ width: 120 }}>
            <Progress
              percent={percent}
              size="small"
              status={getProgressStatus(percent)}
            />
            <div style={{ fontSize: 11, color: '#666' }}>
              {record.usage.project_count} / {record.quota.project_count}
            </div>
          </div>
        );
      },
    },
    {
      title: t('quotaManagement.columns.users'),
      key: 'users',
      render: (_, record) => {
        if (!record.quota || !record.usage) return '-';
        const percent = getUsagePercent(record.usage.user_count, record.quota.user_count);
        return (
          <div style={{ width: 120 }}>
            <Progress
              percent={percent}
              size="small"
              status={getProgressStatus(percent)}
            />
            <div style={{ fontSize: 11, color: '#666' }}>
              {record.usage.user_count} / {record.quota.user_count}
            </div>
          </div>
        );
      },
    },
    {
      title: t('quotaManagement.columns.apiCalls'),
      key: 'api',
      render: (_, record) => {
        if (!record.quota || !record.usage) return '-';
        const percent = getUsagePercent(record.usage.api_call_count, record.quota.api_call_count);
        return (
          <div style={{ width: 120 }}>
            <Progress
              percent={percent}
              size="small"
              status={getProgressStatus(percent)}
            />
            <div style={{ fontSize: 11, color: '#666' }}>
              {record.usage.api_call_count.toLocaleString()} / {record.quota.api_call_count.toLocaleString()}
            </div>
          </div>
        );
      },
    },
    {
      title: t('quotaManagement.columns.status'),
      key: 'status',
      render: (_, record) => {
        if (!record.quota || !record.usage) return <Tag>{t('quotaManagement.status.notConfigured')}</Tag>;
        const maxPercent = Math.max(
          getUsagePercent(record.usage.storage_bytes, record.quota.storage_bytes),
          getUsagePercent(record.usage.project_count, record.quota.project_count),
          getUsagePercent(record.usage.user_count, record.quota.user_count),
          getUsagePercent(record.usage.api_call_count, record.quota.api_call_count)
        );
        if (maxPercent >= 90) return <Tag color="error" icon={<WarningOutlined />}>{t('quotaManagement.statusTags.quotaTight')}</Tag>;
        if (maxPercent >= 70) return <Tag color="warning">{t('quotaManagement.statusTags.approachingLimit')}</Tag>;
        return <Tag color="success">{t('quotaManagement.statusTags.normal')}</Tag>;
      },
    },
    {
      title: t('quotaManagement.columns.actions'),
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => {
            setSelectedEntity({ id: record.tenant.id, type: 'tenant', name: record.tenant.name });
            if (record.quota) {
              form.setFieldsValue({
                storage_gb: record.quota.storage_bytes / 1024 / 1024 / 1024,
                project_count: record.quota.project_count,
                user_count: record.quota.user_count,
                api_call_count: record.quota.api_call_count,
              });
            }
            setIsEditModalVisible(true);
          }}
        >
          {t('quotaManagement.actions.adjustQuota')}
        </Button>
      ),
    },
  ];

  // Calculate summary stats
  const summaryStats = tenantQuotas.data?.reduce(
    (acc, item) => {
      if (item.usage) {
        acc.totalStorage += item.usage.storage_bytes;
        acc.totalProjects += item.usage.project_count;
        acc.totalUsers += item.usage.user_count;
        acc.totalApiCalls += item.usage.api_call_count;
      }
      return acc;
    },
    { totalStorage: 0, totalProjects: 0, totalUsers: 0, totalApiCalls: 0 }
  ) || { totalStorage: 0, totalProjects: 0, totalUsers: 0, totalApiCalls: 0 };

  const warningTenants = tenantQuotas.data?.filter(item => {
    if (!item.quota || !item.usage) return false;
    return (
      getUsagePercent(item.usage.storage_bytes, item.quota.storage_bytes) >= 80 ||
      getUsagePercent(item.usage.project_count, item.quota.project_count) >= 80 ||
      getUsagePercent(item.usage.user_count, item.quota.user_count) >= 80 ||
      getUsagePercent(item.usage.api_call_count, item.quota.api_call_count) >= 80
    );
  }) || [];

  const handleSubmit = (values: any) => {
    if (!selectedEntity) return;
    updateQuotaMutation.mutate({
      entityType: selectedEntity.type,
      entityId: selectedEntity.id,
      data: {
        storage_bytes: values.storage_gb * 1024 * 1024 * 1024,
        project_count: values.project_count,
        user_count: values.user_count,
        api_call_count: values.api_call_count,
      },
    });
  };

  return (
    <div className="quota-management">
      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quotaManagement.statistics.totalStorage')}
              value={formatBytes(summaryStats.totalStorage)}
              prefix={<CloudOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quotaManagement.statistics.totalProjects')}
              value={summaryStats.totalProjects}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quotaManagement.statistics.totalUsers')}
              value={summaryStats.totalUsers}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('quotaManagement.statistics.totalApiCalls')}
              value={summaryStats.totalApiCalls.toLocaleString()}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Warnings */}
      {warningTenants.length > 0 && (
        <Alert
          message={t('quotaManagement.alert.quotaWarning', { count: warningTenants.length })}
          description={
            <Space wrap>
              {warningTenants.map(item => (
                <Tag key={item.tenant.id} color="warning">{item.tenant.name}</Tag>
              ))}
            </Space>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Quota Table */}
      <Card
        title={t('quotaManagement.title')}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('quotaManagement.buttons.refresh')}
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tenantQuotas.data || []}
          loading={tenantsLoading || tenantQuotas.isLoading}
          rowKey={(record) => record.tenant.id}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => t('quotaManagement.pagination.total', { total }),
          }}
        />
      </Card>

      {/* Edit Quota Modal */}
      <Modal
        title={t('quotaManagement.modal.adjustQuota', { name: selectedEntity?.name || '' })}
        open={isEditModalVisible}
        onCancel={() => setIsEditModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={updateQuotaMutation.isPending}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="storage_gb"
            label={t('quotaManagement.form.storageQuota')}
            rules={[{ required: true, message: t('quotaManagement.form.storageQuotaRequired') }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="project_count"
            label={t('quotaManagement.form.projectQuota')}
            rules={[{ required: true, message: t('quotaManagement.form.projectQuotaRequired') }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="user_count"
            label={t('quotaManagement.form.userQuota')}
            rules={[{ required: true, message: t('quotaManagement.form.userQuotaRequired') }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="api_call_count"
            label={t('quotaManagement.form.apiQuota')}
            rules={[{ required: true, message: t('quotaManagement.form.apiQuotaRequired') }]}
          >
            <InputNumber min={1000} max={100000000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QuotaManagement;
