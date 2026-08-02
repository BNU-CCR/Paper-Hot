import { AppSidebar } from "../../components/app-sidebar";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";

export default function AboutPage() {
  return <div className="shell"><AppSidebar activePath="/about/" /><main className="main about-page"><section className="hero"><h1>为计算传播研究保留一条可追溯的新论文脉络。</h1><p>Paper HOT 从团队红榜期刊抓取更新，经过 AI 辅助筛选后，提供精选论文、摘要、主题标签与推荐理由。</p><a className="primary-link" href={GITHUB_URL} target="_blank" rel="noreferrer">在 GitHub 查看项目 ↗</a></section><section className="about-grid"><article><h2>数据如何更新</h2><p>期刊数据按周抓取、去重并导出。GitHub Actions 每周一北京时间 13:00 自动运行，更新完成后同步发布网页。</p></article><article><h2>如何使用</h2><p>从精选或期刊全量开始，按相关性、期刊、主题和关键词缩小范围；点击论文标题即可打开原文。</p></article><article><h2>开源协作</h2><p>项目代码、自动化流程和公开数据均可在 GitHub 查看。欢迎通过 issue 或 pull request 提供建议。</p></article></section></main></div>;
}
