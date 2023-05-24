# ---- BUILD STAGE ----
# Start from the latest Node base image
FROM node:16 AS build-env
WORKDIR /app

# Install the requirements
COPY package*.json /app/
RUN npm install --omit dev

# Copy the rest of the code and build (pass the env var to the build script)
COPY . /app
RUN npm run build

# ---- PRODUCTION STAGE ----
# Start from Nginx to serve built static files
FROM nginx:1.19.0-alpine as prod-stage

# Copy static files from builder stage
COPY --from=build-env /app/build /usr/share/nginx/html
COPY --from=build-env /app/setup.sh /app/
COPY nginx.conf /etc/nginx/conf.d/template.conf

# Expose the port (incoming)
EXPOSE 80
RUN chmod +x /app/setup.sh
# Start Nginx
#CMD ["nginx", "-g", "daemon off;"]
# Unfortunately the environment variables aren't known at ENTRYPOINT
#   ---> Pass the entry cmd with docker-compose instead
#CMD ["/bin/sh", "-c", "envsubst < /etc/nginx/conf.d/template.conf > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]

