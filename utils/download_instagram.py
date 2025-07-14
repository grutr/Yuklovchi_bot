import requests
import re
import os
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InstagramDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def extract_shortcode(self, url):
        """Instagram URL dan shortcode ni ajratib olish"""
        patterns = [
            r'instagram\.com/p/([A-Za-z0-9_-]+)',
            r'instagram\.com/reel/([A-Za-z0-9_-]+)',
            r'instagram\.com/tv/([A-Za-z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_media_info(self, url):
        """Instagram media ma'lumotlarini olish"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None

            # Instagram API endpointi
            api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1"

            response = requests.get(api_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data

        except Exception as e:
            logger.error(f"Instagram ma'lumotlarini olishda xatolik: {e}")

        return None

    def download_via_instaloader(self, url, temp_dir):
        """Instaloader orqali yuklab berish"""
        try:
            import instaloader

            L = instaloader.Instaloader(
                download_videos=True,
                download_video_thumbnails=False,
                download_comments=False,
                save_metadata=False,
                dirname_pattern=temp_dir
            )

            shortcode = self.extract_shortcode(url)
            if shortcode:
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=temp_dir)

                # Yuklab olingan faylni topish
                for file in os.listdir(temp_dir):
                    if file.endswith('.mp4'):
                        return os.path.join(temp_dir, file), post.caption or "Instagram Video"

        except Exception as e:
            logger.error(f"Instaloader orqali yuklab berish xatoligi: {e}")

        return None, None

    def download_via_yt_dlp(self, url, temp_dir):
        """yt-dlp orqali Instagram video yuklab berish"""
        try:
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
                title = info.get('title', 'Instagram Video')
                return filename, title

        except Exception as e:
            logger.error(f"yt-dlp orqali Instagram yuklab berish xatoligi: {e}")

        return None, None


# Asosiy funksiya
async def download_instagram_video(url, temp_dir):
    """Instagram video yuklab berish asosiy funksiyasi"""
    downloader = InstagramDownloader()

    # 1-usul: yt-dlp orqali
    try:
        filename, title = downloader.download_via_yt_dlp(url, temp_dir)
        if filename and os.path.exists(filename):
            return filename, title
    except Exception as e:
        logger.warning(f"yt-dlp orqali yuklab berish muvaffaqiyatsiz: {e}")

    # 2-usul: instaloader orqali
    try:
        filename, title = downloader.download_via_instaloader(url, temp_dir)
        if filename and os.path.exists(filename):
            return filename, title
    except Exception as e:
        logger.warning(f"Instaloader orqali yuklab berish muvaffaqiyatsiz: {e}")

    return None, None