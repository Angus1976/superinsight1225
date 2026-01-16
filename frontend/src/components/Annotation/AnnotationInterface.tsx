// 完整的标注界面组件
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Button,
  Space,
  Radio,
  Input,
  Form,
  message,
  Spin,
  Typography,
  Divider,
  Tag,
  Row,
  Col,
  Tooltip,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { usePermissions } from '@/hooks/usePermissions';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface AnnotationData {
  id?: number;
  result: Array<{
    value: {
      choices?: string[];
      text?: string;
      rating?: number;
    };
    from_name: string;
    to_name: string;
    type: string;
  }>;
  task: number;
}

interface Task {
  id: number;
  data: {
    text: string;
    [key: string]: any;
  };
  annotations: AnnotationData[];
  is_labeled: boolean;
}

interface Project {
  id: number;
  title: string;
  description: string;
  label_config: string;
}

interface AnnotationInterfaceProps {
  project: Project;
  task: Task;
  onAnnotationSave: (annotation: AnnotationData) => void;
  onAnnotationUpdate: (annotation: AnnotationData) => void;
  loading?: boolean;
}

export const AnnotationInterface: React.FC<AnnotationInterfaceProps> = ({
  project,
  task,
  onAnnotationSave,
  onAnnotationUpdate,
  loading = false,
}) => {
  const { t } = useTranslation(['annotation', 'common']);
  const [form] = Form.useForm();
  const { annotation: annotationPerms, roleDisplayName } = usePermissions();
  const [currentAnnotation, setCurrentAnnotation] = useState<AnnotationData | null>(null);
  const [annotationHistory, setAnnotationHistory] = useState<AnnotationData[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [saving, setSaving] = useState(false);

  // 初始化标注数据
  useEffect(() => {
    if (task.annotations && task.annotations.length > 0) {
      const latestAnnotation = task.annotations[task.annotations.length - 1];
      setCurrentAnnotation(latestAnnotation);
      
      // 设置表单初始值
      if (latestAnnotation.result && latestAnnotation.result.length > 0) {
        const result = latestAnnotation.result[0];
        if (result.type === 'choices' && result.value.choices) {
          form.setFieldsValue({ sentiment: result.value.choices[0] });
        } else if (result.type === 'textarea' && result.value.text) {
          form.setFieldsValue({ comment: result.value.text });
        } else if (result.type === 'rating' && result.value.rating) {
          form.setFieldsValue({ rating: result.value.rating });
        }
      }
    }
  }, [task, form]);

  // 保存标注到历史记录
  const saveToHistory = (annotation: AnnotationData) => {
    const newHistory = annotationHistory.slice(0, historyIndex + 1);
    newHistory.push(annotation);
    setAnnotationHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  };

  // 撤销操作
  const handleUndo = () => {
    if (historyIndex > 0) {
      const prevAnnotation = annotationHistory[historyIndex - 1];
      setCurrentAnnotation(prevAnnotation);
      setHistoryIndex(historyIndex - 1);
      updateFormFromAnnotation(prevAnnotation);
    }
  };

  // 重做操作
  const handleRedo = () => {
    if (historyIndex < annotationHistory.length - 1) {
      const nextAnnotation = annotationHistory[historyIndex + 1];
      setCurrentAnnotation(nextAnnotation);
      setHistoryIndex(historyIndex + 1);
      updateFormFromAnnotation(nextAnnotation);
    }
  };

  // 从标注数据更新表单
  const updateFormFromAnnotation = (annotation: AnnotationData) => {
    if (annotation.result && annotation.result.length > 0) {
      const result = annotation.result[0];
      if (result.type === 'choices' && result.value.choices) {
        form.setFieldsValue({ sentiment: result.value.choices[0] });
      } else if (result.type === 'textarea' && result.value.text) {
        form.setFieldsValue({ comment: result.value.text });
      } else if (result.type === 'rating' && result.value.rating) {
        form.setFieldsValue({ rating: result.value.rating });
      }
    }
  };

  // 处理表单提交
  const handleSubmit = async (values: any) => {
    if (!annotationPerms.canCreate && !currentAnnotation?.id) {
      message.error(t('interface.messages.noCreatePermission'));
      return;
    }

    if (!annotationPerms.canEdit && currentAnnotation?.id) {
      message.error(t('interface.messages.noEditPermission'));
      return;
    }

    try {
      setSaving(true);

      // 构建标注结果
      const annotationResult: AnnotationData = {
        result: [],
        task: task.id,
      };

      // 情感分类标注
      if (values.sentiment) {
        annotationResult.result.push({
          value: {
            choices: [values.sentiment],
          },
          from_name: 'sentiment',
          to_name: 'text',
          type: 'choices',
        });
      }

      // 评论标注
      if (values.comment) {
        annotationResult.result.push({
          value: {
            text: values.comment,
          },
          from_name: 'comment',
          to_name: 'text',
          type: 'textarea',
        });
      }

      // 评分标注
      if (values.rating) {
        annotationResult.result.push({
          value: {
            rating: values.rating,
          },
          from_name: 'rating',
          to_name: 'text',
          type: 'rating',
        });
      }

      // 保存到历史记录
      saveToHistory(annotationResult);
      setCurrentAnnotation(annotationResult);

      // 调用保存回调
      if (currentAnnotation?.id) {
        onAnnotationUpdate(annotationResult);
      } else {
        onAnnotationSave(annotationResult);
      }

      message.success(t('interface.messages.saveSuccess'));
    } catch (error) {
      console.error('保存标注失败:', error);
      message.error(t('interface.messages.saveError'));
    } finally {
      setSaving(false);
    }
  };

  // 快速标注按钮
  const handleQuickAnnotation = (sentiment: string) => {
    if (!annotationPerms.canCreate && !currentAnnotation?.id) {
      message.error(t('interface.messages.noCreatePermission'));
      return;
    }

    if (!annotationPerms.canEdit && currentAnnotation?.id) {
      message.error(t('interface.messages.noEditPermission'));
      return;
    }

    form.setFieldsValue({ sentiment });
    form.submit();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>{t('interface.loading')}</p>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 标注工具栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                icon={<UndoOutlined />}
                disabled={historyIndex <= 0}
                onClick={handleUndo}
                title={t('interface.toolbar.undo')}
              />
              <Button
                icon={<RedoOutlined />}
                disabled={historyIndex >= annotationHistory.length - 1}
                onClick={handleRedo}
                title={t('interface.toolbar.redo')}
              />
              <Divider type="vertical" />
              <Text type="secondary">
                {t('interface.toolbar.history')}: {historyIndex + 1} / {annotationHistory.length}
              </Text>
            </Space>
          </Col>
          <Col>
            <Space>
              <Tag color={task.is_labeled ? 'green' : 'orange'}>
                {task.is_labeled ? t('interface.status.labeled') : t('interface.status.unlabeled')}
              </Tag>
              <Tag color="blue">
                {roleDisplayName}
              </Tag>
              {!annotationPerms.canCreate && !annotationPerms.canEdit && (
                <Tag color="red" icon={<LockOutlined />}>
                  {t('interface.status.readOnly')}
                </Tag>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 主要标注区域 */}
      <div style={{ flex: 1, display: 'flex', gap: '16px' }}>
        {/* 左侧：文本内容 */}
        <Card 
          title={t('interface.content.title')} 
          style={{ flex: 2, height: 'fit-content' }}
        >
          <div style={{
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '8px',
            border: '2px solid #e9ecef',
            minHeight: '200px',
          }}>
            <Paragraph style={{ 
              fontSize: '16px', 
              lineHeight: '1.6',
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}>
              {task.data.text}
            </Paragraph>
          </div>
        </Card>

        {/* 右侧：标注控制面板 */}
        <Card 
          title={t('interface.tools.title')} 
          style={{ flex: 1, height: 'fit-content' }}
          extra={
            annotationPerms.canCreate || annotationPerms.canEdit ? (
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={() => form.submit()}
              >
                {t('interface.tools.saveAnnotation')}
              </Button>
            ) : (
              <Tooltip title={t('interface.messages.noCreatePermission')}>
                <Button
                  type="primary"
                  icon={<LockOutlined />}
                  disabled
                >
                  {t('interface.tools.saveAnnotation')}
                </Button>
              </Tooltip>
            )
          }
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
          >
            {/* 情感分类 */}
            <Form.Item
              label={t('interface.sentiment.title')}
              name="sentiment"
              rules={[{ required: true, message: t('interface.sentiment.required') }]}
            >
              <Radio.Group style={{ width: '100%' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Radio value="Positive" style={{ width: '100%' }}>
                    <Space>
                      <CheckOutlined style={{ color: '#52c41a' }} />
                      {t('interface.sentiment.positiveLabel')}
                    </Space>
                  </Radio>
                  <Radio value="Negative" style={{ width: '100%' }}>
                    <Space>
                      <CloseOutlined style={{ color: '#ff4d4f' }} />
                      {t('interface.sentiment.negativeLabel')}
                    </Space>
                  </Radio>
                  <Radio value="Neutral" style={{ width: '100%' }}>
                    <Space>
                      {t('interface.sentiment.neutralLabel')}
                    </Space>
                  </Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            {/* 快速标注按钮 */}
            <div style={{ marginBottom: 24 }}>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                {t('interface.quickAnnotation.title')}:
              </Text>
              <Space wrap>
                <Button
                  type="primary"
                  ghost
                  icon={<CheckOutlined />}
                  onClick={() => handleQuickAnnotation('Positive')}
                  style={{ borderColor: '#52c41a', color: '#52c41a' }}
                  disabled={!annotationPerms.canCreate && !annotationPerms.canEdit}
                >
                  {t('interface.sentiment.positive')}
                </Button>
                <Button
                  type="primary"
                  ghost
                  icon={<CloseOutlined />}
                  onClick={() => handleQuickAnnotation('Negative')}
                  style={{ borderColor: '#ff4d4f', color: '#ff4d4f' }}
                  disabled={!annotationPerms.canCreate && !annotationPerms.canEdit}
                >
                  {t('interface.sentiment.negative')}
                </Button>
                <Button
                  type="default"
                  ghost
                  onClick={() => handleQuickAnnotation('Neutral')}
                  disabled={!annotationPerms.canCreate && !annotationPerms.canEdit}
                >
                  {t('interface.sentiment.neutral')}
                </Button>
              </Space>
            </div>

            {/* 评分 */}
            <Form.Item
              label={t('interface.rating.title')}
              name="rating"
            >
              <Radio.Group>
                <Space>
                  {[1, 2, 3, 4, 5].map(num => (
                    <Radio key={num} value={num}>
                      {num}
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </Form.Item>

            {/* 备注 */}
            <Form.Item
              label={t('interface.comment.title')}
              name="comment"
            >
              <TextArea
                rows={3}
                placeholder={t('interface.comment.placeholder')}
                maxLength={500}
                showCount
              />
            </Form.Item>
          </Form>

          {/* 标注历史 */}
          {currentAnnotation && (
            <div style={{ marginTop: 24 }}>
              <Divider />
              <Title level={5}>{t('interface.currentResult.title')}</Title>
              <div style={{ 
                background: '#f6ffed', 
                border: '1px solid #b7eb8f',
                borderRadius: '6px',
                padding: '12px',
              }}>
                {currentAnnotation.result.map((result, index) => (
                  <div key={index} style={{ marginBottom: 8 }}>
                    {result.type === 'choices' && result.value.choices && (
                      <Text>
                        <strong>{t('interface.currentResult.sentiment')}:</strong> 
                        <Tag color={
                          result.value.choices[0] === 'Positive' ? 'green' :
                          result.value.choices[0] === 'Negative' ? 'red' : 'default'
                        }>
                          {result.value.choices[0]}
                        </Tag>
                      </Text>
                    )}
                    {result.type === 'rating' && result.value.rating && (
                      <Text>
                        <strong>{t('interface.currentResult.rating')}:</strong> {result.value.rating}/5
                      </Text>
                    )}
                    {result.type === 'textarea' && result.value.text && (
                      <div>
                        <Text strong>{t('interface.currentResult.comment')}:</Text>
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary">{result.value.text}</Text>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default AnnotationInterface;