import os
import asyncio
import yt_dlp
from typing import Dict, Any, Callable, Optional
from utils.constants import TEMP_DIR, Platform, Quality, MediaInfo
from utils.helpers import sanitize_filename, ensure_dir, get_file_size
import logging

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.semaphore = asyncio.Semaphore(3)
    
    async def get_video_info(self, url: str) -> MediaInfo:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                platform = Platform.YOUTUBE if 'youtube' in url else Platform.INSTAGRAM
                
                quality_options = {}
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('height'):
                            key = f"{fmt['height']}p"
                            quality_options[key] = {
                                'format_id': fmt['format_id'],
                                'filesize': fmt.get('filesize', 0)
                            }
                
                return MediaInfo(
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    quality_options=quality_options,
                    file_size=info.get('filesize', 0) or 0,
                    platform=platform
                )
            except Exception as e:
                logger.error(f"Error extracting info: {e}")
                raise
    
    async def download_video(
        self, 
        url: str, 
        quality: Quality = Quality.BEST,
        progress_callback: Optional[Callable] = None
    ) -> str:
        await ensure_dir(TEMP_DIR)
        
        filename = sanitize_filename(f"video_{hash(url)}")
        output_path = os.path.join(TEMP_DIR, f"{filename}.%(ext)s")
        
        format_selector = self._get_format_selector(quality)
        
        opts = {
            'outtmpl': output_path,
            'format': format_selector,
            'noplaylist': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'quiet': True,
            'no_warnings': True,
            'extractaudio': quality == Quality.AUDIO,
            'audioformat': 'mp3' if quality == Quality.AUDIO else None,
            'ignoreerrors': True,
            'retries': 3,
            'fragment_retries': 3,
            'no_part': True,  # Avoid .part files
            'keepvideo': False,  # Remove video after audio extraction
            'prefer_ffmpeg': True,  # Use ffmpeg for better compatibility
        }
        
        if progress_callback:
            opts['progress_hooks'] = [self._progress_hook(progress_callback)]
        
        async with self.semaphore:
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    await asyncio.to_thread(ydl.download, [url])
                    
                    downloaded_files = []
                    for f in os.listdir(TEMP_DIR):
                        if f.startswith(filename) and not f.endswith('.part'):
                            downloaded_files.append(os.path.join(TEMP_DIR, f))
                    
                    if downloaded_files:
                        final_file = downloaded_files[0]
                        
                        # Auto-compress if video is larger than 20MB and not audio
                        if quality != Quality.AUDIO and final_file.endswith(('.mp4', '.avi', '.mkv', '.mov')):
                            file_size = await get_file_size(final_file)
                            if file_size > 20 * 1024 * 1024:  # 20MB
                                logger.info(f"File size {file_size} bytes, compressing...")
                                compressed_file = await self.compress_video(final_file, 19, True)
                                if compressed_file != final_file:
                                    # Remove original file if compression was successful
                                    try:
                                        os.remove(final_file)
                                    except:
                                        pass
                                    final_file = compressed_file
                        
                        return final_file
                    else:
                        raise Exception("Download completed but file not found")
                        
                except Exception as e:
                    logger.error(f"Download error: {e}")
                    raise
    
    def _get_format_selector(self, quality: Quality) -> str:
        if quality == Quality.AUDIO:
            return 'bestaudio[ext=m4a]/bestaudio/best'
        elif quality == Quality.LOW:
            return 'best[height<=360]/best[height<=480]/best'
        elif quality == Quality.MEDIUM:
            return 'best[height<=480]/best[height<=720]/best'
        elif quality == Quality.HIGH:
            return 'best[height<=720]/best[height<=1080]/best'
        else:
            return 'best'
    
    def _progress_hook(self, callback: Callable):
        def hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and 'downloaded_bytes' in d:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(callback(progress))
                    except RuntimeError:
                        # No event loop running, ignore the progress update
                        pass
        return hook
    
    async def compress_video(self, input_path: str, target_size_mb: int = 20, preserve_resolution: bool = True) -> str:
        if not await self._check_ffmpeg():
            logger.warning("FFmpeg not available, skipping compression")
            return input_path
            
        output_path = input_path.replace('.', '_compressed.')
        
        try:
            file_size = await get_file_size(input_path)
            target_size_bytes = target_size_mb * 1024 * 1024
            
            if file_size <= target_size_bytes:
                return input_path
            
            info_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', input_path
            ]
            
            try:
                info_process = await asyncio.create_subprocess_exec(
                    *info_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await info_process.communicate()
                
                if info_process.returncode != 0:
                    logger.warning(f"FFprobe failed: {stderr.decode()}")
                    return input_path
                
                import json
                info = json.loads(stdout.decode())
                duration = float(info['format']['duration'])
                
                target_bitrate = int((target_size_bytes * 8 * 0.9) / duration)
                
                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-c:v', 'libx264',
                    '-b:v', f'{target_bitrate}',
                    '-maxrate', f'{int(target_bitrate * 1.2)}',
                    '-bufsize', f'{int(target_bitrate * 2)}',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-preset', 'medium',
                    '-crf', '28' if preserve_resolution else '32',
                    '-movflags', '+faststart',
                    '-avoid_negative_ts', 'make_zero',
                    '-y', output_path
                ]
                
                if not preserve_resolution:
                    cmd.extend(['-vf', 'scale=iw*min(720/iw\\,480/ih):ih*min(720/iw\\,480/ih)'])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.exists(output_path):
                    compressed_size = await get_file_size(output_path)
                    if compressed_size < file_size:
                        logger.info(f"Compression successful: {file_size} -> {compressed_size} bytes")
                        return output_path
                else:
                    logger.warning(f"FFmpeg compression failed: {stderr.decode() if stderr else 'Unknown error'}")
                
            except Exception as e:
                logger.warning(f"Compression process failed: {e}")
            
            return input_path
                
        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return input_path
    
    async def _check_ffmpeg(self) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False
