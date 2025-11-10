# Added by @NaapaExtraa (Edited & Fixed By Your Girl 💗)
import aiohttp
import asyncio
from bot import app  # ✅ IMPORTANT: Use your running client instance
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
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
                    return None
            except aiohttp.ClientError:
                await asyncio.sleep(1)
                continue
    return None

def format_list(items: list, key: str = None, max_items=5) -> str:
    if not items: return "N/A"
    if key:
        return ', '.join([str(item.get(key, '')) for item in items[:max_items]])
    return ', '.join([str(item) for item in items[:max_items]])

# --- Main Command Handler ---
@app.on_message(filters.command("search") & filters.private)
async def imdb_search_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Usage:</b> <code>/search [movie or tv show name]</code>")

    query = " ".join(message.command[1:])
    user_id = message.from_user.id
    IMDB_QUERY_CACHE[user_id] = query
    await show_imdb_search_page(client, message, query, page=1)

# --- Pagination + Search Page Renderer ---
async def show_imdb_search_page(client, message_or_query, query, page):
    is_callback = isinstance(message_or_query, CallbackQuery)
    
    if is_callback:
        message = message_or_query.message
        await message_or_query.answer()
    else:
        message = await message_or_query.reply_photo(
            photo=SEARCH_PLACEHOLDER_PHOTO,
            caption=f"Searching for <b>{query}</b>..."
        )

    encoded_query = urllib.parse.quote(query)
    data = await fetch_consumet_data(encoded_query, params={"page": page})

    if not data or not data.get('results'):
        return await message.edit_caption("No results found.")

    results = data['results']
    buttons = []
    for item in results:
        title = item.get('title', 'Unknown Title')
        item_id = item.get('id')
        item_type = item.get('type', 'Media')
        release_date = item.get('releaseDate', '')
        year = f" ({release_date})" if release_date else ""
        buttons.append([InlineKeyboardButton(f"{title}{year} [{item_type}]", callback_data=f"imdb_detail_{item_id}_{item_type}_{page}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"imdb_page_{page - 1}"))
    if data.get('hasNextPage', False):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"imdb_page_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    await message.edit_caption(
        f"Search results for <b>{query}</b> (Page {page}):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^imdb_page_"))
async def imdb_page_flipper(client, query: CallbackQuery):
    user_id = query.from_user.id
    page = int(query.data.split("_")[2])
    if user_id not in IMDB_QUERY_CACHE:
        return await query.answer("Your search has expired.", show_alert=True)
    await show_imdb_search_page(client, query, IMDB_QUERY_CACHE[user_id], page)

@app.on_callback_query(filters.regex(r"^imdb_detail_(.+)_([^_]+)_(\d+)"))
async def imdb_details(client, query: CallbackQuery):
    await query.answer("Fetching details...")
    item_id, item_type, page = query.matches[0].groups()
    page = int(page)

    data = await fetch_consumet_data(f"info/{item_id}", params={"type": item_type})
    if not data:
        return await query.message.edit_caption(
            "❌ Failed to fetch information.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"imdb_page_{page}")]])
        )

    title = data.get('title', 'N/A')

    # ✅ FINAL POSTER FIX (HD Poster Fallback added)
    image_url = (
        data.get('cover')
        or data.get('poster')
        or data.get('image')
        or (f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None)
        or SEARCH_PLACEHOLDER_PHOTO
    )

    description = data.get('description') or "No description available."
    if len(description) > 400:
        description = description[:400] + "..."

    caption = (
        f"<b>{title}</b>\n\n"
        f"→ <b>Type:</b> {data.get('type', 'N/A')}\n"
        f"→ <b>Released:</b> {data.get('releaseDate', 'N/A')}\n"
        f"→ <b>Rating:</b> {data.get('rating', 'N/A')}/10\n"
        f"→ <b>Genres:</b> {format_list(data.get('genres', []))}\n"
        f"→ <b>Casts:</b> {format_list(data.get('casts', []), key='name')}\n\n"
        f"→ <b>Description:</b> {description}\n\n"
        f"🥀 Made By @NaapaExtraa"
    )

    await query.message.edit_media(
        media=InputMediaPhoto(media=image_url, caption=caption),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Results", callback_data=f"imdb_page_{page}")]])
    )
