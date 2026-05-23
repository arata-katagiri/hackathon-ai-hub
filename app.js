require('dotenv').config();

const express = require('express');
const cors = require('cors');

const PORT = Number(process.env.PORT) || 3000;
const API_KEY = process.env.API_KEY || '';

/** @type {Map<string, { available: boolean, confidence?: number, updatedAt: string }>} */
const parkings = new Map();

const app = express();
app.use(cors());
app.use(express.json());

function requireApiKey(req, res, next) {
  if (!API_KEY) {
    return next();
  }
  const key = req.get('X-API-Key');
  if (key !== API_KEY) {
    return res.status(401).json({ error: 'Неверный или отсутствующий X-API-Key' });
  }
  next();
}

function parkingPayload(id, record) {
  return {
    parkingId: id,
    available: record.available,
    confidence: record.confidence ?? null,
    updatedAt: record.updatedAt,
  };
}

/** ИИ-скрипт: обновить статус парковки */
app.put('/api/parkings/:id/status', requireApiKey, (req, res) => {
  const { id } = req.params;
  const { available, confidence } = req.body;

  if (typeof available !== 'boolean') {
    return res.status(400).json({
      error: 'Поле "available" обязательно и должно быть boolean (true — свободна, false — занята)',
    });
  }

  if (confidence !== undefined && (typeof confidence !== 'number' || confidence < 0 || confidence > 1)) {
    return res.status(400).json({
      error: 'Поле "confidence" должно быть числом от 0 до 1',
    });
  }

  const record = {
    available,
    updatedAt: new Date().toISOString(),
  };
  if (confidence !== undefined) {
    record.confidence = confidence;
  }

  parkings.set(id, record);
  res.json(parkingPayload(id, record));
});

/** Мобильное приложение: статус одной парковки */
app.get('/api/parkings/:id/status', (req, res) => {
  const { id } = req.params;
  const record = parkings.get(id);

  if (!record) {
    return res.status(404).json({
      parkingId: id,
      available: null,
      error: 'Данных по этой парковке пока нет',
    });
  }

  res.json(parkingPayload(id, record));
});

/** Мобильное приложение: все известные парковки */
app.get('/api/parkings', (_req, res) => {
  const list = [...parkings.entries()].map(([id, record]) => parkingPayload(id, record));
  res.json({ parkings: list });
});

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.use((_req, res) => {
  res.status(404).json({ error: 'Маршрут не найден' });
});

app.listen(PORT, () => {
  console.log(`Сервер: http://localhost:${PORT}`);
  if (!API_KEY) {
    console.warn('API_KEY не задан — запись статуса доступна без авторизации (только для разработки)');
  }
});
