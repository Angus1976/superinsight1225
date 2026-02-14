/**
 * Property and Unit Tests for SuperInsight Skill
 * 
 * Tests:
 * - Property 15: Skill Authentication (Requirements 5.2)
 * - Property 16: Natural Language Query Translation (Requirements 5.3)
 * - Unit tests for result formatting (Requirements 5.4)
 */

const skill = require('./index');
const axios = require('axios');

// Mock axios
jest.mock('axios');

describe('Property 15: Skill Authentication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset auth state
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  /**
   * Property: For any skill invocation, the skill should authenticate
   * with SuperInsight using the gateway's API credentials before accessing data.
   */
  test('should authenticate before any data access', async () => {
    const apiKey = 'test-api-key-123';
    process.env.SUPERINSIGHT_API_KEY = apiKey;
    
    const mockToken = 'jwt-token-abc';
    axios.post.mockResolvedValue({
      data: { access_token: mockToken }
    });

    const token = await skill.authenticate();

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/ai-integration/auth/token'),
      { api_key: apiKey },
      expect.any(Object)
    );
    expect(token).toBe(mockToken);
  });

  test('should reuse cached token if still valid', async () => {
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    
    // First authentication
    axios.post.mockResolvedValue({
      data: { access_token: 'token-1' }
    });
    await skill.authenticate();
    
    // Second call should use cache
    const token = await skill.authenticate();
    
    expect(axios.post).toHaveBeenCalledTimes(1);
    expect(token).toBe('token-1');
  });

  test('should refresh expired token', async () => {
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    
    // Set expired token
    skill.authToken = 'old-token';
    skill.tokenExpiry = Date.now() - 1000;
    
    axios.post.mockResolvedValue({
      data: { access_token: 'new-token' }
    });

    const token = await skill.authenticate();

    expect(axios.post).toHaveBeenCalled();
    expect(token).toBe('new-token');
  });

  test('should throw error if API key not configured', async () => {
    delete process.env.SUPERINSIGHT_API_KEY;

    await expect(skill.authenticate()).rejects.toThrow(
      'SUPERINSIGHT_API_KEY not configured'
    );
  });

  test('should handle authentication failure', async () => {
    process.env.SUPERINSIGHT_API_KEY = 'invalid-key';
    
    axios.post.mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } }
    });

    await expect(skill.authenticate()).rejects.toThrow(
      'Authentication failed: Invalid credentials'
    );
  });
});

describe('Property 16: Natural Language Query Translation', () => {
  /**
   * Property: For any natural language query through OpenClaw,
   * the SuperInsight_Skill should translate it into one or more
   * Data_Access_API calls with appropriate parameters.
   */
  
  test('should extract dataset filter from query', () => {
    const queries = [
      'show me dataset customer_data',
      'query dataset: product_catalog',
      'get data from dataset-sales-2024'
    ];

    queries.forEach(query => {
      const filters = skill.parseQuery(query);
      expect(filters).toHaveProperty('dataset');
      expect(typeof filters.dataset).toBe('string');
    });
  });

  test('should extract annotation status from query', () => {
    const annotatedQuery = 'show annotated records';
    const pendingQuery = 'get pending annotations';

    const annotatedFilters = skill.parseQuery(annotatedQuery);
    const pendingFilters = skill.parseQuery(pendingQuery);

    expect(annotatedFilters.annotation_status).toBe('completed');
    expect(pendingFilters.annotation_status).toBe('pending');
  });

  test('should extract quality score threshold', () => {
    const queries = [
      { text: 'quality: 0.8', expected: 0.8 },
      { text: 'quality 0.95', expected: 0.95 },
      { text: 'quality: 0.5', expected: 0.5 }
    ];

    queries.forEach(({ text, expected }) => {
      const filters = skill.parseQuery(text);
      expect(filters.min_quality_score).toBe(expected);
    });
  });

  test('should extract limit from query', () => {
    const queries = [
      { text: 'top 10 records', expected: 10 },
      { text: 'first 5 items', expected: 5 },
      { text: 'limit: 20', expected: 20 }
    ];

    queries.forEach(({ text, expected }) => {
      const filters = skill.parseQuery(text);
      expect(filters.page_size).toBe(expected);
    });
  });

  test('should handle complex queries with multiple filters', () => {
    const query = 'show top 10 annotated records from dataset customer_data with quality: 0.9';
    
    const filters = skill.parseQuery(query);

    expect(filters.dataset).toBe('customer_data');
    expect(filters.annotation_status).toBe('completed');
    expect(filters.min_quality_score).toBe(0.9);
    expect(filters.page_size).toBe(10);
  });

  test('should return empty filters for unrecognized query', () => {
    const query = 'hello world';
    const filters = skill.parseQuery(query);
    
    expect(Object.keys(filters).length).toBe(0);
  });

  test('should be case insensitive', () => {
    const upperQuery = 'DATASET CUSTOMER_DATA ANNOTATED QUALITY: 0.8';
    const lowerQuery = 'dataset customer_data annotated quality: 0.8';

    const upperFilters = skill.parseQuery(upperQuery);
    const lowerFilters = skill.parseQuery(lowerQuery);

    expect(upperFilters).toEqual(lowerFilters);
  });
});

