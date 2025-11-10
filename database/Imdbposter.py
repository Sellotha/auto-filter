import re
import aiohttp
import asyncio
from aiohttp import ClientTimeout
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from info import IMAGE_FETCH
from imdb import Cinemagoer

ia = Cinemagoer()

def list_to_str(lst):
    if lst:
        return ", ".join(map(str, lst))
    return ""

def _normalize_imdb_id(imdb_input):
    """
    Accepts: 'tt0123456', '0123456', 'https://www.imdb.com/title/tt0123456/', or integer.
    Returns digits-only string (e.g. '0123456') or None.
    """
    if imdb_input is None:
        return None
    s = str(imdb_input).strip()
    m = re.search(r'(tt)?(\d+)', s)
    if m:
        return m.group(2)
    return None

async def fetch_image(url, size=(1280, 720), timeout_seconds=10, max_bytes=10_000_000):
    """Fetch image from URL and return BytesIO with JPEG content resized to size.
    Returns None on failure."""
    if not IMAGE_FETCH:
        print("Image fetching is disabled.")
        return None
    if not url:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; auto-filter/1.0; +https://github.com/YourRepo)",
        "Accept": "image/*,*/*;q=0.1",
    }
    timeout = ClientTimeout(total=timeout_seconds)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    print(f"Failed to fetch image: {resp.status} for URL: {url}")
                    return None

                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    print(f"Unexpected content type for image: {content_type} for URL: {url}")

                content = await resp.read()
                if len(content) > max_bytes:
                    print("Fetched image too large, skipping.")
                    return None

                try:
                    img = Image.open(BytesIO(content))
                    img = img.convert("RGB")
                    img = img.resize(size, Image.LANCZOS)

                    out = BytesIO()
                    img.save(out, format="JPEG", quality=90)
                    out.seek(0)
                    return out
                except UnidentifiedImageError:
                    print(f"PIL could not identify image from {url}")
                except Exception as e:
                    print(f"Error processing image from {url}: {e}")
    except aiohttp.ClientError as e:
        print(f"HTTP request error in fetch_image: {e}")
    except asyncio.TimeoutError:
        print(f"Timeout fetching image from {url}")
    except Exception as e:
        print(f"Unexpected error in fetch_image: {e}")

    return None

async def get_movie_details(query, id=False, file=None):
    try:
        if not id:
            q = str(query).strip()
            title = q
            year = re.findall(r'[1-2]\d{3}$', q, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1])
                title = q.replace(year, "").strip()
            elif file:
                year = re.findall(r'[1-2]\d{3}', str(file), re.IGNORECASE)
                if year:
                    year = list_to_str(year[:1])
            else:
                year = None

            results = ia.search_movie(title, results=10)
            if not results:
                return None

            if year:
                filtered = [r for r in results if str(r.get('year')) == str(year)]
                if not filtered:
                    filtered = results
            else:
                filtered = results

            filtered = [r for r in filtered if r.get('kind') in ['movie', 'tv series']] or filtered
            movieid = filtered[0].movieID
        else:
            movieid = _normalize_imdb_id(query)
            if not movieid:
                movieid = str(query)

        movie = ia.get_movie(movieid)
        if not movie:
            return None

        date = movie.get("original air date") or movie.get("year") or "N/A"

        plot = None
        plot_list = movie.get('plot')
        if plot_list:
            try:
                plot = plot_list[0]
            except Exception:
                plot = None
        if not plot:
            plot = movie.get('plot outline')
        if plot and len(plot) > 800:
            plot = plot[:800] + "..."

        poster_url = None
        if movie.get('full-size cover url'):
            poster_url = movie.get('full-size cover url')
        elif movie.get('cover url'):
            poster_url = movie.get('cover url')
        else:
            imgs = movie.get('images') or {}
            poster_list = imgs.get('poster') if isinstance(imgs, dict) else None
            if poster_list and isinstance(poster_list, (list, tuple)) and len(poster_list) > 0:
                poster_url = poster_list[0]

        raw_imdb_id = movie.get('imdbID') or movieid
        imdb_id_str = f"tt{raw_imdb_id}" if raw_imdb_id and not str(raw_imdb_id).startswith("tt") else raw_imdb_id

        rating_val = movie.get("rating")
        rating = float(rating_val) if rating_val is not None else None

        return {
            'title': movie.get('title'),
            'votes': movie.get('votes'),
            'aka': list_to_str(movie.get('akas')),
            'seasons': movie.get('number of seasons'),
            'box_office': movie.get('box office'),
            'localized_title': movie.get('localized title'),
            'kind': movie.get('kind'),
            'imdb_id': imdb_id_str,
            'cast': list_to_str(movie.get('cast')),
            'runtime': list_to_str(movie.get('runtimes')),
            'countries': list_to_str(movie.get('countries')),
            'certificates': list_to_str(movie.get('certificates')),
            'languages': list_to_str(movie.get('languages')),
            'director': list_to_str(movie.get('director')),
            'writer': list_to_str(movie.get('writer')),
            'producer': list_to_str(movie.get('producer')),
            'composer': list_to_str(movie.get('composer')),
            'cinematographer': list_to_str(movie.get('cinematographer')),
            'music_team': list_to_str(movie.get('music department')),
            'distributors': list_to_str(movie.get('distributors')),
            'release_date': date,
            'year': movie.get('year'),
            'genres': list_to_str(movie.get('genres')),
            'poster_url': poster_url,
            'plot': plot,
            'rating': rating,
            'url': f'https://www.imdb.com/title/{imdb_id_str}' if imdb_id_str else None
        }

    except Exception as e:
        print(f"Error in get_movie_details: {e}")
        return None
