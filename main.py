"""
OLX → Telegram: новые объявления о продаже домов с оценкой удобств.
Этот файл менять не нужно. Все настройки — в config.py.
"""
import html
import json
import os
import random
import re
import sys
import time
from datetime import date
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests

import config

STATE_FILE = "seen.json"
SEEN_LIMIT = 6000
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
}

# ---------------------------------------------------------------------------
#  ПРАВИЛА ОЦЕНКИ (украинский + русский)
# ---------------------------------------------------------------------------

# Скрыть полностью
HIDE = [
    ("под снос", r"під\s+знесення|під\s+знос|на\s+знос|под\s+снос"),
    ("аварийный", r"аварійн|аварийн"),
    ("требует капремонта",
     r"(?:потребує|потребуе|требует|потрібен|потрібний|нужен|необхідн\w*|необходим\w*|під|под)\s+"
     r"(?:\w+\s+)?(?:кап\.?\s*ремонт|капремонт|капітальн\w*\s+ремонт|капитальн\w*\s+ремонт)"),
    ("без документов",
     r"без\s+документ|документів\s+немає|документів\s+нема|документов\s+нет|"
     r"документи\s+не\s+оформлен|документы\s+не\s+оформлен"),
    ("самострой", r"самобуд|самострой|самовільн|самовольн"),
    ("без фундамента", r"без\s+фундамент"),
]

TOILET_OUT = (r"(?:зручност|удобств)\w*\s+(?:на\s+)?(?:вулиц|улиц|двор|подвір)|"
              r"(?:туалет|санвузол|санузел)\w*\s+(?:на\s+)?(?:вулиц|улиц|двор|подвір)|"
              r"(?:вуличн|уличн|дворов)\w*\s+туалет|без\s+зручностей|без\s+удобств")
TOILET_IN = (r"санвузол|санвузл|санузел|санузл|с/в|туалет|\bванн[аоуіиыйяюі]|"
             r"\bванная|\bдушов|\bдуш\b|(?:зручност|удобств)\w*\s+(?:в|у)\s+(?:будинк|доме|хат)")
GAS = r"\bгаз(?!о?блок|обетон|он\b|он[аиу]|ет)|газифік|газифиц"
HEAT = r"опален|отоплен|котел|котла|котлом|котёл|тепла\s+підлог|теплый\s+пол|теплі\s+підлог"
WATER = (r"\bвод(?:а|и|у|ою|ой|опровід|опровод|опостач|оснабж)\b|водопровід|водопровод|"
         r"свердловин|скважин|колодяз|колодец|колодц|криниц")
LIGHT = r"світло\b|\bсвет\b|електр|электр"
DOCS = (r"документ|право\s+власн|право\s+собствен|кадастр|приватизован|приватизирован|"
        r"витяг|выписк|техпаспорт|технічн\w*\s+паспорт|свідоцтв|свидетельств")

EXTRAS_2 = [
    ("Канализация/септик", r"каналізац|канализац|септик|вигрібн|выгребн"),
    ("Жилой/зимний", r"зимов|зимн|утеплен|утеплений|утеплена|житлов|жилой|жилом|"
                     r"заїжджай|заїхати\s+і\s+жити|заходь\s+і\s+жив|можна\s+жити|можно\s+жить|"
                     r"заезжай|заехать\s+и\s+жить"),
]
EXTRAS_1 = [
    ("Бойлер", r"бойлер|водонагрів|водонагрев"),
    ("3 фазы", r"3\s*-?\s*х?\s*фаз|три\s+фаз|380\s*в"),
    ("Асфальт", r"асфальт"),
    ("Свежий ремонт", r"(?:свіж|нов|свеж|сучасн|современ|євро|евро)\w*\s+ремонт|"
                      r"після\s+ремонт|после\s+ремонт|відремонтован|отремонтирован"),
    ("Мебель/техника", r"меблі|мебел|побутов\w*\s+техні|бытов\w*\s+техник|з\s+технікою|с\s+техникой"),
]
REPAIR = (r"(?:потребує|потребуе|требует|потрібен|нужен|під|под)\s+"
          r"(?:косметичн\w*\s+|частков\w*\s+|частичн\w*\s+|невелик\w*\s+|небольш\w*\s+)?ремонт")

BRICK = r"цегл|кирпич"
CLADDING = (r"(?:обкладен|обкладн|облицьован|облицован|обложен|обшит)\w*\s+(?:\w+\s+)?(?:цегл|кирпич)|"
            r"(?:цегляній|кирпичной)\s+(?:сорочц|рубашк)|(?:цегляна|кирпичная)\s+облиц")
