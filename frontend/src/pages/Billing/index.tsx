// Enhanced Billing page with comprehensive account list and details
import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Row,
  Col,
  Statistic,
  DatePicker,
  Modal,
  Descriptions,
  message,
  Select,
  Input,
  Tabs,
  Divider,
  Alert,
  Tooltip,
  Typography,
} from 'antd';
import {
  DollarOutlined,
  DownloadOutlined,
  EyeOutlined,
  RiseOutlined,
  FallOutlined,
  SwapOutlined,
  FileExcelOutlined,
  CalendarOutlined,
  HistoryOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useBillingList, useBillingAnalysis, useExportBilling } from '@/hooks/useBilling';
import type { BillingRecord, BillingStatus, BillingListParams } from '@/types/billing';
import { BillingDashboard } from '@/components/Billing/BillingDashboard';
import { WorkHoursAnalysis } from '@/components/Billing/WorkHoursAnalysis';
import { ExcelExportManager } from '@/components/Billing/ExcelExportManager';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Search } = Input;
const { TabPane } = Tabs;
const { Text, Title } = Typography;

const BillingPage: React.FC = () => {
  const { t } = useTranslation('billing');
  const { currentTenant } = useAuthStore();
  const tenantId = currentTenant?.id || 'default';
  
  // Status color map
  const statusColorMap: Record<BillingStatus, string> = {
    pending: 'processing',
    paid: 'success',
    overdue: 'error',
    cancelled: 'default',
  };
  
  // State management
  const [selectedRecord, setSelectedRecord] = useState<BillingRecord | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareRecords, setCompareRecords] = useState<BillingRecord[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  
  // Filter and search state
  const [filters, setFilters] = useState<BillingListParams>({
    page: 1,
    page_size: 10,
  });
  const [searchText, setSearchText] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [statusFilter, setStatusFilter] = useState<BillingStatus | undefined>();

  // API hooks
  const { data: billingData, isLoading, error, refetch } = useBillingList(tenantId, filters);
  const { data: analysisData } = useBillingAnalysis(tenantId);
  const exportMutation = useExportBilling();

  // Computed values
  const billingRecords = billingData?.items || [];
  const totalRecords = billingData?.total || 0;

  // Filter records based on search and filters
  const filteredRecords = useMemo(() => {
    let filtered = billingRecords;

    if (searchText) {
      filtered = filtered.filter(record => 
        record.id.toLowerCase().includes(searchText.toLowerCase()) ||
        record.items.some(item => 
          item.description.toLowerCase().includes(searchText.toLowerCase())
        )
      );
    }

    if (statusFilter) {
      filtered = filtered.filter(record => record.status === statusFilter);
    }

    if (dateRange) {
      const [start, end] = dateRange;
      filtered = filtered.filter(record => {
        const recordDate = dayjs(record.period_start);
        return recordDate.isAfter(start) && recordDate.isBefore(end);
      });
    }

    return filtered;
  }, [billingRecords, searchText, statusFilter, dateRange]);

  // Statistics calculations
  const statistics = useMemo(() => {
    const totalSpending = analysisData?.total_spending || 0;
    const averageMonthly = analysisData?.average_monthly || 0;
    const pendingAmount = filteredRecords
      .filter(r => r.status === 'pending')
      .reduce((sum, r) => sum + r.total_amount, 0);
    const overdueAmount = filteredRecords
      .filter(r => r.status === 'overdue')
      .reduce((sum, r) => sum + r.total_amount, 0);

    return {
      totalSpending,
      averageMonthly,
      pendingAmount,
      overdueAmount,
      trendPercentage: analysisData?.trend_percentage || 0,
    };
  }, [analysisData, filteredRecords]);

  // Event handlers
  const handleExport = async () => {
    try {
      await exportMutation.mutateAsync({ tenantId, params: filters });
      message.success(t('messages.exportSuccess'));
    } catch {
      message.error(t('messages.exportFailed'));
    }
  };

  const handleViewDetail = (record: BillingRecord) => {
    setSelectedRecord(record);
    setDetailModalOpen(true);
  };

  const handleCompareRecords = () => {
    if (selectedRowKeys.length < 2) {
      message.warning(t('messages.selectAtLeast2'));
      return;
    }
    if (selectedRowKeys.length > 3) {
      message.warning(t('messages.compareMax3'));
      return;
    }
    
    const recordsToCompare = billingRecords.filter(r => selectedRowKeys.includes(r.id));
    setCompareRecords(recordsToCompare);
    setCompareModalOpen(true);
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleFilterChange = (key: string, value: unknown) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page when filtering
    }));
  };

  const handleTableChange = (pagination: { current?: number; pageSize?: number }) => {
    setFilters(prev => ({
      ...prev,
      page: pagination.current || 1,
      page_size: pagination.pageSize || 10,
    }));
  };

  const handleDateRangeChange = (
    dates: [Dayjs | null, Dayjs | null] | null,
    _dateStrings: [string, string]
  ) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange([dates[0], dates[1]]);
      handleFilterChange('start_date', dates[0].format('YYYY-MM-DD'));
      handleFilterChange('end_date', dates[1].format('YYYY-MM-DD'));
    } else {
      setDateRange(null);
      const newFilters = { ...filters };
      delete newFilters.start_date;
      delete newFilters.end_date;
      setFilters(newFilters);
    }
  };

  // Table columns configuration
  const columns: ColumnsType<BillingRecord> = [
    {
      title: t('columns.billId'),
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (id: string) => (
        <Text code copyable={{ text: id }}>
          {id.slice(0, 8)}...
        </Text>
      ),
    },
    {
      title: t('period'),
      key: 'period',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>
            {dayjs(record.period_start).format('MMM DD')} - {dayjs(record.period_end).format('MMM DD, YYYY')}
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {dayjs(record.period_end).diff(dayjs(record.period_start), 'day') + 1} {t('columns.days')}
          </Text>
        </Space>
      ),
      sorter: (a, b) => dayjs(a.period_start).unix() - dayjs(b.period_start).unix(),
    },
    {
      title: t('amount'),
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 150,
      render: (amount: number) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#1890ff', fontSize: '16px' }}>
            ¥{amount.toLocaleString()}
          </Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {billingRecords.find(r => r.total_amount === amount)?.items.length || 0} {t('columns.items')}
          </Text>
        </Space>
      ),
      sorter: (a, b) => a.total_amount - b.total_amount,
    },
    {
      title: t('status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: BillingStatus, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={statusColorMap[status]}>{t(`status.${status}`)}</Tag>
          {status === 'overdue' && (
            <Text type="danger" style={{ fontSize: '12px' }}>
              {dayjs().diff(dayjs(record.due_date), 'day')} {t('columns.daysOverdue')}
            </Text>
          )}
        </Space>
      ),
      filters: [
        { text: t('status.pending'), value: 'pending' },
        { text: t('status.paid'), value: 'paid' },
        { text: t('status.overdue'), value: 'overdue' },
        { text: t('status.cancelled'), value: 'cancelled' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      render: (date: string) => (
        <Space direction="vertical" size={0}>
          <Text>{dayjs(date).format('MMM DD, YYYY')}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {dayjs(date).fromNow()}
          </Text>
        </Space>
      ),
      sorter: (a, b) => dayjs(a.due_date).unix() - dayjs(b.due_date).unix(),
    },
    {
      title: t('columns.payment'),
      key: 'payment',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.paid_at ? (
            <>
              <Text type="success">{dayjs(record.paid_at).format('MMM DD, YYYY')}</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {dayjs(record.paid_at).format('HH:mm')}
              </Text>
            </>
          ) : (
            <Text type="secondary">{t('columns.notPaid')}</Text>
          )}
        </Space>
      ),
    },
    {
      title: t('actions'),
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('view')}>
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title={t('downloadInvoice')}>
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => message.info(t('messages.invoiceComingSoon'))}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Row selection configuration
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as string[]),
    getCheckboxProps: (record: BillingRecord) => ({
      disabled: record.status === 'cancelled',
    }),
  };

  if (error) {
    return (
      <Card>
        <Alert
          message={t('messages.loadFailed')}
          description={t('messages.checkConnection')}
          type="error"
          action={
            <Button size="small" onClick={() => refetch()}>
              {t('messages.retry')}
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <div className="billing-page">
      <Title level={2}>{t('title')}</Title>
      
      {/* Statistics Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('totalSpending')}
              value={statistics.totalSpending}
              prefix={<DollarOutlined />}
              suffix="¥"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('averageMonthly')}
              value={statistics.averageMonthly}
              prefix={statistics.trendPercentage >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix="¥"
              precision={0}
              valueStyle={{ 
                color: statistics.trendPercentage >= 0 ? '#cf1322' : '#3f8600' 
              }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {statistics.trendPercentage >= 0 ? '+' : ''}{statistics.trendPercentage.toFixed(1)}% {t('statistics.vsLastPeriod')}
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('pendingPayment')}
              value={statistics.pendingAmount}
              prefix={<CalendarOutlined />}
              suffix="¥"
              valueStyle={{ color: statistics.pendingAmount > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('statistics.overdueAmount')}
              value={statistics.overdueAmount}
              prefix={<HistoryOutlined />}
              suffix="¥"
              valueStyle={{ color: statistics.overdueAmount > 0 ? '#f5222d' : '#52c41a' }}
            />
            {statistics.overdueAmount > 0 && (
              <div style={{ marginTop: 8 }}>
                <Text type="danger" style={{ fontSize: '12px' }}>
                  {t('statistics.requiresAttention')}
                </Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Filters and Actions */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Search
                placeholder={t('filters.searchPlaceholder')}
                allowClear
                style={{ width: 250 }}
                onSearch={handleSearch}
                onChange={(e) => !e.target.value && setSearchText('')}
              />
              <Select
                placeholder={t('filters.filterByStatus')}
                allowClear
                style={{ width: 150 }}
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value);
                  handleFilterChange('status', value);
                }}
                options={[
                  { value: 'pending', label: t('status.pending') },
                  { value: 'paid', label: t('status.paid') },
                  { value: 'overdue', label: t('status.overdue') },
                  { value: 'cancelled', label: t('status.cancelled') },
                ]}
              />
              <RangePicker
                value={dateRange}
                onChange={handleDateRangeChange}
                presets={[
                  { label: t('filters.presets.last7Days'), value: [dayjs().subtract(7, 'day'), dayjs()] },
                  { label: t('filters.presets.last30Days'), value: [dayjs().subtract(30, 'day'), dayjs()] },
                  { label: t('filters.presets.last3Months'), value: [dayjs().subtract(3, 'month'), dayjs()] },
                  { label: t('filters.presets.thisYear'), value: [dayjs().startOf('year'), dayjs()] },
                ]}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <>
                  <Text type="secondary">{selectedRowKeys.length} {t('filters.selected')}</Text>
                  <Button
                    icon={<SwapOutlined />}
                    onClick={handleCompareRecords}
                    disabled={selectedRowKeys.length < 2}
                  >
                    {t('filters.compare')}
                  </Button>
                </>
              )}
              <Button
                icon={<FileExcelOutlined />}
                onClick={handleExport}
                loading={exportMutation.isPending}
              >
                {t('filters.exportExcel')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultActiveKey="dashboard">
        <TabPane
          tab={
            <span>
              <DashboardOutlined />
              {t('tabs.dashboard')}
            </span>
          }
          key="dashboard"
        >
          <BillingDashboard />
        </TabPane>

        <TabPane
          tab={
            <span>
              <HistoryOutlined />
              {t('tabs.records')}
            </span>
          }
          key="records"
        >
          {/* Billing Records Table */}
          <Card
            title={
              <Space>
                <HistoryOutlined />
                {t('records')}
                <Text type="secondary">({totalRecords} {t('tabs.total')})</Text>
              </Space>
            }
          >
            <Table<BillingRecord>
              columns={columns}
              dataSource={filteredRecords}
              rowKey="id"
              loading={isLoading}
              rowSelection={rowSelection}
              pagination={{
                current: filters.page,
                pageSize: filters.page_size,
                total: totalRecords,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => 
                  `${range[0]}-${range[1]} ${t('tabs.of')} ${total} ${t('tabs.recordsText')}`,
                pageSizeOptions: ['10', '20', '50', '100'],
              }}
              onChange={handleTableChange}
              scroll={{ x: 1200 }}
              size="middle"
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <ClockCircleOutlined />
              {t('tabs.workHours')}
            </span>
          }
          key="workhours"
        >
          <WorkHoursAnalysis tenantId={tenantId} />
        </TabPane>

        <TabPane
          tab={
            <span>
              <FileExcelOutlined />
              {t('tabs.export')}
            </span>
          }
          key="export"
        >
          <ExcelExportManager tenantId={tenantId} />
        </TabPane>
      </Tabs>

      {/* Detail Modal */}
      <Modal
        title={
          <Space>
            <EyeOutlined />
            {t('details')}
            {selectedRecord && (
              <Tag color={statusColorMap[selectedRecord.status]}>
                {t(`status.${selectedRecord.status}`)}
              </Tag>
            )}
          </Space>
        }
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('close')}
          </Button>,
          <Button key="download" type="primary" icon={<DownloadOutlined />}>
            {t('downloadInvoice')}
          </Button>,
        ]}
        width={800}
      >
        {selectedRecord && (
          <Tabs defaultActiveKey="overview">
            <TabPane tab={t('modal.overview')} key="overview">
              <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
                <Descriptions.Item label={t('columns.billId')} span={2}>
                  <Text code copyable>{selectedRecord.id}</Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('period')}>
                  {dayjs(selectedRecord.period_start).format('MMMM DD, YYYY')} - {dayjs(selectedRecord.period_end).format('MMMM DD, YYYY')}
                </Descriptions.Item>
                <Descriptions.Item label={t('modal.duration')}>
                  {dayjs(selectedRecord.period_end).diff(dayjs(selectedRecord.period_start), 'day') + 1} {t('columns.days')}
                </Descriptions.Item>
                <Descriptions.Item label={t('status')}>
                  <Tag color={statusColorMap[selectedRecord.status]}>
                    {t(`status.${selectedRecord.status}`)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label={t('amount')}>
                  <Text strong style={{ fontSize: '18px', color: '#1890ff' }}>
                    ¥{selectedRecord.total_amount.toLocaleString()}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('dueDate')}>
                  {dayjs(selectedRecord.due_date).format('MMMM DD, YYYY')}
                  <br />
                  <Text type="secondary">
                    ({dayjs(selectedRecord.due_date).fromNow()})
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('modal.paymentDate')}>
                  {selectedRecord.paid_at ? (
                    <>
                      {dayjs(selectedRecord.paid_at).format('MMMM DD, YYYY HH:mm')}
                      <br />
                      <Text type="success">
                        {t('modal.paid')} {dayjs(selectedRecord.paid_at).fromNow()}
                      </Text>
                    </>
                  ) : (
                    <Text type="secondary">{t('modal.notPaidYet')}</Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label={t('modal.created')}>
                  {dayjs(selectedRecord.created_at).format('MMMM DD, YYYY HH:mm')}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
            
            <TabPane tab={t('modal.lineItems')} key="items">
              <Table
                size="small"
                dataSource={selectedRecord.items}
                rowKey="id"
                pagination={false}
                columns={[
                  { 
                    title: t('description'), 
                    dataIndex: 'description', 
                    key: 'description',
                    render: (text: string) => <Text strong>{text}</Text>
                  },
                  { 
                    title: t('category'), 
                    dataIndex: 'category', 
                    key: 'category',
                    render: (category: string) => (
                      <Tag color="blue">{t(`categories.${category}`)}</Tag>
                    )
                  },
                  { 
                    title: t('quantity'), 
                    dataIndex: 'quantity', 
                    key: 'quantity',
                    align: 'right',
                    render: (qty: number) => qty.toLocaleString()
                  },
                  {
                    title: t('unitPrice'),
                    dataIndex: 'unit_price',
                    key: 'unit_price',
                    align: 'right',
                    render: (price: number) => `¥${price.toFixed(2)}`,
                  },
                  {
                    title: t('amount'),
                    dataIndex: 'amount',
                    key: 'amount',
                    align: 'right',
                    render: (amount: number) => (
                      <Text strong style={{ color: '#1890ff' }}>
                        ¥{amount.toLocaleString()}
                      </Text>
                    ),
                  },
                ]}
                summary={(pageData) => {
                  const total = pageData.reduce((sum, item) => sum + item.amount, 0);
                  return (
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0} colSpan={4}>
                        <Text strong>{t('modal.total')}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={4}>
                        <Text strong style={{ color: '#1890ff', fontSize: '16px' }}>
                          ¥{total.toLocaleString()}
                        </Text>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  );
                }}
              />
            </TabPane>
          </Tabs>
        )}
      </Modal>

      {/* Compare Modal */}
      <Modal
        title={
          <Space>
            <SwapOutlined />
            {t('compare.title')}
          </Space>
        }
        open={compareModalOpen}
        onCancel={() => setCompareModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setCompareModalOpen(false)}>
            {t('close')}
          </Button>,
        ]}
        width={1000}
      >
        {compareRecords.length > 0 && (
          <Row gutter={16}>
            {compareRecords.map((record, index) => (
              <Col span={24 / compareRecords.length} key={record.id}>
                <Card 
                  size="small" 
                  title={
                    <Space>
                      <Text strong>{t('compare.bill')} #{index + 1}</Text>
                      <Tag color={statusColorMap[record.status]}>
                        {t(`status.${record.status}`)}
                      </Tag>
                    </Space>
                  }
                >
                  <Descriptions size="small" column={1}>
                    <Descriptions.Item label={t('period')}>
                      {dayjs(record.period_start).format('MMM DD')} - {dayjs(record.period_end).format('MMM DD, YYYY')}
                    </Descriptions.Item>
                    <Descriptions.Item label={t('amount')}>
                      <Text strong style={{ color: '#1890ff' }}>
                        ¥{record.total_amount.toLocaleString()}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label={t('compare.items')}>
                      {record.items.length} {t('columns.items')}
                    </Descriptions.Item>
                    <Descriptions.Item label={t('dueDate')}>
                      {dayjs(record.due_date).format('MMM DD, YYYY')}
                    </Descriptions.Item>
                  </Descriptions>
                  
                  <Divider style={{ margin: '12px 0' }} />
                  
                  <div>
                    <Text strong style={{ fontSize: '12px' }}>{t('compare.topCategories')}:</Text>
                    <div style={{ marginTop: 8 }}>
                      {record.items.slice(0, 3).map(item => (
                        <div key={item.id} style={{ marginBottom: 4 }}>
                          <Tag style={{ fontSize: '12px' }}>{t(`categories.${item.category}`)}</Tag>
                          <Text style={{ fontSize: '12px' }}>
                            ¥{item.amount.toLocaleString()}
                          </Text>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Modal>
    </div>
  );
};

export default BillingPage;
