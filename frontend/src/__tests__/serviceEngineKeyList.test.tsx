/**
 * Unit Tests: Service Engine KeyList Extensions
 *
 * Tests for the service engine fields added to KeyList.tsx:
 * - allowed_request_types column display
 * - Create modal new fields (request types, skill whitelist, webhook config)
 * - Form submission with new fields
 * - i18n translation for new UI text
 *
 * Validates: Requirements 9.6, 9.7, 9.8
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';
import axios from 'axios';
import KeyList from '@/pages/DataSync/APIManagement/KeyList';

// Mock axios
vi.mock('axios');

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

const zhResources = {
  dataSync: {
    'apiManagement.createKey': '创建密钥',
    'apiManagement.createKeyTitle': '创建 API 密钥',
    'apiManagement.keyName': '密钥名称',
    'apiManagement.keyNamePlaceholder': '请输入密钥名称',
    'apiManagement.description': '管理外部 API 密钥...',
    'apiManagement.descriptionPlaceholder': '请输入密钥描述',
    'apiManagement.selectScopes': '选择访问范围',
    'apiManagement.scopeAnnotations': '标注结果',
    'apiManagement.scopeAugmentedData': '增强数据',
    'apiManagement.scopeQualityReports': '质量报告',
    'apiManagement.scopeExperiments': 'AI 试验结果',
    'apiManagement.allowedRequestTypes': '允许的请求类型',
    'apiManagement.selectRequestTypes': '选择允许的请求类型',
    'apiManagement.requestTypeQuery': '结构化数据查询',
    'apiManagement.requestTypeChat': '对话式分析',
    'apiManagement.requestTypeDecision': '辅助决策',
    'apiManagement.requestTypeSkill': '技能调用',
    'apiManagement.skillWhitelist': '技能白名单',
    'apiManagement.skillWhitelistPlaceholder': '输入技能 ID，按回车添加多个',
    'apiManagement.webhookConfig': 'Webhook 配置',
    'apiManagement.webhookUrl': 'Webhook 地址',
    'apiManagement.webhookUrlPlaceholder': 'https://example.com/webhook',
    'apiManagement.webhookSecret': 'Webhook 密钥',
    'apiManagement.webhookSecretPlaceholder': '输入 Webhook 签名密钥',
    'apiManagement.webhookEvents': '订阅事件',
    'apiManagement.webhookEventDataSync': '数据同步完成',
    'apiManagement.webhookEventExport': '数据导出完成',
    'apiManagement.webhookEventAlert': '告警通知',
    'apiManagement.comingSoon': '即将推出',
    'apiManagement.createSuccess': 'API 密钥创建成功',
    'apiManagement.createError': '创建 API 密钥失败',
    'apiManagement.rateLimit': '速率限制',
    'apiManagement.perMinute': '每分钟',
    'apiManagement.perDay': '每天',
    'apiManagement.totalCalls': '总调用次数',
    'apiManagement.lastUsed': '最后使用',
    'apiManagement.actions': '操作',
    'apiManagement.keyPrefix': '密钥前缀',
    'apiManagement.scopes': '访问范围',
    'apiManagement.expiresInDays': '过期天数',
    'apiManagement.expiresInDaysPlaceholder': '留空表示永不过期',
    'apiManagement.rateLimitPerMinute': '每分钟请求限制',
    'apiManagement.rateLimitPerDay': '每日请求限制',
    'status.active': '活跃',
    'status.inactive': '非活跃',
    'status.failed': '失败',
    'status.status': '状态',
    'syncTask.description': '描述',
    'dataSource.neverSynced': '从未同步',
  },
  common: {
    total: '共',
    items: '条',
    confirm: '确认',
    cancel: '取消',
    close: '关闭',
  },
};

const enResources = {
  dataSync: {
    'apiManagement.createKey': 'Create Key',
    'apiManagement.createKeyTitle': 'Create API Key',
    'apiManagement.keyName': 'Key Name',
    'apiManagement.keyNamePlaceholder': 'Enter key name',
    'apiManagement.description': 'Manage external API keys...',
    'apiManagement.descriptionPlaceholder': 'Enter key description',
    'apiManagement.selectScopes': 'Select access scopes',
    'apiManagement.scopeAnnotations': 'Annotation Results',
    'apiManagement.scopeAugmentedData': 'Augmented Data',
    'apiManagement.scopeQualityReports': 'Quality Reports',
    'apiManagement.scopeExperiments': 'AI Experiment Results',
    'apiManagement.allowedRequestTypes': 'Allowed Request Types',
    'apiManagement.selectRequestTypes': 'Select allowed request types',
    'apiManagement.requestTypeQuery': 'Structured Data Query',
    'apiManagement.requestTypeChat': 'Conversational Analysis',
    'apiManagement.requestTypeDecision': 'Decision Support',
    'apiManagement.requestTypeSkill': 'Skill Invocation',
    'apiManagement.skillWhitelist': 'Skill Whitelist',
    'apiManagement.skillWhitelistPlaceholder': 'Enter skill IDs, press Enter to add multiple',
    'apiManagement.webhookConfig': 'Webhook Configuration',
    'apiManagement.webhookUrl': 'Webhook URL',
    'apiManagement.webhookUrlPlaceholder': 'https://example.com/webhook',
    'apiManagement.webhookSecret': 'Webhook Secret',
    'apiManagement.webhookSecretPlaceholder': 'Enter webhook signing secret',
    'apiManagement.webhookEvents': 'Subscribed Events',
    'apiManagement.webhookEventDataSync': 'Data Sync Completed',
    'apiManagement.webhookEventExport': 'Data Export Completed',
    'apiManagement.webhookEventAlert': 'Alert Notification',
    'apiManagement.comingSoon': 'Coming Soon',
    'apiManagement.createSuccess': 'API key created successfully',
    'apiManagement.createError': 'Failed to create API key',
    'apiManagement.rateLimit': 'Rate Limit',
    'apiManagement.perMinute': 'per minute',
    'apiManagement.perDay': 'per day',
    'apiManagement.totalCalls': 'Total Calls',
    'apiManagement.lastUsed': 'Last Used',
    'apiManagement.actions': 'Actions',
    'apiManagement.keyPrefix': 'Key Prefix',
    'apiManagement.scopes': 'Access Scopes',
    'apiManagement.expiresInDays': 'Expires in days',
    'apiManagement.expiresInDaysPlaceholder': 'Leave empty for no expiration',
    'apiManagement.rateLimitPerMinute': 'Requests per minute',
    'apiManagement.rateLimitPerDay': 'Requests per day',
    'status.active': 'Active',
    'status.inactive': 'Inactive',
    'status.failed': 'Failed',
    'status.status': 'Status',
    'syncTask.description': 'Description',
    'dataSource.neverSynced': 'Never Synced',
  },
  common: {
    total: 'Total',
    items: 'items',
    confirm: 'Confirm',
    cancel: 'Cancel',
    close: 'Close',
  },
};

const mockKeys = [
  {
    id: '1',
    name: 'Test Key',
    key_prefix: 'sk_test',
    scopes: { annotations: true, augmented_data: false },
    status: 'active',
    rate_limit_per_minute: 60,
    rate_limit_per_day: 10000,
    created_at: '2026-01-01T00:00:00Z',
    total_calls: 100,
    allowed_request_types: ['query', 'chat'],
    skill_whitelist: ['skill-1'],
    webhook_config: null,
  },
];

const initI18n = (lng: string) => {
  return i18n.init({
    lng,
    fallbackLng: 'zh',
    ns: ['dataSync', 'common'],
    defaultNS: 'dataSync',
    resources: {
      zh: zhResources,
      en: enResources,
    },
    interpolation: { escapeValue: false },
  });
};

beforeEach(async () => {
  await initI18n('zh');
  vi.mocked(axios.get).mockResolvedValue({ data: mockKeys });
});

afterEach(() => {
  vi.clearAllMocks();
});

const renderKeyList = () => {
  return render(
    <I18nextProvider i18n={i18n}>
      <KeyList />
    </I18nextProvider>
  );
};

describe('KeyList - Service Engine Extensions', () => {
  describe('Request type column display (Req 9.7)', () => {
    it('should render allowed_request_types column with green tags', async () => {
      renderKeyList();

      await waitFor(() => {
        // Ant Design Table renders duplicate text nodes (th + measure cell)
        expect(screen.getAllByText('允许的请求类型').length).toBeGreaterThanOrEqual(1);
      });

      await waitFor(() => {
        expect(screen.getByText('结构化数据查询')).toBeInTheDocument();
        expect(screen.getByText('对话式分析')).toBeInTheDocument();
      });
    });

    it('should show "-" when allowed_request_types is empty', async () => {
      vi.mocked(axios.get).mockResolvedValue({
        data: [{ ...mockKeys[0], allowed_request_types: [] }],
      });

      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('-')).toBeInTheDocument();
      });
    });

    it('should show "-" when allowed_request_types is undefined', async () => {
      const keyWithoutTypes = { ...mockKeys[0] };
      delete (keyWithoutTypes as any).allowed_request_types;
      vi.mocked(axios.get).mockResolvedValue({ data: [keyWithoutTypes] });

      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('-')).toBeInTheDocument();
      });
    });
  });

  describe('Create modal new fields', () => {
    it('should show request type checkboxes in create modal', async () => {
      const user = userEvent.setup();
      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
      });

      await user.click(screen.getByText('创建密钥'));

      await waitFor(() => {
        expect(screen.getByText('选择允许的请求类型')).toBeInTheDocument();
        // Table already shows tags for query/chat; modal adds checkbox labels
        // Use getAllByText to handle duplicates from table + modal
        expect(screen.getAllByText('结构化数据查询').length).toBeGreaterThanOrEqual(2);
        expect(screen.getAllByText('对话式分析').length).toBeGreaterThanOrEqual(2);
        expect(screen.getByText('辅助决策')).toBeInTheDocument();
        expect(screen.getByText('技能调用')).toBeInTheDocument();
      });
    });

    it('should show skill whitelist input in create modal', async () => {
      const user = userEvent.setup();
      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
      });

      await user.click(screen.getByText('创建密钥'));

      await waitFor(() => {
        expect(screen.getByText('技能白名单')).toBeInTheDocument();
      });
    });

    it('should show webhook config section with Coming Soon badge', async () => {
      const user = userEvent.setup();
      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
      });

      await user.click(screen.getByText('创建密钥'));

      await waitFor(() => {
        expect(screen.getByText('Webhook 配置')).toBeInTheDocument();
        expect(screen.getByText('即将推出')).toBeInTheDocument();
      });
    });

    it('should have disabled webhook fields', async () => {
      const user = userEvent.setup();
      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
      });

      await user.click(screen.getByText('创建密钥'));

      await waitFor(() => {
        const webhookUrlInput = screen.getByPlaceholderText('https://example.com/webhook');
        expect(webhookUrlInput).toBeDisabled();
      });
    });
  });

  describe('Form submission includes new fields (Req 9.7)', () => {
    it('should send allowed_request_types and skill_whitelist in API payload', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: { ...mockKeys[0], raw_key: 'sk_test_full_key' },
      });
      const user = userEvent.setup();
      renderKeyList();

      await waitFor(() => {
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
      });

      await user.click(screen.getByText('创建密钥'));

      await waitFor(() => {
        expect(screen.getByText('创建 API 密钥')).toBeInTheDocument();
      });

      // Fill required fields
      const nameInput = screen.getByPlaceholderText('请输入密钥名称');
      await user.type(nameInput, 'My Test Key');

      // Select a scope (required)
      const annotationsCheckbox = screen.getByLabelText('标注结果');
      await user.click(annotationsCheckbox);

      // Select request types
      const queryCheckbox = screen.getByLabelText('结构化数据查询');
      await user.click(queryCheckbox);

      // Enter skill whitelist
      const skillInput = screen.getByPlaceholderText('输入技能 ID，按回车添加多个');
      await user.type(skillInput, 'skill-a, skill-b');

      // Submit the form via OK button
      const okButton = screen.getByRole('button', { name: /ok|确认|确定/i });
      await user.click(okButton);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          '/api/v1/sync/api-keys/',
          expect.objectContaining({
            name: 'My Test Key',
            allowed_request_types: ['query'],
            skill_whitelist: ['skill-a', 'skill-b'],
            webhook_config: null,
          })
        );
      });
    });
  });

  describe('i18n translation (Req 9.6)', () => {
    it('should render Chinese text with zh locale', async () => {
      renderKeyList();

      await waitFor(() => {
        expect(screen.getAllByText('允许的请求类型').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('创建密钥')).toBeInTheDocument();
        expect(screen.getAllByText('密钥名称').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('should render English text with en locale', async () => {
      await i18n.changeLanguage('en');

      renderKeyList();

      await waitFor(() => {
        expect(screen.getAllByText('Allowed Request Types').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('Create Key')).toBeInTheDocument();
        expect(screen.getAllByText('Key Name').length).toBeGreaterThanOrEqual(1);
      });
    });
  });
});
