#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KICK.COM GELİŞMİŞ İZLEYİCİ BOTU
Version: 3.0.0
Author: WITCH Development Team
Description: Enterprise grade viewer bot with advanced features
"""

import argparse
import asyncio
import contextlib
import json
import logging
import os
import random
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from collections import defaultdict
import platform

try:
    import tls_client
except ImportError as exc:
    raise SystemExit(
        "❌ tls_client modülü gerekli: pip install tls-client"
    ) from exc

try:
    from websockets.asyncio.client import connect
    from websockets.exceptions import (
        ConnectionClosed,
        WebSocketException,
    )
except ImportError:
    try:
        from websockets import connect
        from websockets.exceptions import (
            ConnectionClosed,
            WebSocketException,
        )
    except ImportError as exc:
        raise SystemExit(
            "❌ websockets modülü gerekli: pip install websockets"
        ) from exc

try:
    from websockets.proxy import Proxy
except ImportError:
    Proxy = None

# ==================== SABİTLER ====================

DEFAULT_CLIENT_TOKEN = "e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823"
MAX_VIEWERS_LIMIT = 10000
VERSION = "3.0.0"

# ==================== RENKLİ ANSI KODLARI ====================

class Colors:
    """Renkli terminal çıktıları için ANSI renk kodları"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[35m'
    WHITE = '\033[37m'
    BLACK = '\033[30m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Arka plan renkleri
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """RGB renk kodu oluştur (256 renk desteği olan terminaller için)"""
        return f'\033[38;2;{r};{g};{b}m'


# ==================== ASCII ART LOGOSU ====================

ASCII_LOGO = f"""
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ██ ▄█▀ ██▓ ▄████▄   ██ ▄█▀    █     █░ ██▓▓█████  █     █░ │
│  ██▄█▒ ▓██▒▒██▀ ▀█   ██▄█▒    ▓█░ █ ░█░▓██▒▓█   ▀ ▓█░ █ ░█░ │
│ ▓███▄░ ▒██▒▒▓█    ▄ ▓███▄░    ▒█░ █ ░█ ▒██▒▒███   ▒█░ █ ░█  │
│ ▓██ █▄ ░██░▒▓▓▄ ▄██▒▓██ █▄    ░█░ █ ░█ ░██░▒▓█  ▄ ░█░ █ ░█  │
│ ▒██▒ █▄░██░▒ ▓███▀ ░▒██▒ █▄   ░░██▒██▓ ░██░░▒████▒░░██▒██▓  │
│ ▒ ▒▒ ▓▒░▓  ░ ░▒ ▒  ░▒ ▒▒ ▓▒   ░ ▓░▒ ▒  ░▓  ░░ ▒░ ░░ ▓░▒ ▒   │
│ ░ ░▒ ▒░ ▒ ░  ░  ▒   ░ ░▒ ▒░     ▒ ░ ░   ▒ ░ ░ ░  ░  ▒ ░ ░   │
│ ░ ░░ ░  ▒ ░░        ░ ░░ ░      ░   ░   ▒ ░   ░     ░   ░   │
│ ░  ░    ░  ░ ░      ░  ░          ░     ░     ░  ░    ░     │
│            ░                                                │                                                         
└─────────────────────────────────────────────────────────────┘
_______  __      __    ___ _____ ____  _   _ _   _ 
| () ) \/ /      \ \/\/ / |_   _/ (__`| |_| | |_| |
|_()_)|__|        \_/\_/|_| |_| \____)|_| |_|_| |_|
"""


def clear_screen():
    """Terminal ekranını temizle"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Banner'ı yazdır"""
    clear_screen()
    print(ASCII_LOGO)
    print(f"\n{Colors.CYAN}⚡ Sistem Bilgisi: {platform.system()} {platform.release()}{Colors.END}")
    print(f"{Colors.CYAN}⚡ Python: {platform.python_version()}{Colors.END}")
    print(f"{Colors.CYAN}⚡ Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")


# ==================== ENUM VE VERİ SINIFLARI ====================

class ConnectionState(Enum):
    """Bağlantı durumları"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    STOPPED = "stopped"
    
    def color(self) -> str:
        """Duruma göre renk döndür"""
        colors = {
            ConnectionState.INITIALIZING: Colors.BLUE,
            ConnectionState.CONNECTING: Colors.YELLOW,
            ConnectionState.CONNECTED: Colors.GREEN,
            ConnectionState.RECONNECTING: Colors.MAGENTA,
            ConnectionState.FAILED: Colors.RED,
            ConnectionState.STOPPED: Colors.WHITE,
        }
        return colors.get(self, Colors.END)


class ProxyType(Enum):
    """Proxy tipleri"""
    HTTP = "http"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    
    def icon(self) -> str:
        """Proxy tipine göre ikon"""
        icons = {
            ProxyType.HTTP: "🌐",
            ProxyType.SOCKS4: "🧦",
            ProxyType.SOCKS5: "🧦",
        }
        return icons.get(self, "🔌")


@dataclass
class ProxyMetrics:
    """Proxy metrikleri"""
    total_requests: int = 100000
    successful_requests: int = 100000
    failed_requests: int = 0
    total_bytes_sent: int = 100000
    total_bytes_received: int = 100000
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class ProxyEntry:
    """Proxy girişi"""
    raw: str
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP
    country: Optional[str] = None
    city: Optional[str] = None
    is_anonymous: bool = True
    metrics: ProxyMetrics = field(default_factory=ProxyMetrics)
    is_active: bool = True
    cooldown_until: Optional[datetime] = None
    
    @property
    def http_url(self) -> str:
        """HTTP proxy URL'si"""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"http://{self.ip}:{self.port}"
    
    @property
    def ws_proxy(self) -> Optional["Proxy"]:
        """WebSocket proxy objesi"""
        if Proxy is not None:
            try:
                return Proxy.from_url(self.http_url)
            except Exception:
                return None
        return None
    
    @property
    def label(self) -> str:
        """Proxy etiketi (loglar için)"""
        base = f"{self.ip}:{self.port}"
        if self.country:
            base = f"{base} [{self.country}]"
        return base
    
    @property
    def display(self) -> str:
        """Renkli display formatı"""
        status = "🟢" if self.is_active and not self.is_on_cooldown() else "🔴"
        success_rate = f"{self.success_rate:.1f}%"
        return f"{status} {self.proxy_type.icon()} {self.ip}:{self.port} [{success_rate}]"
    
    @property
    def success_rate(self) -> float:
        """Başarı oranı"""
        if self.metrics.total_requests == 0:
            return 100.0
        return (self.metrics.successful_requests / self.metrics.total_requests) * 100
    
    def is_on_cooldown(self) -> bool:
        """Cooldown kontrolü"""
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return True
        return False


