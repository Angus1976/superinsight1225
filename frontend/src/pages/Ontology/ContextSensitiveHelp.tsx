/**
 * ContextSensitiveHelp Component (上下文敏感帮助)
 * 
 * Help component with:
 * - Help icon on every screen
 * - Display relevant documentation
 * - Link to tutorials and best practices
 * - Search help content
 * 
 * Requirements: 15.4
 */

import React, { useState } from 'react';
import {
  Drawer,
  Input,
  List,
  Typography,
  Tag,
  Space,
  Button,
  Collapse,
  Empty,
  Divider,
  Card,
  Tooltip,
  FloatButton,
} from 'antd';
import {
  QuestionCircleOutlined,
  SearchOutlined,
  BookOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  RightOutlined,
  BulbOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Title, Paragraph, Link } = Typography;
const { Panel } = Collapse;

interface HelpArticle {
  id: string;
  title: string;
  category: string;
  content: string;
  keywords: string[];
  relatedArticles?: string[];
  videoUrl?: string;
}

interface HelpCategory {
  key: string;
  name: string;
  icon: React.ReactNode;
  articles: HelpArticle[];
}

interface ContextSensitiveHelpProps {
  contextKey?: string; // Current context for relevant help
  showFloatButton?: boolean;
}

// Help content database
const HELP_CATEGORIES: HelpCategory[] = [
  {
    key: 'gettingStarted',
    name: 'help.categories.gettingStarted',
    icon: <BulbOutlined />,
    articles: [
      {
        id: 'gs-1',
        title: 'help.articles.createExpert',
        category: 'gettingStarted',
        content: '创建专家档案是使用本体协作平台的第一步。您需要填写基本信息、选择专业领域、添加认证资质等。',
        keywords: ['专家', '档案', '创建', '入门'],
      },
      {
        id: 'gs-2',
        title: 'help.articles.useTemplate',
        category: 'gettingStarted',
        content: '本体模板提供了预定义的实体类型和关系类型，可以帮助您快速构建本体结构。',
        keywords: ['模板', '本体', '使用'],
      },
    ],
  },
  {
    key: 'expertManagement',
    name: 'help.categories.expertManagement',
    icon: <BookOutlined />,
    articles: [
      {
        id: 'em-1',
        title: 'help.articles.createExpert',
        category: 'expertManagement',
        content: '专家档案包含姓名、邮箱、专业领域、认证资质、语言偏好等信息。系统会根据这些信息进行专家推荐。',
        keywords: ['专家', '档案', '管理'],
      },
    ],
  },
  {
    key: 'collaboration',
    name: 'help.categories.collaboration',
    icon: <BookOutlined />,
    articles: [
      {
        id: 'co-1',
        title: 'help.articles.startCollaboration',
        category: 'collaboration',
        content: '协作编辑允许多位专家同时编辑本体。系统会自动检测冲突并提供解决方案。',
        keywords: ['协作', '编辑', '实时'],
      },
    ],
  },
  {
    key: 'approvalWorkflow',
    name: 'help.categories.approvalWorkflow',
    icon: <BookOutlined />,
    articles: [
      {
        id: 'aw-1',
        title: 'help.articles.submitApproval',
        category: 'approvalWorkflow',
        content: '变更请求需要经过审批流程。您可以创建审批链，设置多级审批人和截止时间。',
        keywords: ['审批', '流程', '变更'],
      },
    ],
  },
  {
    key: 'validation',
    name: 'help.categories.validation',
    icon: <BookOutlined />,
    articles: [
      {
        id: 'va-1',
        title: 'help.articles.createValidationRule',
        category: 'validation',
        content: '验证规则用于确保数据质量。您可以创建正则表达式规则或Python表达式规则。',
        keywords: ['验证', '规则', '数据质量'],
      },
    ],
  },
  {
    key: 'compliance',
    name: 'help.categories.compliance',
    icon: <BookOutlined />,
    articles: [
      {
        id: 'cp-1',
        title: 'help.articles.applyCompliance',
        category: 'compliance',
        content: '合规模板帮助您满足法规要求，如数据安全法、个人信息保护法等。',
        keywords: ['合规', '法规', '模板'],
      },
    ],
  },
];

