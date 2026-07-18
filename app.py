import streamlit as st
import pandas as pd
import altair as alt
import requests
import re
import datetime
from io import StringIO

# ページの設定
st.set_page_config(page_title="HydroVane ULTRA PRO", layout="wide")

# 🎨 ダークネイビー×レーンカラーのカスタムテーマ(最初のプロトタイプのテイストに合わせる)
st.markdown("""
<style>
    .stApp {
        background-color: #0B2233;
        color: #EAF2F5;
    }
    section[data-testid="stSidebar"] {
        background-color: #122E43;
        border-right: 1px solid #234A63;
    }
    section[data-testid="stSidebar"] * {
        color: #EAF2F5 !important;
    }
    h1, h2, h3, h4 {
        color: #EAF2F5 !important;
    }
    .stMarkdown, .stCaption, p, span, label {
        color: #EAF2F5;
    }
    div[data-testid="stMetric"], .stDataFrame, .stAlert {
        background-color: #122E43 !important;
        border-radius: 8px;
    }
    .stButton > button, .stLinkButton > a {
        background-color: #1856A8 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stButton > button:hover, .stLinkButton > a:hover {
        background-color: #2270CC !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #7FB3CC;
    }
    .stTabs [aria-selected="true"] {
        color: #EAF2F5 !important;
        border-bottom-color: #5FA8C9 !important;
    }
    code, .stCode {
        font-family: 'Courier New', monospace;
    }
    .hv-eyebrow {
        font-size: 12px;
        letter-spacing: 0.18em;
        color: #5FA8C9;
        font-family: 'Courier New', monospace;
        margin-bottom: 4px;
    }
    .hv-card {
        background: #122E43;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .hv-card.is-top {
        background: #173F58;
        border: 1px solid #3E8FB0;
    }
    .hv-lane-chip {
        display: inline-flex;
        width: 32px;
        height: 32px;
        border-radius: 7px;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .hv-card-name {
        font-size: 14px;
        font-weight: 700;
        margin-top: 4px;
    }
    .hv-card-reason {
        font-size: 12px;
        color: #7FB3CC;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

LANE_BG = {1: "#F5F5F0", 2: "#1A1A1A", 3: "#D6331C", 4: "#1856A8", 5: "#F2C316", 6: "#1E8A4C"}
LANE_FG = {1: "#1A1A1A", 2: "#F5F5F0", 3: "#FFFFFF", 4: "#FFFFFF", 5: "#1A1A1A", 6: "#FFFFFF"}

st.markdown('<div class="hv-eyebrow">HYDROVANE — REAL-TIME TACTICAL PREDICTOR</div>', unsafe_allow_html=True)

st.title("⚡ HydroVane ULTRA PRO : Real-Time Tactical Predictor")
st.markdown("*📊 出走表 × 直前情報 × 場別コース率 完全自動取得システム*")
st.markdown("---")

# ============================================================
# 🔌 データ取得部(公式サイトから自動取得。コピペ不要)
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.boatrace.jp/",
}


def split_multi(s):
    return re.split(r"\s{2,}", str(s).strip())


def zen2han(s):
    table = str.maketrans("０１２３４５６７８９", "0123456789")
    return str(s).translate(table)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_racelist(jcd, hd, rno):
    """出走表: 選手名・級別・全国/当地成績・モーター/ボート成績"""
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd:02d}&hd={hd}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding

    tables = pd.read_html(StringIO(res.text))
    raw = tables[1].iloc[::4].reset_index(drop=True)

    rows = []
    for i in range(len(raw)):
        r = raw.iloc[i]
        name_parts = split_multi(r.iloc[2])   # [登録番号, 級別, 氏名, 支部/出身地, 年齢/体重]
        zenkoku = split_multi(r.iloc[4])       # [全国勝率, 全国2連率, 全国3連率]
        touchi = split_multi(r.iloc[5])        # [当地勝率, 当地2連率, 当地3連率]
        motor = split_multi(r.iloc[6])         # [モーターNo, モーター2連率, モーター3連率]
        boat = split_multi(r.iloc[7])          # [ボートNo, ボート2連率, ボート3連率]

        grade = name_parts[1].replace("/", "").strip() if len(name_parts) > 1 else ""

        rows.append({
            "号艇": int(zen2han(r.iloc[0])),
            "登録番号": name_parts[0].strip() if len(name_parts) > 0 else "",
            "選手名": name_parts[2] if len(name_parts) > 2 else "不明",
            "級別": grade,
            "全国勝率": float(zenkoku[0]) if len(zenkoku) > 0 else 0.0,
            "全国2連": float(zenkoku[1]) if len(zenkoku) > 1 else 0.0,
            "全国3連": float(zenkoku[2]) if len(zenkoku) > 2 else 0.0,
            "当地勝率": float(touchi[0]) if len(touchi) > 0 else 0.0,
            "当地2連": float(touchi[1]) if len(touchi) > 1 else 0.0,
            "当地3連": float(touchi[2]) if len(touchi) > 2 else 0.0,
            "モーター2連": float(motor[1]) if len(motor) > 1 else 0.0,
            "モーター3連": float(motor[2]) if len(motor) > 2 else 0.0,
            "ボート2連": float(boat[1]) if len(boat) > 1 else 0.0,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_beforeinfo(jcd, hd, rno):
    """直前情報: 体重・展示タイム・チルト・部品交換・展示ST・F有無"""
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd:02d}&hd={hd}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    tables = pd.read_html(StringIO(res.text))

    t1 = tables[1].iloc[::4].reset_index(drop=True)
    rows = []
    for i in range(len(t1)):
        r = t1.iloc[i]
        weight_text = str(r.iloc[3]).replace("kg", "").strip()
        try:
            weight = float(weight_text)
        except ValueError:
            weight = None
        parts_text = str(r.iloc[7]).strip()
        parts_text = "なし" if parts_text.lower() in ("nan", "none", "") else parts_text

        rows.append({
            "号艇": int(zen2han(r.iloc[0])),
            "体重": weight,
            "展示タイム": pd.to_numeric(r.iloc[4], errors="coerce"),
            "チルト": pd.to_numeric(r.iloc[5], errors="coerce"),
            "部品交換": parts_text,
        })
    ex_df = pd.DataFrame(rows)

    # 直前情報がまだ発表前だと、スタート展示の表(3枚目)が存在しないことがある
    if len(tables) < 3:
        ex_df["展示ST"] = None
        ex_df["展示F"] = 0
        return ex_df

    t2 = tables[2]
    starts = []
    for i in range(len(t2)):
        parts = split_multi(t2.iloc[i, 0])
        if len(parts) >= 2:
            printed_course = int(parts[0])  # 展示スタートで実際に予想される進入コース(号艇とは限らない)
            raw_st = parts[1]
            is_f = "F" in raw_st
            st_text = re.sub(r"[FL]", "", raw_st)
            if st_text.startswith("."):
                st_text = "0" + st_text
            try:
                st_val = float(st_text)
            except ValueError:
                st_val = None
            # この表の行の並び順が号艇(1〜6)順であることを利用
            starts.append({
                "号艇": i + 1,
                "進入コース": printed_course,
                "展示ST": st_val,
                "展示F": 1 if is_f else 0,
            })
    st_df = pd.DataFrame(starts)

    merged = ex_df.merge(st_df, on="号艇", how="left")
    merged["進入コース"] = merged["進入コース"].fillna(merged["号艇"])
    return merged


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_course_rate(jcd):
    """場別・コース別の直近3ヶ月の1着率と決まり手内訳"""
    url = f"https://www.boatrace.jp/owpc/pc/data/stadium?jcd={jcd:02d}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    tables = pd.read_html(StringIO(res.text))
    t0 = tables[0]

    cols = ["号艇", "コース1着率", "c2", "c3", "c4", "c5", "c6",
            "逃げ率", "捲り率", "差し率", "捲り差し率", "抜き率", "恵まれ率"]
    df = t0.iloc[:, 0:len(cols)].copy()
    df.columns = cols
    df["号艇"] = pd.to_numeric(df["号艇"], errors="coerce").astype(int)
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    keep = ["号艇", "コース1着率", "逃げ率", "捲り率", "差し率", "捲り差し率", "抜き率", "恵まれ率"]
    return df[keep]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_racer_course_stats(toban, course):
    """選手個人のコース別成績(3連対率・平均ST)。取れない場合はNoneを返す"""
    try:
        url = f"https://www.boatrace.jp/owpc/pc/data/racersearch/course?toban={toban}"
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        res.encoding = res.apparent_encoding
        tables = pd.read_html(StringIO(res.text))

        # 表の並びは[進入率, 3連対率, 平均ST, スタート順]の想定
        # コース列(1列目)がcourseと一致する行を探す
        def find_value(table_index):
            t = tables[table_index]
            t.columns = ["course", "value"]
            t["course"] = pd.to_numeric(t["course"], errors="coerce")
            match = t[t["course"] == course]
            if len(match) == 0:
                return None
            val = str(match.iloc[0]["value"]).replace("%", "").strip()
            try:
                return float(val)
            except ValueError:
                return None

        rentai = find_value(1) if len(tables) > 1 else None
        avg_st = find_value(2) if len(tables) > 2 else None
        return {"選手コース3連対率": rentai, "選手コース平均ST": avg_st}
    except Exception:
        return {"選手コース3連対率": None, "選手コース平均ST": None}



@st.cache_data(ttl=60, show_spinner=False)
def fetch_weather(jcd, hd, rno):
    """水面気象情報: 気温・天候・風速・水温・波高(風向きは画像アイコンのため取得不可)"""
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd:02d}&hd={hd}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(res.text, "html5lib")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)

    result = {"気温": None, "天候": None, "風速": None, "水温": None, "波高": None}

    m = re.search(r"気温\s*([\d.]+)\s*℃", text)
    if m:
        result["気温"] = float(m.group(1))

    m = re.search(r"℃\s*(\S+?)\s*風速", text)
    if m:
        result["天候"] = m.group(1)

    m = re.search(r"風速\s*([\d.]+)\s*m", text)
    if m:
        result["風速"] = float(m.group(1))

    m = re.search(r"水温\s*([\d.]+)\s*℃", text)
    if m:
        result["水温"] = float(m.group(1))

    m = re.search(r"波高\s*([\d.]+)\s*cm", text)
    if m:
        result["波高"] = float(m.group(1))

    return result


def explain_boat(row, df_all):
    """その艇が上位に来た根拠を、目立つ指標から自動で文章化する"""
    reasons = []

    # コース1着率(場の平均より高いか)
    if pd.notna(row.get("コース1着率")) and pd.notna(df_all["コース1着率"]).any():
        if row["コース1着率"] >= df_all["コース1着率"].median():
            reasons.append(f"場別コース1着率{row['コース1着率']:.1f}%")

    # 選手個人のコース3連対率
    if pd.notna(row.get("選手コース3連対率")) and row["選手コース3連対率"] >= 50:
        reasons.append(f"当該コース3連対率{row['選手コース3連対率']:.1f}%")

    # モーター(2連・3連の平均)が高いか
    motor_avg = (row.get("モーター2連", 0) + row.get("モーター3連", 0)) / 2
    if motor_avg >= 40:
        reasons.append(f"モーター機力良好(2連{row.get('モーター2連', 0):.1f}%/3連{row.get('モーター3連', 0):.1f}%)")

    # 展示タイムの順位
    if pd.notna(row.get("展示順位")) and row["展示順位"] <= 2:
        reasons.append(f"展示タイム{int(row['展示順位'])}位")

    # ST差(スリットで先行しているか)
    if pd.notna(row.get("ST差")) and row["ST差"] <= 0.02:
        reasons.append("スタート先行")

    # 決まり手(2〜4号艇の差し・捲り系)
    if row.get("号艇") == 2 and pd.notna(row.get("差し率")) and row["差し率"] >= 40:
        reasons.append(f"差し決まり手率{row['差し率']:.1f}%")
    if row.get("号艇") in (3, 4) and pd.notna(row.get("捲り率")) and pd.notna(row.get("捲り差し率")):
        makuri_total = row["捲り率"] + row["捲り差し率"]
        if makuri_total >= 35:
            reasons.append(f"捲り系決まり手率{makuri_total:.1f}%")

    if not reasons:
        reasons.append("総合力で浮上")

    return "・".join(reasons)


VENUES = {
    "桐生": 1, "戸田": 2, "江戸川": 3, "平和島": 4, "多摩川": 5, "浜名湖": 6,
    "蒲郡": 7, "常滑": 8, "津": 9, "三国": 10, "びわこ": 11, "住之江": 12,
    "尼崎": 13, "鳴門": 14, "丸亀": 15, "児島": 16, "宮島": 17, "徳山": 18,
    "下関": 19, "若松": 20, "芦屋": 21, "福岡": 22, "唐津": 23, "大村": 24,
}

# ============================================================
# 🔍 サイドバー: レース選択 & 重み調整
# ============================================================

st.sidebar.header("🔍 レース選択")
selected_venue_name = st.sidebar.selectbox("開催場", list(VENUES.keys()), index=20)  # 芦屋を初期値に
jcd = VENUES[selected_venue_name]
selected_date = st.sidebar.date_input("日付", datetime.date.today())
race_no = st.sidebar.number_input("レース番号", min_value=1, max_value=12, value=1, step=1)
hd = selected_date.strftime("%Y%m%d")

st.sidebar.markdown("---")
st.sidebar.header("🌤️ WEATHER & WIND STATUS")
selected_wind_dir = st.sidebar.selectbox("風向き", ["無風・穏やか", "向かい風", "追い風", "右方向（横風）", "左方向（横風）"])
selected_wind_speed = st.sidebar.slider("風速 (m)", 0, 10, 2, step=1)

st.sidebar.markdown("---")
st.sidebar.header("📐 信頼度調整")
# 各要素の重み(場コース率・選手実績・勝率などは固定値。統計的に裏付けのあるスタート差のみ調整可能)
w_course = 0.25
w_racer_course = 0.20
w_win_rate = 0.15
w_ren_rate = 0.15
w_machinery = 0.10
w_exhibit = 0.15
w_st_gap = st.sidebar.slider("スタート差(実データ回帰)の信頼度", 0.0, 1.5, 1.0, step=0.1)
st.sidebar.caption("↑ 2026年6月の約4,600レース分析による実測値。1.0が実データそのままの強さです。他の要素は固定の重みで計算されます。")

st.markdown(f"### 選択中のレース: {selected_venue_name} {selected_date.strftime('%Y/%m/%d')} {race_no}R")

# ============================================================
# 🚀 実行
# ============================================================

if st.button("🚀 出走・直前・場データ 自動取得して予測", type="primary"):
    try:
        with st.spinner("公式サイトから出走表・直前情報・場データを取得中..."):
            df_race = fetch_racelist(jcd, hd, race_no)
            df_before = fetch_beforeinfo(jcd, hd, race_no)
            df_course = fetch_course_rate(jcd)

            df = df_race.merge(df_before, on="号艇", how="left")
            df = df.merge(df_course, left_on="進入コース", right_on="号艇", how="left", suffixes=("", "_course"))

        with st.spinner("選手個人のコース別成績を取得中..."):
            racer_stats = []
            for i in range(len(df)):
                row = df.iloc[i]
                stats = fetch_racer_course_stats(row["登録番号"], row.get("進入コース", row["号艇"]))
                stats["号艇"] = row["号艇"]
                racer_stats.append(stats)
            df_racer = pd.DataFrame(racer_stats)
            df = df.merge(df_racer, on="号艇", how="left")

        if df["展示タイム"].isna().all():
            st.info("直前情報はまだ発表されていないようです(締切のおよそ20分前から発表されます)。出走表のデータだけで計算します。")
            df["展示タイム"] = df["展示タイム"].fillna(6.85)
            df["チルト"] = df["チルト"].fillna(0.0)
            df["展示ST"] = df["展示ST"].fillna(0.17)
            df["展示F"] = df["展示F"].fillna(0)
            df["部品交換"] = df["部品交換"].fillna("なし")

        with st.spinner("水面気象情報を取得中..."):
            weather = fetch_weather(jcd, hd, race_no)
            st.session_state["weather"] = weather

        # ここでは取得と前処理までを行い、結果をsession_stateに保存する
        # (風向きなどのスコア計算は下で毎回re-runされるので、ここに含めない)
        st.session_state["df_raw"] = df
        st.session_state["race_label"] = f"{selected_venue_name} {selected_date.strftime('%Y/%m/%d')} {race_no}R"

    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {e}")
        st.caption("直前情報は締切の約20分前から発表されます。時間が早すぎる可能性もあります。")
        import traceback
        with st.expander("詳しいエラー内容(サポート用)"):
            st.code(traceback.format_exc())

# ============================================================
# 📊 スコア計算・表示部(session_stateにデータがあれば、
#     風向き・重みスライダーを動かすたびにここだけ再計算される)
# ============================================================

if "df_raw" in st.session_state:
    df = st.session_state["df_raw"].copy()
    st.caption(f"📌 表示中のレース: {st.session_state.get('race_label', '')} (データは保持されたままです)")

    weather = st.session_state.get("weather", {})
    wind = selected_wind_speed
    weather_note = ""
    official_url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={jcd:02d}&hd={hd}"
    if weather.get("風速") is not None:
        wind = weather["風速"]
        weather_note = (
            f"🌡️ 気温 {weather.get('気温', '—')}℃ / "
            f"{weather.get('天候', '—')} / "
            f"💨 風速 {weather.get('風速', '—')}m(自動取得) / "
            f"🌊 水温 {weather.get('水温', '—')}℃ / "
            f"波高 {weather.get('波高', '—')}cm"
        )
        st.info(weather_note)
        st.link_button("🧭 風向きだけ公式ページで確認する(このレースのページが開きます)", official_url)
    else:
        st.caption("水面気象情報が取得できなかったため、サイドバーの手動設定の風速を使用します。")

    # 展示タイム順位・ST差(実データの回帰係数を反映した連続式)
    # 2026年6月の約4,600レース分をロジスティック回帰した結果:
    #   展示タイム順位が1つ悪化 → 1着オッズがexp(-0.2118)倍
    #   ST差が0.1秒悪化      → 1着オッズがexp(-1.639)倍(非常に強い影響)
    # これをスコア(点数)に変換するため10倍して使用
    EX_RANK_COEF = -0.2118 * 10   # 順位1つあたりの点数
    ST_GAP_COEF = -16.39 * 10     # ST差1秒あたりの点数

    df["展示順位"] = df["展示タイム"].rank(ascending=True, method="min")
    df["展示スコア"] = df["展示順位"] * EX_RANK_COEF

    # 基礎戦術スコア
    score_course = df["コース1着率"].fillna(0) * w_course
    score_racer_course = df["選手コース3連対率"].fillna(df["全国2連"]) * w_racer_course * 0.1
    score_win = (df["全国勝率"] + df["当地勝率"]) * w_win_rate
    score_ren = ((df["全国2連"] + df["全国3連"] + df["当地2連"] + df["当地3連"]) / 4) * 0.1 * w_ren_rate
    score_machine = ((df["モーター2連"] + df["モーター3連"]) / 2) * 0.1 * w_machinery
    score_ex = df["展示スコア"] * w_exhibit

    df["総合スコア"] = score_course + score_racer_course + score_win + score_ren + score_machine + score_ex

    # 各種補正
    df.loc[df["チルト"] > 0, "総合スコア"] += 1.0
    df.loc[df["部品交換"] != "なし", "総合スコア"] -= 0.5
    df.loc[df["展示F"] == 1, "総合スコア"] -= 2.0  # 展示Fがあった艇は減点

    # 🥊 決まり手セオリー: この水面が「差されやすい/まくられやすい」かを反映
    kimarite_note = ""
    if df["差し率"].notna().any():
        c2 = df[df["進入コース"] == 2]
        c3 = df[df["進入コース"] == 3]
        c4 = df[df["進入コース"] == 4]
        sashi_2 = c2["差し率"].iloc[0] if len(c2) > 0 and pd.notna(c2["差し率"].iloc[0]) else 0
        makuri_3 = (c3["捲り率"].iloc[0] + c3["捲り差し率"].iloc[0]) if len(c3) > 0 else 0
        makuri_4 = (c4["捲り率"].iloc[0] + c4["捲り差し率"].iloc[0]) if len(c4) > 0 else 0

        # 差され警戒度が高い(2コースの差し率が高水面)場合、1コースをやや割り引き、2コースを評価
        if sashi_2 >= 40:
            df.loc[df["進入コース"] == 1, "総合スコア"] -= 1.0
            df.loc[df["進入コース"] == 2, "総合スコア"] += 1.2
            kimarite_note += f"🥊 この水面は2コースの『差し』決まり手率{sashi_2:.1f}%と高め、イン粘り切れない可能性あり。 "

        # まくられ警戒度が高い(3・4コースの捲り系決まり手率が高水面)場合
        if makuri_3 >= 40:
            df.loc[df["進入コース"].isin([1, 2]), "総合スコア"] -= 0.5
            df.loc[df["進入コース"] == 3, "総合スコア"] += 1.0
            kimarite_note += f"🥊 3コースの『捲り』系決まり手率{makuri_3:.1f}%、まくり・まくり差しに警戒。 "
        if makuri_4 >= 35:
            df.loc[df["進入コース"] == 4, "総合スコア"] += 0.8
            kimarite_note += f"🥊 4コースの『捲り』系決まり手率{makuri_4:.1f}%も無視できません。"

    # 🚤 スリット隊形分析(展示STベース・実データ係数): 競艇予想の核心とされる「1マーク展開」を反映
    slit_note = ""
    if df["展示ST"].notna().sum() >= 4:  # 最低限STが揃っている場合のみ分析
        fastest_st = df["展示ST"].min()
        df["ST差"] = df["展示ST"] - fastest_st

        # 実データの回帰係数をそのまま点数化(w_st_gapで信頼度を調整可能)
        df["総合スコア"] = df["総合スコア"] + df["ST差"] * ST_GAP_COEF * w_st_gap

        boat1_row = df[df["進入コース"] == 1]
        boat1_gap = boat1_row["ST差"].iloc[0] if len(boat1_row) > 0 and pd.notna(boat1_row["ST差"].iloc[0]) else None

        if boat1_gap is not None:
            if boat1_gap <= 0.02:
                slit_note = "🚤【スリット: 横一線】1コースのスタートが良く、イン逃げが濃厚な隊形です。"
            elif boat1_gap <= 0.05:
                slit_note = f"🚤【スリット: 軽い凹み(ST差{boat1_gap:.2f}秒)】1コースがわずかに遅れ気味。実データ上、この程度の差でも1着率はかなり下がる傾向です。"
            else:
                slit_note = f"🚤【スリット: イン大凹み(ST差{boat1_gap:.2f}秒)】1コースが大きく出遅れ。実データ上、1着の可能性はかなり低い水準まで落ちる差です。"

        boat2_row = df[df["進入コース"] == 2]
        boat2_gap = boat2_row["ST差"].iloc[0] if len(boat2_row) > 0 and pd.notna(boat2_row["ST差"].iloc[0]) else None
        if boat2_gap is not None and boat2_gap >= 0.05:
            slit_note += " 2コースの出も遅く、3コースの『まくり差し』が生きる形。"

    # 🌡️ 水温セオリー: 水温が低いとイン有利(出足が良くなる)、高いとアウトがやや有利
    water_temp = weather.get("水温")
    if water_temp is not None:
        if water_temp <= 15:
            # 内側(1〜3コース)を優遇
            df.loc[df["進入コース"].isin([1, 2, 3]), "総合スコア"] += 0.5
        elif water_temp >= 25:
            # 外側(4〜6コース)をわずかに優遇
            df.loc[df["進入コース"].isin([4, 5, 6]), "総合スコア"] += 0.3

    # ⚓ 荒天セオリー: 風速5m以上・波高5cm以上では体重が重い艇が安定しやすい
    wave_height = weather.get("波高")
    rough_water = wind >= 5 or (wave_height is not None and wave_height >= 5)
    if rough_water and df["体重"].notna().any():
        heavy_threshold = df["体重"].median()
        df.loc[df["体重"] >= heavy_threshold, "総合スコア"] += 0.8

    # 🌪️ 4方向風向き 特殊展開ロジック(セオリーに合わせて対象コースを拡張)
    tactical_alert = ""
    wind_dir = selected_wind_dir
    # wind(風速)は自動取得できていればそちらを、できていなければ手動設定を使用(上で設定済み)

    if wind >= 3:
        if wind_dir == "向かい風":
            # セオリー: 向かい風3m以上はアウト全体(3〜6コース)が有利
            df.loc[df["進入コース"] == 1, "総合スコア"] -= (wind * 0.2)
            df.loc[df["進入コース"].isin([3, 4, 5, 6]), "総合スコア"] += (wind * 0.12)
            tactical_alert = f"💨【向かい風 {wind}m】インの加速が鈍ります。3〜6コースの『まくり・まくり差し』展開を広めに警戒！"
        elif wind_dir == "追い風":
            if wind >= 5:
                df.loc[df["進入コース"] == 1, "総合スコア"] -= (wind * 0.15)
                df.loc[df["進入コース"].isin([2, 3]), "総合スコア"] += (wind * 0.2)
                tactical_alert = f"💨【強追い風 {wind}m】イン艇が1マークで流れやすい水面。2・3コースの『差し・差し返し』が絶好機。"
            else:
                df.loc[df["進入コース"] == 1, "総合スコア"] += 1.0
                tactical_alert = f"🌤️【順風/追い風 {wind}m】インコースに優位な風。スタートを決めて先マイ安定パターン。"
        elif wind_dir == "右方向（横風）":
            df.loc[df["進入コース"] == 1, "総合スコア"] -= 0.5
            df.loc[df["進入コース"] == 2, "総合スコア"] += 0.8
            tactical_alert = f"横風【右風 {wind}m】バックからスタンドへ吹く風。インのターンが膨らみやすく、2コースの『逃げ追走・差しきり』が浮上。"
        elif wind_dir == "左方向（横風）":
            df.loc[df["進入コース"].isin([1, 2]), "総合スコア"] -= 0.4
            df.loc[df["進入コース"].isin([3, 4, 5]), "総合スコア"] += 0.5
            tactical_alert = f"横風【左風 {wind}m】スタンドからバックへ吹く風。1マーク手前で艇がバタつきやすく、センター勢の『握りマイ・全速まくり』に妙味。"

    df_display = df.sort_values(by="総合スコア", ascending=False)

    if kimarite_note:
        st.info(kimarite_note)

    if slit_note:
        st.warning(slit_note)

    if tactical_alert:
        st.warning(tactical_alert)
    else:
        st.success(f"🌤️ 水面コンディション：穏やか（風速: {wind}m / 風向き: {wind_dir}）")

    if rough_water:
        st.error(
            "⚠️【大荒れ水面】風速5m以上または波高5cm以上です。定石では『見送りが賢明』とされる荒れ具合です。"
            "スタート事故や転覆のリスクも高く、通常のセオリーが通用しにくい点にご注意ください。"
        )

    st.caption(f"🏟️ SYSTEM LOG: {selected_venue_name} 場別コース1着率(直近3ヶ月)を適用中")

    tab1, tab2 = st.tabs(["🔮 リアルタイム展開予測", "📊 直前統合データシート"])

    with tab1:
        top1, top2, top3 = df_display.iloc[0], df_display.iloc[1], df_display.iloc[2]

        def render_card(col, rank_label, row, is_top=False):
            waku = int(row["号艇"])
            bg = LANE_BG.get(waku, "#122E43")
            fg = LANE_FG.get(waku, "#EAF2F5")
            card_class = "hv-card is-top" if is_top else "hv-card"
            col.markdown(
                f"""
                <div class="{card_class}">
                    <div class="hv-eyebrow">{rank_label}</div>
                    <span class="hv-lane-chip" style="background:{bg};color:{fg};">{waku}</span>
                    <div class="hv-card-name">{row['選手名']} ({row['級別']})</div>
                    <div class="hv-card-reason">{explain_boat(row, df_display)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        c1, c2, c3 = st.columns(3)
        render_card(c1, "🏆 本命 (◎)", top1, is_top=True)
        render_card(c2, "🥈 対抗 (◯)", top2)
        render_card(c3, "🥉 単穴 (▲)", top3)

        st.markdown("---")

        # 🚤 スリット隊形の図(ボート型・枠なり/展示スタート切替可能)
        if df["展示ST"].notna().sum() >= 4:
            st.markdown("#### 🚤 予想スリット隊形")
            slit_mode = st.radio(
                "コースの表示基準",
                ["展示スタート予想(実際の進入)", "枠なり(号艇順)"],
                horizontal=True,
                key="slit_mode",
            )
            course_col = "進入コース" if slit_mode.startswith("展示") else "号艇"

            lane_colors = LANE_BG
            lane_text = LANE_FG

            slit_df = df[["号艇", "選手名", "ST差", course_col]].dropna(subset=["ST差", course_col]).copy()
            slit_df = slit_df.rename(columns={course_col: "表示コース"})
            slit_df["表示コース"] = slit_df["表示コース"].astype(int)
            slit_df["色"] = slit_df["号艇"].map(lane_colors)
            slit_df["文字色"] = slit_df["号艇"].map(lane_text)
            # 進み具合(奥行き) = ST差が小さいほど先行 → 大きい値ほど上(先頭)に描く
            slit_df["進み"] = slit_df["ST差"].max() - slit_df["ST差"] + 0.02

            base = alt.Chart(slit_df).encode(
                x=alt.X("表示コース:O", title="コース(左=1コース、右=6コース)",
                        scale=alt.Scale(domain=[1, 2, 3, 4, 5, 6])),
                y=alt.Y("進み:Q", title=None, axis=None, scale=alt.Scale(domain=[0, slit_df["進み"].max() + 0.05])),
            )
            boats = base.mark_point(shape="triangle-up", size=900, filled=True, stroke="#0B2233", strokeWidth=2).encode(
                color=alt.Color("色:N", scale=None, legend=None),
                tooltip=[alt.Tooltip("号艇:N", title="号艇"), alt.Tooltip("選手名:N"), alt.Tooltip("ST差:Q", format=".2f")],
            )
            labels = base.mark_text(dy=2, fontSize=13, fontWeight="bold").encode(
                text="号艇:N",
                color=alt.Color("文字色:N", scale=None, legend=None),
            )
            start_line = (
                alt.Chart(pd.DataFrame({"y": [0.02]}))
                .mark_rule(color="#5FA8C9", strokeDash=[4, 4])
                .encode(y="y:Q")
            )
            st.altair_chart((boats + labels + start_line).properties(height=280), use_container_width=True)
            st.caption("▲が艇の位置(上に行くほどスタートで先行)。「展示スタート予想」は当日の進入変化を反映、「枠なり」は号艇どおりの並びです。")

        st.markdown("---")

        # 🎯 柔軟な買い目提案(スコア上位艇から複数パターンを自動生成)
        st.markdown("#### 🎯 買い目候補(3連単・スコア上位から自動生成)")
        top_n = df_display.head(5).reset_index(drop=True)
        axis_boat = int(top_n.iloc[0]["号艇"])  # 1着軸は最上位固定
        candidates = top_n.iloc[1:5]  # 2〜5位を2着・3着候補に

        combos = []
        for i in range(len(candidates)):
            for j in range(len(candidates)):
                if i == j:
                    continue
                second = candidates.iloc[i]
                third = candidates.iloc[j]
                combined_score = float(top_n.iloc[0]["総合スコア"]) + float(second["総合スコア"]) * 0.6 + float(third["総合スコア"]) * 0.4
                combos.append({
                    "組み合わせ": f"{axis_boat} — {int(second['号艇'])} — {int(third['号艇'])}",
                    "目安スコア": round(combined_score, 1),
                })

        combo_df = pd.DataFrame(combos).drop_duplicates(subset="組み合わせ").sort_values("目安スコア", ascending=False).head(6)
        st.dataframe(combo_df.reset_index(drop=True), use_container_width=True, hide_index=True)
        st.caption(f"1着軸は{axis_boat}号艇固定、2・3着はスコア2〜5位の艇から組み合わせを自動生成しています(目安スコアは参考値で、的中を保証するものではありません)。")

    with tab2:
        display_cols = ["号艇", "進入コース", "選手名", "級別", "コース1着率", "逃げ率", "差し率", "捲り率", "捲り差し率",
                         "選手コース3連対率", "選手コース平均ST",
                         "全国勝率", "モーター2連", "モーター3連", "展示タイム", "展示ST", "ST差", "チルト",
                         "部品交換", "展示F", "体重", "総合スコア"]
        display_cols = [c for c in display_cols if c in df_display.columns]
        st.dataframe(df_display[display_cols], use_container_width=True)
