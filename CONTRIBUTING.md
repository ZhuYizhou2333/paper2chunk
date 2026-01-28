# 贡献指南

欢迎参与 `paper2chunk` 的开发！本文档给出本地开发环境、测试与提交流程的约定。

## 开发环境（使用 uv）

1) 克隆仓库：
```bash
git clone https://github.com/ZhuYizhou2333/paper2chunk.git
cd paper2chunk
```

2) 创建虚拟环境并安装依赖：
```bash
uv venv
uv sync --group dev
```

3) 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env，按需填入你的 API Key
```

## 运行测试

```bash
uv run pytest
```

（可选）带覆盖率：
```bash
uv run pytest --cov=paper2chunk --cov-report=html
```

## 代码风格

- 遵循 PEP 8
- 优先使用类型提示
- 公共函数/类需要 docstring
- 函数保持单一职责，避免过长

## 提交流程

```bash
git checkout -b feature/your-feature-name
uv run pytest
git add .
git commit -m "你的提交说明"
git push origin feature/your-feature-name
```

