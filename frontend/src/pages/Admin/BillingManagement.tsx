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
      pending: { color: 'processing', text: '待支付' },
      paid: { color: 'success', text: '已支付' },
      overdue: { color: 'error', text: '逾期' },
    };
    const { color, text } = config[status] || config.pending;
    return <Tag color={color}>{text}</Tag>;
  };

  const columns: ColumnsType<BillingRecord> = [
    {
      title: '租户',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
    },
    {
      title: '账期',
      dataIndex: 'period',
      key: 'period',
      render: (period: string) => <Tag icon={<CalendarOutlined />}>{period}</Tag>,
    },
    {
      title: '存储费用',
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
      title: 'API 费用',
      key: 'api',
      render: (_, record) => (
        <div>
          <div>¥{record.api_cost.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.api_calls.toLocaleString()} 次
          </div>
        </div>
      ),
    },
    {
      title: '用户费用',
      key: 'user',
      render: (_, record) => (
        <div>
          <div>¥{record.user_cost.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.user_count} 人
          </div>
        </div>
      ),
    },
    {
      title: '总费用',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
      filters: [
        { text: '待支付', value: 'pending' },
        { text: '已支付', value: 'paid' },
        { text: '逾期', value: 'overdue' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<FileTextOutlined />}>
            详情
          </Button>
          <Button type="link" size="small" icon={<DownloadOutlined />}>
            下载
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
    message.success(`正在导出 ${format.toUpperCase()} 格式报表...`);
    // In real implementation, this would trigger a download
  };

  return (
    <div className="billing-management">
      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="本月总收入"
              value={totalRevenue}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已收款"
              value={paidAmount}
              precision={2}
              valueStyle={{ color: '#3f8600' }}
              prefix={<RiseOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待收款"
              value={pendingAmount}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
              suffix="元"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="逾期金额"
              value={overdueAmount}
              precision={2}
              valueStyle={{ color: '#cf1322' }}
              prefix={<FallOutlined />}
              suffix="元"
            />
          </Card>
        </Col>
      </Row>

      {/* Billing Table */}
      <Card
        title="账单管理"
        extra={
          <Space>
            <Select
              placeholder="选择租户"
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
            <Button icon={<ReloadOutlined />}>刷新</Button>
            <Button.Group>
              <Button icon={<DownloadOutlined />} onClick={() => handleExport('csv')}>
                CSV
              </Button>
              <Button onClick={() => handleExport('excel')}>Excel</Button>
              <Button onClick={() => handleExport('pdf')}>PDF</Button>
            </Button.Group>
          </Space>
        }
      >
        <Tabs defaultActiveKey="all">
          <Tabs.TabPane tab="全部账单" key="all">
            <Table
              columns={columns}
              dataSource={billingData}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条账单`,
              }}
              summary={(pageData) => {
                const total = pageData.reduce((sum, record) => sum + record.total_cost, 0);
                return (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={5}>
                      <strong>本页合计</strong>
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
          <Tabs.TabPane tab="待支付" key="pending">
            <Table
              columns={columns}
              dataSource={billingData.filter(b => b.status === 'pending')}
              rowKey="id"
              pagination={false}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="已支付" key="paid">
            <Table
              columns={columns}
              dataSource={billingData.filter(b => b.status === 'paid')}
              rowKey="id"
              pagination={false}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="逾期" key="overdue">
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
          <Card title="存储费用分布" size="small">
            <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
              图表区域 - 存储费用饼图
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="API 调用趋势" size="small">
            <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
              图表区域 - API 调用折线图
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="收入趋势" size="small">
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
