FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port (Vite default)
EXPOSE 5173

# Run dev server accessible from outside
CMD ["npm", "run", "dev", "--", "--host"]
