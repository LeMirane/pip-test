#!/usr/bin/env python3
"""
Бот-стенд: три способа отдать видео пользователю из Telegram, и что из них даёт PiP на iPhone.

  1) inline-кнопка с `url`      → встроенный браузер Telegram → PiP РАБОТАЕТ
  2) inline-кнопка с `web_app`  → вебвью Mini App            → PiP ВЫКЛЮЧЕН НАМЕРЕННО
  3) sendVideo                  → родной плеер Telegram      → PiP РАБОТАЕТ (нативный)

Запуск (токен НЕ хранится в файле и не попадает в git):
    BOT_TOKEN=123456:AA... python3 bot.py

Зависимостей нет — только стандартная библиотека.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PAGE_URL = os.environ.get("PAGE_URL", "https://lemirane.github.io/pip-test/").strip()
VIDEO_URL = os.environ.get(
    "VIDEO_URL", "https://media.w3.org/2010/05/sintel/trailer.mp4"
)  # 4.1 МБ — влезает в лимит Telegram на отправку по URL (20 МБ)
GAME_SHORT_NAME = os.environ.get("GAME_SHORT_NAME", "pip").strip()

if not TOKEN:
    sys.exit(
        "Не задан BOT_TOKEN.\n\n"
        "  1. @BotFather -> /newbot -> получить токен\n"
        "  2. BOT_TOKEN=<токен> python3 bot.py\n\n"
        "Токен читается из переменной окружения и никуда не записывается."
    )

API = "https://api.telegram.org/bot%s/" % TOKEN


def api(method, **params):
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        API + method, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print("! %s -> HTTP %s %s" % (method, e.code, body), file=sys.stderr)
        return {"ok": False, "error": body}
    except Exception as e:  # таймаут long polling — это норма
        print("! %s -> %s" % (method, e), file=sys.stderr)
        return {"ok": False, "error": str(e)}


MENU = {
    "inline_keyboard": [
        [{"text": "1 · Ссылкой → встроенный браузер", "url": PAGE_URL + "?ctx=browser"}],
        [{"text": "2 · Mini App → web_app", "web_app": {"url": PAGE_URL + "?ctx=miniapp"}}],
        [{"text": "3 · Видео файлом → родной плеер", "callback_data": "video"}],
        [{"text": "4 · Как игру → вебвью с включённым PiP", "callback_data": "game"}],
    ]
}

INTRO = (
    "<b>PiP через бота — три пути</b>\n\n"
    "Одна и та же страница, три разных вебвью. Открой по очереди и сравни.\n\n"
    "<b>1 · Ссылкой</b> — обычная <code>url</code>-кнопка. Открывает встроенный браузер "
    "Telegram. Там <code>allowsPictureInPictureMediaPlayback</code> не переопределён и "
    "остаётся дефолтным <code>true</code>. <b>PiP должен работать.</b>\n\n"
    "<b>2 · Mini App</b> — кнопка <code>web_app</code>. Открывает вебвью Mini App, где "
    "Telegram явно ставит этот флаг в <code>false</code>. <b>PiP не заработает</b>, "
    "и обойти это из JS нельзя.\n\n"
    "<b>3 · Видео файлом</b> — вообще без веба. Родной плеер Telegram, настоящий "
    "системный PiP через <code>AVPictureInPictureController</code>. "
    "<b>Работает и переживает сворачивание приложения.</b>\n\n"
    "<b>4 · Как игру</b> — та же страница, но открытая через <code>sendGame</code>. "
    "Вебвью игр (<code>GameControllerNode.swift</code>) флаг PiP не переопределяет и "
    "<code>playsinline</code> не навязывает. <b>Свой плеер + рабочий PiP, и всё ещё через бота.</b>\n\n"
    "На странице жми <b>1. Запустить видео</b>, потом <b>2a</b> и <b>2b</b>."
)


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if text.startswith("/start") or text.startswith("/help"):
        api(
            "sendMessage",
            chat_id=chat_id,
            text=INTRO,
            parse_mode="HTML",
            reply_markup=MENU,
            disable_web_page_preview=True,
        )
    else:
        api("sendMessage", chat_id=chat_id, text="Жми /start", reply_markup=MENU)


def handle_callback(cq):
    # Нажали Play на сообщении-игре: Telegram ждёт, что бот отдаст URL прямо в ответе.
    if cq.get("game_short_name"):
        api("answerCallbackQuery", callback_query_id=cq["id"], url=PAGE_URL + "?ctx=game")
        return

    data = cq.get("data") or ""
    chat_id = cq["message"]["chat"]["id"]

    if data == "game":
        api("answerCallbackQuery", callback_query_id=cq["id"], text="Отправляю игру…")
        r = api("sendGame", chat_id=chat_id, game_short_name=GAME_SHORT_NAME)
        if not r.get("ok"):
            api(
                "sendMessage",
                chat_id=chat_id,
                parse_mode="HTML",
                text=(
                    "Игра <code>%s</code> не зарегистрирована.\n\n"
                    "@BotFather → <code>/newgame</code> → выбрать этого бота → "
                    "название, описание, картинку 640×360 → короткое имя <code>%s</code>.\n\n"
                    "URL игры BotFather не спросит — его отдаёт сам бот в ответе на нажатие Play."
                ) % (GAME_SHORT_NAME, GAME_SHORT_NAME),
            )
        return

    api("answerCallbackQuery", callback_query_id=cq["id"], text="Отправляю видео…")
    api(
        "sendVideo",
        chat_id=chat_id,
        video=VIDEO_URL,
        supports_streaming=True,
        caption=(
            "Открой на весь экран и ищи кнопку PiP в углу плеера. "
            "Это родной плеер Telegram — тут PiP настоящий, системный: "
            "сверни Telegram, окошко останется поверх других приложений."
        ),
    )


def main():
    me = api("getMe")
    if not me.get("ok"):
        sys.exit("Токен не принят Telegram. Проверь BOT_TOKEN.")
    print("Бот @%s запущен. Страница: %s" % (me["result"]["username"], PAGE_URL))
    print("Открой в Telegram: https://t.me/%s  и отправь /start" % me["result"]["username"])
    print("Ctrl+C — остановить.\n")

    offset = None
    while True:
        upd = api("getUpdates", offset=offset, timeout=30)
        if not upd.get("ok"):
            time.sleep(3)
            continue
        for u in upd.get("result", []):
            offset = u["update_id"] + 1
            try:
                if "message" in u:
                    handle_message(u["message"])
                elif "callback_query" in u:
                    handle_callback(u["callback_query"])
            except Exception as e:
                print("! ошибка обработки: %s" % e, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nостановлен")
