/**
 * Expert List Component (专家列表)
 * 
 * Displays a list of experts with filtering, pagination, and actions.
 * Supports filtering by expertise area, language, and status.
 * 
 * Requirements: 9.4 - Expert Search and Filtering
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Row,
  Col,
  Tooltip,
  Modal,
  message,
  Badge,
  Avatar,
  Typography,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  ReloadOutlined,
  EyeOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  ontologyExpertApi,
  ExpertProfile,
  ExpertiseArea,
  ExpertStatus,
  AvailabilityLevel,
} from '@/services/ontologyExpertApi';
import ExpertProfileForm from './ExpertProfileForm';
import ExpertMetrics from './ExpertMetrics';

const { Text } = Typography;

// Expertise area options
const EXPERTISE_AREAS: { value: ExpertiseArea; label: string }[] = [
  { value: '金融', label: '金融 (Finance)' },
  { value: '医疗', label: '医疗 (Healthcare)' },
  { value: '制造', label: '制造 (Manufacturing)' },
  { value: '政务', label: '政务 (Government)' },
  { value: '法律', label: '法律 (Legal)' },
  { value: '教育', label: '教育 (Education)' },
];

// Status options
const STATUS_OPTIONS: { value: ExpertStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'pending', label: 'Pending' },
  { value: 'suspended', label: 'Suspended' },
];

// Language options
const LANGUAGE_OPTIONS = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en-US', label: 'English' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'ja-JP', label: '日本語' },
  { value: 'ko-KR', label: '한국어' },
];

// Status badge colors
const STATUS_COLORS: Record<ExpertStatus, string> = {
  active: 'success',
  inactive: 'default',
  pending: 'warning',
  suspended: 'error',
};

// Availability badge colors
const AVAILABILITY_COLORS: Record<AvailabilityLevel, string> = {
  high: 'green',
  medium: 'orange',
  low: 'red',
  unavailable: 'default',
};

// Expertise area colors
const EXPERTISE_COLORS: Record<ExpertiseArea, string> = {
  '金融': 'blue',
  '医疗': 'green',
  '制造': 'orange',
  '政务': 'purple',
  '法律': 'red',
  '教育': 'cyan',
};

interface ExpertListProps {
  onSelectExpert?: (expert: ExpertProfile) => void;
}

const ExpertList: React.FC<ExpertListProps> = ({ onSelectExpert }) => {
  const { t } = useTranslation(['ontology', 'common']);
  const queryClient = useQueryClient();

  // State
  const [searchText, setSearchText] = useState('');
  const [expertiseFilter, setExpertiseFilter] = useState<ExpertiseArea | undefined>();
  const [statusFilter, setStatusFilter] = useState<ExpertStatus | undefined>();
  const [languageFilter, setLanguageFilter] = useState<string | undefined>();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [metricsModalVisible, setMetricsModalVisible] = useState(false);
  const [selectedExpert, setSelectedExpert] = useState<ExpertProfile | null>(null);

  // Fetch experts
  const { data, isLoading, refetch } = useQuery({
    queryKey: [
      'ontology-experts',
      expertiseFilter,
      statusFilter,
      languageFilter,
      pagination.current,
      pagination.pageSize,
    ],
    queryFn: () =>
      ontologyExpertApi.listExperts({
        expertise_area: expertiseFilter,
        status: statusFilter,
        language: languageFilter,
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (expertId: string) => ontologyExpertApi.deleteExpert(expertId),
    onSuccess: () => {
      message.success(t('ontology:expert.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ontology-experts'] });
    },
    onError: (error: Error) => {
      message.error(`${t('ontology:expert.deleteFailed')}: ${error.message}`);
    },
  });

  // Filter experts by search text
  const filteredExperts = data?.experts.filter((expert) => {
    if (!searchText) return true;
    const search = searchText.toLowerCase();
    return (
      expert.name.toLowerCase().includes(search) ||
      expert.email.toLowerCase().includes(search) ||
      expert.department?.toLowerCase().includes(search) ||
      expert.title?.toLowerCase().includes(search)
    );
  }) || [];

  // Handle create
  const handleCreate = () => {
    setSelectedExpert(null);
    setFormModalVisible(true);
  };

  // Handle edit
  const handleEdit = (expert: ExpertProfile) => {
    setSelectedExpert(expert);
    setFormModalVisible(true);
  };

  // Handle view metrics
  const handleViewMetrics = (expert: ExpertProfile) => {
    setSelectedExpert(expert);
    setMetricsModalVisible(true);
  };

  // Handle delete
  const handleDelete = (expertId: string) => {
    deleteMutation.mutate(expertId);
  };

  // Handle form success
  const handleFormSuccess = () => {
    setFormModalVisible(false);
    setSelectedExpert(null);
  };

  // Reset filters
  const handleResetFilters = () => {
    setSearchText('');
    setExpertiseFilter(undefined);
    setStatusFilter(undefined);
    setLanguageFilter(undefined);
    setPagination({ current: 1, pageSize: 10 });
  };

  // Table columns
  const columns: ColumnsType<ExpertProfile> = [
    {
      title: t('ontology:expert.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} size="small" />
          <div>
            <Text strong>{name}</Text>
            {record.title && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {record.title}
                </Text>
              </div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: t('ontology:expert.email'),
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => <Text copyable>{email}</Text>,
    },
    {
      title: t('ontology:expert.expertiseAreas'),
      dataIndex: 'expertise_areas',
      key: 'expertise_areas',
      render: (areas: ExpertiseArea[]) => (
        <Space wrap>
          {areas.map((area) => (
            <Tag key={area} color={EXPERTISE_COLORS[area]}>
              {area}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('ontology:expert.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: ExpertStatus) => (
        <Badge
          status={STATUS_COLORS[status] as 'success' | 'default' | 'warning' | 'error'}
          text={status}
        />
      ),
    },
    {
      title: t('ontology:expert.availability'),
      dataIndex: 'availability',
      key: 'availability',
      render: (availability: AvailabilityLevel) => (
        <Tag color={AVAILABILITY_COLORS[availability]}>{availability}</Tag>
      ),
    },
    {
      title: t('ontology:expert.contributionScore'),
      dataIndex: 'contribution_score',
      key: 'contribution_score',
      render: (score: number) => (
        <Text>{score.toFixed(2)}</Text>
      ),
      sorter: (a, b) => a.contribution_score - b.contribution_score,
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('ontology:expert.viewMetrics')}>
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewMetrics(record)}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('ontology:expert.confirmDelete')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('common:delete')}>
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <UserOutlined />
            <span>{t('ontology:expert.listTitle')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('ontology:expert.addExpert')}
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder={t('ontology:expert.searchPlaceholder')}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Select
              placeholder={t('ontology:expert.filterByExpertise')}
              value={expertiseFilter}
              onChange={setExpertiseFilter}
              options={EXPERTISE_AREAS}
              allowClear
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Select
              placeholder={t('ontology:expert.filterByStatus')}
              value={statusFilter}
              onChange={setStatusFilter}
              options={STATUS_OPTIONS}
              allowClear
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Select
              placeholder={t('ontology:expert.filterByLanguage')}
              value={languageFilter}
              onChange={setLanguageFilter}
              options={LANGUAGE_OPTIONS}
              allowClear
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={12} md={3}>
            <Button icon={<FilterOutlined />} onClick={handleResetFilters}>
              {t('common:reset')}
            </Button>
          </Col>
        </Row>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={filteredExperts}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => t('common:totalItems', { count: total }),
            onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
          }}
          onRow={(record) => ({
            onClick: () => onSelectExpert?.(record),
            style: { cursor: onSelectExpert ? 'pointer' : 'default' },
          })}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={selectedExpert ? t('ontology:expert.editProfile') : t('ontology:expert.createProfile')}
        open={formModalVisible}
        onCancel={() => {
          setFormModalVisible(false);
          setSelectedExpert(null);
        }}
        footer={null}
        width={700}
        destroyOnClose
      >
        <ExpertProfileForm
          expert={selectedExpert}
          onSuccess={handleFormSuccess}
          onCancel={() => {
            setFormModalVisible(false);
            setSelectedExpert(null);
          }}
        />
      </Modal>

      {/* Metrics Modal */}
      <Modal
        title={t('ontology:expert.metricsTitle')}
        open={metricsModalVisible}
        onCancel={() => {
          setMetricsModalVisible(false);
          setSelectedExpert(null);
        }}
        footer={null}
        width={600}
        destroyOnClose
      >
        {selectedExpert && <ExpertMetrics expertId={selectedExpert.id} />}
      </Modal>
    </div>
  );
};

export default ExpertList;
