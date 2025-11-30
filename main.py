import asyncio

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import BOT_TOKEN, DEFAULT_EDGE, DEFAULT_BET, ADMIN_CHAT_ID, AFFILIATES
from utils.odds import compute_allocations
from utils.memory import get_last_budget, set_last_budget
from utils.parser_ai import extract_from_email
from utils.image_card import generate_card
from fastapi import FastAPI, Request
import uvicorn


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()
DROPS: dict[str, dict] = {}


class BetStates(StatesGroup):
    waiting_budget = State()


def format_drop_text() -> str:
    b = DEFAULT_BET
    text = (
        "🎯 Risk0 Smart Bet\n"
        f"Match : {b['event']}\n"
        f"Player : {b['player']}\n"
        f"Edge : {DEFAULT_EDGE}%\n"
        f"{b['over']['book']} → {b['over']['label']} {b['over']['odds']:+d}\n"
        f"{b['under']['book']} → {b['under']['label']} {b['under']['odds']:+d}\n"
        f"Date : {b['kickoff']}"
    )
    return text


def build_keyboard_from_drop(drop: dict) -> InlineKeyboardMarkup:
    over, under = drop.get("selection_over", {}), drop.get("selection_under", {})
    row_books: list[InlineKeyboardButton] = []
    for sel in (over, under):
        book = sel.get("book", "").strip()
        url = sel.get("url") or (AFFILIATES.get(book.lower()) if book else None)
        text = book or "Book"
        if url:
            row_books.append(InlineKeyboardButton(text=text, url=url))
        else:
            # Fallback bouton non cliquable externe
            row_books.append(InlineKeyboardButton(text=text, callback_data=f"book|{book}"))

    row_calc = [InlineKeyboardButton(text="🧮 Calculer profit / mise", callback_data=f"calc_start|{drop.get('event_id','')}")]
    row_copy = [InlineKeyboardButton(text="📋 Copier", callback_data=f"copy|{drop.get('event_id','')}")]
    return InlineKeyboardMarkup(inline_keyboard=[row_books, row_calc, row_copy])


def format_drop_text_from_json(d: dict) -> str:
    return (
        "🎯 Risk0 Bet\n"
        f"{d.get('league','')} · {d.get('market','')}\n"
        f"Match : {d.get('event','')}\n"
        f"Player : {d.get('player','')}\n"
        f"Edge : {d.get('edge_percent',0):.1f}%\n"
        f"{d['selection_over']['book']} → {d['selection_over']['label']} {int(d['selection_over']['american']):+d}\n"
        f"{d['selection_under']['book']} → {d['selection_under']['label']} {int(d['selection_under']['american']):+d}\n"
        f"Date : {d.get('kickoff_iso','')}"
    )


def format_allocations_text(bankroll: float) -> str:
    res = compute_allocations(
        DEFAULT_BET["over"]["odds"],
        DEFAULT_BET["under"]["odds"],
        bankroll,
    )
    txt = (
        f"💵 Budget total : {bankroll:.2f} $\n\n"
        f"✅ Safe (Arbitrage)\n"
        f"   {res['safe']['over']:.2f} $ sur Over\n"
        f"   {res['safe']['under']:.2f} $ sur Under\n"
        f"   → Profit garanti : +{res['safe']['profit']:.2f} $\n\n"
        f"⚖️ Balanced\n"
        f"   50/50 → gain/perte : +{res['balanced']['win_over']:.2f} $ / {res['balanced']['win_under']:.2f} $\n\n"
        f"⚡ Aggressive\n"
        f"   70/30 → gain/perte : +{res['aggressive']['win_over']:.2f} $ / {res['aggressive']['win_under']:.2f} $"
    )
    return txt


