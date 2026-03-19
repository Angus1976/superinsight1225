import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Card, Input, Tag, Empty, Space, Typography, Spin, Alert, Pagination } from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { WorkflowItem } from '@/types/aiAssistant';

const { Text } = Typography;

const STORAGE_KEY = 'ai_last_workflow_id';
const PAGE_SIZE = 4;

export interface WorkflowSelectorProps {
  workflows: WorkflowItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading?: boolean;
  userRole?: string;
}

/**
 * Smart sort: role-match first → preset → has skills → alphabetical.
 */
function smartSort(items: WorkflowItem[], userRole: string): WorkflowItem[] {
  return [...items].sort((a, b) => {
    const aRole = a.visible_roles?.includes(userRole) ? 1 : 0;
    const bRole = b.visible_roles?.includes(userRole) ? 1 : 0;
    if (aRole !== bRole) return bRole - aRole;

    const aPreset = a.is_preset ? 1 : 0;
    const bPreset = b.is_preset ? 1 : 0;
    if (aPreset !== bPreset) return bPreset - aPreset;

    const aSkills = a.skill_ids?.length ?? 0;
    const bSkills = b.skill_ids?.length ?? 0;
    if (aSkills !== bSkills) return bSkills - aSkills;

    return (a.name || '').localeCompare(b.name || '');
  });
}

const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({
  workflows,
  selectedId,
  onSelect,
  loading = false,
  userRole = 'viewer',
}) => {
  const { t } = useTranslation('workflow');
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Restore last selection from localStorage on mount
  useEffect(() => {
    const savedId = localStorage.getItem(STORAGE_KEY);
    if (!savedId) return;
    const found = workflows.find(w => w.id === savedId && w.status === 'enabled');
    if (found) {
      onSelect(savedId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [workflows]);

  const handleSelect = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id);
    onSelect(id);
  }, [onSelect]);

  // Fuzzy search filter
  const filterWorkflows = useCallback((items: WorkflowItem[], query: string): WorkflowItem[] => {
    if (!query.trim()) return items;
    const lower = query.toLowerCase();
    return items.filter(w =>
      (w.name?.toLowerCase().includes(lower)) ||
      (w.description?.toLowerCase().includes(lower)) ||
      (w.name_en?.toLowerCase().includes(lower)) ||
      (w.description_en?.toLowerCase().includes(lower))
    );
  }, []);

  // Smart sort + filter + paginate
  const sorted = useMemo(() => smartSort(workflows, userRole), [workflows, userRole]);
  const filtered = useMemo(() => filterWorkflows(sorted, searchText), [sorted, searchText]);
  const totalCount = filtered.length;
  const pageItems = useMemo(
    () => filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [filtered, currentPage],
  );

  // Reset page when search changes
  useEffect(() => { setCurrentPage(1); }, [searchText]);

  const showGuideTip = !selectedId && workflows.length > 0;

  if (loading) {
    return (
      <Card title={t('selector.title')} size="small">
        <div style={{ textAlign: 'center', padding: '24px 0' }}><Spin /></div>
      </Card>
    );
  }

  return (
    <Card title={t('selector.title')} size="small">
      {workflows.length === 0 ? (
        <Empty description={t('selector.noWorkflows')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <>
          <Input
            prefix={<SearchOutlined />}
            placeholder={t('selector.searchPlaceholder')}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            allowClear
            style={{ marginBottom: 12 }}
          />

          {showGuideTip && (
            <Alert message={t('selector.guideTip')} type="info" showIcon style={{ marginBottom: 12 }} />
          )}

          {filtered.length === 0 ? (
            <Empty description={t('selector.noResults')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <>
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                {pageItems.map(workflow => (
                  <WorkflowCard
                    key={workflow.id}
                    workflow={workflow}
                    selected={workflow.id === selectedId}
                    onSelect={handleSelect}
                    t={t}
                  />
                ))}
              </Space>
              {totalCount > PAGE_SIZE && (
                <div style={{ textAlign: 'center', marginTop: 12 }}>
                  <Pagination
                    current={currentPage}
                    pageSize={PAGE_SIZE}
                    total={totalCount}
                    onChange={setCurrentPage}
                    size="small"
                    simple
                  />
                </div>
              )}
            </>
          )}
        </>
      )}
    </Card>
  );
};

// Extracted card component for each workflow item
interface WorkflowCardProps {
  workflow: WorkflowItem;
  selected: boolean;
  onSelect: (id: string) => void;
  t: (key: string, options?: Record<string, unknown>) => string;
}

const WorkflowCard: React.FC<WorkflowCardProps> = ({ workflow, selected, onSelect, t }) => (
  <div
    onClick={() => onSelect(workflow.id)}
    style={{
      padding: '10px 12px',
      border: selected ? '2px solid #1890ff' : '1px solid #f0f0f0',
      borderRadius: 8,
      cursor: 'pointer',
      background: selected ? '#e6f7ff' : '#fafafa',
      transition: 'all 0.2s',
    }}
  >
    <Space size={6} wrap>
      <Text strong style={{ fontSize: 14 }}>{workflow.name}</Text>
      {workflow.is_preset && (
        <Tag color="blue" icon={<ThunderboltOutlined />}>{t('selector.preset')}</Tag>
      )}
      <Tag>{t('selector.skillCount', { count: workflow.skill_ids?.length ?? 0 })}</Tag>
    </Space>
    {workflow.description && (
      <div style={{ marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>{workflow.description}</Text>
      </div>
    )}
  </div>
);

export default WorkflowSelector;
