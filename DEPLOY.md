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
