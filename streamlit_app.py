import time
import os
import requests
import streamlit as st
from pathlib import Path



CIRCULAR_LOGO = Path(__file__).parent / "assets" / "logo_circular.png"
LOGO_PATH = CIRCULAR_LOGO if CIRCULAR_LOGO.exists() else (Path(__file__).parent / "assets" / "logo.png")

# Page Configuration
st.set_page_config(
    page_title="Playlist Downloader",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Custom CSS for theme styling (matching logo vibrant cyan & royal blue palette)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Brand Title Gradient */
    .brand-title {
        font-size: 2.7rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0052D4 0%, #00C9A7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
        letter-spacing: -0.5px;
    }
    
    .sub-header {
        font-size: 1.05rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }
    
    /* Glowing Circular Logo Container */
    .logo-circle {
        border-radius: 50%;
        border: 2px solid #00C9A7;
        box-shadow: 0 0 20px rgba(0, 201, 167, 0.4), 0 0 40px rgba(0, 82, 212, 0.3);
        transition: transform 0.3s ease;
    }
    .logo-circle:hover {
        transform: scale(1.05);
    }
    
    /* Metrics Accent */
    [data-testid="stMetricValue"] {
        color: #00C9A7 !important;
        font-weight: 700 !important;
    }
    
    /* Progress Bar Color */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #0052D4 0%, #00C9A7 100%) !important;
    }
    
    /* Primary Action Buttons */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0052D4 0%, #00C9A7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(0, 201, 167, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 201, 167, 0.6) !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(0, 201, 167, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)



# Main Header with Circular Logo
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=105)
with header_col2:
    st.markdown('<div class="brand-title">Playlist Downloader</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Download YouTube playlists and videos in high resolution and MP3 audio.</div>', unsafe_allow_html=True)


# Sidebar Configuration
if LOGO_PATH.exists():
    sidebar_c1, sidebar_c2, sidebar_c3 = st.sidebar.columns([1, 2, 1])
    with sidebar_c2:
        st.image(str(LOGO_PATH), width=120)

st.sidebar.header("⚙️ Download Settings")



format_type = st.sidebar.radio(
    "Download Format",
    ["video", "audio"],
    format_func=lambda x: "🎥 Video" if x == "video" else "🎵 Audio Only"
)

if format_type == "video":
    resolution = st.sidebar.selectbox(
        "Video Quality",
        ["best", "1080p", "720p", "480p", "360p", "worst"],
        index=0
    )
    audio_format = "mp3"
else:
    resolution = "best"
    audio_format = st.sidebar.selectbox(
        "Audio Format",
        ["mp3", "m4a", "wav", "flac"],
        index=0
    )




# Navigation Tabs
tab1, tab2 = st.tabs(["📋 Playlist Downloader", "📹 Single Video"])




