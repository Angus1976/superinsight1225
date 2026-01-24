// i18next configuration
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import zhCommon from './zh/common.json';
import zhAuth from './zh/auth.json';
import zhDashboard from './zh/dashboard.json';
import zhTasks from './zh/tasks.json';
import zhBilling from './zh/billing.json';
import zhQuality from './zh/quality.json';
import zhSecurity from './zh/security.json';
import zhDataSync from './zh/dataSync.json';
import zhSystem from './zh/system.json';
import zhVersioning from './zh/versioning.json';
import zhLineage from './zh/lineage.json';
import zhImpact from './zh/impact.json';
import zhSnapshot from './zh/snapshot.json';
import zhAdmin from './zh/admin.json';
import zhWorkspace from './zh/workspace.json';
import zhLicense from './zh/license.json';
import zhSettings from './zh/settings.json';
import zhCollaboration from './zh/collaboration.json';
import zhCrowdsource from './zh/crowdsource.json';
import zhAugmentation from './zh/augmentation.json';
import zhBusinessLogic from './zh/businessLogic.json';
import zhAnnotation from './zh/annotation.json';
import zhOntology from './zh/ontology.json';
import enCommon from './en/common.json';
import enAuth from './en/auth.json';
import enDashboard from './en/dashboard.json';
import enTasks from './en/tasks.json';
import enBilling from './en/billing.json';
import enQuality from './en/quality.json';
import enSecurity from './en/security.json';
import enDataSync from './en/dataSync.json';
import enSystem from './en/system.json';
import enVersioning from './en/versioning.json';
import enLineage from './en/lineage.json';
import enImpact from './en/impact.json';
import enSnapshot from './en/snapshot.json';
import enAdmin from './en/admin.json';
import enWorkspace from './en/workspace.json';
import enLicense from './en/license.json';
import enSettings from './en/settings.json';
import enCollaboration from './en/collaboration.json';
import enCrowdsource from './en/crowdsource.json';
import enAugmentation from './en/augmentation.json';
import enBusinessLogic from './en/businessLogic.json';
import enAnnotation from './en/annotation.json';
import enOntology from './en/ontology.json';

const resources = {
  zh: {
    common: zhCommon,
    auth: zhAuth,
    dashboard: zhDashboard,
    tasks: zhTasks,
    billing: zhBilling,
    quality: zhQuality,
    security: zhSecurity,
    dataSync: zhDataSync,
    system: zhSystem,
    versioning: zhVersioning,
    lineage: zhLineage,
    impact: zhImpact,
    snapshot: zhSnapshot,
    admin: zhAdmin,
    workspace: zhWorkspace,
    license: zhLicense,
    settings: zhSettings,
    collaboration: zhCollaboration,
    crowdsource: zhCrowdsource,
    augmentation: zhAugmentation,
    businessLogic: zhBusinessLogic,
    annotation: zhAnnotation,
    ontology: zhOntology,
  },
  en: {
    common: enCommon,
    auth: enAuth,
    dashboard: enDashboard,
    tasks: enTasks,
    billing: enBilling,
    quality: enQuality,
    security: enSecurity,
    dataSync: enDataSync,
    system: enSystem,
    versioning: enVersioning,
    lineage: enLineage,
    impact: enImpact,
    snapshot: enSnapshot,
    admin: enAdmin,
    workspace: enWorkspace,
    license: enLicense,
    settings: enSettings,
    collaboration: enCollaboration,
    crowdsource: enCrowdsource,
    augmentation: enAugmentation,
    businessLogic: enBusinessLogic,
    annotation: enAnnotation,
    ontology: enOntology,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh',
    defaultNS: 'common',
    fallbackNS: 'common',
    ns: ['common', 'auth', 'dashboard', 'tasks', 'billing', 'quality', 'security', 'dataSync', 'system', 'versioning', 'lineage', 'impact', 'snapshot', 'admin', 'workspace', 'license', 'settings', 'collaboration', 'crowdsource', 'augmentation', 'businessLogic', 'annotation', 'ontology'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
