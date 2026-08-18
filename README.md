# 🎬 YouTube Playlist & Video Downloader

A full-featured FastAPI backend and Streamlit web interface for downloading YouTube playlists and single videos with customizable resolutions (1080p, 720p, 480p), MP3 audio extraction, English subtitles, selective video downloading, job control (pause, resume, cancel, retry), and Zip file archiving.

---

## 🚀 Features

- **Streamlit Web UI**: Easy-to-use graphical dashboard for extracting playlists, selecting videos, monitoring progress, and downloading files.
- **FastAPI REST API**: High-performance asynchronous API endpoints for metadata extraction, background job management, and file streaming.
- **Download Customization**:
  - **Resolution options**: `best`, `1080p`, `720p`, `480p`, `360p`, `worst`.
  - **Audio-only mode**: Extract MP3, M4A, WAV, or FLAC audio files using FFmpeg.
  - **Subtitles**: Option to download embedded/sidecar English subtitles.
  - **Selective Download**: Choose specific videos to download from a playlist.
- **Job Control**: Live status tracking, pause, resume, cancel, and retry failed downloads.
- **File Delivery & Zip Export**: Direct file download endpoints and one-click `.zip` export for full playlist jobs.
- **Distributed Queues Support**: Configured for Celery & Redis background task processing with threading fallback.
- **Automated Test Suite**: Integrated unit and API tests with Pytest.

---

## 📁 Folder Structure

```
Playlist Downloader/
├── app/
│   ├── api/
│   │   └── routes/         # FastAPI endpoints (health, playlist, download)
│   ├── core/               # Configuration, logging, celery setup, exceptions
│   ├── jobs/               # In-memory job manager and Celery task definitions
│   ├── models/             # Data models placeholder
│   ├── schemas/            # Pydantic schemas for requests and responses
│   ├── services/           # Downloader, Extractor, and Playlist services
│   ├── utils/              # Directory and validator helpers
│   └── main.py             # FastAPI entrypoint
├── downloads/              # Default downloaded files directory
├── tests/                  # Pytest test suite
├── streamlit_app.py        # Streamlit web dashboard
├── requirements.txt        # Dependencies
├── .env.example            # Environment variables template
└── README.md               # Documentation
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- FFmpeg installed on your system PATH (required for audio conversion and high-res video merging)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## 🏃 Running the Application

### Launch FastAPI Backend
```bash
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### Launch Streamlit Frontend Dashboard
In a new terminal window:
```bash
streamlit run streamlit_app.py
```
- Web UI: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Running Tests

Run the test suite with pytest:
```bash
python -m pytest
```

---

## 📡 API Reference Endpoint Highlights

- `POST /playlist/extract`: Extract metadata and video list from playlist URL.
- `POST /playlist/download`: Start background download job with format and quality options.
- `GET /playlist/status/{job_id}`: Retrieve progress, speed, ETA, and status.
- `POST /playlist/jobs/{job_id}/cancel`: Cancel a running download job.
- `POST /playlist/jobs/{job_id}/pause`: Pause job.
- `POST /playlist/jobs/{job_id}/resume`: Resume job.
- `POST /playlist/jobs/{job_id}/retry`: Retry failed video downloads.
- `POST /download/video`: Directly download a single video.
- `GET /download/file`: Stream/download a completed file.
- `GET /download/zip/{job_id}`: Download a `.zip` archive of a completed job's files.