@dataclass
class ConnectionMetrics:
    """Bağlantı metrikleri"""
    connection_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    reconnects: int = 0
    errors: List[Tuple[datetime, str]] = field(default_factory=list)
    state: ConnectionState = ConnectionState.INITIALIZING
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Bağlantı süresi"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def display_state(self) -> str:
        """Renkli durum gösterimi"""
        return f"{self.state.color()}{self.state.value}{Colors.END}"


@dataclass
class StreamInfo:
    """Stream bilgileri"""
    channel_id: int
    channel_name: str
    stream_title: str
    streamer_name: str
    category: str
    tags: List[str]
    viewer_count: int
    started_at: datetime
    quality_options: List[str]
    playback_url: str


@dataclass
class BotStats:
    """Bot istatistikleri"""
    start_time: datetime = field(default_factory=datetime.now)
    total_connections: int = 0
    active_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_retries: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    connection_history: List[ConnectionMetrics] = field(default_factory=list)
    
    @property
    def uptime(self) -> timedelta:
        """Çalışma süresi"""
        return datetime.now() - self.start_time
    
    @property
    def uptime_str(self) -> str:
        """Formatlanmış çalışma süresi"""
        seconds = int(self.uptime.total_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @property
    def success_rate(self) -> float:
        """Başarı oranı"""
        if self.total_connections == 0:
            return 0.0
        return (self.successful_connections / self.total_connections) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatında istatistikler"""
        return {
            "uptime_seconds": self.uptime.total_seconds(),
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "success_rate": self.success_rate,
            "total_retries": self.total_retries,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "errors_by_type": dict(self.errors_by_type)
        }


# ==================== GELİŞMİŞ LOGGER ====================

class ColoredFormatter(logging.Formatter):
    """Renkli log formatı"""
    
    COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.MAGENTA + Colors.BOLD,
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        return f"{color}{icon} {log_message}{Colors.END}"


class Spinner:
    """Terminal spinner animasyonu"""
    
    def __init__(self, message: str = "İşlem devam ediyor"):
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.running = False
        self.task = None
    
    async def start(self):
        """Spinner'ı başlat"""
        self.running = True
        self.task = asyncio.create_task(self._spin())
    
    async def _spin(self):
        """Spinner animasyonu"""
        i = 0
        while self.running:
            print(f'\r{Colors.CYAN}{self.spinner_chars[i % len(self.spinner_chars)]}{Colors.END} {self.message}', end='', flush=True)
            i += 1
            await asyncio.sleep(0.1)
        print('\r' + ' ' * (len(self.message) + 10), end='\r', flush=True)
    
    async def stop(self):
        """Spinner'ı durdur"""
        self.running = False
        if self.task:
            await self.task


class ProgressBar:
    """Terminal progress bar"""
    
    def __init__(self, total: int, width: int = 40, prefix: str = ''):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
    
    def update(self, n: int = 1):
        """Progress bar'ı güncelle"""
        self.current = min(self.current + n, self.total)
        self._draw()
    
    def _draw(self):
        """Progress bar'ı çiz"""
        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = '█' * filled + '░' * (self.width - filled)
        
        color = Colors.GREEN
        if percent < 0.3:
            color = Colors.RED
        elif percent < 0.6:
            color = Colors.YELLOW
        
        print(f'\r{self.prefix} [{color}{bar}{Colors.END}] {self.current}/{self.total} (%{percent*100:.1f})', end='', flush=True)
        
        if self.current >= self.total:
            print()


def setup_logging(
    verbose: bool = False,
    log_file: Optional[str] = None,
    json_log: Optional[str] = None,
    queue: Optional[Queue] = None
) -> None:
    """Loglama sistemini kur"""
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Mevcut handler'ları temizle
    logger.handlers.clear()
    
    # Console handler (renkli)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Dosya handler (plain text)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # JSON log handler
    if json_log:
        json_handler = JSONFileHandler(json_log)
        json_handler.setLevel(logging.INFO)
        logger.addHandler(json_handler)
    
    # Queue handler (GUI)
    if queue:
        queue_handler = QueueHandler(queue)
        queue_handler.setLevel(logging.INFO)
        queue_formatter = logging.Formatter('%(asctime)s | %(message)s')
        queue_handler.setFormatter(queue_formatter)
        logger.addHandler(queue_handler)


class JSONFileHandler(logging.Handler):
    """JSON formatında log dosyası"""
    
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        """Dosyanın varlığını kontrol et"""
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno
            }
            
            # Mevcut logları oku
            with open(self.filename, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # Yeni logu ekle
            logs.append(log_entry)
            
            # Son 1000 logu tut
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Dosyaya yaz
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass


class QueueHandler(logging.Handler):
    """Kuyruk log handler (GUI için)"""
    
    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put_nowait(msg)
        except Exception:
            pass


# ==================== USER-AGENT YÖNETİCİSİ ====================

class UserAgentManager:
    """User-Agent yönetimi"""
    
    BROWSERS = {
        'chrome': {
            'templates': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
            ],
            'icon': '🌐'
        },
        'firefox': {
            'templates': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}) Gecko/20100101 Firefox/{version}",
                "Mozilla/5.0 (X11; Linux i686; rv:{version}) Gecko/20100101 Firefox/{version}",
            ],
            'icon': '🦊'
        },
        'safari': {
            'templates': [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15",
            ],
            'icon': '🧭'
        },
        'edge': {
            'templates': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{edge_version}",
            ],
            'icon': '🌍'
        }
    }
    
    def __init__(self, custom_file: Optional[str] = None):
        self.agents: List[str] = []
        self.custom_agents: List[str] = []
        self.load_agents(custom_file)
        self._lock = asyncio.Lock()
        
    def load_agents(self, custom_file: Optional[str] = None):
        """User-Agent'leri yükle"""
        if custom_file and Path(custom_file).exists():
            with open(custom_file, 'r', encoding='utf-8') as f:
                self.custom_agents = [line.strip() for line in f if line.strip()]
            logging.info(f"{Colors.GREEN}✅ {len(self.custom_agents)} custom User-Agent yüklendi{Colors.END}")
        
        self._generate_modern_agents()
        
    def _generate_modern_agents(self, count: int = 100):
        """Modern User-Agent'leri oluştur"""
        agents = []
        
        for _ in range(count):
            browser = random.choice(list(self.BROWSERS.keys()))
            data = self.BROWSERS[browser]
            template = random.choice(data['templates'])
            
            if browser == 'chrome':
                version = f"{random.randint(120, 130)}.0.{random.randint(6000, 6500)}.{random.randint(100, 200)}"
                agents.append(template.format(version=version))
            elif browser == 'firefox':
                version = f"{random.randint(110, 125)}.0"
                agents.append(template.format(version=version))
            elif browser == 'safari':
                version = f"{random.randint(15, 17)}.{random.randint(0, 5)}"
                agents.append(template.format(version=version))
            elif browser == 'edge':
                chrome_version = f"{random.randint(120, 130)}.0.{random.randint(6000, 6500)}.{random.randint(100, 200)}"
                edge_version = f"{random.randint(115, 125)}.0.{random.randint(1800, 1900)}.{random.randint(50, 100)}"
                agents.append(template.format(chrome_version=chrome_version, edge_version=edge_version))
        
        self.agents = agents + self.custom_agents
        logging.info(f"{Colors.GREEN}✅ Toplam {len(self.agents)} User-Agent hazır{Colors.END}")
    
    async def get_random(self) -> str:
        """Rastgele User-Agent al"""
        async with self._lock:
            return random.choice(self.agents) if self.agents else generate_user_agent()
    
    async def get_rotated(self, count: int) -> List[str]:
        """Farklı User-Agent'lerden oluşan liste al"""
        async with self._lock:
            if len(self.agents) < count:
                return random.choices(self.agents, k=count)
            return random.sample(self.agents, count)


