FROM node:18-alpine as build

WORKDIR /app

ARG REACT_APP_CONTENT_API_URL
ENV REACT_APP_CONTENT_API_URL=$REACT_APP_CONTENT_API_URL

COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
