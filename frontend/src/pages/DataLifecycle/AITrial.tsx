/**
 * AI Trial Management Page
 * 
 * Configure and run AI trial calculations on different data stages.
 */

import { useState } from 'react';
import { Card, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

const { Title } = Typography;

const AITrial: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');

  return (
    <div>
      <Title level={4}>{t('aiTrial.title')}</Title>
      <Card>
        <p>{t('aiTrial.description')}</p>
      </Card>
    </div>
  );
};

export default AITrial;
