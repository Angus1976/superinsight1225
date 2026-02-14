/**
 * SuperInsight Skill for OpenClaw
 * 
 * Enables querying and analyzing SuperInsight governed data through
 * conversational interfaces across multiple channels.
 * 
 * Enhanced with workflow design capabilities for conversational
 * data processing workflow creation and execution.
 * 
 * Requirements: 5.2, 5.3, 5.4, 5.5, 14.1, 14.2, 14.3, 14.5
 */

require('dotenv').config();
const axios = require('axios');

// Configuration from environment variables
function getConfig() {
  return {
    apiUrl: process.env.SUPERINSIGHT_API_URL || 'http://backend:8000',
    apiKey: process.env.SUPERINSIGHT_API_KEY,
    tenantId: process.env.SUPERINSIGHT_TENANT_ID,
    timeout: parseInt(process.env.SKILL_TIMEOUT || '30000', 10)
  };
}

// Authentication state
let authToken = null;
let tokenExpiry = null;

/**
 * Authenticate with SuperInsight API
 * 
 * Validates: Requirement 5.2
 * 
 * @returns {Promise<string>} JWT token
 * @throws {Error} If authentication fails
 */
async function authenticate() {
  const config = getConfig();
  
  // Return cached token if still valid
  if (authToken && tokenExpiry && Date.now() < tokenExpiry) {
    return authToken;
  }

  if (!config.apiKey) {
    throw new Error('SUPERINSIGHT_API_KEY not configured');
  }

  try {
    const response = await axios.post(
      `${config.apiUrl}/api/v1/ai-integration/auth/token`,
      { api_key: config.apiKey },
      { timeout: config.timeout }
    );

    authToken = response.data.access_token;
    // Token expires in 1 hour, refresh 5 minutes early
    tokenExpiry = Date.now() + (55 * 60 * 1000);

    return authToken;
  } catch (error) {
    throw new Error(
      `Authentication failed: ${error.response?.data?.detail || error.message}`
    );
  }
}

/**
 * Parse natural language query into API parameters
 * 
 * Validates: Requirement 5.3
 * 
 * @param {string} query - Natural language query
 * @returns {Object} Parsed query parameters
 */
function parseQuery(query) {
  const filters = {};
  const lowerQuery = query.toLowerCase();

  // Extract dataset filter - improved regex with multiple patterns
  // Matches: dataset name, from dataset name, show me dataset name, query dataset: name, get data from dataset-name
  const datasetMatch = query.match(/dataset[:\s]+([a-zA-Z0-9_-]+)|from\s+dataset[:\s-]+([a-zA-Z0-9_-]+)|show\s+me\s+dataset\s+([a-zA-Z0-9_-]+)|query\s+dataset[:\s]+([a-zA-Z0-9_-]+)|get\s+data\s+from\s+dataset[:\s-]+([a-zA-Z0-9_-]+)/i);
  if (datasetMatch) {
    const datasetName = datasetMatch[1] || datasetMatch[2] || datasetMatch[3] || datasetMatch[4] || datasetMatch[5];
    filters.dataset = datasetName.toLowerCase();
  }

  // Extract annotation status
  if (lowerQuery.includes('annotated')) {
    filters.annotation_status = 'completed';
  } else if (lowerQuery.includes('pending')) {
    filters.annotation_status = 'pending';
  }

  // Extract quality score threshold
  const qualityMatch = lowerQuery.match(/quality[:\s]+([0-9.]+)/i);
  if (qualityMatch) {
    filters.min_quality_score = parseFloat(qualityMatch[1]);
  }

  // Extract limit
  const limitMatch = lowerQuery.match(/(?:top|first|limit)[:\s]+(\d+)/i);
  if (limitMatch) {
    filters.page_size = parseInt(limitMatch[1], 10);
  }

  return filters;
}

/**
 * Query governed data from SuperInsight
 * 
 * @param {Object} filters - Query filters
 * @param {number} page - Page number
 * @param {number} pageSize - Page size
 * @returns {Promise<Object>} Query results
 * @throws {Error} If query fails
 */
async function queryData(filters = {}, page = 1, pageSize = 100) {
  const config = getConfig();
  const token = await authenticate();

  try {
    const response = await axios.get(
      `${config.apiUrl}/api/v1/ai-integration/data/query`,
      {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          filters: JSON.stringify(filters),
          page,
          page_size: pageSize
        },
        timeout: config.timeout
      }
    );

    return response.data;
  } catch (error) {
    if (error.response?.status === 401) {
      // Token expired, clear cache and retry
      authToken = null;
      tokenExpiry = null;
      return queryData(filters, page, pageSize);
    }
    throw error;
  }
}

