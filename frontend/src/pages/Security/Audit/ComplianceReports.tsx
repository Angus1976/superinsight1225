/**
 * Compliance Reports Page
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  DatePicker,
  Select,
  Row,
  Col,
  Modal,
  Descriptions,
  Typography,
  message,
  Progress,
  List,
  Divider,
  Alert,
  Tabs,
} from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  EyeOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import { auditApi, ComplianceReport, ComplianceReportRequest } from '@/services/auditApi';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Title, Text, Paragraph } = Typography;

const reportTypeLabels: Record<string, string> = {
  gdpr: 'GDPR Compliance',
  soc2: 'SOC 2 Compliance',
  access: 'Data Access Report',
  permission_changes: 'Permission Changes',
};

const reportTypeColors: Record<string, string> = {
  gdpr: 'purple',
  soc2: 'blue',
  access: 'cyan',
  permission_changes: 'orange',
};

const ComplianceReports: React.FC = () => {
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ComplianceReport | null>(null);
  const [reportType, setReportType] = useState<string>('gdpr');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const queryClient = useQueryClient();

  // Fetch reports list
  const { data: reportsResponse, isLoading } = useQuery({
    queryKey: ['complianceReports'],
    queryFn: () => auditApi.listReports({ limit: 50 }),
  });

  // Generate report mutations
  const generateGDPRMutation = useMutation({
    mutationFn: (data: ComplianceReportRequest) => auditApi.generateGDPRReport(data),
    onSuccess: () => {
      message.success('GDPR report generated successfully');
      queryClient.invalidateQueries({ queryKey: ['complianceReports'] });
      setGenerateModalOpen(false);
    },
    onError: () => {
      message.error('Failed to generate report');
    },
  });

  const generateSOC2Mutation = useMutation({
    mutationFn: (data: ComplianceReportRequest) => auditApi.generateSOC2Report(data),
    onSuccess: () => {
      message.success('SOC 2 report generated successfully');
      queryClient.invalidateQueries({ queryKey: ['complianceReports'] });
      setGenerateModalOpen(false);
    },
    onError: () => {
      message.error('Failed to generate report');
    },
  });

  const generateAccessMutation = useMutation({
    mutationFn: (data: ComplianceReportRequest) =>
      auditApi.generateAccessReport({
        start_date: data.start_date,
        end_date: data.end_date,
      }),
    onSuccess: () => {
      message.success('Access report generated successfully');
      queryClient.invalidateQueries({ queryKey: ['complianceReports'] });
      setGenerateModalOpen(false);
    },
    onError: () => {
      message.error('Failed to generate report');
    },
  });

  const generatePermissionMutation = useMutation({
    mutationFn: (data: ComplianceReportRequest) =>
      auditApi.generatePermissionChangeReport({
        start_date: data.start_date,
        end_date: data.end_date,
      }),
    onSuccess: () => {
      message.success('Permission change report generated successfully');
      queryClient.invalidateQueries({ queryKey: ['complianceReports'] });
      setGenerateModalOpen(false);
    },
    onError: () => {
      message.error('Failed to generate report');
    },
  });

  const handleGenerateReport = () => {
    const data: ComplianceReportRequest = {
      start_date: dateRange[0].toISOString(),
      end_date: dateRange[1].toISOString(),
      include_details: true,
    };

    switch (reportType) {
      case 'gdpr':
        generateGDPRMutation.mutate(data);
        break;
      case 'soc2':
        generateSOC2Mutation.mutate(data);
        break;
      case 'access':
        generateAccessMutation.mutate(data);
        break;
      case 'permission_changes':
        generatePermissionMutation.mutate(data);
        break;
    }
  };

  const handleViewReport = async (reportId: string) => {
    try {
      const report = await auditApi.getReport(reportId);
      setSelectedReport(report);
      setViewModalOpen(true);
    } catch {
      message.error('Failed to load report');
    }
  };

  const isGenerating =
    generateGDPRMutation.isPending ||
    generateSOC2Mutation.isPending ||
    generateAccessMutation.isPending ||
    generatePermissionMutation.isPending;

  const columns: ColumnsType<{
    id: string;
    report_type: string;
    generated_at: string;
    period_start: string;
    period_end: string;
    compliance_score?: number;
  }> = [
    {
      title: 'Report Type',
      dataIndex: 'report_type',
      key: 'report_type',
      render: (type) => (
        <Tag color={reportTypeColors[type.toLowerCase()] || 'default'}>
          {reportTypeLabels[type.toLowerCase()] || type}
        </Tag>
      ),
    },
    {
      title: 'Period',
      key: 'period',
      render: (_, record) => (
        <Text>
          {dayjs(record.period_start).format('YYYY-MM-DD')} -{' '}
          {dayjs(record.period_end).format('YYYY-MM-DD')}
        </Text>
      ),
    },
    {
      title: 'Compliance Score',
      dataIndex: 'compliance_score',
      key: 'compliance_score',
      render: (score) =>
        score !== undefined && score !== null ? (
          <Progress
            percent={score}
            size="small"
            status={score >= 80 ? 'success' : score >= 60 ? 'normal' : 'exception'}
            style={{ width: 100 }}
          />
        ) : (
          '-'
        ),
    },
    {
      title: 'Generated',
      dataIndex: 'generated_at',
      key: 'generated_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewReport(record.id)}
          >
            View
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>Compliance Reports</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenerateModalOpen(true)}
          >
            Generate Report
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={reportsResponse?.reports || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `Total ${total} reports`,
          }}
        />
      </Card>

      {/* Generate Report Modal */}
      <Modal
        title="Generate Compliance Report"
        open={generateModalOpen}
        onOk={handleGenerateReport}
        onCancel={() => setGenerateModalOpen(false)}
        confirmLoading={isGenerating}
        okText="Generate"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text strong>Report Type</Text>
            <Select
              value={reportType}
              onChange={setReportType}
              style={{ width: '100%', marginTop: 8 }}
              options={[
                { label: 'GDPR Compliance Report', value: 'gdpr' },
                { label: 'SOC 2 Compliance Report', value: 'soc2' },
                { label: 'Data Access Report', value: 'access' },
                { label: 'Permission Changes Report', value: 'permission_changes' },
              ]}
            />
          </div>

          <div>
            <Text strong>Report Period</Text>
            <RangePicker
              value={dateRange}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  setDateRange([dates[0], dates[1]]);
                }
              }}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>

          <Alert
            message="Report Generation"
            description={`This will generate a ${reportTypeLabels[reportType] || reportType} for the selected period. The report will include detailed findings and recommendations.`}
            type="info"
            showIcon
          />
        </Space>
      </Modal>

      {/* View Report Modal */}
      <Modal
        title={
          selectedReport
            ? `${reportTypeLabels[selectedReport.report_type.toLowerCase()] || selectedReport.report_type} Report`
            : 'Report Details'
        }
        open={viewModalOpen}
        onCancel={() => setViewModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedReport && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Statistic
                  title="Compliance Score"
                  value={selectedReport.compliance_score || 'N/A'}
                  suffix={selectedReport.compliance_score !== undefined ? '%' : ''}
                  valueStyle={{
                    color:
                      selectedReport.compliance_score !== undefined
                        ? selectedReport.compliance_score >= 80
                          ? '#52c41a'
                          : selectedReport.compliance_score >= 60
                          ? '#faad14'
                          : '#ff4d4f'
                        : undefined,
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Period"
                  value={`${dayjs(selectedReport.period_start).format('MMM D')} - ${dayjs(
                    selectedReport.period_end
                  ).format('MMM D, YYYY')}`}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Generated"
                  value={dayjs(selectedReport.generated_at).format('YYYY-MM-DD HH:mm')}
                />
              </Col>
            </Row>

            <Tabs
              items={[
                {
                  key: 'summary',
                  label: 'Summary',
                  children: (
                    <Descriptions column={2} bordered size="small">
                      {Object.entries(selectedReport.summary || {}).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key.replace(/_/g, ' ')}>
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  ),
                },
                {
                  key: 'findings',
                  label: `Findings (${selectedReport.findings?.length || 0})`,
                  children: (
                    <List
                      dataSource={selectedReport.findings || []}
                      renderItem={(finding: Record<string, unknown>) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={
                              finding.type === 'critical' || finding.type === 'warning' ? (
                                <WarningOutlined style={{ color: '#faad14' }} />
                              ) : (
                                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                              )
                            }
                            title={
                              <Space>
                                <Tag
                                  color={
                                    finding.type === 'critical'
                                      ? 'red'
                                      : finding.type === 'warning'
                                      ? 'orange'
                                      : 'blue'
                                  }
                                >
                                  {String(finding.type || 'info').toUpperCase()}
                                </Tag>
                                <Text>{String(finding.category || '')}</Text>
                              </Space>
                            }
                            description={String(finding.description || '')}
                          />
                        </List.Item>
                      )}
                      locale={{ emptyText: 'No findings' }}
                    />
                  ),
                },
                {
                  key: 'recommendations',
                  label: `Recommendations (${selectedReport.recommendations?.length || 0})`,
                  children: (
                    <List
                      dataSource={selectedReport.recommendations || []}
                      renderItem={(rec: string, index: number) => (
                        <List.Item>
                          <Text>
                            {index + 1}. {rec}
                          </Text>
                        </List.Item>
                      )}
                      locale={{ emptyText: 'No recommendations' }}
                    />
                  ),
                },
              ]}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

// Helper component for statistics
const Statistic: React.FC<{
  title: string;
  value: string | number;
  suffix?: string;
  valueStyle?: React.CSSProperties;
}> = ({ title, value, suffix, valueStyle }) => (
  <div>
    <Text type="secondary" style={{ fontSize: 12 }}>
      {title}
    </Text>
    <div style={{ fontSize: 24, fontWeight: 600, ...valueStyle }}>
      {value}
      {suffix}
    </div>
  </div>
);

export default ComplianceReports;
