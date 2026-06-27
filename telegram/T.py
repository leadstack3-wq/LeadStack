import streamlit as st
import pandas as pd
import asyncio
import requests
import os
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest

# ==========================================
# 🎨 STREAMLIT PAGE CONFIG & TELEGRAM THEME
# ==========================================
st.set_page_config(page_title="Leadstack Telegram", layout="wide", page_icon="✉️")

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
    background: linear-gradient(135deg, #F0F6FC 0%, #FAFAFA 100%) !important;
    color: #24292E !important;
}
h1, h2, h3, .stMarkdown {
    color: #1F74B4 !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 14px;
    padding: 10px 0;
}
.stTabs [data-baseweb="tab"] {
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
    padding: 10px 18px !important;
    border-radius: 10px !important;
    background: rgba(36, 161, 222, 0.06) !important;
    border: 1px solid rgba(36, 161, 222, 0.15) !important;
    color: #24A1DE !important;
    margin-right: 6px;
    transition: all 0.25s ease;
}
.stTabs [data-baseweb="tab-highlight-container"] {
    background-color: #24A1DE !important;
}
.stTabs [role="tablist"] + div {
    background-color: #24A1DE !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #24A1DE, #147CB0) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(36, 161, 222, 0.25) !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #E8F4FA 100%) !important;
    border-right: 1px solid rgba(36, 161, 222, 0.15);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
    color: #147CB0 !important;
}
div[data-baseweb="input"] input, 
div[data-baseweb="input"] textarea,
.stNumberInput input {
    background: linear-gradient(135deg, #F0F6FC 0%, #E8F4FA 100%) !important;
    color: #24292E !important;
    border: 1px solid rgba(36, 161, 222, 0.3) !important;
    border-radius: 10px !important;
}
div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(36, 161, 222, 0.2) !important;
    box-shadow: 0 4px 12px rgba(36, 161, 222, 0.04) !important;
    border-radius: 12px;
    padding: 14px;
}
.stButton > button {
    background: linear-gradient(90deg, #24A1DE, #147CB0) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 10px 20px !important;
    box-shadow: 0 4px 12px rgba(36, 161, 222, 0.15) !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(36, 161, 222, 0.25) !important;
}
.block-container {
    padding-top: 0rem !important;
    max-width: 1400px;
}
div[data-testid="stDataFrame"] {
    background-color: #FFFFFF !important;
    border: 1px solid rgba(36, 161, 222, 0.15);
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.01);
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# --- Header Presentation Block ---
st.markdown(
    "<div style='padding:22px; border-radius:18px;"
    "background: linear-gradient(90deg, #24A1DE, #147CB0);"
    "color: white; margin-bottom: 1.5rem; box-shadow: 0 6px 20px rgba(36,161,222,0.2);'>"
    "<h1 style='margin:0; color:#FFFFFF !important; font-size:28px;'>✉️ Telegram Leads Generator</h1>"
    "<p style='margin:5px 0 0 0; color:#FFFFFF !important; opacity:0.95; font-size:15px;'>Headless community mapping & engagement behavior analytics hub</p>"
    "</div>",
    unsafe_allow_html=True
)

# =========================================================
# PER-USER SESSION & HISTORY FILE NAMING
# =========================================================
# Each visitor gets their own Telethon session file and dedup history file,
# derived from their own phone number. This keeps one person's logged-in
# Telegram account, and one person's "already scraped" history, fully
# isolated from everyone else using this app -- the same way each person's
# own YouTube API key never touches anyone else's quota or results.
import hashlib

DATA_DIR = "."

def get_user_session_name(phone):
    """Unique, filesystem-safe Telethon session filename, scoped to one phone number."""
    digest = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16]
    return os.path.join(DATA_DIR, f"session_{digest}")

def get_user_history_file(phone):
    """Unique dedup-history file, scoped to one phone number."""
    digest = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16]
    return os.path.join(DATA_DIR, f"seen_leads_{digest}.txt")

# ==========================================
# 📊 UTILITIES & TIERING SCHEMAS
# ==========================================
def get_channel_tier(sub_count):
    if sub_count >= 100000: return "📢 Broadcast Network"
    if sub_count >= 20000: return "👥 Large Community"
    if sub_count >= 5000: return "🎯 Target Hub"
    return "🌱 Micro Niche"