describe('Unit Tests: Result Formatting (Requirements 5.4)', () => {
  const mockData = {
    total_records: 25,
    page: 1,
    page_size: 10,
    data: {
      results: [
        { id: '1', annotation_status: 'completed', quality_score: 0.95 },
        { id: '2', annotation_status: 'pending', quality_score: 0.80 },
        { id: '3', annotation_status: 'completed', quality_score: 0.88 }
      ]
    }
  };

  test('should format results for WhatsApp channel', () => {
    const result = skill.formatResults(mockData, 'whatsapp');

    expect(result).toContain('Found 25 records');
    expect(result).toContain('ID: 1');
    expect(result).toContain('Quality: 95.0%');
    expect(result.length).toBeLessThanOrEqual(4096);
  });

  test('should format results for Telegram channel', () => {
    const result = skill.formatResults(mockData, 'telegram');

    expect(result).toContain('Found 25 records');
    expect(result).toContain('Status: completed');
    expect(result.length).toBeLessThanOrEqual(2000);
  });

  test('should limit records based on channel', () => {
    const largeData = {
      ...mockData,
      data: {
        results: Array(20).fill(null).map((_, i) => ({
          id: `${i}`,
          annotation_status: 'completed',
          quality_score: 0.9
        }))
      }
    };

    const whatsappResult = skill.formatResults(largeData, 'whatsapp');
    const telegramResult = skill.formatResults(largeData, 'telegram');

    // WhatsApp shows max 5 records, Telegram shows max 10
    const whatsappRecords = (whatsappResult.match(/ID:/g) || []).length;
    const telegramRecords = (telegramResult.match(/ID:/g) || []).length;

    expect(whatsappRecords).toBeLessThanOrEqual(5);
    expect(telegramRecords).toBeLessThanOrEqual(10);
  });

  test('should truncate long messages', () => {
    const hugeData = {
      total_records: 1000,
      page: 1,
      page_size: 100,
      data: {
        results: Array(100).fill(null).map((_, i) => ({
          id: `very-long-id-${i}-with-lots-of-text`,
          annotation_status: 'completed',
          quality_score: 0.9
        }))
      }
    };

    const whatsappResult = skill.formatResults(hugeData, 'whatsapp');
    const telegramResult = skill.formatResults(hugeData, 'telegram');

    expect(whatsappResult.length).toBeLessThanOrEqual(4096);
    expect(telegramResult.length).toBeLessThanOrEqual(2000);
  });

  test('should include pagination info', () => {
    const result = skill.formatResults(mockData, 'whatsapp');

    expect(result).toContain('Page 1 of 3');
  });

  test('should handle empty results', () => {
    const emptyData = {
      total_records: 0,
      page: 1,
      page_size: 10,
      data: { results: [] }
    };

    const result = skill.formatResults(emptyData, 'whatsapp');

    expect(result).toBe('No data found.');
  });

  test('should handle null data', () => {
    const result = skill.formatResults(null, 'whatsapp');
    expect(result).toBe('No data found.');
  });

  test('should format quality score as percentage', () => {
    const result = skill.formatResults(mockData, 'whatsapp');

    expect(result).toContain('95.0%');
    expect(result).toContain('80.0%');
  });

  test('should handle missing quality score', () => {
    const dataWithoutQuality = {
      total_records: 1,
      page: 1,
      page_size: 10,
      data: {
        results: [{ id: '1', annotation_status: 'pending' }]
      }
    };

    const result = skill.formatResults(dataWithoutQuality, 'whatsapp');

    expect(result).toContain('ID: 1');
    expect(result).toContain('Status: pending');
    expect(result).not.toContain('Quality:');
  });
});

