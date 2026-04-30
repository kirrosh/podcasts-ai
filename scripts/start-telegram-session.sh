#!/usr/bin/env bash
# Запускает долгоживущую Claude-сессию с Telegram-каналом в фоне через screen.
# Пререквизиты: плагин уже установлен (`/plugin install telegram@claude-plugins-official`
# + `/reload-plugins`), токен уже записан в ~/.claude/channels/telegram/.env.
set -euo pipefail

SESSION="podcasts"
PROJECT_DIR="/Users/kirrotech/Projects/podcasts-ai"

if ! command -v screen >/dev/null 2>&1; then
  echo "screen не найден. Поставь: brew install screen (или tmux)." >&2
  exit 1
fi

if [[ ! -f "$HOME/.claude/channels/telegram/.env" ]]; then
  echo "Нет ~/.claude/channels/telegram/.env — плагин не найдёт токен." >&2
  echo "Либо запусти в Claude: /telegram:configure <token>" >&2
  echo "Либо создай файл руками со строкой TELEGRAM_BOT_TOKEN=..." >&2
  exit 1
fi

if screen -ls | grep -q "\.${SESSION}[[:space:]]"; then
  echo "Сессия '${SESSION}' уже запущена."
  echo "Приткнуться: screen -r ${SESSION}"
  exit 0
fi

cd "${PROJECT_DIR}"

screen -dmS "${SESSION}" claude --channels plugin:telegram@claude-plugins-official

sleep 1
if screen -ls | grep -q "\.${SESSION}[[:space:]]"; then
  cat <<EOF
Сессия '${SESSION}' запущена в фоне.

Приткнуться (видеть вывод Claude, вводить slash-команды):
  screen -r ${SESSION}

Отцепиться, не убивая её: нажми Ctrl+A, потом D

Список сессий:
  screen -ls

Убить сессию:
  screen -S ${SESSION} -X quit

После первого запуска:
  1. screen -r ${SESSION}
  2. В Telegram напиши что-нибудь боту — получишь 6-символьный код
  3. В Claude: /telegram:access pair <код>
  4. Затем: /telegram:access policy allowlist
  5. Ctrl+A, D — отцепиться
EOF
else
  echo "Не удалось запустить screen-сессию. Проверь руками: screen -ls" >&2
  exit 1
fi
