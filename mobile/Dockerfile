# =========================================================
# MARAMARA Mobile - Expo Web build (for Railway "frontend")
# =========================================================
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .

# Export static web bundle to ./dist
RUN npx expo export --platform web --output-dir dist

# --- Runtime stage: serve static files ---
FROM node:20-alpine AS runtime

WORKDIR /app
RUN npm install -g serve

COPY --from=build /app/dist ./dist

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "serve -s dist -l ${PORT}"]
