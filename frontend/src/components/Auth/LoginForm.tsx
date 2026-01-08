// Login form component
import { useState, useEffect } from 'react';
import { Form, Input, Button, Checkbox, Select } from 'antd';
import { UserOutlined, LockOutlined, TeamOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/auth';
import { ROUTES } from '@/constants';
import type { LoginCredentials, Tenant } from '@/types';

interface LoginFormProps {
  onSuccess?: () => void;
}

interface LoginFormValues extends LoginCredentials {
  remember: boolean;
  tenant_id?: string;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const { t } = useTranslation('auth');
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(false);

  // Load available tenants on component mount
  useEffect(() => {
    const loadTenants = async () => {
      setLoadingTenants(true);
      try {
        const tenantList = await authService.getTenants();
        setTenants(tenantList);
      } catch (error) {
        console.error('Failed to load tenants:', error);
        // Don't show error message as tenant selection might be optional
      } finally {
        setLoadingTenants(false);
      }
    };

    loadTenants();
  }, []);

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      const credentials: LoginCredentials = {
        username: values.username,
        password: values.password,
        tenant_id: values.tenant_id,
      };
      await login(credentials);
      onSuccess?.();
    } catch {
      // Error is handled in useAuth hook
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      name="login"
      initialValues={{ remember: true }}
      onFinish={handleSubmit}
      size="large"
      layout="vertical"
    >
      <Form.Item
        name="username"
        rules={[{ required: true, message: t('login.usernamePlaceholder') }]}
      >
        <Input prefix={<UserOutlined />} placeholder={t('login.usernamePlaceholder')} />
      </Form.Item>

      <Form.Item name="password" rules={[{ required: true, message: t('login.passwordPlaceholder') }]}>
        <Input.Password prefix={<LockOutlined />} placeholder={t('login.passwordPlaceholder')} />
      </Form.Item>

      {/* Tenant Selection - Show if tenants are available */}
      {tenants.length > 0 && (
        <Form.Item
          name="tenant_id"
          label={t('tenant.select')}
          rules={[{ required: true, message: t('tenant.selectRequired') }]}
        >
          <Select
            placeholder={t('tenant.selectPlaceholder')}
            loading={loadingTenants}
            prefix={<TeamOutlined />}
            showSearch
            optionFilterProp="children"
          >
            {tenants.map((tenant) => (
              <Select.Option key={tenant.id} value={tenant.id}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {tenant.logo && (
                    <img 
                      src={tenant.logo} 
                      alt={tenant.name} 
                      style={{ width: 16, height: 16, borderRadius: 2 }}
                    />
                  )}
                  {tenant.name}
                </div>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      )}

      <Form.Item>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Form.Item name="remember" valuePropName="checked" noStyle>
            <Checkbox>{t('login.rememberMe')}</Checkbox>
          </Form.Item>
          <Link to={ROUTES.FORGOT_PASSWORD}>{t('login.forgotPassword')}</Link>
        </div>
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block>
          {t('login.submit')}
        </Button>
      </Form.Item>
    </Form>
  );
};
