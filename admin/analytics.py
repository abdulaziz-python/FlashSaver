import os
import asyncio
import aiosqlite
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Dict, Any
from io import BytesIO
from utils.constants import DB_PATH, TEMP_DIR
from utils.helpers import ensure_dir

class AnalyticsManager:
    def __init__(self):
        plt.style.use('dark_background')
    
    async def get_user_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM users WHERE date(join_date) = date("now")')
            new_today = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            active_users = (await cursor.fetchone())[0]
            
            return {
                'total': total_users,
                'new_today': new_today,
                'active': active_users
            }
    
    async def get_download_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM downloads')
            total_downloads = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM downloads WHERE status = "completed"')
            successful = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM downloads WHERE status = "failed"')
            failed = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(*) FROM downloads WHERE date(created_at) = date("now")')
            today = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT platform, COUNT(*) FROM downloads GROUP BY platform')
            platforms = dict(await cursor.fetchall())
            
            return {
                'total': total_downloads,
                'successful': successful,
                'failed': failed,
                'today': today,
                'platforms': platforms
            }
    
    async def generate_user_growth_chart(self) -> str:
        await ensure_dir(TEMP_DIR)
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT date(join_date) as day, COUNT(*) 
                FROM users 
                WHERE join_date >= date("now", "-30 days")
                GROUP BY day
                ORDER BY day
            ''')
            data = await cursor.fetchall()
        
        if not data:
            return None
        
        dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in data]
        counts = [row[1] for row in data]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, counts, marker='o', linewidth=2, markersize=6, color='#00ff88')
        plt.fill_between(dates, counts, alpha=0.3, color='#00ff88')
        
        plt.title('User Growth (Last 30 Days)', fontsize=16, color='white')
        plt.xlabel('Date', fontsize=12, color='white')
        plt.ylabel('New Users', fontsize=12, color='white')
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45, color='white')
        plt.yticks(color='white')
        
        plt.tight_layout()
        plt.grid(True, alpha=0.3)
        
        chart_path = os.path.join(TEMP_DIR, f"user_growth_{int(datetime.now().timestamp())}.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#2b2b2b')
        plt.close()
        
        return chart_path
    
    async def generate_download_stats_chart(self) -> str:
        await ensure_dir(TEMP_DIR)
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT date(created_at) as day, 
                       SUM(CASE WHEN status = "completed" THEN 1 ELSE 0 END) as successful,
                       SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
                FROM downloads 
                WHERE created_at >= date("now", "-30 days")
                GROUP BY day
                ORDER BY day
            ''')
            data = await cursor.fetchall()
        
        if not data:
            return None
        
        dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in data]
        successful = [row[1] for row in data]
        failed = [row[2] for row in data]
        
        plt.figure(figsize=(12, 6))
        
        plt.bar(dates, successful, label='Successful', color='#00ff88', alpha=0.8)
        plt.bar(dates, failed, bottom=successful, label='Failed', color='#ff4444', alpha=0.8)
        
        plt.title('Download Statistics (Last 30 Days)', fontsize=16, color='white')
        plt.xlabel('Date', fontsize=12, color='white')
        plt.ylabel('Downloads', fontsize=12, color='white')
        plt.legend()
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45, color='white')
        plt.yticks(color='white')
        
        plt.tight_layout()
        plt.grid(True, alpha=0.3)
        
        chart_path = os.path.join(TEMP_DIR, f"download_stats_{int(datetime.now().timestamp())}.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#2b2b2b')
        plt.close()
        
        return chart_path
    
    async def generate_platform_distribution_chart(self) -> str:
        await ensure_dir(TEMP_DIR)
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT platform, COUNT(*) FROM downloads GROUP BY platform')
            data = await cursor.fetchall()
        
        if not data:
            return None
        
        platforms = [row[0].title() for row in data]
        counts = [row[1] for row in data]
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7']
        
        plt.figure(figsize=(10, 8))
        wedges, texts, autotexts = plt.pie(counts, labels=platforms, colors=colors[:len(platforms)], 
                                          autopct='%1.1f%%', startangle=90)
        
        for text in texts:
            text.set_color('white')
            text.set_fontsize(12)
        
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
        
        plt.title('Downloads by Platform', fontsize=16, color='white', pad=20)
        
        chart_path = os.path.join(TEMP_DIR, f"platform_dist_{int(datetime.now().timestamp())}.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#2b2b2b')
        plt.close()
        
        return chart_path
    
    async def get_system_stats(self) -> Dict[str, Any]:
        import psutil
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        cpu = psutil.cpu_percent(interval=1)
        
        return {
            'memory_percent': memory.percent,
            'memory_available': memory.available,
            'disk_percent': disk.percent,
            'disk_free': disk.free,
            'cpu_percent': cpu
        }
