# PROJECT.md — живое состояние системы podcasts-ai

**Последнее обновление:** 2026-04-19 (вечер, spike F5-TTS)

## Что это и зачем

Генератор одноголосых познавательных аудиорассказов на русском с доставкой в Telegram. Формат — документальный монолог с метафорами и аналогиями, без воды. Темы задаёт пользователь ("Капитал Маркса, 15 минут"), фидбэк — текстом или голосом, система углубляется в запрошенные направления. Покрытые темы накапливаются в Obsidian-wiki как граф концептов, что даёт дедупликацию и компаундинг знаний по мере роста числа эпизодов.

## Текущие решения

| Параметр | Значение | Файл |
|---|---|---|
| TTS провайдер (активный) | Yandex SpeechKit v3 | `podcasts/tts/yandex.py` |
| TTS провайдер (экспериментальный) | F5-TTS_RUSSIAN (Misha24-10 v2, MPS) | `podcasts/tts/f5_russian.py` |
| TTS провайдер (живой, ключ в .env) | SaluteSpeech (Sber REST + SSML) | `podcasts/tts/salutespeech.py` |
| Голос | `marina` (neural v3) | `config.toml` → `tts.voice` |
| STT провайдер | Yandex SpeechKit v3 | `podcasts/stt/yandex.py` |
| Stress-простановка | RUAccent (turbo, с PyTorch/MPS) | `podcasts/stress/ruaccent.py` |
| Стиль по умолчанию | `documentary` | `styles/documentary.md` |
| Vault | `./vault` (можно симлинкнуть в Obsidian) | `config.toml` → `vault.path` |
| Транспорт | Claude Code Channels + Telegram | `--channels plugin:telegram@...` |
| Yandex folder | `your-folder-id` | `.env` |
| Yandex SA | `podcasts-ai` (id `your-service-account-id`) | — |

## Критическое правило разметки ударений

**В Yandex SpeechKit `+` ставится НЕПОСРЕДСТВЕННО ПЕРЕД ударной гласной**, а не после. Буква сразу после `+` обязана быть гласной (а, е, ё, и, о, у, ы, э, ю, я). Если `+` оказывается перед согласной или в конце слова, Yandex зачитывает его буквально как «плюс».

- ✅ `з+амок` (замок-здание), `зам+ок` (замок-запор)
- ✅ `плач+у` (плачу́ деньги), `пл+ачу` (пла́чу слезами)
- ❌ `За+мок`, `плачу+`, `бел+ки` — Яндекс произнесёт «плюс»

`YandexTTS.synthesize` содержит скрабер, который удаляет `+` не перед гласной (safety net), но это не замена корректной разметке — скрабер молча удаляет знак, и слово остаётся без ударения.

Полный чек-лист разметки омографов — в `.claude/skills/podcast/SKILL.md`.

## Двухступенчатая схема ударений

Claude и RUAccent играют разные роли:

1. **Claude при генерации сценария** размечает `+` на омографах по контексту. LLM-модель понимает смысл, поэтому лучше автоматики различает `з+амок`/`зам+ок` и т.п. Это критично — автоматика без контекста эти пары путает примерно в половине случаев.
2. **RUAccent** расставляет ударения на обычных (не-омографных) словах — здесь его точность 0.97, что больше нам не нужно.

Попытка полагаться только на RUAccent (даже с моделью `big_poetry`) в теле параграфа даёт ~3 из 10 корректных омографов — проверено 2026-04-19. Поэтому Claude **обязан** размечать омографы явно.

## Известные ограничения

- **RUAccent иногда расставляет контекстно-чувствительные ударения неточно** даже на не-омографах (пример: `Д+ухи прошлого` может прозвучать с нетипичной интонацией). Лечение — перефразировать или явно разметить ещё больше слов на этапе Claude.
- **Голос `marina` слегка монотонный** на длинных повествованиях. Можно экспериментировать с другими голосами (`alena`, `filipp`) или с параметром `role` в `Hints` (`neutral`/`good`/`friendly`), чтобы менять эмоциональную окраску. Не включено в MVP.
- **Лимит Yandex v3 UtteranceSynthesis — 250 символов** на запрос (не 5000, как в v1 REST). Провайдер режет текст на чанки по 230 символов. Для 15-минутного эпизода это ~60 gRPC-вызовов, но каждый занимает <1 сек.

## Как запускать

Предусловия: Bun, Claude Code v2.1.80+, claude.ai Pro/Max, ffmpeg, заполненный `.env` (см. `.env.example`).

```bash
cd /Users/kirrotech/Projects/podcasts-ai
python3 -m uv sync        # один раз — установит зависимости в .venv

# Демо-сборка (параграф с омографами)
python3 -m uv run python -m podcasts.build scripts/test-paragraph.txt

# Когда подключён Telegram-плагин и запарены:
# /plugin marketplace add anthropics/claude-plugins-official
# /plugin install telegram@claude-plugins-official
# /telegram:configure <BOT_TOKEN>

tmux new -s podcasts
claude --channels plugin:telegram@claude-plugins-official
# В Telegram: DM боту, получить код
# В Claude: /telegram:access pair <код>
#          /telegram:access policy allowlist
```

