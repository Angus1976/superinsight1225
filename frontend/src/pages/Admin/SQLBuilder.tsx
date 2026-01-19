/**
 * Admin SQL Builder Page
 * 
 * Provides visual SQL query builder with table/column selection,
 * condition configuration, SQL preview, and execution.
 * 
 * **Requirement 5.1, 5.2, 5.3, 5.4, 5.6: SQL Builder**
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Space,
  Table,
  Input,
  Form,
  Tag,
  Tooltip,
  message,
  Alert,
  Typography,
  Divider,
  Collapse,
  List,
  Empty,
  Spin,
  Modal,
  InputNumber,
} from 'antd';
import {
  PlayCircleOutlined,
  CopyOutlined,
  SaveOutlined,
  DeleteOutlined,
  PlusOutlined,
  DatabaseOutlined,
  TableOutlined,
  CodeOutlined,
  ReloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import {
  adminApi,
  DBConfigResponse,
  DatabaseSchema,
  QueryConfig,
  QueryResult,
  WhereCondition,
  OrderByClause,
  QueryTemplateResponse,
} from '@/services/adminApi';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;

const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'NOT IN', 'IS NULL', 'IS NOT NULL'];
const LOGIC_OPERATORS = ['AND', 'OR'];
const SORT_DIRECTIONS = ['ASC', 'DESC'];

const SQLBuilder: React.FC = () => {
  const { t } = useTranslation('admin');
  const { user } = useAuthStore();
  const [selectedDbId, setSelectedDbId] = useState<string | null>(null);
  const [queryConfig, setQueryConfig] = useState<QueryConfig>({
    tables: [],
    columns: ['*'],
    where_conditions: [],
    order_by: [],
    group_by: [],
    limit: 100,
  });
  const [generatedSQL, setGeneratedSQL] = useState<string>('');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateDesc, setTemplateDesc] = useState('');

  // Fetch DB configs
  const { data: dbConfigs = [] } = useQuery({
    queryKey: ['admin-db-configs'],
    queryFn: () => adminApi.listDBConfigs(),
  });

  // Fetch schema for selected DB
  const { data: schema, isLoading: schemaLoading, refetch: refetchSchema } = useQuery({
    queryKey: ['admin-db-schema', selectedDbId],
    queryFn: () => selectedDbId ? adminApi.getDBSchema(selectedDbId) : Promise.resolve({ tables: [], views: [] }),
    enabled: !!selectedDbId,
  });

  // Fetch templates
  const { data: templates = [], refetch: refetchTemplates } = useQuery({
    queryKey: ['admin-query-templates', selectedDbId],
    queryFn: () => adminApi.listQueryTemplates(selectedDbId || undefined),
  });

  // Build SQL mutation
  const buildMutation = useMutation({
    mutationFn: () => adminApi.buildSQL(queryConfig),
    onSuccess: (result) => {
      setGeneratedSQL(result.sql);
      if (!result.validation.is_valid) {
        message.warning(t('sqlBuilder.validationWarning'));
      }
    },
    onError: (error: Error) => {
      message.error(`${t('sqlBuilder.buildFailed')}: ${error.message}`);
    },
  });

  // Execute SQL mutation
  const executeMutation = useMutation({
    mutationFn: () => {
      if (!selectedDbId || !generatedSQL) {
        throw new Error(t('sqlBuilder.selectDbFirst'));
      }
      return adminApi.executeSQL({
        db_config_id: selectedDbId,
        sql: generatedSQL,
        limit: queryConfig.limit || 100,
      });
    },
    onSuccess: (result) => {
      setQueryResult(result);
      message.success(t('sqlBuilder.querySuccess', { count: result.row_count }));
    },
    onError: (error: Error) => {
      message.error(`${t('sqlBuilder.executeFailed')}: ${error.message}`);
    },
  });

  // Save template mutation
  const saveTemplateMutation = useMutation({
    mutationFn: () => {
      if (!selectedDbId) throw new Error(t('sqlBuilder.selectDbForTemplate'));
      return adminApi.createQueryTemplate(
        {
          name: templateName,
          description: templateDesc,
          query_config: queryConfig,
          db_config_id: selectedDbId,
        },
        user?.id || ''
      );
    },
    onSuccess: () => {
      message.success(t('sqlBuilder.templateSaved'));
      setSaveModalVisible(false);
      setTemplateName('');
      setTemplateDesc('');
      refetchTemplates();
    },
    onError: (error: Error) => {
      message.error(`${t('sqlBuilder.saveFailed')}: ${error.message}`);
    },
  });

  // Auto-build SQL when config changes
  useEffect(() => {
    if (queryConfig.tables.length > 0) {
      buildMutation.mutate();
    } else {
      setGeneratedSQL('');
    }
  }, [queryConfig]);

  const handleDbChange = (dbId: string) => {
    setSelectedDbId(dbId);
    setQueryConfig({
      tables: [],
      columns: ['*'],
      where_conditions: [],
      order_by: [],
      group_by: [],
      limit: 100,
    });
    setGeneratedSQL('');
    setQueryResult(null);
  };

  const handleTableSelect = (tables: string[]) => {
    setQueryConfig(prev => ({ ...prev, tables, columns: ['*'] }));
  };

  const handleColumnSelect = (columns: string[]) => {
    setQueryConfig(prev => ({ ...prev, columns: columns.length > 0 ? columns : ['*'] }));
  };

  const addWhereCondition = () => {
    setQueryConfig(prev => ({
      ...prev,
      where_conditions: [
        ...prev.where_conditions,
        { field: '', operator: '=', value: '', logic: 'AND' },
      ],
    }));
  };

  const updateWhereCondition = (index: number, field: keyof WhereCondition, value: unknown) => {
    setQueryConfig(prev => ({
      ...prev,
      where_conditions: prev.where_conditions.map((cond, i) =>
        i === index ? { ...cond, [field]: value } : cond
      ),
    }));
  };

  const removeWhereCondition = (index: number) => {
    setQueryConfig(prev => ({
      ...prev,
      where_conditions: prev.where_conditions.filter((_, i) => i !== index),
    }));
  };

  const addOrderBy = () => {
    setQueryConfig(prev => ({
      ...prev,
      order_by: [...prev.order_by, { field: '', direction: 'ASC' }],
    }));
  };

  const updateOrderBy = (index: number, field: keyof OrderByClause, value: string) => {
    setQueryConfig(prev => ({
      ...prev,
      order_by: prev.order_by.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  const removeOrderBy = (index: number) => {
    setQueryConfig(prev => ({
      ...prev,
      order_by: prev.order_by.filter((_, i) => i !== index),
    }));
  };

  const loadTemplate = (template: QueryTemplateResponse) => {
    setQueryConfig(template.query_config);
    setGeneratedSQL(template.sql);
    message.success(t('sqlBuilder.templateLoaded', { name: template.name }));
  };

  const copySQL = () => {
    navigator.clipboard.writeText(generatedSQL);
    message.success(t('sqlBuilder.sqlCopied'));
  };

  // Get all columns from selected tables
  const availableColumns = schema?.tables
    .filter(t => queryConfig.tables.includes(t.name))
    .flatMap(t => t.columns?.map((c: Record<string, unknown>) => `${t.name}.${c.name}`) || []) || [];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <CodeOutlined />
            <span>{t('sqlBuilder.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Select
              placeholder={t('sqlBuilder.selectDatabase')}
              style={{ width: 200 }}
              value={selectedDbId}
              onChange={handleDbChange}
            >
              {dbConfigs.map((config: DBConfigResponse) => (
                <Option key={config.id} value={config.id}>
                  {config.name}
                </Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetchSchema()} disabled={!selectedDbId}>
              {t('common.refresh')}
            </Button>
          </Space>
        }
      >
        {!selectedDbId ? (
          <Alert
            message={t('sqlBuilder.selectDbFirst')}
            description={t('sqlBuilder.selectDbDescription')}
            type="info"
            showIcon
          />
        ) : (
          <Row gutter={16}>
            {/* Left Panel - Schema Browser */}
            <Col xs={24} lg={6}>
              <Card size="small" title={t('sqlBuilder.databaseStructure')} loading={schemaLoading}>
                {schema?.tables.length === 0 ? (
                  <Empty description={t('sqlBuilder.noTables')} />
                ) : (
                  <Collapse accordion>
                    {schema?.tables.map((table) => (
                      <Panel
                        header={
                          <Space>
                            <TableOutlined />
                            <Text>{table.name}</Text>
                            {table.row_count !== undefined && (
                              <Tag>{t('sqlBuilder.rows', { count: table.row_count })}</Tag>
                            )}
                          </Space>
                        }
                        key={table.name}
                      >
                        <List
                          size="small"
                          dataSource={table.columns || []}
                          renderItem={(col: Record<string, unknown>) => (
                            <List.Item>
                              <Text code>{col.name as string}</Text>
                              <Tag>{col.type as string}</Tag>
                            </List.Item>
                          )}
                        />
                      </Panel>
                    ))}
                  </Collapse>
                )}
              </Card>

              {/* Templates */}
              <Card size="small" title={t('sqlBuilder.queryTemplates')} style={{ marginTop: 16 }}>
                {templates.length === 0 ? (
                  <Empty description={t('sqlBuilder.noTemplates')} />
                ) : (
                  <List
                    size="small"
                    dataSource={templates}
                    renderItem={(template: QueryTemplateResponse) => (
                      <List.Item
                        actions={[
                          <Button
                            type="link"
                            size="small"
                            onClick={() => loadTemplate(template)}
                          >
                            {t('sqlBuilder.loadTemplate')}
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          avatar={<FileTextOutlined />}
                          title={template.name}
                          description={template.description}
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </Col>

            {/* Middle Panel - Query Builder */}
            <Col xs={24} lg={10}>
              <Card size="small" title={t('sqlBuilder.queryConfiguration')}>
                <Form layout="vertical">
                  <Form.Item label={t('sqlBuilder.selectTables')}>
                    <Select
                      mode="multiple"
                      placeholder={t('sqlBuilder.selectTablesPlaceholder')}
                      value={queryConfig.tables}
                      onChange={handleTableSelect}
                      style={{ width: '100%' }}
                    >
                      {schema?.tables.map((table) => (
                        <Option key={table.name} value={table.name}>
                          {table.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item label={t('sqlBuilder.selectColumns')}>
                    <Select
                      mode="multiple"
                      placeholder={t('sqlBuilder.selectColumnsPlaceholder')}
                      value={queryConfig.columns.includes('*') ? [] : queryConfig.columns}
                      onChange={handleColumnSelect}
                      style={{ width: '100%' }}
                      disabled={queryConfig.tables.length === 0}
                    >
                      {availableColumns.map((col) => (
                        <Option key={col} value={col}>
                          {col}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Divider>{t('sqlBuilder.whereConditions')}</Divider>
                  {queryConfig.where_conditions.map((cond, index) => (
                    <Space key={index} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      {index > 0 && (
                        <Select
                          value={cond.logic}
                          onChange={(v) => updateWhereCondition(index, 'logic', v)}
                          style={{ width: 80 }}
                        >
                          {LOGIC_OPERATORS.map(op => (
                            <Option key={op} value={op}>{op}</Option>
                          ))}
                        </Select>
                      )}
                      <Select
                        placeholder={t('sqlBuilder.field')}
                        value={cond.field}
                        onChange={(v) => updateWhereCondition(index, 'field', v)}
                        style={{ width: 150 }}
                      >
                        {availableColumns.map((col) => (
                          <Option key={col} value={col}>{col}</Option>
                        ))}
                      </Select>
                      <Select
                        value={cond.operator}
                        onChange={(v) => updateWhereCondition(index, 'operator', v)}
                        style={{ width: 100 }}
                      >
                        {OPERATORS.map(op => (
                          <Option key={op} value={op}>{op}</Option>
                        ))}
                      </Select>
                      <Input
                        placeholder={t('sqlBuilder.value')}
                        value={cond.value as string}
                        onChange={(e) => updateWhereCondition(index, 'value', e.target.value)}
                        style={{ width: 150 }}
                      />
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeWhereCondition(index)}
                      />
                    </Space>
                  ))}
                  <Button type="dashed" onClick={addWhereCondition} icon={<PlusOutlined />}>
                    {t('sqlBuilder.addCondition')}
                  </Button>

                  <Divider>{t('sqlBuilder.orderBy')}</Divider>
                  {queryConfig.order_by.map((item, index) => (
                    <Space key={index} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Select
                        placeholder={t('sqlBuilder.field')}
                        value={item.field}
                        onChange={(v) => updateOrderBy(index, 'field', v)}
                        style={{ width: 200 }}
                      >
                        {availableColumns.map((col) => (
                          <Option key={col} value={col}>{col}</Option>
                        ))}
                      </Select>
                      <Select
                        value={item.direction}
                        onChange={(v) => updateOrderBy(index, 'direction', v)}
                        style={{ width: 100 }}
                      >
                        {SORT_DIRECTIONS.map(dir => (
                          <Option key={dir} value={dir}>{dir}</Option>
                        ))}
                      </Select>
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeOrderBy(index)}
                      />
                    </Space>
                  ))}
                  <Button type="dashed" onClick={addOrderBy} icon={<PlusOutlined />}>
                    {t('sqlBuilder.addOrderBy')}
                  </Button>

                  <Divider>{t('sqlBuilder.limit')}</Divider>
                  <Form.Item label={t('sqlBuilder.limitRows')}>
                    <InputNumber
                      min={1}
                      max={1000}
                      value={queryConfig.limit}
                      onChange={(v) => setQueryConfig(prev => ({ ...prev, limit: v || 100 }))}
                      style={{ width: 150 }}
                    />
                  </Form.Item>
                </Form>
              </Card>
            </Col>

            {/* Right Panel - SQL Preview & Results */}
            <Col xs={24} lg={8}>
              <Card
                size="small"
                title={t('sqlBuilder.generatedSQL')}
                extra={
                  <Space>
                    <Tooltip title={t('sqlBuilder.copySQL')}>
                      <Button
                        type="text"
                        icon={<CopyOutlined />}
                        onClick={copySQL}
                        disabled={!generatedSQL}
                      />
                    </Tooltip>
                    <Tooltip title={t('sqlBuilder.saveAsTemplate')}>
                      <Button
                        type="text"
                        icon={<SaveOutlined />}
                        onClick={() => setSaveModalVisible(true)}
                        disabled={!generatedSQL}
                      />
                    </Tooltip>
                  </Space>
                }
              >
                <TextArea
                  value={generatedSQL}
                  readOnly
                  rows={8}
                  style={{ fontFamily: 'monospace' }}
                  placeholder={t('sqlBuilder.sqlPlaceholder')}
                />
                <div style={{ marginTop: 16, textAlign: 'center' }}>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => executeMutation.mutate()}
                    loading={executeMutation.isPending}
                    disabled={!generatedSQL}
                  >
                    {t('sqlBuilder.executeQuery')}
                  </Button>
                </div>
              </Card>

              {/* Query Results */}
              {queryResult && (
                <Card
                  size="small"
                  title={t('sqlBuilder.queryResultTitle', { count: queryResult.row_count, time: queryResult.execution_time_ms })}
                  style={{ marginTop: 16 }}
                >
                  {queryResult.truncated && (
                    <Alert
                      message={t('sqlBuilder.resultTruncated')}
                      type="warning"
                      showIcon
                      style={{ marginBottom: 8 }}
                    />
                  )}
                  <Table
                    columns={queryResult.columns.map(col => ({
                      title: col,
                      dataIndex: col,
                      key: col,
                      ellipsis: true,
                    }))}
                    dataSource={queryResult.rows.map((row, i) => {
                      const obj: Record<string, unknown> = { key: i };
                      queryResult.columns.forEach((col, j) => {
                        obj[col] = row[j];
                      });
                      return obj;
                    })}
                    size="small"
                    scroll={{ x: true, y: 300 }}
                    pagination={{ pageSize: 10 }}
                  />
                </Card>
              )}
            </Col>
          </Row>
        )}
      </Card>

      {/* Save Template Modal */}
      <Modal
        title={t('sqlBuilder.saveTemplate')}
        open={saveModalVisible}
        onOk={() => saveTemplateMutation.mutate()}
        onCancel={() => setSaveModalVisible(false)}
        confirmLoading={saveTemplateMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label={t('sqlBuilder.templateNameRequired')} required>
            <Input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder={t('sqlBuilder.templateNamePlaceholder')}
            />
          </Form.Item>
          <Form.Item label={t('sqlBuilder.description')}>
            <TextArea
              value={templateDesc}
              onChange={(e) => setTemplateDesc(e.target.value)}
              placeholder={t('sqlBuilder.descriptionPlaceholder')}
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SQLBuilder;
