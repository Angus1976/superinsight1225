/**
 * ClientBranding Component — 侧边栏顶部客户品牌白板区
 *
 * 可配置的 B2B 白标区域，客户可通过 uiStore.setClientCompany() 配置：
 *
 * Logo 图片要求：
 *   - 展开态推荐尺寸：120×40px（横向 Logo）或 40×40px（方形 Logo）
 *   - 折叠态显示尺寸：32×32px（自动裁切为圆角方形）
 *   - 格式：PNG / SVG / JPG，建议 SVG 或 2x PNG
 *   - 最大文件大小：50KB
 *   - 背景：透明背景优先（适配浅色/深色主题）
 *
 * 配置示例：
 *   setClientCompany({
 *     name: '客户公司名',
 *     nameEn: 'Client Corp',
 *     logo: 'https://example.com/logo.svg',  // 可选
 *     label: '企业版',                         // 可选标签
 *   })
 *   setClientCompany(null)  // 恢复默认问视间品牌
 *
 * 显示逻辑：
 *   - clientCompany=null → 默认 Logo + "问视间"
 *   - 有 logo URL → logo 图片 + 公司名
 *   - 无 logo → 渐变首字 Avatar + 公司名
 *   - 折叠态 → 仅 Avatar/Icon，不显示文字
 */

import React, { useState } from 'react';
import { Avatar, Tag } from 'antd';
import { useUIStore, type ClientCompany } from '@/stores/uiStore';
import styles from './ClientBranding.module.scss';

export interface ClientBrandingProps {
  collapsed: boolean;
}

/**
 * Validate that a logo URL is a safe image source.
 * Accepts http/https URLs and root-relative paths (/path/to/logo.svg).
 * Rejects javascript:, data:, blob:, and other unsafe schemes to prevent XSS.
 */
export function isValidLogoUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;

  const trimmed = url.trim();
  if (!trimmed) return false;

  // Allow root-relative paths (e.g. /logos/logo.svg)
  if (trimmed.startsWith('/')) return true;

  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/** Logo pixel sizes */
const LOGO_EXPANDED_SIZE = 40;
const LOGO_COLLAPSED_SIZE = 32;

/** Deterministic gradient from company name for Avatar background */
function getAvatarGradient(name: string): string {
  const gradients = [
    'linear-gradient(135deg, #1890ff, #722ed1)',
    'linear-gradient(135deg, #13c2c2, #1890ff)',
    'linear-gradient(135deg, #722ed1, #eb2f96)',
    'linear-gradient(135deg, #52c41a, #13c2c2)',
    'linear-gradient(135deg, #faad14, #fa541c)',
  ];
  const code = name.charCodeAt(0) || 0;
  return gradients[code % gradients.length];
}

/** Render gradient Avatar with first character of company name */
const GradientAvatar: React.FC<{ name: string; size: number }> = ({ name, size }) => (
  <Avatar
    size={size}
    style={{ background: getAvatarGradient(name), flexShrink: 0 }}
  >
    {name.charAt(0)}
  </Avatar>
);

/** Render company logo image with error fallback to gradient Avatar */
const LogoImage: React.FC<{ company: ClientCompany; size: number }> = ({ company, size }) => {
  const [hasError, setHasError] = useState(false);

  if (hasError || !company.logo || !isValidLogoUrl(company.logo)) {
    return <GradientAvatar name={company.name} size={size} />;
  }

  return (
    <img
      src={company.logo}
      alt={company.name}
      className={styles.logoImage}
      width={size}
      height={size}
      onError={() => setHasError(true)}
    />
  );
};

/** Default brand config used when no client company is configured */
const DEFAULT_BRAND: ClientCompany = {
  name: '问视间',
  nameEn: 'SuperInsight',
  logo: '/logos/logo-icon-64.svg',
};

export const ClientBranding: React.FC<ClientBrandingProps> = ({ collapsed }) => {
  const clientCompany = useUIStore((s) => s.clientCompany);
  const company = clientCompany ?? DEFAULT_BRAND;
  const logoSize = collapsed ? LOGO_COLLAPSED_SIZE : LOGO_EXPANDED_SIZE;
  const hasValidLogo = !!company.logo && isValidLogoUrl(company.logo);

  return (
    <div className={styles.container}>
      {hasValidLogo ? (
        <LogoImage company={company} size={logoSize} />
      ) : (
        <GradientAvatar name={company.name} size={logoSize} />
      )}
      {!collapsed && (
        <div className={styles.info}>
          <span className={styles.companyName}>{company.name}</span>
          {company.label && (
            <Tag className={styles.label} color="blue">
              {company.label}
            </Tag>
          )}
        </div>
      )}
    </div>
  );
};

export default ClientBranding;