/**
 * Format results for channel-appropriate display
 * 
 * Validates: Requirement 5.4
 * 
 * @param {Object} data - Query results
 * @param {string} channel - Channel type (whatsapp, telegram, slack, etc.)
 * @returns {string} Formatted message
 */
function formatResults(data, channel = 'whatsapp') {
  if (!data || !data.data || !data.data.results || data.data.results.length === 0) {
    return 'No data found.';
  }

  const { total_records, page, page_size } = data;
  const records = data.data.results || [];

  // Channel-specific constraints
  const maxLength = channel === 'whatsapp' ? 4096 : 2000;
  const maxRecords = channel === 'telegram' ? 10 : 5;

  let message = `Found ${total_records} records (page ${page}):\n\n`;

  // Format records
  const displayRecords = records.slice(0, maxRecords);
  for (const record of displayRecords) {
    const recordText = formatRecord(record);
    if (message.length + recordText.length > maxLength - 100) {
      message += '\n... (truncated)';
      break;
    }
    message += recordText + '\n';
  }

  // Add pagination info
  if (total_records > page_size) {
    const totalPages = Math.ceil(total_records / page_size);
    message += `\nPage ${page} of ${totalPages}`;
  }

  return message.substring(0, maxLength);
}

/**
 * Format a single record
 * 
 * @param {Object} record - Data record
 * @returns {string} Formatted record text
 */
function formatRecord(record) {
  const id = record.id || 'N/A';
  const quality = record.quality_score 
    ? `Quality: ${(record.quality_score * 100).toFixed(1)}%` 
    : '';
  const status = record.annotation_status || 'unknown';

  return `• ID: ${id} | Status: ${status} ${quality}`.trim();
}

/**
 * Handle errors with user-friendly messages
 * 
 * Validates: Requirement 5.5
 * 
 * @param {Error} error - Error object
 * @returns {string} User-friendly error message
 */
function handleError(error) {
  // Authentication errors
  if (error.message && error.message.includes('Authentication failed')) {
    return 'Unable to connect to SuperInsight. Please check your API credentials.';
  }

  // Permission errors
  if (error.response?.status === 403) {
    return 'You do not have permission to access this data. Please contact your administrator.';
  }

  // Network errors
  if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') {
    return 'Cannot reach SuperInsight service. Please try again later.';
  }

  // Rate limiting
  if (error.response?.status === 429) {
    const retryAfter = error.response.headers['retry-after'] || '60';
    return `Rate limit exceeded. Please try again in ${retryAfter} seconds.`;
  }

  // Generic error with suggestion
  const errorMessage = error.message || 'Unknown error';
  return `An error occurred: ${errorMessage}. Please try rephrasing your query or contact support.`;
}

/**
 * Main skill handler
 * 
 * @param {string} query - Natural language query
 * @param {Object} context - Execution context (channel, user, etc.)
 * @returns {Promise<string>} Response message
 */
async function handleQuery(query, context = {}) {
  try {
    // Check if this is a workflow-related query
    if (isWorkflowQuery(query)) {
      return await handleWorkflowQuery(query, context);
    }

    // Parse natural language query
    const filters = parseQuery(query);

    // Query data
    const data = await queryData(
      filters,
      context.page || 1,
      context.pageSize || 100
    );

    // Format results for channel
    return formatResults(data, context.channel);
  } catch (error) {
    return handleError(error);
  }
}

/**
 * Check if query is workflow-related
 * 
 * @param {string} query - Natural language query
 * @returns {boolean} True if workflow query
 */
function isWorkflowQuery(query) {
  const lowerQuery = query.toLowerCase();
  const workflowKeywords = [
    'workflow', 'design', 'create workflow', 'build workflow',
    'execute workflow', 'run workflow', 'compare', 'comparison',
    'pipeline', 'build a pipeline'
  ];
  return workflowKeywords.some(keyword => lowerQuery.includes(keyword));
}

/**
 * Handle workflow-related queries
 * 
 * Validates: Requirements 14.1, 14.2, 14.3, 14.5
 * 
 * @param {string} query - Natural language query
 * @param {Object} context - Execution context
 * @returns {Promise<string>} Response message
 */
async function handleWorkflowQuery(query, context = {}) {
  const lowerQuery = query.toLowerCase();

  try {
    // Design/create workflow
    if (lowerQuery.includes('design') || lowerQuery.includes('create')) {
      return await designWorkflow(query, context);
    }

    // Execute workflow
    if (lowerQuery.includes('execute') || lowerQuery.includes('run')) {
      return await executeWorkflow(query, context);
    }

    // Compare results
    if (lowerQuery.includes('compare') || lowerQuery.includes('comparison')) {
      return await compareWorkflowResults(query, context);
    }

    return 'I can help you design, execute, or compare workflows. What would you like to do?';
  } catch (error) {
    return handleError(error);
  }
}

