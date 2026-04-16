/**
 * 登录后对核心模块做浅层路由烟测（加载主布局与关键容器，不依赖具体文案）。
 */
describe('核心路由烟测', () => {
  const routes: { path: string; note: string }[] = [
    { path: '/dashboard', note: '仪表盘' },
    { path: '/tasks', note: '任务' },
    { path: '/settings', note: '设置' },
    { path: '/billing/overview', note: '计费概览' },
    { path: '/admin/console', note: '管理控制台' },
    { path: '/admin/config', note: '配置中心' },
    { path: '/admin/users', note: '用户管理' },
    { path: '/data-structuring/upload', note: '数据结构化上传' },
    { path: '/augmentation', note: '数据增强' },
    { path: '/quality', note: '质量管理' },
    { path: '/data-sync', note: '数据同步' },
    { path: '/data-lifecycle', note: '数据生命周期' },
    { path: '/security/audit', note: '安全审计' },
    { path: '/license', note: '许可证' },
    { path: '/ls-workspaces', note: 'Label Studio 工作区' },
    { path: '/admin/tenants', note: '租户管理' },
    { path: '/ai-annotation', note: 'AI 标注' },
    { path: '/augmentation/ai-processing', note: 'AI 处理' },
  ]

  it('各路由应能加载主界面（无跳转回登录）', () => {
    cy.login()

    for (const { path } of routes) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', path.split('?')[0])
      cy.get('.ant-layout, .ant-layout-content, [class*="layout"]', { timeout: 25_000 }).should(
        'exist',
      )
      cy.url().should('not.include', '/login')
    }
  })
})
