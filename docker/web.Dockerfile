# 开发阶段
FROM node:24-alpine AS development
WORKDIR /app
ENV TZ=Asia/Shanghai

# 安装 pnpm
RUN npm install -g pnpm@latest

# 复制 package.json 和 pnpm-lock.yaml
COPY ./web/package*.json ./
COPY ./web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --registry=https://registry.npmmirror.com

# pnpm 10 默认拦截非安全依赖的 build script（esbuild/core-js），会导致
# vite 启动报错“esbuild 二进制缺失”。显式 rebuild 触发其 postinstall 生成原生二进制。
RUN pnpm rebuild esbuild core-js

# 复制源代码
COPY ./web .

# 暴露端口
EXPOSE 5173

# 启动开发服务器的命令在 docker-compose 文件中定义

# 生产阶段
FROM node:24-alpine AS build-stage
WORKDIR /app

# 安装 pnpm
RUN npm install -g pnpm@latest

# 复制依赖文件
COPY ./web/package*.json ./
COPY ./web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile --registry=https://registry.npmmirror.com

# pnpm 10 拦截 build script，显式 rebuild 触发 esbuild/core-js 原生二进制生成
RUN pnpm rebuild esbuild core-js

# 复制源代码并构建
COPY ./web .
RUN pnpm run build

# 生产环境运行阶段
FROM nginx:alpine AS production
COPY --from=build-stage /app/dist /usr/share/nginx/html
RUN find /usr/share/nginx/html -type d -exec chmod 755 {} \; \
    && find /usr/share/nginx/html -type f -exec chmod 644 {} \;
COPY ./docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./docker/nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
