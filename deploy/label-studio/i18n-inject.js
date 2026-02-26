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
    // ================================================================
    // 品牌
    // ================================================================
    'Label Studio': '问视间',
    'Label Studio Community': '问视间社区版',

    // ================================================================
    // 侧边栏导航
    // ================================================================
    'Home': '首页',
    'Projects': '项目',
    'Organization': '组织',
    'Pin menu': '固定菜单',
    'Unpin menu': '取消固定',

    // 侧边栏底部链接（将通过 CSS 隐藏，翻译作为备用）
    'API': 'API',
    'Documentation': '文档',
    'Docs': '文档',
    'GitHub': 'GitHub',
    'Slack Community': '社区',

    // ================================================================
    // 顶部导航与用户菜单
    // ================================================================
    'Data Manager': '数据管理',
    'Settings': '设置',
    'Dashboard': '仪表盘',
    'Members': '成员',
    'Account & Settings': '账户与设置',
    'Account': '账户',
    'Sign Out': '退出登录',
    'Log out': '退出登录',
    'Notifications': '通知',

    // ================================================================
    // 项目管理
    // ================================================================
    'Create': '创建',
    'Create Project': '创建项目',
    'Delete Project': '删除项目',
    'Duplicate Project': '复制项目',
    'Project Name': '项目名称',
    'Enter project name': '输入项目名称',
    'Enter description': '输入描述',
    'No projects yet': '暂无项目',
    'Create your first project': '创建你的第一个项目',

    // ================================================================
    // 项目设置页面
    // ================================================================
    'General': '常规',
    'Labeling Interface': '标注界面',
    'Instructions': '说明',
    'Machine Learning': '机器学习',
    'Cloud Storage': '云存储',
    'Webhooks': '网络钩子',
    'Danger Zone': '危险区域',
    'Annotation': '标注',
    'Quality': '质量',
    'Members': '成员',

    // 常规设置
    'Project Description': '项目描述',
    'Color': '颜色',
    'Task Sampling': '任务采样',
    'Sequential sampling': '顺序采样',
    'Uniform sampling': '均匀采样',
    'Uncertainty sampling': '不确定性采样',

    // 标注界面设置
    'Labeling Config': '标注配置',
    'Visual': '可视化',
    'Code': '代码',
    'Preview': '预览',
    'Save': '保存',
    'Validate': '验证',
    'Config is valid': '配置有效',
    'Templates': '模板',
    'Custom template': '自定义模板',

    // 标注说明
    'Show before labeling': '标注前显示',
    'Show at the top of the labeling area': '在标注区域顶部显示',

    // 机器学习设置
    'Add Model': '添加模型',
    'Connect Model': '连接模型',
    'URL': '地址',
    'Name': '名称',
    'Description': '描述',
    'Start model training on annotation submission': '提交标注时开始模型训练',
    'Retrieve predictions when loading a task': '加载任务时获取预测',
    'Interactive preannotations': '交互式预标注',
    'No models connected': '未连接模型',

    // 云存储设置
    'Source Cloud Storage': '源云存储',
    'Target Cloud Storage': '目标云存储',
    'Add Source Storage': '添加源存储',
    'Add Target Storage': '添加目标存储',
    'Sync Storage': '同步存储',
    'Storage Type': '存储类型',
    'Bucket Name': '存储桶名称',
    'Prefix': '前缀',
    'Use pre-signed URLs': '使用预签名 URL',
    'Treat every bucket object as a source file': '将每个存储桶对象视为源文件',

    // 危险区域
    'Delete this project': '删除此项目',
    'Once you delete a project, there is no going back.': '项目一旦删除，将无法恢复。',
    'Are you sure you want to delete this project?': '确定要删除此项目吗？',
    'Type project name to confirm': '输入项目名称以确认',

    // ================================================================
    // 数据管理器（Data Manager）
    // ================================================================
    'Label All Tasks': '标注所有任务',
    'Label': '标注',
    'Filters': '筛选',
    'Order by': '排序',

    // 数据管理器表头
    'ID': 'ID',
    'Status': '状态',
    'Annotator': '标注员',
    'Annotated by': '标注者',
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
    'Agreement': '一致性',
    'Reviewers': '审核员',
    'Reviews': '审核',
    'Ground Truth': '标准答案',
    'Submitted annotations': '已提交标注',
    'Inner id': '内部 ID',

    // 数据管理器操作
    'Select All': '全选',
    'Select all tasks': '选择所有任务',
    'Selected': '已选择',
    'Delete Tasks': '删除任务',
    'Delete Annotations': '删除标注',
    'Retrieve Predictions': '获取预测',
    'Assign Annotators': '分配标注员',

    // 数据管理器视图
    'List': '列表',
    'Grid': '网格',
    'Tabs': '标签页',
    'Add Tab': '添加标签页',
    'Rename Tab': '重命名标签页',
    'Delete Tab': '删除标签页',
    'Default': '默认',

    // ================================================================
    // 筛选与排序
    // ================================================================
    'Filter': '筛选',
    'Add Filter': '添加筛选',
    'Sort': '排序',
    'Columns': '列',
    'Order': '排序',
    'Search': '搜索',
    'contains': '包含',
    'not contains': '不包含',
    'equal': '等于',
    'not equal': '不等于',
    'is empty': '为空',
    'is not empty': '不为空',
    'greater than': '大于',
    'less than': '小于',
    'greater or equal': '大于等于',
    'less or equal': '小于等于',
    'in': '在范围内',
    'not in': '不在范围内',
    'between': '介于',
    'Ascending': '升序',
    'Descending': '降序',

    // ================================================================
    // 数据导入导出
    // ================================================================
    'Import': '导入',
    'Export': '导出',
    'Upload Files': '上传文件',
    'Upload': '上传',
    'Drag and drop files here': '拖拽文件到此处',
    'or click to browse': '或点击浏览',
    'Supported formats': '支持的格式',
    'Import Tasks': '导入任务',
    'Export Annotations': '导出标注',
    'Export Format': '导出格式',
    'JSON': 'JSON',
    'JSON-MIN': 'JSON-MIN',
    'CSV': 'CSV',
    'TSV': 'TSV',
    'COCO': 'COCO',
    'VOC': 'VOC',
    'YOLO': 'YOLO',
    'Brush labels to instance': '画笔标签转实例',
    'Download': '下载',

    // ================================================================
    // 标注界面
    // ================================================================
    'Submit': '提交',
    'Skip': '跳过',
    'Update': '更新',
    'Cancel': '取消',
    'Delete': '删除',
    'Accept': '接受',
    'Reject': '拒绝',
    'Fix + Accept': '修正并接受',

    // 标注面板
    'Regions': '区域',
    'Relations': '关系',
    'History': '历史',
    'Results': '结果',
    'Details': '详情',
    'Selection': '选择',
    'No region selected': '未选择区域',
    'Select a region to see its details': '选择一个区域查看详情',
    'No regions yet': '暂无区域',
    'Click on the image to create a region': '点击图片创建区域',

    // 标注工具
    'Undo': '撤销',
    'Redo': '重做',
    'Reset': '重置',
    'Zoom In': '放大',
    'Zoom Out': '缩小',
    'Fit': '适应',
    'Rotate Left': '向左旋转',
    'Rotate Right': '向右旋转',
    'Brightness': '亮度',
    'Contrast': '对比度',
    'Selection tool': '选择工具',
    'Pan tool': '平移工具',
    'Zoom tool': '缩放工具',
    'Move': '移动',
    'Eraser': '橡皮擦',
    'Brush': '画笔',
    'Rectangle': '矩形',
    'Ellipse': '椭圆',
    'Polygon': '多边形',
    'Polyline': '折线',
    'Point': '点',
    'KeyPoint': '关键点',

    // 标注类型标签
    'Labels': '标签',
    'Choices': '选项',
    'TextArea': '文本区域',
    'Rating': '评分',
    'Taxonomy': '分类',
    'DateTime': '日期时间',
    'Number': '数字',
    'Pairwise': '成对比较',
    'Ranker': '排序器',

    // 标注状态
    'In Progress': '进行中',
    'Skipped': '已跳过',
    'Submitted': '已提交',
    'Draft': '草稿',
    'Fixed and accepted': '已修正并接受',
    'Accepted': '已接受',
    'Rejected': '已拒绝',
    'Pending review': '待审核',

    // 标注导航
    'Next': '下一个',
    'Previous': '上一个',
    'Task': '任务',
    'of': '/',

    // ================================================================
    // 审核流程
    // ================================================================
    'Review': '审核',
    'Reviewed': '已审核',
    'Not reviewed': '未审核',
    'Approve': '批准',
    'Approve All': '全部批准',
    'Reject All': '全部拒绝',
    'Send back': '退回',

    // ================================================================
    // 用户与组织管理
    // ================================================================
    'Email': '邮箱',
    'Password': '密码',
    'First Name': '名',
    'Last Name': '姓',
    'Username': '用户名',
    'Role': '角色',
    'Active': '活跃',
    'Last Activity': '最后活动',
    'Created': '创建时间',
    'Invite People': '邀请成员',
    'Invite Link': '邀请链接',
    'Copy Link': '复制链接',
    'Copied!': '已复制！',
    'Invite Members': '邀请成员',
    'Remove Member': '移除成员',
    'Change Role': '更改角色',
    'Administrator': '管理员',
    'Manager': '管理者',
    'Reviewer': '审核员',
    'Annotator': '标注员',
    'Not Activated': '未激活',
    'Deactivated': '已停用',

    // 个人设置
    'Personal Token': '个人令牌',
    'Access Token': '访问令牌',
    'Copy token': '复制令牌',
    'Reset token': '重置令牌',
    'Your token': '你的令牌',

    // ================================================================
    // 通用按钮与操作
    // ================================================================
    'OK': '确定',
    'Confirm': '确认',
    'Close': '关闭',
    'Back': '返回',
    'Apply': '应用',
    'Clear': '清除',
    'Clear All': '全部清除',
    'Refresh': '刷新',
    'Reload': '重新加载',
    'Retry': '重试',
    'Edit': '编辑',
    'Copy': '复制',
    'Duplicate': '复制',
    'Rename': '重命名',
    'Move': '移动',
    'Add': '添加',
    'Remove': '移除',
    'Enable': '启用',
    'Disable': '禁用',
    'Show': '显示',
    'Hide': '隐藏',
    'Expand': '展开',
    'Collapse': '折叠',
    'More': '更多',
    'Less': '更少',
    'All': '全部',
    'None': '无',
    'Yes': '是',
    'No': '否',
    'On': '开',
    'Off': '关',
    'Select': '选择',
    'Select all': '全选',
    'Deselect all': '取消全选',

    // ================================================================
    // 表单标签
    // ================================================================
    'Title': '标题',
    'Type': '类型',
    'Value': '值',
    'Required': '必填',
    'Optional': '可选',

    // ================================================================
    // 提示与状态信息
    // ================================================================
    'Loading...': '加载中...',
    'Saving...': '保存中...',
    'Submitting...': '提交中...',
    'Processing...': '处理中...',
    'Uploading...': '上传中...',
    'Deleting...': '删除中...',
    'Connecting...': '连接中...',
    'Syncing...': '同步中...',
    'No results': '无结果',
    'No data': '暂无数据',
    'No tasks': '暂无任务',
    'No annotations': '暂无标注',
    'No predictions': '暂无预测',
    'No members': '暂无成员',
    'Are you sure?': '确定吗？',
    'Something went wrong': '出现错误',
    'Page not found': '页面未找到',
    'Access denied': '访问被拒绝',
    'Not found': '未找到',
    'Error': '错误',
    'Warning': '警告',
    'Success': '成功',
    'Info': '信息',

    // 成功消息
    'Project created successfully': '项目创建成功',
    'Project deleted successfully': '项目删除成功',
    'Settings saved successfully': '设置保存成功',
    'Annotation submitted successfully': '标注提交成功',
    'Tasks imported successfully': '任务导入成功',
    'Tasks deleted successfully': '任务删除成功',

    // ================================================================
    // 分页
    // ================================================================
    'per page': '每页',
    'Showing': '显示',
    'items': '项',
    'First': '首页',
    'Last': '末页',

    // ================================================================
    // 时间相关
    // ================================================================
    'Today': '今天',
    'Yesterday': '昨天',
    'Last 7 days': '最近 7 天',
    'Last 30 days': '最近 30 天',
    'ago': '前',
    'just now': '刚刚',
    'seconds': '秒',
    'minutes': '分钟',
    'hours': '小时',
    'days': '天',

    // ================================================================
    // 快捷键提示
    // ================================================================
    'Keyboard shortcuts': '键盘快捷键',
    'Hotkeys': '快捷键',
    'Press': '按下',
    'to submit': '提交',
    'to skip': '跳过',
    'to undo': '撤销',
    'to redo': '重做'
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
      hideSidebarFooter();
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
              hideSidebarFooter();
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

  // ============================================================
  // 侧边栏底部隐藏 — CSS 的 JS 补充方案
  // ============================================================

  /**
   * 隐藏侧边栏底部外部链接和版本号
   * 作为 CSS 隐藏规则的防御性补充
   */
  function hideSidebarFooter() {
    try {
      // 侧边栏底部区域
      var selectors = [
        '[class*="sidebar"] [class*="footer"]',
        '[class*="sidebar"] [class*="version"]',
        '[class*="sidebar"] a[href*="github"]',
        '[class*="sidebar"] a[href*="slack"]',
        '[class*="sidebar"] a[href*="community"]'
      ];

      selectors.forEach(function (sel) {
        var els = document.querySelectorAll(sel);
        els.forEach(function (el) {
          if (el) el.style.display = 'none';
        });
      });
    } catch (e) {
      // 静默降级
    }
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