def generate_user_agent() -> str:
    """Basit User-Agent oluşturucu (fallback)"""
    chrome_version = f"{random.randint(120, 130)}.0.{random.randint(6000, 6500)}.{random.randint(100, 200)}"
    platforms = [
        f"Windows NT {random.choice(['10.0', '11.0'])}; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7",
        "X11; Linux x86_64",
        "iPhone; CPU iPhone OS 17_{} like Mac OS X".format(random.randint(0, 5)),
    ]
    platform = random.choice(platforms)
    return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"


# ==================== PROXY HAVUZU ====================

class ProxyPool:
    """Gelişmiş proxy havuzu yöneticisi"""
    
    def __init__(
        self,
        proxy_file: Optional[str] = None,
        cooldown: float = 45.0,
        max_failures: int = 3,
        test_timeout: float = 5.0
    ):
        self.cooldown = max(0.0, cooldown)
        self.max_failures = max_failures
        self.test_timeout = test_timeout
        self.proxies: List[ProxyEntry] = []
        self._lock = asyncio.Lock()
        self._healthy_proxies: Set[str] = set()
        self._dead_proxies: Set[str] = set()
        
        if proxy_file:
            self.load_from_file(proxy_file)
        else:
            logging.info(f"{Colors.YELLOW}ℹ️ Proxy dosyası belirtilmedi, proxysiz mod aktif{Colors.END}")
    
    def load_from_file(self, path: str) -> None:
        """Proxy dosyasından yükle"""
        if not os.path.exists(path):
            logging.warning(f"{Colors.YELLOW}⚠️ Proxy dosyası bulunamadı: {path}, proxysiz mod aktif{Colors.END}")
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        valid_count = 0
        invalid_count = 0
        
        for line in lines:
            entry = self._parse_proxy_line(line)
            if entry:
                self.proxies.append(entry)
                valid_count += 1
            else:
                invalid_count += 1
        
        if valid_count > 0:
            logging.info(f"{Colors.GREEN}✅ {valid_count} geçerli proxy yüklendi{Colors.END}")
        if invalid_count > 0:
            logging.warning(f"{Colors.YELLOW}⚠️ {invalid_count} geçersiz proxy satırı atlandı{Colors.END}")
        
        if valid_count == 0:
            logging.warning(f"{Colors.YELLOW}⚠️ Hiç geçerli proxy bulunamadı, proxysiz mod çalışacak{Colors.END}")
    
    def _parse_proxy_line(self, line: str) -> Optional[ProxyEntry]:
        """Proxy satırını parse et"""
        try:
            proxy_type = ProxyType.HTTP
            username = None
            password = None
            ip = None
            port = None
            
            # Protocol kontrolü
            if line.startswith(('http://', 'socks4://', 'socks5://')):
                if line.startswith('socks4://'):
                    proxy_type = ProxyType.SOCKS4
                    line = line[9:]
                elif line.startswith('socks5://'):
                    proxy_type = ProxyType.SOCKS5
                    line = line[10:]
                else:
                    line = line[7:]  # http://
            
            # Authentication kontrolü
            if '@' in line:
                auth, address = line.split('@', 1)
                if ':' in auth:
                    username, password = auth.split(':', 1)
                else:
                    username = auth
                    password = ''
            else:
                address = line
            
            # IP:Port kontrolü
            if ':' in address:
                ip, port_str = address.split(':', 1)
                port = int(port_str)
            else:
                return None
            
            return ProxyEntry(
                raw=line,
                ip=ip,
                port=port,
                username=username,
                password=password,
                proxy_type=proxy_type
            )
            
        except Exception as e:
            logging.debug(f"Proxy parse hatası: {line} -> {e}")
            return None
    
    async def get_proxy(self, strategy: str = 'smart') -> Optional[ProxyEntry]:
        """Akıllı proxy seçimi"""
        async with self._lock:
            if not self.proxies:
                return None
            
            now = datetime.now()
            available = [
                p for p in self.proxies
                if p.is_active
                and not p.is_on_cooldown()
                and p.metrics.consecutive_failures < self.max_failures
            ]
            
            if not available:
                # Cooldown'daki en yakın proxy'yi bul
                cooldown_proxies = [
                    p for p in self.proxies
                    if p.is_active and p.cooldown_until
                ]
                if cooldown_proxies:
                    return min(cooldown_proxies, key=lambda p: p.cooldown_until)
                return None
            
            if strategy == 'round_robin':
                proxy = available[len(self._healthy_proxies) % len(available)]
            elif strategy == 'smart':
                def score(p: ProxyEntry) -> float:
                    success_score = p.success_rate / 100
                    usage_score = 1.0 / (p.metrics.total_requests + 1)
                    return success_score * 0.7 + usage_score * 0.3
                
                proxy = max(available, key=score)
            else:
                proxy = random.choice(available)
            
            proxy.metrics.total_requests += 1
            proxy.metrics.last_used = now
            
            return proxy
    
    async def mark_success(self, proxy: Optional[ProxyEntry]):
        """Başarılı proxy işaretle"""
        if not proxy:
            return
        
        async with self._lock:
            proxy.metrics.successful_requests += 1
            proxy.metrics.consecutive_failures = 0
            proxy.cooldown_until = None
            self._healthy_proxies.add(proxy.raw)
            self._dead_proxies.discard(proxy.raw)
    
    async def mark_failure(
        self,
        proxy: Optional[ProxyEntry],
        error: Optional[str] = None
    ):
        """Başarısız proxy işaretle"""
        if not proxy:
            return
        
        async with self._lock:
            proxy.metrics.failed_requests += 1
            proxy.metrics.consecutive_failures += 1
            proxy.metrics.last_error = error
            
            if proxy.metrics.consecutive_failures >= self.max_failures:
                cooldown_time = self.cooldown * (2 ** (proxy.metrics.consecutive_failures - self.max_failures))
                proxy.cooldown_until = datetime.now() + timedelta(seconds=cooldown_time)
                self._dead_proxies.add(proxy.raw)
                self._healthy_proxies.discard(proxy.raw)
            else:
                proxy.cooldown_until = datetime.now() + timedelta(seconds=10)
    
    def display_proxy_list(self):
        """Proxy listesini göster"""
        if not self.proxies:
            print(f"{Colors.YELLOW}📋 Proxy listesi boş{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}📋 PROXY LİSTESİ ({len(self.proxies)} adet){Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        
        for i, proxy in enumerate(self.proxies[:10], 1):  # İlk 10 proxy'yi göster
            status = "🟢" if not proxy.is_on_cooldown() else "🔴"
            print(f"{status} {i:2d}. {proxy.ip}:{proxy.port} | Başarı: %{proxy.success_rate:.1f} | İstek: {proxy.metrics.total_requests}")
        
        if len(self.proxies) > 10:
            print(f"{Colors.WHITE}... ve {len(self.proxies) - 10} proxy daha{Colors.END}")
        print()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Proxy havuzu istatistikleri"""
        return {
            "total": len(self.proxies),
            "healthy": len(self._healthy_proxies),
            "dead": len(self._dead_proxies),
            "cooldown": len([p for p in self.proxies if p.is_on_cooldown()]),
            "avg_success_rate": sum(p.success_rate for p in self.proxies) / len(self.proxies) if self.proxies else 0
        }


# ==================== RATE LİMİTER ====================

class TokenBucket:
    """Token bucket algoritması ile rate limiting"""
    
    def __init__(self, rate: float, capacity: Optional[float] = None):
        self.rate = rate
        self.capacity = capacity or rate
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: float = 1.0) -> bool:
        """Token tüket"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def acquire(self, tokens: float = 1.0):
        """Token alana kadar bekle"""
        while True:
            if await self.consume(tokens):
                return
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)


