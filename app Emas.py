
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

st.set_page_config(page_title="Gold Futures Market Analytics", page_icon="🟡", layout="wide")

GOLD="#D4A017"; GOLD2="#F2C94C"; NAVY="#0F172A"; BG="#F8FAFC"
GREEN="#16A34A"; RED="#DC2626"; TEXT="#172033"; MUTED="#64748B"

st.markdown(f"""
<style>
.stApp{{background:{BG};color:{TEXT};}}
.block-container{{padding-top:1.15rem;padding-bottom:2rem;max-width:1500px;}}
.hero{{background:linear-gradient(120deg,#0F172A,#1E293B);padding:25px 28px;border-radius:22px;
color:white;margin-bottom:18px;border-bottom:4px solid {GOLD};box-shadow:0 10px 25px rgba(15,23,42,.13)}}
.hero h1{{margin:0;font-size:2rem}} .hero p{{margin:.35rem 0 0;color:#CBD5E1}}
.badge{{display:inline-block;margin-top:11px;background:{GOLD};color:#111827;padding:5px 11px;border-radius:999px;font-weight:800}}
div[data-testid="stMetric"]{{background:white!important;border:1px solid #E2E8F0!important;
border-top:4px solid {GOLD}!important;padding:14px!important;border-radius:16px!important;
box-shadow:0 3px 12px rgba(15,23,42,.055)!important;min-height:118px}}
div[data-testid="stMetricLabel"],div[data-testid="stMetricLabel"] *{{color:{MUTED}!important;opacity:1!important;font-weight:650!important}}
div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] *{{color:{NAVY}!important;opacity:1!important;font-weight:800!important;font-size:1.5rem!important}}
.section{{font-size:1.35rem;font-weight:800;color:{NAVY};margin:18px 0 8px}}
.insight{{background:white;border-left:5px solid {GOLD};border-radius:14px;padding:17px 19px;
box-shadow:0 3px 12px rgba(15,23,42,.05);line-height:1.65}}
.note{{background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:12px 14px;color:#713F12}}
</style>
""",unsafe_allow_html=True)

DATA=Path(__file__).parent/"Gold Futures Historical Data.json"

@st.cache_data
def load_data():
    d=pd.read_json(DATA)
    d["Date"]=pd.to_datetime(d["Date"],format="%m/%d/%Y",errors="coerce")
    for c in ["Price","Open","High","Low"]:
        d[c]=pd.to_numeric(d[c].astype(str).str.replace(",","",regex=False),errors="coerce")
    def volume(v):
        s=str(v).strip().upper().replace(",","")
        if s in ("","NAN","-"): return np.nan
        mult=1000 if s.endswith("K") else 1_000_000 if s.endswith("M") else 1
        s=s.rstrip("KM")
        try:return float(s)*mult
        except:return np.nan
    d["Volume"]=d["Vol."].map(volume)
    d["ChangePct"]=pd.to_numeric(d["Change %"].astype(str).str.replace("%","",regex=False),errors="coerce")
    d=d.dropna(subset=["Date","Price"]).sort_values("Date").drop_duplicates("Date",keep="last").reset_index(drop=True)
    d["LogReturn"]=np.log(d["Price"]/d["Price"].shift(1))
    d["Range"]=d["High"]-d["Low"]
    d["MA5"]=d["Price"].rolling(5).mean()
    d["MA10"]=d["Price"].rolling(10).mean()
    d["Vol5"]=d["LogReturn"].rolling(5).std()*np.sqrt(252)*100
    peak=d["Price"].cummax()
    d["Drawdown"]=(d["Price"]/peak-1)*100
    return d

df=load_data()

st.markdown("""
<div class="hero">
<h1>GOLD FUTURES MARKET ANALYTICS</h1>
<p>Price • Market Movement • Volume • Volatility • Risk • Short-Term Forecast</p>
<span class="badge">GOLD FUTURES</span>
</div>
""",unsafe_allow_html=True)

mn,mx=df.Date.min().date(),df.Date.max().date()
a,b,c=st.columns([2,1,1])
with a:
    dr=st.date_input("Rentang tanggal",(mn,mx),min_value=mn,max_value=mx)
with b:
    horizon=st.selectbox("Horizon prediksi (hari perdagangan)",[1,7,14,30],index=3,help="Jumlah hari perdagangan ke depan yang diproyeksikan. Pilihan 30 berarti H+30, bukan 30 tahun.")
with c:
    investment=st.number_input("Nilai investasi / eksposur ($)",min_value=100.0,value=10000.0,step=1000.0,help="Nilai simulasi investasi dalam USD yang digunakan untuk mengubah VaR (%) menjadi estimasi kerugian nominal. Ini bukan variabel dari dataset.")

st.info(
    "Panduan filter — Rentang tanggal menentukan periode historis yang dianalisis. "
    "Horizon prediksi menentukan jumlah hari perdagangan ke depan yang diproyeksikan "
    "(H+1, H+7, H+14, atau H+30). Nilai investasi/eksposur adalah nilai simulasi dalam USD "
    "yang hanya digunakan untuk menghitung estimasi nominal Value at Risk (VaR), bukan data asli Gold Futures."
)

