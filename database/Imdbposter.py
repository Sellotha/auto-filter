# Added by @NaapaExtraa
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
import urllib.parse

CONSUMET_API_URL = "https://consumet-api-org.vercel.app/meta/tmdb/"
SEARCH_PLACEHOLDER_PHOTO = "https://graph.org/file/460e0a539a6671a1c97a7.jpg"
RESULTS_PER_PAGE = 5

IMDB_QUERY_CACHE = {}

async def fetch_consumet_data(endpoint: str, params: dict = None, retries: int = 3):
    """
    Makes a unified async request to the consumet API with automatic retries for server errors.
    """
    url = f"{CONSUMET_API_URL}{endpoint}"
    for attempt in range(retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status >= 500:
                        print(f"Consumet API Server Error (Status {response.status}), attempt {attempt + 1}/{retries} for URL {response.url}")
                        await asyncio.sleep(1) 
                        continue
                    else:
                        print(f"Consumet API Client Error: Status {response.status} for URL {response.url}")
                        return None 
            except aiohttp.ClientError as e:
                print(f"Consumet API Request Error: {e}, attempt {attempt + 1}/{retries}")
                await asyncio.sleep(1)
                continue
    return None 

def format_list(items: list, key: str = None, max_items=5) -> str:
    if not items: return "N/A"
    if key:
        return ', '.join([str(item.get(key, '')) for item in items[:max_items]])
    return ', '.join([str(item) for item in items[:max_items]])

# --- Main Command Handler ---
@Client.on_message(filters.command("search") & filters.private)
async def imdb_search_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Usage:</b> <code>/search [movie or tv show name]</code>")

    query = " ".join(message.command[1:])
    user_id = message.from_user.id
    IMDB_QUERY_CACHE[user_id] = query
    await show_imdb_search_page(client, message, query, page=1)

# --- Pagination and Search Page Renderer ---
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
        
        callback_data = f"imdb_detail_{item_id}_{item_type}_{page}"
        button_text = f"{title}{year} [{item_type}]"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"imdb_page_{page - 1}"))
    if data.get('hasNextPage', False):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"imdb_page_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    await message.edit_caption(
        f"Search results for <b>{query}</b> (Page {page}):",
        reply_markup=reply_markup
    )

@Client.on_callback_query(filters.regex("^imdb_page_"))
async def imdb_page_flipper(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    page = int(query.data.split("_")[2])
    if user_id not in IMDB_QUERY_CACHE:
        return await query.answer("Your search has expired.", show_alert=True)
    
    search_query = IMDB_QUERY_CACHE[user_id]
    await show_imdb_search_page(client, query, search_query, page)

@Client.on_callback_query(filters.regex(r"^imdb_detail_(.+)_([^_]+)_(\d+)"))
async def imdb_details(client: Client, query: CallbackQuery):
    await query.answer("Fetching details...")
    item_id, item_type, page = query.matches[0].groups()
    page = int(page)

    data = await fetch_consumet_data(f"info/{item_id}", params={"type": item_type})

    if not data:
        await query.message.edit_caption(
            "❌ **Could not fetch details for this item.**\n\nThe source API might be temporarily unavailable. Please try again in a moment.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Results", callback_data=f"imdb_page_{page}")]]))
        return

    title = data.get('title', 'N/A')
    image_url = data.get('cover') or data.get('poster') or data.get('image', SEARCH_PLACEHOLDER_PHOTO)
    
    description = data.get('description') or "No description available."
    if len(description) > 400:
        description = description[:400] + "..."

    caption = f"<b>{title}</b>\n\n"
    caption += f"→ <b>Type:</b> {data.get('type', 'N/A')}\n"
    caption += f"→ <b>Released:</b> {data.get('releaseDate', 'N/A')}\n"
    caption += f"→ <b>Rating:</b> {data.get('rating', 'N/A')}/10\n"
    caption += f"→ <b>Genres:</b> {format_list(data.get('genres', []))}\n"
    caption += f"→ <b>Casts:</b> {format_list(data.get('casts', []), key='name')}\n\n"
    caption += f"→ <b>Description:</b> {description}\n\n"
    caption += f"Made By @NaapaExtraa 🥀"
    
    buttons = [
        [InlineKeyboardButton("« Back to Results", callback_data=f"imdb_page_{page}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.message.edit_media(
        media=InputMediaPhoto(media=image_url, caption=caption),
        reply_markup=reply_markup
    )
