"""
Automatic Database Backup System
Sends all .db files to admin every 2 weeks via Telegram
"""
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import logging
from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

class AutoBackupManager:
    """Manages automatic database backups"""
    
    def __init__(self, bot: Bot, admin_id: int):
        """
        Initialize backup manager
        
        Args:
            bot: Telegram bot instance
            admin_id: Admin's Telegram ID to send backups to
        """
        self.bot = bot
        self.admin_id = admin_id
        self.backup_interval = timedelta(weeks=2)  # 2 weeks
        self.last_backup_file = "last_backup.txt"
        self.running = False
        
    def get_last_backup_time(self) -> datetime:
        """Get the timestamp of last backup"""
        try:
            if os.path.exists(self.last_backup_file):
                with open(self.last_backup_file, 'r') as f:
                    timestamp = float(f.read().strip())
                    return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.warning(f"Could not read last backup time: {e}")
        
        # If no record, return epoch (force immediate backup)
        return datetime(2000, 1, 1)
    
    def save_last_backup_time(self):
        """Save current time as last backup timestamp"""
        try:
            with open(self.last_backup_file, 'w') as f:
                f.write(str(datetime.now().timestamp()))
        except Exception as e:
            logger.error(f"Could not save last backup time: {e}")
    
    async def find_all_db_files(self) -> list[str]:
        """
        Find all .db files in the project directory
        
        Returns:
            List of absolute paths to .db files
        """
        db_files = []
        project_root = Path(__file__).parent.parent
        
        # Search for .db files
        for db_file in project_root.glob("*.db"):
            if db_file.is_file():
                db_files.append(str(db_file.absolute()))
                logger.info(f"Found database: {db_file.name}")
        
        return db_files
    
    async def send_backup_to_admin(self):
        """Send all database files to admin"""
        try:
            logger.info("🗄️ Starting automatic backup process...")
            
            # Find all .db files
            db_files = await self.find_all_db_files()
            
            if not db_files:
                logger.warning("⚠️ No .db files found for backup!")
                await self.bot.send_message(
                    self.admin_id,
                    "⚠️ <b>BACKUP WARNING</b>\n\n"
                    "Automatic backup failed: No .db files found!",
                    parse_mode="HTML"
                )
                return
            
            # Send header message
            await self.bot.send_message(
                self.admin_id,
                f"🗄️ <b>AUTOMATIC DATABASE BACKUP</b>\n\n"
                f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📊 Databases found: {len(db_files)}\n\n"
                f"⬇️ Sending files...",
                parse_mode="HTML"
            )
            
            # Send each .db file (skip empty files)
            sent_count = 0
            skipped_empty = []
            
            for db_path in db_files:
                try:
                    file_name = os.path.basename(db_path)
                    file_size_bytes = os.path.getsize(db_path)
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    
                    # Skip empty files (Telegram doesn't accept them)
                    if file_size_bytes == 0:
                        logger.warning(f"⚠️ Skipping {file_name} (empty file - 0 bytes)")
                        skipped_empty.append(file_name)
                        continue
                    
                    logger.info(f"📤 Sending {file_name} ({file_size_mb:.2f} MB)...")
                    
                    # Send file via Telegram
                    document = FSInputFile(db_path)
                    await self.bot.send_document(
                        self.admin_id,
                        document=document,
                        caption=f"📊 <b>{file_name}</b>\n"
                                f"💾 Size: {file_size_mb:.2f} MB\n"
                                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        parse_mode="HTML"
                    )
                    
                    logger.info(f"✅ {file_name} sent successfully")
                    sent_count += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send {db_path}: {e}")
                    await self.bot.send_message(
                        self.admin_id,
                        f"❌ Failed to backup: {os.path.basename(db_path)}\n"
                        f"Error: {str(e)}",
                        parse_mode="HTML"
                    )
            
            # Success message
            success_msg = f"✅ <b>BACKUP COMPLETE</b>\n\n" \
                         f"📊 {sent_count} database(s) backed up successfully\n"
            
            if skipped_empty:
                success_msg += f"⚠️ Skipped {len(skipped_empty)} empty file(s):\n"
                for empty_file in skipped_empty:
                    success_msg += f"  • {empty_file}\n"
                success_msg += "\n"
            
            success_msg += f"⏭️ Next backup: {(datetime.now() + self.backup_interval).strftime('%Y-%m-%d')}"
            
            await self.bot.send_message(
                self.admin_id,
                success_msg,
                parse_mode="HTML"
            )
            
            # Save timestamp
            self.save_last_backup_time()
            logger.info("✅ Automatic backup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Backup process failed: {e}")
            try:
                await self.bot.send_message(
                    self.admin_id,
                    f"❌ <b>BACKUP FAILED</b>\n\n"
                    f"Error: {str(e)}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    
    def is_backup_ready(self) -> bool:
        """Check if backup is ready (2 weeks passed since last backup)"""
        last_backup = self.get_last_backup_time()
        time_since_backup = datetime.now() - last_backup
        return time_since_backup >= self.backup_interval
    
    def days_until_next_backup(self) -> int:
        """Get number of days until next backup is ready"""
        last_backup = self.get_last_backup_time()
        time_since_backup = datetime.now() - last_backup
        if time_since_backup >= self.backup_interval:
            return 0
        days_remaining = (self.backup_interval - time_since_backup).days
        return max(0, days_remaining)
    
    async def backup_loop(self):
        """Main backup loop - checks every 24 hours and notifies admin when ready"""
        self.running = True
        logger.info("🗄️ Auto-backup system started (checks every 24h, notifies after 2 weeks)")
        
        # Startup notification removed - no spam at each restart
        
        backup_ready_notified = False
        
        while self.running:
            try:
                # Check if backup is ready
                if self.is_backup_ready():
                    if not backup_ready_notified:
                        logger.info(f"⏰ Backup is ready! Notifying admin...")
                        try:
                            await self.bot.send_message(
                                self.admin_id,
                                "🔔 <b>BACKUP READY!</b>\n\n"
                                "✅ 2 weeks have passed since last backup\n"
                                "📊 Click 'Admin' button to receive all database files\n"
                                "💡 Or use /backup command",
                                parse_mode="HTML"
                            )
                            backup_ready_notified = True
                        except Exception as e:
                            logger.warning(f"Could not send backup ready notification: {e}")
                else:
                    backup_ready_notified = False
                    days_until_next = self.days_until_next_backup()
                    logger.info(f"✅ Backup up to date. Next backup in {days_until_next} days")
                
                # Wait 24 hours before next check
                await asyncio.sleep(24 * 60 * 60)
                
            except asyncio.CancelledError:
                logger.info("🛑 Auto-backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(60 * 60)
    
    def stop(self):
        """Stop the backup loop"""
        self.running = False
        logger.info("🛑 Auto-backup system stopped")


async def manual_backup_now(bot: Bot, admin_id: int):
    """
    Trigger an immediate backup (for testing or manual trigger)
    
    Args:
        bot: Telegram bot instance
        admin_id: Admin's Telegram ID
    """
    manager = AutoBackupManager(bot, admin_id)
    await manager.send_backup_to_admin()