if isinstance(dr,(tuple,list)) and len(dr)==2:
    x=df[(df.Date>=pd.Timestamp(dr[0]))&(df.Date<=pd.Timestamp(dr[1]))].copy()
else:x=df.copy()
if len(x)<8:
    st.warning("Rentang terlalu pendek untuk analisis. Dashboard menggunakan seluruh data.")
    x=df.copy()

last=x.iloc[-1]; first=x.iloc[0]
period=(last.Price/first.Price-1)*100
high=x.High.max(); low=x.Low.min(); avgvol=x.Volume.mean()
ret=x.LogReturn.dropna()
vol=ret.std()*np.sqrt(252)*100 if len(ret)>1 else np.nan
maxdd=x.Drawdown.min()

st.markdown('<div class="section">Market Overview</div>',unsafe_allow_html=True)
cols=st.columns(6)
cols[0].metric("Last Price",f"{last.Price:,.2f}")
cols[1].metric("Period Return",f"{period:+.2f}%")
cols[2].metric("Highest High",f"{high:,.2f}")
cols[3].metric("Lowest Low",f"{low:,.2f}")
cols[4].metric("Average Volume",f"{avgvol/1000:.2f}K")
cols[5].metric("Annualized Volatility",f"{vol:.2f}%")

# Candlestick-like OHLC using rule + body
st.markdown('<div class="section">Price Action — OHLC</div>',unsafe_allow_html=True)
base=alt.Chart(x)
wick=base.mark_rule().encode(
    x=alt.X("Date:T",title=None),
    y=alt.Y("Low:Q",title="Price",scale=alt.Scale(zero=False)),
    y2="High:Q",
    color=alt.condition("datum.Price >= datum.Open",alt.value(GREEN),alt.value(RED)),
    tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Open:Q",format=",.2f"),alt.Tooltip("High:Q",format=",.2f"),
             alt.Tooltip("Low:Q",format=",.2f"),alt.Tooltip("Price:Q",format=",.2f")]
)
body=base.mark_bar(size=10).encode(
    x="Date:T",y="Open:Q",y2="Price:Q",
    color=alt.condition("datum.Price >= datum.Open",alt.value(GREEN),alt.value(RED))
)
st.altair_chart((wick+body).properties(height=400),use_container_width=True)

# Volume
vchart=alt.Chart(x).mark_bar(color=GOLD).encode(
    x=alt.X("Date:T",title=None),y=alt.Y("Volume:Q",title="Volume"),
    tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Volume:Q",format=",.0f")]
).properties(height=170)
st.altair_chart(vchart,use_container_width=True)

c1,c2=st.columns(2)
with c1:
    st.markdown('<div class="section">Daily Change</div>',unsafe_allow_html=True)
    ch=alt.Chart(x).mark_bar().encode(
        x=alt.X("Date:T",title=None),y=alt.Y("ChangePct:Q",title="Change (%)"),
        color=alt.condition("datum.ChangePct >= 0",alt.value(GREEN),alt.value(RED)),
        tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("ChangePct:Q",format=".2f")]
    ).properties(height=290)
    st.altair_chart(ch,use_container_width=True)
with c2:
    st.markdown('<div class="section">Intraday Trading Range</div>',unsafe_allow_html=True)
    rg=alt.Chart(x).mark_bar(color=GOLD).encode(
        x=alt.X("Date:T",title=None),y=alt.Y("Range:Q",title="High − Low"),
        tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Range:Q",format=",.2f")]
    ).properties(height=290)
    st.altair_chart(rg,use_container_width=True)

# Price vs Volume
st.markdown('<div class="section">Price & Volume Relationship</div>',unsafe_allow_html=True)
pv=alt.Chart(x).mark_circle(size=100,color=GOLD,opacity=.8).encode(
    x=alt.X("Volume:Q",title="Volume"),
    y=alt.Y("ChangePct:Q",title="Daily Change (%)"),
    tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Volume:Q",format=",.0f"),
             alt.Tooltip("ChangePct:Q",format=".2f"),alt.Tooltip("Price:Q",format=",.2f")]
).properties(height=320)
st.altair_chart(pv,use_container_width=True)

# Risk
q95=ret.quantile(.05) if len(ret) else np.nan
q99=ret.quantile(.01) if len(ret) else np.nan
var95=max(0,-q95*100); var99=max(0,-q99*100)
st.markdown('<div class="section">Risk Analytics</div>',unsafe_allow_html=True)
r=st.columns(4)
r[0].metric("Historical VaR 95%",f"{var95:.2f}%",f"${investment*var95/100:,.2f}")
r[1].metric("Historical VaR 99%",f"{var99:.2f}%",f"${investment*var99/100:,.2f}")
r[2].metric("Maximum Drawdown",f"{maxdd:.2f}%")
r[3].metric("Worst Daily Change",f"{x.ChangePct.min():.2f}%")

