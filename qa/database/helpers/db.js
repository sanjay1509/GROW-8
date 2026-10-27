import mysql from 'mysql2/promise';

export async function withDatabase(callback) {
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number(process.env.DB_PORT || 3307),
    user: process.env.DB_USER || 'grow8',
    password: process.env.DB_PASSWORD || 'change-me',
    database: process.env.DB_NAME || 'grow8',
    connectTimeout: 15_000,
  });
  try {
    return await callback(connection);
  } finally {
    await connection.end();
  }
}
