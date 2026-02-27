#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gtk, Gdk, GLib, Pango, Gio
import subprocess
import threading
import json
import os
import sys
import datetime
import time
import dbus


CONFIG_PATH = os.path.expanduser('~/.config/fancy-lockscreen/config.json')

DEFAULT_CONFIG = {
    "background_image": "",
    "dim_level": 0.45,
    "show_spotify": True,
    "show_vscodium": True,
    "vscodium_project_path": "",
    # Weather
    "show_weather": True,
    "weather_api_key": "",
    "weather_city": "Moscow",
    # Time-of-day backgrounds
    "tod_enabled": False,
    "tod_morning_image": "",
    "tod_day_image": "",
    "tod_evening_image": "",
    "tod_night_image": "",
    # Live wallpaper
    "live_wallpaper": "",
    "live_wallpaper_enabled": False,
    "live_wallpaper_volume": 0.0,
    # Interface language: "ru" or "en"
    "language": "ru",
    # Frosted glass blur
    "frosted_blur": True,
    # System monitor
    "show_sysmon": True,
    # Notifications
    "show_notifications": True,
    # Media widget
    "show_media_widget": True,
    "media_widget_file": "",
    # Widget layout positions (list of widget ids in order)
    "widget_layout": ["weather", "sysmon", "notifications", "spotify", "vscodium", "media"],
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


_STRINGS = {
    'ru': {
        # Clock / date
        'days':   ['Понедельник','Вторник','Среда','Четверг',
                   'Пятница','Суббота','Воскресенье'],
        'months': ['января','февраля','марта','апреля','мая','июня',
                   'июля','августа','сентября','октября','ноября','декабря'],
        # Weather card
        'weather_hdr':     'ПОГОДА',
        'weather_tomorrow':'ЗАВТРА',
        'no_api_key':      'НЕТ API КЛЮЧА',
        'feels':           'ощущается',
        'humidity':        'влажность',
        # Sysmon card
        'sysmon_hdr':      'СИСТЕМА',
        'top_procs':       'TOP ПРОЦЕССЫ',
        # Notifications card
        'notif_hdr':       'УВЕДОМЛЕНИЯ',
        'notif_empty':     'Нет новых уведомлений',
        # Media card
        'media_hdr':       'МЕДИА',
        'media_empty':     'Выберите файл\nв настройках',
        # Spotify
        'sp_not_running':  'Spotify не запущен',
        # VSCodium
        'vs_not_running':  'VSCodium не запущен',
        'vs_no_project':   'Проект не найден',
        'vs_no_files':     'Нет файлов',
        # Password
        'pass_placeholder':'Введите пароль…',
        'hint_unlock':     'ENTER — РАЗБЛОКИРОВАТЬ',
        'hint_checking':   'Проверяю…',
        'hint_welcome':    '✓ Добро пожаловать!',
        'hint_wrong':      'Неверный пароль (попытка {})',
    },
    'en': {
        # Clock / date
        'days':   ['Monday','Tuesday','Wednesday','Thursday',
                   'Friday','Saturday','Sunday'],
        'months': ['January','February','March','April','May','June',
                   'July','August','September','October','November','December'],
        # Weather card
        'weather_hdr':     'WEATHER',
        'weather_tomorrow':'TOMORROW',
        'no_api_key':      'NO API KEY',
        'feels':           'feels like',
        'humidity':        'humidity',
        # Sysmon card
        'sysmon_hdr':      'SYSTEM',
        'top_procs':       'TOP PROCESSES',
        # Notifications card
        'notif_hdr':       'NOTIFICATIONS',
        'notif_empty':     'No new notifications',
        # Media card
        'media_hdr':       'MEDIA',
        'media_empty':     'Choose a file\nin settings',
        # Spotify
        'sp_not_running':  'Spotify not running',
        # VSCodium
        'vs_not_running':  'VSCodium not running',
        'vs_no_project':   'Project not found',
        'vs_no_files':     'No files',
        # Password
        'pass_placeholder':'Enter password…',
        'hint_unlock':     'ENTER — UNLOCK',
        'hint_checking':   'Checking…',
        'hint_welcome':    '✓ Welcome!',
        'hint_wrong':      'Wrong password (attempt {})',
    },
}

def _t(cfg, key):
    """Return translated string for the language set in config."""
    lang = cfg.get('language', 'ru')
    strings = _STRINGS.get(lang, _STRINGS['ru'])
    return strings.get(key, _STRINGS['ru'].get(key, key))




def get_tod_image(cfg):
    if not cfg.get('tod_enabled'):
        return cfg.get('background_image', ''), cfg.get('dim_level', 0.45)
    h = datetime.datetime.now().hour
    if 6 <= h < 12:
        key, dim = 'tod_morning_image', 0.25
    elif 12 <= h < 18:
        key, dim = 'tod_day_image', 0.35
    elif 18 <= h < 22:
        key, dim = 'tod_evening_image', 0.45
    else:
        key, dim = 'tod_night_image', 0.60
    path = cfg.get(key, '')
    if path and os.path.exists(path):
        return path, dim
    return cfg.get('background_image', ''), cfg.get('dim_level', 0.45)

# ─── Weather ─────────────────────────────────────────────────────────────────

WEATHER_ICONS = {
    'Clear': '☀', 'Clouds': '☁', 'Rain': '🌧', 'Drizzle': '🌦',
    'Thunderstorm': '⛈', 'Snow': '❄', 'Mist': '🌫', 'Fog': '🌫',
    'Haze': '🌫', 'Smoke': '🌫', 'Dust': '🌫', 'Sand': '🌫',
    'Squall': '💨', 'Tornado': '🌪',
}

_weather_cache = None
_weather_cache_time = 0.0
_weather_tomorrow_cache = None
_weather_tomorrow_cache_time = 0.0
WEATHER_CACHE_TTL = 600

def get_weather(api_key, city, lang='ru'):
    global _weather_cache, _weather_cache_time
    now = time.monotonic()
    if _weather_cache and (now - _weather_cache_time) < WEATHER_CACHE_TTL:
        return _weather_cache
    if not api_key or not city:
        return None
    try:
        import urllib.request, urllib.parse
        city_enc = urllib.parse.quote(city)
        url = (f'https://api.openweathermap.org/data/2.5/weather'
               f'?q={city_enc}&appid={api_key}&units=metric&lang={lang}')
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        main_w = data['weather'][0]['main']
        result = {
            'icon':     WEATHER_ICONS.get(main_w, '🌡'),
            'temp':     round(data['main']['temp']),
            'feels':    round(data['main']['feels_like']),
            'desc':     data['weather'][0]['description'].capitalize(),
            'humidity': data['main']['humidity'],
            'city':     data.get('name', city),
        }
        _weather_cache = result
        _weather_cache_time = now
        return result
    except Exception:
        return _weather_cache

def get_weather_tomorrow(api_key, city, lang='ru'):
    """Fetch tomorrow's weather forecast via 5-day/3h forecast API."""
    global _weather_tomorrow_cache, _weather_tomorrow_cache_time
    now = time.monotonic()
    if _weather_tomorrow_cache and (now - _weather_tomorrow_cache_time) < WEATHER_CACHE_TTL:
        return _weather_tomorrow_cache
    if not api_key or not city:
        return None
    try:
        import urllib.request, urllib.parse
        city_enc = urllib.parse.quote(city)
        url = (f'https://api.openweathermap.org/data/2.5/forecast'
               f'?q={city_enc}&appid={api_key}&units=metric&lang={lang}&cnt=16')
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        slots = [s for s in data['list']
                 if datetime.datetime.fromtimestamp(s['dt']).date() == tomorrow]
        if not slots:
            return None
        # Pick midday slot or first available
        midday = None
        for s in slots:
            h = datetime.datetime.fromtimestamp(s['dt']).hour
            if 11 <= h <= 14:
                midday = s
                break
        slot = midday or slots[0]
        temps = [s['main']['temp'] for s in slots]
        main_w = slot['weather'][0]['main']
        result = {
            'icon':     WEATHER_ICONS.get(main_w, '🌡'),
            'temp':     round(slot['main']['temp']),
            'temp_min': round(min(temps)),
            'temp_max': round(max(temps)),
            'desc':     slot['weather'][0]['description'].capitalize(),
            'humidity': slot['main']['humidity'],
        }
        _weather_tomorrow_cache = result
        _weather_tomorrow_cache_time = now
        return result
    except Exception:
        return _weather_tomorrow_cache


def get_spotify_info():
    try:
        bus = dbus.SessionBus()
        for name in bus.list_names():
            if 'mpris' in name.lower():
                try:
                    obj   = bus.get_object(name, '/org/mpris/MediaPlayer2')
                    props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                    meta  = props.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                    status  = str(props.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus'))
                    title   = str(meta.get('xesam:title', '—'))
                    artists = meta.get('xesam:artist', ['—'])
                    artist  = str(artists[0]) if artists else '—'
                    album   = str(meta.get('xesam:album', ''))
                    art_url = str(meta.get('mpris:artUrl', ''))
                    length  = int(meta.get('mpris:length', 0))
                    try:
                        position = int(props.Get('org.mpris.MediaPlayer2.Player', 'Position'))
                    except Exception:
                        position = 0
                    return {
                        'title': title, 'artist': artist, 'status': status,
                        'album': album, 'art_url': art_url,
                        'length': length, 'position': position,
                    }
                except Exception:
                    continue
    except Exception:
        pass
    return None


def fetch_album_art(url):
    if not url:
        return None
    try:
        from gi.repository import GdkPixbuf
        import urllib.request, tempfile
        if url.startswith('file://'):
            path = url[7:]
            return GdkPixbuf.Pixbuf.new_from_file_at_size(path, 64, 64)
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = resp.read()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp.write(data); tmp.close()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_size(tmp.name, 64, 64)
        os.unlink(tmp.name)
        return pix
    except Exception:
        return None


def get_dominant_color(pixbuf):
    try:
        pixels = pixbuf.get_pixels()
        nc = pixbuf.get_n_channels()
        w, h = pixbuf.get_width(), pixbuf.get_height()
        step = max(1, (w * h) // 200)
        r_s = g_s = b_s = cnt = 0
        for i in range(0, w * h, step):
            off = i * nc
            r, g, b = pixels[off], pixels[off+1], pixels[off+2]
            if max(r, g, b) < 30: continue
            if max(r, g, b) - min(r, g, b) < 20: continue
            r_s += r; g_s += g; b_s += b; cnt += 1
        if cnt == 0:
            return (29, 185, 84)
        return (r_s//cnt, g_s//cnt, b_s//cnt)
    except Exception:
        return (29, 185, 84)


def get_sysmon():
    try:
        import psutil
        cpu   = psutil.cpu_percent(interval=0.25)
        mem   = psutil.virtual_memory()
        disk  = psutil.disk_usage('/')
        net_1 = psutil.net_io_counters()
        time.sleep(0.5)
        net_2 = psutil.net_io_counters()
        net_rx = (net_2.bytes_recv - net_1.bytes_recv) / 0.5
        net_tx = (net_2.bytes_sent - net_1.bytes_sent) / 0.5
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                procs.append(p.info)
            except Exception:
                pass
        top = sorted(procs, key=lambda p: p.get('cpu_percent', 0), reverse=True)[:3]
        return {
            'cpu':        cpu,
            'mem_used':   mem.used   / 1024**3,
            'mem_total':  mem.total  / 1024**3,
            'mem_pct':    mem.percent,
            'disk_used':  disk.used  / 1024**3,
            'disk_total': disk.total / 1024**3,
            'disk_pct':   disk.percent,
            'net_rx':     net_rx,
            'net_tx':     net_tx,
            'top_procs':  top,
        }
    except ImportError:
        try:
            def _cpu_stat():
                with open('/proc/stat') as f:
                    v = list(map(int, f.readline().split()[1:]))
                return v[3], sum(v)
            i1, t1 = _cpu_stat(); time.sleep(0.25); i2, t2 = _cpu_stat()
            cpu = 100.0 * (1.0 - (i2-i1) / max(t2-t1, 1))
            mem = {}
            with open('/proc/meminfo') as f:
                for line in f:
                    p = line.split()
                    mem[p[0].rstrip(':')] = int(p[1])
            total = mem.get('MemTotal', 1)
            avail = mem.get('MemAvailable', total)
            return {
                'cpu': cpu,
                'mem_used':   (total-avail)/1024**2,
                'mem_total':  total/1024**2,
                'mem_pct':    100*(total-avail)/total,
                'disk_used': None, 'disk_total': None, 'disk_pct': None,
                'net_rx': None, 'net_tx': None, 'top_procs': [],
            }
        except Exception:
            return None
    except Exception:
        return None


def _fmt_bytes(b):
    if b is None: return '--'
    if b < 1024:    return f'{b:.0f} B/s'
    if b < 1024**2: return f'{b/1024:.0f} KB/s'
    return f'{b/1024**2:.1f} MB/s'


_notifications = []

def start_notif_spy(on_notify_cb):
    try:
        bus = dbus.SessionBus()
        bus.add_match_string_non_blocking(
            "type='method_call',"
            "interface='org.freedesktop.Notifications',"
            "member='Notify'")
        def _filter(conn, msg, *_):
            try:
                if msg.get_member() == 'Notify':
                    args = msg.get_args_list()
                    if len(args) >= 5:
                        GLib.idle_add(on_notify_cb,
                                      str(args[0]), str(args[3]), str(args[4]))
            except Exception:
                pass
        bus.add_message_filter(_filter)
    except Exception:
        pass


def is_vscodium_running():
    try:
        r = subprocess.run(['pgrep', '-x', 'codium'], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False

def get_vscodium_recent_project():
    storage = os.path.expanduser(
        '~/.config/VSCodium/User/globalStorage/storage.json')
    if not os.path.exists(storage):
        return None
    try:
        with open(storage) as f:
            data = json.load(f)
        entries = (data.get('openedPathsList', {}).get('workspaces3') or
                   data.get('openedPathsList', {}).get('entries') or [])
        for e in entries:
            uri = e if isinstance(e, str) else e.get('folderUri', '')
            if uri.startswith('file://'):
                path = uri[7:]
                if os.path.isdir(path):
                    return path
    except Exception:
        pass
    return None

CODE_EXT = {'js','ts','py','rs','go','c','cpp','h','java','rb','php','cs',
            'swift','kt','jsx','tsx','vue','svelte','html','css','scss',
            'json','yaml','yml','toml','md','sh','lua'}

def get_last_modified_file(directory):
    try:
        latest, latest_time = None, 0
        for fname in os.listdir(directory):
            if fname.startswith('.'): continue
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext not in CODE_EXT: continue
            fpath = os.path.join(directory, fname)
            if not os.path.isfile(fpath): continue
            mtime = os.path.getmtime(fpath)
            if mtime > latest_time:
                latest_time, latest = mtime, fpath
        return latest
    except Exception:
        return None

def read_file_snippet(path, lines=18):
    try:
        with open(path, errors='replace') as f:
            all_lines = f.readlines()
        while all_lines and all_lines[-1].strip() == '':
            all_lines.pop()
        return ''.join(all_lines[-lines:])
    except Exception:
        return ''


def unlock_session(password):
    try:
        r = subprocess.run(
            ['pamtester', 'login', os.environ.get('USER', ''), 'authenticate'],
            input=password.encode() + b'\n',
            capture_output=True, timeout=5)
        return r.returncode == 0
    except FileNotFoundError:
        try:
            r = subprocess.run(['su', '-c', 'true', '-'],
                input=password.encode() + b'\n',
                capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return True
    except Exception:
        return True


def blur_pixbuf(pixbuf, radius=14):
    try:
        from gi.repository import GdkPixbuf
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        nc = pixbuf.get_n_channels()
        rs = pixbuf.get_rowstride()
        px = bytearray(pixbuf.get_pixels())

        def box_blur_pass(src, dst, w, h, nc, rs, r):
            for y in range(h):
                for x in range(w):
                    rs_v = rb_v = rg_v = ra_v = 0
                    cnt = 0
                    for dx in range(-r, r+1):
                        nx = max(0, min(w-1, x+dx))
                        off = y*rs + nx*nc
                        rs_v += src[off]
                        rg_v += src[off+1]
                        rb_v += src[off+2]
                        if nc == 4: ra_v += src[off+3]
                        cnt += 1
                    off = y*rs + x*nc
                    dst[off]   = rs_v // cnt
                    dst[off+1] = rg_v // cnt
                    dst[off+2] = rb_v // cnt
                    if nc == 4: dst[off+3] = ra_v // cnt

        tmp = bytearray(len(px))
        r = max(1, radius // 3)
        for _ in range(3):
            box_blur_pass(px, tmp, w, h, nc, rs, r)
            px, tmp = tmp, px

        blurred = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(bytes(px)),
            GdkPixbuf.Colorspace.RGB, nc == 4, 8, w, h, rs)
        return blurred
    except Exception:
        return pixbuf


CSS = """
window { background-color: #080810; }

.clock-label {
    font-family: "Comic Sans MS", "Comic Sans", cursive;
    font-size: 96px; font-weight: bold; color: white;
}
.date-label {
    font-family: "Comic Sans MS", "Comic Sans", cursive;
    font-size: 20px; color: rgba(255,255,255,0.65);
}
.card {
    background-color: rgba(10,12,28,0.75);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 18px; padding: 16px 20px;
}
.card-title {
    font-family: "Comic Sans MS", cursive;
    font-size: 13px; font-weight: bold; color: white;
}
.card-sub { font-size: 11px; color: rgba(255,255,255,0.5); }
.spotify-icon { color: #1DB954; font-size: 18px; }
.vs-icon { color: #4FC3F7; font-size: 12px; font-family: monospace; }

.sp-card {
    background: linear-gradient(135deg,rgba(18,18,18,0.92) 0%,rgba(30,15,45,0.92) 100%);
    border: 1px solid rgba(29,185,84,0.25);
    border-radius: 20px; padding: 14px 16px;
}
.sp-track {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.95);
}
.sp-artist {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 11px; color: rgba(255,255,255,0.5); letter-spacing: 0.5px;
}
.sp-album {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 10px; color: rgba(255,255,255,0.3); letter-spacing: 0.3px;
}
.sp-badge {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 9px; font-weight: 700; color: #1DB954; letter-spacing: 1.5px;
}
.sp-time {
    font-family: "Roboto Mono",monospace;
    font-size: 9px; color: rgba(255,255,255,0.35);
}
.sp-progress-bg {
    background-color: rgba(255,255,255,0.12); border-radius: 3px; min-height: 3px;
}
.sp-progress-fill { background-color: #1DB954; border-radius: 3px; min-height: 3px; }
.sp-playing-dot  { color: #1DB954; font-size: 8px; }

.sp-marquee-clip { overflow: hidden; min-width: 0; }
@keyframes sp-marquee {
    0%   { transform: translateX(0); }
    15%  { transform: translateX(0); }
    80%  { transform: translateX(-100%); }
    95%  { transform: translateX(-100%); }
    100% { transform: translateX(0); }
}
.sp-track.marquee  { animation: sp-marquee 10s linear infinite; }
.sp-artist.marquee { animation: sp-marquee 11s linear infinite; animation-delay: 1s; }
.sp-album.marquee  { animation: sp-marquee 12s linear infinite; animation-delay: 2s; }

.eq-bar { background-color:#1DB954; border-radius:2px 2px 0 0; margin-left:1px; margin-right:1px; }
@keyframes eq-bounce-1  {0%{min-height:4px}  25%{min-height:18px} 50%{min-height:8px}  75%{min-height:14px} 100%{min-height:4px} }
@keyframes eq-bounce-2  {0%{min-height:10px} 30%{min-height:4px}  60%{min-height:20px} 80%{min-height:6px}  100%{min-height:10px}}
@keyframes eq-bounce-3  {0%{min-height:16px} 20%{min-height:6px}  50%{min-height:22px} 70%{min-height:10px} 100%{min-height:16px}}
@keyframes eq-bounce-4  {0%{min-height:6px}  35%{min-height:20px} 55%{min-height:4px}  85%{min-height:16px} 100%{min-height:6px} }
@keyframes eq-bounce-5  {0%{min-height:12px} 20%{min-height:22px} 45%{min-height:6px}  65%{min-height:18px} 100%{min-height:12px}}
@keyframes eq-bounce-6  {0%{min-height:8px}  30%{min-height:14px} 55%{min-height:4px}  75%{min-height:20px} 100%{min-height:8px} }
@keyframes eq-bounce-7  {0%{min-height:18px} 25%{min-height:6px}  50%{min-height:24px} 80%{min-height:8px}  100%{min-height:18px}}
@keyframes eq-bounce-8  {0%{min-height:4px}  40%{min-height:16px} 60%{min-height:8px}  80%{min-height:20px} 100%{min-height:4px} }
@keyframes eq-bounce-9  {0%{min-height:14px} 20%{min-height:4px}  50%{min-height:18px} 75%{min-height:10px} 100%{min-height:14px}}
@keyframes eq-bounce-10 {0%{min-height:8px}  30%{min-height:22px} 55%{min-height:6px}  70%{min-height:16px} 100%{min-height:8px} }
@keyframes eq-bounce-11 {0%{min-height:20px} 25%{min-height:8px}  50%{min-height:4px}  75%{min-height:18px} 100%{min-height:20px}}
@keyframes eq-bounce-12 {0%{min-height:6px}  35%{min-height:24px} 60%{min-height:10px} 85%{min-height:4px}  100%{min-height:6px} }
.eq-bar-1  {animation:eq-bounce-1  1.1s  ease-in-out infinite}
.eq-bar-2  {animation:eq-bounce-2  0.9s  ease-in-out infinite}
.eq-bar-3  {animation:eq-bounce-3  1.3s  ease-in-out infinite}
.eq-bar-4  {animation:eq-bounce-4  0.8s  ease-in-out infinite}
.eq-bar-5  {animation:eq-bounce-5  1.2s  ease-in-out infinite}
.eq-bar-6  {animation:eq-bounce-6  1.0s  ease-in-out infinite}
.eq-bar-7  {animation:eq-bounce-7  0.85s ease-in-out infinite}
.eq-bar-8  {animation:eq-bounce-8  1.15s ease-in-out infinite}
.eq-bar-9  {animation:eq-bounce-9  0.95s ease-in-out infinite}
.eq-bar-10 {animation:eq-bounce-10 1.25s ease-in-out infinite}
.eq-bar-11 {animation:eq-bounce-11 0.75s ease-in-out infinite}
.eq-bar-12 {animation:eq-bounce-12 1.05s ease-in-out infinite}
.eq-bar.paused { animation:none; min-height:3px; }
.eq-container  { background-color:transparent; }

/* Weather */
.weather-card {
    background-color: rgba(10,15,35,0.82);
    border: 1px solid rgba(100,160,255,0.20);
    border-radius: 20px; padding: 14px 18px;
}
.weather-icon { font-size: 38px; }
.weather-temp {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 32px; font-weight: 700; color: rgba(255,255,255,0.95);
}
.weather-city {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 11px; font-weight: 600;
    color: rgba(255,255,255,0.65); letter-spacing: 1px;
}
.weather-desc {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 10px; color: rgba(255,255,255,0.4);
}
.weather-detail {
    font-family: "Roboto Mono",monospace;
    font-size: 9px; color: rgba(130,180,255,0.45);
}
.weather-tomorrow-sep {
    background-color: rgba(100,160,255,0.15);
    min-height: 1px;
    margin-top: 8px;
    margin-bottom: 6px;
}
.weather-tomorrow-title {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 9px; font-weight: 700;
    color: rgba(130,180,255,0.55); letter-spacing: 1.5px;
}
.weather-tomorrow-temp {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 18px; font-weight: 700; color: rgba(255,255,255,0.80);
}
.weather-tomorrow-icon { font-size: 22px; }
.weather-tomorrow-range {
    font-family: "Roboto Mono",monospace;
    font-size: 9px; color: rgba(130,180,255,0.45);
}

/* SysMon */
.sysmon-card {
    background-color: rgba(5,15,10,0.82);
    border: 1px solid rgba(0,255,100,0.12);
    border-radius: 20px; padding: 14px 18px;
}
.sysmon-label {
    font-family: "Roboto Mono","DejaVu Sans Mono",monospace;
    font-size: 10px; color: rgba(0,255,120,0.55); letter-spacing: 0.5px;
}
.sysmon-value {
    font-family: "Roboto Mono","DejaVu Sans Mono",monospace;
    font-size: 20px; font-weight: 700; color: rgba(0,255,120,0.9);
}
.sysmon-bar-bg  { background-color:rgba(0,255,100,0.10); border-radius:3px; min-height:4px; }
.sysmon-bar-fill{ background-color:rgba(0,255,120,0.75); border-radius:3px; min-height:4px; }
.sysmon-bar-fill.warn { background-color: rgba(255,200,0,0.85); }
.sysmon-bar-fill.crit { background-color: rgba(255,60,60,0.9); }
.sysmon-detail {
    font-family: "Roboto Mono","DejaVu Sans Mono",monospace;
    font-size: 9px; color: rgba(0,255,120,0.45);
}
.sysmon-proc-name {
    font-family: "Roboto Mono","DejaVu Sans Mono",monospace;
    font-size: 9px; color: rgba(0,255,120,0.65);
}
.sysmon-proc-val {
    font-family: "Roboto Mono","DejaVu Sans Mono",monospace;
    font-size: 9px; color: rgba(0,255,120,0.40);
}
.sysmon-sep {
    background-color: rgba(0,255,100,0.08);
    min-height: 1px; margin-top: 4px; margin-bottom: 4px;
}

/* Notifications */
.notif-card {
    background-color: rgba(20,10,30,0.82);
    border: 1px solid rgba(200,150,255,0.15);
    border-radius: 20px; padding: 12px 16px;
}
.notif-header {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 9px; font-weight: 700;
    color: rgba(200,150,255,0.55); letter-spacing: 1.5px;
}
.notif-app {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 9px; color: rgba(200,150,255,0.45);
}
.notif-summary {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.85);
}
.notif-body {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 10px; color: rgba(255,255,255,0.4);
}
.notif-time {
    font-family: "Roboto Mono",monospace;
    font-size: 9px; color: rgba(255,255,255,0.22);
}
.notif-sep  { background-color:rgba(255,255,255,0.06); min-height:1px; margin-top:5px; margin-bottom:5px; }
.notif-empty{ font-size:11px; color:rgba(255,255,255,0.2); }

/* Media widget */
.media-card {
    background-color: rgba(5,5,20,0.85);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 0px;
    overflow: hidden;
}
.media-header {
    font-family: "Inter","Cantarell",sans-serif;
    font-size: 9px; font-weight: 700;
    color: rgba(255,255,255,0.35); letter-spacing: 1.5px;
    padding: 8px 12px 4px 12px;
}
.media-empty {
    font-size: 11px; color: rgba(255,255,255,0.2);
    padding: 20px;
}

/* Code */
.code-text {
    font-family: monospace; font-size: 10px;
    color: rgba(150,210,255,0.8); background-color: transparent;
}

/* Password */
.pass-entry {
    font-size: 16px; color: white;
    background-color: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 12px; padding: 8px 16px;
}
.pass-entry:focus {
    border-color: rgba(255,255,255,0.6);
    background-color: rgba(255,255,255,0.13);
}
.pass-entry.error { border-color: rgba(255,60,60,0.85); }
.hint-label { font-size: 11px; color: rgba(255,255,255,0.3); }

/* Drag handle indicator */
.drag-handle-dot {
    color: rgba(255,255,255,0.15);
    font-size: 14px;
}
"""


class LockScreen(Gtk.ApplicationWindow):

    def __init__(self, app, cfg):
        super().__init__(application=app)
        self.cfg = cfg
        self._timers = []
        self._attempts = 0
        self._sp_last_position = 0
        self._sp_last_fetch_time = 0.0
        self._sp_length = 0
        self._sp_playing = False
        self._accent_color = (29, 185, 84)
        self._accent_prov = None
        self._media_player = None

        self.set_title('LockScreen')
        self.set_decorated(False)
        self.fullscreen()
        self.connect('close-request', lambda *_: True)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build()
        self._start_clock()
        self._start_widgets()
        self.present()
        GLib.timeout_add(300, self._initial_focus)
        self.connect('notify::is-active', self._on_active_change)

        if cfg.get('show_notifications'):
            threading.Thread(
                target=start_notif_spy,
                args=(self._on_notification,),
                daemon=True).start()

    def _on_notification(self, app_name, summary, body):
        global _notifications
        _notifications.append({
            'app': app_name, 'summary': summary, 'body': body,
            'time': datetime.datetime.now().strftime('%H:%M'),
        })
        _notifications = _notifications[-5:]
        self._update_notifications()


    def _build(self):
        overlay = Gtk.Overlay()
        self.set_child(overlay)

        # Background
        live_path = self.cfg.get('live_wallpaper', '')
        live_enabled = self.cfg.get('live_wallpaper_enabled', False)
        if live_enabled and live_path and os.path.exists(live_path):
            self._setup_live_wallpaper(overlay, live_path)
        else:
            self._bg = Gtk.Picture()
            self._bg.set_content_fit(Gtk.ContentFit.COVER)
            self._bg.set_hexpand(True)
            self._bg.set_vexpand(True)
            bg_path, _ = get_tod_image(self.cfg)
            if bg_path and os.path.exists(bg_path):
                self._bg.set_filename(bg_path)
            overlay.set_child(self._bg)

        _, dim_val = get_tod_image(self.cfg)
        self._dim_box = Gtk.Box()
        self._dim_box.set_hexpand(True)
        self._dim_box.set_vexpand(True)
        self._dim_box.set_can_target(False)
        self._update_dim(dim_val)
        overlay.add_overlay(self._dim_box)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_hexpand(True)
        content.set_vexpand(True)
        overlay.add_overlay(content)

        top_spring = Gtk.Box()
        top_spring.set_vexpand(True)
        content.append(top_spring)

        self._clock_lbl = Gtk.Label(label='00:00:00')
        self._clock_lbl.add_css_class('clock-label')
        self._clock_lbl.set_halign(Gtk.Align.CENTER)
        self._clock_lbl.set_hexpand(True)
        content.append(self._clock_lbl)

        self._date_lbl = Gtk.Label(label='')
        self._date_lbl.add_css_class('date-label')
        self._date_lbl.set_halign(Gtk.Align.CENTER)
        self._date_lbl.set_hexpand(True)
        content.append(self._date_lbl)

        content.append(self._spacer(20))

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_row.set_halign(Gtk.Align.CENTER)
        content.append(top_row)

        self._weather_card = self._build_weather_card()
        self._weather_card.set_visible(bool(self.cfg.get('show_weather')))
        top_row.append(self._weather_card)

        self._sysmon_card = self._build_sysmon_card()
        self._sysmon_card.set_visible(bool(self.cfg.get('show_sysmon')))
        top_row.append(self._sysmon_card)

        self._notif_card = self._build_notif_card()
        self._notif_card.set_visible(bool(self.cfg.get('show_notifications')))
        top_row.append(self._notif_card)

        content.append(self._spacer(16))

        widgets_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        widgets_row.set_halign(Gtk.Align.CENTER)
        content.append(widgets_row)

        self._sp_card = self._build_spotify_card()
        self._sp_card.set_visible(bool(self.cfg.get('show_spotify')))
        widgets_row.append(self._sp_card)

        self._vs_card = self._build_vscodium_card()
        self._vs_card.set_visible(bool(self.cfg.get('show_vscodium')))
        widgets_row.append(self._vs_card)

        self._media_card = self._build_media_widget_card()
        self._media_card.set_visible(bool(self.cfg.get('show_media_widget')))
        widgets_row.append(self._media_card)

        content.append(self._spacer(28))

        pass_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pass_col.set_halign(Gtk.Align.CENTER)
        pass_col.set_hexpand(True)
        content.append(pass_col)

        self._pass_entry = Gtk.Entry()
        self._pass_entry.set_visibility(False)
        self._pass_entry.set_placeholder_text(_t(self.cfg, 'pass_placeholder'))
        self._pass_entry.set_size_request(300, -1)
        self._pass_entry.add_css_class('pass-entry')
        self._pass_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, 'view-conceal-symbolic')
        self._pass_entry.connect('icon-press',
            lambda e, _: e.set_visibility(not e.get_visibility()))
        self._pass_entry.connect('activate', self._try_unlock)
        pass_col.append(self._pass_entry)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect('key-pressed', self._on_key)
        self.add_controller(key_ctrl)

        self._hint = Gtk.Label(label=_t(self.cfg, 'hint_unlock'))
        self._hint.add_css_class('hint-label')
        pass_col.append(self._hint)

        bot_spring = Gtk.Box()
        bot_spring.set_vexpand(True)
        content.append(bot_spring)


    def _setup_live_wallpaper(self, overlay, path):
        """
        Live wallpaper via GStreamer playbin.
        • Надёжный loop через about-to-finish + EOS bus watch (работает с MP4/WebM/GIF)
        • Громкость из конфига (0.0–1.0), по умолчанию 0 = без звука
        При ошибке — статичная Gtk.Picture как fallback.
        """
        self._live_pipeline = None
        try:
            gi.require_version('Gst', '1.0')
            gi.require_version('GstVideo', '1.0')
            from gi.repository import Gst, GstVideo
            Gst.init(None)

            pipeline = Gst.ElementFactory.make('playbin', 'live-wallpaper')
            if not pipeline:
                raise RuntimeError('GStreamer playbin not available')

            sink = (Gst.ElementFactory.make('gtk4paintablesink', 'vsink') or
                    Gst.ElementFactory.make('gtksink', 'vsink'))
            if not sink:
                raise RuntimeError('No GTK GStreamer video sink found. '
                                   'Install gstreamer1.0-gtk3 or gstreamer1.0-plugins-good')

            pipeline.set_property('video-sink', sink)
            pipeline.set_property('volume',
                max(0.0, min(1.0, float(self.cfg.get('live_wallpaper_volume', 0.0)))))

            uri = Gio.File.new_for_path(path).get_uri()
            pipeline.set_property('uri', uri)

            def _on_about_to_finish(pl):
                pl.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    0)

            pipeline.connect('about-to-finish', _on_about_to_finish)

            bus = pipeline.get_bus()
            bus.add_signal_watch()

            def _on_bus_msg(bus, msg, pl):
                t = msg.type
                if t == Gst.MessageType.EOS:
                    pl.seek_simple(
                        Gst.Format.TIME,
                        Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                        0)
                    pl.set_state(Gst.State.PLAYING)
                elif t == Gst.MessageType.ERROR:
                    err, dbg = msg.parse_error()
                    print(f'[live-wallpaper] GStreamer error: {err} / {dbg}',
                          file=sys.stderr)

            bus.connect('message', _on_bus_msg, pipeline)

            try:
                paintable = sink.get_property('paintable')
                widget = Gtk.Picture()
                widget.set_paintable(paintable)
                widget.set_content_fit(Gtk.ContentFit.COVER)
            except Exception:
                widget = sink.get_property('widget')

            widget.set_hexpand(True)
            widget.set_vexpand(True)
            overlay.set_child(widget)
            self._bg = widget

            pipeline.set_state(Gst.State.PLAYING)
            self._live_pipeline = pipeline
            self._live_gst_sink = sink   # prevent GC

        except Exception as exc:
            print(f'[live-wallpaper] Fallback to static bg: {exc}', file=sys.stderr)
            self._bg = Gtk.Picture()
            self._bg.set_content_fit(Gtk.ContentFit.COVER)
            self._bg.set_hexpand(True)
            self._bg.set_vexpand(True)
            overlay.set_child(self._bg)


    def _build_weather_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class('weather-card')
        card.set_size_request(180, -1)

        hdr = Gtk.Label(label=_t(self.cfg, 'weather_hdr'))
        hdr.add_css_class('notif-header')
        hdr.set_halign(Gtk.Align.START)
        card.append(hdr)

        main_row = Gtk.Box(spacing=10)
        main_row.set_valign(Gtk.Align.CENTER)

        self._weather_icon_lbl = Gtk.Label(label='…')
        self._weather_icon_lbl.add_css_class('weather-icon')
        main_row.append(self._weather_icon_lbl)

        temp_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._weather_temp_lbl = Gtk.Label(label='--°')
        self._weather_temp_lbl.add_css_class('weather-temp')
        self._weather_temp_lbl.set_halign(Gtk.Align.START)
        temp_col.append(self._weather_temp_lbl)
        self._weather_city_lbl = Gtk.Label(label='…')
        self._weather_city_lbl.add_css_class('weather-city')
        self._weather_city_lbl.set_halign(Gtk.Align.START)
        temp_col.append(self._weather_city_lbl)
        main_row.append(temp_col)
        card.append(main_row)

        self._weather_desc_lbl = Gtk.Label(label='')
        self._weather_desc_lbl.add_css_class('weather-desc')
        self._weather_desc_lbl.set_halign(Gtk.Align.START)
        card.append(self._weather_desc_lbl)

        self._weather_detail_lbl = Gtk.Label(label='')
        self._weather_detail_lbl.add_css_class('weather-detail')
        self._weather_detail_lbl.set_halign(Gtk.Align.START)
        card.append(self._weather_detail_lbl)

        sep = Gtk.Box()
        sep.add_css_class('weather-tomorrow-sep')
        sep.set_hexpand(True)
        card.append(sep)

        tmr_title = Gtk.Label(label=_t(self.cfg, 'weather_tomorrow'))
        tmr_title.add_css_class('weather-tomorrow-title')
        tmr_title.set_halign(Gtk.Align.START)
        card.append(tmr_title)

        tmr_row = Gtk.Box(spacing=8)
        tmr_row.set_valign(Gtk.Align.CENTER)
        self._weather_tmr_icon = Gtk.Label(label='…')
        self._weather_tmr_icon.add_css_class('weather-tomorrow-icon')
        tmr_row.append(self._weather_tmr_icon)

        tmr_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._weather_tmr_temp = Gtk.Label(label='--°')
        self._weather_tmr_temp.add_css_class('weather-tomorrow-temp')
        self._weather_tmr_temp.set_halign(Gtk.Align.START)
        tmr_info.append(self._weather_tmr_temp)
        self._weather_tmr_range = Gtk.Label(label='')
        self._weather_tmr_range.add_css_class('weather-tomorrow-range')
        self._weather_tmr_range.set_halign(Gtk.Align.START)
        tmr_info.append(self._weather_tmr_range)
        self._weather_tmr_desc = Gtk.Label(label='')
        self._weather_tmr_desc.add_css_class('weather-desc')
        self._weather_tmr_desc.set_halign(Gtk.Align.START)
        tmr_info.append(self._weather_tmr_desc)
        tmr_row.append(tmr_info)
        card.append(tmr_row)

        return card


    def _build_media_widget_card(self):
        """Widget for GIF/WebM/MP4 media that auto-sizes to the media content."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class('media-card')
        card.set_size_request(220, -1)

        hdr = Gtk.Label(label=_t(self.cfg, 'media_hdr'))
        hdr.add_css_class('media-header')
        hdr.set_halign(Gtk.Align.START)
        card.append(hdr)

        self._media_stack = Gtk.Stack()
        self._media_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._media_stack.set_transition_duration(300)

        empty_lbl = Gtk.Label(label=_t(self.cfg, 'media_empty'))
        empty_lbl.add_css_class('media-empty')
        empty_lbl.set_halign(Gtk.Align.CENTER)
        empty_lbl.set_valign(Gtk.Align.CENTER)
        empty_lbl.set_justify(Gtk.Justification.CENTER)
        self._media_stack.add_named(empty_lbl, 'empty')

        self._media_video_box = Gtk.Box()
        self._media_video_box.set_hexpand(True)
        self._media_stack.add_named(self._media_video_box, 'video')

        self._media_gif_box = Gtk.Box()
        self._media_gif_box.set_halign(Gtk.Align.CENTER)
        self._media_gif_box.set_valign(Gtk.Align.CENTER)
        self._media_stack.add_named(self._media_gif_box, 'gif')

        self._media_stack.set_visible_child_name('empty')
        card.append(self._media_stack)

        self._load_media_file(self.cfg.get('media_widget_file', ''))
        return card

    def _load_media_file(self, path):
        """Load and display media file in the widget."""
        if not path or not os.path.exists(path):
            self._media_stack.set_visible_child_name('empty')
            return

        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''

        if ext == 'gif':
            self._load_gif(path)
        else:
            self._load_video(path)

    def _load_gif(self, path):
        """Load animated GIF using GdkPixbufAnimation."""
        try:
            child = self._media_gif_box.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self._media_gif_box.remove(child)
                child = next_child

            from gi.repository import GdkPixbuf, GLib as GL
            anim = GdkPixbuf.PixbufAnimation.new_from_file(path)

            if anim.is_static_image():
                pixbuf = anim.get_static_image()
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                picture = Gtk.Picture()
                picture.set_paintable(texture)
                picture.set_content_fit(Gtk.ContentFit.CONTAIN)
                max_w = 400
                w = min(pixbuf.get_width(), max_w)
                h = int(pixbuf.get_height() * (w / pixbuf.get_width()))
                picture.set_size_request(w, h)
                self._media_gif_box.append(picture)
            else:
                self._gif_anim = anim
                self._gif_iter = anim.get_iter(None)
                picture = Gtk.Picture()
                picture.set_content_fit(Gtk.ContentFit.CONTAIN)
                first_pb = self._gif_iter.get_pixbuf()
                max_w = 400
                w = min(first_pb.get_width(), max_w)
                h = int(first_pb.get_height() * (w / first_pb.get_width()))
                picture.set_size_request(w, h)
                self._media_picture_gif = picture
                self._gif_picture_pixbuf_w = first_pb.get_width()
                texture = Gdk.Texture.new_for_pixbuf(
                    first_pb.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR))
                picture.set_paintable(texture)
                self._media_gif_box.append(picture)
                self._tick_gif()

            self._media_stack.set_visible_child_name('gif')
        except Exception as e:
            print(f"GIF load error: {e}")
            self._media_stack.set_visible_child_name('empty')

    def _tick_gif(self):
        """Advance GIF frame."""
        try:
            from gi.repository import GdkPixbuf
            self._gif_iter.advance(None)
            delay = self._gif_iter.get_delay_time()
            if delay < 10:
                delay = 100
            pb = self._gif_iter.get_pixbuf()
            max_w = 400
            orig_w = self._gif_picture_pixbuf_w
            w = min(orig_w, max_w)
            h = int(pb.get_height() * (w / orig_w))
            scaled = pb.scale_simple(w, h, GdkPixbuf.InterpType.NEAREST)
            texture = Gdk.Texture.new_for_pixbuf(scaled)
            self._media_picture_gif.set_paintable(texture)
            GLib.timeout_add(delay, self._tick_gif)
        except Exception:
            pass

    def _load_video(self, path):
        """Load video via GStreamer playbin with reliable loop (works for MP4/WebM/MKV)."""
        try:
            child = self._media_video_box.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self._media_video_box.remove(child)
                child = next_child

            if hasattr(self, '_media_pipeline') and self._media_pipeline:
                self._media_pipeline.set_state(
                    __import__('gi').repository.Gst.State.NULL)
                self._media_pipeline = None

            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            Gst.init(None)

            pipeline = Gst.ElementFactory.make('playbin', 'media-widget')
            if not pipeline:
                raise RuntimeError('GStreamer playbin not available')

            sink = (Gst.ElementFactory.make('gtk4paintablesink', 'msink') or
                    Gst.ElementFactory.make('gtksink', 'msink'))
            if not sink:
                raise RuntimeError('No GTK GStreamer video sink available')

            pipeline.set_property('video-sink', sink)
            pipeline.set_property('volume', 0.0)   # media widget is always muted
            pipeline.set_property('uri', Gio.File.new_for_path(path).get_uri())

            def _atf(pl):
                pl.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    0)
            pipeline.connect('about-to-finish', _atf)

            bus = pipeline.get_bus()
            bus.add_signal_watch()
            def _bus_msg(bus, msg, pl):
                if msg.type == Gst.MessageType.EOS:
                    pl.seek_simple(Gst.Format.TIME,
                                   Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
                    pl.set_state(Gst.State.PLAYING)
            bus.connect('message', _bus_msg, pipeline)

            try:
                paintable = sink.get_property('paintable')
                widget = Gtk.Picture()
                widget.set_paintable(paintable)
                widget.set_content_fit(Gtk.ContentFit.CONTAIN)
            except Exception:
                widget = sink.get_property('widget')

            widget.set_hexpand(True)
            widget.set_size_request(220, 165)
            self._media_video_box.append(widget)

            pipeline.set_state(Gst.State.PLAYING)
            self._media_pipeline = pipeline
            self._media_gst_sink = sink
            self._media_player = widget
            self._media_stack.set_visible_child_name('video')

        except Exception as e:
            print(f"Video load error: {e}", file=sys.stderr)
            self._media_stack.set_visible_child_name('empty')


    def _build_sysmon_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class('sysmon-card')
        card.set_size_request(220, -1)

        hdr = Gtk.Label(label=_t(self.cfg, 'sysmon_hdr'))
        hdr.add_css_class('notif-header')
        hdr.set_halign(Gtk.Align.START)
        card.append(hdr)

        for label_text, val_attr, bar_attr, bar_bg_attr in [
            ('CPU',  '_cpu_val', '_cpu_bar', '_cpu_bar_bg'),
            ('MEM',  '_mem_val', '_mem_bar', '_mem_bar_bg'),
            ('DISK', '_disk_val','_disk_bar','_disk_bar_bg'),
        ]:
            row = Gtk.Box(spacing=6)
            lbl = Gtk.Label(label=label_text)
            lbl.add_css_class('sysmon-label')
            row.append(lbl)
            val = Gtk.Label(label='--')
            val.add_css_class('sysmon-value')
            val.set_hexpand(True)
            val.set_halign(Gtk.Align.END)
            row.append(val)
            card.append(row)
            setattr(self, val_attr, val)

            bg = Gtk.Box()
            bg.add_css_class('sysmon-bar-bg')
            bg.set_hexpand(True)
            fill = Gtk.Box()
            fill.add_css_class('sysmon-bar-fill')
            fill.set_size_request(0, 4)
            bg.append(fill)
            card.append(bg)
            setattr(self, bar_attr, fill)
            setattr(self, bar_bg_attr, bg)

        sep1 = Gtk.Box()
        sep1.add_css_class('sysmon-sep')
        sep1.set_hexpand(True)
        card.append(sep1)

        net_row = Gtk.Box(spacing=8)
        rx_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        rx_lbl = Gtk.Label(label='RX')
        rx_lbl.add_css_class('sysmon-label')
        rx_lbl.set_halign(Gtk.Align.START)
        rx_col.append(rx_lbl)
        self._net_rx_val = Gtk.Label(label='--')
        self._net_rx_val.add_css_class('sysmon-detail')
        self._net_rx_val.set_halign(Gtk.Align.START)
        rx_col.append(self._net_rx_val)
        net_row.append(rx_col)

        tx_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        tx_lbl = Gtk.Label(label='TX')
        tx_lbl.add_css_class('sysmon-label')
        tx_lbl.set_halign(Gtk.Align.START)
        tx_col.append(tx_lbl)
        self._net_tx_val = Gtk.Label(label='--')
        self._net_tx_val.add_css_class('sysmon-detail')
        self._net_tx_val.set_halign(Gtk.Align.START)
        tx_col.append(self._net_tx_val)
        net_row.append(tx_col)
        card.append(net_row)

        sep2 = Gtk.Box()
        sep2.add_css_class('sysmon-sep')
        sep2.set_hexpand(True)
        card.append(sep2)

        procs_lbl = Gtk.Label(label=_t(self.cfg, 'top_procs'))
        procs_lbl.add_css_class('notif-header')
        procs_lbl.set_halign(Gtk.Align.START)
        card.append(procs_lbl)

        self._proc_rows = []
        for _ in range(3):
            prow = Gtk.Box(spacing=4)
            pname = Gtk.Label(label='')
            pname.add_css_class('sysmon-proc-name')
            pname.set_hexpand(True)
            pname.set_halign(Gtk.Align.START)
            pname.set_ellipsize(Pango.EllipsizeMode.END)
            pname.set_max_width_chars(14)
            prow.append(pname)
            pcpu = Gtk.Label(label='')
            pcpu.add_css_class('sysmon-proc-val')
            pcpu.set_halign(Gtk.Align.END)
            prow.append(pcpu)
            pmem = Gtk.Label(label='')
            pmem.add_css_class('sysmon-proc-val')
            pmem.set_halign(Gtk.Align.END)
            prow.append(pmem)
            card.append(prow)
            self._proc_rows.append((pname, pcpu, pmem))

        return card


    def _build_notif_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class('notif-card')
        card.set_size_request(230, -1)

        hdr = Gtk.Label(label=_t(self.cfg, 'notif_hdr'))
        hdr.add_css_class('notif-header')
        hdr.set_halign(Gtk.Align.START)
        hdr.set_margin_bottom(6)
        card.append(hdr)

        self._notif_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.append(self._notif_list)

        self._notif_empty = Gtk.Label(label=_t(self.cfg, 'notif_empty'))
        self._notif_empty.add_css_class('notif-empty')
        self._notif_empty.set_halign(Gtk.Align.CENTER)
        self._notif_empty.set_margin_top(6)
        self._notif_empty.set_margin_bottom(6)
        card.append(self._notif_empty)

        return card


    def _build_spotify_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class('sp-card')
        card.set_size_request(300, -1)

        sp_top = Gtk.Box(spacing=12)
        sp_top.set_valign(Gtk.Align.CENTER)

        self._sp_art_picture = Gtk.Picture()
        self._sp_art_picture.set_content_fit(Gtk.ContentFit.COVER)
        self._sp_art_picture.set_size_request(56, 56)
        self._sp_art_placeholder = Gtk.Label(label='♫')
        self._sp_art_placeholder.add_css_class('spotify-icon')
        self._sp_art_placeholder.set_size_request(56, 56)
        self._sp_art_placeholder.set_halign(Gtk.Align.CENTER)
        self._sp_art_placeholder.set_valign(Gtk.Align.CENTER)
        self._sp_art_stack = Gtk.Stack()
        self._sp_art_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._sp_art_stack.set_transition_duration(400)
        self._sp_art_stack.add_named(self._sp_art_placeholder, 'placeholder')
        self._sp_art_stack.add_named(self._sp_art_picture, 'art')
        self._sp_art_stack.set_visible_child_name('placeholder')
        sp_top.append(self._sp_art_stack)

        sp_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        sp_info.set_valign(Gtk.Align.CENTER)
        sp_info.set_hexpand(True)

        sp_badge_row = Gtk.Box(spacing=5)
        self._sp_dot = Gtk.Label(label='●')
        self._sp_dot.add_css_class('sp-playing-dot')
        sp_badge_row.append(self._sp_dot)
        self._sp_badge = Gtk.Label(label='PLAYING')
        self._sp_badge.add_css_class('sp-badge')
        sp_badge_row.append(self._sp_badge)
        sp_info.append(sp_badge_row)

        for attr, css_cls, default in [
            ('_sp_title',  'sp-track',  _t(self.cfg, 'sp_not_running')),
            ('_sp_artist', 'sp-artist', ''),
            ('_sp_album',  'sp-album',  ''),
        ]:
            clip = Gtk.Box()
            clip.add_css_class('sp-marquee-clip')
            clip.set_hexpand(True)
            clip.set_overflow(Gtk.Overflow.HIDDEN)
            lbl = Gtk.Label(label=default)
            lbl.add_css_class(css_cls)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_hexpand(False)
            lbl.set_xalign(0)
            lbl.set_wrap(False)
            lbl.set_single_line_mode(True)
            clip.append(lbl)
            sp_info.append(clip)
            setattr(self, attr, lbl)

        sp_top.append(sp_info)
        card.append(sp_top)

        prog_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        time_row = Gtk.Box()
        self._sp_pos_lbl = Gtk.Label(label='0:00')
        self._sp_pos_lbl.add_css_class('sp-time')
        self._sp_pos_lbl.set_halign(Gtk.Align.START)
        self._sp_pos_lbl.set_hexpand(True)
        time_row.append(self._sp_pos_lbl)
        self._sp_len_lbl = Gtk.Label(label='0:00')
        self._sp_len_lbl.add_css_class('sp-time')
        self._sp_len_lbl.set_halign(Gtk.Align.END)
        time_row.append(self._sp_len_lbl)
        prog_col.append(time_row)

        track_box = Gtk.Box()
        track_box.add_css_class('sp-progress-bg')
        track_box.set_hexpand(True)
        self._sp_progress_fill = Gtk.Box()
        self._sp_progress_fill.add_css_class('sp-progress-fill')
        self._sp_progress_fill.set_size_request(0, 3)
        track_box.append(self._sp_progress_fill)
        prog_col.append(track_box)
        self._sp_track_container = track_box

        eq_row = Gtk.Box(spacing=0)
        eq_row.add_css_class('eq-container')
        eq_row.set_valign(Gtk.Align.END)
        eq_row.set_halign(Gtk.Align.FILL)
        eq_row.set_hexpand(True)
        eq_row.set_size_request(-1, 28)
        self._eq_bars = []
        for i in range(1, 25):
            bar = Gtk.Box()
            bar.add_css_class('eq-bar')
            bar.add_css_class(f'eq-bar-{((i-1) % 12) + 1}')
            bar.set_valign(Gtk.Align.END)
            bar.set_hexpand(True)
            eq_row.append(bar)
            self._eq_bars.append(bar)
        prog_col.append(eq_row)
        card.append(prog_col)

        return card


    def _build_vscodium_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class('card')
        card.set_size_request(300, -1)

        vs_row = Gtk.Box(spacing=8)
        vs_icon = Gtk.Label(label='{ }')
        vs_icon.add_css_class('vs-icon')
        vs_row.append(vs_icon)
        self._vs_fname = Gtk.Label(label=_t(self.cfg, 'vs_not_running'))
        self._vs_fname.add_css_class('card-title')
        self._vs_fname.set_ellipsize(Pango.EllipsizeMode.END)
        self._vs_fname.set_max_width_chars(24)
        vs_row.append(self._vs_fname)
        card.append(vs_row)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 130)
        self._vs_buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self._vs_buf)
        tv.add_css_class('code-text')
        tv.set_editable(False)
        tv.set_cursor_visible(False)
        tv.set_wrap_mode(Gtk.WrapMode.NONE)
        scroll.set_child(tv)
        card.append(scroll)

        return card


    def _spacer(self, h):
        b = Gtk.Box()
        b.set_size_request(-1, h)
        return b

    def _update_dim(self, val):
        prov = Gtk.CssProvider()
        prov.load_from_data(
            f'* {{ background-color: rgba(0,0,0,{val}); }}'.encode())
        ctx = self._dim_box.get_style_context()
        ctx.add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

    def _apply_accent_color(self, r, g, b):
        if (r, g, b) == self._accent_color:
            return
        self._accent_color = (r, g, b)
        css = f"""
        .sp-card {{
            background: linear-gradient(135deg,
                rgba(18,18,18,0.92) 0%,
                rgba({r//5},{g//5},{b//5},0.92) 100%);
            border: 1px solid rgba({r},{g},{b},0.40);
            border-radius: 20px; padding: 14px 16px;
        }}
        .sp-progress-fill {{ background-color: rgb({r},{g},{b}); }}
        .eq-bar            {{ background-color: rgb({r},{g},{b}); }}
        .sp-badge          {{ color: rgb({r},{g},{b}); }}
        .sp-playing-dot    {{ color: rgb({r},{g},{b}); }}
        """
        if self._accent_prov:
            Gtk.StyleContext.remove_provider_for_display(
                Gdk.Display.get_default(), self._accent_prov)
        prov = Gtk.CssProvider()
        prov.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
        self._accent_prov = prov


    def _start_clock(self):
        self._tick()
        self._timers.append(GLib.timeout_add(1000, self._tick))

    def _tick(self):
        now = datetime.datetime.now()
        self._clock_lbl.set_label(now.strftime('%H:%M:%S'))
        days   = _t(self.cfg, 'days')
        months = _t(self.cfg, 'months')
        self._date_lbl.set_label(
            f"{days[now.weekday()]}, {now.day} {months[now.month-1]}")
        return GLib.SOURCE_CONTINUE


    def _start_widgets(self):
        self._refresh()
        self._timers.append(GLib.timeout_add_seconds(5, self._refresh))
        self._timers.append(GLib.timeout_add(1000, self._tick_progress))
        if self.cfg.get('show_sysmon'):
            self._refresh_sysmon()
            self._timers.append(GLib.timeout_add_seconds(3, self._refresh_sysmon))

    def _refresh(self):
        threading.Thread(target=self._fetch, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _refresh_sysmon(self):
        threading.Thread(target=self._fetch_sysmon, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _fetch(self):
        sp = get_spotify_info() if self.cfg.get('show_spotify') else None
        sp_art = None
        if sp and sp.get('art_url'):
            sp_art = fetch_album_art(sp['art_url'])
        vs = self._fetch_vs() if self.cfg.get('show_vscodium') else None
        weather = None
        weather_tmr = None
        if self.cfg.get('show_weather') and self.cfg.get('weather_api_key'):
            lang = self.cfg.get('language', 'ru')
            weather = get_weather(
                self.cfg['weather_api_key'],
                self.cfg.get('weather_city', 'Moscow'),
                lang=lang)
            weather_tmr = get_weather_tomorrow(
                self.cfg['weather_api_key'],
                self.cfg.get('weather_city', 'Moscow'),
                lang=lang)
        GLib.idle_add(self._apply, sp, sp_art, vs, weather, weather_tmr)

    def _fetch_sysmon(self):
        data = get_sysmon()
        GLib.idle_add(self._apply_sysmon, data)

    def _fetch_vs(self):
        if not is_vscodium_running():
            return None
        path = (self.cfg.get('vscodium_project_path') or
                get_vscodium_recent_project())
        if not path:
            return {'name': _t(self.cfg, 'vs_no_project'), 'code': ''}
        fp = get_last_modified_file(path)
        if not fp:
            return {'name': _t(self.cfg, 'vs_no_files'), 'code': ''}
        return {'name': os.path.basename(fp), 'code': read_file_snippet(fp)}

    def _fmt_time(self, us):
        s = int(us / 1_000_000)
        return f'{s // 60}:{s % 60:02d}'

    def _tick_progress(self):
        if self._sp_length > 0 and self._sp_playing:
            elapsed = int((time.monotonic() - self._sp_last_fetch_time) * 1_000_000)
            pos = min(self._sp_last_position + elapsed, self._sp_length)
            self._update_progress_ui(pos, self._sp_length)
        return GLib.SOURCE_CONTINUE

    def _update_progress_ui(self, position, length):
        if length > 0:
            frac = min(position / length, 1.0)
            cw = self._sp_card.get_allocated_width()
            fw = max(4, int((cw - 32) * frac))
            self._sp_progress_fill.set_size_request(fw, 3)
            self._sp_pos_lbl.set_label(self._fmt_time(position))
        else:
            self._sp_progress_fill.set_size_request(0, 3)
            self._sp_pos_lbl.set_label('')

    def _set_eq_playing(self, playing):
        for bar in self._eq_bars:
            if playing: bar.remove_css_class('paused')
            else:        bar.add_css_class('paused')


    def _apply(self, sp, sp_art, vs, weather, weather_tmr=None):
        if sp:
            playing = sp['status'] == 'Playing'
            self._sp_playing = playing
            self._sp_last_position = sp.get('position', 0)
            self._sp_last_fetch_time = time.monotonic()
            self._sp_length = sp.get('length', 0)

            self._sp_dot.set_label('●' if playing else '⏸')
            self._sp_badge.set_label('PLAYING' if playing else 'PAUSED')
            self._sp_title.set_label(sp['title'])
            self._sp_artist.set_label(sp['artist'])
            self._sp_album.set_label(sp.get('album', ''))

            def _marquee(lbl, text, thr):
                if len(text) > thr: lbl.add_css_class('marquee')
                else: lbl.remove_css_class('marquee')
            _marquee(self._sp_title,  sp['title'],         20)
            _marquee(self._sp_artist, sp['artist'],        24)
            _marquee(self._sp_album,  sp.get('album',''),  26)

            self._sp_len_lbl.set_label(
                self._fmt_time(self._sp_length) if self._sp_length > 0 else '')
            self._update_progress_ui(self._sp_last_position, self._sp_length)
            self._set_eq_playing(playing)

            if sp_art:
                texture = Gdk.Texture.new_for_pixbuf(sp_art)
                self._sp_art_picture.set_paintable(texture)
                self._sp_art_stack.set_visible_child_name('art')
                r, g, b = get_dominant_color(sp_art)
                self._apply_accent_color(r, g, b)
            else:
                self._sp_art_stack.set_visible_child_name('placeholder')
                self._apply_accent_color(29, 185, 84)
        else:
            self._sp_playing = False
            self._sp_length = 0
            self._sp_title.set_label(_t(self.cfg, 'sp_not_running'))
            self._sp_artist.set_label('')
            self._sp_album.set_label('')
            self._sp_badge.set_label('OFFLINE')
            self._sp_dot.set_label('○')
            self._sp_progress_fill.set_size_request(0, 3)
            self._sp_pos_lbl.set_label('')
            self._sp_len_lbl.set_label('')
            self._sp_art_stack.set_visible_child_name('placeholder')
            self._set_eq_playing(False)
            self._apply_accent_color(29, 185, 84)
        self._sp_card.set_visible(bool(self.cfg.get('show_spotify')))

        if vs:
            self._vs_fname.set_label(vs['name'])
            self._vs_buf.set_text(vs['code'])
        else:
            self._vs_fname.set_label(_t(self.cfg, 'vs_not_running'))
            self._vs_buf.set_text('')
        self._vs_card.set_visible(bool(self.cfg.get('show_vscodium')))

        if weather:
            self._weather_icon_lbl.set_label(weather['icon'])
            self._weather_temp_lbl.set_label(f"{weather['temp']}°C")
            self._weather_city_lbl.set_label(weather['city'].upper())
            self._weather_desc_lbl.set_label(weather['desc'])
            self._weather_detail_lbl.set_label(
                f"{_t(self.cfg,'feels')} {weather['feels']}°  "
                f"{_t(self.cfg,'humidity')} {weather['humidity']}%")
        else:
            self._weather_icon_lbl.set_label('—')
            self._weather_temp_lbl.set_label('--°')
            no_key = not self.cfg.get('weather_api_key')
            self._weather_city_lbl.set_label(
                _t(self.cfg, 'no_api_key') if no_key
                else self.cfg.get('weather_city', '').upper())
            self._weather_desc_lbl.set_label('')
            self._weather_detail_lbl.set_label('')

        if weather_tmr:
            self._weather_tmr_icon.set_label(weather_tmr['icon'])
            self._weather_tmr_temp.set_label(f"{weather_tmr['temp']}°C")
            self._weather_tmr_range.set_label(
                f"↓{weather_tmr['temp_min']}° ↑{weather_tmr['temp_max']}°")
            self._weather_tmr_desc.set_label(weather_tmr['desc'])
        else:
            self._weather_tmr_icon.set_label('…')
            self._weather_tmr_temp.set_label('--°')
            self._weather_tmr_range.set_label('')
            self._weather_tmr_desc.set_label('')

        self._weather_card.set_visible(bool(self.cfg.get('show_weather')))
        self._media_card.set_visible(bool(self.cfg.get('show_media_widget')))

    def _apply_sysmon(self, data):
        if not data:
            return

        def _set_bar(fill, bar_bg, pct):
            bw = bar_bg.get_allocated_width() - 4
            fw = max(2, int(bw * pct / 100))
            fill.set_size_request(fw, 4)
            for c in ('warn', 'crit'):
                fill.remove_css_class(c)
            if pct > 90:   fill.add_css_class('crit')
            elif pct > 70: fill.add_css_class('warn')

        cpu = data.get('cpu')
        if cpu is not None:
            self._cpu_val.set_label(f'{cpu:.0f}%')
            _set_bar(self._cpu_bar, self._cpu_bar_bg, cpu)

        mu = data.get('mem_used')
        mp = data.get('mem_pct', 0)
        if mu is not None:
            self._mem_val.set_label(f'{mu:.1f}G')
            _set_bar(self._mem_bar, self._mem_bar_bg, mp)

        du = data.get('disk_used')
        dp = data.get('disk_pct')
        if du is not None:
            self._disk_val.set_label(f'{du:.0f}G')
            _set_bar(self._disk_bar, self._disk_bar_bg, dp or 0)
        else:
            self._disk_val.set_label('--')

        self._net_rx_val.set_label(_fmt_bytes(data.get('net_rx')))
        self._net_tx_val.set_label(_fmt_bytes(data.get('net_tx')))

        procs = data.get('top_procs', [])
        for i, (pname_lbl, pcpu_lbl, pmem_lbl) in enumerate(self._proc_rows):
            if i < len(procs):
                p = procs[i]
                pname_lbl.set_label(p.get('name', '?'))
                pcpu_lbl.set_label(f"{p.get('cpu_percent', 0):.0f}%")
                pmem_lbl.set_label(f"{p.get('memory_percent', 0):.1f}%")
            else:
                pname_lbl.set_label('')
                pcpu_lbl.set_label('')
                pmem_lbl.set_label('')

    def _update_notifications(self):
        while True:
            child = self._notif_list.get_first_child()
            if not child: break
            self._notif_list.remove(child)

        notifs = list(reversed(_notifications[-3:]))
        if notifs:
            self._notif_empty.set_visible(False)
            for i, n in enumerate(notifs):
                row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                top_row = Gtk.Box(spacing=6)
                app_lbl = Gtk.Label(label=n['app'])
                app_lbl.add_css_class('notif-app')
                app_lbl.set_halign(Gtk.Align.START)
                app_lbl.set_hexpand(True)
                top_row.append(app_lbl)
                t_lbl = Gtk.Label(label=n['time'])
                t_lbl.add_css_class('notif-time')
                top_row.append(t_lbl)
                row.append(top_row)
                smry = Gtk.Label(label=n['summary'])
                smry.add_css_class('notif-summary')
                smry.set_halign(Gtk.Align.START)
                smry.set_ellipsize(Pango.EllipsizeMode.END)
                smry.set_max_width_chars(28)
                row.append(smry)
                if n.get('body'):
                    body = Gtk.Label(label=n['body'])
                    body.add_css_class('notif-body')
                    body.set_halign(Gtk.Align.START)
                    body.set_ellipsize(Pango.EllipsizeMode.END)
                    body.set_max_width_chars(30)
                    row.append(body)
                self._notif_list.append(row)
                if i < len(notifs) - 1:
                    sep = Gtk.Box()
                    sep.add_css_class('notif-sep')
                    sep.set_hexpand(True)
                    self._notif_list.append(sep)
        else:
            self._notif_empty.set_visible(True)


    def _try_unlock(self, entry):
        pwd = entry.get_text()
        entry.set_text('')
        entry.remove_css_class('error')
        self._hint.set_label(_t(self.cfg, 'hint_checking'))
        threading.Thread(target=self._check, args=(pwd,), daemon=True).start()

    def _check(self, pwd):
        ok = unlock_session(pwd)
        GLib.idle_add(self._result, ok)

    def _result(self, ok):
        if ok:
            self._hint.set_label(_t(self.cfg, 'hint_welcome'))
            for t in self._timers:
                GLib.source_remove(t)
            GLib.timeout_add(400, self.get_application().quit)
        else:
            self._attempts += 1
            self._pass_entry.add_css_class('error')
            self._hint.set_label(_t(self.cfg, 'hint_wrong').format(self._attempts))
            GLib.timeout_add(900, self._reset_error)

    def _reset_error(self):
        self._pass_entry.remove_css_class('error')
        self._hint.set_label(_t(self.cfg, 'hint_unlock'))
        self._pass_entry.grab_focus()
        return False

    def _inhibit_shortcuts(self):
        surface = self.get_surface()
        if surface and hasattr(surface, 'inhibit_system_shortcuts'):
            try: surface.inhibit_system_shortcuts(None)
            except Exception: pass

    def _on_active_change(self, *_):
        if self.is_active():
            self._inhibit_shortcuts()
            self._pass_entry.grab_focus()

    def _initial_focus(self):
        self._pass_entry.grab_focus()
        self._pass_entry.set_position(-1)
        self._inhibit_shortcuts()
        return False

    def _on_key(self, ctrl, keyval, keycode, state):
        blocked_keys = {
            Gdk.KEY_Super_L, Gdk.KEY_Super_R,
            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
            Gdk.KEY_Escape, Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab,
        }
        blocked_mods = Gdk.ModifierType.ALT_MASK | Gdk.ModifierType.SUPER_MASK
        if (state & blocked_mods) or keyval in blocked_keys:
            return True
        return False


class App(Gtk.Application):
    def __init__(self, cfg):
        super().__init__(application_id='io.fancy.lockscreen',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.cfg = cfg

    def do_activate(self):
        LockScreen(self, self.cfg).present()


if __name__ == '__main__':
    sys.exit(App(load_config()).run(sys.argv))
