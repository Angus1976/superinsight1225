/**
 * ApprovalChainBuilder Component (审批链构建器)
 * 
 * Visual builder for creating and editing approval chains with:
 * - Add/remove approval levels (1-5 levels)
 * - Assign approvers to each level
 * - Configure approval type (PARALLEL/SEQUENTIAL)
 * - Set deadlines and minimum approvals
 * 
 * Requirements: 13.1, 13.5
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Radio,
  InputNumber,
  Divider,
  Alert,
  message,
  Tooltip,
  Typography,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  TeamOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  ontologyApprovalApi,
  ontologyExpertApi,
  type ApprovalChain,
  type ApprovalLevel,
  type ApprovalChainCreateRequest,
  type ExpertProfile,
} from '../../services/ontologyExpertApi';

const { Text } = Typography;

interface ApprovalChainBuilderProps {
  chain?: ApprovalChain;
  onSuccess?: (chain: ApprovalChain) => void;
  onCancel?: () => void;
}

interface LevelFormData {
  approvers: string[];
  deadline_hours: number;
  min_approvals?: number;
}

interface FormData {
  name: string;
  ontology_area: string;
  approval_type: 'PARALLEL' | 'SEQUENTIAL';
  levels: LevelFormData[];
}

const ONTOLOGY_AREAS = [
  '金融',
  '医疗',
  '制造',
  '政务',
  '法律',
  '教育',
];

const MAX_LEVELS = 5;
const MIN_LEVELS = 1;

const ApprovalChainBuilder: React.FC<ApprovalChainBuilderProps> = ({
  chain,
  onSuccess,
  onCancel,
}) => {
  const { t } = useTranslation('ontology');
  const [form] = Form.useForm<FormData>();
  const [loading, setLoading] = useState(false);
  const [experts, setExperts] = useState<ExpertProfile[]>([]);
  const [loadingExperts, setLoadingExperts] = useState(false);

  const isEditing = !!chain;

  // Load experts for approver selection
  useEffect(() => {
    const loadExperts = async () => {
      setLoadingExperts(true);
      try {
        const response = await ontologyExpertApi.listExperts({ status: 'active', limit: 100 });
        setExperts(response.experts);
      } catch (error) {
        console.error('Failed to load experts:', error);
      } finally {
        setLoadingExperts(false);
      }
    };
    loadExperts();
  }, []);

  // Initialize form with chain data if editing
  useEffect(() => {
    if (chain) {
      form.setFieldsValue({
        name: chain.name,
        ontology_area: chain.ontology_area,
        approval_type: chain.approval_type,
        levels: chain.levels.map((level) => ({
          approvers: level.approvers,
          deadline_hours: level.deadline_hours,
          min_approvals: level.min_approvals,
        })),
      });
    } else {
      // Default values for new chain
      form.setFieldsValue({
        approval_type: 'SEQUENTIAL',
        levels: [{ approvers: [], deadline_hours: 24 }],
      });
    }
  }, [chain, form]);

  const handleSubmit = async (values: FormData) => {
    setLoading(true);
    try {
      const request: ApprovalChainCreateRequest = {
        name: values.name,
        ontology_area: values.ontology_area,
        approval_type: values.approval_type,
        levels: values.levels.map((level, index) => ({
          level_number: index + 1,
          approvers: level.approvers,
          deadline_hours: level.deadline_hours,
          min_approvals: level.min_approvals,
        })),
      };

      const result = await ontologyApprovalApi.createApprovalChain(request);
      message.success(t(isEditing ? 'approval.updateSuccess' : 'approval.createSuccess'));
      onSuccess?.(result);
    } catch (error) {
      console.error('Failed to save approval chain:', error);
      message.error(t(isEditing ? 'approval.updateFailed' : 'approval.createFailed'));
    } finally {
      setLoading(false);
    }
  };

  const renderLevelCard = (
    field: { key: number; name: number },
    index: number,
    remove: (index: number) => void,
    totalLevels: number
  ) => {
    const approvalType = form.getFieldValue('approval_type');
    const showMinApprovals = approvalType === 'PARALLEL';

    return (
      <Card
        key={field.key}
        size="small"
        title={
          <Space>
            <TeamOutlined />
            <span>{t('approval.levelNumber', { number: index + 1 })}</span>
          </Space>
        }
        extra={
          totalLevels > MIN_LEVELS && (
            <Tooltip title={t('approval.removeLevel')}>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => remove(field.name)}
              />
            </Tooltip>
          )
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col span={showMinApprovals ? 12 : 16}>
            <Form.Item
              name={[field.name, 'approvers']}
              label={t('approval.approvers')}
              rules={[{ required: true, message: t('approval.approversRequired') }]}
            >
              <Select
                mode="multiple"
                placeholder={t('approval.approversPlaceholder')}
                loading={loadingExperts}
                optionFilterProp="label"
                options={experts.map((expert) => ({
                  value: expert.id,
                  label: `${expert.name} (${expert.expertise_areas.join(', ')})`,
                }))}
              />
            </Form.Item>
          </Col>
          <Col span={showMinApprovals ? 6 : 8}>
            <Form.Item
              name={[field.name, 'deadline_hours']}
              label={
                <Space>
                  <ClockCircleOutlined />
                  {t('approval.deadlineHours')}
                </Space>
              }
              rules={[{ required: true, message: t('approval.deadlineHoursRequired') }]}
            >
              <InputNumber
                min={1}
                max={720}
                style={{ width: '100%' }}
                placeholder={t('approval.deadlineHoursPlaceholder')}
              />
            </Form.Item>
          </Col>
          {showMinApprovals && (
            <Col span={6}>
              <Form.Item
                name={[field.name, 'min_approvals']}
                label={
                  <Space>
                    {t('approval.minApprovals')}
                    <Tooltip title={t('approval.minApprovalsHint')}>
                      <InfoCircleOutlined />
                    </Tooltip>
                  </Space>
                }
              >
                <InputNumber
                  min={1}
                  style={{ width: '100%' }}
                  placeholder={t('approval.minApprovalsPlaceholder')}
                />
              </Form.Item>
            </Col>
          )}
        </Row>
      </Card>
    );
  };

  return (
    <Card title={t(isEditing ? 'approval.editChain' : 'approval.createChain')}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          approval_type: 'SEQUENTIAL',
          levels: [{ approvers: [], deadline_hours: 24 }],
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="name"
              label={t('approval.chainName')}
              rules={[{ required: true, message: t('approval.chainNameRequired') }]}
            >
              <Input placeholder={t('approval.chainNamePlaceholder')} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="ontology_area"
              label={t('approval.ontologyArea')}
              rules={[{ required: true, message: t('approval.ontologyAreaRequired') }]}
            >
              <Select
                placeholder={t('approval.ontologyAreaPlaceholder')}
                showSearch
                allowClear
              >
                {ONTOLOGY_AREAS.map((area) => (
                  <Select.Option key={area} value={area}>
                    {area}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="approval_type"
          label={t('approval.approvalType')}
        >
          <Radio.Group>
            <Radio.Button value="SEQUENTIAL">
              <Space>
                {t('approval.approvalTypeSequential')}
                <Tooltip title={t('approval.approvalTypeSequentialDesc')}>
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            </Radio.Button>
            <Radio.Button value="PARALLEL">
              <Space>
                {t('approval.approvalTypeParallel')}
                <Tooltip title={t('approval.approvalTypeParallelDesc')}>
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            </Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Divider orientation="left">{t('approval.levels')}</Divider>

        <Form.List name="levels">
          {(fields, { add, remove }) => (
            <>
              {fields.map((field, index) =>
                renderLevelCard(field, index, remove, fields.length)
              )}

              {fields.length < MAX_LEVELS ? (
                <Button
                  type="dashed"
                  onClick={() => add({ approvers: [], deadline_hours: 24 })}
                  block
                  icon={<PlusOutlined />}
                >
                  {t('approval.addLevel')}
                </Button>
              ) : (
                <Alert
                  message={t('approval.maxLevels')}
                  type="info"
                  showIcon
                />
              )}
            </>
          )}
        </Form.List>

        <Divider />

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              {t(isEditing ? 'common.save' : 'common.create')}
            </Button>
            {onCancel && (
              <Button onClick={onCancel}>
                {t('common.cancel')}
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default ApprovalChainBuilder;
