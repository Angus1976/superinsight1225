/**
 * CreateTaskModal Component
 * 
 * Multi-step form modal for creating annotation tasks.
 * Steps: 1) Basic Info, 2) Select Samples, 3) Assign Annotators
 * 
 * Requirements: 14.2, 19.3
 */

import React, { useState, useCallback } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Steps,
  Button,
  Space,
  message,
  Typography,
} from 'antd';
import { useTranslation } from 'react-i18next';
import type { Dayjs } from 'dayjs';

const { TextArea } = Input;
const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

export interface CreateTaskFormData {
  name: string;
  description?: string;
  annotationType: string;
  instructions: string;
  deadline?: string;
  assignedTo: string[];
  sampleIds: string[];
}

export interface CreateTaskModalProps {
  visible: boolean;
  selectedSamples?: string[];
  onClose: () => void;
  onSubmit: (data: CreateTaskFormData) => Promise<void>;
}

// ============================================================================
// Component
// ============================================================================

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
  visible,
  selectedSamples = [],
  onClose,
  onSubmit,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);

  // Reset form when modal closes
  const handleClose = useCallback(() => {
    form.resetFields();
    setCurrentStep(0);
    onClose();
  }, [form, onClose]);

  // Handle next step
  const handleNext = useCallback(async () => {
    try {
      // Validate current step fields
      const fieldsToValidate = getStepFields(currentStep);
      await form.validateFields(fieldsToValidate);
      setCurrentStep(prev => prev + 1);
    } catch (error) {
      // Validation failed, stay on current step
    }
  }, [currentStep, form]);

  // Handle previous step
  const handlePrevious = useCallback(() => {
    setCurrentStep(prev => prev - 1);
  }, []);

  // Handle form submission
  const handleSubmit = useCallback(async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      // Format data
      const formData: CreateTaskFormData = {
        name: values.name,
        description: values.description,
        annotationType: values.annotationType,
        instructions: values.instructions,
        deadline: values.deadline?.toISOString(),
        assignedTo: values.assignedTo || [],
        sampleIds: selectedSamples,
      };

      await onSubmit(formData);
      message.success(t('annotationTask.messages.createSuccess'));
      handleClose();
    } catch (error) {
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [form, selectedSamples, onSubmit, t, handleClose]);

  // Get fields to validate for each step
  const getStepFields = (step: number): string[] => {
    switch (step) {
      case 0:
        return ['name', 'annotationType', 'instructions'];
      case 1:
        return []; // Sample selection is pre-filled
      case 2:
        return ['assignedTo'];
      default:
        return [];
    }
  };

  // Steps configuration
  const steps = [
    {
      title: t('annotationTask.steps.basicInfo'),
      description: t('annotationTask.steps.basicInfoDesc'),
    },
    {
      title: t('annotationTask.steps.selectSamples'),
      description: t('annotationTask.steps.selectSamplesDesc'),
    },
    {
      title: t('annotationTask.steps.assignAnnotators'),
      description: t('annotationTask.steps.assignAnnotatorsDesc'),
    },
  ];

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <>
            <Form.Item
              name="name"
              label={t('annotationTask.columns.name')}
              rules={[
                { required: true, message: t('annotationTask.validation.nameRequired') },
                { max: 100, message: t('annotationTask.validation.nameTooLong') },
              ]}
            >
              <Input placeholder={t('annotationTask.placeholders.name')} />
            </Form.Item>

            <Form.Item
              name="description"
              label={t('annotationTask.columns.description')}
            >
              <TextArea
                rows={3}
                placeholder={t('annotationTask.placeholders.description')}
              />
            </Form.Item>

            <Form.Item
              name="annotationType"
              label={t('annotationTask.fields.annotationType')}
              rules={[{ required: true, message: t('annotationTask.validation.typeRequired') }]}
            >
              <Select placeholder={t('annotationTask.placeholders.selectType')}>
                <Select.Option value="classification">
                  {t('annotationTask.types.classification')}
                </Select.Option>
                <Select.Option value="entity_recognition">
                  {t('annotationTask.types.entityRecognition')}
                </Select.Option>
                <Select.Option value="relation_extraction">
                  {t('annotationTask.types.relationExtraction')}
                </Select.Option>
                <Select.Option value="sentiment_analysis">
                  {t('annotationTask.types.sentimentAnalysis')}
                </Select.Option>
                <Select.Option value="custom">
                  {t('annotationTask.types.custom')}
                </Select.Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="instructions"
              label={t('annotationTask.fields.instructions')}
              rules={[{ required: true, message: t('annotationTask.validation.instructionsRequired') }]}
            >
              <TextArea
                rows={4}
                placeholder={t('annotationTask.placeholders.instructions')}
              />
            </Form.Item>

            <Form.Item
              name="deadline"
              label={t('annotationTask.columns.dueDate')}
              rules={[
                {
                  validator: (_, value: Dayjs) => {
                    if (!value) return Promise.resolve();
                    if (value.isBefore(new Date())) {
                      return Promise.reject(new Error(t('annotationTask.validation.deadlinePast')));
                    }
                    return Promise.resolve();
                  },
                },
              ]}
            >
              <DatePicker
                showTime
                style={{ width: '100%' }}
                placeholder={t('annotationTask.placeholders.deadline')}
              />
            </Form.Item>
          </>
        );

      case 1:
        return (
          <div>
            <Text strong>{t('sampleLibrary.title')}</Text>
            <div style={{ marginTop: 16, padding: 16, background: '#f5f5f5', borderRadius: 4 }}>
              <Text type="secondary">
                {t('annotationTask.messages.samplesSelected', { count: selectedSamples.length })}
              </Text>
              {selectedSamples.length === 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text type="warning">
                    {t('annotationTask.messages.noSamplesSelected')}
                  </Text>
                </div>
              )}
            </div>
          </div>
        );

      case 2:
        return (
          <>
            <Form.Item
              name="assignedTo"
              label={t('annotationTask.columns.assignee')}
              rules={[{ required: true, message: t('annotationTask.messages.assignee') }]}
            >
              <Select
                mode="multiple"
                placeholder={t('annotationTask.placeholders.selectAnnotators')}
                options={[
                  // TODO: Load from API
                  { label: 'User 1', value: 'user1' },
                  { label: 'User 2', value: 'user2' },
                  { label: 'User 3', value: 'user3' },
                ]}
              />
            </Form.Item>

            <div style={{ marginTop: 16, padding: 16, background: '#f0f9ff', borderRadius: 4 }}>
              <Text type="secondary">
                {t('annotationTask.messages.assignmentInfo')}
              </Text>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Modal
      title={t('annotationTask.actions.create')}
      open={visible}
      onCancel={handleClose}
      width={700}
      footer={null}
    >
      <div style={{ marginBottom: 24 }}>
        <Steps current={currentStep} items={steps} />
      </div>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          sampleIds: selectedSamples,
        }}
      >
        {renderStepContent()}
      </Form>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          {currentStep > 0 && (
            <Button onClick={handlePrevious}>
              {t('common.actions.previous')}
            </Button>
          )}
        </Space>
        <Space>
          <Button onClick={handleClose}>
            {t('common.actions.cancel')}
          </Button>
          {currentStep < steps.length - 1 ? (
            <Button type="primary" onClick={handleNext}>
              {t('common.actions.next')}
            </Button>
          ) : (
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
              disabled={selectedSamples.length === 0}
            >
              {t('common.actions.submit')}
            </Button>
          )}
        </Space>
      </div>
    </Modal>
  );
};

export default CreateTaskModal;