## Контракты модулей

Все внешние сервисы — через `Protocol`-абстракции. Новый провайдер добавляется файлом в соответствующей папке + регистрацией в `registry.py`.

```python
# podcasts/tts/base.py
class TTSProvider(Protocol):
    def synthesize(self, text: str, voice: str, speed: float) -> bytes: ...
    def supported_voices(self) -> list[str]: ...
    def max_chunk_chars(self) -> int: ...
    def output_mime(self) -> str: ...

# podcasts/stt/base.py
class STTProvider(Protocol):
    def transcribe(self, audio_path: Path, language: str = "ru-RU") -> str: ...

# podcasts/stress/base.py
class StressProvider(Protocol):
    def annotate(self, text: str) -> str: ...
```

## Как расширять

**Новый TTS-провайдер:**
1. `podcasts/tts/<name>.py` с классом, реализующим `TTSProvider`.
2. Если у провайдера своя разметка ударений (не Yandex `+vowel`) — конвертировать на входе `.synthesize()`.
3. Зарегистрировать в `podcasts/tts/registry.py`.
4. Новые секреты — в `.env.example` и `podcasts/config.py`.
5. Обновить этот файл.

**Про ElevenLabs и другие:** исследование 2026-04-19 показало, что ElevenLabs `multilingual_v2`/`v3` поддерживает русский как язык, но **не имеет явной разметки ударений** — модель сама гадает по контексту. Для омографов это регресс по сравнению с Yandex, поэтому стаб провайдера удалён. Если интересно поэкспериментировать с тембром — добавь файл руками; интерфейс остаётся стабильным.

**Про F5-TTS_RUSSIAN:** провайдер `f5_russian` подключён (Misha24-10/F5TTS_v1_Base_v2, 335M параметров, на MPS). Нативно понимает `+гласная` — миграция разметки нулевая. Voice cloning из `scripts/f5_ref/reference.wav` (~10 сек живого голоса). Первый запуск скачивает ~1.35 GB чекпоинт + 100 MB Vocos вокодер. `vocab.txt` лежит в `F5TTS_v1_Base/`, не в `v2`-папке. Переключение — `config.toml` → `tts.provider = "f5_russian"`. RTF на M2 Pro + MPS ≈ 5× (47 сек аудио = ~4 мин сборки); подойдёт для ночных фоновых сборок, не real-time.

**Про SaluteSpeech (Sber):** провайдер `salutespeech` подключён, ждёт `SBER_AUTH_KEY` в `.env` (base64 из ЛК → пункт "Get key", scope `SALUTE_SPEECH_PERS`). Freemium для физлиц — 200 000 символов/мес бесплатно (≈3–4 часа аудио). REST + SSML: `<speak>...</speak>`, разметка ударений — апостроф **после** ударной гласной (`за'мок` vs `замо'к`) — конвертируется из Yandex-формата `+гласная` автоматически (`_to_ssml()` в провайдере). Голоса: `Nec_24000` (Наталья), `Ost_24000` (Александра), `Bys_24000` (Борис) и ещё 3. Лимит 4000 символов за запрос (в 17× больше Yandex v3). OAuth access token кэшируется в провайдере (TTL ≈ 30 мин). Для продакшена нужно подпихнуть CA-сертификат Минцифры; сейчас `verify=False` только на OAuth-endpoint.

**Новый стиль:**
1. `styles/<name>.md` по образцу `styles/documentary.md`.
2. В команде: `--style <name>`. Постоянный дефолт — через `style.default` в `config.toml`.

**Новая команда:**
1. `.claude/commands/<name>.md` — slash-команда.
2. Если нужен CLI-скрипт — `podcasts/<name>.py` с `main()` и entry-point в `pyproject.toml`.

## Open questions / в работе

- [ ] Выбрать основной TTS-провайдер после прослушки spike-файлов: Yandex marina / SaluteSpeech Ost или Tur / F5-female3. По плану — SaluteSpeech как дефолт (живая интонация + свободный freemium), F5 как ночной batch для эксклюзивного тембра.
- [ ] Для SaluteSpeech на прод — подложить CA-сертификат Минцифры (`russiantrustedca.pem`) вместо `verify=False` в `salutespeech.py`.
- [ ] Рассмотреть SSML-обогащение для Сбера: обернуть абзацы в `<paint slope="4">`, добавлять `<break time="500ms"/>` между предложениями, расставлять `*` на ключевых существительных для эмфазы.
- [ ] Снять монотонность голоса Yandex: `alena`/`filipp` или `Hints.role = "good"`.
- [ ] Решить где физически хранить `vault/` — внутри репо или симлинком на `~/Documents/Obsidian/Podcasts`.
- [ ] Демонизировать Claude-сессию через launchd (сейчас tmux).
- [ ] Добавить `mcpvault` MCP-сервер когда vault разрастётся — для BM25 поиска.
- [ ] Отслеживать потраченные символы Yandex/Sber для бюджета (сейчас rate-limit только по числу запросов).
- [ ] Настроить Telegram-плагин (`/telegram:configure`, `/telegram:access pair`, allowlist).

