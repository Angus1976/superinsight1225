/**
 * Brand A/B Testing Service
 * 品牌A/B测试服务
 * 
 * 功能：
 * - 品牌变体测试
 * - 用户分组机制
 * - 数据收集
 * - 测试报告生成
 */

import type { 
  ABTestConfig, 
  BrandVariant
} from '@/types/brand';

// 用户分组存储键
const USER_GROUP_KEY = 'brand_ab_test_group';
const TEST_DATA_KEY = 'brand_ab_test_data';

interface TestData {
  testId: string;
  variantId: string;
  impressions: number;
  interactions: number;
  conversions: number;
  startTime: number;
  lastActivity: number;
}

interface UserTestAssignment {
  testId: string;
  variantId: string;
  assignedAt: number;
}

class BrandABTestService {
  private activeTests: Map<string, ABTestConfig> = new Map();
  private userAssignments: Map<string, UserTestAssignment> = new Map();
  private testData: Map<string, TestData> = new Map();
  private userId: string;

  constructor() {
    this.userId = this.getOrCreateUserId();
    this.loadPersistedData();
  }

  /**
   * 获取或创建用户ID
   */
  private getOrCreateUserId(): string {
    let userId = localStorage.getItem('brand_ab_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
      localStorage.setItem('brand_ab_user_id', userId);
    }
    return userId;
  }

  /**
   * 加载持久化数据
   */
  private loadPersistedData(): void {
    try {
      const groupData = localStorage.getItem(USER_GROUP_KEY);
      if (groupData) {
        const assignments = JSON.parse(groupData);
        Object.entries(assignments).forEach(([testId, assignment]) => {
          this.userAssignments.set(testId, assignment as UserTestAssignment);
        });
      }

      const testDataStr = localStorage.getItem(TEST_DATA_KEY);
      if (testDataStr) {
        const data = JSON.parse(testDataStr);
        Object.entries(data).forEach(([key, value]) => {
          this.testData.set(key, value as TestData);
        });
      }
    } catch (error) {
      console.error('[ABTest] Failed to load persisted data:', error);
    }
  }

  /**
   * 保存持久化数据
   */
  private persistData(): void {
    try {
      const assignments: Record<string, UserTestAssignment> = {};
      this.userAssignments.forEach((value, key) => {
        assignments[key] = value;
      });
      localStorage.setItem(USER_GROUP_KEY, JSON.stringify(assignments));

      const testData: Record<string, TestData> = {};
      this.testData.forEach((value, key) => {
        testData[key] = value;
      });
      localStorage.setItem(TEST_DATA_KEY, JSON.stringify(testData));
    } catch (error) {
      console.error('[ABTest] Failed to persist data:', error);
    }
  }

  /**
   * 创建A/B测试
   */
  createTest(config: ABTestConfig): void {
    // 验证配置
    if (!config.id || !config.variants || config.variants.length < 2) {
      throw new Error('Invalid test configuration');
    }

    // 验证权重总和
    const totalWeight = config.variants.reduce((sum, v) => sum + v.weight, 0);
    if (totalWeight !== 100) {
      throw new Error('Variant weights must sum to 100');
    }

    // 确保有一个对照组
    const hasControl = config.variants.some(v => v.isControl);
    if (!hasControl) {
      config.variants[0].isControl = true;
    }

    this.activeTests.set(config.id, config);
    console.log('[ABTest] Test created:', config.id);
  }

