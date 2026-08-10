import re

def validate_youtube_url(url: str) -> bool:
    pattern = r"^https?://(www\.)?(youtube\.com|youtu\.be)/.+$"
    return bool(re.match(pattern, url))