/**
 * Design a workflow from natural language description
 * 
 * Validates: Requirements 14.1, 14.2
 * 
 * @param {string} description - Natural language workflow description
 * @param {Object} context - Execution context
 * @returns {Promise<string>} Workflow design response
 */
async function designWorkflow(description, context = {}) {
  const config = getConfig();
  const token = await authenticate();

  try {
    // Parse workflow description
    const response = await axios.post(
      `${config.apiUrl}/api/v1/ai-integration/workflows/parse`,
      { description },
      {
        headers: { Authorization: `Bearer ${token}` },
        timeout: config.timeout
      }
    );

    const workflow = response.data;

    // Format workflow definition for chat
    return formatWorkflowDesign(workflow, context.channel);
  } catch (error) {
    if (error.response?.status === 401) {
      authToken = null;
      tokenExpiry = null;
      return designWorkflow(description, context);
    }
    throw error;
  }
}

/**
 * Execute a workflow
 * 
 * Validates: Requirements 14.3, 14.5
 * 
 * @param {string} query - Query containing workflow ID or name
 * @param {Object} context - Execution context
 * @returns {Promise<string>} Execution results
 */
async function executeWorkflow(query, context = {}) {
  const config = getConfig();
  const token = await authenticate();

  // Extract workflow ID from query
  const workflowId = extractWorkflowId(query);
  if (!workflowId) {
    return 'Please specify a workflow ID or name to execute. Example: "execute workflow abc123"';
  }

  try {
    const response = await axios.post(
      `${config.apiUrl}/api/v1/ai-integration/workflows/${workflowId}/execute`,
      { use_governed_data: true },
      {
        headers: { Authorization: `Bearer ${token}` },
        timeout: config.timeout * 2 // Workflows may take longer
      }
    );

    const results = response.data;
    return formatWorkflowResults(results, context.channel);
  } catch (error) {
    if (error.response?.status === 401) {
      authToken = null;
      tokenExpiry = null;
      return executeWorkflow(query, context);
    }
    throw error;
  }
}

/**
 * Compare workflow results (governed vs raw data)
 * 
 * Validates: Requirements 14.5
 * 
 * @param {string} query - Query containing workflow ID
 * @param {Object} context - Execution context
 * @returns {Promise<string>} Comparison results
 */
async function compareWorkflowResults(query, context = {}) {
  const config = getConfig();
  const token = await authenticate();

  const workflowId = extractWorkflowId(query);
  if (!workflowId) {
    return 'Please specify a workflow ID to compare. Example: "compare workflow abc123"';
  }

  try {
    const response = await axios.post(
      `${config.apiUrl}/api/v1/ai-integration/workflows/${workflowId}/compare`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
        timeout: config.timeout * 3 // Comparison takes longer
      }
    );

    const comparison = response.data;
    return formatComparisonResults(comparison, context.channel);
  } catch (error) {
    if (error.response?.status === 401) {
      authToken = null;
      tokenExpiry = null;
      return compareWorkflowResults(query, context);
    }
    throw error;
  }
}

/**
 * Extract workflow ID from query
 * 
 * @param {string} query - Natural language query
 * @returns {string|null} Workflow ID or null
 */
function extractWorkflowId(query) {
  // Match UUID pattern
  const uuidMatch = query.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  if (uuidMatch) {
    return uuidMatch[0];
  }

  // Match workflow name pattern
  const nameMatch = query.match(/workflow[:\s]+([a-z0-9_-]+)/i);
  if (nameMatch) {
    return nameMatch[1];
  }

  return null;
}

/**
 * Format workflow design for chat display
 * 
 * Validates: Requirement 14.1
 * 
 * @param {Object} workflow - Workflow definition
 * @param {string} channel - Channel type
 * @returns {string} Formatted workflow design
 */
function formatWorkflowDesign(workflow, channel = 'whatsapp') {
  const maxLength = channel === 'whatsapp' ? 4096 : 2000;

  let message = `✅ Workflow designed successfully!\n\n`;
  message += `📋 Name: ${workflow.name}\n`;
  message += `🆔 ID: ${workflow.id}\n\n`;

  message += `📊 Data Sources:\n`;
  for (const source of workflow.data_sources || []) {
    message += `  • ${source.dataset} (${source.filters || 'no filters'})\n`;
  }

  message += `\n⚙️ Processing Steps:\n`;
  for (let i = 0; i < (workflow.steps || []).length; i++) {
    const step = workflow.steps[i];
    message += `  ${i + 1}. ${step.operation}: ${step.description}\n`;
  }

  message += `\n📤 Output: ${workflow.output_format || 'JSON'}\n`;

  message += `\n💡 To execute: "execute workflow ${workflow.id}"`;
  message += `\n📊 To compare: "compare workflow ${workflow.id}"`;

  return message.substring(0, maxLength);
}

