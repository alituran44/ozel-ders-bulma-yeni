# -*- coding: utf-8 -*-
"""
Apify Social Listening Scraper Modülü
=====================================
Apify platformu üzerinden Facebook Grupları ve Instagram'dan
özel ders taleplerini otomatik olarak tarayan async modül.

Kullanım:
    scraper = ApifyScraper()
    leads = await scraper.scrape(max_posts=30)

Konfigürasyon:
    - backend/auth/apify_config.json dosyasından api_token okunur
    - Alternatif: APIFY_API_TOKEN ortam değişkeni
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Logger yapılandırması
# ---------------------------------------------------------------------------
logger = logging.getLogger("apify_scraper")
logger.setLevel(logging.DEBUG)

# Konsol handler (henüz eklenmemişse)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Apify API temel URL'si
APIFY_BASE_URL = "https://api.apify.com/v2"

# Apify aktör kimlikleri
ACTOR_FACEBOOK_GROUPS = "apify/facebook-groups-scraper"
ACTOR_INSTAGRAM = "apify/instagram-scraper"

# Durum sorgulama aralığı (saniye)
POLL_INTERVAL_SECONDS = 10

# Maksimum bekleme süresi — bir run'ın tamamlanması için (saniye)
MAX_WAIT_SECONDS = 600  # 10 dakika

# Varsayılan Türkçe özel ders anahtar kelimeleri
DEFAULT_KEYWORDS: list[str] = [
    "özel ders arıyorum",
    "hoca arıyorum",
    "özel ders lazım",
    "matematik özel ders",
    "ingilizce hoca",
    "lgs özel ders",
    "yks özel ders",
    "kpss hoca",
    "ales özel ders",
    "çocuğuma özel ders",
    "öğretmen arıyorum",
]

# Varsayılan Facebook grup URL'leri
DEFAULT_FB_GROUPS: list[str] = [
    "https://www.facebook.com/groups/ozeldersarayanlar",
    "https://www.facebook.com/groups/lgsanneleri",
    "https://www.facebook.com/groups/ykshazirlananlar",
]

# Varsayılan Instagram hashtag'leri
DEFAULT_IG_HASHTAGS: list[str] = [
    "özelders",
    "hocaarıyorum",
    "özeldersarıyorum",
]

# Konfigürasyon dosya yolu (bu dosyaya göre göreli)
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "auth" / "apify_config.json"


# ---------------------------------------------------------------------------
# ApifyScraper Sınıfı
# ---------------------------------------------------------------------------
class ApifyScraper:
    """
    Apify platformu ile Facebook Grupları ve Instagram'dan
    özel ders lead'lerini toplayan async scraper.

    Akış:
        1. Aktörü çalıştır  (POST /acts/{actor}/runs)
        2. Durumu yokla       (GET  /actor-runs/{run_id})
        3. Veri setini indir  (GET  /datasets/{dataset_id}/items)
        4. Sonuçları standart lead formatına dönüştür
    """

    def __init__(self) -> None:
        """
        API token'ını yükler.

        Öncelik sırası:
            1. backend/auth/apify_config.json → api_token alanı
            2. APIFY_API_TOKEN ortam değişkeni
        """
        self._token: str = ""
        self._config: dict = {}

        # --- Konfigürasyon dosyasından oku ---
        if _CONFIG_PATH.exists():
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                    self._config = json.load(fh)
                    self._token = self._config.get("api_token", "").strip()
                    if self._token:
                        logger.info("API token apify_config.json dosyasından yüklendi.")
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("apify_config.json okunamadı: %s", exc)

        # --- Ortam değişkeninden yedek olarak oku ---
        if not self._token:
            env_token = os.getenv("APIFY_API_TOKEN", "").strip()
            if env_token:
                self._token = env_token
                logger.info("API token ortam değişkeninden (APIFY_API_TOKEN) yüklendi.")

        if not self._token:
            logger.warning(
                "Apify API token bulunamadı! "
                "apify_config.json dosyasına veya APIFY_API_TOKEN ortam değişkenine ekleyin."
            )

        # Konfigürasyondaki ekstra ayarlar
        self._fb_group_urls: list[str] = self._config.get(
            "facebook_group_urls", DEFAULT_FB_GROUPS
        )
        self._ig_hashtags: list[str] = self._config.get(
            "instagram_hashtags", DEFAULT_IG_HASHTAGS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """API token mevcut mu kontrol eder."""
        return bool(self._token)

    async def scrape(self, max_posts: int = 30) -> list[dict]:
        """
        Facebook Grupları ve Instagram taramalarını paralel çalıştırır,
        sonuçları birleştirerek döndürür.

        Args:
            max_posts: Her platform başına maksimum gönderi sayısı.

        Returns:
            Standart lead dict listesi.
        """
        if not self.is_configured():
            logger.error("Apify API token yapılandırılmamış, tarama atlanıyor.")
            return []

        logger.info(
            "🔍 Apify taraması başlatılıyor (max_posts=%d)…", max_posts
        )

        # Her iki platformu eş zamanlı başlat
        fb_task = asyncio.create_task(
            self.run_facebook_groups_scan(max_posts=max_posts)
        )
        ig_task = asyncio.create_task(
            self.run_instagram_scan(max_posts=max_posts)
        )

        fb_leads, ig_leads = await asyncio.gather(
            fb_task, ig_task, return_exceptions=True
        )

        # Hata kontrolü
        if isinstance(fb_leads, BaseException):
            logger.error("Facebook taraması başarısız: %s", fb_leads)
            fb_leads = []
        if isinstance(ig_leads, BaseException):
            logger.error("Instagram taraması başarısız: %s", ig_leads)
            ig_leads = []

        combined = fb_leads + ig_leads

        # Tekrar eden hash'leri ayıkla
        seen: set[str] = set()
        unique: list[dict] = []
        for lead in combined:
            h = lead.get("text_hash", "")
            if h and h not in seen:
                seen.add(h)
                unique.append(lead)

        logger.info(
            "✅ Apify taraması tamamlandı — FB: %d, IG: %d, toplam benzersiz: %d",
            len(fb_leads) if isinstance(fb_leads, list) else 0,
            len(ig_leads) if isinstance(ig_leads, list) else 0,
            len(unique),
        )
        return unique

    async def run_facebook_groups_scan(
        self,
        group_urls: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        max_posts: int = 50,
    ) -> list[dict]:
        """
        Apify Facebook Groups Scraper aktörünü çalıştırır.

        Args:
            group_urls: Taranacak Facebook grup URL'leri (None → varsayılan).
            keywords:   Filtreleme anahtar kelimeleri (None → varsayılan).
            max_posts:  Maksimum gönderi sayısı.

        Returns:
            Standart formatta lead listesi.
        """
        urls = group_urls or self._fb_group_urls
        kws = keywords or DEFAULT_KEYWORDS

        logger.info(
            "📘 Facebook Groups taraması: %d grup, %d anahtar kelime, max %d gönderi",
            len(urls),
            len(kws),
            max_posts,
        )

        # Apify aktörüne gönderilecek giriş verisi
        run_input = {
            "startUrls": [{"url": u} for u in urls],
            "maxPosts": max_posts,
            "maxPostComments": 0,
            "maxReviewComments": 0,
        }

        raw_items = await self._execute_actor(ACTOR_FACEBOOK_GROUPS, run_input)

        # Ham verileri standart lead formatına dönüştür
        leads = self._transform_facebook_items(raw_items, kws)
        logger.info("📘 Facebook: %d ham öğe → %d nitelikli lead", len(raw_items), len(leads))
        return leads

    async def run_instagram_scan(
        self,
        hashtags: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        max_posts: int = 30,
    ) -> list[dict]:
        """
        Apify Instagram Scraper aktörünü çalıştırır.

        Args:
            hashtags:   Taranacak hashtag'ler (None → varsayılan).
            keywords:   Filtreleme anahtar kelimeleri (None → varsayılan).
            max_posts:  Maksimum gönderi sayısı.

        Returns:
            Standart formatta lead listesi.
        """
        tags = hashtags or self._ig_hashtags
        kws = keywords or DEFAULT_KEYWORDS

        logger.info(
            "📸 Instagram taraması: %d hashtag, max %d gönderi",
            len(tags),
            max_posts,
        )

        # Apify aktörüne gönderilecek giriş verisi
        run_input = {
            "hashtags": tags,
            "resultsLimit": max_posts,
            "resultsType": "posts",
        }

        raw_items = await self._execute_actor(ACTOR_INSTAGRAM, run_input)

        leads = self._transform_instagram_items(raw_items, kws)
        logger.info("📸 Instagram: %d ham öğe → %d nitelikli lead", len(raw_items), len(leads))
        return leads

    # ------------------------------------------------------------------
    # Apify API İletişimi (Private)
    # ------------------------------------------------------------------

    async def _execute_actor(self, actor_id: str, run_input: dict) -> list[dict]:
        """
        Bir Apify aktörünü çalıştırıp tamamlanmasını bekler,
        ardından veri seti öğelerini döndürür.

        Adımlar:
            1. POST /acts/{actor_id}/runs  → run başlat
            2. GET  /actor-runs/{run_id}   → durum yokla (POLL)
            3. GET  /datasets/{dataset_id}/items → sonuçları al

        Args:
            actor_id:  Apify aktör kimliği (ör. "apify/facebook-groups-scraper").
            run_input: Aktöre gönderilecek girdi parametreleri.

        Returns:
            Veri seti öğeleri (dict listesi).

        Raises:
            RuntimeError: Aktör çalıştırma başarısız olursa.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:

            # ── 1. Aktörü başlat ──────────────────────────────────────
            start_url = (
                f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
                f"?token={self._token}"
            )
            logger.debug("Aktör başlatılıyor: %s", actor_id)

            try:
                resp = await client.post(
                    start_url,
                    json=run_input,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Aktör başlatma HTTP hatası (%s): %d — %s",
                    actor_id,
                    exc.response.status_code,
                    exc.response.text[:300],
                )
                raise RuntimeError(
                    f"Apify aktör başlatma başarısız: {exc.response.status_code}"
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Aktör başlatma bağlantı hatası (%s): %s", actor_id, exc)
                raise RuntimeError(
                    f"Apify bağlantı hatası: {exc}"
                ) from exc

            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            if not run_id:
                logger.error("Aktör çalıştırma yanıtında 'id' bulunamadı: %s", resp.text[:300])
                raise RuntimeError("Apify run ID alınamadı.")

            logger.info("Aktör çalışması başlatıldı — run_id: %s", run_id)

            # ── 2. Durum yoklama (polling) ────────────────────────────
            status_url = (
                f"{APIFY_BASE_URL}/actor-runs/{run_id}"
                f"?token={self._token}"
            )

            elapsed = 0
            status = "RUNNING"
            dataset_id: str = ""

            while elapsed < MAX_WAIT_SECONDS:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                elapsed += POLL_INTERVAL_SECONDS

                try:
                    poll_resp = await client.get(status_url)
                    poll_resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Durum sorgulama hatası (run=%s, geçen=%ds): %s",
                        run_id,
                        elapsed,
                        exc,
                    )
                    continue  # Geçici hatalarda yeniden dene

                poll_data = poll_resp.json().get("data", {})
                status = poll_data.get("status", "UNKNOWN")
                dataset_id = poll_data.get("defaultDatasetId", "")

                logger.debug(
                    "Yoklama — run_id: %s, durum: %s, geçen: %ds",
                    run_id,
                    status,
                    elapsed,
                )

                if status == "SUCCEEDED":
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    logger.error("Aktör çalışması başarısız oldu: %s (durum: %s)", run_id, status)
                    raise RuntimeError(
                        f"Apify run başarısız — durum: {status}, run_id: {run_id}"
                    )

            if status != "SUCCEEDED":
                logger.error(
                    "Aktör çalışması zaman aşımına uğradı (run=%s, %ds)",
                    run_id,
                    MAX_WAIT_SECONDS,
                )
                raise RuntimeError(
                    f"Apify run zaman aşımı ({MAX_WAIT_SECONDS}s): {run_id}"
                )

            # ── 3. Veri seti öğelerini al ─────────────────────────────
            if not dataset_id:
                logger.warning("Dataset ID boş, boş liste döndürülüyor.")
                return []

            items_url = (
                f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
                f"?token={self._token}"
            )

            try:
                items_resp = await client.get(items_url)
                items_resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Veri seti indirme hatası: %s", exc)
                return []

            items: list[dict] = items_resp.json()
            logger.info(
                "Veri seti indirildi — dataset: %s, öğe sayısı: %d",
                dataset_id,
                len(items),
            )
            return items

    # ------------------------------------------------------------------
    # Veri Dönüştürme (Private)
    # ------------------------------------------------------------------

    def _transform_facebook_items(
        self, items: list[dict], keywords: list[str]
    ) -> list[dict]:
        """
        Ham Apify Facebook verilerini projenin standart lead formatına dönüştürür.

        Yalnızca içeriğinde en az bir anahtar kelime geçen gönderiler alınır.
        """
        leads: list[dict] = []
        seen: set[str] = set()

        for item in items:
            # Gönderi metni — farklı alan adları olabilir
            text = (
                item.get("text")
                or item.get("message")
                or item.get("postText")
                or ""
            ).strip()

            if not text or len(text) < 10:
                continue

            # Anahtar kelime filtresi
            text_lower = text.lower()
            if not any(kw.lower() in text_lower for kw in keywords):
                continue

            content = text[:500]
            text_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

            if text_hash in seen:
                continue
            seen.add(text_hash)

            # Gönderi URL'si
            original_link = (
                item.get("url")
                or item.get("postUrl")
                or item.get("link")
                or ""
            )

            # Gönderi tarihi
            raw_date = item.get("time") or item.get("timestamp") or item.get("date")
            original_date = self._format_date(raw_date)

            leads.append(
                {
                    "id": str(uuid.uuid4()),
                    "platform": "Facebook Group (Apify)",
                    "content": content,
                    "subject": "Özel Ders",
                    "location": "Türkiye Geneli",
                    "original_link": original_link,
                    "original_date": original_date,
                    "text_hash": text_hash,
                    "is_qualified": 1,
                }
            )

        return leads

    def _transform_instagram_items(
        self, items: list[dict], keywords: list[str]
    ) -> list[dict]:
        """
        Ham Apify Instagram verilerini projenin standart lead formatına dönüştürür.

        Yalnızca caption'ında en az bir anahtar kelime geçen gönderiler alınır.
        """
        leads: list[dict] = []
        seen: set[str] = set()

        for item in items:
            # Instagram caption metni — farklı alan adları olabilir
            text = (
                item.get("caption")
                or item.get("text")
                or item.get("alt")
                or ""
            ).strip()

            if not text or len(text) < 10:
                continue

            # Anahtar kelime filtresi
            text_lower = text.lower()
            if not any(kw.lower() in text_lower for kw in keywords):
                continue

            content = text[:500]
            text_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

            if text_hash in seen:
                continue
            seen.add(text_hash)

            # Gönderi URL'si
            shortcode = item.get("shortCode") or item.get("shortcode") or ""
            original_link = (
                item.get("url")
                or item.get("postUrl")
                or (f"https://www.instagram.com/p/{shortcode}/" if shortcode else "")
            )

            # Gönderi tarihi
            raw_date = item.get("timestamp") or item.get("time") or item.get("date")
            original_date = self._format_date(raw_date)

            leads.append(
                {
                    "id": str(uuid.uuid4()),
                    "platform": "Instagram (Apify)",
                    "content": content,
                    "subject": "Özel Ders",
                    "location": "Türkiye Geneli",
                    "original_link": original_link,
                    "original_date": original_date,
                    "text_hash": text_hash,
                    "is_qualified": 1,
                }
            )

        return leads

    # ------------------------------------------------------------------
    # Yardımcı Metotlar (Private)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_date(raw: object) -> str:
        """
        Apify'den gelen farklı tarih formatlarını okunabilir stringe dönüştürür.
        Dönüştürülemezse "Anlık" döndürür.
        """
        if not raw:
            return "Anlık"

        # ISO-8601 string
        if isinstance(raw, str):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return raw[:30] if len(raw) > 30 else raw

        # Unix timestamp (saniye veya milisaniye)
        if isinstance(raw, (int, float)):
            try:
                # Milisaniye kontrolü
                ts = raw / 1000 if raw > 1e12 else raw
                dt = datetime.utcfromtimestamp(ts)
                return dt.strftime("%Y-%m-%d %H:%M")
            except (OSError, ValueError, OverflowError):
                return "Anlık"

        return "Anlık"


# ---------------------------------------------------------------------------
# Doğrudan çalıştırma (test amaçlı)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    async def _main() -> None:
        scraper = ApifyScraper()

        if not scraper.is_configured():
            print("⚠️  Apify API token yapılandırılmamış.")
            print(f"   Config dosyası: {_CONFIG_PATH}")
            print("   Lütfen api_token alanını doldurun veya APIFY_API_TOKEN ortam değişkenini ayarlayın.")
            return

        leads = await scraper.scrape(max_posts=10)
        print(f"\n{'='*60}")
        print(f"Toplam bulunan lead: {len(leads)}")
        print(f"{'='*60}")
        for i, lead in enumerate(leads, 1):
            print(f"\n--- Lead #{i} ---")
            print(json.dumps(lead, indent=2, ensure_ascii=False))

    asyncio.run(_main())