@dp.message(Command("start"))
async def start(msg: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🧮 Calculer profit / mise", callback_data="calc_start")]]
    )
    await msg.answer(format_drop_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


@dp.callback_query(F.data.startswith("calc_start"))
async def ask_budget_for_event(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    eid = None
    if "|" in cb.data:
        _, eid = cb.data.split("|", 1)
    if eid:
        await state.update_data(eid=eid)
    last = get_last_budget(cb.from_user.id)
    prompt = "💰 Entre ton budget total (en $)"
    if last:
        prompt += f" (dernier : {last}$)"
    await cb.message.answer(prompt)
    await state.set_state(BetStates.waiting_budget)


@dp.message(BetStates.waiting_budget)
async def receive_budget(msg: types.Message, state: FSMContext):
    try:
        bankroll = float(msg.text.replace(",", "."))
        if bankroll <= 0:
            raise ValueError
    except ValueError:
        await msg.answer("⚠️ Montant invalide. Entre un montant positif (ex: 250).")
        return

    set_last_budget(msg.from_user.id, bankroll)

    # Détermine les cotes depuis un drop d'event si présent, sinon fallback défaut
    data = await state.get_data()
    eid = data.get("eid") if data else None
    drop = DROPS.get(eid) if eid else None
    if drop:
        over_odds = float(drop["selection_over"]["american"])  # ex: +250
        under_odds = float(drop["selection_under"]["american"])  # ex: -225
        res = compute_allocations(over_odds, under_odds, bankroll)
        txt = (
            f"💵 Budget total : {bankroll:.2f} $\n\n"
            f"✅ Safe (Arbitrage)\n"
            f"   {res['safe']['over']:.2f} $ sur Over\n"
            f"   {res['safe']['under']:.2f} $ sur Under\n"
            f"   → Profit garanti : +{res['safe']['profit']:.2f} $\n\n"
            f"⚖️ Balanced\n"
            f"   50/50 → gain/perte : +{res['balanced']['win_over']:.2f} $ / {res['balanced']['win_under']:.2f} $\n\n"
            f"⚡ Aggressive\n"
            f"   70/30 → gain/perte : +{res['aggressive']['win_over']:.2f} $ / {res['aggressive']['win_under']:.2f} $"
        )
    else:
        txt = format_allocations_text(bankroll)

    # Construit le clavier en préservant l'event_id si présent
    if eid:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔁 Recalculer", callback_data=f"calc_start|{eid}"),
                    InlineKeyboardButton(text="💵 Copier résultats", callback_data=f"copy|{eid}"),
                ]
            ]
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔁 Recalculer", callback_data="calc_start"),
                    InlineKeyboardButton(text="💵 Copier résultats", callback_data="copy_results"),
                ]
            ]
        )

    await msg.answer(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    await state.clear()


@dp.callback_query(F.data == "copy_results")
async def copy_results(cb: types.CallbackQuery):
    await cb.answer("Résultats copiés ✅", show_alert=False)
    last = get_last_budget(cb.from_user.id)
    if not last:
        await cb.message.answer("Aucun budget mémorisé. Appuie sur \"🔁 Recalculer\" pour recommencer.")
        return
    try:
        bankroll = float(last)
    except Exception:
        bankroll = None
    if bankroll is None:
        await cb.message.answer("Aucun budget mémorisé valide. Appuie sur \"🔁 Recalculer\" pour recommencer.")
        return

    txt = format_allocations_text(bankroll)
    await cb.message.answer(txt, parse_mode=ParseMode.MARKDOWN)


@dp.callback_query(F.data.startswith("copy|"))
async def copy_results_for_event(cb: types.CallbackQuery):
    await cb.answer("Résultats copiés ✅", show_alert=False)
    last = get_last_budget(cb.from_user.id)
    if not last:
        await cb.message.answer("Aucun budget mémorisé. Appuie sur \"🔁 Recalculer\" pour recommencer.")
        return
    try:
        bankroll = float(last)
        if bankroll <= 0:
            raise ValueError
    except Exception:
        await cb.message.answer("Budget mémorisé invalide. Appuie sur \"🔁 Recalculer\" pour recommencer.")
        return

    eid = None
    if "|" in cb.data:
        _, eid = cb.data.split("|", 1)
    drop = DROPS.get(eid) if eid else None
    if drop:
        over_odds = float(drop["selection_over"]["american"])  # ex: +250
        under_odds = float(drop["selection_under"]["american"])  # ex: -225
        res = compute_allocations(over_odds, under_odds, bankroll)
        txt = (
            f"💵 Budget total : {bankroll:.2f} $\n\n"
            f"✅ Safe (Arbitrage)\n"
            f"   {res['safe']['over']:.2f} $ sur Over\n"
            f"   {res['safe']['under']:.2f} $ sur Under\n"
            f"   → Profit garanti : +{res['safe']['profit']:.2f} $\n\n"
            f"⚖️ Balanced\n"
            f"   50/50 → gain/perte : +{res['balanced']['win_over']:.2f} $ / {res['balanced']['win_under']:.2f} $\n\n"
            f"⚡ Aggressive\n"
            f"   70/30 → gain/perte : +{res['aggressive']['win_over']:.2f} $ / {res['aggressive']['win_under']:.2f} $"
        )
    else:
        txt = format_allocations_text(bankroll)

    await cb.message.answer(txt, parse_mode=ParseMode.MARKDOWN)


@app.post("/public/drop")
async def receive_drop(req: Request):
    d = await req.json()
    eid = d.get("event_id")
    if not eid:
        return {"ok": False, "error": "missing event_id"}
    DROPS[eid] = d
    if ADMIN_CHAT_ID:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=format_drop_text_from_json(d),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_keyboard_from_drop(d),
        )
    return {"ok": True}


@app.post("/public/email")
async def receive_email(req: Request):
    payload = await req.json()
    subject = payload.get("subject", "")
    body = payload.get("body", "")

    # Gating: only process expected notifications (with common misspelling tolerance)
    subj = (subject or "").strip()
    if not (subj.startswith("Arbitrage Bet Notification:") or subj.startswith("Arbitrage Bet Notifcation:")):
        return {"ok": False, "reason": "subject_mismatch"}

    # 1) Extraction IA (avec fallback regex intégré)
    drop = extract_from_email(subject, body)
    eid = drop.get("event_id")
    if not eid:
        return {"ok": False, "error": "missing event_id after parse"}
    DROPS[eid] = drop

    # 2) Génération de l'image
    img_path = generate_card(drop)

    # 3) Publication Telegram (image + caption + menu)
    if ADMIN_CHAT_ID:
        try:
            with open(img_path, "rb") as f:
                await bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=f,
                    caption=format_drop_text_from_json(drop),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=build_keyboard_from_drop(drop),
                )
        except Exception:
            # Fallback en texte si l'image ne peut être envoyée
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=format_drop_text_from_json(drop),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_keyboard_from_drop(drop),
            )
    return {"ok": True, "event_id": eid, "image": img_path}


async def runner():
    print("✅ Risk0 Bot + API en ligne.")

    async def serve():
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    await asyncio.gather(
        serve(),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    asyncio.run(runner())
