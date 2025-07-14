import requests
import re
import os
import tempfile
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class TikTokDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def extract_video_id(self, url):
        """TikTok URL dan video ID ni ajratib olish"""
        patterns = [
            r'tiktok\.com/@[\w\.-]+/video/(\d+)',
            r'tiktok\.com/t/(\w+)',
            r'vm\.tiktok\.com/(\w+)',
            r'tiktok\.com/.*?/(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, url):
        """TikTok video ma'lumotlarini olish"""
        try:
            # TikTok API yoki web scraping orqali
            # Bu yerda oddiy example
            video_id = self.extract_video_id(url)
            if not video_id:
                return None

            # API so'rovi (bu yerda example API)
            api_url = f"https://api.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}"

            response = requests.get(api_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data

        except Exception as e:
            logger.error(f"TikTok ma'lumotlarini olishda xatolik: {e}")

        return None

    def download_video(self, url, temp_dir):
        """TikTok videoni yuklab berish"""
        try:
            # Bu yerda real TikTok API yoki sniffer ishlatiladi
            # Hozircha placeholder

            # Alternative: yt-dlp orqali
            import yt_dlp

            ydl_opts = {
                'format': 'best[filesize<50M]/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'ignoreerrors': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'TikTok Video')
                return filename, title

        except Exception as e:
            logger.error(f"TikTok yuklab berish xatoligi: {e}")
            return None, None

    def get_video_url_via_api(self, tiktok_url):
        """External API orqali TikTok video URL olish"""
        try:
            # Sniffer API example
            api_endpoints = [
                "https://api.ssstik.io/",
                "https://api.tikmate.online/",
                "https://api.ttsave.app/"
            ]

            for api_url in api_endpoints:
                try:
                    payload = {
                        'url': tiktok_url,
                        'hd': 1
                    }

                    response = requests.post(api_url, data=payload, headers=self.headers, timeout=15)

                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            return data.get('download_url')

                except Exception as e:
                    logger.warning(f"API {api_url} bilan muammo: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"TikTok API orqali yuklab berish xatoligi: {e}")
            return None

    def download_from_direct_url(self, video_url, temp_dir, filename="tiktok_video.mp4"):
        """To'g'ridan-to'g'ri URL dan video yuklab berish"""
        try:
            response = requests.get(video_url, headers=self.headers, stream=True, timeout=30)

            if response.status_code == 200:
                filepath = os.path.join(temp_dir, filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                return filepath

        except Exception as e:
            logger.error(f"To'g'ridan-to'g'ri yuklab berish xatoligi: {e}")

        return None


# Asosiy funksiya
async def download_tiktok_video(url, temp_dir):
    """TikTok video yuklab berish asosiy funksiyasi"""
    downloader = TikTokDownloader()

    # 1-usul: yt-dlp orqali
    try:
        filename, title = downloader.download_video(url, temp_dir)
        if filename and os.path.exists(filename):
            return filename, title
    except Exception as e:
        logger.warning(f"yt-dlp orqali yuklab berish muvaffaqiyatsiz: {e}")

    # 2-usul: API orqali
    try:
        video_url = downloader.get_video_url_via_api(url)
        if video_url:
            filename = downloader.download_from_direct_url(video_url, temp_dir)
            if filename:
                return filename, "TikTok Video"
    except Exception as e:
        logger.warning(f"API orqali yuklab berish muvaffaqiyatsiz: {e}")

    return None, None