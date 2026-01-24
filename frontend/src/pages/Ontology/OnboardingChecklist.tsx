/**
 * OnboardingChecklist Component (新手引导清单)
 * 
 * Personalized onboarding checklist with:
 * - Track tutorial completion
 * - Unlock features progressively
 * - Connect to mentor
 * 
 * Requirements: 15.2, 15.3, 15.5
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Steps,
  Progress,
  Button,
  Space,
  Typography,
  Tag,
  Avatar,
  Divider,
  Modal,
  message,
  Alert,
  Row,
  Col,
  Tooltip,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  TeamOutlined,
  FileTextOutlined,
  EditOutlined,
  PlayCircleOutlined,
  TrophyOutlined,
  RocketOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text, Paragraph } = Typography;

interface OnboardingStep {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action?: () => void;
  actionLabel?: string;
  videoUrl?: string;
  completed: boolean;
  skipped: boolean;
}

interface MentorInfo {
  id: string;
  name: string;
  avatar?: string;
  expertise: string[];
  email: string;
}

interface OnboardingChecklistProps {
  expertId: string;
  onStepComplete?: (stepKey: string) => void;
  onRequestMentor?: () => void;
}

const STORAGE_KEY = 'ontology_onboarding_progress';

const OnboardingChecklist: React.FC<OnboardingChecklistProps> = ({
  expertId,
  onStepComplete,
  onRequestMentor,
}) => {
  const { t } = useTranslation('ontology');
  const [steps, setSteps] = useState<OnboardingStep[]>([]);
  const [mentor, setMentor] = useState<MentorInfo | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);

  // Initialize steps
  useEffect(() => {
    const savedProgress = localStorage.getItem(`${STORAGE_KEY}_${expertId}`);
    const progress = savedProgress ? JSON.parse(savedProgress) : {};

    const initialSteps: OnboardingStep[] = [
      {
        key: 'createProfile',
        title: t('onboarding.steps.createProfile'),
        description: t('onboarding.steps.createProfileDesc'),
        icon: <UserOutlined />,
        actionLabel: t('expert.createProfile'),
        completed: progress.createProfile || false,
        skipped: progress.createProfile_skipped || false,
      },
      {
        key: 'exploreTemplates',
        title: t('onboarding.steps.exploreTemplates'),
        description: t('onboarding.steps.exploreTemplatesDesc'),
        icon: <FileTextOutlined />,
        actionLabel: t('template.listTitle'),
        completed: progress.exploreTemplates || false,
        skipped: progress.exploreTemplates_skipped || false,
      },
      {
        key: 'joinCollaboration',
        title: t('onboarding.steps.joinCollaboration'),
        description: t('onboarding.steps.joinCollaborationDesc'),
        icon: <TeamOutlined />,
        actionLabel: t('collaboration.joinSession'),
        completed: progress.joinCollaboration || false,
        skipped: progress.joinCollaboration_skipped || false,
      },
      {
        key: 'submitChange',
        title: t('onboarding.steps.submitChange'),
        description: t('onboarding.steps.submitChangeDesc'),
        icon: <EditOutlined />,
        actionLabel: t('approval.createChain'),
        completed: progress.submitChange || false,
        skipped: progress.submitChange_skipped || false,
      },
      {
        key: 'completeTraining',
        title: t('onboarding.steps.completeTraining'),
        description: t('onboarding.steps.completeTrainingDesc'),
        icon: <PlayCircleOutlined />,
        actionLabel: t('help.tutorials'),
        videoUrl: 'https://example.com/training',
        completed: progress.completeTraining || false,
        skipped: progress.completeTraining_skipped || false,
      },
    ];

    setSteps(initialSteps);

    // Find current step
    const firstIncomplete = initialSteps.findIndex((s) => !s.completed && !s.skipped);
    setCurrentStep(firstIncomplete >= 0 ? firstIncomplete : initialSteps.length);
  }, [expertId, t]);

  // Save progress
  const saveProgress = (updatedSteps: OnboardingStep[]) => {
    const progress: Record<string, boolean> = {};
    updatedSteps.forEach((step) => {
      progress[step.key] = step.completed;
      progress[`${step.key}_skipped`] = step.skipped;
    });
    localStorage.setItem(`${STORAGE_KEY}_${expertId}`, JSON.stringify(progress));
  };

  const handleMarkComplete = (stepKey: string) => {
    const updatedSteps = steps.map((step) =>
      step.key === stepKey ? { ...step, completed: true, skipped: false } : step
    );
    setSteps(updatedSteps);
    saveProgress(updatedSteps);
    onStepComplete?.(stepKey);
    message.success(t('common.success'));

    // Move to next step
    const nextIncomplete = updatedSteps.findIndex((s) => !s.completed && !s.skipped);
    setCurrentStep(nextIncomplete >= 0 ? nextIncomplete : updatedSteps.length);
  };

  const handleSkipStep = (stepKey: string) => {
    const updatedSteps = steps.map((step) =>
      step.key === stepKey ? { ...step, skipped: true } : step
    );
    setSteps(updatedSteps);
    saveProgress(updatedSteps);

    // Move to next step
    const nextIncomplete = updatedSteps.findIndex((s) => !s.completed && !s.skipped);
    setCurrentStep(nextIncomplete >= 0 ? nextIncomplete : updatedSteps.length);
  };

  const handleRestartOnboarding = () => {
    const resetSteps = steps.map((step) => ({
      ...step,
      completed: false,
      skipped: false,
    }));
    setSteps(resetSteps);
    saveProgress(resetSteps);
    setCurrentStep(0);
    setShowWelcome(true);
  };

  const handleRequestMentor = () => {
    onRequestMentor?.();
    message.success(t('onboarding.mentorRequestSuccess'));
  };

  const completedCount = steps.filter((s) => s.completed).length;
  const totalSteps = steps.length;
  const progressPercent = Math.round((completedCount / totalSteps) * 100);
  const isComplete = completedCount === totalSteps;

  const getStepStatus = (index: number, step: OnboardingStep) => {
    if (step.completed) return 'finish';
    if (step.skipped) return 'wait';
    if (index === currentStep) return 'process';
    return 'wait';
  };

  return (
    <div>
      {/* Welcome Modal */}
      <Modal
        title={
          <Space>
            <RocketOutlined style={{ color: '#1890ff' }} />
            {t('onboarding.welcome')}
          </Space>
        }
        open={showWelcome && !isComplete}
        onOk={() => setShowWelcome(false)}
        onCancel={() => setShowWelcome(false)}
        okText={t('common.start')}
        cancelText={t('common.later')}
      >
        <Paragraph>{t('onboarding.welcomeDesc')}</Paragraph>
        <Alert
          type="info"
          showIcon
          message={t('onboarding.checklist')}
          description={`${totalSteps} ${t('common.steps')}`}
        />
      </Modal>

      {/* Progress Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col span={16}>
            <Title level={4} style={{ margin: 0 }}>
              <TrophyOutlined style={{ color: '#faad14' }} /> {t('onboarding.checklist')}
            </Title>
            <Text type="secondary">
              {t('onboarding.progress')}: {completedCount} / {totalSteps}
            </Text>
          </Col>
          <Col span={8}>
            <Progress
              type="circle"
              percent={progressPercent}
              width={80}
              format={(percent) => (
                <span style={{ fontSize: 16 }}>
                  {isComplete ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : `${percent}%`}
                </span>
              )}
            />
          </Col>
        </Row>
      </Card>

      {/* Completion Celebration */}
      {isComplete && (
        <Alert
          type="success"
          showIcon
          icon={<StarOutlined />}
          message={t('common.congratulations')}
          description={t('onboarding.finish')}
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={handleRestartOnboarding}>
              {t('onboarding.restartOnboarding')}
            </Button>
          }
        />
      )}

      {/* Steps */}
      <Card>
        <Steps
          direction="vertical"
          current={currentStep}
          items={steps.map((step, index) => ({
            title: (
              <Space>
                {step.title}
                {step.completed && <Tag color="success">{t('common.completed')}</Tag>}
                {step.skipped && <Tag>{t('common.skipped')}</Tag>}
              </Space>
            ),
            description: (
              <div style={{ marginTop: 8 }}>
                <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                  {step.description}
                </Paragraph>
                {!step.completed && !step.skipped && index === currentStep && (
                  <Space>
                    <Button
                      type="primary"
                      size="small"
                      onClick={() => handleMarkComplete(step.key)}
                    >
                      {t('onboarding.markComplete')}
                    </Button>
                    <Button size="small" onClick={() => handleSkipStep(step.key)}>
                      {t('onboarding.skipStep')}
                    </Button>
                    {step.videoUrl && (
                      <Button
                        size="small"
                        icon={<PlayCircleOutlined />}
                        href={step.videoUrl}
                        target="_blank"
                      >
                        {t('help.tutorials')}
                      </Button>
                    )}
                  </Space>
                )}
              </div>
            ),
            icon: step.icon,
            status: getStepStatus(index, step),
          }))}
        />
      </Card>

      {/* Mentor Section */}
      <Card title={t('onboarding.mentor')} style={{ marginTop: 16 }}>
        {mentor ? (
          <Space>
            <Avatar size={48} icon={<UserOutlined />} src={mentor.avatar} />
            <div>
              <Text strong>{mentor.name}</Text>
              <br />
              <Text type="secondary">{mentor.expertise.join(', ')}</Text>
              <br />
              <Text type="secondary">{mentor.email}</Text>
            </div>
          </Space>
        ) : (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Text type="secondary">{t('onboarding.noMentor')}</Text>
            <br />
            <Button
              type="primary"
              icon={<TeamOutlined />}
              onClick={handleRequestMentor}
              style={{ marginTop: 8 }}
            >
              {t('onboarding.requestMentor')}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};

export default OnboardingChecklist;
