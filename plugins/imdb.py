# Added by @NaapaExtraa (Fixed by your girl 💗)
import aiohttp
import asyncio
from bot import Codeflix as Client   # ✅ YOUR RUNNING BOT INSTANCE
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
import urllib.parse

CONSUMET_API_URL = "https://consumet-api-org.vercel.app/meta/tmdb/"
SEARCH_PLACEHOLDER_PHOTO = "https://graph.org/file/460e0a539a6671a1c97a7.jpg"
RESULTS_PER_PAGE = 5

IMDB_QUERY_CACHE = {}

async def fetch_consumet_data(endpoint: str, params: dict = None, retries: int = 3):
    url = f"{CONSUMET_API_URL}{endpoint}"
    for attempt in range(retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()

                    if response.status >= 500:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None
            except:
                await asyncio.sleep(1)
                continue
    return None


def format_list(items: list, key: str = None, max_items=5) -> str:
    if not items: return "N/A"
    if key:
        return ', '.join([str(item.get(key, '')) for item in items[:max_items]])
    return ', '.join([str(item) for item in items[:max_items]])


# =================== SEARCH COMMAND =================== #
@Client.on_message(filters.command("search") & filters.private)
async def imdb_search_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Usage:</b> <code>/search movie name</code>")

    query = " ".join(message.command[1:])
    user_id = message.from_user.id
    IMDB_QUERY_CACHE[user_id] = query
    await show_imdb_search_page(client, message, query, page=1)


# =================== PAGINATION =================== #
async def show_imdb_search_page(client, message_or_query, query, page):
    is_callback = isinstance(message_or_query, CallbackQuery)

    if is_callback:
        message = message_or_query.message
        await message_or_query.answer()
    else:
        message = await message_or_query.reply_photo(
            photo=SEARCH_PLACEHOLDER_PHOTO,
            caption=f"🔍 Searching for <b>{query}</b>..."
        )

    data = await fetch_consumet_data(urllib.parse.quote(query), params={"page": page})

    if not data or not data.get("results"):
        return await message.edit_caption("❌ No results found.")

    results = data["results"]
    buttons = []

    for item in results:
        title = item.get("title", "Unknown Title")
        item_id = item.get("id")
        item_type = item.get("type", "Media")
        year = f" ({item.get('releaseDate', '')})" if item.get("releaseDate") else ""

        buttons.append([
            InlineKeyboardButton(
                text=f"{title}{year} [{item_type}]",
                callback_data=f"imdb_detail_{item_id}_{item_type}_{page}"
            )
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"imdb_page_{page-1}"))
    if data.get("hasNextPage", False):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"imdb_page_{page+1}"))

    if nav:
        buttons.append(nav)

    await message.edit_caption(
        f"📄 Results for <b>{query}</b> (Page {page}):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex("^imdb_page_"))
async def imdb_page_flipper(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    page = int(query.data.split("_")[2])
    if user_id not in IMDB_QUERY_CACHE:
        return await query.answer("Search expired.", show_alert=True)

    await show_imdb_search_page(client, query, IMDB_QUERY_CACHE[user_id], page)


# =================== DETAILS VIEW =================== #
@Client.on_callback_query(filters.regex(r"^imdb_detail_(.+)_([^_]+)_(\d+)"))
async def imdb_details(client: Client, query: CallbackQuery):
    await query.answer("⏳ Fetching details...")
    item_id, item_type, page = query.matches[0].groups()
    page = int(page)

    data = await fetch_consumet_data(f"info/{item_id}", params={"type": item_type})

    if not data:
        return await query.message.edit_caption(
            "❌ Could not fetch details.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"imdb_page_{page}")]])
        )

    # ✅ UPDATED POSTER FETCHING
    image_url = (
        data.get("cover")
        or data.get("poster")
        or data.get("image")
        or (f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None)
        or SEARCH_PLACEHOLDER_PHOTO
    )

    description = data.get("description", "No description available.")
    if len(description) > 400:
        description = description[:400] + "..."

    caption = (
        f"<b>{data.get('title', 'N/A')}</b>\n\n"
        f"🎬 <b>Type:</b> {data.get('type', 'N/A')}\n"
        f"📆 <b>Year:</b> {data.get('releaseDate', 'N/A')}\n"
        f"⭐ <b>Rating:</b> {data.get('rating', 'N/A')}/10\n"
        f"🎭 <b>Genres:</b> {format_list(data.get('genres', []))}\n"
        f"🎤 <b>Casts:</b> {format_list(data.get('casts', []), key='name')}\n\n"
        f"📝 <b>Description:</b> {description}\n\n"
        f"Made with ❤️"
    )

    await query.message.edit_media(
        media=InputMediaPhoto(image_url, caption=caption),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"imdb_page_{page}")]])
    )
