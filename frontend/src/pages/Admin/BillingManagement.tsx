/**
 * Billing Management Page
 * 
 * Provides billing management including:
 * - Billing details
 * - Usage reports
 * - Report export
 * - Invoice management
 */

import React, { useState } from 'react';
import { 
  Card, Table, Button, Space, Tag, DatePicker, Select, 
  Row, Col, Statistic, Tabs, message
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  DollarOutlined, DownloadOutlined, FileTextOutlined,
  ReloadOutlined, CalendarOutlined, RiseOutlined, FallOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { tenantApi, quotaApi, Tenant } from '@/services/multiTenantApi';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface BillingRecord {
  id: string;
  tenant_id: string;
  tenant_name: string;
  period: string;
  storage_usage_gb: number;
  storage_cost: number;
  api_calls: number;
  api_cost: number;
  user_count: number;
  user_cost: number;
  total_cost: number;
  status: 'pending' | 'paid' | 'overdue';
  created_at: string;
}

const BillingManagement: React.FC = () => {
  const { t } = useTranslation('admin');
  const [selectedTenantId, setSelectedTenantId] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  // Fetch tenants
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantApi.list().then(res => res.data),
  });

  // Mock billing data (in real implementation, this would come from API)
  const billingData: BillingRecord[] = tenants?.map((tenant, index) => ({
    id: `bill-${tenant.id}`,
    tenant_id: tenant.id,
    tenant_name: tenant.name,
    period: '2026-01',
    storage_usage_gb: Math.random() * 50,
    storage_cost: Math.random() * 100,
    api_calls: Math.floor(Math.random() * 100000),
    api_cost: Math.random() * 200,
    user_count: Math.floor(Math.random() * 50),
    user_cost: Math.random() * 150,
    total_cost: Math.random() * 500,
    status: ['pending', 'paid', 'overdue'][index % 3] as any,
    created_at: new Date().toISOString(),
  })) || [];

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; text: string }> = {
      pending: { color: 'processing', text: t('billingManagement.status.pending') },
      paid: { color: 'success', text: t('billingManagement.status.paid') },
      overdue: { color: 'error', text: t('billingManagement.status.overdue') },
    };
    const { color, text } = config[status] || config.pending;
    return <Tag color={color}>{text}</Tag>;
  };

  const columns: ColumnsType<BillingRecord> = [
    {
      title: t('billingManagement.columns.tenant'),
      dataIndex: 'tenant_name',
      key: 'tenant_name',
    },
    {
      title: t('billingManagement.columns.period'),
      dataIndex: 'period',
      key: 'period',
      render: (period: string) => <Tag icon={<CalendarOutlined />}>{period}</Tag>,
    },
    {
      title: t('billingManagement.columns.storage'),
      key: 'storage',
      render: (_, record) => (
        <div>
          <div>¥{record.storage_cost.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.storage_usage_gb.toFixed(2)} GB
          </div>
        </div>
      ),
    },
    {
      title: t('billingManagement.columns.api'),
      key: 'api',
      render: (_, record) => (
        <div>
          <div>¥{record.api_cost.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.api_calls.toLocaleString()} {t('billingManagement.unit.calls')}
          </div>
        </div>
      ),
    },
    {
      title: t('billingManagement.columns.user'),
      key: 'user',
      render: (_, record) => (
        <div>
          <div>¥{record.user_cost.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.user_count} {t('billingManagement.unit.users')}
          </div>
        </div>
      ),
    },
    {
      title: t('billingManagement.columns.total'),
      dataIndex: 'total_cost',
      key: 'total_cost',
      render: (cost: number) => (
        <span style={{ fontWeight: 'bold', color: '#1890ff' }}>
          ¥{cost.toFixed(2)}
        </span>
      ),
      sorter: (a, b) => a.total_cost - b.total_cost,
    },
    {
      title: t('billingManagement.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
      filters: [
        { text: t('billingManagement.status.pending'), value: 'pending' },
        { text: t('billingManagement.status.paid'), value: 'paid' },
        { text: t('billingManagement.status.overdue'), value: 'overdue' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('billingManagement.columns.actions'),
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<FileTextOutlined />}>
            {t('billingManagement.actions.details')}
          </Button>
          <Button type="link" size="small" icon={<DownloadOutlined />}>
            {t('billingManagement.actions.download')}
          </Button>
        </Space>
      ),
    },
  ];


  // Calculate summary
  const totalRevenue = billingData.reduce((sum, b) => sum + b.total_cost, 0);
  const pendingAmount = billingData.filter(b => b.status === 'pending').reduce((sum, b) => sum + b.total_cost, 0);
  const overdueAmount = billingData.filter(b => b.status === 'overdue').reduce((sum, b) => sum + b.total_cost, 0);
  const paidAmount = billingData.filter(b => b.status === 'paid').reduce((sum, b) => sum + b.total_cost, 0);

  const handleExport = (format: 'csv' | 'excel' | 'pdf') => {
    message.success(t('billingManagement.export.exporting', { format: format.toUpperCase() }));
    // In real implementation, this would trigger a download
  };

  return (
    <div className="billing-management">
      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('billingManagement.summary.monthlyRevenue')}
              value={totalRevenue}
              precision={2}
              prefix={<DollarOutlined />}
              suffix={t('billingManagement.unit.currency')}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('billingManagement.summary.paid')}
              value={paidAmount}
              precision={2}
              valueStyle={{ color: '#3f8600' }}
              prefix={<RiseOutlined />}
              suffix={t('billingManagement.unit.currency')}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('billingManagement.summary.pending')}
              value={pendingAmount}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
              suffix={t('billingManagement.unit.currency')}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('billingManagement.summary.overdue')}
              value={overdueAmount}
              precision={2}
              valueStyle={{ color: '#cf1322' }}
              prefix={<FallOutlined />}
              suffix={t('billingManagement.unit.currency')}
            />
          </Card>
        </Col>
      </Row>

      {/* Billing Table */}
      <Card
        title={t('billingManagement.title')}
        extra={
          <Space>
            <Select
              placeholder={t('billingManagement.columns.tenant')}
              style={{ width: 150 }}
              allowClear
              onChange={setSelectedTenantId}
            >
              {tenants?.map(t => (
                <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
              ))}
            </Select>
            <RangePicker
              picker="month"
              onChange={(dates) => setDateRange(dates as any)}
            />
            <Button icon={<ReloadOutlined />}>{t('common.refresh')}</Button>
            <Button.Group>
              <Button icon={<DownloadOutlined />} onClick={() => handleExport('csv')}>
                {t('billingManagement.export.csv')}
              </Button>
              <Button onClick={() => handleExport('excel')}>{t('billingManagement.export.excel')}</Button>
              <Button onClick={() => handleExport('pdf')}>{t('billingManagement.export.pdf')}</Button>
            </Button.Group>
          </Space>
        }
      >
        <Tabs defaultActiveKey="all">
          <Tabs.TabPane tab={t('billingManagement.tabs.all')} key="all">
            <Table
              columns={columns}
              dataSource={billingData}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showTotal: (total) => t('billingManagement.pagination.total', { total }),
              }}
              summary={(pageData) => {
                const total = pageData.reduce((sum, record) => sum + record.total_cost, 0);
                return (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={5}>
                      <strong>{t('billingManagement.summary.pageTotal')}</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={5}>
                      <strong style={{ color: '#1890ff' }}>¥{total.toFixed(2)}</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={6} colSpan={2} />
                  </Table.Summary.Row>
                );
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab={t('billingManagement.tabs.pending')} key="pending">
            <Table
              columns={columns}
              dataSource={billingData.filter(b => b.status === 'pending')}
              rowKey="id"
              pagination={false}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab={t('billingManagement.tabs.paid')} key="paid">
            <Table
              columns={columns}
              dataSource={billingData.filter(b => b.status === 'paid')}
              rowKey="id"
              pagination={false}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab={t('billingManagement.tabs.overdue')} key="overdue">
            <Table
              columns={columns}
              dataSource={billingData.filter(b => b.status === 'overdue')}
              rowKey="id"
              pagination={false}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* Usage Breakdown */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title={t('billingManagement.charts.storageDistribution')} size="small">
            <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
              图表区域 - 存储费用饼图
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title={t('billingManagement.charts.apiTrend')} size="small">
            <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
              图表区域 - API 调用折线图
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title={t('billingManagement.charts.revenueTrend')} size="small">
            <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
              图表区域 - 收入柱状图
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default BillingManagement;
