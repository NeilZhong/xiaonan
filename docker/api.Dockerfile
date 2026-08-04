# 使用轻量级Python基础镜像
FROM python:3.13-slim
# ghcr.io 在部分网络环境下不可达（拉取 astral-sh/uv 镜像会 EOF 失败），
# 改用 pip 从 PyPI 安装 uv（已验证 PyPI 可达）。
RUN pip install --no-cache-dir uv==0.11.26
COPY --from=node:24-slim /usr/local/bin /usr/local/bin
COPY --from=node:24-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node:24-slim /usr/local/include /usr/local/include
COPY --from=node:24-slim /usr/local/share /usr/local/share

# 设置工作目录
WORKDIR /app

# 环境变量设置
ENV TZ=Asia/Shanghai \
    UV_PROJECT_ENVIRONMENT="/usr/local" \
    UV_COMPILE_BYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置 npm 镜像源，为 MCP 和 Skills 安装依赖
RUN npm config set registry https://registry.npmmirror.com --global \
    && npm cache clean --force

# 设置代理和时区，更换镜像源，安装系统依赖 - 合并为一个RUN减少层数
RUN set -ex \
    # (A) 设置时区
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    # (B) 更换为阿里云 Debian 源：
    #     deb.debian.org 的 pool 路径被容器网络透明代理 (198.18.0.63) 返回 502，
    #     实测 mirrors.aliyun.com 可正常下载 .deb，故整体切换。
    && printf 'Types: deb\nURIs: http://mirrors.aliyun.com/debian http://mirrors.cloud.tencent.com/debian http://mirrors.ustc.edu.cn/debian\nSuites: trixie\nComponents: main contrib non-free\n' > /etc/apt/sources.list.d/debian.sources \

    # (C) 安装必要的系统库
    && apt-get update -o Acquire::Retries=5 -o Acquire::Queue-Mode=host \
    && apt-get install -y --no-install-recommends --fix-missing -o Acquire::Retries=5 -o Acquire::Queue-Mode=host \
        curl \
        ffmpeg \
        fonts-liberation \
        fonts-noto-cjk \
        libpq5 \
        libsm6 \
        libxext6 \
    # 注：libreoffice-impress-nogui / libreoffice-writer-nogui 依赖链极长，
    # 首次构建易因个别包缺失拖垮 apt；当前 Phase 2 验证暂不需要文档预览，
    # 后续若需后端生成 PPT/Word 预览再恢复这两行。
    # (D) 清理垃圾，减小体积
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目配置文件
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/.python-version /app/.python-version
COPY backend/uv.lock /app/uv.lock

# 先复制 package 目录，因为 pyproject.toml 中 yuxi = { path = "package", editable = true }
COPY backend/package /app/package

# 如果网络还是不好，可以在后面添加 --index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 去掉 --frozen：本地 uv.lock 可能未与 pyproject 严格对齐，
# 非 frozen 让 uv 自行解析，避免 build 因 lock 不一致直接失败。
RUN uv sync --no-cache --group test --no-dev

# 复制 server 代码
COPY backend/server /app/server
