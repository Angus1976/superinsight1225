/**
 * License Report Page
 * 
 * Generates and displays license usage reports.
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  DatePicker,
  Button,
  Checkbox,
  Statistic,
  Table,
  Spin,
  message,
  Typography,
  Space,
  Divider,
  Empty,
} from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  BarChartOutlined,
  TeamOutlined,
  CloudServerOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { usageApi, LicenseUsageReport } from '../../services/licenseApi';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const LicenseReport: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<LicenseUsageReport | null>(null);

  const handleGenerateReport = async (values: {
    dateRange: [dayjs.Dayjs, dayjs.Dayjs];
    include_sessions: boolean;
    include_resources: boolean;
    include_features: boolean;
  }) => {
    setLoading(true);
    try {
      const result = await usageApi.generateReport({
        start_date: values.dateRange[0].toISOString(),
        end_date: values.dateRange[1].toISOString(),
        include_sessions: values.include_sessions,
        include_resources: values.include_resources,
        include_features: values.include_features,
      });
      setReport(result);
      message.success('报告生成成功');
    } catch (err) {
      message.error('生成报告失败');
      console.error('Failed to generate report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportReport = async () => {
    if (!report) return;
    
    try {
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `license_report_${dayjs().format('YYYY-MM-DD')}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('报告已导出');
    } catch (err) {
      message.error('导出失败');
    }
  };

  const auditColumns: ColumnsType<{ event_type: string; count: number }> = [
    {
      title: '事件类型',
      dataIndex: 'event_type',
      key: 'event_type',
    },
    {
      title: '次数',
      dataIndex: 'count',
      key: 'count',
      align: 'right',
    },
  ];

  const featureColumns: ColumnsType<{
    feature: string;
    total: number;
    allowed: number;
    denied: number;
  }> = [
    {
      title: '功能',
      dataIndex: 'feature',
      key: 'feature',
    },
    {
      title: '总访问',
      dataIndex: 'total',
      key: 'total',
      align: 'right',
    },
    {
      title: '允许',
      dataIndex: 'allowed',
      key: 'allowed',
      align: 'right',
      render: (val: number) => <Text type="success">{val}</Text>,
    },
    {
      title: '拒绝',
      dataIndex: 'denied',
      key: 'denied',
      align: 'right',
      render: (val: number) => <Text type="danger">{val}</Text>,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <FileTextOutlined /> 使用报告
      </Title>

      {/* Report Configuration */}
      <Card title="报告配置" style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="inline"
          onFinish={handleGenerateReport}
          initialValues={{
            dateRange: [dayjs().subtract(30, 'day'), dayjs()],
            include_sessions: true,
            include_resources: true,
            include_features: true,
          }}
        >
          <Form.Item
            name="dateRange"
            label="时间范围"
            rules={[{ required: true, message: '请选择时间范围' }]}
          >
            <RangePicker />
          </Form.Item>

          <Form.Item name="include_sessions" valuePropName="checked">
            <Checkbox>包含会话数据</Checkbox>
          </Form.Item>

          <Form.Item name="include_resources" valuePropName="checked">
            <Checkbox>包含资源数据</Checkbox>
          </Form.Item>

          <Form.Item name="include_features" valuePropName="checked">
            <Checkbox>包含功能数据</Checkbox>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                生成报告
              </Button>
              {report && (
                <Button icon={<DownloadOutlined />} onClick={handleExportReport}>
                  导出
                </Button>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Report Content */}
      <Spin spinning={loading}>
        {report ? (
          <>
            {/* Report Header */}
            <Card style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="报告周期"
                    value={`${dayjs(report.report_period.start).format('YYYY-MM-DD')} ~ ${dayjs(report.report_period.end).format('YYYY-MM-DD')}`}
                    prefix={<BarChartOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="许可证类型"
                    value={report.license_type.toUpperCase()}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="生成时间"
                    value={dayjs(report.generated_at).format('YYYY-MM-DD HH:mm')}
                  />
                </Col>
              </Row>
            </Card>

            <Row gutter={16}>
              {/* Concurrent User Stats */}
              <Col xs={24} lg={12}>
                <Card
                  title={
                    <Space>
                      <TeamOutlined />
                      并发用户统计
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  {report.concurrent_user_stats && Object.keys(report.concurrent_user_stats).length > 0 ? (
                    <Row gutter={[16, 16]}>
                      <Col span={12}>
                        <Statistic
                          title="总会话数"
                          value={(report.concurrent_user_stats as Record<string, number>).total_sessions || 0}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="独立用户"
                          value={(report.concurrent_user_stats as Record<string, number>).unique_users || 0}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="峰值并发"
                          value={(report.concurrent_user_stats as Record<string, number>).peak_concurrent || 0}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="平均会话时长"
                          value={(report.concurrent_user_stats as Record<string, number>).average_session_duration_minutes || 0}
                          suffix="分钟"
                        />
                      </Col>
                    </Row>
                  ) : (
                    <Empty description="无数据" />
                  )}
                </Card>
              </Col>

              {/* Resource Stats */}
              <Col xs={24} lg={12}>
                <Card
                  title={
                    <Space>
                      <CloudServerOutlined />
                      资源使用统计
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  {report.resource_usage_stats && Object.keys(report.resource_usage_stats).length > 0 ? (
                    Object.entries(report.resource_usage_stats).map(([resource, stats]) => (
                      <div key={resource} style={{ marginBottom: 16 }}>
                        <Text strong>{resource.toUpperCase()}</Text>
                        <Row gutter={16} style={{ marginTop: 8 }}>
                          <Col span={8}>
                            <Statistic
                              title="检查次数"
                              value={(stats as Record<string, number>).checks || 0}
                              valueStyle={{ fontSize: 16 }}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="最大使用率"
                              value={(stats as Record<string, number>).max_utilization || 0}
                              suffix="%"
                              valueStyle={{ fontSize: 16 }}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="平均使用率"
                              value={(stats as Record<string, number>).avg_utilization || 0}
                              suffix="%"
                              valueStyle={{ fontSize: 16 }}
                            />
                          </Col>
                        </Row>
                        <Divider style={{ margin: '12px 0' }} />
                      </div>
                    ))
                  ) : (
                    <Empty description="无数据" />
                  )}
                </Card>
              </Col>
            </Row>

            <Row gutter={16}>
              {/* Feature Usage */}
              <Col xs={24} lg={12}>
                <Card
                  title={
                    <Space>
                      <AppstoreOutlined />
                      功能使用统计
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  {report.feature_usage_stats && 
                   (report.feature_usage_stats as Record<string, unknown>).by_feature &&
                   Object.keys((report.feature_usage_stats as Record<string, Record<string, unknown>>).by_feature).length > 0 ? (
                    <Table
                      columns={featureColumns}
                      dataSource={Object.entries(
                        (report.feature_usage_stats as Record<string, Record<string, Record<string, number>>>).by_feature
                      ).map(([feature, stats]) => ({
                        key: feature,
                        feature,
                        ...stats,
                      }))}
                      pagination={false}
                      size="small"
                    />
                  ) : (
                    <Empty description="无数据" />
                  )}
                </Card>
              </Col>

              {/* Audit Summary */}
              <Col xs={24} lg={12}>
                <Card
                  title={
                    <Space>
                      <FileTextOutlined />
                      审计事件统计
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  {report.audit_summary && Object.keys(report.audit_summary).length > 0 ? (
                    <Table
                      columns={auditColumns}
                      dataSource={Object.entries(report.audit_summary).map(([event_type, count]) => ({
                        key: event_type,
                        event_type,
                        count,
                      }))}
                      pagination={false}
                      size="small"
                    />
                  ) : (
                    <Empty description="无数据" />
                  )}
                </Card>
              </Col>
            </Row>
          </>
        ) : (
          <Card>
            <Empty description="请配置参数并生成报告" />
          </Card>
        )}
      </Spin>
    </div>
  );
};

export default LicenseReport;
