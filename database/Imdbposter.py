import re
import aiohttp
from io import BytesIO
from PIL import Image
from info import IMAGE_FETCH, TMDB_API_KEY
from imdb import Cinemagoer

ia = Cinemagoer()

def list_to_str(lst):
    if lst:
        return ", ".join(map(str, lst))
    return ""

async def fetch_image(url, size=(720, 720)):
    if not IMAGE_FETCH or not url:
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    print(f"[×] Poster Fetch Failed: {url}")
                    return None

                data = await response.read()
                img = Image.open(BytesIO(data)).convert("RGB")
                img = img.resize(size, Image.LANCZOS)

                byte_arr = BytesIO()
                img.save(byte_arr, format="JPEG")
                byte_arr.seek(0)
                return byte_arr

    except Exception as e:
        print(f"[Poster Fetch Error] {e}")
    return None


async def get_movie_details(query, id=False, file=None):
    try:
        query = query.strip().lower()
        year = re.findall(r"[1-2]\d{3}$", query)
        title = query.replace(year[0], "").strip() if year else query

        movie_list = ia.search_movie(title, results=5)
        if not movie_list:
            return None

        if year:
            movie_list = [m for m in movie_list if str(m.get("year")) == year[0]] or movie_list

        movie = ia.get_movie(movie_list[0].movieID)

        # IMDB Poster First Attempt
        poster_url = (
            movie.get('full-size cover url') or
            movie.get('cover url') or
            movie.get('thumbnail url')
        )

        # ✅ TMDB Fallback
        if not poster_url and TMDB_API_KEY:
            tmdb_title = movie.get("title").replace(" ", "%20")
            tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={tmdb_title}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(tmdb_url) as r:
                        tmdb_data = await r.json()
                        if tmdb_data.get("results"):
                            poster_path = tmdb_data["results"][0].get("poster_path")
                            if poster_path:
                                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            except:
                pass

        plot = movie.get("plot", ["No Description Available"])[0]
        if len(plot) > 600:
            plot = plot[:600] + "..."

        return {
            "title": movie.get("title"),
            "year": movie.get("year"),
            "genres": list_to_str(movie.get("genres")),
            "languages": list_to_str(movie.get("languages")),
            "director": list_to_str(movie.get("director")),
            "cast": list_to_str(movie.get("cast")),
            "runtime": list_to_str(movie.get("runtimes")),
            "plot": plot,
            "rating": movie.get("rating"),
            "poster_url": poster_url,
            "url": f"https://www.imdb.com/title/tt{movie.movieID}"
        }

    except Exception as e:
        print(f"[IMDB Fetch Error] {e}")
        return None
