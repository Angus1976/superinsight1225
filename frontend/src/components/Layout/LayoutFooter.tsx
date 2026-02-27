/**
 * LayoutFooter Component
 *
 * 底部品牌栏，显示官方 Logo + "Powered by WinsAI Co., LTD." + 版权信息
 * - 展开态：Logo + 品牌文字 + 版权
 * - 折叠态：仅显示小 Logo
 *
 * Logo 来源：/logos/logo-simple-48.svg（设计系统官方资源）
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import styles from './LayoutFooter.module.scss';

export interface LayoutFooterProps {
  collapsed: boolean;
}

const LOGO_SIZE_EXPANDED = 20;
const LOGO_SIZE_COLLAPSED = 24;

export const LayoutFooter: React.FC<LayoutFooterProps> = ({ collapsed }) => {
  const { t } = useTranslation('common');
  const currentYear = new Date().getFullYear();

  if (collapsed) {
    return (
      <div className={styles.container}>
        <img
          src="/logos/logo-simple-48.svg"
          alt="WinsAI"
          width={LOGO_SIZE_COLLAPSED}
          height={LOGO_SIZE_COLLAPSED}
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.brandRow}>
        <img
          src="/logos/logo-simple-48.svg"
          alt="WinsAI"
          width={LOGO_SIZE_EXPANDED}
          height={LOGO_SIZE_EXPANDED}
        />
        <span className={styles.poweredText}>
          {t('footer.poweredBy', 'Powered by WinsAI Co., LTD.')}
        </span>
      </div>
      <span className={styles.copyright}>
        © {currentYear} {t('footer.companyName', '问视间（上海）科技有限公司')}
      </span>
    </div>
  );
};

export default LayoutFooter;
