/**
 * BrandingConfigButton — 侧边栏底部品牌配置入口
 *
 * 点击弹出 Modal，可配置客户 Logo、公司名、英文名、标签。
 * 配置保存到 uiStore.clientCompany（持久化到 localStorage）。
 */

import React, { useState, useEffect } from 'react';
import { Button, Modal, Form, Input, Space, Avatar, Tag, message, Tooltip } from 'antd';
import { SettingOutlined, UndoOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useUIStore, type ClientCompany } from '@/stores/uiStore';
import { isValidLogoUrl } from './ClientBranding';

export interface BrandingConfigButtonProps {
  collapsed: boolean;
}

export const BrandingConfigButton: React.FC<BrandingConfigButtonProps> = ({ collapsed }) => {
  const { t } = useTranslation('common');
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { clientCompany, setClientCompany } = useUIStore();

  // Sync form when modal opens
  useEffect(() => {
    if (!open) return;
    form.setFieldsValue({
      name: clientCompany?.name ?? '',
      nameEn: clientCompany?.nameEn ?? '',
      logo: clientCompany?.logo ?? '',
      label: clientCompany?.label ?? '',
    });
  }, [open, clientCompany, form]);

  const handleSave = (values: { name: string; nameEn: string; logo: string; label: string }) => {
    const company: ClientCompany = {
      name: values.name.trim(),
      nameEn: values.nameEn.trim(),
    };
    if (values.logo?.trim()) company.logo = values.logo.trim();
    if (values.label?.trim()) company.label = values.label.trim();

    setClientCompany(company);
    setOpen(false);
    message.success(t('branding.saveSuccess'));
  };

  const handleReset = () => {
    setClientCompany(null);
    form.resetFields();
    setOpen(false);
    message.success(t('branding.resetSuccess'));
  };

  // Preview values from form (live)
  const PreviewSection: React.FC = () => {
    const name = Form.useWatch('name', form) || t('appName');
    const logo = Form.useWatch('logo', form) || '';
    const label = Form.useWatch('label', form) || '';
    const showLogo = logo && isValidLogoUrl(logo);

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0' }}>
        {showLogo ? (
          <img
            src={logo}
            alt={name}
            style={{ width: 32, height: 32, borderRadius: 6, objectFit: 'cover' }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <Avatar size={32} style={{ background: 'linear-gradient(135deg, #1890ff, #722ed1)', flexShrink: 0 }}>
            {name.charAt(0)}
          </Avatar>
        )}
        <span style={{ fontWeight: 600 }}>{name}</span>
        {label && <Tag color="blue" style={{ margin: 0 }}>{label}</Tag>}
      </div>
    );
  };

  return (
    <>
      <Tooltip title={collapsed ? t('branding.configButton') : undefined} placement="right">
        <Button
          type="text"
          icon={<SettingOutlined />}
          onClick={() => setOpen(true)}
          style={{
            width: '100%',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '4px 0' : '4px 16px',
            color: 'rgba(0, 0, 0, 0.45)',
          }}
        >
          {!collapsed && t('branding.configButton')}
        </Button>
      </Tooltip>

      <Modal
        title={t('branding.configTitle')}
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={480}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item
            name="name"
            label={t('branding.companyName')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input placeholder={t('branding.companyNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="nameEn"
            label={t('branding.companyNameEn')}
            rules={[{ required: true, message: t('validation.required') }]}
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
            <PreviewSection />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button icon={<UndoOutlined />} onClick={handleReset}>
                {t('branding.resetDefault')}
              </Button>
              <Space>
                <Button onClick={() => setOpen(false)}>{t('cancel')}</Button>
                <Button type="primary" htmlType="submit">{t('save')}</Button>
              </Space>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default BrandingConfigButton;
