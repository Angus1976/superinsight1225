// Task edit form component
import { Form, Input, Select, DatePicker, Button, Space, Row, Col } from 'antd';
import { SaveOutlined, CloseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import type { Task, TaskStatus, TaskPriority } from '@/types';

const { TextArea } = Input;

interface TaskEditFormProps {
  initialValues: Partial<Task>;
  onSubmit: (values: any) => void;
  onCancel: () => void;
  loading?: boolean;
}

export const TaskEditForm: React.FC<TaskEditFormProps> = ({
  initialValues,
  onSubmit,
  onCancel,
  loading = false,
}) => {
  const { t } = useTranslation('tasks');
  const [form] = Form.useForm();

  const handleFinish = (values: any) => {
    const payload = {
      ...values,
      due_date: values.due_date ? values.due_date.format('YYYY-MM-DD') : null,
    };
    onSubmit(payload);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        ...initialValues,
        due_date: initialValues.due_date ? dayjs(initialValues.due_date) : null,
      }}
      onFinish={handleFinish}
    >
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            name="name"
            label={t('taskName')}
            rules={[{ required: true, message: t('taskNameRequired') }]}
          >
            <Input placeholder={t('enterTaskName')} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            name="annotation_type"
            label={t('annotationType')}
            rules={[{ required: true, message: t('annotationTypeRequired') }]}
          >
            <Select placeholder={t('selectAnnotationType')}>
              <Select.Option value="text_classification">{t('typeTextClassification')}</Select.Option>
              <Select.Option value="ner">{t('typeNER')}</Select.Option>
              <Select.Option value="sentiment">{t('typeSentiment')}</Select.Option>
              <Select.Option value="qa">{t('typeQA')}</Select.Option>
              <Select.Option value="custom">{t('typeCustom')}</Select.Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        name="description"
        label={t('description')}
      >
        <TextArea rows={4} placeholder={t('enterDescription')} />
      </Form.Item>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            name="status"
            label={t('status')}
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="pending">{t('statusPending')}</Select.Option>
              <Select.Option value="in_progress">{t('statusInProgress')}</Select.Option>
              <Select.Option value="completed">{t('statusCompleted')}</Select.Option>
              <Select.Option value="cancelled">{t('statusCancelled')}</Select.Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="priority"
            label={t('priority')}
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="low">{t('priorityLow')}</Select.Option>
              <Select.Option value="medium">{t('priorityMedium')}</Select.Option>
              <Select.Option value="high">{t('priorityHigh')}</Select.Option>
              <Select.Option value="urgent">{t('priorityUrgent')}</Select.Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="due_date"
            label={t('dueDate')}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
        <Space>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={loading}
          >
            {t('save')}
          </Button>
          <Button icon={<CloseOutlined />} onClick={onCancel}>
            {t('cancel')}
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

export default TaskEditForm;