def get_engagement_tier(msg_count):
    if msg_count >= 50: return "🔥 Super Fan / Hyperactive"
    if msg_count >= 15: return "💬 Frequent Contributor"
    return "👀 Casual Participant"

def get_channel_engagement_tier(comments_count):
    if comments_count >= 15: return "🔥 Mega Commenter / Fan"
    if comments_count >= 5: return "💬 Active Discussant"
    return "👀 Casual Observer"

def get_async_loop():
    """
    Returns a single, persistent event loop cached for the lifetime of the
    Streamlit session. Creating a brand-new loop on every script rerun (the
    original approach) causes Telethon connections to intermittently break
    with 'event loop is closed' / 'no current event loop' errors, since each
    rerun is a fresh synchronous execution, not a continuation of a coroutine.
    """
    if "_telethon_loop" not in st.session_state:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        st.session_state["_telethon_loop"] = loop
    return st.session_state["_telethon_loop"]

# ==========================================
# 📊 SIDEBAR MANUAL CODES MATRIX
# ==========================================
with st.sidebar:
    st.header("Step 1: Master API Keys")
    user_api_id_raw = st.text_input("API ID", placeholder="e.g. 123456")
    user_api_hash = st.text_input("API Hash", type="password")
    user_phone = st.text_input("Account Phone Number", placeholder="+1234567890")

    st.divider()

    st.header("Step 2: Session Security Activation")
    request_code_btn = st.button("📨 Request Verification Code", use_container_width=True)
    login_code = st.text_input("Telegram 5-Digit Code", placeholder="12345", type="password")
    submit_auth_btn = st.button("🔐 Complete Web Authentication", use_container_width=True)

    user_api_id = int(user_api_id_raw) if (user_api_id_raw and user_api_id_raw.isdigit()) else 0
    loop = get_async_loop()

    # Every credential, session file, and dedup history below is keyed off
    # this phone number -- so each visitor only ever touches their own
    # Telegram login and their own "already scraped" history, never anyone
    # else's, even if many people use this app at the same time.
    SESSION_NAME = get_user_session_name(user_phone) if user_phone else None
    HISTORY_FILE = get_user_history_file(user_phone) if user_phone else None

    if user_phone and "seen_telegram_leads" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.seen_telegram_leads = set(line.strip() for line in f if line.strip())
        else:
            st.session_state.seen_telegram_leads = set()
    elif "seen_telegram_leads" not in st.session_state:
        st.session_state.seen_telegram_leads = set()

    if request_code_btn:
        if user_api_id == 0 or not user_api_hash or not user_phone:
            st.error("API ID, API Hash, and Phone Number are mandatory to request a code.")
        else:
            async def send_code():
                c = TelegramClient(SESSION_NAME, user_api_id, user_api_hash)
                await c.connect()
                await c.send_code_request(user_phone)
                await c.disconnect()
            try:
                loop.run_until_complete(send_code())
                st.info("📩 Login code transmitted! Check your Telegram app.")
            except Exception as e:
                st.error(f"Request Failure: {e}")

    if submit_auth_btn:
        if not login_code.strip():
            st.error("Please fill in the 5-digit verification code field.")
        else:
            async def complete_login():
                c = TelegramClient(SESSION_NAME, user_api_id, user_api_hash)
                await c.connect()
                await c.sign_in(user_phone, login_code.strip())
                await c.disconnect()
            try:
                loop.run_until_complete(complete_login())
                st.success("🟢 Web Session Authorized! You can now scrape across all workspace routes.")
            except Exception as e:
                st.error(f"Sign-In Error: {e}")

    st.divider()
    st.header("📊 Pipeline Sync")
    user_gsheet_url = st.text_input("Google Apps Script URL", placeholder="https://script.google.com/...")

    st.divider()
    st.markdown(f"📦 **Permanent Memory History:** `{len(st.session_state.seen_telegram_leads)}` unique targets remembered.")