CLAY = r"саман|глинян|глинобит|глиноб|мазанк|лампач|турлук"
BLOCK = r"газоблок|піноблок|пеноблок|газобетон|пінобетон|пенобетон"
OTHER_WALLS = [("Шлакоблок", r"шлакоблок|шлакобетон"),
               ("Дерево/каркас", r"дерев'ян|деревян|\bбрус|зруб|сруб|каркасн")]

FOUND_GOOD = (r"(?:бетонн|стрічков|ленточн|монолітн|монолитн|залит)\w*\s+(?:\w+\s+)?фундамент|"
              r"фундамент\w*\s+(?:\w+\s+)?(?:бетонн|стрічков|ленточн|монолітн|монолитн|залит)")
FOUND_CELLAR = r"цокол|підвал|подвал"
FOUND_BAD = (r"тріщин|трещин|просів|просел|\bосів|\bосел\b|"
             r"фундамент\w*\s+(?:\w+\s+)?(?:потребує|требует)")

DACHA = r"\bдач[аіуеиы]\b|дачн|садівниц|садоводств|садов\w*\s+будин|садов\w*\s+дом"
LAND_HOME = r"житлов\w*\s+будин|жилого\s+дома|будівництва\s+(?:та|і)\s+обслуговування|ИЖС|ижс"

NEG_BEFORE = r"(?:без|немає|нема|нет|відсутн\w*|отсутств\w*)\s+(?:\w+\s+)?"
NEG_AFTER = (r"\w*\s+(?:\w+\s+)?(?:немає|нема\b|нет\b|відсутн|отсутств|не\s+підвед|не\s+подвед|"
             r"не\s+підключ|не\s+подключ|не\s+провед)")

Q = {
    "ru": {
        "hello": "Добрый день! Интересует ваш дом. Подскажите, пожалуйста:",
        "toilet": "есть ли санузел (туалет, ванна/душ) в доме?",
        "gas": "есть ли газ и чем отапливается дом?",
        "water": "есть ли вода (водопровод, скважина, колодец)?",
        "light": "подключено ли электричество?",
        "walls": "из какого материала стены?",
        "walls_clad": "из какого материала стены под облицовкой?",
        "found": "какой фундамент и в каком он состоянии?",
        "docs": "в порядке ли документы на дом и землю?",
        "land": "какое целевое назначение земли?",
    },
    "uk": {
        "hello": "Добрий день! Цікавить ваш будинок. Підкажіть, будь ласка:",
        "toilet": "чи є санвузол (туалет, ванна/душ) у будинку?",
        "gas": "чи є газ і чим опалюється будинок?",
        "water": "чи є вода (водопровід, свердловина, криниця)?",
        "light": "чи підключене світло?",
        "walls": "з якого матеріалу стіни?",
        "walls_clad": "з якого матеріалу стіни під облицюванням?",
        "found": "який фундамент і в якому він стані?",
        "docs": "чи в порядку документи на будинок і землю?",
        "land": "яке цільове призначення землі?",
    },
}


def norm(text):
    t = (text or "").lower().replace("ё", "е")
    for ch in "’ʼ`´‘":
        t = t.replace(ch, "'")
    return t


def found(t, pat):
    return re.search(pat, t) is not None


def status(t, pat):
    """1 = есть, -1 = явно нет, 0 = не упомянуто"""
    if found(t, NEG_BEFORE + "(?:" + pat + ")") or found(t, "(?:" + pat + ")" + NEG_AFTER):
        return -1
    return 1 if found(t, pat) else 0


