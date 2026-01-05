// 实时业务洞察通知组件
import React, { useState, useEffect, useCallback } from 'react';
import {
  notification,
  Badge,
  Button,
  Drawer,
  List,
  Avatar,
  Typography,
  Tag,
  Space,
  Empty,
  Divider,
  Tooltip,
  Switch,
  Card,
  Alert,
} from 'antd';
import {
  BellOutlined,
  BulbOutlined,
  CheckOutlined,
  CloseOutlined,
  SettingOutlined,
  MailOutlined,
  MessageOutlined,
  SoundOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

interface BusinessInsight {
  id: string;
  insight_type: string;
  title: string;
  description: string;
  impact_score: number;
  recommendations: string[];
  data_points: any[];
  created_at: string;
  acknowledged_at?: string;
}

interface NotificationSettings {
  enabled: boolean;
  sound: boolean;
  email: boolean;
  sms: boolean;
  minImpactScore: number;
}

interface InsightNotificationProps {
  projectId: string;
  onInsightReceived?: (insight: BusinessInsight) => void;
  onInsightAcknowledge?: (insightId: string) => void;
}

export const InsightNotification: React.FC<InsightNotificationProps> = ({
  projectId,
  onInsightReceived,
  onInsightAcknowledge,
}) => {
  const [notifications, setNotifications] = useState<BusinessInsight[]>([]);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [settings, setSettings] = useState<NotificationSettings>({
    enabled: true,
    sound: true,
    email: false,
    sms: false,
    minImpactScore: 0.5,
  });
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  // 初始化WebSocket连接
  const initWebSocket = useCallback(() => {
    if (!settings.enabled) return;

    const wsUrl = `ws://localhost:8000/ws/business-logic/${projectId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('业务洞察WebSocket连接已建立');
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'business_insight') {
          const insight: BusinessInsight = data.payload;
          
          // 检查影响分数阈值
          if (insight.impact_score >= settings.minImpactScore) {
            handleNewInsight(insight);
          }
        } else if (data.type === 'pattern_change') {
          handlePatternChange(data.payload);
        } else if (data.type === 'rule_update') {
          handleRuleUpdate(data.payload);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };

    ws.onclose = () => {
      console.log('业务洞察WebSocket连接已关闭');
      setConnectionStatus('disconnected');
      
      // 5秒后尝试重连
      setTimeout(() => {
        if (settings.enabled) {
          setConnectionStatus('connecting');
          initWebSocket();
        }
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error('业务洞察WebSocket连接错误:', error);
      setConnectionStatus('disconnected');
    };

    setWebsocket(ws);
  }, [projectId, settings.enabled, settings.minImpactScore]);

  // 处理新洞察
  const handleNewInsight = (insight: BusinessInsight) => {
    // 添加到通知列表
    setNotifications(prev => [insight, ...prev]);

    // 显示系统通知
    const impactLevel = insight.impact_score >= 0.8 ? 'error' : 
                       insight.impact_score >= 0.6 ? 'warning' : 'info';

    notification[impactLevel]({
      message: '新的业务洞察',
      description: insight.title,
      icon: <BulbOutlined style={{ color: '#1890ff' }} />,
      duration: 6,
      onClick: () => {
        setDrawerVisible(true);
      },
    });

    // 播放提示音
    if (settings.sound) {
      playNotificationSound();
    }

    // 发送邮件通知
    if (settings.email) {
      sendEmailNotification(insight);
    }

    // 发送短信通知
    if (settings.sms) {
      sendSmsNotification(insight);
    }

    // 回调通知
    onInsightReceived?.(insight);
  };

  // 处理模式变化
  const handlePatternChange = (changeData: any) => {
    notification.info({
      message: '业务模式变化',
      description: changeData.description,
      icon: <BellOutlined style={{ color: '#52c41a' }} />,
      duration: 4,
    });
  };

  // 处理规则更新
  const handleRuleUpdate = (updateData: any) => {
    notification.info({
      message: '业务规则更新',
      description: updateData.description,
      icon: <SettingOutlined style={{ color: '#faad14' }} />,
      duration: 4,
    });
  };

  // 播放通知音效
  const playNotificationSound = () => {
    try {
      const audio = new Audio('/sounds/notification.mp3');
      audio.volume = 0.3;
      audio.play().catch(error => {
        console.warn('播放通知音效失败:', error);
      });
    } catch (error) {
      console.warn('创建音频对象失败:', error);
    }
  };

  // 发送邮件通知
  const sendEmailNotification = async (insight: BusinessInsight) => {
    try {
      await fetch('/api/notifications/email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'business_insight',
          project_id: projectId,
          insight_id: insight.id,
          title: insight.title,
          description: insight.description,
          impact_score: insight.impact_score,
        }),
      });
    } catch (error) {
      console.error('发送邮件通知失败:', error);
    }
  };

  // 发送短信通知
  const sendSmsNotification = async (insight: BusinessInsight) => {
    try {
      await fetch('/api/notifications/sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'business_insight',
          project_id: projectId,
          insight_id: insight.id,
          title: insight.title,
          impact_score: insight.impact_score,
        }),
      });
    } catch (error) {
      console.error('发送短信通知失败:', error);
    }
  };

  // 确认洞察
  const acknowledgeInsight = async (insightId: string) => {
    try {
      const response = await fetch(`/api/business-logic/insights/${insightId}/acknowledge`, {
        method: 'POST',
      });

      if (response.ok) {
        // 从通知列表中移除
        setNotifications(prev => prev.filter(n => n.id !== insightId));
        onInsightAcknowledge?.(insightId);
        
        notification.success({
          message: '洞察已确认',
          duration: 2,
        });
      }
    } catch (error) {
      console.error('确认洞察失败:', error);
      notification.error({
        message: '确认洞察失败',
        duration: 3,
      });
    }
  };

  // 忽略洞察
  const dismissInsight = (insightId: string) => {
    setNotifications(prev => prev.filter(n => n.id !== insightId));
  };

  // 清空所有通知
  const clearAllNotifications = () => {
    setNotifications([]);
  };

  // 更新设置
  const updateSettings = (newSettings: Partial<NotificationSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  // 获取影响等级颜色
  const getImpactColor = (score: number) => {
    if (score >= 0.8) return 'red';
    if (score >= 0.6) return 'orange';
    if (score >= 0.4) return 'blue';
    return 'green';
  };

  // 获取影响等级文本
  const getImpactText = (score: number) => {
    if (score >= 0.8) return '高影响';
    if (score >= 0.6) return '中影响';
    if (score >= 0.4) return '低影响';
    return '微影响';
  };

  // 初始化WebSocket连接
  useEffect(() => {
    initWebSocket();

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [initWebSocket]);

  // 连接状态指示器
  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return '#52c41a';
      case 'connecting': return '#faad14';
      case 'disconnected': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中';
      case 'disconnected': return '已断开';
      default: return '未知';
    }
  };

  return (
    <>
      {/* 通知按钮 */}
      <Tooltip title={`业务洞察通知 (${getConnectionStatusText()})`}>
        <Badge count={notifications.length} size="small">
          <Button
            type="text"
            icon={<BellOutlined />}
            onClick={() => setDrawerVisible(true)}
            style={{
              border: `2px solid ${getConnectionStatusColor()}`,
              borderRadius: '50%',
            }}
          />
        </Badge>
      </Tooltip>

      {/* 通知抽屉 */}
      <Drawer
        title={
          <Space>
            <BulbOutlined />
            业务洞察通知
            <Badge count={notifications.length} />
          </Space>
        }
        placement="right"
        width={400}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        extra={
          <Space>
            <Tooltip title="清空所有通知">
              <Button
                type="text"
                size="small"
                onClick={clearAllNotifications}
                disabled={notifications.length === 0}
              >
                清空
              </Button>
            </Tooltip>
            <Tooltip title="通知设置">
              <Button
                type="text"
                size="small"
                icon={<SettingOutlined />}
                onClick={() => {
                  // 这里可以打开设置模态框
                }}
              />
            </Tooltip>
          </Space>
        }
      >
        {/* 连接状态 */}
        <Alert
          message={
            <Space>
              <span>连接状态:</span>
              <Tag color={getConnectionStatusColor()}>{getConnectionStatusText()}</Tag>
              {connectionStatus === 'disconnected' && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    setConnectionStatus('connecting');
                    initWebSocket();
                  }}
                >
                  重连
                </Button>
              )}
            </Space>
          }
          type={connectionStatus === 'connected' ? 'success' : 'warning'}
          showIcon={false}
          style={{ marginBottom: 16 }}
        />

        {/* 通知设置 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Title level={5}>通知设置</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Switch
                checked={settings.enabled}
                onChange={(checked) => updateSettings({ enabled: checked })}
              />
              <Text>启用通知</Text>
            </Space>
            <Space>
              <Switch
                checked={settings.sound}
                onChange={(checked) => updateSettings({ sound: checked })}
                disabled={!settings.enabled}
              />
              <SoundOutlined />
              <Text>声音提醒</Text>
            </Space>
            <Space>
              <Switch
                checked={settings.email}
                onChange={(checked) => updateSettings({ email: checked })}
                disabled={!settings.enabled}
              />
              <MailOutlined />
              <Text>邮件通知</Text>
            </Space>
            <Space>
              <Switch
                checked={settings.sms}
                onChange={(checked) => updateSettings({ sms: checked })}
                disabled={!settings.enabled}
              />
              <MessageOutlined />
              <Text>短信通知</Text>
            </Space>
          </Space>
        </Card>

        {/* 通知列表 */}
        {notifications.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无新的业务洞察"
          />
        ) : (
          <List
            dataSource={notifications}
            renderItem={(insight) => (
              <List.Item
                key={insight.id}
                actions={[
                  <Tooltip title="确认洞察">
                    <Button
                      type="text"
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={() => acknowledgeInsight(insight.id)}
                    />
                  </Tooltip>,
                  <Tooltip title="忽略">
                    <Button
                      type="text"
                      size="small"
                      icon={<CloseOutlined />}
                      onClick={() => dismissInsight(insight.id)}
                    />
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar
                      icon={<BulbOutlined />}
                      style={{
                        backgroundColor: getImpactColor(insight.impact_score),
                      }}
                    />
                  }
                  title={
                    <Space>
                      <Text strong>{insight.title}</Text>
                      <Tag color={getImpactColor(insight.impact_score)} size="small">
                        {getImpactText(insight.impact_score)}
                      </Tag>
                    </Space>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {insight.description}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {new Date(insight.created_at).toLocaleString()}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </>
  );
};