# ==========================================
#⚡ CORE TELEGRAM ASYNC LEAD EXTRACTION LOOPS
# ==========================================
async def harvest_telegram_leads(api_id, api_hash, session_name, history_file, keyword, min_subs, max_subs, limit):
    async def run():
        search_results = await client(SearchRequest(q=keyword, limit=limit * 5))
        leads_data = []
        for peer in search_results.results:
            if len(leads_data) >= limit: break
            try:
                entity = await client.get_entity(peer)
                
                # Create a unique verification identifier string for global tracking
                unique_id = f"directory_{entity.id}"
                if unique_id in st.session_state.seen_telegram_leads:
                    continue

                if hasattr(entity, 'broadcast') or hasattr(entity, 'megagroup'):
                    full_info = await client(GetFullChannelRequest(channel=entity))
                    sub_count = full_info.full_chat.participants_count
                    about_text = full_info.full_chat.about if full_info.full_chat.about else ""
                    if min_subs <= sub_count <= max_subs:
                        # Commit identifier permanently to file structures
                        st.session_state.seen_telegram_leads.add(unique_id)
                        with open(history_file, "a", encoding="utf-8") as f:
                            f.write(f"{unique_id}\n")

                        leads_data.append({
                            "Community Name": entity.title,
                            "Telegram Username": f"@{entity.username}" if entity.username else "Private/Link Only",
                            "Channel/Group Type": "📢 Channel" if getattr(entity, 'broadcast', False) else "💬 Megagroup",
                            "Subscriber Count": sub_count,
                            "About Bio Description": about_text[:150] + "..." if len(about_text) > 150 else about_text,
                            "Direct Join Link": f"https://t.me/{entity.username}" if entity.username else "N/A"
                        })
            except: continue
        return pd.DataFrame(leads_data)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    res_df = await run()
    await client.disconnect()
    return res_df

async def mine_top_engagers(api_id, api_hash, session_name, history_file, target_group, message_limit):
    async def run():
        try: group_entity = await client.get_entity(target_group)
        except Exception as e: return pd.DataFrame()
        user_message_counts = {}
        user_profiles = {}
        async for message in client.iter_messages(group_entity, limit=message_limit):
            if message.sender_id and message.sender:
                sender = message.sender
                user_id = message.sender_id
                if getattr(sender, 'bot', False): continue
                
                # Contextual unique identifier layout to isolate a user inside a distinct scope
                unique_id = f"group_{group_entity.id}_user_{user_id}"
                if unique_id in st.session_state.seen_telegram_leads:
                    continue

                user_message_counts[user_id] = user_message_counts.get(user_id, 0) + 1
                if user_id not in user_profiles:
                    first_name = getattr(sender, 'first_name', '') or ''
                    last_name = getattr(sender, 'last_name', '') or ''
                    full_name = f"{first_name} {last_name}".strip()
                    user_profiles[user_id] = {
                        "User Name": full_name if full_name else "Anonymous Member",
                        "Telegram Handle": f"@{sender.username}" if sender.username else "No Public Handle",
                        "Phone Contact": f"+{sender.phone}" if getattr(sender, 'phone', None) else "Hidden",
                        "User ID": user_id,
                        "MemKey": unique_id
                    }
        engager_list = []
        for user_id, count in user_message_counts.items():
            profile = user_profiles[user_id]
            
            # Commit unique contact targets to local persistence system
            st.session_state.seen_telegram_leads.add(profile["MemKey"])
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(f"{profile['MemKey']}\n")

            engager_list.append({
                "Lead Name": profile["User Name"],
                "Telegram Handle": profile["Telegram Handle"],
                "Messages Sent": count,
                "Phone": profile["Phone Contact"],
                "User ID": profile["User ID"],
                "Source Group": group_entity.title
            })
        return pd.DataFrame(engager_list)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    res_df = await run()
    await client.disconnect()
    return res_df