def analyze(text):
    t = norm(text)
    lang = getattr(config, "QUESTION_LANG", "ru")
    q = Q.get(lang, Q["ru"])
    r = {"hide": None, "score": 0, "marks": [], "extras": [], "walls": "", "found": "",
         "notes": [], "questions": []}

    for label, pat in HIDE:
        if found(t, pat):
            r["hide"] = label
            return r

    def mark(label, st, weight, qkey):
        if st == 1:
            r["score"] += weight
            r["marks"].append("✅ " + label)
        elif st == -1:
            r["marks"].append("✖️ " + label)
            if qkey:
                r["questions"].append(q[qkey])
        else:
            r["marks"].append("❓ " + label)
            if qkey:
                r["questions"].append(q[qkey])

    water = status(t, WATER)

    # Санузел
    if found(t, TOILET_OUT):
        r["marks"].append("🚽 Санузел во дворе")
        if water == 1:
            r["score"] -= 1
            r["notes"].append("🟡 Санузел во дворе, но вода есть — можно рассмотреть")
        elif water == -1:
            r["score"] -= 5
            r["notes"].append("🔴 Санузел во дворе и нет воды")
        else:
            r["score"] -= 3
            r["notes"].append("🟠 Санузел во дворе, про воду не написано — уточнить")
    else:
        mark("Санузел в доме", status(t, TOILET_IN), 3, "toilet")

    # Газ / отопление
    gas, heat = status(t, GAS), status(t, HEAT)
    if gas == 1:
        mark("Газ", 1, 3, None)
    elif heat == 1:
        mark("Отопление" + (" (без газа)" if gas == -1 else ""), 1, 3, None)
    else:
        mark("Газ/отопление", -1 if gas == -1 else 0, 3, "gas")

    mark("Вода", water, 3, "water")
    mark("Свет", status(t, LIGHT), 3, "light")
    mark("Документы", status(t, DOCS), 3, "docs")

    for label, pat in EXTRAS_2:
        if status(t, pat) == 1:
            r["score"] += 2
            r["extras"].append(label)
    for label, pat in EXTRAS_1:
        if status(t, pat) == 1:
            r["score"] += 1
            r["extras"].append(label)

    if found(t, REPAIR):
        r["score"] -= 1
        r["notes"].append("🔧 Нужен ремонт (не капитальный)")

    # Стены
    clay, clad = found(t, CLAY), found(t, CLADDING)
    if clay and clad:
        r["score"] -= 1
        r["walls"] = "🟤 Мазанка в кирпичной облицовке"
        r["notes"].append("⚠️ Проверить стены и фундамент")
        r["questions"].append(q["walls_clad"])
    elif clay:
        r["score"] -= 2
        r["walls"] = "⚠️ Саман/глина"
    elif clad:
        r["walls"] = "❓ Кирпичная облицовка — уточнить стены"
        r["questions"].append(q["walls_clad"])
    elif found(t, BRICK):
        r["score"] += 3
        r["walls"] = "🧱 Кирпич"
    elif found(t, BLOCK):
        r["score"] += 2
        r["walls"] = "🧱 Газоблок/пеноблок"
    else:
        for label, pat in OTHER_WALLS:
            if found(t, pat):
                r["walls"] = label
                break
        if not r["walls"]:
            r["walls"] = "❓ не указано"
            r["questions"].append(q["walls"])

    # Фундамент
    if found(t, FOUND_BAD):
        r["score"] -= 3
        r["found"] = "⚠️ возможны проблемы"
        r["notes"].append("⚠️ Проверить фундамент (трещины/просадка)")
        r["questions"].append(q["found"])
    elif found(t, FOUND_GOOD):
        r["score"] += 2
        r["found"] = "✅ бетонный/ленточный"
    elif found(t, FOUND_CELLAR):
        r["score"] += 1
        r["found"] = "✅ есть цоколь/подвал"
    else:
        r["found"] = "❓ не указано"
        if q["found"] not in r["questions"]:
            r["questions"].append(q["found"])

    # Дача
    if found(t, DACHA):
        if found(t, LAND_HOME):
            r["notes"].append("🏡 Дача, но земля под жилой дом")
        else:
            r["notes"].append("⚠️ Дача — проверьте назначение земли: "
                              "«для будівництва та обслуговування житлового будинку» = можно прописаться")
            r["questions"].append(q["land"])

    return r


# ---------------------------------------------------------------------------
#  OLX
# ---------------------------------------------------------------------------

OLX_API = "https://www.olx.ua/api/v1/offers/"

# Области OLX: кусок ссылки -> id
REGION_IDS = {"pol": 15, "chk": 12, "kir": 7, "vin": 24}


