# PiP Test — Telegram Mini App

Одностраничный стенд для проверки гипотезы: **можно ли из Telegram Mini App на iPhone вывести видео в Picture-in-Picture.**

Всё в одном файле — `index.html`. Никакой сборки, никаких зависимостей.

## Ответ на гипотезу (из исходников Telegram-iOS)

**Нет — из Telegram Mini App на iPhone PiP не включить. Он выключен намеренно, на нативном уровне.**

`submodules/WebUI/Sources/WebAppWebView.swift` — вебвью, в котором работают Mini App:

```swift
configuration.allowsInlineMediaPlayback = true
configuration.allowsPictureInPictureMediaPlayback = false   // ← вот оно
```

Это флаг `WKWebViewConfiguration`. Он гасит PiP в самом WebKit, до того как до дела дойдёт JavaScript. `requestPictureInPicture()` и `webkitSetPresentationMode()` из страницы обойти его не могут — обходить нечего, API просто не подключён к нативному `AVPictureInPictureController`.

Вторая дверь закрыта отдельно. В каждый Mini App Telegram впрыскивает user script (там же, `videoSource`), который вешает `MutationObserver` и принудительно проставляет `playsinline` **каждому** `<video>` — существующему и любому будущему. То есть нативный полноэкранный плеер, в котором живёт системная кнопка PiP, тоже не открыть.

### Но: встроенный браузер Telegram — другой вебвью

`submodules/BrowserUI/Sources/BrowserWebContent.swift` конфигурируется отдельно и `allowsPictureInPictureMediaPlayback` **не трогает вообще** — значит флаг остаётся в дефолтном `true`. Инъекцию `playsinline` он делает ту же самую, а вот PiP-API там живой.

Практический вывод: если PiP нужен — уводи воспроизведение из Mini App во встроенный браузер (`Telegram.WebApp.openLink()`) или в Safari. Внутри самого Mini App вариантов нет.

Страница определяет свой контекст сама: пробует создать `<video>` без `playsinline` и смотрит, проставит ли его обсервер Telegram. По этому признаку + `Telegram.WebApp.platform` она различает Mini App, встроенный браузер и обычный Safari.

## Что страница проверяет

Три независимых пути к PiP — страница даёт нажать каждый и показывает точную ошибку, если путь закрыт:

| # | Путь | Что вызывается |
|---|------|----------------|
| 2a | Стандартный W3C API | `video.requestPictureInPicture()` |
| 2b | WebKit-API (основной на iOS) | `video.webkitSetPresentationMode('picture-in-picture')` |
| 3a | Нативная кнопка PiP в плеере | `video.webkitEnterFullscreen()` → кнопка в оверлее |
| — | Авто-PiP при сворачивании | вызов PiP в `visibilitychange` + системная настройка iOS |

Плюс: таблица фактической поддержки API в вебвью, окружение (`platform`, `version` из `Telegram.WebApp`, UA), и лог всех медиа-событий (`webkitpresentationmodechanged`, `enterpictureinpicture`, `webkitbeginfullscreen`, …).

Лог пишется в `localStorage` — он переживает перезагрузку вебвью после того, как ты свернёшь Telegram. Это важно: именно так проверяется, продолжается ли PiP в фоне.

## Как запустить

Telegram Mini App принимает **только HTTPS**. Локальный `file://` или `http://localhost` не подойдут.

### Вариант 1 — GitHub Pages (бесплатно, постоянный URL)

```bash
git init -b main && git add -A && git commit -m "pip test page" && gh repo create pip-test --public --source=. --push && gh api -X POST repos/:owner/pip-test/pages -f 'source[branch]=main' -f 'source[path]=/'
```

Через ~1 минуту страница будет на `https://<твой-логин>.github.io/pip-test/`.

### Вариант 2 — локальный сервер + туннель (для быстрых правок)

```bash
cd /Users/george/test-player && python3 -m http.server 8899
```

```bash
npx --yes localtunnel --port 8899
```

Туннель выдаёт HTTPS-URL. Минус: localtunnel показывает страницу-заглушку при первом заходе — её надо один раз пройти.

### Вариант 3 — Netlify Drop

Перетащить папку на https://app.netlify.com/drop — HTTPS-URL сразу, без аккаунта.

## Как открыть как Mini App

1. В Telegram → [@BotFather](https://t.me/BotFather) → `/newbot` (если бота ещё нет).
2. `/newapp` → выбрать бота → название, описание, картинку 640×360 → **Web App URL** = твой HTTPS-адрес → короткое имя, например `pip`.
3. Открыть `https://t.me/<имя_бота>/pip` на iPhone.

Быстрая альтернатива без `/newapp`: BotFather → `/mybots` → бот → **Bot Settings → Menu Button → Edit menu button URL** → вставить URL. Дальше — кнопка меню в чате с ботом.

Сравни с обычным браузером Telegram: просто отправь себе тот же URL ссылкой и открой тапом. Встроенный браузер и Mini App — это **разные** конфигурации вебвью, результат может отличаться. Страница показывает, где именно она запущена.

Telegram кеширует Mini App агрессивно — при правках добавляй `?v=2`, `?v=3` к URL.

## Порядок теста на iPhone

1. Нажать **1. Запустить видео** — на iOS PiP не включится, пока видео не играет.
2. **2a**, затем **2b**. Если хоть одна открыла окошко — гипотеза подтверждена, дальше можно не идти.
3. Если обе упали — **3a. Fullscreen · WebKit**, и искать в плеере кнопку PiP (прямоугольник со стрелкой в углу).
4. Из полноэкранного режима свернуть Telegram свайпом вверх — если в *Настройки → Основные → Картинка в картинке* включён «Автозапуск», видео может уйти в PiP само.
5. Нажать **Скопировать отчёт** и прислать текст.

Ключевое место в логе — точное имя ошибки: `NotAllowedError` (нет жеста / запрещено политикой) и `NotSupportedError` (API отключён в вебвью) означают совершенно разные вещи.