async def mine_channel_engagers(api_id, api_hash, session_name, history_file, target_channel, post_limit):
    async def run():
        try: channel_entity = await client.get_entity(target_channel)
        except Exception as e: return pd.DataFrame()
        user_comment_counts = {}
        user_profiles = {}
        async for message in client.iter_messages(channel_entity, limit=post_limit):
            if message.replies and message.replies.replies > 0:
                try:
                    async for reply in client.iter_replies(message):
                        if reply.sender_id and reply.sender:
                            sender = reply.sender
                            user_id = reply.sender_id
                            if getattr(sender, 'bot', False): continue
                            
                            # Distinct channel user tracking matrix checkpoint boundary
                            unique_id = f"channel_{channel_entity.id}_user_{user_id}"
                            if unique_id in st.session_state.seen_telegram_leads:
                                continue

                            user_comment_counts[user_id] = user_comment_counts.get(user_id, 0) + 1
                            if user_id not in user_profiles:
                                f_name = getattr(sender, 'first_name', '') or ''
                                l_name = getattr(sender, 'last_name', '') or ''
                                full_name = f"{f_name} {l_name}".strip()
                                user_profiles[user_id] = {
                                    "Name": full_name if full_name else "Channel Reader",
                                    "Handle": f"@{sender.username}" if sender.username else "Hidden Handle",
                                    "Phone": f"+{sender.phone}" if getattr(sender, 'phone', None) else "Hidden",
                                    "MemKey": unique_id
                                }
                except: continue
        channel_leads = []
        for user_id, count in user_comment_counts.items():
            profile = user_profiles[user_id]
            
            # Commit identifier permanently to block future sweeps tracking this exact commenter
            st.session_state.seen_telegram_leads.add(profile["MemKey"])
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(f"{profile['MemKey']}\n")

            channel_leads.append({
                "Lead Name": profile["Name"],
                "Telegram Handle": profile["Handle"],
                "Total Comments Tracked": count,
                "Phone": profile["Phone"],
                "User ID": user_id,
                "Source Channel": channel_entity.title
            })
        return pd.DataFrame(channel_leads)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    res_df = await run()
    await client.disconnect()
    return res_df


# Workspace Tabs
tab_directory, tab_group, tab_channel = st.tabs([
    "🛡️ Global Directory Search",
    "💬 Group Chat Engagers", 
    "📢 Channel Commenters"
])

# ------------------------------------------
# TAB 1: DIRECTORY SEARCH
# ------------------------------------------
with tab_directory:
    st.subheader("Global Discovery and Filtering Matrix")
    c1, c2 = st.columns(2)
    with c1:
        keyword_input = st.text_input("Search Term / Niche Keyword", "Crypto Signals", key="d_key")
        min_subs_input = st.number_input("Minimum Subscriber Floor", min_value=0, value=1000, step=500, key="d_min")
    with c2:
        limit_total = st.number_input("Max Clean Entries Saved", min_value=1, max_value=100, value=15, key="d_limit")
        max_subs_input = st.number_input("Maximum Subscriber Cap", min_value=0, value=500000, step=10000, key="d_max")
        
    start_dir_btn = st.button("🚀 Scrape Directory Indices", use_container_width=True)
    
    if start_dir_btn:
        if user_api_id == 0 or not user_api_hash or not user_phone:
            st.error("Please configure your master Telegram API credentials completely in the sidebar.")
        elif min_subs_input >= max_subs_input:
            st.error("Minimum subscriber floor limit must be strictly lower than your maximum cap.")
        else:
            with st.spinner("Establishing background connection to Telegram directory matrix..."):
                try:
                    loop = get_async_loop()
                    df_leads = loop.run_until_complete(
                        harvest_telegram_leads(user_api_id, user_api_hash, SESSION_NAME, HISTORY_FILE, keyword_input, min_subs_input, max_subs_input, limit_total)
                    )
                    if df_leads.empty:
                        st.warning("No new directories matched your parameters or your distributed collection range is already captured.")
                    else:
                        df_leads["Market Reach Tier"] = df_leads["Subscriber Count"].apply(get_channel_tier)
                        df_sorted = df_leads.sort_values(by="Subscriber Count", ascending=False)
                        st.success(f"Successfully scraped {len(df_sorted)} verified target hubs!")
                        st.dataframe(df_sorted, use_container_width=True)
                        if user_gsheet_url:
                            requests.post(user_gsheet_url, json=df_sorted.to_dict(orient='records'))
                        csv_bytes = df_sorted.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Telegram Database (CSV)", csv_bytes, "tg_market_leads.csv", key="d_dl")
                except Exception as e:
                    st.error(f"Mainframe Protocol Exception: {e}")