describe('Integration: Authentication with Query', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
  });

  test('should authenticate before querying data', async () => {
    axios.post.mockResolvedValue({
      data: { access_token: 'token-123' }
    });

    axios.get.mockResolvedValue({
      data: {
        total_records: 5,
        page: 1,
        page_size: 10,
        data: { results: [] }
      }
    });

    await skill.queryData({ dataset: 'test' });

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/token'),
      expect.any(Object),
      expect.any(Object)
    );

    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/data/query'),
      expect.objectContaining({
        headers: { Authorization: 'Bearer token-123' }
      })
    );
  });

  test('should retry with new token on 401 error', async () => {
    axios.post.mockResolvedValue({
      data: { access_token: 'new-token' }
    });

    axios.get
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce({
        data: {
          total_records: 0,
          page: 1,
          page_size: 10,
          data: { results: [] }
        }
      });

    await skill.queryData({ dataset: 'test' });

    expect(axios.get).toHaveBeenCalledTimes(2);
  });
});

describe('Integration: Workflow Design Conversation Flow (Requirements 14.1, 14.2)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  test('should detect workflow-related queries', () => {
    const workflowQueries = [
      'design a workflow',
      'create workflow for data processing',
      'build a pipeline',
      'execute workflow abc123',
      'compare workflow results'
    ];

    workflowQueries.forEach(query => {
      expect(skill.isWorkflowQuery(query)).toBe(true);
    });
  });

  test('should not detect non-workflow queries', () => {
    const normalQueries = [
      'show me data',
      'get annotated records',
      'query dataset customer_data'
    ];

    normalQueries.forEach(query => {
      expect(skill.isWorkflowQuery(query)).toBe(false);
    });
  });

  test('should design workflow from natural language', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/parse')) {
        return Promise.resolve({
          data: {
            id: 'wf-123',
            name: 'Customer Analysis',
            data_sources: [
              { dataset: 'customers', filters: 'quality > 0.9' }
            ],
            steps: [
              { operation: 'filter', description: 'Filter by quality' },
              { operation: 'analyze', description: 'Analyze sentiment' }
            ],
            output_format: 'JSON'
          }
        });
      }
    });

    const result = await skill.designWorkflow(
      'Design a workflow to analyze customers with quality > 0.9',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Workflow designed successfully');
    expect(result).toContain('Customer Analysis');
    expect(result).toContain('wf-123');
    expect(result).toContain('customers');
    expect(result).toContain('filter');
    expect(result).toContain('analyze');
  });

  test('should handle workflow design errors gracefully', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/parse')) {
        return Promise.reject({
          response: {
            status: 400,
            data: { detail: 'Invalid workflow description' }
          }
        });
      }
    });

    const result = await skill.handleQuery(
      'design a workflow with invalid syntax',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('error');
  });
});

