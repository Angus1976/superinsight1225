/**
 * 问视间 — Label Studio 中文翻译 & 品牌替换
 *
 * 设计原则：
 * - 所有替换基于文本内容匹配，不依赖 LS 内部 CSS 类名 → 升级安全
 * - MutationObserver 实时翻译 React SPA 动态渲染的内容
 * - 加载失败静默降级，不影响标注功能
 */
(function () {
  'use strict';

  var BRAND = '问视间';

  // ============================================================
  // 翻译词典
  // ============================================================
  var TRANSLATIONS = {
    'Label Studio': BRAND,
    'Label Studio Community': BRAND,
    'Home': '首页',
    'Projects': '项目',
    'Organization': '组织',
    'Pin menu': '固定菜单',
    'Unpin menu': '取消固定',
    'Data Manager': '数据管理',
    'Settings': '设置',
    'Dashboard': '仪表盘',
    'Members': '成员',
    'Account & Settings': '账户与设置',
    'Account': '账户',
    'Sign Out': '退出登录',
    'Log out': '退出登录',
    'Notifications': '通知',
    'Create': '创建',
    'Create Project': '创建项目',
    'Delete Project': '删除项目',
    'Duplicate Project': '复制项目',
    'Project Name': '项目名称',
    'Enter project name': '输入项目名称',
    'Enter description': '输入描述',
    'No projects yet': '暂无项目',
    'Create your first project': '创建你的第一个项目',
    'General': '常规',
    'Labeling Interface': '标注界面',
    'Instructions': '说明',
    'Machine Learning': '机器学习',
    'Cloud Storage': '云存储',
    'Webhooks': '网络钩子',
    'Danger Zone': '危险区域',
    'Annotation': '标注',
    'Quality': '质量',
    'Project Description': '项目描述',
    'Color': '颜色',
    'Task Sampling': '任务采样',
    'Labeling Config': '标注配置',
    'Visual': '可视化',
    'Code': '代码',
    'Preview': '预览',
    'Save': '保存',
    'Validate': '验证',
    'Templates': '模板',
    'Custom template': '自定义模板',
    'Add Model': '添加模型',
    'Connect Model': '连接模型',
    'Name': '名称',
    'Description': '描述',
    'Source Cloud Storage': '源云存储',
    'Target Cloud Storage': '目标云存储',
    'Add Source Storage': '添加源存储',
    'Add Target Storage': '添加目标存储',
    'Sync Storage': '同步存储',
    'Delete this project': '删除此项目',
    'Label All Tasks': '标注所有任务',
    'Label': '标注',
    'Filters': '筛选',
    'Order by': '排序',
    'ID': 'ID',
    'Status': '状态',
    'Annotator': '标注员',
    'Total Annotations': '标注总数',
    'Total Predictions': '预测总数',
    'Completed': '已完成',
    'Created At': '创建时间',
    'Updated At': '更新时间',
    'Tasks': '任务',
    'Annotations': '标注',
    'Predictions': '预测',
    'Agreement': '一致性',
    'Ground Truth': '标准答案',
    'Select All': '全选',
    'Delete Tasks': '删除任务',
    'Delete Annotations': '删除标注',
    'Retrieve Predictions': '获取预测',
    'Filter': '筛选',
    'Sort': '排序',
    'Columns': '列',
    'Search': '搜索',
    'Ascending': '升序',
    'Descending': '降序',
    'Import': '导入',
    'Export': '导出',
    'Upload Files': '上传文件',
    'Upload': '上传',
    'Download': '下载',
    'Submit': '提交',
    'Skip': '跳过',
    'Update': '更新',
    'Cancel': '取消',
    'Delete': '删除',
    'Accept': '接受',
    'Reject': '拒绝',
    'Regions': '区域',
    'Relations': '关系',
    'History': '历史',
    'Results': '结果',
    'Details': '详情',
    'Undo': '撤销',
    'Redo': '重做',
    'Reset': '重置',
    'Zoom In': '放大',
    'Zoom Out': '缩小',
    'Labels': '标签',
    'Choices': '选项',
    'Rating': '评分',
    'In Progress': '进行中',
    'Skipped': '已跳过',
    'Submitted': '已提交',
    'Draft': '草稿',
    'Next': '下一个',
    'Previous': '上一个',
    'Task': '任务',
    'Review': '审核',
    'Approve': '批准',
    'Email': '邮箱',
    'Password': '密码',
    'First Name': '名',
    'Last Name': '姓',
    'Username': '用户名',
    'Role': '角色',
    'Invite People': '邀请成员',
    'Copy Link': '复制链接',
    'Administrator': '管理员',
    'Manager': '管理者',
    'Reviewer': '审核员',
    'OK': '确定',
    'Confirm': '确认',
    'Close': '关闭',
    'Back': '返回',
    'Apply': '应用',
    'Edit': '编辑',
    'Add': '添加',
    'Remove': '移除',
    'Loading...': '加载中...',
    'Saving...': '保存中...',
    'No results': '无结果',
    'No data': '暂无数据',
    'Error': '错误',
    'Warning': '警告',
    'Success': '成功'
  };

  // 反向词典（zh → en 还原）
  var REVERSE = {};
  Object.keys(TRANSLATIONS).forEach(function (k) { REVERSE[TRANSLATIONS[k]] = k; });

  var currentLang = 'zh';
  var observer = null;
  var busy = false;

  // ============================================================
  // 核心：翻译文本节点
  // ============================================================
  function tr(text) {
    if (!text || typeof text !== 'string') return text;
    var t = text.trim();
    if (!t) return text;
    var dict = currentLang === 'zh' ? TRANSLATIONS : REVERSE;
    return dict[t] !== undefined ? dict[t] : text;
  }

  function trNode(node) {
    if (!node || node.nodeType !== 3 || !node.nodeValue || !node.nodeValue.trim()) return;
    var p = node.parentElement;
    if (!p) return;
    var tag = p.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA' || tag === 'CODE' || tag === 'PRE') return;
    var out = tr(node.nodeValue);
    if (out !== node.nodeValue) node.nodeValue = out;
  }

  function trTree(root) {
    if (!root) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    var n;
    while ((n = w.nextNode())) trNode(n);
  }

  function trAttrs(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('[placeholder],[title],[aria-label]').forEach(function (el) {
      ['placeholder', 'title', 'aria-label'].forEach(function (a) {
        var v = el.getAttribute(a);
        if (v) { var t = tr(v); if (t !== v) el.setAttribute(a, t); }
      });
    });
  }

  // ============================================================
  // 品牌替换 — 基于文本内容，不依赖 CSS 类名
  // ============================================================
  function replaceBrand() {
    try {
      // 1. 所有文本节点中的 "Label Studio"
      var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      var n;
      while ((n = w.nextNode())) {
        if (n.nodeValue && n.nodeValue.indexOf('Label Studio') !== -1) {
          n.nodeValue = n.nodeValue.replace(/Label Studio/g, BRAND);
        }
      }
      // 2. SVG 文本
      document.querySelectorAll('svg text, svg tspan').forEach(function (el) {
        if (el.textContent && el.textContent.indexOf('Label Studio') !== -1) {
          el.textContent = el.textContent.replace(/Label Studio/g, BRAND);
        }
      });
      // 3. img alt
      document.querySelectorAll('img[alt*="Label Studio"]').forEach(function (img) {
        img.alt = img.alt.replace(/Label Studio/gi, BRAND);
      });
      // 4. 侧边栏 SVG logo → 隐藏（CSS 已通过 ::before 注入品牌文字）
      document.querySelectorAll('svg[alt*="Label Studio"], svg.lsf-menu-header__logo, svg[viewBox="0 0 194 30"]').forEach(function (svg) {
        svg.style.display = 'none';
      });
      // 5. 兜底：a[href="/"] 内的 SVG（登录页等）
      document.querySelectorAll('a[href="/"]').forEach(function (link) {
        if (link.getAttribute('data-si')) return;
        var svg = link.querySelector('svg');
        if (!svg) return;
        svg.style.display = 'none';
        if (!link.querySelector('.si-brand-text')) {
          var s = document.createElement('span');
          s.className = 'si-brand-text';
          s.textContent = BRAND;
          link.appendChild(s);
        }
        link.setAttribute('data-si', '1');
      });
    } catch (e) { /* 静默降级 */ }
  }

  // ============================================================
  // 隐藏外部链接 — 基于 href，升级安全
  // ============================================================
  function hideExtLinks() {
    try {
      ['labelstud.io', 'humansignal', 'github.com/HumanSignal', 'slack.labelstud.io'].forEach(function (kw) {
        document.querySelectorAll('a[href*="' + kw + '"]').forEach(function (el) {
          el.style.display = 'none';
        });
      });
    } catch (e) { /* 静默降级 */ }
  }

  // ============================================================
  // 页面标题替换
  // ============================================================
  function patchTitle() {
    if (document.title && document.title.indexOf('Label Studio') !== -1) {
      document.title = document.title.replace(/Label Studio/g, BRAND);
    }
  }

  // ============================================================
  // 全页翻译
  // ============================================================
  function translatePage() {
    if (busy) return;
    busy = true;
    try {
      trTree(document.body);
      trAttrs(document.body);
      replaceBrand();
      hideExtLinks();
      patchTitle();
    } catch (e) { /* 静默降级 */ }
    finally { busy = false; }
  }

  // ============================================================
  // MutationObserver
  // ============================================================
  function startObserver() {
    if (observer || !window.MutationObserver) return;
    observer = new MutationObserver(function (muts) {
      if (busy) return;
      muts.forEach(function (m) {
        if (m.addedNodes && m.addedNodes.length) {
          m.addedNodes.forEach(function (node) {
            if (node.nodeType === 3) { trNode(node); return; }
            if (node.nodeType === 1) {
              trTree(node);
              trAttrs(node);
              replaceBrand();
              hideExtLinks();
            }
          });
        }
        if (m.type === 'characterData' && m.target) trNode(m.target);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  // ============================================================
  // 语言切换 & postMessage
  // ============================================================
  function switchLang(lang) {
    if (lang !== 'zh' && lang !== 'en') return;
    if (lang === currentLang) return;
    currentLang = lang;
    if (observer) { observer.disconnect(); observer = null; }
    translatePage();
    startObserver();
  }

  window.addEventListener('message', function (e) {
    if (!e || !e.data) return;
    if (e.data.type === 'setLanguage' && e.data.source === 'superinsight') {
      switchLang(e.data.lang);
    }
  });

  // ============================================================
  // 初始化
  // ============================================================
  function init() {
    try {
      var p = new URLSearchParams(window.location.search);
      if (p.get('lang') === 'en') currentLang = 'en';
    } catch (e) { /* 降级 */ }

    var run = function () {
      translatePage();
      startObserver();
      // 标题监听
      patchTitle();
      var titleEl = document.querySelector('title');
      if (titleEl && window.MutationObserver) {
        new MutationObserver(patchTitle).observe(titleEl, { childList: true, characterData: true, subtree: true });
      }
      setInterval(patchTitle, 3000);
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', run);
    } else {
      run();
    }
  }

  // 测试导出
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      translateText: tr,
      switchLanguage: switchLang,
      getCurrentLang: function () { return currentLang; },
      TRANSLATIONS: TRANSLATIONS,
      REVERSE_TRANSLATIONS: REVERSE,
      _setLang: function (l) { currentLang = l; }
    };
  }

  try { init(); } catch (e) { /* 静默降级 */ }
})();
