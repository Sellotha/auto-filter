import re
import aiohttp
from io import BytesIO
from PIL import Image
from info import IMAGE_FETCH, TMDB_API_KEY
from imdb import Cinemagoer

ia = Cinemagoer()

def list_to_str(lst):
    return ", ".join(map(str, lst)) if lst else ""

async def fetch_image(url, size=(720, 720)):
    if not IMAGE_FETCH or not url:
        return None

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    print(f"[×] Poster Fetch Failed: {url}")
                    return None

                data = await resp.read()
                img = Image.open(BytesIO(data)).convert("RGB")
                img = img.resize(size, Image.LANCZOS)
                byte_arr = BytesIO()
                img.save(byte_arr, format="JPEG")
                byte_arr.seek(0)
                return byte_arr

    except Exception as e:
        print(f"[Poster Fetch Error] {e}")
        return None


async def tmdb_fallback(query):
    if not TMDB_API_KEY:
        return None

    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()
                if not data.get("results"):
                    return None

                poster_path = data["results"][0].get("poster_path")
                if poster_path:
                    return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except:
        pass
    return None


async def get_movie_details(query, id=False, file=None):
    try:
        query = query.strip()

        # First try IMDB
        movie_list = ia.search_movie(query, results=3)

        if movie_list:
            movie = ia.get_movie(movie_list[0].movieID)

            poster_url = (
                movie.get("full-size cover url")
                or movie.get("cover url")
                or movie.get("thumbnail url")
            )

            # If IMDB poster missing → TMDB fallback
            if not poster_url:
                poster_url = await tmdb_fallback(movie.get("title"))

            plot = movie.get("plot", ["No Description Available"])[0]
            if len(plot) > 600:
                plot = plot[:600] + "..."

            return {
                "title": movie.get("title"),
                "year": movie.get("year"),
                "rating": movie.get("rating"),
                "genres": list_to_str(movie.get("genres")),
                "languages": list_to_str(movie.get("languages")),
                "plot": plot,
                "poster_url": poster_url,
            }

        # ✅ IF IMDB SEARCH FAILED COMPLETELY → DIRECT TMDB
        poster_url = await tmdb_fallback(query)
        if poster_url:
            return {
                "title": query.title(),
                "plot": "No IMDB Data Found",
                "poster_url": poster_url
            }

        return None

    except Exception as e:
        print(f"[IMDB Error] {e}")
        return None
