# syntax=docker/dockerfile:1

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci || npm i
COPY . .
# 构建时将 API 指向同源反代 /，WS 由 nginx 反代同源
ENV VITE_API_BASE_URL=/
ENV VITE_WS_BASE_URL=
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx","-g","daemon off;"]


