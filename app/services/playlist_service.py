from app.services.extractor import PlaylistExtractor


class PlaylistService:

    def __init__(self):
        self.extractor = PlaylistExtractor()

    def get_playlist(self, url: str):

        data = self.extractor.extract(url)

        entries = data.get("entries", [])

        videos = []

        for entry in entries:

            if not entry:
                continue

            video_id = entry.get("id")

            video_url = entry.get("url")

            if not video_url and video_id:
                video_url = (
                    f"https://www.youtube.com/watch?v={video_id}"
                )

            videos.append({
                "id": video_id,
                "title": entry.get(
                    "title",
                    "Unknown title"
                ),
                "url": video_url,
            })

        return {
            "title": data.get(
                "title",
                "Unknown playlist"
            ),
            "uploader": data.get("uploader"),
            "video_count": len(videos),
            "thumbnail": (
                data["thumbnails"][-1]["url"]
                if data.get("thumbnails")
                else None
            ),
            "videos": videos,
        }