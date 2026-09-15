# 微信小程序上线清单

- 在 `frontend/project.config.json` 填入自有 AppID，构建时通过 `TARO_APP_API_BASE_URL=https://<domain>/api/v1` 注入已备案 HTTPS 域名。
- 部署后端 Docker 镜像，注入 MySQL、JWT、模型、微信登录及对象存储密钥。
- 先执行 `backend/sql/init_mysql.sql` 和 `backend/sql/migrations/*.sql`，生产启动不自动建表。
- 生产设置 `APP_ENVIRONMENT=production`、`APP_DEBUG=false`、强随机 `JWT_SECRET`、`PLATFORM_STORE=mysql`、`MYSQL_CONNECT_ON_START=true`、`TRAINING_TASK_STORE=redis`、`TRAINING_DOCUMENT_STORE=cos`、`ENABLE_WEB_SEARCH=false` 和精确 `CORS_ORIGINS`。
- 配置合法域名、隐私指引、用户协议、内容安全机制和服务类目。
- 名称、商标、ICP 备案和 AI 内容要求以提交时微信公众平台规则为准。
- 先发布体验版，完成真机、弱网、登录、安全拦截、并发和隐私检查。
- 探活使用 `/api/v1/health`，流量就绪检查使用 `/api/v1/ready`。
