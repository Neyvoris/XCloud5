#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build-time generation of committed Russian XCloud5 UI localization.

Only public, hard-coded English UI source strings are sent to a translation
service during an explicitly invoked generation command. PS4 runtime never
contacts that service. Generated .inc files are committed with release source.
Fail closed if any required entry cannot be translated or format placeholders
change; never silently ship an incomplete "fully translated" release.

The pinned offline Argos model is used only during authoring. Generated
strings ship inside the client; no language model or network translation is
required on PS4. Use --check to validate files without translation dependencies.
"""
import argparse
import ast
import concurrent.futures
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/ui/lang.c"
UI = ROOT / "src/ui/lang_ru.inc"
STAGES = ROOT / "src/ui/lang_ru_stage.inc"

ENTRY = re.compile(r'^(\s*\[(X4_TR_[A-Za-z0-9_]+)\]\s*=\s*)("(?:\\.|[^"\\])*")(\s*,.*)$', re.M)
STAGE_ROW = re.compile(
    r'^\s*\{\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*,',
    re.M,
)
PRINTF = re.compile(
    r'%(?:[1-9]\d*\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?'
    r'(?:hh|ll|h|l|z|j|t|L)?[diouxXfFeEgGaAcspn%]'
)
MARKER = "🟣🟣🟣"
CACHE = ROOT / "scripts/ru_translation_cache.json"

# Reviewed core translations. Everything else is translated in a generation
# pass, then checked for UTF-8/C-escape, printf placeholders and completeness.
OVERRIDES = {
    "X4_TR_U49_SEARCH_LABEL": "Поиск",
    "X4_TR_U49_MY_GAMES": "Мои игры",
    "X4_TR_U49_LAST_SESSION": "Последняя сессия",
    "X4_TR_U49_PLAY_TIME": "Время в игре",
    "X4_TR_U49_NO_FAVORITES": "В избранном пока ничего нет.",
    "X4_TR_U49_POPULAR_CLOUD": "Популярное в облаке",
    "X4_TR_U49_COLLECTIONS": "Подборки",
    "X4_TR_U49_SORT_NEW": "Новинки",
    "X4_TR_U49_SORT_FEATURED": "Рекомендуемые",
    "X4_TR_U49_FAVORITES": "Избранное",
    "X4_TR_U49_GENRE": "Жанр",
    "X4_TR_U49_ACCESS": "Доступ",
    "X4_TR_U49_SORT_BY": "Сортировка",
    "X4_TR_U49_LIBRARY": "Моя библиотека",
    "X4_TR_U49_RECENTLY_PLAYED": "Недавно играли",
    "X4_TR_U49_SORT_MOST_PLAYED": "Часто запускаемые",
    "X4_TR_U49_SORT_FAVORITES_FIRST": "Сначала избранное",
    "X4_TR_U49_SORT_RECENT": "Недавние",
    "X4_TR_U49_FILTER": "Фильтр",
    "X4_TR_U49_PAGE": "Страница",
    "X4_TR_U49_SEE_ALL": "Показать всё",
    "X4_TR_U49_MANAGE": "Управление",
    "X4_TR_U49_VIEW_GAME_SHORT": "Открыть игру",
    "X4_TR_U49_REMOVE_FROM_FAVORITES": "Убрать из избранного",
    "X4_TR_U49_SEARCH_SUBTITLE": "Найдите игру по названию.",
    "X4_TR_U49_CATALOG_SUBTITLE": "Каталог облачных игр.",
    "X4_TR_U49_SEARCH_PLACEHOLDER": "Поиск игр…",
    "X4_TR_U49_RESULT": "результат",
    "X4_TR_U49_RESULTS": "результатов",
    "X4_TR_U49_GAME": "игра",
    "X4_TR_U49_GAMES": "игр",
    "X4_TR_50_LANG_AUTO": "Автоматически (язык консоли)",
    "X4_TR_50_LANG_ES": "Español",
    "X4_TR_50_LANG_EN": "English",
    "X4_TR_50_LANG_PT_BR": "Português (Brasil)",
    "X4_TR_50_LANG_FR": "Français",
    "X4_TR_50_LANG_IT": "Italiano",
    "X4_TR_50_LANG_DE": "Deutsch",
    "X4_TR_50_LANG_RU": "Русский",
    "X4_TR_50_SETTINGS_LANGUAGE": "Язык",
    "X4_TR_50_SETTINGS_SAVING": "Сохранение…",
    "X4_TR_51_UPDATE_NOW": "Обновить",
    "X4_TR_51_UPDATE_LATER": "Позже",
    "X4_TR_51_UPDATE_CHECK": "Проверить обновления",
    "X4_TR_51_UPDATE_MANIFEST": "Поиск обновления…",
    "X4_TR_51_UPDATE_DOWNLOAD": "Скачивание…",
    "X4_TR_51_UPDATE_VERIFY": "Проверка…",
    "X4_TR_51_UPDATE_INSTALL": "Установка…",
    "X4_TR_51_UPDATE_ERR_SIGNATURE": "Недействительная подпись обновления.",
    "X4_TR_51_UPDATE_ERR_HASH": "Контрольная сумма SHA-256 не совпадает.",
    "X4_TR_51_UPDATE_ERR_SPACE": "Недостаточно свободного места или не удалось проверить его объём.",
    "X4_TR_51_UPDATE_NO_ASSETS": "Для этого релиза нет подписанного обновления внутри приложения.",
    "X4_TR_51_UPDATE_CANCELLED": "Загрузка отменена.",
    "X4_TR_51_UPDATE_LOCAL": "Обновить из /data/pkg",
    "X4_TR_51_UPDATE_CLOSE_APP": "Закрыть XCloud5",
    "X4_TR_51_UPDATE_LAST_RESULT": "Последний результат",
    "X4_TR_51_UPDATE_NONE": "Проверки ещё не запускались",
    "X4_TR_51B_INSTALL_TITLE": "Установка обновления",
    "X4_TR_51B_CANCEL_PENDING": "Отменить ожидающее обновление",
    "X4_TR_51F_CLOSE_NOW": "Закрыть сейчас",
    "X4_TR_51F_MANUAL_TITLE": "Ручная установка",
    "X4_TR_51F_UPDATED_TITLE": "Обновление установлено",
    "X4_TR_51F_RESUME": "На PS4 по-прежнему запущена предыдущая версия. Проверенный пакет готов.",
    "X4_TR_51G_PREPARE_MANUAL": "Подготовка ручной установки…",
    "X4_TR_51G_REMOVE_PKG": "Чтобы освободить место, можно удалить этот файл из /data/pkg.",
}


# Reviewed Russian wording for visible navigation, sign-in and updater paths.
# This layer overrides machine translations without touching the 6 earlier languages.
OVERRIDES.update({
    "X4_TR_U49_HOME_PLAY_TIME_PREFIX": "Время в игре: ",
    "X4_TR_U49_RECENTS_LOAD_FAILED": "Не удалось загрузить недавно запущенные игры.",
    "X4_TR_U49_NO_GAMES_IN_VIEW": "В этом разделе пока нет игр.",
    "X4_TR_U49_FAVORITE_FROM_GAME": "Добавьте игру в избранное на странице её описания.",
    "X4_TR_U49_LIBRARY_CLOUD_SUBTITLE": "Ваша библиотека и избранное в облаке",
    "X4_TR_U49_LIBRARY_SUBTITLE": "Все недавно запущенные и избранные игры в одном месте.",
    "X4_TR_U49_REMOVE_FAVORITE": "Убрать из избранного",
    "X4_TR_U49_COLLECTION_MULTIPLAYER_NAME": "Мультиплеер",
    "X4_TR_U49_COLLECTION_SPORTS_CAPTION": "Соревнуйтесь и побеждайте",
    "X4_TR_U49_COLLECTION_RACING_NAME": "Гонки",
    "X4_TR_U49_COLLECTION_RACING_CAPTION": "Жмите на газ",
    "X4_TR_U49_COLLECTION_SHOOTER_NAME": "Шутеры",
    "X4_TR_U49_COLLECTION_SHOOTER_CAPTION": "Проверьте меткость",
    "X4_TR_U49_COLLECTION_INDIE_CAPTION": "Откройте новые игровые миры",
    "X4_TR_U49_QUALITY_NORMAL_HELP": "1920 × 1080, до 8 Мбит/с. Меньше трафика, но сильнее сжатие. Подойдёт, если высокое качество работает рывками.",
    "X4_TR_U49_VSYNC_AUTO_HELP": "Уменьшает разрывы изображения, подстраиваясь под частоту кадров.",
    "X4_TR_U49_VSYNC_T27_HELP": "Синхронизирует изображение при низкой частоте кадров, а при высокой уменьшает задержку отклика.",
    "X4_TR_U49_FORTNITE_OPEN": "Открыть игру",
    "X4_TR_U49_ABOUT_TITLE": "О приложении",
    "X4_TR_U49_ABOUT_DEVELOPER": "Разработчик",
    "X4_TR_U49_ABOUT_CREDITS": "Благодарности",
    "X4_TR_U49_ABOUT_HELP": "Управление и выход",
    "X4_TR_U49_ABOUT_LATEST": "Установлена последняя версия.",
    "X4_TR_U49_GPU": "GPU",
    "X4_TR_U49_FORTNITE_TITLE": "Fortnite",
    "X4_TR_U49_FORTNITE_WAIT": "Поиск Fortnite…",
    "X4_TR_U49_ACCOUNT_TITLE": "Учётная запись",
    "X4_TR_U49_ACCOUNT_ACTIVE": "Вход выполнен",
    "X4_TR_U49_ACCOUNT_SERVER": "Сервер",
    "X4_TR_U49_ACCOUNT_CLOUD_TIME": "Время облачной игры",
    "X4_TR_U49_ACCOUNT_LOCAL_FMT": "%u игр · %s в игре",
    "X4_TR_U49_ACCOUNT_SIGN_OUT": "Выйти",
    "X4_TR_U49_ACCOUNT_FORGET": "Забыть данные входа",
    "X4_TR_U49_ACCOUNT_SIGN_IN": "Войти",
    "X4_TR_U49_ACCOUNT_WAIT": "Ожидание входа…",
    "X4_TR_U49_ACCOUNT_LOGOUT_REMEMBER": "Сохранённые данные входа на PS4 также будут удалены.",
    "X4_TR_U49_HOME_SIGN_IN_TITLE": "Войти",
    "X4_TR_U49_HOME_SIGN_IN_RECENTS": "После входа появятся ваши недавно запущенные игры.",
    "X4_TR_U49_HOME_CLOUD_COUNT_FMT": "Более %u игр в облаке",
    "X4_TR_U49_HOME_EXPLORE_CATALOG": "Открыть каталог",
    "X4_TR_U49_HOME_EXPLORE": "Открыть каталог",
    "X4_TR_U49_HOME_LAST_PLAYED": "Последний запуск",
    "X4_TR_U49_HOME_RECENTS_ERROR": "Не удалось загрузить недавно запущенные игры.",
    "X4_TR_U49_HOME_EMPTY_RECENTS": "Вы пока не запускали игры.",
    "X4_TR_U49_HOME_WELCOME_FMT": "Добро пожаловать, %s",
    "X4_TR_UPDATE_NOTICE_VERSION_FMT": "Доступна версия XCloud5 %s. У вас установлена %s.",
    "X4_TR_UPDATE_NOTICE_DESCRIPTION": "Сканируйте QR-код, чтобы открыть загрузку на GitHub. Установите PKG через GoldHEN → Package Installer.",
    "X4_TR_UPDATE_NOTICE_TEST_QUEUED": "Тестовое уведомление появится при возвращении на главный экран.",
    "X4_TR_UI2_MODAL_ACCESS_STEP": "Используйте кнопки влево и вправо для выбора страны.",
    "X4_TR_UI2_MODAL_UPDATE_LINK": "github.com/Neyvoris/XCloud5/releases",
    "X4_TR_UI2_SETTINGS_TRANSMISSION": "Трансляция",
    "X4_TR_UI2_SETTINGS_SAVE": "Сохранить",
    "X4_TR_UI2_SETTINGS_DISCARD": "Не сохранять",
    "X4_TR_UI2_SETTINGS_UNSAVED_TITLE": "Несохранённые изменения",
    "X4_TR_UI2_SETTINGS_UNSAVED_BODY": "Сохраните изменения, чтобы применить настройки, или отмените их.",
    "X4_TR_UI2_SETTINGS_SECTION": "Сменить раздел",
    "X4_TR_UI2_SETTINGS_LAB_APPLY": "Применить",
    "X4_TR_UI2_SETTINGS_LAB_CANCEL": "Отмена",
    "X4_TR_51_UPDATE_LOCAL_CONFIRM": "Перед установкой локального PKG будут проверены подпись и версия.",
    "X4_TR_51C_UPDATE_ERR_READ_FMT": "Не удалось прочитать пакет (код %s).",
    "X4_TR_51C_UPDATE_ERR_MANIFEST": "Недействительный манифест обновления.",
    "X4_TR_51C_UPDATE_ERR_BUSY": "Обновление уже выполняется или ожидает установки.",
    "X4_TR_51F_MANUAL_VERIFIED_FMT": "Обновление %s загружено и проверено.",
    "X4_TR_51F_APPINST_WARNING": "Тест запускает AppInstUtil и может закрыть XCloud5. Сохраните данные перед продолжением.",
    "X4_TR_51F_CLOSE_IN_FMT": "PS4 устанавливает обновление. XCloud5 закроется через %u с. Проверьте уведомления и после установки откройте приложение заново.",
    "X4_TR_50_SCREEN_ABOUT_CRUMB": "Главная / О приложении",
    "X4_TR_50_SCREEN_SUPPORT_CRUMB": "Главная / Поддержка",
    "X4_TR_50_SCREEN_ERROR_GENERIC": "Не удалось продолжить",
    "X4_TR_50_SCREEN_RETRY": "Повторить",
    "X4_TR_50_SCREEN_FORTNITE_CRUMB": "Главная / Fortnite",
    "X4_TR_50_SCREEN_FORTNITE_FINDING": "Поиск Fortnite на Xbox…",
    "X4_TR_50_SCREEN_FORTNITE_SERVER_PING": "Сервер: %s · %d мс",
    "X4_TR_50_SCREEN_QUALITY_HIGH": "1080p · высокое качество",
    "X4_TR_50_SCREEN_ACCOUNT_CRUMB": "Главная / Учётная запись",
    "X4_TR_50_SCREEN_ACCOUNT_LINKED": "Учётная запись подключена",
    "X4_TR_50_SCREEN_ACCOUNT_HINT_PUBLIC": "X — войти · △ — выйти · OPTIONS — настройки · R1 — каталог",
    "X4_TR_50_SCREEN_SESSION_CRUMB": "Главная / Игра",
    "X4_TR_50_SCREEN_SESSION_CLOSED": "Сеанс завершён",
    "X4_TR_50_SCREEN_SESSION_PREPARING_FMT": "Xbox готовит игру… %u с",
    "X4_TR_50_SCREEN_SESSION_QUEUE_LIMIT": "Все серверы Xbox заняты. Повторите попытку через несколько минут или выберите другой сервер в настройках.",
    "X4_TR_50_SCREEN_SESSION_QUEUE_CANCEL": "Можно подождать или отменить (кнопка ○).",
    "X4_TR_50_SCREEN_SESSION_UNCONFIRMED_FMT": "Закрытие сеанса не подтверждено: 0x%08x · HTTP %d",
    "X4_TR_50_SCREEN_SESSION_AUDIO_ERROR_FMT": "Не удалось запустить звук (0x%08x).",
    "X4_TR_50_SCREEN_GAME_STORE_REFRESH": "Проверить доступ в Xbox",
    "X4_TR_50_SCREEN_GAME_CHANGE_TAB": "Переключить вкладку",
    "X4_TR_50_SCREEN_GAME_TIME_PLAYED_FMT": "Время в игре: %s",
    "X4_TR_50_SCREEN_GAME_SINGLE_PLAYER": "Одиночная игра",
    "X4_TR_50_SCREEN_GAME_COOP": "Совместная игра",
    "X4_TR_50_SCREEN_GAME_SIMILAR": "Похожие игры",
    "X4_TR_50_SCREEN_GAME_NO_SIMILAR": "Похожих игр не найдено.",
    "X4_TR_50_SCREEN_GAME_PUBLISHER": "Издатель",
    "X4_TR_50_SCREEN_GAME_TOUCH": "Сенсорное управление",
    "X4_TR_50_SCREEN_GAME_DETAILS_SCROLL": "Правый стик: прокрутка информации",
    "X4_TR_50_SCREEN_LOAD_REQUEST": "Запрос сеанса…",
    "X4_TR_50_SCREEN_LOAD_WAIT_RESOURCES": "Xbox готовит ресурсы…",
    "X4_TR_50_SCREEN_LOAD_AUTHORIZE": "Авторизация подключения…",
    "X4_TR_50_SCREEN_LOAD_CONNECTED": "Подключено…",
})


def literal(string):
    return json.dumps(string, ensure_ascii=False)


def decode(token):
    return ast.literal_eval(token)


def english_entries(source):
    begin = 'static const char *const table_en[X4_TR_ALL_COUNT] = {'
    start = source.index(begin) + len(begin)
    end = source.index('\n};', start)
    return source[start:end]


def english_stage(source):
    begin = '} stage_map[] = {'
    start = source.index(begin) + len(begin)
    end = source.index('\n};', start)
    return [decode(row.group(2)) for row in STAGE_ROW.finditer(source[start:end])]


def protected(string):
    # Google may alter %u, %s or %.2f. Replace these with unusual ASCII tokens.
    tokens = []
    def save(m):
        tokens.append(m.group())
        return 'ZZXCLDVAR' + str(len(tokens) - 1) + 'ZXX'
    return PRINTF.sub(save, string), tokens


def restored(string, tokens):
    for i, token in enumerate(tokens):
        marker = 'ZZXCLDVAR' + str(i) + 'ZXX'
        # Whitespace/case variations must not leak to signed printf formats.
        pattern = re.compile(r'ZZXCLDVAR\s*' + str(i) + r'\s*ZXX', re.I)
        string, count = pattern.subn(lambda _: token, string)
        if count != 1:
            raise ValueError('Formatter marker could not be recovered: ' + marker)
    return string


def translate_request(message):
    """Translate using the pinned, installed offline Argos en→ru model.

    No per-string network calls: the translation package is installed once
    in the GitHub Actions authoring environment, never in the PS4 package.
    """
    import argostranslate.translate
    result = argostranslate.translate.translate(message, "en", "ru")
    if not result:
        raise ValueError("Offline translator returned no text")
    return result


def translate_one(text):
    """Translate only natural-language segments; NEVER send C format fields to NMT.

    NMT models may change, remove or move unknown sentinel tokens. Translation
    of the segments around literal printf fields is less idiomatic but preserves
    argument count, order and type by construction (crash-safety property).
    """
    if not text or not text.strip():
        return text
    # Pure numbers, percent signs and control-unit markers are universal and
    # must never be submitted to NMT (e.g. "0 %" is not natural language).
    if not re.search(r"[A-Za-z]", text):
        return text
    source = text.replace("XCloud4", "XCloud5")
    placeholders = PRINTF.findall(source)
    segments = PRINTF.split(source)
    result = []
    for i, segment in enumerate(segments):
        if segment.strip():
            leading = segment[:len(segment) - len(segment.lstrip())]
            trailing = segment[len(segment.rstrip()):]
            translated = translate_request(segment.strip())
            result.append(leading + translated.strip() + trailing)
        else:
            result.append(segment)
        if i < len(placeholders):
            result.append(placeholders[i])
    output = "".join(result)
    if PRINTF.findall(output) != placeholders:
        raise ValueError("Translated message changed a printf placeholder: " + repr(text))
    return output


def translate_group(group):
    # The offline model is strongest with one UI sentence at a time. Emoji/ASCII
    # separators were not reliably preserved; avoid wasting an extra inference
    # and do not risk cross-message leakage.
    return [translate_one(text) for text in group]


def prepare_translations(inputs, overrides, cache):
    pending = sorted({value for key, value in inputs
                      if key not in overrides and value.strip() and value not in cache})
    groups, batch = [], []
    for item in pending:
        if batch and (len(batch) >= 6 or sum(len(x) for x in batch) + len(item) > 1100):
            groups.append(batch)
            batch = []
        batch.append(item)
    if batch:
        groups.append(batch)
    print(f"Russian generation: {len(pending)} unique new strings in {len(groups)} batches", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_map = {executor.submit(translate_group, group): group for group in groups}
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            group = future_map[future]
            translations = future.result()
            for original, translated in zip(group, translations):
                if PRINTF.findall(original) != PRINTF.findall(translated):
                    raise ValueError("Printf mismatch for: " + repr(original))
                if not translated.strip():
                    raise ValueError("Empty Russian translation for: " + repr(original))
                cache[original] = translated
            if index % 20 == 0:
                print(f"Translated {index}/{len(groups)} batches", flush=True)
    return cache


def generate_ui(source, overrides, cache):
    original = english_entries(source)
    entries = list(ENTRY.finditer(original))
    if len(entries) < 800:
        raise ValueError(f"Unexpectedly incomplete English UI table: {len(entries)} entries")
    result = original
    for m in reversed(entries):
        key, token = m.group(2), m.group(3)
        en = decode(token)
        ru = overrides[key] if key in overrides else cache[en] if en.strip() else en
        if PRINTF.findall(en) != PRINTF.findall(ru):
            raise ValueError(f"Printf mismatch in {key}: {en!r} -> {ru!r}")
        if en.strip() and not ru.strip():
            raise ValueError(f"Empty translated entry: {key}")
        result = result[:m.start(3)] + literal(ru) + result[m.end(3):]
    # The Russian language label is also present in the other six tables.
    return '/* Generated by scripts/generate_russian_localization.py; do not edit. */\n' + \
        'static const char *const table_ru[X4_TR_ALL_COUNT] = {' + result + '\n};\n'


def generate_stages(values, cache):
    if len(values) < 100:
        raise ValueError(f"Unexpectedly incomplete stage map: {len(values)}")
    rows = []
    for en in values:
        ru = cache[en] if en.strip() else en
        if PRINTF.findall(en) != PRINTF.findall(ru):
            raise ValueError("Stage printf mismatch: " + en)
        rows.append("    " + literal(ru) + ",")
    return "/* Generated Russian display-only stage messages. */\n" + \
        "static const char *const stage_ru[] = {\n" + '\n'.join(rows) + "\n};\n" + \
        "_Static_assert(sizeof(stage_ru) / sizeof(stage_ru[0]) ==\n" + \
        "    sizeof(stage_map) / sizeof(stage_map[0]),\n" + \
        '    "Russian stage translation count mismatch");\n'


def validate(source):
    en = english_entries(source)
    source_keys = [m.group(2) for m in ENTRY.finditer(en)]
    ru = UI.read_text(encoding="utf-8")
    ru_keys = [m.group(2) for m in ENTRY.finditer(ru)]
    if ru_keys != source_keys:
        raise ValueError("Russian UI IDs or ordering incomplete compared with English")
    en_values = [decode(m.group(3)) for m in ENTRY.finditer(en)]
    ru_values = [decode(m.group(3)) for m in ENTRY.finditer(ru)]
    for key, en_value, ru_value in zip(source_keys, en_values, ru_values):
        if PRINTF.findall(en_value) != PRINTF.findall(ru_value):
            raise ValueError("Invalid printf args for " + key)
        if en_value.strip() and not ru_value.strip():
            raise ValueError("Missing Russian text for " + key)
        if en_value.strip() and en_value != ru_value and not any('\u0400' <= c <= '\u04ff' for c in ru_value):
            # Keep proper nouns, protocol identifiers and universal short terms.
            if len(en_value.split()) > 1 and not re.fullmatch(r'[\w\s():/.,-]+', en_value):
                print("Review translation (may be technical):", key, file=sys.stderr)
    stage_values = english_stage(source)
    stage_ru = STAGES.read_text(encoding="utf-8")
    stage_rows = re.findall(r'^\s*("(?:\\.|[^"\\])*")\s*,\s*$', stage_ru, re.M)
    if len(stage_rows) != len(stage_values):
        raise ValueError(f"Russian stage map incomplete: {len(stage_rows)}/{len(stage_values)}")
    if not any(ord(c) >= 0x0400 and ord(c) <= 0x04ff for c in ru):
        raise ValueError("Russian table contains no Cyrillic")
    print(f"PASS Russian UI: {len(source_keys)} entries, {len(stage_rows)} stage messages, exact formatter parity")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate with a public translation service")
    parser.add_argument("--check", action="store_true", help="Validate committed translation offline")
    args = parser.parse_args()
    source = SOURCE.read_text(encoding="utf-8")
    if args.generate:
        en = [(m.group(2), decode(m.group(3))) for m in ENTRY.finditer(english_entries(source))]
        stages = english_stage(source)
        if CACHE.exists():
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        else:
            cache = {}
        cache = prepare_translations(en + [("STAGE_" + str(i), s) for i, s in enumerate(stages)],
                                     OVERRIDES, cache)
        UI.write_text(generate_ui(source, OVERRIDES, cache), encoding="utf-8")
        STAGES.write_text(generate_stages(stages, cache), encoding="utf-8")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    if args.check or args.generate:
        validate(source)
    if not args.check and not args.generate:
        parser.error("Specify --generate or --check")


if __name__ == "__main__":
    main()
