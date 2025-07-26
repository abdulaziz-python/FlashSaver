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
        self.semaphore = asyncio.Semaphore(5)

    async def get_video_info(self, url: str) -> MediaInfo:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'no_check_certificate': True,
            'socket_timeout': 15,
            'retries': 2,
            'youtube_include_dash_manifest': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'concurrent_fragment_downloads': 8
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)

                platform = Platform.YOUTUBE if any(x in url.lower() for x in ['youtube.com', 'youtu.be']) else Platform.INSTAGRAM

                quality_options = {}
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('height') and fmt.get('vcodec') != 'none':
                            key = f"{fmt['height']}p"
                            quality_options[key] = {
                                'format_id': fmt['format_id'],
                                'filesize': fmt.get('filesize', 0) or fmt.get('filesize_approx', 0) or 0
                            }

                return MediaInfo(
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    quality_options=quality_options,
                    file_size=info.get('filesize', 0) or info.get('filesize_approx', 0) or 0,
                    platform=platform
                )
            except Exception as e:
                logger.error(f"Error extracting info from {url}: {e}")
                raise Exception(f"Failed to extract video info: {str(e)}")

    async def download_video(
        self,
        url: str,
        quality: Quality = Quality.BEST,
        progress_callback: Optional[Callable] = None
    ) -> str:
        await ensure_dir(TEMP_DIR)

        url_hash = abs(hash(url))
        filename = sanitize_filename(f"video_{url_hash}_{int(asyncio.get_event_loop().time())}")
        output_path = os.path.join(TEMP_DIR, f"{filename}.%(ext)s")

        format_selector = self._get_format_selector(quality, url)

        opts = {
            'outtmpl': output_path,
            'format': format_selector,
            'noplaylist': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'quiet': True,
            'no_warnings': True,
            'extractaudio': quality == Quality.AUDIO,
            'audioformat': 'mp3' if quality == Quality.AUDIO else None,
            'ignoreerrors': False,
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'no_part': False,
            'keepvideo': False,
            'prefer_ffmpeg': True,
            'socket_timeout': 30,
            'no_check_certificate': True,
            'youtube_include_dash_manifest': False,
            'extract_flat': False,
            'concurrent_fragment_downloads': 8,
            'buffersize': 16384
        }

        if any(x in url.lower() for x in ['youtube.com', 'youtu.be']):
            opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            })

        if progress_callback:
            opts['progress_hooks'] = [self._progress_hook(progress_callback)]

        async with self.semaphore:
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    logger.info(f"Starting download: {url} with quality: {quality.value}")
                    await asyncio.to_thread(ydl.download, [url])

                    downloaded_files = []
                    for f in os.listdir(TEMP_DIR):
                        if f.startswith(filename.split('.')[0]) and not f.endswith('.part'):
                            downloaded_files.append(os.path.join(TEMP_DIR, f))

                    if not downloaded_files:
                        raise Exception("Download completed but no file found")

                    final_file = max(downloaded_files, key=os.path.getctime)
                    logger.info(f"Downloaded file: {final_file}")

                    if quality != Quality.AUDIO and final_file.endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm')):
                        file_size = await get_file_size(final_file)
                        if file_size > 20 * 1024 * 1024:
                            logger.info(f"File size {file_size} bytes, compressing...")
                            compressed_file = await self.compress_video(final_file, 19, True)
                            if compressed_file != final_file:
                                try:
                                    os.remove(final_file)
                                    logger.info("Original file removed after compression")
                                except Exception as e:
                                    logger.warning(f"Failed to remove original file: {e}")
                                final_file = compressed_file

                    return final_file

                except Exception as e:
                    logger.error(f"Download error for {url}: {e}")
                    try:
                        for f in os.listdir(TEMP_DIR):
                            if f.startswith(filename.split('.')[0]):
                                os.remove(os.path.join(TEMP_DIR, f))
                    except:
                        pass
                    raise Exception(f"Download failed: {str(e)}")

    def _get_format_selector(self, quality: Quality, url: str) -> str:
        if any(x in url.lower() for x in ['youtube.com', 'youtu.be']):
            if quality == Quality.AUDIO:
                return 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best[height<=360]'
            elif quality == Quality.LOW:
                return 'best[height<=360][ext=mp4]/best[height<=360]/worst[ext=mp4]/worst'
            elif quality == Quality.MEDIUM:
                return 'best[height<=480][ext=mp4]/best[height<=480]/best[height<=720][ext=mp4]/best[height<=720]'
            elif quality == Quality.HIGH:
                return 'best[height<=720][ext=mp4]/best[height<=720]/best[height<=1080][ext=mp4]/best[height<=1080]'
            else:
                return 'best[height<=1080][ext=mp4]/best[ext=mp4]/best'
        else:
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
                elif '_total_bytes_estimate' in d and 'downloaded_bytes' in d:
                    progress = (d['downloaded_bytes'] / d['_total_bytes_estimate']) * 100
                elif '_percent_str' in d:
                    try:
                        progress = float(d['_percent_str'].replace('%', ''))
                    except:
                        progress = 0
                else:
                    progress = 0

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(callback(min(progress, 100)))
                except RuntimeError:
                    pass
            elif d['status'] == 'error':
                logger.error(f"Download hook error: {d.get('error', 'Unknown error')}")
        return hook

    async def compress_video(self, input_path: str, target_size_mb: int = 19, preserve_resolution: bool = True) -> str:
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

                stdout, stderr = await asyncio.wait_for(info_process.communicate(), timeout=15)

                if info_process.returncode != 0:
                    logger.warning(f"FFprobe failed: {stderr.decode()}")
                    return input_path

                import json
                info = json.loads(stdout.decode())
                duration = float(info['format']['duration'])

                target_bitrate = int((target_size_bytes * 8 * 0.8) / duration)

                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-c:v', 'libx264',
                    '-b:v', f'{target_bitrate}',
                    '-maxrate', f'{int(target_bitrate * 1.1)}',
                    '-bufsize', f'{int(target_bitrate * 1.5)}',
                    '-c:a', 'aac',
                    '-b:a', '80k',
                    '-preset', 'ultrafast',
                    '-crf', '24' if preserve_resolution else '28',
                    '-movflags', '+faststart',
                    '-avoid_negative_ts', 'make_zero',
                    '-threads', '0',
                    '-y', output_path
                ]

                if not preserve_resolution:
                    cmd.extend(['-vf', 'scale=640:480'])

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

                if process.returncode == 0 and os.path.exists(output_path):
                    compressed_size = await get_file_size(output_path)
                    if compressed_size < file_size and compressed_size > 0:
                        logger.info(f"Compression successful: {file_size} -> {compressed_size} bytes")
                        return output_path
                    else:
                        if os.path.exists(output_path):
                            os.remove(output_path)
                else:
                    logger.warning(f"FFmpeg compression failed: {stderr.decode() if stderr else 'Unknown error'}")

            except asyncio.TimeoutError:
                logger.warning("Compression timeout")
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
            await asyncio.wait_for(process.communicate(), timeout=10)
            return process.returncode == 0
        except:
            return False
