# podcasts-ai

Генератор русскоязычных познавательных аудиорассказов. Доставка — в Telegram, фидбэк — голосом или текстом. Темы и покрытые концепты накапливаются в Obsidian-wiki.

## Быстрый старт

1. `cp .env.example .env` и заполнить `YC_API_KEY`, `YC_FOLDER_ID`.
2. `uv sync`
3. Установить плагин Telegram-канала (см. `PROJECT.md` → «Как запускать»).
4. Запустить `claude --channels plugin:telegram@claude-plugins-official` из корня проекта в tmux.
5. В Telegram DM боту: *«Капитал Маркса, том 1, саммари 15 минут»*.

Подробности — в `PROJECT.md`. Правила для Claude — в `CLAUDE.md`.

## Основные концепции

- **Модульные провайдеры** — TTS/STT/Stress за абстракциями, выбор в `config.toml`.
- **Obsidian LLM Wiki** — компаундирующая база знаний, не RAG с эмбеддингами.
- **Стили нарратива** — переключаемые файлы в `styles/` (документальный, сторителлинг, академический, fireside).
- **Claude Code Channels** — официальный плагин Anthropic вместо своего бота.
