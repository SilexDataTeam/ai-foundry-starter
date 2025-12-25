import path from 'node:path';
import { defineConfig } from 'prisma/config';

function getDatabaseUrl(): string {
  // Support both DATABASE_URL and component-based configuration
  if (process.env.DATABASE_URL) {
    return process.env.DATABASE_URL;
  }

  const { DB_USER, DB_PASSWORD, DB_HOST, DB_NAME } = process.env;
  return `postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}`;
}

export default defineConfig({
  schema: path.join(__dirname, 'schema.prisma'),
  migrate: {
    async url() {
      return getDatabaseUrl();
    },
  },
});
