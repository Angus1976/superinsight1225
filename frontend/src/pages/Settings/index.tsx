// Settings page
import { useState } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Switch,
  Select,
  message,
  Divider,
  Row,
  Col,
  Avatar,
  Upload,
  Space,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  BellOutlined,
  GlobalOutlined,
  UploadOutlined,
  SaveOutlined,
  SkinOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useUIStore, type ClientCompany } from '@/stores/uiStore';
import { isValidLogoUrl } from '@/components/Layout/ClientBranding';

const { TabPane } = Tabs;
const { Option } = Select;

const SettingsPage: React.FC = () => {
  const { t, i18n } = useTranslation('settings');
  const { user } = useAuthStore();
  const { theme, setTheme, clientCompany, setClientCompany } = useUIStore();
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [brandingForm] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleProfileSubmit = async (values: Record<string, string>) => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      message.success(t('profile.updateSuccess'));
      console.log('Profile values:', values);
    } catch {
      message.error(t('profile.updateFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (values: Record<string, string>) => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      message.success(t('security.changeSuccess'));
      passwordForm.resetFields();
      console.log('Password values:', values);
    } catch {
      message.error(t('security.changeFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
    const languageName = lang === 'zh' ? t('appearance.language.chinese') : t('appearance.language.english');
    message.success(t('appearance.language.changeSuccess', { language: languageName }));
  };

  const handleThemeChange = (isDark: boolean) => {
    setTheme(isDark ? 'dark' : 'light');
    const themeName = isDark ? t('appearance.darkMode.dark') : t('appearance.darkMode.light');
    message.success(t('appearance.darkMode.changeSuccess', { theme: themeName }));
  };

  const handleBrandingSave = (values: { name: string; nameEn: string; logo: string; label: string }) => {
    const company: ClientCompany = {
      name: values.name.trim(),
      nameEn: values.nameEn.trim(),
    };
    if (values.logo?.trim()) company.logo = values.logo.trim();
    if (values.label?.trim()) company.label = values.label.trim();
    setClientCompany(company);
    message.success(t('branding.saveSuccess'));
  };

  const handleBrandingReset = () => {
    setClientCompany(null);
    brandingForm.resetFields();
    message.success(t('branding.resetSuccess'));
  };

  // Preview for branding form
  const BrandingPreview: React.FC = () => {
    const name = Form.useWatch('name', brandingForm) || t('common:appName', '问视间');
    const logo = Form.useWatch('logo', brandingForm) || '';
    const label = Form.useWatch('label', brandingForm) || '';
    
    // Use default logo if no custom logo is provided
    const defaultLogo = '/logos/logo-icon-64.svg';
    const displayLogo = logo || defaultLogo;
    const showLogo = isValidLogoUrl(displayLogo);

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0' }}>
        {showLogo ? (
          <img
            src={displayLogo}
            alt={name}
            style={{ width: 32, height: 32, borderRadius: 6, objectFit: 'contain' }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <Avatar size={32} style={{ background: 'linear-gradient(135deg, #1890ff, #722ed1)', flexShrink: 0 }}>
            {name.charAt(0)}
          </Avatar>
        )}
        <span style={{ fontWeight: 600 }}>{name}</span>
        {label && <span style={{ color: '#1890ff', fontSize: 12 }}>{label}</span>}
      </div>
    );
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>{t('title')}</h2>

      <Card>
        <Tabs defaultActiveKey="profile" tabPosition="left">
          {/* Profile Tab */}
          <TabPane
            tab={
              <span>
                <UserOutlined />
                {t('profile.tab')}
              </span>
            }
            key="profile"
          >
            <h3>{t('profile.title')}</h3>
            <Divider />

            <Row gutter={24}>
              <Col xs={24} md={8} style={{ textAlign: 'center', marginBottom: 24 }}>
                <Avatar size={120} icon={<UserOutlined />} />
                <div style={{ marginTop: 16 }}>
                  <Upload showUploadList={false}>
                    <Button icon={<UploadOutlined />}>{t('profile.changeAvatar')}</Button>
                  </Upload>
                </div>
              </Col>

              <Col xs={24} md={16}>
                <Form
                  form={profileForm}
                  layout="vertical"
                  initialValues={{
                    username: user?.username || '',
                    email: user?.email || '',
                    display_name: user?.username || '',
                  }}
                  onFinish={handleProfileSubmit}
                >
                  <Form.Item
                    name="username"
                    label={t('profile.username')}
                    rules={[{ required: true, message: t('profile.usernameRequired') }]}
                  >
                    <Input disabled placeholder={t('profile.usernamePlaceholder')} />
                  </Form.Item>

                  <Form.Item
                    name="email"
                    label={t('profile.email')}
                    rules={[
                      { required: true, message: t('profile.emailRequired') },
                      { type: 'email', message: t('profile.emailInvalid') },
                    ]}
                  >
                    <Input placeholder={t('profile.emailPlaceholder')} />
                  </Form.Item>

                  <Form.Item name="display_name" label={t('profile.displayName')}>
                    <Input placeholder={t('profile.displayNamePlaceholder')} />
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      icon={<SaveOutlined />}
                    >
                      {t('profile.saveChanges')}
                    </Button>
                  </Form.Item>
                </Form>
              </Col>
            </Row>
          </TabPane>

          {/* Security Tab */}
          <TabPane
            tab={
              <span>
                <LockOutlined />
                {t('security.tab')}
              </span>
            }
            key="security"
          >
            <h3>{t('security.title')}</h3>
            <Divider />

            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handlePasswordSubmit}
              style={{ maxWidth: 400 }}
            >
              <Form.Item
                name="current_password"
                label={t('security.currentPassword')}
                rules={[{ required: true, message: t('security.currentPasswordRequired') }]}
              >
                <Input.Password placeholder={t('security.currentPasswordPlaceholder')} />
              </Form.Item>

              <Form.Item
                name="new_password"
                label={t('security.newPassword')}
                rules={[
                  { required: true, message: t('security.newPasswordRequired') },
                  { min: 8, message: t('security.newPasswordLength') },
                ]}
              >
                <Input.Password placeholder={t('security.newPasswordPlaceholder')} />
              </Form.Item>

              <Form.Item
                name="confirm_password"
                label={t('security.confirmPassword')}
                dependencies={['new_password']}
                rules={[
                  { required: true, message: t('security.confirmPasswordRequired') },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error(t('security.passwordMismatch')));
                    },
                  }),
                ]}
              >
                <Input.Password placeholder={t('security.confirmPasswordPlaceholder')} />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  {t('security.changePassword')}
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          {/* Notifications Tab */}
          <TabPane
            tab={
              <span>
                <BellOutlined />
                {t('notifications.tab')}
              </span>
            }
            key="notifications"
          >
            <h3>{t('notifications.title')}</h3>
            <Divider />

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('notifications.email.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('notifications.email.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch defaultChecked />
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('notifications.taskAssignments.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('notifications.taskAssignments.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch defaultChecked />
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('notifications.taskCompletions.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('notifications.taskCompletions.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch defaultChecked />
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('notifications.billingAlerts.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('notifications.billingAlerts.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch defaultChecked />
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('notifications.systemAnnouncements.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('notifications.systemAnnouncements.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch defaultChecked />
                </Col>
              </Row>
            </Space>
          </TabPane>

          {/* Appearance Tab */}
          <TabPane
            tab={
              <span>
                <GlobalOutlined />
                {t('appearance.tab')}
              </span>
            }
            key="appearance"
          >
            <h3>{t('appearance.title')}</h3>
            <Divider />

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('appearance.language.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('appearance.language.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Select
                    value={i18n.language}
                    onChange={handleLanguageChange}
                    style={{ width: 150 }}
                  >
                    <Option value="en">{t('appearance.language.english')}</Option>
                    <Option value="zh">{t('appearance.language.chinese')}</Option>
                  </Select>
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('appearance.darkMode.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('appearance.darkMode.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch
                    checked={theme === 'dark'}
                    onChange={handleThemeChange}
                    checkedChildren={t('appearance.darkMode.dark')}
                    unCheckedChildren={t('appearance.darkMode.light')}
                  />
                </Col>
              </Row>

              <Row justify="space-between" align="middle">
                <Col>
                  <div>
                    <strong>{t('appearance.compactMode.title')}</strong>
                    <p style={{ margin: 0, color: '#999' }}>
                      {t('appearance.compactMode.description')}
                    </p>
                  </div>
                </Col>
                <Col>
                  <Switch />
                </Col>
              </Row>
            </Space>
          </TabPane>

          {/* Branding Tab */}
          <TabPane
            tab={
              <span>
                <SkinOutlined />
                {t('branding.tab')}
              </span>
            }
            key="branding"
          >
            <h3>{t('branding.title')}</h3>
            <Divider />

            <Form
              form={brandingForm}
              layout="vertical"
              initialValues={{
                name: clientCompany?.name ?? '',
                nameEn: clientCompany?.nameEn ?? '',
                logo: clientCompany?.logo ?? '',
                label: clientCompany?.label ?? '',
              }}
              onFinish={handleBrandingSave}
              style={{ maxWidth: 480 }}
            >
              <Form.Item
                name="name"
                label={t('branding.companyName')}
                rules={[{ required: true, message: t('branding.companyNameRequired') }]}
              >
                <Input placeholder={t('branding.companyNamePlaceholder')} />
              </Form.Item>

              <Form.Item
                name="nameEn"
                label={t('branding.companyNameEn')}
                rules={[{ required: true, message: t('branding.companyNameEnRequired') }]}
              >
                <Input placeholder={t('branding.companyNameEnPlaceholder')} />
              </Form.Item>

              <Form.Item
                name="logo"
                label={t('branding.logoUrl')}
                extra={t('branding.logoUrlHint')}
              >
                <Input placeholder={t('branding.logoUrlPlaceholder')} />
              </Form.Item>

              <Form.Item name="label" label={t('branding.label')}>
                <Input placeholder={t('branding.labelPlaceholder')} />
              </Form.Item>

              <Form.Item label={t('branding.preview')}>
                <BrandingPreview />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                    {t('branding.save')}
                  </Button>
                  <Button onClick={handleBrandingReset}>
                    {t('branding.resetDefault')}
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SettingsPage;
