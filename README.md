# R7 — 17 September 2026

打开独立文件 `Sam-Ge-Webpage-R7.html` 检查新版；下载后使用浏览器打开，避免与旧的同名文件混淆。第一项研究主题默认展开。

# Sam Ge personal webpage

## 本版内容

- 指标名称为 Google Scholar citations；Biography 在 an h-index of 126 后增加 as of March 2026。
- Research 分为指定的五个主题，每个主题可点击展开 3 篇代表论文（共 15 个条目、13 篇不同论文，交叉主题允许重复）。题名、Ge 作者身份与 DOI 经出版社提交的 Crossref 记录核对；基础论文也参考所提供的 Top 12 清单。
- `research-papers.json` 记录本轮论文选题，供下轮调整。网页已内嵌列表，调整该 JSON 后还需同步编辑 HTML。
- Projects 保留 AISG SRS、MR2、Social Robots、INPACE，扩充研究问题和方法，配有带出处的项目图。Adam 合影保留原材料照片；MR2 展示模块、组装与实物；INPACE 改用官方 2025 年会议合影。
- 其他栏目及 Selected Publications 的说明文字保持不变。

## 推荐：GitHub Pages + GitHub Actions 自动更新

无需每次在电脑上运行 Python，也无需电脑常开。GitHub 在服务器上每天获取一次 Google Scholar 数据并发布网页。访客打开网页时，页面读取同站点的 `scholar.json`。这是“定时同步 + 访问时读取”，不是每个访客都触发外部抓取。

单独把 HTML 上传到 GitHub Pages 不会执行 Python，也不能安全保存私密 API Key。真正按访问触发抓取需要额外的后端接口，例如带缓存的 Serverless 服务。本包使用 GitHub Actions 定时方案。

### 一次性配置步骤

1. 在 GitHub 创建网站仓库。个人主页通常命名为 `你的用户名.github.io`；普通项目仓库也可以。工作流会使用仓库的默认分支。
2. 完整解压本包，将包内文件放入仓库根目录。`dist/`、`preview.py`、`update_scholar.py`、`publications.json` 和 `.github/workflows/pages.yml` 应在对应根目录位置；不要再套一层 `Sam-Ge-Webpage/`。上传完整文件树，不能只上传 HTML 或 ZIP。
3. 在仓库 **Settings → Secrets and variables → Actions → New repository secret** 新建：
   - Name：`SERPAPI_API_KEY`
   - Secret：您的 SerpApi API Key
   - 不要把真实密钥写入源码、网页或提交到仓库。`scholar-config.example.json` 是空模板；不需要为 GitHub 创建本地密钥文件。
4. 在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
5. 在 **Actions** 页面选择 **Update Scholar and publish Pages**，点击 **Run workflow**，选择默认分支运行。如果此前推送时尚未设置密钥、导致第一次运行失败，配置后重新运行即可。
6. 等待运行成功。网站链接可在 **Settings → Pages** 或该 workflow 的 deployment 结果中查看。页面会显示实际更新日期，引用数字的鼠标提示显示各自的取数时间。

本版自动识别默认分支，无需修改 main/master。工作流文件必须存在于默认分支；首次上传配置可能触发运行，但请完成密钥和 Pages 设置后再检查结果。

### 自动更新频率与运行边界

- 当前计划每天 UTC 01:23（新加坡时间 09:23）运行；GitHub 的定时任务可能延迟，不能保证精确到分钟。
- 每次推送到默认分支 或手动 Run workflow 也会尝试同步。
- 每轮最多 3 次 SerpApi 查询；访客浏览或刷新网页只读取公开 JSON，不消耗新的 SerpApi 查询额度。接口请求设置 no_cache=true，要求 SerpApi 重新抓取；Google Scholar 自身的统计更新仍有时间差。
- GitHub 的公开仓库连续 60 天没有活动时，定时工作流可能被自动停用。届时在 Actions 中重新启用；定期检查运行状态和账户额度。
- 取数失败会使本轮工作流停止发布，原来已发布的网页继续提供服务。未配置密钥时，不会假装完成首次同步。
- 尝试从已发布网站读取上一份数据；精确匹配不到的论文保留可用的原引用数和原时间，不猜测相近标题。若无法读取上一版，则只能使用包内的材料基线数据。
- 总引用数和 h-index 的显示日期不代表所有论文都在同一轮匹配成功；逐篇真实数据时间见鼠标提示。
- 部署只上传 `dist/`，不上传配置、脚本或材料。Actions 生成的数据保存在部署产物中，不会自动回写到源代码仓库。

## 初始数据与真实同步状态

当前尚无有效密钥或目标 GitHub 仓库，因此没有进行真实 API 联调，也没有运行线上部署。R7 移除了动态指标中的材料基线数值，首次成功同步前显示“—”。Biography 中的历史数据按要求保留，并注明 as of March 2026。

自动同步成功后，总引用数、h-index 和匹配成功论文的引用数会更新。工作流也会把新数字写进发布的 HTML。Biography 中的 70,000+ / 126 是指定正文，明确标注 as of March 2026，保持固定。

## 如果数字仍然不更新

1. **双击 HTML 打开**：这是离线预览，没有后台，不会自动抓取。请在完成一次性配置后的 GitHub Pages 地址查看。
2. **只上传了 HTML**：必须上传完整文件树，包括 `.github/workflows/pages.yml`，然后把 Pages Source 设为 GitHub Actions。
3. **Actions 运行失败**：打开最近一次 `Update Scholar and publish Pages`。本版会分别提示缺失密钥、密钥被拒绝、额度/速率限制或网络错误；不输出真实密钥。
4. **工作流成功但某篇未变化**：看运行页面的 Summary → Google Scholar synchronization。这里逐篇列出是否匹配和本次引用数。相同数值也可能是 Scholar 确实没有新增引用；取数时间可以区分“没有新增”与“没有运行”。
5. **总数变了、论文没变**：Summary 会指出未匹配的标题；未匹配论文保留旧数与原日期，不会假装实时。全部论文均未匹配时，本轮停止发布以提示检查。
6. **确认已发布数据**：在网站地址后加 `scholar.json`（项目仓库须保留仓库路径）。`fetched_at: null` 表示仍是本包基线；真实同步成功后它应为时间戳，论文条目也有各自的时间戳。

这次没有目标仓库地址或实际 API Key，因而只验证了离线逻辑和网页数据更新路径，没有完成真实 SerpApi 联调或线上部署。若已配置但仍失败，请提供 GitHub 仓库/网页地址和失败步骤；不需要提供密钥。

## 本地预览（可选）

直接打开 `dist/index.html` 可查看排版，头像和研究图片均已内嵌。
如需在本地进行真实同步，仍可使用 Python 3.10+：复制 `scholar-config.example.json` 为 `scholar-config.json`，填入密钥，在该目录运行 `py preview.py`（macOS/Linux 可用 `python3 preview.py`），然后打开终端显示的本地地址。此本地方式只有在程序运行时才更新；GitHub 托管方案不依赖本地程序。

运行离线逻辑测试：`python -m unittest test_scholar.py`。这些测试使用模拟数据，不会请求 SerpApi。

## 依据与参考

- GitHub Pages 静态托管：https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Pages 工作流部署：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- 定时任务限制：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- Actions Secrets：https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- SerpApi 作者指标接口：https://serpapi.com/google-scholar-author-api

本包不包含 CV、提名表或研究 PDF 原件。本次没有公开发布。
