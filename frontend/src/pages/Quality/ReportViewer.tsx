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
      message.success('报告生成成功');
    } catch {
      message.error('生成报告失败');
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
      message.success('排名报告生成成功');
    } catch {
      message.error('生成报告失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'pdf' | 'excel' | 'html' | 'json') => {
    if (!projectReport && !rankingReport) {
      message.warning('请先生成报告');
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
      message.success('导出成功');
    } catch {
      message.error('导出失败');
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
      message.success('定时报告已创建');
      setScheduleModalVisible(false);
      form.resetFields();
    } catch {
      message.error('创建失败');
    }
  };

  const rankingColumns: ColumnsType<AnnotatorRanking> = [
    {
      title: '排名',
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
    { title: '标注员', dataIndex: 'annotator_name', key: 'annotator_name' },
    { title: '标注数', dataIndex: 'total_annotations', key: 'total_annotations' },
    {
      title: '平均分',
      dataIndex: 'average_score',
      key: 'average_score',
      render: (score: number) => <Progress percent={score * 100} size="small" format={(p) => `${p?.toFixed(0)}%`} />,
    },
    {
      title: '准确率',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: '通过率',
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
                <FileTextOutlined /> 项目报告
              </span>
            ),
            children: (
              <Card
                title="项目质量报告"
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
                      定时报告
                    </Button>
                    <Select defaultValue="pdf" style={{ width: 100 }} onChange={(v) => handleExport(v)}>
                      <Option value="pdf">导出 PDF</Option>
                      <Option value="excel">导出 Excel</Option>
                      <Option value="html">导出 HTML</Option>
                      <Option value="json">导出 JSON</Option>
                    </Select>
                  </Space>
                }
              >
                <Spin spinning={loading}>
                  {projectReport ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 24 }}>
                        <Col span={6}>
                          <Statistic title="总标注数" value={projectReport.total_annotations} />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="平均准确率"
                            value={(projectReport.average_scores.accuracy || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="平均完整性"
                            value={(projectReport.average_scores.completeness || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="平均时效性"
                            value={(projectReport.average_scores.timeliness || 0) * 100}
                            precision={1}
                            suffix="%"
                          />
                        </Col>
                      </Row>
                      <Card title="问题分布" size="small">
                        <Row gutter={16}>
                          {Object.entries(projectReport.issue_distribution).map(([type, count]) => (
                            <Col span={6} key={type}>
                              <Statistic title={type} value={count as number} />
                            </Col>
                          ))}
                        </Row>
                      </Card>
                      <Card title="质量趋势" size="small" style={{ marginTop: 16 }}>
                        <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                          <span style={{ color: '#999' }}>趋势图表 (需要集成图表库)</span>
                        </div>
                      </Card>
                    </>
                  ) : (
                    <Empty description="选择日期范围生成报告" />
                  )}
                </Spin>
              </Card>
            ),
          },
          {
            key: 'ranking',
            label: (
              <span>
                <TrophyOutlined /> 标注员排名
              </span>
            ),
            children: (
              <Card
                title="标注员质量排名"
                extra={
                  <Space>
                    <Select defaultValue="month" style={{ width: 120 }} onChange={handleGenerateRankingReport}>
                      <Option value="week">本周</Option>
                      <Option value="month">本月</Option>
                      <Option value="quarter">本季度</Option>
                      <Option value="year">本年</Option>
                    </Select>
                    <Button icon={<ReloadOutlined />} onClick={() => handleGenerateRankingReport('month')}>
                      刷新
                    </Button>
                  </Space>
                }
              >
                <Spin spinning={loading}>
                  {rankingReport ? (
                    <Table dataSource={rankingReport.rankings} columns={rankingColumns} rowKey="annotator_id" pagination={false} />
                  ) : (
                    <Empty description="选择时间范围生成排名" />
                  )}
                </Spin>
              </Card>
            ),
          },
          {
            key: 'trend',
            label: (
              <span>
                <LineChartOutlined /> 趋势分析
              </span>
            ),
            children: (
              <Card title="质量趋势分析">
                <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                  <span style={{ color: '#999' }}>趋势分析图表 (需要集成图表库)</span>
                </div>
              </Card>
            ),
          },
        ]}
      />

      {/* 定时报告弹窗 */}
      <Modal
        title="创建定时报告"
        open={scheduleModalVisible}
        onOk={handleScheduleReport}
        onCancel={() => setScheduleModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="report_type" label="报告类型" rules={[{ required: true }]}>
            <Select placeholder="选择报告类型">
              <Option value="project">项目质量报告</Option>
              <Option value="ranking">标注员排名报告</Option>
              <Option value="trend">趋势分析报告</Option>
            </Select>
          </Form.Item>
          <Form.Item name="schedule" label="执行周期" rules={[{ required: true }]}>
            <Select placeholder="选择执行周期">
              <Option value="0 9 * * 1">每周一 9:00</Option>
              <Option value="0 9 1 * *">每月1日 9:00</Option>
              <Option value="0 9 * * *">每天 9:00</Option>
            </Select>
          </Form.Item>
          <Form.Item name="recipients" label="接收人邮箱" rules={[{ required: true }]}>
            <Input placeholder="多个邮箱用逗号分隔" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportViewer;
