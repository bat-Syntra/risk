"""
Test Middle Bet Push
Simule l'envoi d'un middle bet pour tester le système
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Import bot
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Import utilities
from utils.middle_calculator import classify_middle_type, describe_middle_zone, get_recommendation
from core.casinos import get_casino_logo
from bot.middle_handlers import store_middle, build_middle_keyboard, format_middle_message_with_calc

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

bot = Bot(token=BOT_TOKEN)


def format_middle_safe_test(data: dict, calc: dict, user_cash: float) -> str:
    """Format middle safe message pour test"""
    
    total_stake = calc['total_stake']
    min_profit = min(calc['profit_scenario_1'], calc['profit_scenario_3'])
    middle_profit = calc['profit_scenario_2']
    
    emoji_a = get_casino_logo(data['side_a']['bookmaker'])
    emoji_b = get_casino_logo(data['side_b']['bookmaker'])
    
    player_line = f"👤 {data.get('player', '')} - {data.get('market', '')}\n" if data.get('player') else ""
    
    message = f"""✅🎰 <b>MIDDLE SAFE - PROFIT GARANTI + JACKPOT!</b> 🎰✅

🏈 <b>{data['team1']} vs {data['team2']}</b>
📊 {data['league']}
{player_line}🕐 {data.get('time', 'Today')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>CONFIGURATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji_a} <b>[{data['side_a']['bookmaker']}]</b> {data['side_a']['selection']}
💵 Mise: <b>${calc['stake_a']:.2f}</b> ({data['side_a']['odds']})
📈 Retour: ${calc['return_a']:.2f}

{emoji_b} <b>[{data['side_b']['bookmaker']}]</b> {data['side_b']['selection']}
💵 Mise: <b>${calc['stake_b']:.2f}</b> ({data['side_b']['odds']})
📈 Retour: ${calc['return_b']:.2f}

