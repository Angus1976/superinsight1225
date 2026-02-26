/**
 * DesensitizationAudit — 审计日志表格、时间/操作人筛选
 *
 * Standalone audit log viewer for desensitization operations.
 * Validates: Requirements 6.1, 6.2
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, DatePicker, Input, Button, Space, Tag } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { getAuditLogs } from '@/services/aiAnnotationApi';
import type { AuditLogEntry, AuditFilter } from '@/services/aiAnnotationApi';
import { filterAuditLogs } from '@/utils/annotationHelpers';

const { RangePicker } = DatePicker;

const DesensitizationAudit: React.FC = () => {
  const { t } = useTranslation(['ai_annotation']);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<AuditFilter>({});

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAuditLogs(filter);
      setLogs(data);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const filteredLogs = filterAuditLogs(logs, filter);

  const handleDateChange = useCallback(
    (_: unknown, dateStrings: [string, string]) => {
      const hasRange = dateStrings[0] && dateStrings[1];
      setFilter((prev) => ({
        ...prev,
        dateRange: hasRange ? dateStrings : undefined,
      }));
    },
    [],
  );

  const handleOperatorChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value.trim();
      setFilter((prev) => ({
        ...prev,
        operator: val || undefined,
      }));
    },
    [],
  );

  const columns: ColumnsType<AuditLogEntry> = [
    {
      title: t('audit.operator'),
      dataIndex: 'operator',
      key: 'operator',
      width: 120,
    },
    {
      title: t('audit.timestamp'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      sorter: (a, b) => a.timestamp.localeCompare(b.timestamp),
    },
    {
      title: t('audit.rules_count'),
      key: 'rulesCount',
      width: 100,
      render: (_, record) => (
        <Tag color="blue">{record.rules.length}</Tag>
      ),
    },
    {
      title: t('audit.affected_count'),
      dataIndex: 'affectedCount',
      key: 'affectedCount',
      width: 120,
    },
    {
      title: t('audit.task_id'),
      dataIndex: 'taskId',
      key: 'taskId',
      width: 160,
      ellipsis: true,
    },
  ];

  return (
    <Card
      title={t('audit.title')}
      size="small"
      extra={
        <Button
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={fetchLogs}
        >
          {t('audit.refresh')}
        </Button>
      }
    >
      <Space style={{ marginBottom: 16 }} wrap>
        <RangePicker onChange={handleDateChange} />
        <Input
          prefix={<SearchOutlined />}
          placeholder={t('audit.operator_placeholder')}
          allowClear
          onChange={handleOperatorChange}
          style={{ width: 200 }}
        />
      </Space>

      <Table<AuditLogEntry>
        dataSource={filteredLogs}
        columns={columns}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
};

export default DesensitizationAudit;