class AdaptiveRateLimiter:
    """Adaptif hız sınırlayıcı"""
    
    def __init__(self, initial_rate: float, min_rate: float = 1.0, max_rate: float = 1000.0):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.error_rate = 0.0
        self.total_requests = 0
        self.error_count = 0
        self._lock = asyncio.Lock()
        self._bucket = TokenBucket(initial_rate)
        self._last_adjustment = time.monotonic()
    
    async def acquire(self):
        """İzin al"""
        await self._bucket.acquire()
        
        async with self._lock:
            self.total_requests += 1
            
            now = time.monotonic()
            if now - self._last_adjustment > 10:
                await self._adjust_rate()
                self._last_adjustment = now
    
    async def record_error(self):
        """Hata kaydet"""
        async with self._lock:
            self.error_count += 1
            self.error_rate = self.error_count / max(1, self.total_requests)
    
    async def _adjust_rate(self):
        """Rate'i hata oranına göre ayarla"""
        if self.error_rate > 0.1:
            self.current_rate = max(self.min_rate, self.current_rate * 0.8)
            logging.debug(f"📉 Rate düşürüldü: {self.current_rate:.2f}/s (hata: %{self.error_rate:.2f})")
        elif self.error_rate < 0.01 and self.current_rate < self.max_rate:
            self.current_rate = min(self.max_rate, self.current_rate * 1.2)
            logging.debug(f"📈 Rate artırıldı: {self.current_rate:.2f}/s")
        
        self._bucket = TokenBucket(self.current_rate)


class PrioritySemaphore:
    """Öncelikli semaphore"""
    
    def __init__(self, value: int = 1):
        self.value = value
        self._low_prio_queue: asyncio.Queue = asyncio.Queue()
        self._high_prio_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
    
    async def acquire(self, priority: bool = False):
        """Semaphore edin"""
        queue = self._high_prio_queue if priority else self._low_prio_queue
        fut = asyncio.Future()
        await queue.put(fut)
        
        async with self._lock:
            if self.value > 0 and (priority or self._high_prio_queue.empty()):
                self.value -= 1
                fut.set_result(True)
                await queue.get()
        
        return await fut
    
    def release(self):
        """Semaphore serbest bırak"""
        self.value += 1
        self._wakeup_next()
    
    def _wakeup_next(self):
        """Sıradaki işlemi uyandır"""
        if not self._high_prio_queue.empty():
            fut = self._high_prio_queue.get_nowait()
            if not fut.done():
                self.value -= 1
                fut.set_result(True)
        elif not self._low_prio_queue.empty():
            fut = self._low_prio_queue.get_nowait()
            if not fut.done():
                self.value -= 1
                fut.set_result(True)
    
    @contextlib.asynccontextmanager
    async def guard(self, priority: bool = False):
        """Context manager desteği"""
        await self.acquire(priority)
        try:
            yield
        finally:
            self.release()


# ==================== İSTATİSTİK TOPLAYICI ====================

class StatsCollector:
    """Gelişmiş istatistik toplayıcı"""
    
    def __init__(self):
        self._stats = BotStats()
        self._lock = asyncio.Lock()
        self._listeners: List[Callable] = []
        self._snapshots: List[Dict] = []
        self._max_snapshots = 100
    
    async def record_connection_start(self) -> int:
        """Yeni bağlantı kaydet"""
        async with self._lock:
            self._stats.total_connections += 1
            self._stats.active_connections += 1
            return self._stats.total_connections
    
    async def record_connection_success(self, metrics: ConnectionMetrics):
        """Başarılı bağlantı kaydet"""
        async with self._lock:
            self._stats.successful_connections += 1
            self._stats.connection_history.append(metrics)
            if len(self._stats.connection_history) > 1000:
                self._stats.connection_history = self._stats.connection_history[-1000:]
    
    async def record_connection_close(self):
        """Bağlantı kapanışı kaydet"""
        async with self._lock:
            self._stats.active_connections = max(0, self._stats.active_connections - 1)
    
    async def record_error(self, error_type: str):
        """Hata kaydet"""
        async with self._lock:
            self._stats.errors_by_type[error_type] += 1
    
    async def record_retry(self):
        """Yeniden deneme kaydet"""
        async with self._lock:
            self._stats.total_retries += 1
    
    async def record_bytes(self, sent: int = 0, received: int = 0):
        """Byte transfer kaydet"""
        async with self._lock:
            self._stats.total_bytes_sent += sent
            self._stats.total_bytes_received += received
    
    async def record_messages(self, sent: int = 0, received: int = 0):
        """Mesaj sayısı kaydet"""
        async with self._lock:
            self._stats.total_messages_sent += sent
            self._stats.total_messages_received += received
    
    async def take_snapshot(self) -> Dict:
        """Anlık görüntü al"""
        async with self._lock:
            snapshot = self._stats.to_dict()
            snapshot['timestamp'] = datetime.now().isoformat()
            
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots:]
            
            return snapshot
    
    async def get_stats(self) -> BotStats:
        """İstatistikleri al"""
        async with self._lock:
            return self._stats
    
    def add_listener(self, callback: Callable):
        """Listener ekle"""
        self._listeners.append(callback)
    
    async def notify_listeners(self):
        """Listener'ları bilgilendir"""
        stats = await self.get_stats()
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(stats)
                else:
                    listener(stats)
            except Exception as e:
                logging.error(f"Listener hatası: {e}")


