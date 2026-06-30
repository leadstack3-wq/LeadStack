import streamlit as st
import pandas as pd
import re
import requests
import os
from googleapiclient.discovery import build
import streamlit_analytics2 as streamlit_analytics

# --- Page Configuration ---
st.set_page_config(page_title="Free YouTube Scraper | Leadstack", layout="wide", page_icon="🎥")

# --- Professional Light Mode & YouTube Red Accent Injection ---
st.markdown("""
<style>
header[data-testid="stHeader"] {
    background-color: transparent !important;
    background: transparent !important;
    height: 0px !important;
}
.stApp [data-testid="stHeader"] {
    display: none !important;
}
.stApp {
    background: linear-gradient(135deg, #FFF5F5 0%, #F9FAFB 100%) !important;
    color: #1F2937 !important;
}
h1, h2, h3, .stMarkdown {
    color: #CC0000 !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FFEBEB 100%) !important;
    border-right: 1px solid rgba(255, 0, 0, 0.15);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
    color: #990000 !important;
}
div[data-baseweb="input"] input, 
div[data-baseweb="input"] textarea,
.stNumberInput input {
    background-color: #FFFFFF !important;
    color: #1F2937 !important;
    border: 1px solid rgba(255, 0, 0, 0.25) !important;
    border-radius: 12px !important;
}
div[data-baseweb="input"] input:focus, .stNumberInput input:focus {
    border-color: #FF0000 !important;
    box-shadow: 0 0 0 1px #FF0000 !important;
}
div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(255, 0, 0, 0.2) !important;
    box-shadow: 0 4px 15px rgba(255, 0, 0, 0.03) !important;
    border-radius: 14px;
    padding: 16px;
}
.stButton > button {
    background: linear-gradient(90deg, #FF0000, #CC0000) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 12px 24px !important;
    box-shadow: 0 4px 14px rgba(255, 0, 0, 0.2) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(255, 0, 0, 0.3) !important;
}
div.stDownloadButton > button {
    background: #FFFFFF !important;
    color: #1F2937 !important;
    border: 1px solid rgba(255, 0, 0, 0.3) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
div.stDownloadButton > button:hover {
    background: #FFEBEB !important;
    border-color: #FF0000 !important;
}
.block-container {
    padding-top: 0rem !important;
    max-width: 1400px;
}
div[data-testid="stDataFrame"] {
    background-color: #FFFFFF !important;
    border: 1px solid rgba(255, 0, 0, 0.15);
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
    overflow: hidden;
}
.yt-metric-card {
    background: #FFFFFF;
    border: 1px solid rgba(255, 0, 0, 0.2);
    border-left: 6px solid #FF0000;
    box-shadow: 0 4px 15px rgba(255, 0, 0, 0.03);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 20px;
}
.yt-card-label {
    color: #606060;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.yt-card-value {
    color: #030303;
    font-size: 22px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --- Header Presentation Block ---
st.markdown(
    "<div style='padding:22px; border-radius:18px;"
    "background: linear-gradient(90deg, #FF0000, #CC0000);"
    "color: white; margin-bottom: 1.5rem; box-shadow: 0 8px 25px rgba(255,0,0,0.2);'>"
    "<h1 style='margin:0; color:#FFFFFF !important; font-size:28px;'>🎥 Free YouTube Scraper</h1>"
    "<p style='margin:5px 0 0 0; color:#FFFFFF !important; opacity:0.95; font-size:15px;'>Export YouTube Leads to Google Sheets or Download CSV</p>"
    "</div>",
    unsafe_allow_html=True
)

# =========================================================
# INITIALIZE SESSION STATE FOR PERSISTENT DATA & PERM FILE
# =========================================================
DATA_DIR = "."
HISTORY_FILE = os.path.join(DATA_DIR, "permanently_seen_youtube_channels.txt")

# Load history from local file storage if it exists to maintain day-to-day permanent memory
if "seen_youtube_channels" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            st.session_state.seen_youtube_channels = set(line.strip() for line in f if line.strip())
    else:
        st.session_state.seen_youtube_channels = set()

# =====================
# CALCULATION UTILITY
# =====================
def get_channel_tier(subs):
    if subs >= 1000000: return "👑 Mega Creator"
    if subs >= 100000: return "💎 Macro Influencer"
    if subs >= 10000: return "🚀 Micro Creator"
    return "🌱 Nano Influencer"

def extract_email_from_text(text):
    """Parses text fields using regular expressions to isolate valid public emails."""
    if not text:
        return "N/A"
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_regex, text)
    return match.group(0) if match else "N/A"

def extract_link_from_text(text):
    if not text:
        return "N/A"
    # Matches typical http, https protocols along with clean www. address layouts
    url_regex = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
    match = re.search(url_regex, text)
    return match.group(0) if match else "N/A"

# =====================
# YOUTUBE API CORE
# =====================
def fetch_youtube_channels(api_key, keyword, region_code, min_subs, max_subs, min_videos, max_videos, min_views, max_views, about_keywords, require_email, require_link, limit):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Step 1: Execute search targeting channels matching the main niche keyword
    search_response = youtube.search().list(
        q=keyword,
        type='channel',
        part='id,snippet',
        maxResults=min(limit * 5, 50),
        regionCode=region_code if region_code else None
    ).execute()

    channel_ids = [item['id']['channelId'] for item in search_response.get('items', [])]
    
    if not channel_ids:
        return pd.DataFrame()

    # Step 2: Fetch full statistics and 'About' description text
    stats_response = youtube.channels().list(
        id=','.join(channel_ids),
        part='snippet,statistics'
    ).execute()

    channels_data = []
    about_keyword_list = [k.strip().lower() for k in about_keywords.split(',')] if about_keywords else []
    
    for item in stats_response.get('items', []):
        channel_id = item['id']
        channel_url = f"https://www.youtube.com/channel/{channel_id}"
        
        # --- PERMANENT CACHE CHECK ---
        if channel_url in st.session_state.seen_youtube_channels:
            continue

        stats = item.get('statistics', {})
        snippet = item.get('snippet', {})
        
        subs = int(stats.get('subscriberCount', 0))
        views = int(stats.get('viewCount', 0))
        video_count = int(stats.get('videoCount', 0))
        about_text = snippet.get('description', '')

        # Filter 1: Subscriber Range
        if not (min_subs <= subs <= max_subs):
            continue
            
        # Filter 2: Video Count Range
        if not (min_videos <= video_count <= max_videos):
            continue

        # Filter 3: Total View Count Range
        if not (min_views <= views <= max_views):
            continue

        # Filter 4: Keywords in the 'About' section
        if about_keyword_list:
            matches_about = any(word in about_text.lower() for word in about_keyword_list)
            if not matches_about:
                continue

        # Extract information metrics fields
        extracted_email = extract_email_from_text(about_text)
        extracted_link = extract_link_from_text(about_text)
        
        # Strict verification filtering validation checkpoints
        if require_email and extracted_email == "N/A":
            continue
            
        # UPGRADE: Strict URL payload data verification checkpoint step
        if require_link and extracted_link == "N/A":
            continue

        # Commit entry into history tracking configurations
        st.session_state.seen_youtube_channels.add(channel_url)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{channel_url}\n")

        channels_data.append({
            "Channel Name": snippet.get('title', 'Unknown'),
            "Email Address": extracted_email,
            "Website/Social Link": extracted_link,
            "Subscriber Count": subs,
            "Total View Count": views,
            "Videos Uploaded": video_count,
            "Country Profile": snippet.get('country', 'N/A'),
            "About Snippet": about_text[:150] + "..." if len(about_text) > 150 else about_text,
            "Channel Link": channel_url
        })
        
        if len(channels_data) >= limit:
            break
                
    return pd.DataFrame(channels_data)

# =====================
# SIDEBAR NAVIGATION
# =====================
with streamlit_analytics.track():
    with st.sidebar:
        st.header("🔑 Google API Token")
        api_token = st.text_input("YouTube Data API Key", type="password", help="Obtain a v3 API key from Google Cloud Console.")
        
        st.divider()
        st.header("📊 Delivery Destination")
        user_gsheet_url = st.text_input("Google Apps Script URL", placeholder="https://script.google.com/...")
        
        st.divider()
        st.markdown(f"📦 **Permanent Memory History:** `{len(st.session_state.seen_youtube_channels)}` channels remembered.")
        
        start_button = st.button("🚀 Harvest YouTube Channels", use_container_width=True)

    # =========================================================================
    # WORKSPACE LAYOUT
    # =========================================================================

    # Row 1: Target Parameters
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        keyword_input = st.text_input("Niche Main Keyword", "Cooking")
    with row1_col2:
        region_input = st.text_input("ISO Country Code Filter", "US")
    with row1_col3:
        limit_total = st.number_input("Maximum Results Requested", min_value=1, max_value=50, value=15)

    st.divider()

    # Row 2: Audience Metrics Floors & Ceilings
    st.subheader("Granular Metrics Filter Configuration")
    c1, c2 = st.columns(2)
    with c1:
        min_subs_input = st.number_input("Minimum Subscribers", min_value=0, value=10000, step=1000)
        min_videos_input = st.number_input("Total Videos (Min)", min_value=0, value=50, step=10)
        min_views_input = st.number_input("Minimum Total Views", min_value=0, value=100000, step=25000)
    with c2:
        max_subs_input = st.number_input("Maximum Subscribers", min_value=0, value=2000000, step=100000)
        max_videos_input = st.number_input("Total Videos (Max)", min_value=0, value=5000, step=100)
        max_views_input = st.number_input("Maximum Total Views", min_value=0, value=500000000, step=1000000)

    st.divider()

    # Row 3: Advanced Data Filtering & Parsing Matrix
    st.subheader("Advanced Data Filtering & Parsing Matrix")
    about_keywords_input = st.text_input("Keywords to search in Channel 'About'", placeholder="e.g. email, sponsorship, pr, review (comma-separated)")

    # UPGRADE: Placed the checkboxes side-by-side cleanly using a sub-column row matrix layout
    col_check1, col_check2 = st.columns(2)
    with col_check1:
        only_email_toggle = st.checkbox("Strict Verification: Only return channels with an identified email address", value=False)
    with col_check2:
        only_link_toggle = st.checkbox("Strict Verification: Only return channels with an identified Website/Social Link", value=False)

    # Scraper Execution Pipeline
    if start_button:
        if not api_token:
            st.error("Please supply a valid YouTube API Key in the sidebar.")
        elif min_subs_input >= max_subs_input:
            st.error("The minimum subscriber threshold must be less than the maximum ceiling threshold.")
        elif min_videos_input >= max_videos_input:
            st.error("The minimum video count threshold must be less than the maximum video count threshold.")
        elif min_views_input >= max_views_input:
            st.error("The minimum views threshold must be less than the maximum views threshold.")
        else:
            with st.spinner("Quizzing official YouTube database infrastructure..."):
                try:
                    df_results = fetch_youtube_channels(
                        api_token,
                        keyword_input,
                        region_input.upper().strip(),
                        min_subs_input,
                        max_subs_input,
                        min_videos_input,
                        max_videos_input,
                        min_views_input,
                        max_views_input,
                        about_keywords_input,
                        only_email_toggle,
                        only_link_toggle,
                        limit_total
                    )
                    
                    if df_results.empty:
                        st.warning("No new creators matched your specific layer combination of metrics filters and text criteria.")
                    else:
                        df_results["Creator Tier"] = df_results["Subscriber Count"].apply(get_channel_tier)
                        df_sorted = df_results.sort_values(by="Subscriber Count", ascending=False)
                        
                        # Styled Metrics Summary Row
                        m1, m2 = st.columns(2)
                        with m1:
                            st.markdown(f"""
                                <div class="yt-metric-card">
                                    <div class="yt-card-label">Pipelines Compiled</div>
                                    <div class="yt-card-value">📹 {len(df_sorted)} New Channels Found</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with m2:
                            avg_subs = int(df_sorted["Subscriber Count"].mean())
                            st.markdown(f"""
                                <div class="yt-metric-card">
                                    <div class="yt-card-label">Average Subscriber Base</div>
                                    <div class="yt-card-value">📊 {avg_subs:,} Subs</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        st.success(f"Successfully compiled {len(df_sorted)} verified creator pipelines!")
                        st.dataframe(df_sorted, use_container_width=True)
                        
                        if user_gsheet_url:
                            with st.spinner("Streaming records to Sheets architecture..."):
                                requests.post(user_gsheet_url, json=df_sorted.to_dict(orient='records'))
                                st.success("✅ Shared Google Sheet synchronized!")
                        
                        csv_data = df_sorted.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Filtered Directory (CSV)", csv_data, "youtube_fully_filtered_leads.csv")
                        
                except Exception as e:
                    st.error(f"API Interface Error: {e}")
