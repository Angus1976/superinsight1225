/**
 * Ontology Expert Collaboration Page (本体专家协作页面)
 * 
 * Main page for ontology expert collaboration features including:
 * - Expert Management
 * - Expert Recommendations
 * - Template Management
 * - Collaborative Editing
 * - Approval Workflow
 * - Validation & Compliance
 * 
 * Requirements: Task 20-25 - Frontend React Components
 */

import React, { useState } from 'react';
import { Tabs, Card, Space, Typography, message } from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  FileTextOutlined,
  EditOutlined,
  AuditOutlined,
  SafetyCertificateOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ExpertList from './ExpertList';
import ExpertRecommendation from './ExpertRecommendation';
import TemplateBrowser from './TemplateBrowser';
import TemplateInstantiationWizard from './TemplateInstantiationWizard';
import TemplateCustomizationEditor from './TemplateCustomizationEditor';
import TemplateExportImport from './TemplateExportImport';
import CollaborativeOntologyEditor from './CollaborativeOntologyEditor';
import PendingApprovalsDashboard from './PendingApprovalsDashboard';
import ApprovalChainBuilder from './ApprovalChainBuilder';
import ValidationRuleEditor from './ValidationRuleEditor';
import ChineseBusinessValidatorPanel from './ChineseBusinessValidatorPanel';
import ComplianceTemplateSelector from './ComplianceTemplateSelector';
import ComplianceReportViewer from './ComplianceReportViewer';
import TranslationEditor from './TranslationEditor';
import LanguageSwitcher from './LanguageSwitcher';
import ContextSensitiveHelp from './ContextSensitiveHelp';
import { ExpertProfile, OntologyTemplate } from '@/services/ontologyExpertApi';

const { Title } = Typography;

const OntologyPage: React.FC = () => {
  const { t } = useTranslation(['ontology', 'common']);
  const [activeTab, setActiveTab] = useState('experts');
  const [selectedExpert, setSelectedExpert] = useState<ExpertProfile | null>(null);
  
  // Template management state
  const [selectedTemplate, setSelectedTemplate] = useState<OntologyTemplate | null>(null);
  const [instantiationWizardVisible, setInstantiationWizardVisible] = useState(false);
  const [customizationEditorVisible, setCustomizationEditorVisible] = useState(false);
  const [exportImportVisible, setExportImportVisible] = useState(false);
  const [exportImportMode, setExportImportMode] = useState<'export' | 'import'>('export');
  
  // Approval workflow state
  const [showApprovalChainBuilder, setShowApprovalChainBuilder] = useState(false);
  
  // Mock current expert ID (would come from auth context in real app)
  const currentExpertId = 'current-expert-id';
  
  // Mock ontology ID (would come from route params or context)
  const currentOntologyId = 'current-ontology-id';

  // Handle expert selection from list
  const handleSelectExpert = (expert: ExpertProfile) => {
    setSelectedExpert(expert);
    // Could navigate to expert detail or show in a panel
  };

  // Handle template selection
  const handleSelectTemplate = (template: OntologyTemplate) => {
    setSelectedTemplate(template);
    // Could show template detail panel
  };

  // Handle template instantiation
  const handleInstantiateTemplate = (template: OntologyTemplate) => {
    setSelectedTemplate(template);
    setInstantiationWizardVisible(true);
  };

  // Handle template customization
  const handleCustomizeTemplate = (template: OntologyTemplate) => {
    setSelectedTemplate(template);
    setCustomizationEditorVisible(true);
  };

  // Handle template export
  const handleExportTemplate = (template: OntologyTemplate) => {
    setSelectedTemplate(template);
    setExportImportMode('export');
    setExportImportVisible(true);
  };

  // Handle template import
  const handleImportTemplate = () => {
    setSelectedTemplate(null);
    setExportImportMode('import');
    setExportImportVisible(true);
  };

  // Handle instantiation success
  const handleInstantiationSuccess = (instanceId: string) => {
    message.success(t('ontology:template.instantiateSuccess'));
    // Could navigate to the new instance or refresh the list
  };

  // Handle customization success
  const handleCustomizationSuccess = (customizedTemplate: OntologyTemplate) => {
    message.success(t('ontology:template.customizeSuccess'));
    // Could refresh the template list
  };

  // Handle import success
  const handleImportSuccess = (importedTemplate: OntologyTemplate) => {
    message.success(t('ontology:template.importSuccess'));
    // Could refresh the template list
  };
  
  // Handle view change request
  const handleViewChangeRequest = (changeRequestId: string) => {
    // Navigate to change request detail or show in modal
    console.log('View change request:', changeRequestId);
  };

  const tabItems = [
    {
      key: 'experts',
      label: (
        <Space>
          <UserOutlined />
          {t('ontology:tabs.experts')}
        </Space>
      ),
      children: <ExpertList onSelectExpert={handleSelectExpert} />,
    },
    {
      key: 'recommendations',
      label: (
        <Space>
          <TeamOutlined />
          {t('ontology:tabs.recommendations')}
        </Space>
      ),
      children: <ExpertRecommendation />,
    },
    {
      key: 'templates',
      label: (
        <Space>
          <FileTextOutlined />
          {t('ontology:tabs.templates')}
        </Space>
      ),
      children: (
        <TemplateBrowser
          onSelectTemplate={handleSelectTemplate}
          onInstantiate={handleInstantiateTemplate}
          onCustomize={handleCustomizeTemplate}
          onExport={handleExportTemplate}
        />
      ),
    },
    {
      key: 'collaboration',
      label: (
        <Space>
          <EditOutlined />
          {t('ontology:tabs.collaboration')}
        </Space>
      ),
      children: (
        <CollaborativeOntologyEditor
          ontologyId={currentOntologyId}
          currentUserId={currentExpertId}
          currentUserName="Current User"
        />
      ),
    },
    {
      key: 'approvals',
      label: (
        <Space>
          <AuditOutlined />
          {t('ontology:tabs.approvals')}
        </Space>
      ),
      children: (
        <div>
          {showApprovalChainBuilder ? (
            <ApprovalChainBuilder
              onSuccess={() => setShowApprovalChainBuilder(false)}
              onCancel={() => setShowApprovalChainBuilder(false)}
            />
          ) : (
            <PendingApprovalsDashboard
              expertId={currentExpertId}
              onViewRequest={handleViewChangeRequest}
            />
          )}
        </div>
      ),
    },
    {
      key: 'validation',
      label: (
        <Space>
          <SafetyCertificateOutlined />
          {t('ontology:validation.rulesTitle')}
        </Space>
      ),
      children: (
        <Tabs
          type="card"
          items={[
            {
              key: 'rules',
              label: t('ontology:validation.rulesTitle'),
              children: <ValidationRuleEditor />,
            },
            {
              key: 'chinese',
              label: t('ontology:validation.chineseBusinessTitle'),
              children: <ChineseBusinessValidatorPanel />,
            },
            {
              key: 'compliance',
              label: t('ontology:compliance.title'),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <ComplianceTemplateSelector ontologyId={currentOntologyId} />
                  <ComplianceReportViewer />
                </Space>
              ),
            },
          ]}
        />
      ),
    },
    {
      key: 'i18n',
      label: (
        <Space>
          <GlobalOutlined />
          {t('ontology:i18n.title')}
        </Space>
      ),
      children: <TranslationEditor ontologyId={currentOntologyId} />,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={3} style={{ margin: 0 }}>
            <Space>
              <TeamOutlined />
              {t('ontology:pageTitle')}
            </Space>
          </Title>
          <LanguageSwitcher />
        </div>
        
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
        />
      </Card>

      {/* Template Instantiation Wizard */}
      <TemplateInstantiationWizard
        template={selectedTemplate}
        visible={instantiationWizardVisible}
        onClose={() => setInstantiationWizardVisible(false)}
        onSuccess={handleInstantiationSuccess}
      />

      {/* Template Customization Editor */}
      <TemplateCustomizationEditor
        template={selectedTemplate}
        visible={customizationEditorVisible}
        onClose={() => setCustomizationEditorVisible(false)}
        onSuccess={handleCustomizationSuccess}
      />

      {/* Template Export/Import */}
      <TemplateExportImport
        template={selectedTemplate}
        mode={exportImportMode}
        visible={exportImportVisible}
        onClose={() => setExportImportVisible(false)}
        onImportSuccess={handleImportSuccess}
      />
      
      {/* Context Sensitive Help */}
      <ContextSensitiveHelp contextKey={activeTab} />
    </div>
  );
};

