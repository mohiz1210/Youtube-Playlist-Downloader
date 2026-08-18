import yt_dlp

from app.core.exceptions import PlaylistError


class PlaylistExtractor:

    def extract(self, url: str):

        options = {
            "quiet": True,
            "extract_flat": True,
        }


        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                data = ydl.extract_info(
                    url,
                    download=False,
                )

                return data

        except Exception as error:
            raise PlaylistError(str(error))