## Changelog

- **2026-04-19 (фикс RUAccent restore)**: Баг — `_capture_existing` хранил по ключу `stripped_lower`, поэтому омографы с разной разметкой в одном тексте затирали друг друга (в test-paragraph «Д+ухи прошлого» и «дух+и французской» оба восстанавливались как «дух+и»). Заменено на `_capture_existing_ordered` + `_restore_ordered` с позиционными курсорами — каждое вхождение берёт свою форму в порядке документа. 5 новых тестов (33 passed).
- **2026-04-19 (spike ElevenLabs)**: Проверен `eleven_v3` — на free-плане API отвечает 402 для всех library voices (собственные IVC-клоны требуют Creator+). Тариф Creator $22/мес (121k символов ≈ 230 мин) признан слишком дорогим для подкаст-потока. Провайдер и зависимость `elevenlabs` удалены — в таблице сравнения TTS (Yandex / Sber / F5 / ElevenLabs) победили Сбер + F5.
- **2026-04-19 (spike SaluteSpeech)**: Добавлен провайдер `salutespeech` (Sber REST + SSML). Конвертор `+гласная → гласная'`, OAuth2 client credentials с кэшем токена, 6 русских голосов, лимит 4000 символов/запрос, 7 unit-тестов на SSML-конверсию. На M2 Pro целый тестовый абзац ген. за 2.5 сек (1 чанк) против 5 чанков у Yandex — более ровная интонация за счёт отсутствия склеек. Голоса Ost (Александра) и Tur (Тарас) — живая интонация. Free tier 200k символов/мес. Для dev: `verify=False` на обоих endpoint'ах (Минцифры CA не в macOS trust store) — TODO на прод.
- **2026-04-19 (spike F5-TTS_RUSSIAN, ч.2)**: Повторный прогон F5 с живым reference-голосом `female_3.wav` с демо-сайта Misha24-10 (предыдущий реф был клон marina и дал неотличимый результат). Сборка за ~70 сек на M2 Pro + MPS → `audio/test-paragraph-f5-female3.mp3`. RTF ≈ 1.5× — значительно быстрее первого прогона (~4 мин), видимо за счёт прогретого кэша моделей.
- **2026-04-19 (spike F5-TTS_RUSSIAN)**: Добавлен экспериментальный провайдер `f5_russian` (Misha24-10/F5TTS_v1_Base_v2). Сгенерирован `audio/test-paragraph-f5.mp3` (45 сек, 2 чанка, 5 sub-chunks внутри). Тайминги на M2 Pro + MPS на холодный кэш: ~4 мин общего времени (2:17 + 1:30 чистый инференс). `vocab.txt` лежит в `F5TTS_v1_Base/` (общий для всех версий), не в `F5TTS_v1_Base_v2/` — учтено в коде. Рефакторинг: `_scrub_stray_plus` вынесен в `podcasts/tts/_stress_utils.py` и переиспользуется всеми провайдерами.
- **2026-04-19 (evening)**: Первый end-to-end тест связного параграфа (`scripts/test-paragraph.txt` → `audio/test-paragraph.mp3`, 47 сек, 5 омографов). Пользователь подтвердил «приемлемый результат». Удалены стабы `elevenlabs.py`/`silero.py` и диагностические тест-скрипты — остаётся только Yandex-провайдер, расширение — по необходимости.
- **2026-04-19 (диагностика)**: Обнаружено два бага в исходной реализации:
  1. PyTorch не был в зависимостях → RUAccent работал в dictionary-only fallback. Добавлен `torch>=2.4`, теперь используется neural-модель с MPS-ускорением.
  2. `+` для ударений ставился после гласной вместо перед — Yandex зачитывал буквально «плюс». Добавлен скрабер `YandexTTS._scrub_stray_plus`, уточнено правило в SKILL.md, сохранено в память Claude.
- **2026-04-19 (сетап)**: Создан сервис-аккаунт `podcasts-ai` в Yandex Cloud с ролями `ai.speechkit-tts.user` и `ai.speechkit-stt.user`. API-ключ записан в `.env` (не в git). Установлены зависимости через `uv sync`.
- **2026-04-19 (скаффолд)**: Начальная структура — Python 3.12+, модульные провайдеры (TTS/STT/Stress) через Protocol, Yandex как default, Obsidian LLM Wiki в `vault/`, 5 стилей, 4 slash-команды, 2 скилла. Claude Code Channels Telegram-плагин как транспорт.