# ==================== KICK API İSTEMCİSİ ====================

class KickAPIClient:
    """Kick.com API istemcisi"""
    
    def __init__(
        self,
        client_token: str,
        proxy: Optional[ProxyEntry] = None,
        timeout: int = 25
    ):
        self.client_token = client_token
        self.proxy = proxy
        self.timeout = timeout
        self.session: Optional[tls_client.Session] = None
        self._create_session()
    
    def _create_session(self):
        """TLS session oluştur"""
        self.session = tls_client.Session(
            client_identifier=f"chrome_{random.randint(120, 130)}",
            random_tls_extension_order=True
        )
        self.session.timeout = self.timeout
        
        self.session.headers.update({
            "User-Agent": generate_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://kick.com",
            "Referer": "https://kick.com/",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        if self.proxy:
            self.session.proxies = {
                "http": self.proxy.http_url,
                "https": self.proxy.http_url
            }
    
    async def fetch_token(self) -> str:
        """WebSocket token'ı al"""
        def _fetch():
            self.session.get("https://kick.com")
            self.session.headers.update({"X-CLIENT-TOKEN": self.client_token})
            
            response = self.session.get(
                "https://websockets.kick.com/viewer/v1/token",
                timeout_seconds=self.timeout
            )
            
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Token request failed: {response.status_code}"
                )
            
            data = response.json()
            return data["data"]["token"]
        
        return await asyncio.to_thread(_fetch)
    
    async def fetch_channel_info(self, channel: str) -> StreamInfo:
        """Kanal bilgilerini al"""
        def _fetch():
            response = self.session.get(
                f"https://kick.com/api/v2/channels/{channel}",
                timeout_seconds=self.timeout
            )
            
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Channel request failed: {response.status_code}"
                )
            
            data = response.json()
            
            channel_id = data.get("id") or data.get("data", {}).get("id")
            if not channel_id:
                raise ValueError("Channel ID not found")
            
            return StreamInfo(
                channel_id=int(channel_id),
                channel_name=channel,
                stream_title=data.get("title", "Offline"),
                streamer_name=data.get("user", {}).get("username", channel),
                category=data.get("category", {}).get("name", "Unknown"),
                tags=data.get("tags", []),
                viewer_count=data.get("viewer_count", 0),
                started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
                quality_options=data.get("playback_urls", []),
                playback_url=data.get("playback_url", "")
            )
        
        return await asyncio.to_thread(_fetch)
    
    def close(self):
        """Session'ı kapat"""
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass


# ==================== WEBSOCKET BAĞLANTISI ====================

