/**
 * Report Viewer Component - 报告查看组件
 * 实现质量报告的查看和导出功能
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Button,
  Space,
  Select,
  DatePicker,
  Progress,
  Tag,
  Tabs,
  message,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  TimePicker,
} from 'antd';
import {
  DownloadOutlined,
  FileTextOutlined,
  TrophyOutlined,
  LineChartOutlined,
  ScheduleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  qualityApi,
  type ProjectQualityReport,
  type AnnotatorRankingReport,
  type AnnotatorRanking,
  type TrendPoint,
} from '@/services/qualityApi';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface ReportViewerProps {
  projectId: string;
}

const ReportViewer: React.FC<ReportViewerProps> = ({ projectId }) => {
  const { t } = useTranslation(['quality', 'common']);
  const [loading, setLoading] = useState(false);
  const [projectReport, setProjectReport] = useState<ProjectQualityReport | null>(null);
  const [rankingReport, setRankingReport] = useState<AnnotatorRankingReport | null>(null);
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [form] = Form.useForm();

  const handleGenerateProjectReport = async (dates: [string, string]) => {
    setLoading(true);
    try {
      const report = await qualityApi.generateProjectReport({
        project_id: projectId,
        start_date: dates[0],
        end_date: dates[1],
      });
      setProjectReport(report);
      message.success(t('messages.reportGenerated'));
    } catch {
      message.error(t('messages.reportGenerateFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateRankingReport = async (period: string) => {
    setLoading(true);
    try {
      const report = await qualityApi.generateAnnotatorRanking({
        project_id: projectId,
        period,
      });
      setRankingReport(report);
      message.success(t('messages.rankingGenerated'));
    } catch {
      message.error(t('messages.reportGenerateFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'excel' | 'html' | 'json') => {
    if (!projectReport && !rankingReport) {
      message.warning(t('messages.generateReportFirst'));
      return;
    }
    try {
      const blob = await qualityApi.exportReport({
        report_type: projectReport ? 'project' : 'ranking',
        report_data: (projectReport || rankingReport) as unknown as Record<string, unknown>,
        format,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quality_report.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success(t('messages.exportSuccess'));
    } catch {
      message.error(t('messages.exportFailed'));
    }
  };

  const handleScheduleReport = async () => {
    try {
      const values = await form.validateFields();
      await qualityApi.scheduleReport({
        project_id: projectId,
        report_type: values.report_type,
        schedule: values.schedule,
        recipients: values.recipients.split(',').map((e: string) => e.trim()),
      });
      message.success(t('messages.scheduleCreated'));
      setScheduleModalVisible(false);
      form.resetFields();
    } catch {
      message.error(t('messages.createFailed'));
    }
  };

  const rankingColumns: ColumnsType<AnnotatorRanking> = [
    {
      title: t('reports.annotatorRanking.columns.rank'),
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      render: (rank: number) => (
        <span style={{ color: rank <= 3 ? '#faad14' : undefined, fontWeight: rank <= 3 ? 'bold' : undefined }}>
          {rank <= 3 ? <TrophyOutlined style={{ marginRight: 4 }} /> : null}
          {rank}
        </span>
      ),
    },
    { title: t('reports.annotatorRanking.columns.annotator'), dataIndex: 'annotator_name', key: 'annotator_name' },
    { title: t('reports.annotatorRanking.columns.annotations'), dataIndex: 'total_annotations', key: 'total_annotations' },
    {
      title: t('reports.annotatorRanking.columns.avgScore'),
      dataIndex: 'average_score',
      key: 'average_score',
      render: (score: number) => <Progress percent={score * 100} size="small" format={(p) => `${p?.toFixed(0)}%`} />,
    },
    {
      title: t('reports.annotatorRanking.columns.accuracy'),
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: t('reports.annotatorRanking.columns.passRate'),
      dataIndex: 'pass_rate',
      key: 'pass_rate',
      render: (v: number) => <Tag color={v >= 0.9 ? 'green' : v >= 0.7 ? 'gold' : 'red'}>{(v * 100).toFixed(1)}%</Tag>,
    },
  ];

  return (
    <div>
      <Tabs
        items={[
          {
            key: 'project',
            label: (
              <span>
                <FileTextOutlined /> {t('reports.projectReport.title')}
              </span>
            ),
            children: (
              <Card
                title={t('reports.projectReport.title')}
                extra={
                  <Space>
                    <RangePicker
                      onChange={(_, dateStrings) => {
                        if (dateStrings[0] && dateStrings[1]) {
                          handleGenerateProjectReport(dateStrings as [string, string]);
                        }
                      }}
                    />
                    <Button icon={<ScheduleOutlined />} onClick={() => setScheduleModalVisible(true)}>
                      {t('reports.projectReport.scheduleReport')}
                    </Button>
                    <Select defaultValue="pdf" style={{ width: 120 }} onChange={(v) => handleExport(v)}>
                      <Option value="pdf">{t('reports.projectReport.exportPdf')}</Option>
                      <Option value="excel">{t('reports.projectReport.exportExcel')}</Option>
                      <Option value="html">{t('reports.projectReport.exportHtml')}</Option>
                      <Option value="json">{t('reports.projectReport.exportJson')}</Option>
                    </Select>
                  </Space>
                }
              >
                <Spin spinning={loading}>
                  {projectReport ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 24 }}>
                        <Col span={6}>
                          <Statistic title={t('reports.projectReport.totalAnnotations')} value={projectReport.total_annotations} />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title={t('reports.projectReport.avgAccuracy')}
                            value={(projectReport.average_scores.accuracy || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title={t('reports.projectReport.avgCompleteness')}
                            value={(projectReport.average_scores.completeness || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title={t('reports.projectReport.avgTimeliness')}
                            value={(projectReport.average_scores.timeliness || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                      </Row>
                      <Card title={t('reports.projectReport.issueDistribution')} size="small">
                        <Row gutter={16}>
                          {Object.entries(projectReport.issue_distribution).map(([type, count]) => (
                            <Col span={6} key={type}>
                              <Statistic title={type} value={count as number} />
                            </Col>
                          ))}
                        </Row>
                      </Card>
                      <Card title={t('reports.projectReport.qualityTrend')} size="small" style={{ marginTop: 16 }}>
                        <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                          <span style={{ color: '#999' }}>{t('reports.projectReport.trendChart')}</span>
                        </div>
                      </Card>
                    </>
                  ) : (
                    <Empty description={t('reports.projectReport.selectDateRange')} />
                  )}
                </Spin>
              </Card>
            ),
          },
          {
            key: 'ranking',
            label: (
              <span>
                <TrophyOutlined /> {t('reports.annotatorRanking.title')}
              </span>
            ),
            children: (
              <Card
                title={t('reports.annotatorRanking.title')}
                extra={
                  <Space>
                    <Select defaultValue="month" style={{ width: 120 }} onChange={handleGenerateRankingReport}>
                      <Option value="week">{t('reports.annotatorRanking.period.week')}</Option>
                      <Option value="month">{t('reports.annotatorRanking.period.month')}</Option>
                      <Option value="quarter">{t('reports.annotatorRanking.period.quarter')}</Option>
                      <Option value="year">{t('reports.annotatorRanking.period.year')}</Option>
                    </Select>
                    <Button icon={<ReloadOutlined />} onClick={() => handleGenerateRankingReport('month')}>
                      {t('reports.actions.refresh')}
                    </Button>
                  </Space>
                }
              >
                <Spin spinning={loading}>
                  {rankingReport ? (
                    <Table dataSource={rankingReport.rankings} columns={rankingColumns} rowKey="annotator_id" pagination={false} />
                  ) : (
                    <Empty description={t('reports.annotatorRanking.selectPeriod')} />
                  )}
                </Spin>
              </Card>
            ),
          },
          {
            key: 'trend',
            label: (
              <span>
                <LineChartOutlined /> {t('reports.trendAnalysis.title')}
              </span>
            ),
            children: (
              <Card title={t('reports.trendAnalysis.title')}>
                <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                  <span style={{ color: '#999' }}>{t('reports.trendAnalysis.chart')}</span>
                </div>
              </Card>
            ),
          },
        ]}
      />

      {/* 定时报告弹窗 */}
      <Modal
        title={t('reports.scheduleModal.title')}
        open={scheduleModalVisible}
        onOk={handleScheduleReport}
        onCancel={() => setScheduleModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="report_type" label={t('reports.scheduleModal.reportType')} rules={[{ required: true }]}>
            <Select placeholder={t('reports.scheduleModal.selectReportType')}>
              <Option value="project">{t('reports.scheduleModal.projectReport')}</Option>
              <Option value="ranking">{t('reports.scheduleModal.rankingReport')}</Option>
              <Option value="trend">{t('reports.scheduleModal.trendReport')}</Option>
            </Select>
          </Form.Item>
          <Form.Item name="schedule" label={t('reports.scheduleModal.schedule')} rules={[{ required: true }]}>
            <Select placeholder={t('reports.scheduleModal.selectSchedule')}>
              <Option value="0 9 * * 1">{t('reports.scheduleModal.weeklyMonday')}</Option>
              <Option value="0 9 1 * *">{t('reports.scheduleModal.monthlyFirst')}</Option>
              <Option value="0 9 * * *">{t('reports.scheduleModal.daily')}</Option>
            </Select>
          </Form.Item>
          <Form.Item name="recipients" label={t('reports.scheduleModal.recipients')} rules={[{ required: true }]}>
            <Input placeholder={t('reports.scheduleModal.recipientsPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportViewer;
