/**
 * Expert Profile Form Component (专家档案表单)
 * 
 * Form for creating and editing expert profiles with validation.
 * Supports expertise areas, certifications, and language preferences.
 * 
 * Requirements: 1.1, 1.2 - Expert Role Management
 */

import React, { useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Button,
  Space,
  Card,
  message,
  Divider,
  Typography,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  TeamOutlined,
  SafetyCertificateOutlined,
  GlobalOutlined,
  SaveOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  ontologyExpertApi,
  ExpertProfile,
  ExpertCreateRequest,
  ExpertUpdateRequest,
  ExpertiseArea,
  CertificationType,
  ExpertStatus,
  AvailabilityLevel,
} from '@/services/ontologyExpertApi';

const { TextArea } = Input;
const { Title } = Typography;

// Expertise area options
const EXPERTISE_AREAS: { value: ExpertiseArea; label: string }[] = [
  { value: '金融', label: '金融 (Finance)' },
  { value: '医疗', label: '医疗 (Healthcare)' },
  { value: '制造', label: '制造 (Manufacturing)' },
  { value: '政务', label: '政务 (Government)' },
  { value: '法律', label: '法律 (Legal)' },
  { value: '教育', label: '教育 (Education)' },
];

// Certification options
const CERTIFICATION_TYPES: { value: CertificationType; label: string }[] = [
  { value: 'CFA', label: 'CFA (Chartered Financial Analyst)' },
  { value: 'CPA', label: 'CPA (Certified Public Accountant)' },
  { value: 'PMP', label: 'PMP (Project Management Professional)' },
  { value: 'CISSP', label: 'CISSP (Certified Information Systems Security Professional)' },
  { value: 'AWS_CERTIFIED', label: 'AWS Certified' },
  { value: 'AZURE_CERTIFIED', label: 'Azure Certified' },
  { value: 'OTHER', label: 'Other' },
];

// Language options
const LANGUAGE_OPTIONS = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en-US', label: 'English (US)' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'ja-JP', label: '日本語' },
  { value: 'ko-KR', label: '한국어' },
];

// Status options
const STATUS_OPTIONS: { value: ExpertStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'pending', label: 'Pending' },
  { value: 'suspended', label: 'Suspended' },
];

// Availability options
const AVAILABILITY_OPTIONS: { value: AvailabilityLevel; label: string }[] = [
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'unavailable', label: 'Unavailable' },
];

interface ExpertProfileFormProps {
  expert?: ExpertProfile | null;
  onSuccess?: () => void;
  onCancel?: () => void;
}

interface FormValues {
  name: string;
  email: string;
  expertise_areas: ExpertiseArea[];
  certifications: CertificationType[];
  languages: string[];
  department?: string;
  title?: string;
  bio?: string;
  status?: ExpertStatus;
  availability?: AvailabilityLevel;
}