/**
 * Format workflow execution results
 * 
 * Validates: Requirement 14.3
 * 
 * @param {Object} results - Execution results
 * @param {string} channel - Channel type
 * @returns {string} Formatted results
 */
function formatWorkflowResults(results, channel = 'whatsapp') {
  const maxLength = channel === 'whatsapp' ? 4096 : 2000;

  let message = `✅ Workflow executed successfully!\n\n`;
  message += `⏱️ Execution time: ${results.execution_time_ms}ms\n`;
  message += `📊 Records processed: ${results.records_processed}\n`;
  message += `✨ Quality score: ${(results.quality_score * 100).toFixed(1)}%\n\n`;

  message += `📈 Results:\n`;
  const resultData = results.results || [];
  const maxRecords = channel === 'telegram' ? 5 : 3;

  for (let i = 0; i < Math.min(resultData.length, maxRecords); i++) {
    const record = resultData[i];
    message += `  ${i + 1}. ${JSON.stringify(record).substring(0, 100)}...\n`;
  }

  if (resultData.length > maxRecords) {
    message += `  ... and ${resultData.length - maxRecords} more\n`;
  }

  message += `\n💡 To compare with raw data: "compare workflow ${results.workflow_id}"`;

  return message.substring(0, maxLength);
}

/**
 * Format comparison results
 * 
 * Validates: Requirement 14.5
 * 
 * @param {Object} comparison - Comparison results
 * @param {string} channel - Channel type
 * @returns {string} Formatted comparison
 */
function formatComparisonResults(comparison, channel = 'whatsapp') {
  const maxLength = channel === 'whatsapp' ? 4096 : 2000;

  const governed = comparison.governed_data || {};
  const raw = comparison.raw_data || {};
  const improvement = comparison.improvement || {};

  let message = `📊 Data Quality Comparison\n\n`;

  message += `🏆 Governed Data:\n`;
  message += `  • Completeness: ${(governed.completeness * 100).toFixed(1)}%\n`;
  message += `  • Accuracy: ${(governed.accuracy * 100).toFixed(1)}%\n`;
  message += `  • Consistency: ${(governed.consistency * 100).toFixed(1)}%\n`;
  message += `  • Overall Quality: ${(governed.overall_quality * 100).toFixed(1)}%\n\n`;

  message += `📉 Raw Data:\n`;
  message += `  • Completeness: ${(raw.completeness * 100).toFixed(1)}%\n`;
  message += `  • Accuracy: ${(raw.accuracy * 100).toFixed(1)}%\n`;
  message += `  • Consistency: ${(raw.consistency * 100).toFixed(1)}%\n`;
  message += `  • Overall Quality: ${(raw.overall_quality * 100).toFixed(1)}%\n\n`;

  message += `✨ Improvement:\n`;
  message += `  • Completeness: +${(improvement.completeness * 100).toFixed(1)}%\n`;
  message += `  • Accuracy: +${(improvement.accuracy * 100).toFixed(1)}%\n`;
  message += `  • Consistency: +${(improvement.consistency * 100).toFixed(1)}%\n`;
  message += `  • Overall: +${(improvement.overall * 100).toFixed(1)}%\n\n`;

  message += `💡 Governed data shows ${(improvement.overall * 100).toFixed(0)}% better quality!`;

  return message.substring(0, maxLength);
}

// Export skill interface
module.exports = {
  name: 'superinsight',
  description: 'Query and analyze SuperInsight governed data with workflow design capabilities',
  version: '2.0.0',
  
  // Main handler
  handle: handleQuery,
  handleQuery, // Export for tests
  
  // Exported functions for testing
  authenticate,
  parseQuery,
  queryData,
  formatResults,
  handleError,
  
  // Workflow functions
  isWorkflowQuery,
  handleWorkflowQuery,
  designWorkflow,
  executeWorkflow,
  compareWorkflowResults,
  extractWorkflowId,
  formatWorkflowDesign,
  formatWorkflowResults,
  formatComparisonResults,
  
  // Auth state for testing
  get authToken() { return authToken; },
  set authToken(value) { authToken = value; },
  get tokenExpiry() { return tokenExpiry; },
  set tokenExpiry(value) { tokenExpiry = value; }
};