describe('Integration: Workflow Execution (Requirements 14.3, 14.5)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  test('should extract workflow ID from query', () => {
    const queries = [
      { text: 'execute workflow abc123', expected: 'abc123' },
      { text: 'run workflow: customer-analysis', expected: 'customer-analysis' },
      { text: 'execute workflow a1b2c3d4-e5f6-7890-abcd-ef1234567890', 
        expected: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' }
    ];

    queries.forEach(({ text, expected }) => {
      const id = skill.extractWorkflowId(text);
      expect(id).toBe(expected);
    });
  });

  test('should execute workflow successfully', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/wf-123/execute')) {
        return Promise.resolve({
          data: {
            workflow_id: 'wf-123',
            execution_time_ms: 1250,
            records_processed: 847,
            quality_score: 0.943,
            results: [
              { product: 'Widget A', sentiment: 0.85 },
              { product: 'Widget B', sentiment: 0.92 }
            ]
          }
        });
      }
    });

    const result = await skill.executeWorkflow(
      'execute workflow wf-123',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('executed successfully');
    expect(result).toContain('1250ms');
    expect(result).toContain('847');
    expect(result).toContain('94.3%');
  });

  test('should handle missing workflow ID', async () => {
    const result = await skill.executeWorkflow(
      'execute workflow',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Please specify a workflow ID');
  });

  test('should handle workflow execution errors', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/invalid/execute')) {
        return Promise.reject({
          response: {
            status: 404,
            data: { detail: 'Workflow not found' }
          }
        });
      }
    });

    const result = await skill.handleQuery(
      'execute workflow invalid',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('error');
  });
});

describe('Integration: Quality Comparison (Requirements 14.5)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  test('should compare workflow results', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/wf-123/compare')) {
        return Promise.resolve({
          data: {
            governed_data: {
              completeness: 0.965,
              accuracy: 0.943,
              consistency: 0.978,
              overall_quality: 0.962
            },
            raw_data: {
              completeness: 0.782,
              accuracy: 0.715,
              consistency: 0.693,
              overall_quality: 0.730
            },
            improvement: {
              completeness: 0.183,
              accuracy: 0.228,
              consistency: 0.285,
              overall: 0.232
            }
          }
        });
      }
    });

    const result = await skill.compareWorkflowResults(
      'compare workflow wf-123',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Data Quality Comparison');
    expect(result).toContain('Governed Data');
    expect(result).toContain('Raw Data');
    expect(result).toContain('Improvement');
    expect(result).toContain('96.5%'); // Governed completeness
    expect(result).toContain('78.2%'); // Raw completeness
    expect(result).toContain('+18.3%'); // Improvement
  });

  test('should handle missing workflow ID in comparison', async () => {
    const result = await skill.compareWorkflowResults(
      'compare workflow',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Please specify a workflow ID');
  });

  test('should format comparison for different channels', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/wf-123/compare')) {
        return Promise.resolve({
          data: {
            governed_data: { completeness: 0.9, accuracy: 0.9, consistency: 0.9, overall_quality: 0.9 },
            raw_data: { completeness: 0.7, accuracy: 0.7, consistency: 0.7, overall_quality: 0.7 },
            improvement: { completeness: 0.2, accuracy: 0.2, consistency: 0.2, overall: 0.2 }
          }
        });
      }
    });

    const whatsappResult = await skill.compareWorkflowResults(
      'compare workflow wf-123',
      { channel: 'whatsapp' }
    );

    const telegramResult = await skill.compareWorkflowResults(
      'compare workflow wf-123',
      { channel: 'telegram' }
    );

    expect(whatsappResult.length).toBeLessThanOrEqual(4096);
    expect(telegramResult.length).toBeLessThanOrEqual(2000);
  });
});

