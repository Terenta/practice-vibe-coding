# Школа Вайбкодеров — лендинг + бэкенд

Интерактивный лендинг, где ребёнок собирает свой первый проект через Claude. Фронтенд раздаётся с **GitHub Pages**, генерация идёт через **Cloudflare Worker** с встроенным API-ключом.

```
vibe-school/
├── docs/               ← корень GitHub Pages (статика)
│   └── index.html
├── worker/             ← Cloudflare Worker-прокси
│   ├── worker.js
│   ├── wrangler.toml
│   └── package.json
└── README.md
```

---

## Как это работает

1. Браузер открывает `index.html` с GitHub Pages.
2. Когда пользователь жмёт «Создать проект», фронт шлёт POST на Worker (`BACKEND_URL/api/claude`).
3. Worker берёт ключ из своего секрета `ANTHROPIC_API_KEY` (или из тела запроса, если юзер ввёл свой) и проксирует в `api.anthropic.com/v1/messages`.
4. Ответ возвращается в браузер, HTML рендерится в iframe.

Поле «API ключ» в шапке — **необязательное**. Встроенный ключ в Worker'е используется по умолчанию.

---

## Шаг 1 — деплой бэкенда (Cloudflare Worker)

Нужны: Node.js, аккаунт Cloudflare (бесплатный).

API-ключ уже лежит в `worker/.dev.vars` (для локальной разработки). Этот файл **исключён из git** через `.gitignore`, так что в репо он не уедет.

```bash
cd worker
npm install
npx wrangler login                                  # один раз

# Загрузи ключ в Cloudflare как секрет (значение возьми из .dev.vars):
npm run push-secret
# ↑ wrangler спросит ключ — открой .dev.vars, скопируй значение
#   после ANTHROPIC_API_KEY= и вставь

npm run deploy
```

В конце `deploy` Wrangler выведет URL вида:

```
https://vibe-school-backend.<твой-субдомен>.workers.dev
```

**Скопируй этот URL — он нужен для фронта.**

> Имя Worker'а задаётся в `wrangler.toml` (`name = "vibe-school-backend"`). Хочешь другое — поменяй там.

---

## Шаг 2 — настройка фронтенда

Открой `docs/index.html`, найди в начале `<script>` строку:

```js
const BACKEND_URL = 'https://vibe-school-backend.YOUR-SUBDOMAIN.workers.dev';
```

Замени на URL из предыдущего шага.

---

## Шаг 3 — публикация на GitHub Pages

```bash
cd <корень проекта>   # папка vibe-school
git init
git add .
git commit -m "Initial vibe-school deploy"
git branch -M main
git remote add origin https://github.com/<ник>/<репо>.git
git push -u origin main
```

В GitHub: **Settings → Pages**:
- **Source:** Deploy from a branch
- **Branch:** `main`, папка `/docs`
- **Save**

Через 1–2 минуты сайт будет на `https://<ник>.github.io/<репо>/`.

---

## Проверка

1. Открой сайт на GH Pages.
2. Имя → возраст → проект → настройка → идея → «Создать проект».
3. Через 15–25 сек должна появиться превью-рамка с работающим приложением.

Если ошибка:
- **401 / "invalid api key"** → ключ в Worker'е не задан или невалидный. Перезапусти `wrangler secret put ANTHROPIC_API_KEY`.
- **CORS / network** → проверь, что `BACKEND_URL` в `index.html` совпадает с URL Worker'а (без слеша в конце).
- **500** → открой DevTools → Network → посмотри тело ответа.

Логи воркера: `npx wrangler tail` из папки `worker/`.

---

## Локальная разработка

```bash
# Терминал 1: бэкенд
cd worker
npx wrangler dev        # запустит на http://localhost:8787 с ключом из .dev.vars

# Во фронте временно:
# const BACKEND_URL = 'http://localhost:8787';

# Терминал 2: статика
cd docs
python -m http.server 5500
# → http://localhost:5500
```

---

## Безопасность

- Ключ `ANTHROPIC_API_KEY`:
  - **Локально** — в `worker/.dev.vars` (этот файл в `.gitignore`, в коммит не попадёт).
  - **В проде** — в Cloudflare Secret Store, загружается через `npm run push-secret`. В код воркера и в `wrangler.toml` ключ не зашит.
- Worker принимает любой Origin (`CORS: *`). Если хочешь ограничить — правь `CORS` в `worker/worker.js` на свой GH Pages домен.
- Квоту Anthropic контролируй через лимиты на console.anthropic.com.
- Для защиты от абьюза можно добавить rate-limit через Cloudflare KV или Turnstile — по необходимости.
- **Перед первым деплоем в прод проверь, что `.dev.vars` не закоммичен:** `git status` в корне репо не должен его показывать.

---

## Стоимость

- **GitHub Pages:** бесплатно.
- **Cloudflare Workers:** бесплатно до 100 000 запросов/день.
- **Anthropic Claude API:** по тарифу `claude-sonnet-4-6` — платишь только за токены.