const ExpertProfileForm: React.FC<ExpertProfileFormProps> = ({
  expert,
  onSuccess,
  onCancel,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const queryClient = useQueryClient();
  const [form] = Form.useForm<FormValues>();
  const isEditing = !!expert;

  // Set form values when editing
  useEffect(() => {
    if (expert) {
      form.setFieldsValue({
        name: expert.name,
        email: expert.email,
        expertise_areas: expert.expertise_areas,
        certifications: expert.certifications,
        languages: expert.languages,
        department: expert.department,
        title: expert.title,
        bio: expert.bio,
        status: expert.status,
        availability: expert.availability,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        languages: ['zh-CN'],
        status: 'active',
        availability: 'high',
      });
    }
  }, [expert, form]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ExpertCreateRequest) => ontologyExpertApi.createExpert(data),
    onSuccess: () => {
      message.success(t('ontology:expert.createSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ontology-experts'] });
      form.resetFields();
      onSuccess?.();
    },
    onError: (error: Error) => {
      message.error(`${t('ontology:expert.createFailed')}: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ExpertUpdateRequest }) =>
      ontologyExpertApi.updateExpert(id, data),
    onSuccess: () => {
      message.success(t('ontology:expert.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ontology-experts'] });
      onSuccess?.();
    },
    onError: (error: Error) => {
      message.error(`${t('ontology:expert.updateFailed')}: ${error.message}`);
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (isEditing && expert) {
        updateMutation.mutate({
          id: expert.id,
          data: {
            name: values.name,
            expertise_areas: values.expertise_areas,
            certifications: values.certifications,
            languages: values.languages,
            department: values.department,
            title: values.title,
            bio: values.bio,
            status: values.status,
            availability: values.availability,
          },
        });
      } else {
        createMutation.mutate({
          name: values.name,
          email: values.email,
          expertise_areas: values.expertise_areas,
          certifications: values.certifications,
          languages: values.languages,
          department: values.department,
          title: values.title,
          bio: values.bio,
        });
      }
    } catch {
      // Form validation error
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Card>
      <Title level={4}>
        {isEditing ? t('ontology:expert.editProfile') : t('ontology:expert.createProfile')}
      </Title>
      
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* Basic Information */}
        <Divider orientation="left">{t('ontology:expert.basicInfo')}</Divider>
        
        <Form.Item
          name="name"
          label={t('ontology:expert.name')}
          rules={[
            { required: true, message: t('ontology:expert.nameRequired') },
            { max: 100, message: t('ontology:expert.nameTooLong') },
          ]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder={t('ontology:expert.namePlaceholder')}
          />
        </Form.Item>

        <Form.Item
          name="email"
          label={t('ontology:expert.email')}
          rules={[
            { required: true, message: t('ontology:expert.emailRequired') },
            { type: 'email', message: t('ontology:expert.emailInvalid') },
          ]}
        >
          <Input
            prefix={<MailOutlined />}
            placeholder={t('ontology:expert.emailPlaceholder')}
            disabled={isEditing}
          />
        </Form.Item>

        <Form.Item
          name="department"
          label={t('ontology:expert.department')}
        >
          <Input
            prefix={<TeamOutlined />}
            placeholder={t('ontology:expert.departmentPlaceholder')}
          />
        </Form.Item>

        <Form.Item
          name="title"
          label={t('ontology:expert.title')}
        >
          <Input placeholder={t('ontology:expert.titlePlaceholder')} />
        </Form.Item>

        <Form.Item
          name="bio"
          label={t('ontology:expert.bio')}
        >
          <TextArea
            rows={3}
            placeholder={t('ontology:expert.bioPlaceholder')}
            maxLength={500}
            showCount
          />
        </Form.Item>

        {/* Expertise */}
        <Divider orientation="left">{t('ontology:expert.expertise')}</Divider>

        <Form.Item
          name="expertise_areas"
          label={t('ontology:expert.expertiseAreas')}
          rules={[
            { required: true, message: t('ontology:expert.expertiseAreasRequired') },
          ]}
        >
          <Select
            mode="multiple"
            placeholder={t('ontology:expert.expertiseAreasPlaceholder')}
            options={EXPERTISE_AREAS}
          />
        </Form.Item>

        <Form.Item
          name="certifications"
          label={t('ontology:expert.certifications')}
        >
          <Select
            mode="multiple"
            placeholder={t('ontology:expert.certificationsPlaceholder')}
            options={CERTIFICATION_TYPES}
            prefix={<SafetyCertificateOutlined />}
          />
        </Form.Item>

        <Form.Item
          name="languages"
          label={t('ontology:expert.languages')}
          rules={[
            { required: true, message: t('ontology:expert.languagesRequired') },
          ]}
        >
          <Select
            mode="multiple"
            placeholder={t('ontology:expert.languagesPlaceholder')}
            options={LANGUAGE_OPTIONS}
            prefix={<GlobalOutlined />}
          />
        </Form.Item>

        {/* Status (only for editing) */}
        {isEditing && (
          <>
            <Divider orientation="left">{t('ontology:expert.statusSection')}</Divider>

            <Form.Item
              name="status"
              label={t('ontology:expert.status')}
            >
              <Select options={STATUS_OPTIONS} />
            </Form.Item>

            <Form.Item
              name="availability"
              label={t('ontology:expert.availability')}
            >
              <Select options={AVAILABILITY_OPTIONS} />
            </Form.Item>
          </>
        )}

        {/* Actions */}
        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={isLoading}
            >
              {isEditing ? t('common:save') : t('common:create')}
            </Button>
            {onCancel && (
              <Button icon={<CloseOutlined />} onClick={onCancel}>
                {t('common:cancel')}
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default ExpertProfileForm;
