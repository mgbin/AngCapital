# Ang Capital Research Website

这是一个基于 FastAPI + MySQL 的 Ang Capital 研报发布网站脚手架，包含：

- 首页研报展示
- 研报详情页
- 简单后台登录与发布入口
- SQLAlchemy 数据模型
- 自动初始化数据库表与示例研报

## 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
cp .env.example .env
```

然后按你的 MySQL 实际配置修改 `.env`，至少确保数据库已提前创建：

```sql
CREATE DATABASE ang_capital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 3. 启动项目

```bash
uvicorn app.main:app --reload
```

打开：

- 前台首页: `http://127.0.0.1:8000/`
- 后台登录: `http://127.0.0.1:8000/admin/login`
- 正式网站地址: `https://www.ang-capital.com`

## 4. 默认后台账号

- 用户名: `.env` 里的 `ADMIN_USERNAME`
- 密码: `.env` 里的 `ADMIN_PASSWORD`

## 5. 项目结构

```text
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  crud.py
  routers/
  templates/
  static/
```

## 6. 下一步建议

- 接入真正的管理员用户表，而不是使用环境变量账号
- 增加 PDF 文件上传和对象存储
- 增加研报搜索、标签、分页
- 增加 Alembic 数据库迁移