def api_get(params):
    """Запрос к API OLX. Возвращает (список объявлений или None, код ответа)."""
    last = None
    for attempt in range(3):
        try:
            resp = requests.get(OLX_API, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                data = resp.json().get("data")
                if isinstance(data, list):
                    return data, 200
                last = "нет данных"
            else:
                last = resp.status_code
        except (requests.RequestException, ValueError) as e:
            last = type(e).__name__
        time.sleep(5 * (attempt + 1))
    return None, last


def search_params(url, category_id):
    """Переводит ссылку OLX в параметры API."""
    p = urlparse(url)
    slug = [s for s in p.path.split("/") if s][-1]
    region_id = REGION_IDS.get(slug)
    if region_id is None:
        raise ValueError(f"неизвестная область «{slug}»")
    params = {"offset": 0, "limit": 50, "category_id": category_id,
              "region_id": region_id, "sort_by": "created_at:desc"}
    for k, v in parse_qsl(p.query):
        if k in ("min_id", "reason", "search[order]", "page"):
            continue
        if k.startswith("search[") and k.endswith("]"):
            params[k[7:-1]] = v
        else:
            params[k] = v
    return params


def detect_category(state):
    """Находит id категории «Продаж будинків» (один раз, потом берёт из памяти)."""
    if getattr(config, "CATEGORY_ID", None):
        return config.CATEGORY_ID
    if state.get("category_id"):
        return state["category_id"]
    counts, examples = {}, {}
    for region_id in REGION_IDS.values():
        items, code = api_get({"query": "продам будинок", "limit": 50, "region_id": region_id})
        if items is None:
            print("Категория: ответ", code)
            return None
        for it in items:
            cat = it.get("category") or {}
            if isinstance(cat, dict) and cat.get("id"):
                counts[cat["id"]] = counts.get(cat["id"], 0) + 1
                examples.setdefault(cat["id"], []).append(it.get("title") or "")
        time.sleep(2)
    if not counts:
        return None
    cid = max(counts, key=counts.get)
    state["category_id"] = cid
    sample = "\n".join("• " + html.escape(t) for t in examples[cid][:3])
    tg_send(f"🔧 Определила категорию «Продажа домов»: id {cid}. Примеры:\n{sample}\n"
            f"Если это не дома на продажу — напишите Claude.")
    return cid


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def params_text(params):
    out = []
    for p in params or []:
        if not isinstance(p, dict):
            continue
        val = p.get("value")
        if isinstance(val, dict):
            val = val.get("label") or val.get("value") or val.get("key") or ""
        if not val:
            val = p.get("normalizedValue") or ""
        if p.get("key") == "price":
            continue
        out.append(f"{p.get('name') or p.get('key') or ''}: {val}")
    return "\n".join(out)


def ad_info(ad):
    price = "цена не указана"
    for p in ad.get("params") or []:
        if isinstance(p, dict) and p.get("key") == "price" and isinstance(p.get("value"), dict):
            v = p["value"]
            price = v.get("label") or f"{v.get('value', '')} {v.get('currency', '')}".strip() or price
    pr = ad.get("price")
    if isinstance(pr, dict):
        rp = pr.get("regularPrice") or {}
        if pr.get("displayValue"):
            price = pr["displayValue"]
        elif isinstance(rp, dict) and rp.get("value"):
            price = f"{rp['value']} {rp.get('currencyCode', '')}".strip()

    loc = ad.get("location") or {}
    city = loc.get("cityName") or (loc.get("city") or {}).get("name") or ""
    region = loc.get("regionName") or (loc.get("region") or {}).get("name") or ""
    place = ", ".join(x for x in (city, region) if x)

    photo = ""
    photos = ad.get("photos") or []
    if photos:
        ph = photos[0]
        if isinstance(ph, dict):
            ph = ph.get("link") or ph.get("url") or ""
        photo = str(ph).replace("{width}", "800").replace("{height}", "600")

    url = str(ad.get("url") or "")
    if url.startswith("/"):
        url = "https://www.olx.ua" + url

    title = str(ad.get("title") or "")
    text = "\n".join([title, strip_html(ad.get("description")), params_text(ad.get("params"))])
    return {"id": str(ad.get("id")), "title": title, "price": price, "place": place,
            "photo": photo, "url": url, "text": text}


# ---------------------------------------------------------------------------
#  Telegram
# ---------------------------------------------------------------------------

def tg_send(text, photo=None, url=None):
    payload = {"chat_id": TG_CHAT, "text": text[:4000], "parse_mode": "HTML",
               "link_preview_options": {"is_disabled": True}}
    if photo:
        payload["link_preview_options"] = {"url": photo, "prefer_large_media": True,
                                           "show_above_text": True}
    if url:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": "Открыть на OLX", "url": url}]]}
    api = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    for _ in range(3):
        try:
            resp = requests.post(api, json=payload, timeout=30)
        except requests.RequestException:
            time.sleep(3)
            continue
        if resp.ok:
            return True
        if resp.status_code == 429:
            wait = resp.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(int(wait) + 1)
            continue
        print("Telegram error:", resp.status_code, resp.text[:300])
        if photo:
            payload["link_preview_options"] = {"is_disabled": True}
            photo = None
            continue
        return False
    return False


def card(info, labels, a):
    e = html.escape
    hot = a["score"] >= config.HOT_SCORE
    lines = [
        ("🔥 " if hot else "🏠 ") + f"<b>{e(info['title'])}</b>",
        f"💰 {e(info['price'])}" + (f"  ·  📍 {e(info['place'])}" if info["place"] else ""),
        f"🔎 {e(' + '.join(labels))}",
        f"<b>Баллы: {a['score']}</b>",
        "",
        "   ".join(a["marks"]),
    ]
    if a["extras"]:
        lines.append("➕ " + ", ".join(a["extras"]))
    lines.append(f"Стены: {e(a['walls'])}")
    lines.append(f"🏗️ Фундамент: {e(a['found'])}")
    for n in a["notes"]:
        lines.append(e(n))
    if a["questions"]:
        q = Q.get(getattr(config, "QUESTION_LANG", "ru"), Q["ru"])
        msg = q["hello"] + "\n" + "\n".join("– " + x for x in a["questions"])
        lines += ["", "💬 <b>Вопросы продавцу</b> (нажмите, чтобы скопировать):",
                  f"<code>{e(msg)}</code>"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Запуск
# ---------------------------------------------------------------------------

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    state["seen"] = state["seen"][-SEEN_LIMIT:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def main():
    if not TG_TOKEN or not TG_CHAT:
        print("Нет TELEGRAM_TOKEN или TELEGRAM_CHAT_ID в Secrets")
        sys.exit(1)

    state = load_state()
    first_run = state is None
    if first_run:
        state = {"seen": [], "errors": {}}
    seen = set(state["seen"])
    today = date.today().isoformat()

    new = {}  # id -> {"info":..., "labels": [...]}
    total_ads = 0
    category_id = detect_category(state)
    if not category_id:
        if state["errors"].get("category") != today:
            tg_send("⚠️ OLX не отвечает (не удалось определить категорию). Напишите Claude.")
            state["errors"]["category"] = today
        if not first_run:
            save_state(state)
        sys.exit(1)

    for i, (label, url) in enumerate(config.SEARCHES):
        if i:
            time.sleep(random.uniform(2, 4))
        try:
            params = search_params(url, category_id)
        except ValueError as e:
            tg_send(f"⚠️ Поиск «{html.escape(label)}»: {html.escape(str(e))}. Напишите Claude.")
            continue
        ads, code = api_get(params)
        if ads is None:
            print(f"[{label}] не удалось прочитать (ответ: {code})")
            if state["errors"].get(label) != today:
                tg_send(f"⚠️ Не удалось прочитать поиск «{html.escape(label)}» (ответ: {code}). "
                        f"Если повторяется — напишите Claude.")
                state["errors"][label] = today
            continue
        print(f"[{label}] объявлений: {len(ads)}")
        total_ads += len(ads)
        for ad in ads:
            info = ad_info(ad)
            if info["id"] in seen or not info["url"]:
                continue
            if info["id"] in new:
                if label not in new[info["id"]]["labels"]:
                    new[info["id"]]["labels"].append(label)
            else:
                new[info["id"]] = {"info": info, "labels": [label]}

    if first_run and total_ads == 0:
        print("Первый запуск: ничего не прочитано, состояние не сохраняю")
        sys.exit(1)

    results = []
    for ad_id, item in new.items():
        a = analyze(item["info"]["text"])
        if a["hide"]:
            print(f"Скрыто ({a['hide']}): {item['info']['title']}")
        else:
            results.append((a["score"], item, a))
    results.sort(key=lambda x: x[0], reverse=True)

    limit = config.FIRST_RUN_TOP if first_run else config.MAX_PER_RUN
    to_send = results[:limit]

    if first_run:
        tg_send(f"✅ Бот запущен. Сейчас в ваших поисках {len(results)} подходящих объявлений. "
                f"Присылаю {len(to_send)} лучших, дальше — только новые.")

    for score, item, a in to_send:
        tg_send(card(item["info"], item["labels"], a), item["info"]["photo"], item["info"]["url"])
        time.sleep(1.2)

    if not first_run and len(results) > limit:
        tg_send(f"ℹ️ Ещё {len(results) - limit} новых объявлений с меньшими баллами не показаны.")

    state["seen"].extend(new.keys())
    save_state(state)
    print(f"Новых: {len(new)}, отправлено: {len(to_send)}")


if __name__ == "__main__":
    main()