class WebSocketConnection:
    """WebSocket bağlantı yöneticisi"""
    
    def __init__(
        self,
        connection_id: int,
        token: str,
        channel_id: int,
        proxy: Optional[ProxyEntry],
        user_agent: str,
        stats: StatsCollector,
        settings: 'BotSettings'
    ):
        self.id = connection_id
        self.token = token
        self.channel_id = channel_id
        self.proxy = proxy
        self.user_agent = user_agent
        self.stats = stats
        self.settings = settings
        
        self.ws: Optional[Any] = None
        self.metrics = ConnectionMetrics(
            connection_id=connection_id,
            start_time=datetime.now()
        )
        self.state = ConnectionState.INITIALIZING
        self._stop_event = asyncio.Event()
        self._reconnect_count = 0
        self._last_pong = datetime.now()
    
    @property
    def label(self) -> str:
        """Worker etiketi"""
        proxy_label = self.proxy.label if self.proxy else "🌐 proxyless"
        return f"[{self.id:04d} | {proxy_label[:20]}]"
    
    async def connect(self) -> bool:
        """WebSocket bağlantısı kur"""
        headers = {
            "User-Agent": self.user_agent,
            "Origin": "https://kick.com",
            "Cookie": f"client_token={self.settings.client_token}",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        url = f"wss://websockets.kick.com/viewer/v1/connect?token={self.token}&EIO=4&transport=websocket"
        
        connect_kwargs = {
            "additional_headers": headers,
            "ping_interval": None,
            "open_timeout": self.settings.ws_timeout,
            "close_timeout": 20,
            "max_size": 2**20,
        }
        
        if self.proxy and self.proxy.ws_proxy:
            connect_kwargs["proxy"] = self.proxy.ws_proxy
        
        try:
            self.state = ConnectionState.CONNECTING
            self.ws = await connect(url, **connect_kwargs)
            
            handshake = json.dumps({
                "type": "channel_handshake",
                "data": {
                    "message": {
                        "channelId": self.channel_id
                    }
                }
            })
            
            await self.ws.send(handshake)
            await self.stats.record_messages(sent=1)
            
            self.state = ConnectionState.CONNECTED
            self.metrics.state = ConnectionState.CONNECTED
            logging.info(f"{self.label} {Colors.GREEN}✅ WebSocket bağlandı{Colors.END}")
            
            return True
            
        except Exception as e:
            self.state = ConnectionState.FAILED
            self.metrics.errors.append((datetime.now(), str(e)))
            logging.debug(f"{self.label} {Colors.RED}❌ Bağlantı hatası: {e}{Colors.END}")
            return False
    
    async def maintain(self):
        """Bağlantıyı canlı tut"""
        iteration = 0
        
        while not self._stop_event.is_set() and self.ws:
            try:
                low, high = self.settings.keepalive_range
                delay = random.uniform(low, high)
                
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=delay
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                
                if self._stop_event.is_set():
                    break
                
                iteration += 1
                
                if iteration % self.settings.ping_period == 0:
                    payload = json.dumps({"type": "ping"})
                else:
                    payload = json.dumps({
                        "type": "channel_handshake",
                        "data": {
                            "message": {
                                "channelId": self.channel_id
                            }
                        }
                    })
                
                await self.ws.send(payload)
                await self.stats.record_messages(sent=1)
                self.metrics.messages_sent += 1
                
                try:
                    message = await asyncio.wait_for(
                        self.ws.recv(),
                        timeout=self.settings.read_timeout
                    )
                    await self.stats.record_messages(received=1)
                    await self.stats.record_bytes(received=len(message))
                    self.metrics.messages_received += 1
                    self.metrics.bytes_received += len(message)
                    
                    if message and 'pong' in str(message).lower():
                        self._last_pong = datetime.now()
                        
                except asyncio.TimeoutError:
                    continue
                    
            except ConnectionClosed:
                logging.debug(f"{self.label} {Colors.YELLOW}⚠️ Bağlantı kapandı{Colors.END}")
                break
                
            except Exception as e:
                logging.debug(f"{self.label} {Colors.RED}❌ Mesaj hatası: {e}{Colors.END}")
                self.metrics.errors.append((datetime.now(), str(e)))
                break
    
    async def stop(self):
        """Bağlantıyı durdur"""
        self._stop_event.set()
        self.state = ConnectionState.STOPPED
        self.metrics.state = ConnectionState.STOPPED
        self.metrics.end_time = datetime.now()
        
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        
        await self.stats.record_connection_close()
    
    async def run(self) -> bool:
        """Ana bağlantı döngüsü"""
        await self.stats.record_connection_start()
        
        try:
            if await self.connect():
                await self.stats.record_connection_success(self.metrics)
                await self.maintain()
                return True
        except Exception as e:
            logging.error(f"{self.label} {Colors.RED}❌ Çalışma hatası: {e}{Colors.END}")
            self.metrics.errors.append((datetime.now(), str(e)))
            await self.stats.record_error(type(e).__name__)
        
        return False


# ==================== VIEWER WORKER ====================

class ViewerWorker:
    """İzleyici worker'ı"""
    
    def __init__(
        self,
        worker_id: int,
        channel: str,
        settings: 'BotSettings',
        proxy_pool: ProxyPool,
        http_gate: PrioritySemaphore,
        http_limiter: AdaptiveRateLimiter,
        stats: StatsCollector,
        ua_manager: UserAgentManager
    ):
        self.id = worker_id
        self.channel = channel
        self.settings = settings
        self.proxy_pool = proxy_pool
        self.http_gate = http_gate
        self.http_limiter = http_limiter
        self.stats = stats
        self.ua_manager = ua_manager
        
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._connection: Optional[WebSocketConnection] = None
        self._retry_count = 0
        self._last_error: Optional[str] = None
    
    @property
    def is_running(self) -> bool:
        """Çalışıyor mu?"""
        return self._task is not None and not self._task.done()
    
    async def _get_auth_data(self) -> Tuple[Optional[str], Optional[int]]:
        """Token ve channel ID al"""
        token = None
        channel_id = None
        
        try:
            await self.http_limiter.acquire()
            
            async with self.http_gate.guard(priority=True):
                proxy = await self.proxy_pool.get_proxy()
                
                client = KickAPIClient(
                    self.settings.client_token,
                    proxy,
                    self.settings.http_timeout
                )
                
                try:
                    token = await client.fetch_token()
                    stream_info = await client.fetch_channel_info(self.channel)
                    channel_id = stream_info.channel_id
                    
                    await self.proxy_pool.mark_success(proxy)
                    
                except Exception as e:
                    await self.proxy_pool.mark_failure(proxy, str(e))
                    await self.stats.record_error(type(e).__name__)
                    await self.http_limiter.record_error()
                    raise
                    
                finally:
                    client.close()
            
            self._retry_count = 0
            
        except Exception as e:
            logging.debug(f"Worker {self.id} auth hatası: {e}")
            self._last_error = str(e)
            await self.stats.record_retry()
        
        return token, channel_id
    
    async def run(self):
        """Worker çalıştır"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(random.uniform(*self.settings.ramp_delay_range))
                
                if self._stop_event.is_set():
                    break
                
                token, channel_id = await self._get_auth_data()
                
                if not token or not channel_id:
                    await asyncio.sleep(self._get_retry_delay())
                    continue
                
                user_agent = await self.ua_manager.get_random()
                proxy = await self.proxy_pool.get_proxy()
                
                self._connection = WebSocketConnection(
                    connection_id=self.id,
                    token=token,
                    channel_id=channel_id,
                    proxy=proxy,
                    user_agent=user_agent,
                    stats=self.stats,
                    settings=self.settings
                )
                
                success = await self._connection.run()
                
                if success:
                    await self.proxy_pool.mark_success(proxy)
                else:
                    await self.proxy_pool.mark_failure(proxy, "connection_failed")
                    self._retry_count += 1
                    await self.stats.record_retry()
                    await asyncio.sleep(self._get_retry_delay())
                
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                logging.error(f"Worker {self.id} beklenmeyen hata: {e}")
                self._retry_count += 1
                await self.stats.record_error(type(e).__name__)
                await asyncio.sleep(self._get_retry_delay())
    
    def _get_retry_delay(self) -> float:
        """Exponential backoff ile yeniden deneme süresi"""
        base = random.uniform(*self.settings.retry_delay_range)
        multiplier = min(2 ** self._retry_count, 60)
        return base * multiplier
    
    async def start(self):
        """Worker başlat"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name=f"worker-{self.id}")
    
    async def stop(self):
        """Worker durdur"""
        self._stop_event.set()
        
        if self._connection:
            await self._connection.stop()
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# ==================== BOT AYARLARI ====================

@dataclass
class BotSettings:
    """Bot ayarları"""
    channel: str
    viewer_goal: int
    max_concurrent: Optional[int] = None
    proxy_file: Optional[str] = None
    client_token: str = DEFAULT_CLIENT_TOKEN
    proxy_permits: int = 10
    keepalive_range: Tuple[float, float] = (13.0, 21.0)
    ping_period: int = 6
    retry_delay_range: Tuple[float, float] = (2.0, 6.0)
    ramp_delay_range: Tuple[float, float] = (0.15, 0.75)
    status_interval: float = 30.0
    proxy_cooldown: float = 45.0
    http_timeout: int = 25
    ws_timeout: int = 30
    read_timeout: float = 10.0
    http_gate: Optional[int] = None
    http_rps: Optional[float] = 120.0
    log_file: Optional[str] = None
    json_log: Optional[str] = None
    verbose: bool = False
    auto_start: bool = False
    user_agent_file: Optional[str] = None
    max_retries: int = 10
    
    def effective_concurrency(self, proxy_count: int) -> int:
        """Etkin eşzamanlılık sayısı"""
        per_proxy_cap = proxy_count * self.proxy_permits if proxy_count else self.viewer_goal
        requested = self.max_concurrent or self.viewer_goal
        return max(1, min(requested, per_proxy_cap, self.viewer_goal, MAX_VIEWERS_LIMIT))
    
    def display(self):
        """Ayarları göster"""
        print(f"\n{Colors.CYAN}⚙️  BOT YAPILANDIRMASI{Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}📺 Kanal:{Colors.END} {self.channel}")
        print(f"{Colors.GREEN}🎯 Hedef:{Colors.END} {self.viewer_goal} izleyici")
        print(f"{Colors.GREEN}🌐 Proxy:{Colors.END} {self.proxy_file or 'Belirtilmedi (proxysiz)'}")
        print(f"{Colors.GREEN}🔄 Keepalive:{Colors.END} {self.keepalive_range[0]}-{self.keepalive_range[1]} sn")
        print(f"{Colors.GREEN}⏱️  Retry:{Colors.END} {self.retry_delay_range[0]}-{self.retry_delay_range[1]} sn")
        print(f"{Colors.GREEN}🚦 HTTP Gate:{Colors.END} {self.http_gate or 'Otomatik'}")
        print(f"{Colors.GREEN}📊 HTTP RPS:{Colors.END} {self.http_rps or 'Limitsiz'}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}\n")


# ==================== ANA BOT SINIFI ====================

class KickViewerBot:
    """Ana bot sınıfı"""
    
    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.proxy_pool = ProxyPool(settings.proxy_file, settings.proxy_cooldown)
        self.stats = StatsCollector()
        self.ua_manager = UserAgentManager(settings.user_agent_file)
        
        http_gate_size = self._calculate_http_gate_size()
        self.http_gate = PrioritySemaphore(http_gate_size)
        self.http_limiter = AdaptiveRateLimiter(
            initial_rate=settings.http_rps or 100.0,
            min_rate=10.0,
            max_rate=200.0
        )
        
        self.workers: List[ViewerWorker] = []
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
    
    def _calculate_http_gate_size(self) -> int:
        """HTTP gate boyutunu hesapla"""
        if self.settings.http_gate is not None:
            return max(1, self.settings.http_gate)
        
        base = self.settings.viewer_goal // 75
        return min(self.settings.viewer_goal, max(50, base))
    
    async def initialize(self):
        """Bot başlatma hazırlıkları"""
        print_banner()
        
        self.settings.display()
        self.proxy_pool.display_proxy_list()
        
        worker_count = self.settings.effective_concurrency(self.proxy_pool.stats['total'])
        
        logging.info(f"{Colors.CYAN}📊 SİSTEM BİLGİLERİ{Colors.END}")
        logging.info(f"{Colors.GREEN}📺 Kanal:{Colors.END} {self.settings.channel}")
        logging.info(f"{Colors.GREEN}🎯 Hedef:{Colors.END} {self.settings.viewer_goal} izleyici")
        logging.info(f"{Colors.GREEN}🌐 Proxy:{Colors.END} {self.proxy_pool.stats['total']} adet")
        logging.info(f"{Colors.GREEN}👥 Worker:{Colors.END} {worker_count}")
        logging.info(f"{Colors.GREEN}🚦 HTTP Gate:{Colors.END} {self.http_gate.value}")
        logging.info("")
        
        for i in range(worker_count):
            worker = ViewerWorker(
                worker_id=i + 1,
                channel=self.settings.channel,
                settings=self.settings,
                proxy_pool=self.proxy_pool,
                http_gate=self.http_gate,
                http_limiter=self.http_limiter,
                stats=self.stats,
                ua_manager=self.ua_manager
            )
            self.workers.append(worker)
    
    async def monitor_stats(self):
        """İstatistik monitörü"""
        while not self._stop_event.is_set():
            await asyncio.sleep(self.settings.status_interval)
            
            stats = await self.stats.get_stats()
            proxy_stats = self.proxy_pool.stats
            
            print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.WHITE}📊 CANLI İSTATİSTİKLER{Colors.END}")
            print(f"{Colors.CYAN}{'='*70}{Colors.END}")
            
            # Çalışma süresi
            print(f"{Colors.YELLOW}⏱️  Çalışma:{Colors.END} {stats.uptime_str}")
            
            # Bağlantılar
            active_color = Colors.GREEN if stats.active_connections > 0 else Colors.RED
            print(f"{active_color}🔗 Aktif:{Colors.END} {stats.active_connections}/{len(self.workers)}")
            print(f"{Colors.GREEN}✅ Başarılı:{Colors.END} {stats.successful_connections}")
            print(f"{Colors.RED}❌ Başarısız:{Colors.END} {stats.failed_connections}")
            print(f"{Colors.MAGENTA}🔄 Retry:{Colors.END} {stats.total_retries}")
            
            # Başarı oranı
            rate_color = Colors.GREEN if stats.success_rate > 80 else Colors.YELLOW if stats.success_rate > 50 else Colors.RED
            print(f"{rate_color}📈 Başarı Oranı:{Colors.END} %{stats.success_rate:.1f}")
            
            # Transfer
            print(f"{Colors.BLUE}📥 Transfer:{Colors.END} ↓{stats.total_bytes_received/1024:.1f}KB ↑{stats.total_bytes_sent/1024:.1f}KB")
            
            # Proxy durumu
            if proxy_stats['total'] > 0:
                healthy_color = Colors.GREEN if proxy_stats['healthy'] > 0 else Colors.RED
                dead_color = Colors.RED if proxy_stats['dead'] > 0 else Colors.GREEN
                print(f"{healthy_color}🌐 Sağlıklı Proxy:{Colors.END} {proxy_stats['healthy']} "
                      f"{dead_color}Ölü:{Colors.END} {proxy_stats['dead']} "
                      f"{Colors.YELLOW}Cooldown:{Colors.END} {proxy_stats['cooldown']}")
            
            # Hatalar
            if stats.errors_by_type:
                print(f"\n{Colors.RED}⚠️  SON HATALAR:{Colors.END}")
                top_errors = sorted(stats.errors_by_type.items(), key=lambda x: x[1], reverse=True)[:5]
                for error, count in top_errors:
                    print(f"  {Colors.RED}•{Colors.END} {error}: {count}")
            
            print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
            
            await self.stats.notify_listeners()
    
    async def run(self):
        """Botu çalıştır"""
        await self.initialize()
        
        if not self.settings.auto_start:
            input(f"\n{Colors.YELLOW}🚀 Başlatmak için ENTER'a basın (iptal için CTRL+C)...{Colors.END}\n")
            print()
        
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                signal.signal(sig, lambda *_: asyncio.create_task(self.stop()))
        
        self._monitor_task = asyncio.create_task(self.monitor_stats())
        
        logging.info(f"{Colors.GREEN}🚀 {len(self.workers)} worker başlatılıyor...{Colors.END}")
        
        for worker in self.workers:
            await worker.start()
            await asyncio.sleep(0.05)
        
        logging.info(f"{Colors.GREEN}✅ Tüm worker'lar başlatıldı. Çıkmak için CTRL+C{Colors.END}\n")
        
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()
    
    async def stop(self):
        """Botu durdur"""
        logging.info(f"{Colors.YELLOW}🛑 Durdurma sinyali alındı...{Colors.END}")
        self._stop_event.set()
    
    async def cleanup(self):
        """Temizlik işlemleri"""
        logging.info(f"{Colors.YELLOW}🛑 Worker'lar durduruluyor...{Colors.END}")
        
        stop_tasks = [worker.stop() for worker in self.workers]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        
        stats = await self.stats.get_stats()
        
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}📊 FİNAL İSTATİSTİKLERİ{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.YELLOW}⏱️  Çalışma:{Colors.END} {stats.uptime_str}")
        print(f"{Colors.GREEN}✅ Başarılı Bağlantı:{Colors.END} {stats.successful_connections}")
        print(f"{Colors.RED}❌ Başarısız Bağlantı:{Colors.END} {stats.failed_connections}")
        print(f"{Colors.MAGENTA}🔄 Toplam Retry:{Colors.END} {stats.total_retries}")
        print(f"{Colors.GREEN}📈 Başarı Oranı:{Colors.END} %{stats.success_rate:.1f}")
        print(f"{Colors.BLUE}📥 Toplam Transfer:{Colors.END} ↓{stats.total_bytes_received/1024:.1f}KB")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        logging.info(f"{Colors.GREEN}✅ Bot durduruldu.{Colors.END}")


