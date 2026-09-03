#!/usr/bin/env bash
# Запуск бота. Токен берётся из файла .token рядом со скриптом (он в .gitignore)
# либо из переменной окружения BOT_TOKEN. В репозиторий не попадает ни то, ни другое.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .token ]; then
  BOT_TOKEN="$(tr -d '[:space:]' < .token)"
elif [ -n "${BOT_TOKEN:-}" ]; then
  :
else
  cat >&2 <<'MSG'
Токен не найден.

  1. @BotFather -> /newbot (или /mybots -> твой бот -> API Token)
  2. положи токен в файл .token рядом с этим скриптом:

       printf '%s' 'СЮДА_ТОКЕН' > .token

  3. ./run.sh

Файл .token в .gitignore и никуда не уедет.
MSG
  exit 1
fi

export BOT_TOKEN
exec python3 bot.py