export default OntologyPage;

// Export individual components for direct use
export { default as ExpertList } from './ExpertList';
export { default as ExpertProfileForm } from './ExpertProfileForm';
export { default as ExpertRecommendation } from './ExpertRecommendation';
export { default as ExpertMetrics } from './ExpertMetrics';
export { default as TemplateBrowser } from './TemplateBrowser';
export { default as TemplateInstantiationWizard } from './TemplateInstantiationWizard';
export { default as TemplateCustomizationEditor } from './TemplateCustomizationEditor';
export { default as TemplateExportImport } from './TemplateExportImport';
export { default as CollaborativeOntologyEditor } from './CollaborativeOntologyEditor';
export { default as ChangeComparisonView } from './ChangeComparisonView';
export { default as ConflictResolutionDialog } from './ConflictResolutionDialog';
export { default as VersionHistoryViewer } from './VersionHistoryViewer';
export { default as ApprovalChainBuilder } from './ApprovalChainBuilder';
export { default as PendingApprovalsDashboard } from './PendingApprovalsDashboard';
export { default as ChangeRequestReviewPanel } from './ChangeRequestReviewPanel';
export { default as ApprovalWorkflowTracker } from './ApprovalWorkflowTracker';
export { default as ValidationRuleEditor } from './ValidationRuleEditor';
export { default as ChineseBusinessValidatorPanel } from './ChineseBusinessValidatorPanel';
export { default as ComplianceTemplateSelector } from './ComplianceTemplateSelector';
export { default as ComplianceReportViewer } from './ComplianceReportViewer';
export { default as LanguageSwitcher } from './LanguageSwitcher';
export { default as TranslationEditor } from './TranslationEditor';
export { default as ContextSensitiveHelp } from './ContextSensitiveHelp';
export { default as OnboardingChecklist } from './OnboardingChecklist';
