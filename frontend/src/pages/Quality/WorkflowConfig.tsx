/**
 * Workflow Configuration Component - 工作流配置组件
 * 实现质量改进工作流的配置界面
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Switch,
  Button,
  Space,
  Tag,
  message,
  Spin,
  Row,
  Col,
  Statistic,
  Alert,
  Steps,
  Divider,
  InputNumber,
  Select,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { workflowApi, type QualityWorkflow, type ImprovementEffectReport } from '@/services/workflowApi';

const { Option } = Select;

interface WorkflowConfigProps {
  projectId: string;
}

const WorkflowConfig: React.FC<WorkflowConfigProps> = ({ projectId }) => {
  const { t } = useTranslation(['quality', 'common']);
  const [workflow, setWorkflow] = useState<QualityWorkflow | null>(null);
  const [effectReport, setEffectReport] = useState<ImprovementEffectReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const defaultStages = ['identify', 'assign', 'improve', 'review', 'verify'];

  useEffect(() => {
    loadWorkflowConfig();
    loadEffectReport();
  }, [projectId]);

  const loadWorkflowConfig = async () => {
    setLoading(true);
    try {
      const data = await workflowApi.getWorkflowConfig(projectId);
      setWorkflow(data);
      form.setFieldsValue({
        stages: data.stages,
        auto_create_task: data.auto_create_task,
        escalation_hours: data.escalation_rules?.hours || 24,
        escalation_level: data.escalation_rules?.max_level || 3,
      });
    } catch {
      // Use defaults if no config exists
      form.setFieldsValue({
        stages: defaultStages,
        auto_create_task: true,
        escalation_hours: 24,
        escalation_level: 3,
      });
    } finally {
      setLoading(false);
    }
  };

  const loadEffectReport = async () => {
    try {
      const data = await workflowApi.evaluateEffect(projectId, 'month');
      setEffectReport(data);
    } catch {
      // Effect report is optional
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await workflowApi.configureWorkflow({
        project_id: projectId,
        stages: values.stages,
        auto_create_task: values.auto_create_task,
        escalation_rules: {
          hours: values.escalation_hours,
          max_level: values.escalation_level,
        },
      });
      message.success(t('workflow.messages.configSaved'));
      loadWorkflowConfig();
    } catch {
      message.error(t('workflow.messages.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const stageLabels: Record<string, string> = {
    identify: t('workflow.stageLabels.identify'),
    assign: t('workflow.stageLabels.assign'),
    improve: t('workflow.stageLabels.improve'),
    review: t('workflow.stageLabels.review'),
    verify: t('workflow.stageLabels.verify'),
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Row gutter={16}>
        <Col span={16}>
          <Card
            title={
              <Space>
                <SettingOutlined />
                {t('workflow.title')}
              </Space>
            }
            extra={
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadWorkflowConfig}>
                  {t('workflow.reset')}
                </Button>
                <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
                  {t('workflow.saveConfig')}
                </Button>
              </Space>
            }
          >
            <Form form={form} layout="vertical">
              <Form.Item name="stages" label={t('workflow.stages')} help={t('workflow.stagesHelp')}>
                <Select mode="multiple" placeholder={t('workflow.selectStages')}>
                  {Object.entries(stageLabels).map(([key, label]) => (
                    <Option key={key} value={key}>
                      {label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {({ getFieldValue }) => {
                  const stages = getFieldValue('stages') || [];
                  return (
                    <Card size="small" style={{ marginBottom: 24, background: '#fafafa' }}>
                      <div style={{ marginBottom: 8, fontWeight: 500 }}>{t('workflow.flowPreview')}</div>
                      <Steps
                        size="small"
                        items={stages.map((stage: string, index: number) => ({
                          title: stageLabels[stage] || stage,
                          status: 'wait',
                        }))}
                      />
                    </Card>
                  );
                }}
              </Form.Item>

              <Divider>{t('workflow.automationSettings')}</Divider>

              <Form.Item name="auto_create_task" label={t('workflow.autoCreateTask')} valuePropName="checked">
                <Switch checkedChildren={t('common:enable')} unCheckedChildren={t('common:disable')} />
              </Form.Item>

              <Alert
                message={t('workflow.autoCreateTaskHelp')}
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Divider>{t('workflow.escalationRules')}</Divider>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="escalation_hours" label={t('workflow.escalationHours')} help={t('workflow.escalationHoursHelp')}>
                    <InputNumber min={1} max={168} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="escalation_level" label={t('workflow.maxEscalationLevel')} help={t('workflow.maxEscalationLevelHelp')}>
                    <InputNumber min={1} max={5} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </Card>
        </Col>

        <Col span={8}>
          {/* 效果统计 */}
          <Card title={t('workflow.effectStats')}>
            {effectReport ? (
              <>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic title={t('workflow.totalTasks')} value={effectReport.total_tasks} />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('workflow.completedTasks')}
                      value={effectReport.completed_tasks}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Col>
                  <Col span={24}>
                    <Statistic
                      title={t('workflow.avgImprovementScore')}
                      value={(effectReport.average_improvement_score * 100).toFixed(1)}
                      suffix="%"
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                </Row>

                <Divider>{t('workflow.improvementByDimension')}</Divider>

                {Object.entries(effectReport.improvement_by_dimension).map(([dim, score]) => (
                  <div key={dim} style={{ marginBottom: 8 }}>
                    <span>{dim}: </span>
                    <Tag color={score > 0 ? 'green' : score < 0 ? 'red' : 'default'}>
                      {score > 0 ? '+' : ''}
                      {(score * 100).toFixed(1)}%
                    </Tag>
                  </div>
                ))}
              </>
            ) : (
              <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>{t('workflow.noStats')}</div>
            )}
          </Card>

          {/* 工作流说明 */}
          <Card title={t('workflow.workflowGuide')} style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, color: '#666' }}>
              <p>
                <strong>{t('workflow.stageLabels.identify')}</strong>：{t('workflow.stageDescriptions.identify')}
              </p>
              <p>
                <strong>{t('workflow.stageLabels.assign')}</strong>：{t('workflow.stageDescriptions.assign')}
              </p>
              <p>
                <strong>{t('workflow.stageLabels.improve')}</strong>：{t('workflow.stageDescriptions.improve')}
              </p>
              <p>
                <strong>{t('workflow.stageLabels.review')}</strong>：{t('workflow.stageDescriptions.review')}
              </p>
              <p>
                <strong>{t('workflow.stageLabels.verify')}</strong>：{t('workflow.stageDescriptions.verify')}
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WorkflowConfig;