const ContextSensitiveHelp: React.FC<ContextSensitiveHelpProps> = ({
  contextKey,
  showFloatButton = true,
}) => {
  const { t } = useTranslation('ontology');
  const [visible, setVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null);

  // Filter articles based on search and context
  const getFilteredArticles = () => {
    let allArticles: HelpArticle[] = [];
    
    HELP_CATEGORIES.forEach((category) => {
      allArticles = [...allArticles, ...category.articles];
    });

    if (!searchText) {
      // If context key provided, prioritize relevant articles
      if (contextKey) {
        const contextCategory = HELP_CATEGORIES.find((c) => c.key === contextKey);
        if (contextCategory) {
          return contextCategory.articles;
        }
      }
      return allArticles;
    }

    const search = searchText.toLowerCase();
    return allArticles.filter(
      (article) =>
        t(article.title).toLowerCase().includes(search) ||
        article.content.toLowerCase().includes(search) ||
        article.keywords.some((k) => k.toLowerCase().includes(search))
    );
  };

  const renderArticleList = (articles: HelpArticle[]) => {
    if (articles.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('help.noResults')}
        />
      );
    }

    return (
      <List
        dataSource={articles}
        renderItem={(article) => (
          <List.Item
            style={{ cursor: 'pointer' }}
            onClick={() => setSelectedArticle(article)}
          >
            <List.Item.Meta
              avatar={<FileTextOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
              title={t(article.title)}
              description={
                <Space wrap>
                  {article.keywords.slice(0, 3).map((keyword) => (
                    <Tag key={keyword} size="small">
                      {keyword}
                    </Tag>
                  ))}
                </Space>
              }
            />
            <RightOutlined />
          </List.Item>
        )}
      />
    );
  };

  const renderArticleDetail = () => {
    if (!selectedArticle) return null;

    return (
      <div>
        <Button
          type="link"
          onClick={() => setSelectedArticle(null)}
          style={{ padding: 0, marginBottom: 16 }}
        >
          ← {t('common.back')}
        </Button>

        <Title level={4}>{t(selectedArticle.title)}</Title>
        
        <Tag color="blue">{t(`help.categories.${selectedArticle.category}`)}</Tag>
        
        <Divider />
        
        <Paragraph>{selectedArticle.content}</Paragraph>

        {selectedArticle.videoUrl && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Space>
              <PlayCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
              <div>
                <Text strong>{t('help.tutorials')}</Text>
                <br />
                <Link href={selectedArticle.videoUrl} target="_blank">
                  {t('common.watchVideo')} <LinkOutlined />
                </Link>
              </div>
            </Space>
          </Card>
        )}

        {selectedArticle.relatedArticles && selectedArticle.relatedArticles.length > 0 && (
          <>
            <Divider />
            <Text type="secondary">{t('common.relatedArticles')}:</Text>
            <List
              size="small"
              dataSource={selectedArticle.relatedArticles}
              renderItem={(articleId) => {
                const related = HELP_CATEGORIES
                  .flatMap((c) => c.articles)
                  .find((a) => a.id === articleId);
                if (!related) return null;
                return (
                  <List.Item
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedArticle(related)}
                  >
                    <Space>
                      <FileTextOutlined />
                      {t(related.title)}
                    </Space>
                  </List.Item>
                );
              }}
            />
          </>
        )}
      </div>
    );
  };

  const renderContent = () => {
    if (selectedArticle) {
      return renderArticleDetail();
    }

    return (
      <div>
        {/* Search */}
        <Input
          placeholder={t('help.searchPlaceholder')}
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ marginBottom: 16 }}
        />

        {searchText ? (
          // Search results
          renderArticleList(getFilteredArticles())
        ) : (
          // Category view
          <Collapse defaultActiveKey={contextKey ? [contextKey] : ['gettingStarted']}>
            {HELP_CATEGORIES.map((category) => (
              <Panel
                header={
                  <Space>
                    {category.icon}
                    {t(category.name)}
                    <Tag>{category.articles.length}</Tag>
                  </Space>
                }
                key={category.key}
              >
                {renderArticleList(category.articles)}
              </Panel>
            ))}
          </Collapse>
        )}

        <Divider />

        {/* Quick Links */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button block icon={<BookOutlined />}>
            {t('help.documentation')}
          </Button>
          <Button block icon={<PlayCircleOutlined />}>
            {t('help.tutorials')}
          </Button>
          <Button block icon={<QuestionCircleOutlined />}>
            {t('help.faq')}
          </Button>
          <Button block icon={<CustomerServiceOutlined />} type="primary">
            {t('help.contactSupport')}
          </Button>
        </Space>
      </div>
    );
  };

  return (
    <>
      {/* Float Button */}
      {showFloatButton && (
        <FloatButton
          icon={<QuestionCircleOutlined />}
          type="primary"
          tooltip={t('help.contextHelp')}
          onClick={() => setVisible(true)}
        />
      )}

      {/* Help Drawer */}
      <Drawer
        title={
          <Space>
            <QuestionCircleOutlined />
            {t('help.title')}
          </Space>
        }
        placement="right"
        width={400}
        open={visible}
        onClose={() => {
          setVisible(false);
          setSelectedArticle(null);
          setSearchText('');
        }}
      >
        {renderContent()}
      </Drawer>
    </>
  );
};

export default ContextSensitiveHelp;
