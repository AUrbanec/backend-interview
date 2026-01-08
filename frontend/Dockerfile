FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code (will be synced by Tilt for hot reload)
COPY . .

# Expose port
EXPOSE 5173

# Run the development server with host binding for external access
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