💰 <b>Total: ${total_stake:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>SCÉNARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>1. {data['side_a']['selection']} hits seul</b>
✅ Profit: <b>${calc['profit_scenario_1']:.2f}</b> ({calc['profit_scenario_1']/total_stake*100:.1f}%)

<b>2. MIDDLE HIT! 🎰</b>
🚀 <b>Zone magique: {describe_middle_zone(data)}</b>
🚀 <b>LES DEUX PARIS GAGNENT!</b>
💰 <b>Profit: ${middle_profit:.2f}</b> ({middle_profit/total_stake*100:.0f}% ROI!)

<b>3. {data['side_b']['selection']} hits seul</b>
✅ Profit: <b>${calc['profit_scenario_3']:.2f}</b> ({calc['profit_scenario_3']/total_stake*100:.1f}%)

💡 <b>Zone middle:</b> {describe_middle_zone(data)}
📊 <b>Gap:</b> {calc['middle_zone']} reception(s) ({"tight - excellent!" if calc['middle_zone'] <= 1 else "bon!"})
🎲 <b>Probabilité middle:</b> ~{calc['middle_prob']*100:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>POURQUOI C'EST INCROYABLE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Profit MINIMUM garanti:</b> ${min_profit:.2f}
🛡️ <b>Risque:</b> ZÉRO (arbitrage!)
🎰 <b>Chance jackpot:</b> ~{calc['middle_prob']*100:.0f}%
🚀 <b>Jackpot si hit:</b> ${middle_profit:.2f} ({middle_profit/min_profit:.0f}x profit min!)

<b>C'est le BET PARFAIT:</b>
• Profit garanti dans TOUS les scénarios
• + Chance de jackpot {calc['middle_prob']*100:.0f}%
• + Gap de {calc['middle_zone']} = {"excellente" if calc['middle_zone'] <= 1 else "bonne"} prob middle!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>SIMULATION 10 BETS IDENTIQUES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• {int((1-calc['middle_prob'])*5)} fois Scénario 1: +${calc['profit_scenario_1']:.2f} = ${calc['profit_scenario_1'] * (1-calc['middle_prob'])*5:.2f}
• {int(calc['middle_prob']*10)} fois Middle hits: +${middle_profit:.2f} = ${middle_profit * calc['middle_prob']*10:.2f}
• {int((1-calc['middle_prob'])*5)} fois Scénario 3: +${calc['profit_scenario_3']:.2f} = ${calc['profit_scenario_3'] * (1-calc['middle_prob'])*5:.2f}
• <b>TOTAL: ${(calc['profit_scenario_1'] * (1-calc['middle_prob'])*5) + (middle_profit * calc['middle_prob']*10) + (calc['profit_scenario_3'] * (1-calc['middle_prob'])*5):.2f} profit!</b> 🤑

Profit moyen/bet: ${((calc['profit_scenario_1'] + calc['profit_scenario_3'])/2 * (1-calc['middle_prob']) + middle_profit * calc['middle_prob']):.2f} ({((calc['profit_scenario_1'] + calc['profit_scenario_3'])/2 * (1-calc['middle_prob']) + middle_profit * calc['middle_prob'])/total_stake*100:.0f}% ROI!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>{get_recommendation(calc['middle_zone'])}</b> ⚡

⏰ <b>Cotes peuvent changer - vérifie avant de miser!</b>"""

    return message


async def test_middle_safe():
    """Test avec middle safe (Chase Brown example)"""
    
    # Example data
    middle_data = {
        'team1': 'New England Patriots',
        'team2': 'Cincinnati Bengals',
        'league': 'NFL',
        'market': 'Player Receptions',
        'player': 'Chase Brown',
        'time': 'Today, 1:00PM',
        'side_a': {
            'bookmaker': 'Mise-o-jeu',
            'selection': 'Over 3.5',
            'line': '3.5',
            'odds': '-105',
            'market': 'Player Receptions'
        },
        'side_b': {
            'bookmaker': 'Coolbet',
            'selection': 'Under 4.5',
            'line': '4.5',
            'odds': '+120',
            'market': 'Player Receptions'
        }
    }
    
    user_cash = 500.0
    
    # Calculate
    print("🔄 Calculating middle...")
    calc = classify_middle_type(
        middle_data['side_a'],
        middle_data['side_b'],
        user_cash
    )
    
    print(f"✅ Type: {calc['type']}")
    print(f"✅ EV: {calc['ev_percent']}%")
    print(f"✅ Stakes: ${calc['stake_a']:.2f} / ${calc['stake_b']:.2f}")
    print(f"✅ Profits: ${calc['profit_scenario_1']:.2f} / ${calc['profit_scenario_2']:.2f} / ${calc['profit_scenario_3']:.2f}")
    
    # Format message
    print("\n🔄 Formatting message...")
    message = format_middle_safe_test(middle_data, calc, user_cash)
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{get_casino_logo('Mise-o-jeu')} Mise-o-jeu",
                url="https://www.mise-o-jeu.com"
            ),
            InlineKeyboardButton(
                text=f"{get_casino_logo('Coolbet')} Coolbet",
                url="https://www.coolbet.com"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💰 I BET (${calc['profit_scenario_1']:.2f} to ${calc['profit_scenario_2']:.2f})",
                callback_data="middle_test"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Send to admin
    print(f"\n📤 Sending to Telegram (chat_id: {ADMIN_CHAT_ID})...")
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print("✅ Message sent successfully!")
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        print("\n📝 Message preview:")
        print(message)
    
    finally:
        await bot.session.close()


async def test_middle_risky():
    """Test avec middle risqué (LeBron example)"""
    
    # Example data
    middle_data = {
        'team1': 'Lakers',
        'team2': 'Warriors',
        'league': 'NBA',
        'market': 'Player Points',
        'player': 'LeBron James',
        'time': 'Tonight, 7:00PM',
        'side_a': {
            'bookmaker': 'BET99',
            'selection': 'Over 20.5',
            'line': '20.5',
            'odds': '-118',
            'market': 'Player Points'
        },
        'side_b': {
            'bookmaker': 'Coolbet',
            'selection': 'Under 22.5',
            'line': '22.5',
            'odds': '+114',
            'market': 'Player Points'
        }
    }
    
    user_cash = 500.0
    
    # Calculate
    print("🔄 Calculating middle...")
    calc = classify_middle_type(
        middle_data['side_a'],
        middle_data['side_b'],
        user_cash
    )
    
    print(f"✅ Type: {calc['type']}")
    print(f"✅ EV: {calc['ev_percent']}%")
    print(f"✅ Stakes: ${calc['stake_a']:.2f} / ${calc['stake_b']:.2f}")
    print(f"✅ Profits: ${calc['profit_scenario_1']:.2f} / ${calc['profit_scenario_2']:.2f} / ${calc['profit_scenario_3']:.2f}")
    
    # For risky, format simplified message
    worst_loss = min(calc['profit_scenario_1'], calc['profit_scenario_3'])
    
    message = f"""🎯 <b>MIDDLE RISQUÉ - {calc['ev_percent']:.1f}% EV</b> 🎯

🏀 <b>{middle_data['team1']} vs {middle_data['team2']}</b>
📊 {middle_data['league']} - {middle_data['market']}
👤 {middle_data['player']}
🕐 {middle_data['time']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>CONFIGURATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{get_casino_logo('BET99')} <b>[BET99]</b> {middle_data['side_a']['selection']}
💵 Mise: <b>${calc['stake_a']:.2f}</b> ({middle_data['side_a']['odds']})

{get_casino_logo('Coolbet')} <b>[Coolbet]</b> {middle_data['side_b']['selection']}
💵 Mise: <b>${calc['stake_b']:.2f}</b> ({middle_data['side_b']['odds']})

💰 <b>Total: ${calc['total_stake']:.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎲 <b>SCÉNARIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Si UN seul gagne</b> (~{(1-calc['middle_prob'])*100:.0f}% du temps)
❌ Petite perte: <b>${worst_loss:.2f}</b>

<b>Si LES DEUX gagnent - MIDDLE!</b> (~{calc['middle_prob']*100:.0f}%)
🚀 <b>GROS GAIN: ${calc['profit_scenario_2']:.2f}</b> 💰💰

💡 <b>Zone middle:</b> {describe_middle_zone(middle_data)}
📊 <b>Gap:</b> {calc['middle_zone']} points

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>EXPECTED VALUE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>EV Moyen:</b> +{calc['ev_percent']:.1f}%
<b>Profit moyen/bet:</b> ${calc['ev']:+.2f}

<b>Sur 100 middles:</b>
• {int((1-calc['middle_prob'])*100)} fois: ${worst_loss:.2f} = ${worst_loss * (1-calc['middle_prob']) * 100:.2f}
• {int(calc['middle_prob']*100)} fois: ${calc['profit_scenario_2']:.2f} = ${calc['profit_scenario_2'] * calc['middle_prob'] * 100:.2f}
• <b>NET: ${calc['ev'] * 100:+.2f}</b> ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>POURQUOI C'EST PROFITABLE?</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Ratio gain/perte:</b> {calc['profit_scenario_2']/abs(worst_loss):.0f}:1

Tu perds petit ({abs(worst_loss):.2f}) souvent,
Mais tu gagnes GROS ({calc['profit_scenario_2']:.2f}) assez souvent
= Profit mathématique long terme!

⚠️ <b>Ce N'EST PAS un arbitrage!</b>
Tu PEUX perdre ${abs(worst_loss):.2f} souvent.

⏰ <b>Cotes changent - vérifie avant!</b>"""
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{get_casino_logo('BET99')} BET99",
                url="https://www.bet99.com"
            ),
            InlineKeyboardButton(
                text=f"{get_casino_logo('Coolbet')} Coolbet",
                url="https://www.coolbet.com"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💰 I BET (EV: {calc['ev_percent']:.1f}%)",
                callback_data="middle_test"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Send to admin
    print(f"\n📤 Sending to Telegram (chat_id: {ADMIN_CHAT_ID})...")
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        print("✅ Message sent successfully!")
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        print("\n📝 Message preview:")
        print(message)
    
    finally:
        await bot.session.close()


async def main():
    """Main test function"""
    
    print("=" * 50)
    print("🎰 MIDDLE BET TEST")
    print("=" * 50)
    
    print("\n1️⃣ Testing MIDDLE SAFE (Chase Brown)...\n")
    await test_middle_safe()
    
    print("\n" + "=" * 50)
    print("\n2️⃣ Testing MIDDLE RISQUÉ (LeBron)...\n")
    await test_middle_risky()
    
    print("\n" + "=" * 50)
    print("✅ Tests completed!")


if __name__ == '__main__':
    asyncio.run(main())
