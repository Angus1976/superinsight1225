import WorkflowConfig from './WorkflowConfig';

/** Default project when opening workflow settings via route (E2E / bookmark). */
const DEFAULT_QUALITY_PROJECT_ID = 'default';

export default function WorkflowConfigPage() {
  return <WorkflowConfig projectId={DEFAULT_QUALITY_PROJECT_ID} />;
}
