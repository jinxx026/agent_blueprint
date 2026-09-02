# Streamlit 企业控制台

这个目录是 AgentBlueprint 的轻量前端，直接调用 FastAPI，不保存企业密钥或租户身份。

## 文件说明

- `app.py`：应用入口、侧栏导航、后端地址和全局样式。
- `api_client.py`：统一发送 HTTP 请求，把后端错误转换成用户能读懂的提示。
- `views/dashboard.py`：产品总览和完整运行链路。
- `views/modules.py`：业务模块选择与模块级 RAG 参数配置。
- `views/knowledge.py`：企业知识文本导入和角色权限设置。
- `views/blueprints.py`：Blueprint YAML 编辑、校验、编译和版本保存。
- `views/evaluations.py`：门禁测试、历史结果和受控发布。
- `views/security.py`：当前组织身份和生产安全边界说明。
- `requirements.txt`：Streamlit Cloud 安装前端所需依赖的入口。
- `../.streamlit/config.toml`：仓库级颜色、主题和服务设置，不存放秘密。

从仓库根目录运行 `scripts/dev.ps1`（Windows）或 `scripts/dev.sh`（macOS/Linux），然后访问 `http://localhost:8501`。

## 部署到 Streamlit Community Cloud

主文件路径填写 `frontend/app.py`，Python 选择 3.12。在应用的 Secrets 中填写：

```toml
API_BASE_URL = "https://你的后端域名/api/v1"
```

未配置 `API_BASE_URL` 时，应用使用内置演示后端，不需要单独启动 Uvicorn；它使用开发身份和临时 SQLite，适合在线演示，不适合保存正式企业数据。

生产环境必须部署独立 FastAPI、持久数据库和正式 OIDC/SSO，再通过 `API_BASE_URL` 切换到企业后端。