# =========================================================
# TAB 1: PLAYLIST DOWNLOADER
# =========================================================
with tab1:
    if st.session_state.get("clear_playlist_input"):
        st.session_state["playlist_input"] = ""
        del st.session_state["clear_playlist_input"]

    playlist_url = st.text_input(
        "Enter YouTube Playlist URL",
        placeholder="https://www.youtube.com/playlist?list=...",
        key="playlist_input"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        extract_btn = st.button("🔍 Extract Playlist", use_container_width=True)

    if extract_btn and playlist_url:
        with st.spinner("Extracting playlist information..."):
            try:
                res = requests.post(
                    f"{API_BASE_URL}/playlist/extract",
                    json={"url": playlist_url}
                )
                if res.status_code == 200:
                    st.session_state["playlist_info"] = res.json()
                    if "active_job_id" in st.session_state:
                        del st.session_state["active_job_id"]
                    st.success("Playlist extracted successfully!")
                else:
                    st.error(f"Error extracting playlist: {res.json().get('detail', res.text)}")
            except Exception as e:
                st.error(f"Could not connect to backend server ({e}). Make sure FastAPI app is running.")

    # ---------------------------------------------------------
    # CASE 1: ACTIVE DOWNLOAD JOB RUNNING OR FINISHED
    # ---------------------------------------------------------
    if "active_job_id" in st.session_state:
        job_id = st.session_state["active_job_id"]
        st.markdown("---")
        
        col_hdr1, col_hdr2 = st.columns([3, 1])
        with col_hdr1:
            st.subheader(f"📊 Live Download Tracker")
        with col_hdr2:
            if st.button("✨ New Download", use_container_width=True):
                if "active_job_id" in st.session_state:
                    del st.session_state["active_job_id"]
                if "playlist_info" in st.session_state:
                    del st.session_state["playlist_info"]
                st.session_state["clear_playlist_input"] = True
                st.rerun()





        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            if st.button("⏸️ Pause", key="pause_btn"):
                requests.post(f"{API_BASE_URL}/playlist/jobs/{job_id}/pause")
                st.rerun()
        with col_c2:
            if st.button("▶️ Resume", key="resume_btn"):
                requests.post(f"{API_BASE_URL}/playlist/jobs/{job_id}/resume")
                st.rerun()
        with col_c3:
            if st.button("🛑 Cancel", key="cancel_btn"):
                requests.post(f"{API_BASE_URL}/playlist/jobs/{job_id}/cancel")
                st.rerun()
        with col_c4:
            if st.button("🔄 Retry Failed", key="retry_btn"):
                requests.post(f"{API_BASE_URL}/playlist/jobs/{job_id}/retry")
                st.rerun()

        try:
            status_res = requests.get(f"{API_BASE_URL}/playlist/status/{job_id}")
            if status_res.status_code == 200:
                job_data = status_res.json()

                st.progress(min(1.0, max(0.0, job_data["progress"] / 100.0)))
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Status", job_data["status"].upper())
                m2.metric("Overall Progress", f"{job_data['progress']}%")
                m3.metric("Completed", f"{job_data['completed']}/{job_data['total_videos']}")
                m4.metric("Failed", job_data["failed"])

                if job_data.get("current_video"):
                    st.info(f"Currently downloading: **{job_data['current_video']}**")

                st.markdown("#### 📹 Individual Video Progress")
                for v in job_data.get("videos", []):
                    col_v1, col_v2 = st.columns([3, 2])
                    with col_v1:
                        st.write(f"**{v['title']}**")
                        if v.get("speed") and v.get("eta"):
                            st.caption(f"Speed: {v['speed']} | ETA: {v['eta']}")
                        if v.get("error"):
                            st.caption(f"⚠️ Error: {v['error']}")
                    with col_v2:
                        st.write(f"Status: `{v['status']}`")
                        st.progress(min(1.0, max(0.0, v["progress"] / 100.0)))

                if job_data["status"] in ("completed", "completed_with_errors"):
                    st.balloons()
                    st.success("Download process completed!")
                    
                    try:
                        zip_res = requests.get(f"{API_BASE_URL}/download/zip/{job_id}")
                        if zip_res.status_code == 200:
                            st.download_button(
                                label="💾 Save Full Playlist (.zip)",
                                data=zip_res.content,
                                file_name=f"playlist_{job_id}.zip",
                                mime="application/zip",
                                type="primary",
                                use_container_width=True,
                            )
                    except Exception:
                        pass

                elif job_data["status"] in ("queued", "downloading"):
                    time.sleep(2)
                    st.rerun()

        except Exception as e:
            st.warning(f"Waiting for job updates... ({e})")

    # ---------------------------------------------------------
    # CASE 2: PRE-DOWNLOAD VIDEO SELECTION (ONLY SHOWN BEFORE STARTING)
    # ---------------------------------------------------------
    elif "playlist_info" in st.session_state:
        info = st.session_state["playlist_info"]
        
        st.markdown("---")
        info_col1, info_col2 = st.columns([1, 3])
        with info_col1:
            if info.get("thumbnail"):
                st.image(info["thumbnail"], use_container_width=True)

        with info_col2:
            st.subheader(info.get("title", "Playlist"))
            st.write(f"**Uploader:** {info.get('uploader', 'Unknown')}")
            st.write(f"**Total Videos:** {info.get('video_count', 0)}")

        st.subheader("Select Videos to Download")
        all_videos = info.get("videos", [])
        video_titles = {v["id"]: f"{idx+1}. {v['title']}" for idx, v in enumerate(all_videos)}
        
        selected_ids = st.multiselect(
            "Choose videos (leave empty to download all):",
            options=list(video_titles.keys()),
            format_func=lambda vid: video_titles[vid],
            default=list(video_titles.keys())
        )

        if st.button("🚀 Start Downloading Playlist", type="primary", use_container_width=True):
            with st.spinner("Starting playlist download..."):
                try:
                    payload = {
                        "url": playlist_url,
                        "format_type": format_type,
                        "resolution": resolution,
                        "audio_format": audio_format,
                        "selected_video_ids": selected_ids if selected_ids else None,
                    }
                    res = requests.post(f"{API_BASE_URL}/playlist/download", json=payload)
                    if res.status_code == 202:
                        job_data = res.json()
                        st.session_state["active_job_id"] = job_data["job_id"]
                        st.rerun()
                    else:
                        st.error(f"Error starting download: {res.text}")
                except Exception as e:
                    st.error(f"Failed to start download job: {e}")




# =========================================================
# TAB 2: SINGLE VIDEO DOWNLOAD
# =========================================================
with tab2:
    video_url = st.text_input(
        "Enter YouTube Video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key="video_input"
    )

    if st.button("📥 Download Single Video", type="primary"):
        if video_url:
            with st.spinner("Downloading video to Windows Downloads folder... Please wait."):
                try:
                    payload = {
                        "url": video_url,
                        "format_type": format_type,
                        "resolution": resolution,
                        "audio_format": audio_format,
                    }

                    res = requests.post(f"{API_BASE_URL}/download/video", json=payload)

                    if res.status_code == 200:
                        data = res.json()
                        filepath = data.get("filepath", "")
                        st.success(f"Download complete! Saved to Windows Downloads folder: `{filepath}`")
                    else:
                        st.error(f"Download failed: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")





