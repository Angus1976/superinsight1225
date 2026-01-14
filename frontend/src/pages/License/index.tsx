/**
 * License Management Module Index
 * 
 * Exports all license management pages and provides routing.
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import LicenseDashboard from './LicenseDashboard';
import ActivationWizard from './ActivationWizard';
import UsageMonitor from './UsageMonitor';
import LicenseReport from './LicenseReport';
import AlertConfig from './AlertConfig';

/**
 * License Module Router
 * 
 * Handles routing for all license management pages.
 */
const LicenseModule: React.FC = () => {
  return (
    <Routes>
      <Route index element={<LicenseDashboard />} />
      <Route path="dashboard" element={<LicenseDashboard />} />
      <Route path="activate" element={<ActivationWizard />} />
      <Route path="usage" element={<UsageMonitor />} />
      <Route path="report" element={<LicenseReport />} />
      <Route path="alerts" element={<AlertConfig />} />
      <Route path="*" element={<Navigate to="/license" replace />} />
    </Routes>
  );
};

// Export individual pages for direct imports
export {
  LicenseDashboard,
  ActivationWizard,
  UsageMonitor,
  LicenseReport,
  AlertConfig,
};

export default LicenseModule;
