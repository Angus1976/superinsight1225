/**
 * Label Studio i18n 翻译注入脚本
 *
 * 运行在 Label Studio iframe 内部，通过 DOM 操作实现界面中文翻译。
 * - 内嵌英中翻译词典（导航、按钮、表单、提示、表头、工具栏）
 * - MutationObserver 监听 DOM 变化，翻译新增文本节点
 * - postMessage 接收语言切换指令，500ms 内完成切换
 * - "Label Studio" → "问视间" 品牌替换
 * - 加载失败静默降级，不影响标注功能
 */
(function () {
  'use strict';

  // ============================================================
  // 翻译词典 — 精确文本匹配，避免误替换
  // ============================================================
  var TRANSLATIONS = {
    // 品牌
    'Label Studio': '问视间',

    // 导航菜单
    'Projects': '项目',
    'Data Manager': '数据管理',
    'Settings': '设置',
    'Dashboard': '仪表盘',
    'Organization': '组织',
    'Members': '成员',
    'Account & Settings': '账户与设置',

    // 按钮标签
    'Submit': '提交',
    'Skip': '跳过',
    'Update': '更新',
    'Cancel': '取消',
    'Save': '保存',
    'Delete': '删除',
    'Create': '创建',
    'Create Project': '创建项目',
    'Import': '导入',
    'Export': '导出',
    'Sign Out': '退出登录',
    'Accept': '接受',
    'Reject': '拒绝',
    'Fix + Accept': '修正并接受',

    // 表单标签
    'Name': '名称',
    'Description': '描述',
    'Email': '邮箱',
    'Password': '密码',

    // 提示信息
    'Loading...': '加载中...',
    'No results': '无结果',
    'No data': '暂无数据',
    'No projects yet': '暂无项目',
    'Are you sure?': '确定吗？',
    'Something went wrong': '出现错误',
    'Page not found': '页面未找到',
    'Saving...': '保存中...',
    'Submitting...': '提交中...',

    // 数据管理表头
    'ID': 'ID',
    'Status': '状态',
    'Annotator': '标注员',
    'Total Annotations': '标注总数',
    'Cancelled Annotations': '已取消标注',
    'Total Predictions': '预测总数',
    'Completed': '已完成',
    'Created At': '创建时间',
    'Updated At': '更新时间',
    'Source': '来源',
    'Tasks': '任务',
    'Annotations': '标注',
    'Predictions': '预测',

    // 标注工具栏
    'Regions': '区域',
    'Relations': '关系',
    'History': '历史',
    'Undo': '撤销',
    'Redo': '重做',
    'Reset': '重置',
    'Zoom In': '放大',
    'Zoom Out': '缩小',
    'Fit': '适应',

    // 标注状态
    'In Progress': '进行中',
    'Skipped': '已跳过',

    // 筛选与排序
    'Filter': '筛选',
    'Sort': '排序',
    'Columns': '列',
    'Order': '排序',
    'Search': '搜索'
  };

  // ============================================================
  // 反向词典 — 用于 zh → en 切换时还原
  // ============================================================
  var REVERSE_TRANSLATIONS = {};
  Object.keys(TRANSLATIONS).forEach(function (en) {
    REVERSE_TRANSLATIONS[TRANSLATIONS[en]] = en;
  });

  // ============================================================
  // 状态
  // ============================================================
  var currentLang = 'zh';
  var observer = null;
  var isTranslating = false;

  // ============================================================
  // 核心翻译函数
  // ============================================================

  /**
   * 根据当前语言翻译文本
   * @param {string} text - 原始文本
   * @returns {string} 翻译后的文本
   */
  function translateText(text) {
    if (!text || typeof text !== 'string') return text;

    var trimmed = text.trim();
    if (!trimmed) return text;

    if (currentLang === 'zh') {
      return TRANSLATIONS[trimmed] !== undefined ? TRANSLATIONS[trimmed] : text;
    }

    // en 模式：还原中文为英文
    return REVERSE_TRANSLATIONS[trimmed] !== undefined ? REVERSE_TRANSLATIONS[trimmed] : text;
  }

  /**
   * 翻译单个文本节点
   * @param {Text} node - DOM 文本节点
   */
  function translateTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE) return;
    if (!node.nodeValue || !node.nodeValue.trim()) return;

    var parent = node.parentElement;
    if (!parent) return;

    // 跳过 script / style / textarea 等不可见元素
    var tag = parent.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA' || tag === 'CODE' || tag === 'PRE') {
      return;
    }

    var translated = translateText(node.nodeValue);
    if (translated !== node.nodeValue) {
      node.nodeValue = translated;
    }
  }

  /**
   * 遍历 DOM 树翻译所有文本节点
   * @param {Node} root - 遍历起点
   */
  function translateDOM(root) {
    if (!root) return;

    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    var node;
    while ((node = walker.nextNode())) {
      translateTextNode(node);
    }
  }

  /**
   * 翻译元素的 placeholder / title / aria-label 属性
   * @param {Element} element - DOM 元素
   */
  function translateAttributes(element) {
    if (!element || !element.getAttribute) return;

    var attrs = ['placeholder', 'title', 'aria-label'];
    attrs.forEach(function (attr) {
      var value = element.getAttribute(attr);
      if (!value) return;

      var translated = translateText(value);
      if (translated !== value) {
        element.setAttribute(attr, translated);
      }
    });
  }

  /**
   * 翻译元素及其子树的所有属性
   * @param {Element} root - 遍历起点
   */
  function translateAllAttributes(root) {
    if (!root || !root.querySelectorAll) return;

    var elements = root.querySelectorAll('[placeholder], [title], [aria-label]');
    elements.forEach(function (el) {
      translateAttributes(el);
    });
  }

  // ============================================================
  // 全页翻译
  // ============================================================

  /**
   * 翻译整个页面（文本节点 + 属性）
   */
  function translatePage() {
    if (isTranslating) return;
    isTranslating = true;

    try {
      translateDOM(document.body);
      translateAllAttributes(document.body);
    } catch (e) {
      // 静默降级
    } finally {
      isTranslating = false;
    }
  }

  // ============================================================
  // MutationObserver — 监听 DOM 变化实时翻译
  // ============================================================

  /**
   * 启动 MutationObserver 监听 DOM 变化
   */
  function startObserver() {
    if (observer) return;
    if (!window.MutationObserver) return;

    observer = new MutationObserver(function (mutations) {
      if (isTranslating) return;

      mutations.forEach(function (mutation) {
        // 新增节点
        if (mutation.addedNodes && mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType === Node.TEXT_NODE) {
              translateTextNode(node);
              return;
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
              translateDOM(node);
              translateAttributes(node);
              translateAllAttributes(node);
            }
          });
        }

        // 文本内容变化
        if (mutation.type === 'characterData' && mutation.target) {
          translateTextNode(mutation.target);
        }
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  /**
   * 停止 MutationObserver
   */
  function stopObserver() {
    if (!observer) return;
    observer.disconnect();
    observer = null;
  }

  // ============================================================
  // 语言切换
  // ============================================================

  /**
   * 切换语言并重新翻译页面
   * @param {string} lang - 目标语言 'zh' | 'en'
   */
  function switchLanguage(lang) {
    if (lang !== 'zh' && lang !== 'en') return;
    if (lang === currentLang) return;

    currentLang = lang;

    // 暂停 observer 避免翻译过程中触发循环
    stopObserver();
    translatePage();
    startObserver();
  }

  // ============================================================
  // postMessage 监听 — 接收语言切换指令
  // ============================================================

  /**
   * 验证并处理来自问视间平台的语言切换消息
   * @param {MessageEvent} event - postMessage 事件
   */
  function handleMessage(event) {
    // 防御性校验：消息数据必须存在
    if (!event || !event.data) return;

    var data = event.data;

    // 校验消息结构
    if (data.type !== 'setLanguage') return;
    if (data.source !== 'superinsight') return;
    if (data.lang !== 'zh' && data.lang !== 'en') return;

    switchLanguage(data.lang);
  }

  // ============================================================
  // 初始化
  // ============================================================

  /**
   * 从 URL 参数读取初始语言设置
   * @returns {string} 'zh' | 'en'
   */
  function getInitialLang() {
    try {
      var params = new URLSearchParams(window.location.search);
      var lang = params.get('lang');
      if (lang === 'en') return 'en';
    } catch (e) {
      // URLSearchParams 不可用时静默降级
    }
    return 'zh';
  }

  /**
   * 脚本入口 — 初始化翻译系统
   */
  function init() {
    currentLang = getInitialLang();

    // 等待 DOM 就绪后开始翻译
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        translatePage();
        startObserver();
      });
    } else {
      translatePage();
      startObserver();
    }

    // 监听语言切换消息
    window.addEventListener('message', handleMessage);
  }

  // ============================================================
  // 导出供测试使用（仅在 Node.js / 测试环境下）
  // ============================================================
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      translateText: translateText,
      switchLanguage: switchLanguage,
      getCurrentLang: function () { return currentLang; },
      TRANSLATIONS: TRANSLATIONS,
      REVERSE_TRANSLATIONS: REVERSE_TRANSLATIONS,
      _setLang: function (lang) { currentLang = lang; }
    };
  }

  // 启动
  try {
    init();
  } catch (e) {
    // 静默降级 — 翻译失败不影响标注功能
  }
})();
