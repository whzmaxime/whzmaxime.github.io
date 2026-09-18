# R7：先看新版，再启用自动更新

1. 下载 Sam-Ge-Webpage-R7.html，在 Chrome / Edge 中打开。Research 第一项默认展开；五个主题均可点击，合计 15 个论文条目。
2. 如要每天自动更新，将完整源码包解压后，把其中的文件直接放在 GitHub 仓库根目录。必须包含 .github/workflows/pages.yml；不要只上传 HTML。
3. 在 GitHub 仓库 Settings → Secrets and variables → Actions 添加 Repository secret，名称为 SERPAPI_API_KEY，值为您在 SerpApi 账户中的 API Key。不要把密钥发给他人或放入网页。
4. 在 Settings → Pages → Source 选择 GitHub Actions。
5. 在 Actions 选择 Update Scholar and publish Pages，点击 Run workflow。首次成功后，网页的总引用数、h-index 和匹配成功的 9 篇 Selected Publications 引用数会显示真实抓取结果。
6. 此后每天新加坡时间 09:23 计划更新，GitHub 可能延迟。访客打开网页会读取最近一次同步的数据，不需要本地电脑运行。

当前未提供密钥，也未执行线上部署。HTML 预览的动态数字显示“—”，Biography 的 70,000+ / 126 是指定的 March 2026 历史正文。单独双击离线 HTML 不会运行服务器端抓取。真实更新时间显示在同步后的网页和数字的鼠标提示中。

如工作流失败，把失败步骤或仓库链接发来即可，不需要发送密钥。README 内含详细排错说明。
