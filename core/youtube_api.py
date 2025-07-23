import re
import asyncio
import aiohttp
from typing import Dict, Optional, List, Any
from googleapiclient.discovery import build
from utils.constants import YOUTUBE_API_KEY
import logging

logger = logging.getLogger(__name__)

class YouTubeAPI:
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.youtube = build('youtube', 'v3', developerKey=self.api_key) if self.api_key else None
    
    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/shorts\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def extract_playlist_id(self, url: str) -> Optional[str]:
        match = re.search(r'list=([^&\n?#]+)', url)
        return match.group(1) if match else None
    
    async def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        if not self.youtube:
            return None
            
        try:
            loop = asyncio.get_event_loop()
            request = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            )
            
            response = await loop.run_in_executor(None, request.execute)
            
            if response['items']:
                item = response['items'][0]
                snippet = item['snippet']
                statistics = item['statistics']
                content_details = item['contentDetails']
                
                duration_str = content_details['duration']
                duration_seconds = self._parse_duration(duration_str)
                
                return {
                    'title': snippet['title'],
                    'description': snippet['description'][:500] + '...' if len(snippet['description']) > 500 else snippet['description'],
                    'channel': snippet['channelTitle'],
                    'published': snippet['publishedAt'][:10],
                    'duration': duration_seconds,
                    'views': int(statistics.get('viewCount', 0)),
                    'likes': int(statistics.get('likeCount', 0)),
                    'thumbnails': {
                        'default': snippet['thumbnails'].get('default', {}).get('url'),
                        'medium': snippet['thumbnails'].get('medium', {}).get('url'),
                        'high': snippet['thumbnails'].get('high', {}).get('url'),
                        'maxres': snippet['thumbnails'].get('maxres', {}).get('url')
                    }
                }
        except Exception as e:
            logger.error(f"YouTube API error: {e}")
        
        return None
    
    async def get_playlist_info(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        if not self.youtube:
            return None
            
        try:
            loop = asyncio.get_event_loop()
            
            playlist_request = self.youtube.playlists().list(
                part='snippet,contentDetails',
                id=playlist_id
            )
            
            playlist_response = await loop.run_in_executor(None, playlist_request.execute)
            
            if not playlist_response['items']:
                return None
                
            playlist_info = playlist_response['items'][0]
            
            items_request = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50
            )
            
            items_response = await loop.run_in_executor(None, items_request.execute)
            
            videos = []
            for item in items_response['items']:
                videos.append({
                    'video_id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title'],
                    'thumbnail': item['snippet']['thumbnails'].get('medium', {}).get('url')
                })
            
            return {
                'title': playlist_info['snippet']['title'],
                'description': playlist_info['snippet']['description'][:300] + '...' if len(playlist_info['snippet']['description']) > 300 else playlist_info['snippet']['description'],
                'channel': playlist_info['snippet']['channelTitle'],
                'video_count': playlist_info['contentDetails']['itemCount'],
                'videos': videos,
                'thumbnail': playlist_info['snippet']['thumbnails'].get('medium', {}).get('url')
            }
            
        except Exception as e:
            logger.error(f"YouTube API playlist error: {e}")
        
        return None
    
    async def download_thumbnail(self, url: str, save_path: str) -> bool:
        if not url:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        return True
        except Exception as e:
            logger.error(f"Thumbnail download error: {e}")
        
        return False
    
    def _parse_duration(self, duration: str) -> int:
        import re
        
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0) 
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def format_number(self, num: int) -> str:
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)
