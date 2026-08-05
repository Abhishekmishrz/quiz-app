FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# docker-compose overrides this CMD (bind-mounting ./frontend over /app and
# running `npm run dev -- --host`), so this default is only used for a
# standalone `docker build && docker run` (e.g. a Vercel-adjacent deploy).
CMD ["npm", "run", "dev", "--", "--host"]
