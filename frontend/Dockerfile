ARG NODE_IMAGE=node:20.19.0
ARG NGINX_IMAGE=nginx:stable-alpine

# Build stage
FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS build-stage
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/. .
RUN npm run build

# Production stage
FROM --platform=$TARGETPLATFORM ${NGINX_IMAGE}

# Add our custom nginx config
COPY default.conf /etc/nginx/conf.d/default.conf

COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