  /**
   * 启动测试
   */
  startTest(testId: string): void {
    const test = this.activeTests.get(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    test.isActive = true;
    test.startDate = new Date().toISOString();
    console.log('[ABTest] Test started:', testId);
  }

  /**
   * 停止测试
   */
  stopTest(testId: string): void {
    const test = this.activeTests.get(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    test.isActive = false;
    test.endDate = new Date().toISOString();
    console.log('[ABTest] Test stopped:', testId);
  }

  /**
   * 获取用户的测试变体
   */
  getVariantForUser(testId: string): BrandVariant | null {
    const test = this.activeTests.get(testId);
    if (!test || !test.isActive) {
      return null;
    }

    // 检查是否已分配
    let assignment = this.userAssignments.get(testId);
    
    if (!assignment) {
      // 分配新变体
      const variant = this.assignVariant(test);
      assignment = {
        testId,
        variantId: variant.id,
        assignedAt: Date.now()
      };
      this.userAssignments.set(testId, assignment);
      this.persistData();
    }

    return test.variants.find(v => v.id === assignment!.variantId) || null;
  }

  /**
   * 根据权重分配变体
   */
  private assignVariant(test: ABTestConfig): BrandVariant {
    // 使用用户ID生成确定性随机数
    const hash = this.hashString(`${this.userId}-${test.id}`);
    const random = (hash % 100);

    let cumulative = 0;
    for (const variant of test.variants) {
      cumulative += variant.weight;
      if (random < cumulative) {
        return variant;
      }
    }

    // 默认返回第一个变体
    return test.variants[0];
  }

  /**
   * 简单哈希函数
   */
  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  /**
   * 记录展示
   */
  trackImpression(testId: string, variantId: string): void {
    const key = `${testId}-${variantId}`;
    const data = this.testData.get(key) || this.createTestData(testId, variantId);
    data.impressions++;
    data.lastActivity = Date.now();
    this.testData.set(key, data);
    this.persistData();
  }

  /**
   * 记录互动
   */
  trackInteraction(testId: string, variantId: string): void {
    const key = `${testId}-${variantId}`;
    const data = this.testData.get(key) || this.createTestData(testId, variantId);
    data.interactions++;
    data.lastActivity = Date.now();
    this.testData.set(key, data);
    this.persistData();
  }

  /**
   * 记录转化
   */
  trackConversion(testId: string, variantId: string): void {
    const key = `${testId}-${variantId}`;
    const data = this.testData.get(key) || this.createTestData(testId, variantId);
    data.conversions++;
    data.lastActivity = Date.now();
    this.testData.set(key, data);
    this.persistData();
  }

  /**
   * 创建测试数据
   */
  private createTestData(testId: string, variantId: string): TestData {
    return {
      testId,
      variantId,
      impressions: 0,
      interactions: 0,
      conversions: 0,
      startTime: Date.now(),
      lastActivity: Date.now()
    };
  }

  /**
   * 获取测试结果
   */
  getTestResults(testId: string): {
    variants: Array<{
      id: string;
      name: string;
      isControl: boolean;
      impressions: number;
      interactions: number;
      conversions: number;
      interactionRate: number;
      conversionRate: number;
    }>;
    winner: string | null;
    confidence: number;
  } | null {
    const test = this.activeTests.get(testId);
    if (!test) {
      return null;
    }

    const results = test.variants.map(variant => {
      const key = `${testId}-${variant.id}`;
      const data = this.testData.get(key);
      
      const impressions = data?.impressions || 0;
      const interactions = data?.interactions || 0;
      const conversions = data?.conversions || 0;

      return {
        id: variant.id,
        name: variant.name,
        isControl: variant.isControl,
        impressions,
        interactions,
        conversions,
        interactionRate: impressions > 0 ? (interactions / impressions) * 100 : 0,
        conversionRate: impressions > 0 ? (conversions / impressions) * 100 : 0
      };
    });

    // 简单的胜者判断（基于转化率）
    const control = results.find(r => r.isControl);
    const treatments = results.filter(r => !r.isControl);
    
    let winner: string | null = null;
    let confidence = 0;

    if (control && treatments.length > 0) {
      const bestTreatment = treatments.reduce((best, current) => 
        current.conversionRate > best.conversionRate ? current : best
      );

      if (bestTreatment.conversionRate > control.conversionRate) {
        winner = bestTreatment.id;
        // 简化的置信度计算
        const lift = (bestTreatment.conversionRate - control.conversionRate) / control.conversionRate;
        confidence = Math.min(95, Math.round(lift * 100 + 50));
      }
    }

    return { variants: results, winner, confidence };
  }

  /**
   * 生成测试报告
   */
  generateReport(testId: string): string {
    const test = this.activeTests.get(testId);
    const results = this.getTestResults(testId);

    if (!test || !results) {
      return 'Test not found';
    }

    const report = `
# A/B测试报告: ${test.name}

## 测试信息
- 测试ID: ${test.id}
- 描述: ${test.description}
- 状态: ${test.isActive ? '进行中' : '已结束'}
- 开始时间: ${test.startDate || 'N/A'}
- 结束时间: ${test.endDate || 'N/A'}

## 变体结果

| 变体 | 展示次数 | 互动次数 | 转化次数 | 互动率 | 转化率 |
|------|----------|----------|----------|--------|--------|
${results.variants.map(v => 
  `| ${v.name}${v.isControl ? ' (对照)' : ''} | ${v.impressions} | ${v.interactions} | ${v.conversions} | ${v.interactionRate.toFixed(2)}% | ${v.conversionRate.toFixed(2)}% |`
).join('\n')}

## 结论
${results.winner 
  ? `胜出变体: ${results.variants.find(v => v.id === results.winner)?.name} (置信度: ${results.confidence}%)`
  : '暂无明确胜出变体，建议继续收集数据'
}

---
报告生成时间: ${new Date().toLocaleString('zh-CN')}
    `.trim();

    return report;
  }

  /**
   * 获取所有活跃测试
   */
  getActiveTests(): ABTestConfig[] {
    return Array.from(this.activeTests.values()).filter(t => t.isActive);
  }

  /**
   * 获取所有测试
   */
  getAllTests(): ABTestConfig[] {
    return Array.from(this.activeTests.values());
  }

  /**
   * 删除测试
   */
  deleteTest(testId: string): void {
    this.activeTests.delete(testId);
    this.userAssignments.delete(testId);
    
    // 清理测试数据
    const keysToDelete: string[] = [];
    this.testData.forEach((_, key) => {
      if (key.startsWith(`${testId}-`)) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach(key => this.testData.delete(key));
    
    this.persistData();
  }

  /**
   * 重置用户分组
   */
  resetUserAssignment(testId: string): void {
    this.userAssignments.delete(testId);
    this.persistData();
  }

  /**
   * 重置所有数据
   */
  reset(): void {
    this.activeTests.clear();
    this.userAssignments.clear();
    this.testData.clear();
    localStorage.removeItem(USER_GROUP_KEY);
    localStorage.removeItem(TEST_DATA_KEY);
  }
}

// 单例导出
export const brandABTestService = new BrandABTestService();

export default brandABTestService;
