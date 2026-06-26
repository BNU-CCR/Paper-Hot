# Paper HOT 多阶段路线 TODO

目标：实现一个类似 AI HOT 的计算传播论文情报站，自动追踪期刊论文，AI 筛选总结，公开展示，并定期推送。

## Phase 1: 公开站 V1

- [x] 确认 AI HOT 风格方向：窄侧栏、双主题、时间线、标签、摘要和推荐理由。
- [x] 实现 `web/` 静态前端骨架。
- [x] 读取 `public/data/papers.json` 渲染论文信息流。
- [x] 支持 `High` / `Medium` / 全部筛选。
- [x] 支持标签聚合与标签筛选。
- [x] 支持标题、摘要、作者、期刊、标签搜索。
- [x] 支持 light / system / dark 主题切换。
- [ ] 根据浏览器预览继续微调视觉细节。
- [ ] 用更多真实论文数据验证页面信息密度。

## Phase 2: 真实数据闭环

- [ ] 稳定运行 `search -> filter -> save`。
- [ ] 验证 Claude 筛选结果质量。
- [ ] 验证去重逻辑和重复运行行为。
- [x] 形成 `publish -> export-public -> website refresh` 流程。
- [ ] 将测试论文替换为真实公开论文数据。

## Phase 3: 推送闭环

- [ ] 确定推送渠道：Server 酱、邮件、RSS、飞书或企业微信。
- [ ] 设计每日/每周推送模板。
- [ ] 采集后自动整理 High/Medium 精选。
- [ ] 推送标题、期刊、AI 判断、推荐理由和原文链接。

## Phase 4: 静态部署

- [ ] 选择部署平台：GitHub Pages、Vercel 或 Cloudflare Pages。
- [ ] 配置静态站部署。
- [ ] 验证公开 URL 能读取 `public/data/papers.json`。
- [ ] 明确仓库公开/私有策略。

## Phase 5: 周报与归档

- [ ] 生成 `weekly.json`。
- [ ] 生成 `tags.json`。
- [ ] 实现周报归档页。
- [ ] 实现主题标签页。
- [ ] 增加 RSS / JSON feed。

## Phase 6: 私有后台

- [ ] 设计私有发布管理入口。
- [ ] 支持论文发布/取消发布。
- [ ] 支持编辑摘要、标签、推荐理由。
- [ ] 支持手动调整 score。
- [ ] 支持生成小红书/组会分享卡片。