# ------------------------------------------
# TAB 2: GROUP CHAT MINER
# ------------------------------------------
with tab_group:
    st.subheader("Extract Most Active Members from Public Chats")
    col_target, col_depth = st.columns(2)
    with col_target:
        group_input = st.text_input("Target Group Username / Link", placeholder="e.g. @CryptoGroup or t.me/joinchat...", key="g_input")
    with col_depth:
        message_depth = st.number_input("Message History Scan Depth", min_value=100, max_value=10000, value=1000, step=500, key="g_depth")
        
    start_group_btn = st.button("🚀 Extract Interactive Engagers", use_container_width=True)
    
    if start_group_btn:
        if user_api_id == 0 or not user_api_hash or not user_phone or not group_input:
            st.error("Please fill out your master sidebar credentials and target group input.")
        else:
            with st.spinner("Mining message database nodes anonymously..."):
                try:
                    loop = get_async_loop()
                    df_engagers = loop.run_until_complete(
                        mine_top_engagers(user_api_id, user_api_hash, SESSION_NAME, HISTORY_FILE, group_input.strip(), message_depth)
                    )
                    if df_engagers.empty:
                        st.warning("No new active human engagers found or session authentication failed.")
                    else:
                        df_engagers["Engagement Status"] = df_engagers["Messages Sent"].apply(get_engagement_tier)
                        df_sorted = df_engagers.sort_values(by="Messages Sent", ascending=False)
                        st.success(f"Successfully ranked {len(df_sorted)} unique active engagers!")
                        st.dataframe(df_sorted, use_container_width=True)
                        if user_gsheet_url:
                            requests.post(user_gsheet_url, json=df_sorted.to_dict(orient='records'))
                        csv_bytes = df_sorted.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Top Engagers List", csv_bytes, "tg_top_group_engagers.csv", key="g_dl")
                except Exception as e:
                    st.error(f"Network Mainframe Exception: {e}")

# ------------------------------------------
# TAB 3: CHANNEL COMMENT MINER
# ------------------------------------------
with tab_channel:
    st.subheader("Harvest Leads Tracking Broadcast Reply Threads")
    col_chan, col_posts = st.columns(2)
    with col_chan:
        channel_input = st.text_input("Target Channel Username / Link", placeholder="e.g. @TechCrunch or t.me/niche_channel", key="c_input")
    with col_posts:
        posts_to_scan = st.number_input("Broadcast Posts Scan Depth", min_value=5, max_value=100, value=20, step=5, key="c_posts")
        
    start_channel_btn = st.button("🚀 Extract Broadcast Commenters", use_container_width=True)
    
    if start_channel_btn:
        if user_api_id == 0 or not user_api_hash or not user_phone or not channel_input:
            st.error("Please fill out your master sidebar credentials and target channel input.")
        else:
            with st.spinner("Traversing channel comment database branches..."):
                try:
                    loop = get_async_loop()
                    df_channel_leads = loop.run_until_complete(
                        mine_channel_engagers(user_api_id, user_api_hash, SESSION_NAME, HISTORY_FILE, channel_input.strip(), posts_to_scan)
                    )
                    if df_channel_leads.empty:
                        st.warning("No new public active commenters detected in the specified post range.")
                    else:
                        df_channel_leads["Fan Intensity"] = df_channel_leads["Total Comments Tracked"].apply(get_channel_engagement_tier)
                        df_sorted = df_channel_leads.sort_values(by="Total Comments Tracked", ascending=False)
                        st.success(f"Successfully prioritized {len(df_sorted)} target channel leads!")
                        st.dataframe(df_sorted, use_container_width=True)
                        if user_gsheet_url:
                            requests.post(user_gsheet_url, json=df_sorted.to_dict(orient='records'))
                        csv_bytes = df_sorted.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Export Channel Engagers (CSV)", csv_bytes, "tg_channel_commenters.csv", key="c_dl")
                except Exception as e:
                    st.error(f"Network Protocol Exception: {e}")