describe('Integration: Error Scenarios (Requirements 14.1, 14.2, 14.5)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  test('should handle network errors gracefully', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      return Promise.reject({ code: 'ECONNREFUSED' });
    });

    const result = await skill.handleQuery(
      'design a workflow',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Cannot reach SuperInsight service');
  });

  test('should handle permission errors', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      return Promise.reject({ response: { status: 403 } });
    });

    const result = await skill.handleQuery(
      'execute workflow wf-123',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('do not have permission');
  });

  test('should handle rate limiting', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      return Promise.reject({
        response: {
          status: 429,
          headers: { 'retry-after': '120' }
        }
      });
    });

    const result = await skill.handleQuery(
      'compare workflow wf-123',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Rate limit exceeded');
    expect(result).toContain('120 seconds');
  });

  test('should handle token expiry during workflow operations', async () => {
    let callCount = 0;
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: `token-${++callCount}` } });
      }
      if (url.includes('/workflows')) {
        if (callCount === 1) {
          return Promise.reject({ response: { status: 401 } });
        }
        return Promise.resolve({
          data: {
            id: 'wf-123',
            name: 'Test Workflow',
            data_sources: [],
            steps: [],
            output_format: 'JSON'
          }
        });
      }
    });

    const result = await skill.designWorkflow(
      'design a test workflow',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('Workflow designed successfully');
    expect(callCount).toBe(2); // Should have re-authenticated
  });

  test('should provide helpful error messages', async () => {
    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      return Promise.reject({
        message: 'Unexpected error',
        response: { status: 500 }
      });
    });

    const result = await skill.handleQuery(
      'design a workflow',
      { channel: 'whatsapp' }
    );

    expect(result).toContain('error occurred');
    expect(result).toContain('try rephrasing');
  });
});

describe('Integration: Complete Workflow Journey', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.SUPERINSIGHT_API_KEY = 'test-key';
    process.env.SUPERINSIGHT_API_URL = 'http://test:8000';
    skill.authToken = null;
    skill.tokenExpiry = null;
  });

  test('should handle complete workflow lifecycle', async () => {
    const workflowId = 'wf-complete-test';

    axios.post.mockImplementation((url) => {
      if (url.includes('/auth/token')) {
        return Promise.resolve({ data: { access_token: 'token-123' } });
      }
      if (url.includes('/workflows/parse')) {
        return Promise.resolve({
          data: {
            id: workflowId,
            name: 'Complete Test Workflow',
            data_sources: [{ dataset: 'test_data' }],
            steps: [{ operation: 'filter', description: 'Test filter' }],
            output_format: 'JSON'
          }
        });
      }
      if (url.includes(`/workflows/${workflowId}/execute`)) {
        return Promise.resolve({
          data: {
            workflow_id: workflowId,
            execution_time_ms: 500,
            records_processed: 100,
            quality_score: 0.95,
            results: [{ test: 'data' }]
          }
        });
      }
      if (url.includes(`/workflows/${workflowId}/compare`)) {
        return Promise.resolve({
          data: {
            governed_data: { completeness: 0.95, accuracy: 0.95, consistency: 0.95, overall_quality: 0.95 },
            raw_data: { completeness: 0.75, accuracy: 0.75, consistency: 0.75, overall_quality: 0.75 },
            improvement: { completeness: 0.2, accuracy: 0.2, consistency: 0.2, overall: 0.2 }
          }
        });
      }
    });

    // Step 1: Design workflow
    const designResult = await skill.handleQuery(
      'design a workflow to process test data',
      { channel: 'whatsapp' }
    );
    expect(designResult).toContain('Workflow designed successfully');
    expect(designResult).toContain(workflowId);

    // Step 2: Execute workflow
    const executeResult = await skill.handleQuery(
      `execute workflow ${workflowId}`,
      { channel: 'whatsapp' }
    );
    expect(executeResult).toContain('executed successfully');
    expect(executeResult).toContain('500ms');

    // Step 3: Compare results
    const compareResult = await skill.handleQuery(
      `compare workflow ${workflowId}`,
      { channel: 'whatsapp' }
    );
    expect(compareResult).toContain('Data Quality Comparison');
    expect(compareResult).toContain('95.0%');
  });
});