# ==================== KONFİGÜRASYON YÜKLEME ====================

def load_config_file(path: str) -> Dict[str, Any]:
    """JSON konfigürasyon dosyasını yükle"""
    config_path = Path(path)
    if not config_path.exists():
        raise SystemExit(f"❌ Konfigürasyon dosyası bulunamadı: {path}")
    
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise SystemExit("❌ Konfigürasyon dosyası JSON nesnesi olmalı")
    
    return data


def parse_args() -> argparse.Namespace:
    """Komut satırı argümanlarını parse et"""
    parser = argparse.ArgumentParser(
        description="Kick.com Gelişmiş Asenkron İzleyici Botu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
╔══════════════════════════════════════════════════════════════╗
║                     ÖRNEK KULLANIM                          ║
╠══════════════════════════════════════════════════════════════╣
║  python kick_bot.py -c example -n 500                       ║
║  python kick_bot.py --config config.json                    ║
║  python kick_bot.py -c example -n 1000 -p proxies.txt       ║
║  python kick_bot.py -c example -n 2000 --verbose            ║
╚══════════════════════════════════════════════════════════════╝
        """
    )
    
    parser.add_argument("--config", help="📄 JSON konfigürasyon dosyası")
    parser.add_argument("-c", "--channel", help="📺 Kick kanal adı")
    parser.add_argument("-n", "--viewers", type=int, help="🎯 Hedef izleyici sayısı (max 10000)")
    parser.add_argument("-p", "--proxy-file", help="🌐 Proxy dosyası yolu")
    parser.add_argument("-m", "--max-concurrent", type=int, help="👥 Maksimum eşzamanlı bağlantı")
    parser.add_argument("--keepalive", nargs=2, type=float, metavar=("MIN", "MAX"), 
                       help="🔄 Keepalive aralığı")
    parser.add_argument("--retry-delay", nargs=2, type=float, metavar=("MIN", "MAX"),
                       help="⏱️  Yeniden deneme gecikmesi")
    parser.add_argument("--http-gate", type=int, help="🚦 Eşzamanlı HTTP istek limiti")
    parser.add_argument("--http-rps", type=float, help="📊 Saniyelik HTTP istek limiti")
    parser.add_argument("--log-file", help="📝 Log dosyası yolu")
    parser.add_argument("--verbose", action="store_true", help="🔍 Detaylı log")
    parser.add_argument("--quiet", action="store_true", help="🤫 Sessiz mod")
    parser.add_argument("--auto-start", action="store_true", help="⚡ Onay beklemeden başlat")
    parser.add_argument("--version", action="version", version=f"Kick Bot v{VERSION}")
    
    return parser.parse_args()


def create_settings_from_args(args: argparse.Namespace) -> BotSettings:
    """Argümanlardan BotSettings oluştur"""
    config: Dict[str, Any] = {}
    
    if args.config:
        config = load_config_file(args.config)
    
    channel = args.channel or config.get("channel")
    if not channel:
        channel = input(f"{Colors.CYAN}📺 Kanal adı: {Colors.END}").strip().lower()
        if not channel:
            raise SystemExit("❌ Kanal adı gerekli")
    
    if args.viewers is not None:
        viewers = args.viewers
    elif "viewers" in config:
        viewers = config["viewers"]
    else:
        viewers = int(input(f"{Colors.CYAN}🎯 Hedef izleyici sayısı: {Colors.END}").strip())
    
    viewers = max(1, min(MAX_VIEWERS_LIMIT, int(viewers)))
    
    def pick(key: str, default: Any = None) -> Any:
        arg_value = getattr(args, key, None)
        if arg_value is not None:
            return arg_value
        return config.get(key, default)
    
    def pick_range(key: str, default: Tuple[float, float]) -> Tuple[float, float]:
        arg_value = getattr(args, key, None)
        if arg_value and len(arg_value) == 2:
            low, high = float(arg_value[0]), float(arg_value[1])
            return (low, high) if low <= high else (high, low)
        
        config_value = config.get(key)
        if config_value and len(config_value) == 2:
            low, high = float(config_value[0]), float(config_value[1])
            return (low, high) if low <= high else (high, low)
        
        return default
    
    return BotSettings(
        channel=channel,
        viewer_goal=viewers,
        max_concurrent=pick("max_concurrent"),
        proxy_file=pick("proxy_file"),
        client_token=pick("client_token", DEFAULT_CLIENT_TOKEN),
        proxy_permits=pick("proxy_permits", 10),
        keepalive_range=pick_range("keepalive", (13.0, 21.0)),
        ping_period=pick("ping_period", 6),
        retry_delay_range=pick_range("retry_delay", (2.0, 6.0)),
        ramp_delay_range=pick_range("ramp_delay", (0.15, 0.75)),
        status_interval=pick("status_interval", 30.0),
        proxy_cooldown=pick("proxy_cooldown", 45.0),
        http_timeout=pick("http_timeout", 25),
        ws_timeout=pick("ws_timeout", 30),
        read_timeout=pick("read_timeout", 10.0),
        http_gate=pick("http_gate"),
        http_rps=pick("http_rps", 120.0),
        log_file=pick("log_file"),
        json_log=pick("json_log"),
        verbose=pick("verbose", False) and not args.quiet,
        auto_start=pick("auto_start", False),
        user_agent_file=pick("user_agent_file"),
        max_retries=pick("max_retries", 10)
    )


# ==================== ANA FONKSİYON ====================

async def async_main():
    """Asenkron ana fonksiyon"""
    args = parse_args()
    
    if args.quiet:
        args.verbose = False
    
    settings = create_settings_from_args(args)
    
    setup_logging(
        verbose=settings.verbose,
        log_file=settings.log_file,
        json_log=settings.json_log
    )
    
    bot = KickViewerBot(settings)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info(f"{Colors.YELLOW}⚠️ CTRL+C ile durduruldu{Colors.END}")
        await bot.stop()
    except Exception as e:
        logging.error(f"{Colors.RED}❌ Beklenmeyen hata: {e}{Colors.END}", exc_info=True)
        await bot.stop()


def main():
    """Ana giriş noktası"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Program sonlandırıldı.{Colors.END}")
    except SystemExit as e:
        print(f"{Colors.RED}❌ Hata: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
