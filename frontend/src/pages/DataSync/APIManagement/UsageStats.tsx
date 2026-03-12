import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Statistic, Row, Col, Empty, message, Spin } from 'antd';
import { Column, Pie } from '@ant-design/plots';
import { ApiOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

const { Option } = Select;

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  total_calls: number;
}

interface UsageStats {
  key_id: string;
  total_calls: number;
  calls_by_date: Array<{ date: string; count: number }>;
  calls_by_endpoint: Array<{ endpoint: string; count: number }>;
}

const UsageStats: React.FC = () => {
  const { t } = useTranslation('dataSync');
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>('week');
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchKeys();
  }, []);

  useEffect(() => {
    if (selectedKeyId) {
      fetchStats();
    }
  }, [selectedKeyId, period]);

  const fetchKeys = async () => {
    try {
      const response = await axios.get('/api/v1/sync/api-keys/');
      setKeys(response.data);
      if (response.data.length > 0) {
        setSelectedKeyId(response.data[0].id);
      }
    } catch (error) {
      message.error(t('apiManagement.createError'));
    }
  };

  const fetchStats = async () => {
    if (!selectedKeyId) return;

    setLoading(true);
    try {
      const response = await axios.get(
        `/api/v1/sync/api-keys/${selectedKeyId}/usage`,
        { params: { period } }
      );
      setStats(response.data);
    } catch (error) {
      message.error(t('apiManagement.testError'));
    } finally {
      setLoading(false);
    }
  };

  const columnConfig = {
    data: stats?.calls_by_date || [],
    xField: 'date',
    yField: 'count',
    label: {
      position: 'top' as const,
      style: {
        fill: '#000000',
        opacity: 0.6
      }
    },
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false
      }
    },
    meta: {
      date: {
        alias: t('apiManagement.callsByDate')
      },
      count: {
        alias: t('apiManagement.totalCalls')
      }
    }
  };

  const pieConfig = {
    data: stats?.calls_by_endpoint || [],
    angleField: 'count',
    colorField: 'endpoint',
    radius: 0.8,
    label: {
      type: 'outer' as const,
      content: '{name} {percentage}'
    },
    interactions: [
      {
        type: 'element-active' as const
      }
    ]
  };

  const selectedKey = keys.find((k) => k.id === selectedKeyId);

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Card>
          <Space size="large">
            <div>
              <div style={{ marginBottom: 8 }}>{t('apiManagement.selectKey')}</div>
              <Select
                style={{ width: 300 }}
                value={selectedKeyId}
                onChange={setSelectedKeyId}
                placeholder={t('apiManagement.selectKey')}
              >
                {keys.map((key) => (
                  <Option key={key.id} value={key.id}>
                    {key.name} ({key.key_prefix}...)
                  </Option>
                ))}
              </Select>
            </div>

            <div>
              <div style={{ marginBottom: 8 }}>{t('apiManagement.selectPeriod')}</div>
              <Select
                style={{ width: 200 }}
                value={period}
                onChange={setPeriod}
              >
                <Option value="day">{t('apiManagement.periodDay')}</Option>
                <Option value="week">{t('apiManagement.periodWeek')}</Option>
                <Option value="month">{t('apiManagement.periodMonth')}</Option>
              </Select>
            </div>
          </Space>
        </Card>

        {loading ? (
          <Card>
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin size="large" />
            </div>
          </Card>
        ) : stats ? (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Card>
                  <Statistic
                    title={t('apiManagement.totalCalls')}
                    value={stats.total_calls}
                    prefix={<ApiOutlined />}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card>
                  <Statistic
                    title={t('apiManagement.lastUsed')}
                    value={selectedKey?.total_calls || 0}
                    prefix={<ClockCircleOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            <Card title={t('apiManagement.callsByDate')}>
              {stats.calls_by_date.length > 0 ? (
                <Column {...columnConfig} />
              ) : (
                <Empty description={t('apiManagement.noData')} />
              )}
            </Card>

            <Card title={t('apiManagement.callsByEndpoint')}>
              {stats.calls_by_endpoint.length > 0 ? (
                <Pie {...pieConfig} />
              ) : (
                <Empty description={t('apiManagement.noData')} />
              )}
            </Card>
          </>
        ) : (
          <Card>
            <Empty description={t('apiManagement.noData')} />
          </Card>
        )}
      </Space>
    </div>
  );
};

export default UsageStats;
