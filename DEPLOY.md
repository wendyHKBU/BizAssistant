# BizAdvisor 公网部署（不走局域网）

你现在遇到的问题本质是：手机与电脑之间网络互访受限（常见于校园网/访客网/AP隔离）。
继续用 `192.168.x.x:8501` 不稳定，建议直接公网部署。

## 方案A（推荐）：Render 一键部署

前提：有一个 GitHub 仓库。

1. 把本目录代码推到 GitHub（目录内容应包含 `app.py`、`requirements.txt`、`Dockerfile`、`render.yaml`）。
2. 打开 Render 控制台，选择 New + -> Blueprint。
3. 连接你的 GitHub 仓库，选择该仓库。
4. Render 会自动读取 `render.yaml` 与 `Dockerfile`，点击 Deploy。
5. 等待构建完成后，获得公网地址：`https://xxx.onrender.com`。
6. 手机直接访问这个 `https` 地址。

说明：
- 本项目已配置好容器启动命令，无需手改。
- 如后续启用真实AI模式，请在 Render 的 Environment Variables 添加 `ANTHROPIC_API_KEY`。
- 新闻与政策默认使用本土源（中国政府网政策页 + 百度新闻 RSS + 36氪/钛媒体 RSS），无需额外 key。
- 活动默认使用本土活动源（活动行公开活动页），无需额外 key。
- 活动推荐已启用“用户IP + 2小时路程大城市硬过滤”，线下活动会附带时间成本和交通成本估算。
- IP定位依赖请求头（如 `X-Forwarded-For`）和公开地理解析服务（`ipwho.is` / `ipapi.co`），均无需 key。
- 若运行环境无法提供真实用户IP，系统会提示并临时关闭该硬过滤，不影响基础功能。
- 以下两个国际活动 API key 现在是“可选补充源”（不配置也能跑）：
- `EVENTBRITE_API_TOKEN`（Eventbrite Personal OAuth token）
- `TICKETMASTER_API_KEY`（Ticketmaster Discovery API key）
- 若本土源与可选 API 均暂不可用，系统会自动回退到内置活动池并在侧边栏提示。

Render 环境变量填写示例（可选）：

`EVENTBRITE_API_TOKEN=xxxxxxxx`

`TICKETMASTER_API_KEY=xxxxxxxx`

## 方案B：Streamlit Community Cloud

前提：代码在 GitHub 上。

1. 登录 Streamlit Community Cloud。
2. 选择 New app。
3. 选择你的仓库、分支、主文件 `app.py`。
4. 点击 Deploy。
5. 获得 `https://xxx.streamlit.app`，手机直接访问。

## 本地只用于开发，不再用于手机预览

本地命令：

`python3 -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501`

该方式只建议电脑本机调试，不再作为手机展示方案。
