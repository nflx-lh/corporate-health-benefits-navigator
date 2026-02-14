FROM node:20-alpine

WORKDIR /app

# Copy only dependency manifests first for better layer caching
COPY package*.json ./

# Use npm ci when lockfile exists; fallback to npm install otherwise
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy app source
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
