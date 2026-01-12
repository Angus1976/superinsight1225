import React, { useState } from 'react';
import { Card, Table, DatePicker, Select, Input, Button, Space, Tag, Tooltip, Modal, Descriptions } from 'antd';
import { SearchOutlined, EyeOutlined, DownloadOutlined, ReloadOutlined, FilterOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Search } = Input;

interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  resourceId: string;
  method: string;
  endpoint: string;
  ipAddress: string;
  userAgent: string;
  status: 'success' | 'failed' | 'warning';
  details: any;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

const SecurityAudit: React.FC = () => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'day'),
    dayjs(),
  ]);
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  const { data: auditLogs, isLoading, refetch } = useQuery({
    queryKey: ['audit-logs', dateRange, actionFilter, statusFilter, riskFilter, searchText],
    queryFn: () => api.get('/api/v1/security/audit', {
      params: {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        action: actionFilter !== 'all' ? actionFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        riskLevel: riskFilter !== 'all' ? riskFilter : undefined,
        search: searchText || undefined,
      },
    }).then(res => res.data),
  });

  const columns: ColumnsType<AuditLog> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp: string) => new Date(timestamp).toLocaleString(),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    },
    {
      title: '用户',
      dataIndex: 'userName',
      key: 'userName',
      width: 120,
      render: (userName: string, record) => (
        <Tooltip title={`用户ID: ${record.userId}`}>
          {userName}
        </Tooltip>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 150,
      render: (action: string, record) => (
        <div>
          <div>{action}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.method} {record.endpoint}
          </div>
        </div>
      ),
    },
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
      width: 120,
      render: (resource: string, record) => (
        <Tooltip title={`资源ID: ${record.resourceId}`}>
          {resource}
        </Tooltip>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors = {
          success: 'success',
          failed: 'error',
          warning: 'warning',
        };
        const labels = {
          success: '成功',
          failed: '失败',
          warning: '警告',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{labels[status as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '风险等级',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      width: 100,
      render: (riskLevel: string) => {
        const colors = {
          low: 'default',
          medium: 'processing',
          high: 'warning',
          critical: 'error',
        };
        const labels = {
          low: '低',
          medium: '中',
          high: '高',
          critical: '严重',
        };
        return <Tag color={colors[riskLevel as keyof typeof colors]}>{labels[riskLevel as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="查看详情">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedLog(record);
                setDetailModalVisible(true);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleExport = () => {
    // 导出审计日志
    const params = new URLSearchParams({
      startDate: dateRange[0].format('YYYY-MM-DD'),
      endDate: dateRange[1].format('YYYY-MM-DD'),
      action: actionFilter !== 'all' ? actionFilter : '',
      status: statusFilter !== 'all' ? statusFilter : '',
      riskLevel: riskFilter !== 'all' ? riskFilter : '',
      search: searchText || '',
    });
    
    window.open(`/api/v1/security/audit/export?${params.toString()}`);
  };

  return (
    <div className="security-audit">
      {/* 过滤器 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <span>时间范围:</span>
          <RangePicker
            value={dateRange}
            onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
          />
          
          <span>操作类型:</span>
          <Select
            value={actionFilter}
            onChange={setActionFilter}
            style={{ width: 120 }}
          >
            <Select.Option value="all">全部</Select.Option>
            <Select.Option value="login">登录</Select.Option>
            <Select.Option value="logout">登出</Select.Option>
            <Select.Option value="create">创建</Select.Option>
            <Select.Option value="update">更新</Select.Option>
            <Select.Option value="delete">删除</Select.Option>
            <Select.Option value="view">查看</Select.Option>
            <Select.Option value="export">导出</Select.Option>
          </Select>
          
          <span>状态:</span>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 100 }}
          >
            <Select.Option value="all">全部</Select.Option>
            <Select.Option value="success">成功</Select.Option>
            <Select.Option value="failed">失败</Select.Option>
            <Select.Option value="warning">警告</Select.Option>
          </Select>
          
          <span>风险等级:</span>
          <Select
            value={riskFilter}
            onChange={setRiskFilter}
            style={{ width: 100 }}
          >
            <Select.Option value="all">全部</Select.Option>
            <Select.Option value="low">低</Select.Option>
            <Select.Option value="medium">中</Select.Option>
            <Select.Option value="high">高</Select.Option>
            <Select.Option value="critical">严重</Select.Option>
          </Select>
          
          <Search
            placeholder="搜索用户、IP或资源"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
          
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
        </Space>
      </Card>

      {/* 审计日志表格 */}
      <Card title="安全审计日志">
        <Table
          columns={columns}
          dataSource={auditLogs?.logs || []}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            total: auditLogs?.total || 0,
          }}
        />
      </Card>

      {/* 详情模态框 */}
      <Modal
        title="审计日志详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedLog && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="时间">
              {new Date(selectedLog.timestamp).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="用户">
              {selectedLog.userName} ({selectedLog.userId})
            </Descriptions.Item>
            <Descriptions.Item label="操作">
              {selectedLog.action}
            </Descriptions.Item>
            <Descriptions.Item label="资源">
              {selectedLog.resource} ({selectedLog.resourceId})
            </Descriptions.Item>
            <Descriptions.Item label="请求方法">
              {selectedLog.method}
            </Descriptions.Item>
            <Descriptions.Item label="请求路径">
              {selectedLog.endpoint}
            </Descriptions.Item>
            <Descriptions.Item label="IP地址">
              {selectedLog.ipAddress}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedLog.status === 'success' ? 'success' : selectedLog.status === 'failed' ? 'error' : 'warning'}>
                {selectedLog.status === 'success' ? '成功' : selectedLog.status === 'failed' ? '失败' : '警告'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="风险等级">
              <Tag color={
                selectedLog.riskLevel === 'low' ? 'default' :
                selectedLog.riskLevel === 'medium' ? 'processing' :
                selectedLog.riskLevel === 'high' ? 'warning' : 'error'
              }>
                {selectedLog.riskLevel === 'low' ? '低' :
                 selectedLog.riskLevel === 'medium' ? '中' :
                 selectedLog.riskLevel === 'high' ? '高' : '严重'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="用户代理" span={2}>
              {selectedLog.userAgent}
            </Descriptions.Item>
            <Descriptions.Item label="详细信息" span={2}>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default SecurityAudit;