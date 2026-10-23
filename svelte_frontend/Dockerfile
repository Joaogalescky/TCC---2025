FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev --ignore-scripts

COPY --from=builder /app/build ./build

EXPOSE 3000

ENV NODE_ENV=production
ENV ORIGIN=http://localhost:3000

CMD ["node", "build"]
