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
import { workflowApi, type QualityWorkflow, type ImprovementEffectReport } from '@/services/workflowApi';

const { Option } = Select;

interface WorkflowConfigProps {
  projectId: string;
}

const WorkflowConfig: React.FC<WorkflowConfigProps> = ({ projectId }) => {
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
      message.success('配置已保存');
      loadWorkflowConfig();
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const stageLabels: Record<string, string> = {
    identify: '问题识别',
    assign: '任务分配',
    improve: '改进执行',
    review: '审核验证',
    verify: '效果评估',
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
                工作流配置
              </Space>
            }
            extra={
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadWorkflowConfig}>
                  重置
                </Button>
                <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
                  保存配置
                </Button>
              </Space>
            }
          >
            <Form form={form} layout="vertical">
              <Form.Item name="stages" label="工作流阶段" help="定义质量改进的流程阶段">
                <Select mode="multiple" placeholder="选择工作流阶段">
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
                      <div style={{ marginBottom: 8, fontWeight: 500 }}>流程预览</div>
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

              <Divider>自动化设置</Divider>

              <Form.Item name="auto_create_task" label="自动创建改进任务" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>

              <Alert
                message="开启后，当质量检查发现问题时，系统将自动创建改进任务并分配给原标注员"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Divider>升级规则</Divider>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="escalation_hours" label="升级时间（小时）" help="任务超过此时间未处理将自动升级">
                    <InputNumber min={1} max={168} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="escalation_level" label="最大升级级别" help="任务最多可升级的级别数">
                    <InputNumber min={1} max={5} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </Card>
        </Col>

        <Col span={8}>
          {/* 效果统计 */}
          <Card title="改进效果统计">
            {effectReport ? (
              <>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic title="总任务数" value={effectReport.total_tasks} />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="完成任务"
                      value={effectReport.completed_tasks}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Col>
                  <Col span={24}>
                    <Statistic
                      title="平均改进分数"
                      value={(effectReport.average_improvement_score * 100).toFixed(1)}
                      suffix="%"
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                </Row>

                <Divider>各维度改进</Divider>

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
              <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>暂无统计数据</div>
            )}
          </Card>

          {/* 工作流说明 */}
          <Card title="工作流说明" style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, color: '#666' }}>
              <p>
                <strong>问题识别</strong>：系统自动检测质量问题
              </p>
              <p>
                <strong>任务分配</strong>：将改进任务分配给负责人
              </p>
              <p>
                <strong>改进执行</strong>：负责人修正问题并提交
              </p>
              <p>
                <strong>审核验证</strong>：审核人员验证改进结果
              </p>
              <p>
                <strong>效果评估</strong>：评估改进对质量的影响
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WorkflowConfig;
