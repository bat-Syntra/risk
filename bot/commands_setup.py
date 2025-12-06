"""
Commands and menu button setup for aiogram v3
- Global default commands (FR/EN)
- Per-chat commands update when user changes language
- Menu button configured to show commands list
"""
from __future__ import annotations

from typing import List
from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    MenuButtonCommands,
)


def get_commands(lang: str = "fr") -> List[BotCommand]:
    """Return bot commands for the specified language.

    Args:
        lang: "fr" or "en"
    """
    if lang == "en":
        return [
            BotCommand(command="menu", description="Menu"),
        ]
    # default FR
    return [
        BotCommand(command="menu", description="Menu"),
    ]


async def setup_bot_commands(bot: Bot) -> None:
    """Register default commands for FR and EN globally."""
    # Default FR
    await bot.set_my_commands(
        commands=get_commands("fr"),
        scope=BotCommandScopeDefault(),
        language_code="fr",
    )
    # Default EN
    await bot.set_my_commands(
        commands=get_commands("en"),
        scope=BotCommandScopeDefault(),
        language_code="en",
    )


async def set_user_commands(bot: Bot, chat_id: int, lang: str) -> None:
    """Set commands for a specific chat/user in chosen language."""
    await bot.set_my_commands(
        commands=get_commands(lang),
        scope=BotCommandScopeChat(chat_id=chat_id),
        language_code=lang,
    )


async def setup_menu_button(bot: Bot) -> None:
    """Configure the persistent menu button to open Commands.

    Note: Telegram clients typically show a generic label, not customizable text.
    This ensures the button opens the list of commands where /menu is present.
    """
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        print("✅ Menu button configured (commands)")
    except Exception as e:
        print(f"❌ Menu button error: {e}")