dd=alt.Chart(x).mark_area(color=RED,opacity=.18,line={"color":RED}).encode(
    x=alt.X("Date:T",title=None),y=alt.Y("Drawdown:Q",title="Drawdown (%)"),
    tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Drawdown:Q",format=".2f")]
).properties(height=260)
st.altair_chart(dd,use_container_width=True)

# Short-term forecast: log-return drift baseline due to short sample
mu=ret.mean() if len(ret) else 0
sig=ret.std() if len(ret)>1 else 0
h=np.arange(1,horizon+1)
pred=last.Price*np.exp(mu*h)
lower=last.Price*np.exp(mu*h-1.96*sig*np.sqrt(h))
upper=last.Price*np.exp(mu*h+1.96*sig*np.sqrt(h))
fd=pd.bdate_range(last.Date+pd.Timedelta(days=1),periods=horizon)
fc=pd.DataFrame({"Date":fd,"Forecast":pred,"Lower":lower,"Upper":upper})

st.markdown('<div class="section">Short-Term Forecast</div>',unsafe_allow_html=True)
hist=x[["Date","Price"]]
line=alt.Chart(hist).mark_line(color=NAVY,strokeWidth=2.5).encode(
    x=alt.X("Date:T",title=None),y=alt.Y("Price:Q",title="Price",scale=alt.Scale(zero=False)))
band=alt.Chart(fc).mark_area(color=GOLD2,opacity=.25).encode(
    x="Date:T",y=alt.Y("Lower:Q",scale=alt.Scale(zero=False)),y2="Upper:Q")
fl=alt.Chart(fc).mark_line(color=GOLD,strokeDash=[6,4],strokeWidth=3).encode(
    x="Date:T",y="Forecast:Q",tooltip=[alt.Tooltip("Date:T"),alt.Tooltip("Forecast:Q",format=",.2f")])
st.altair_chart((band+line+fl).properties(height=360),use_container_width=True)
pred_change=(pred[-1]/last.Price-1)*100
st.caption(
    f"Forecast H+{horizon} menggunakan baseline log-return drift dengan interval prediksi 95%. "
    "Karena dataset hanya berisi 23 observasi historis, proyeksi—terutama H+30—memiliki ketidakpastian tinggi "
    "dan digunakan sebagai eksplorasi statistik, bukan kepastian harga masa depan."
)

# Insights
best=x.loc[x.ChangePct.idxmax()]
worst=x.loc[x.ChangePct.idxmin()]
vmax=x.loc[x.Volume.idxmax()]
direction="turun" if period<0 else "naik"
st.markdown('<div class="section">Executive Market Insight</div>',unsafe_allow_html=True)
st.markdown(f"""
<div class="insight">
Selama periode terpilih, Gold Futures bergerak <b>{direction} {abs(period):.2f}%</b> dari
<b>{first.Price:,.2f}</b> menjadi <b>{last.Price:,.2f}</b>.
Perubahan harian terbaik terjadi pada <b>{best.Date.strftime("%d %b %Y")}</b> sebesar
<b>{best.ChangePct:+.2f}%</b>, sedangkan tekanan terbesar terjadi pada
<b>{worst.Date.strftime("%d %b %Y")}</b> sebesar <b>{worst.ChangePct:.2f}%</b>.
Aktivitas perdagangan tertinggi tercatat <b>{vmax.Volume/1000:.2f}K</b> pada
<b>{vmax.Date.strftime("%d %b %Y")}</b>. Historical VaR 95% berada di sekitar
<b>{var95:.2f}%</b> per hari, sementara maximum drawdown periode terpilih sebesar
<b>{maxdd:.2f}%</b>. Baseline forecast H+{horizon} menghasilkan harga sekitar
<b>{pred[-1]:,.2f}</b> ({pred_change:+.2f}% dari harga terakhir).
</div>
""",unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)
st.markdown("""<div class="note"><b>Catatan:</b> Forecast dan VaR adalah estimasi statistik berbasis
data historis dan bukan jaminan hasil di masa depan. Dataset saat ini hanya mencakup 23 observasi. Horizon tersedia hingga H+30 untuk eksplorasi,
tetapi ketidakpastian meningkat pada horizon yang lebih panjang dan hasil tidak boleh diperlakukan sebagai rekomendasi transaksi.</div>""",
unsafe_allow_html=True)

st.markdown('<div class="section">Data Detail</div>',unsafe_allow_html=True)
show=x[["Date","Open","High","Low","Price","Volume","ChangePct","Range","Drawdown"]].copy()
show.columns=["Date","Open","High","Low","Price","Volume","Change (%)","Trading Range","Drawdown (%)"]
st.dataframe(show.sort_values("Date",ascending=False),use_container_width=True,hide_index=True)
st.download_button("Download filtered data",show.to_csv(index=False).encode("utf-8"),
                   "gold_futures_filtered.csv","text/csv")
