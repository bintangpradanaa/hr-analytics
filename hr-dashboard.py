import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib as plt
import seaborn as sns

# ===============================
# STREAMLIT LAYOUT & TITLE
# ===============================
st.set_page_config(layout="wide")

st.markdown('<div style="text-align: center;font-size:42px;font-weight:bold;line-height:1.5; color:#1D4ED8;">📊 HR DASHBOARD</div>', unsafe_allow_html=True)

# ===============================
# GLOBAL STYLING FIX UNTUK LAYOUT
# ===============================
st.markdown("""
    <style>
    .block-container {
        padding-top: 3rem !important; 
        padding-bottom: 5rem !important;
    }

    h1, h2, h3 {
        scroll-margin-top: 100px;
    }
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef;
    }

    /* expander */
    .stExpander {
        margin-top: 10px !important; /* jangan terlalu nempel */
        margin-bottom: 20px !important;
    }
    .stDataFrame {
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)


# LOAD & PREPARE DATA
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTQyERWzY558YfSVl-9PpWL_EJszeOYxx-aqt2Maav1dQmyKXl3G7wy7SlSk2EMpg/pub?output=csv"
df = pd.read_csv(csv_url)

# konversi kolom 
df["DateofHire"] = pd.to_datetime(df["DateofHire"], errors="coerce")
df["DateofTermination"] = pd.to_datetime(df["DateofTermination"], errors="coerce")
# tambahan kolom tahun
df["HireYear"] = df["DateofHire"].dt.year
df["TermYear"] = df["DateofTermination"].dt.year
# masa kerja (tahun)
df["TenureYears"] = np.where(
    df["DateofTermination"].notna(),
    (df["DateofTermination"] - df["DateofHire"]).dt.days / 365,
    (pd.to_datetime("today") - df["DateofHire"]).dt.days / 365
)

# gaji bulanan 40jam/minggu = 160 jam/bulan 
df["PayRate"] = df["PayRate"].fillna(0)
df["MonthlyPay"] = df["PayRate"] * 160

# ===============================
# SIDEBAR FILTER
# ===============================
st.sidebar.header("📅 Filter Data")
years = sorted(pd.concat([df["HireYear"], df["TermYear"]], ignore_index=True).dropna().astype(int).unique(),reverse=True)
selected_year = st.sidebar.selectbox("Select Year", years, index=0)
prev_year = selected_year - 1

# Karyawan aktif pada akhir tahun
active_curr = df[
    (df["HireYear"] <= selected_year) &
    ((df["TermYear"].isna()) | (df["TermYear"] >= selected_year)) &
    (df["EmploymentStatus"].str.lower() == "active")
]

# Karyawan aktif pada tahun sebelumnya
active_prev = df[
    (df["HireYear"] <= prev_year) &
    ((df["TermYear"].isna()) | (df["TermYear"] >= prev_year)) &
    (df["EmploymentStatus"].str.lower() == "active")
]

# karyawan yang keluar pada tahun itu
term_curr = df[df["TermYear"] == selected_year]
term_prev = df[df["TermYear"] == prev_year]

st.sidebar.markdown(
    """
    <div style="
        display: flex;
        flex-direction: column;
        height: 63vh;  
        justify-content: space-between;
    ">
        <div>
            <!-- All other sidebar content goes here -->
        </div>
        <div style="text-align: center; font-size: 16px; font-weight: bold; color: #1D4ED8;">
            Dashboard by<br>Team BIRU
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# KPI 
# 1. Total tenaga kerja aktif
active_curr_count = len(active_curr)
active_prev_count = len(active_prev)
active_change = ((active_curr_count - active_prev_count) / active_prev_count * 100) if active_prev_count > 0 else 0

# 2. Jumlah karyawan keluar
term_curr_count = len(term_curr)
term_prev_count = len(term_prev)
term_change = ((term_curr_count - term_prev_count) / term_prev_count * 100) if term_prev_count > 0 else 0

# 3. Tingkat turnover
def calc_turnover(df, year):
    aktif_awal = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))]
    keluar = df[df["TermYear"] == year]
    rate = (len(keluar) / len(aktif_awal) * 100) if len(aktif_awal) > 0 else 0
    return len(keluar), len(aktif_awal), round(rate, 2)

term_curr_count, active_start_count, turnover_curr = calc_turnover(df, selected_year)
term_prev_count, active_start_prev_count, turnover_prev = calc_turnover(df, prev_year)
turnover_change = turnover_curr - turnover_prev

# 4. Rata-rata lama bekerja
def active_tenure(df, year):
    aktif = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))].copy()
    aktif["TenureYears"] = aktif.apply(
        lambda row: ((min(pd.Timestamp(year=year, month=12, day=31), row["DateofTermination"] if pd.notna(row["DateofTermination"]) else pd.Timestamp(year=year, month=12, day=31)) - row["DateofHire"]).days) / 365.25, axis=1)
    return aktif["TenureYears"].mean() if not aktif.empty else 0

avg_tenure_curr = active_tenure(df, selected_year)
avg_tenure_prev = active_tenure(df, prev_year)
tenure_change = ((avg_tenure_curr - avg_tenure_prev) / avg_tenure_prev * 100) if avg_tenure_prev > 0 else 0

# 5. Rata-rata gaji bulanan
def avg_monthly_pay(df, year):
    aktif = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))].copy()
    # monthly pay 
    return aktif["MonthlyPay"].mean() if not aktif.empty else 0

avg_salary_curr = avg_monthly_pay(df, selected_year)
avg_salary_prev = avg_monthly_pay(df, prev_year)
salary_change = ((avg_salary_curr - avg_salary_prev) / avg_salary_prev * 100) if avg_salary_prev > 0 else 0

# usia karyawan
if "Age" not in df.columns:
    df["Age"] = ((pd.to_datetime("today") - pd.to_datetime(df["DOB"], errors="coerce")).dt.days / 365.25).round(1)


# ===============================
# TAB
# ===============================
tab1, tab2 = st.tabs(["📊 HR Dashboard", "👥 Employee Details"])

# ===============================
# A. TAB UTAMA (Executive Summary)
# ===============================
with tab1:
    # ===============================
    # 1. KPI SCORECARDS
    # ===============================
    st.markdown("<h3>📊 KPI</h3>", unsafe_allow_html=True)

    # list data KPI
    kpi_data = [
        {
            "title": "👥 Active Employee",
            "value": f"{active_curr_count:,}",
            "delta": active_change,
            "delta_text": f"{active_change:+.2f}% vs prev year"
        },
        {
            "title": "🚪 Employee Left",
            "value": f"{term_curr_count:,}",
            "delta": term_change,
            "delta_text": f"{term_change:+.2f}% vs prev year"
        },
        {
            "title": "🔄 Turnover Rate",
            "value": f"{turnover_curr:.2f}%",
            "delta": turnover_change,
            "delta_text": f"{turnover_change:+.2f}% change"
        },
        {
            "title": "⏳ Avg Tenure",
            "value": f"{avg_tenure_curr:.2f} year",
            "delta": tenure_change,
            "delta_text": f"{tenure_change:+.2f}% vs prev year"
        },
        {
            "title": "💰 Monthly Pay",
            "value": f"${avg_salary_curr:,.0f}",
            "delta": salary_change,
            "delta_text": f"{salary_change:+.2f}% vs prev year"
        }
    ]

    cols = st.columns(5, gap="small") # 5 kolom horizontal
    for col, kpi in zip(cols, kpi_data):
        # warna
        if kpi['title'] in ["🚪 Employee Left", "🔄 Turnover Rate"]:
         # KPI negatif, naik = merah
            if kpi['delta'] > 0:
                delta_color = "#e74c3c"  # merah
            elif kpi['delta'] < 0:
                delta_color = "#2ecc71"  # hijau
            else:
                delta_color = "black"
        else:
            # KPI positif, naik = hijau
            if kpi['delta'] > 0:
                delta_color = "#2ecc71"  # hijau
            elif kpi['delta'] < 0:
                delta_color = "#e74c3c"  # merah
            else:
                delta_color = "black"
    
        # memisahkan angka dan teks untuk card
        delta_value = f"{kpi['delta']:+.2f}%"
        delta_suffix = kpi['delta_text'].replace(f"{kpi['delta']:+.2f}%", "")
        
        # tooltip
        if kpi['title'] == "💰 Monthly Pay":
            tooltip_text = f"Monthly Pay currently: ${avg_salary_curr:,.0f} (2024) vs ${avg_salary_prev:,.0f} (2023)"
        elif kpi['title'] == "⏳ Avg Tenure":
            tooltip_text = f"Average Tenure currently: {avg_tenure_curr:.2f} years (2024) vs {avg_tenure_prev:.2f} years (2023)"
        elif kpi['title'] == "👥 Active Employee":
            tooltip_text = f"Active Employees currently: {active_curr_count:,} (2024) vs {active_prev_count:,} (2023)"
        elif kpi['title'] == "🚪 Employee Left":
            tooltip_text = f"Employees Left currently: {term_curr_count:,} (2024) vs {term_prev_count:,} (2023)"
        elif kpi['title'] == "🔄 Turnover Rate":
            tooltip_text = f"Turnover Rate currently: {turnover_curr:.2f}% (2024) vs {turnover_prev:.2f}% (2023)"
        else:
            tooltip_text = ""
        
        col.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 15px;
            padding: 16px;
            background-color: #fafafa;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.08);
            text-align: center;
            height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin-bottom: 30px;
        " title="{tooltip_text}">
            <h6 style="margin: 0; color: black;">{kpi['title']}</h6>
            <p style="font-size: 28px; font-weight: bold; margin: 0; padding-bottom:10px;">{kpi['value']}</p>
            <span style="font-size: 14px; font-weight: 500;">
                <span style="color: {delta_color};">{delta_value}</span>{delta_suffix}
            </span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    # ===============================
    # 2. DEMOGRAFI KARYAWAN
    # ===============================
    st.markdown("<h3>👥 Workforce Demographic</h3>", unsafe_allow_html=True)
    st.markdown("""This section provides an overview of the company's workforce demographics selected by year. """)
    col1, col2, col3 = st.columns(3, gap="medium")

    # 2.1 Gender
    with col1:
        st.markdown("<h6 style='text-align:left'>⚥ Gender Distribution</h6>", unsafe_allow_html=True)
        gender_counts = active_curr["Sex"].value_counts().reset_index()
        gender_counts.columns = ["Gender", "Count"]

        fig_gender = px.pie(
            gender_counts,
            names="Gender",
            values="Count",
            color="Gender",
            color_discrete_map={"Male":"#1E3A8A","Female":"#3B82F6"},
            hole=0.4
        )
        fig_gender.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} employees")
        fig_gender.update_layout(height=300, margin=dict(t=20,b=20,l=20,r=20))
        st.plotly_chart(fig_gender, use_container_width=True)
    
    # 2.1 Age distribution
    with col2:
        st.markdown("<h6 style='text-align:left'>⏳ Age Distribution</h6>", unsafe_allow_html=True)
        active_curr['Age'] = selected_year - pd.to_datetime(active_curr['DOB']).dt.year
        
        # bins 
        age_bins = list(range(20, 66, 5))
        counts, edges = np.histogram(active_curr['Age'], bins=age_bins)
        
        max_idx = np.argmax(counts)
        most_common_age_range = f"{int(edges[max_idx])}-{int(edges[max_idx+1]-1)}"
        most_common_age_count = counts[max_idx]

        # plot
        fig_age = px.histogram(
            active_curr, x="Age", nbins=len(age_bins)-1, color_discrete_sequence=["#1E3A8A"]
        )
        fig_age.update_layout(
            xaxis_title="Age (Years)",
            yaxis_title="Number of Employees",
            height=350,
            margin=dict(t=20,b=20,l=20,r=20)
        )
        st.plotly_chart(fig_age, use_container_width=True)

    # 2.3 Marital Status
    with col3:
        st.markdown("<h6 style='text-align:left'>💍 Marital Status</h6>", unsafe_allow_html=True)
        marital_counts = active_curr["MaritalDesc"].dropna().value_counts().reset_index()
        marital_counts.columns = ["Marital Status", "Count"]
        total_emp = marital_counts["Count"].sum()

        palette = ["#1E3A8A", "#1E40AF", "#2563EB", "#3B82F6", "#60A5FA"][:len(marital_counts)]

        fig_marital = px.bar(
            marital_counts,
            y="Marital Status",
            x="Count",
            color="Marital Status",
            color_discrete_sequence=palette,
            text="Count",
            orientation='h'
        )
        fig_marital.update_traces(textposition="outside", width=0.6)
        fig_marital.update_layout(
            xaxis_title="Number of Employees",
            yaxis_title="Marital Status",
            height=350,
            margin=dict(t=20,b=40,l=120,r=20),
            showlegend=False,
            xaxis=dict(range=[0, marital_counts["Count"].max()*1.2])
        )
        st.plotly_chart(fig_marital, use_container_width=True)

    # Insight utama  Workforce Demographic
    with st.expander(f"📌 Quick Insights Workforce Demographic ({selected_year})"):
        # gender
        gender_total = gender_counts["Count"].sum()
        male_count = gender_counts.loc[gender_counts["Gender"]=="Male","Count"].sum()
        female_count = gender_counts.loc[gender_counts["Gender"]=="Female","Count"].sum()
        most_gender = "Male" if male_count > female_count else "Female"
        most_gender_count = max(male_count, female_count)
        st.write(f"⚥ Majority of employees are **{most_gender}** ({most_gender_count} employees)")
        # age
        st.write(f"⏳ Employees are mostly in the **{most_common_age_range}** age range ({most_common_age_count} employees)")
        # marital Status
        most_marital = marital_counts.loc[marital_counts["Count"].idxmax()]
        st.write(f"💍 Most employees are **{most_marital['Marital Status']}** ({most_marital['Count']} employees)")

    # ===============================
    # 3. Employee & Project Distribution by Department
    # ===============================
    st.markdown("<h3>🏢 Employee & Project Distribution by Department</h3>", unsafe_allow_html=True)
    st.markdown("This section provides an overview of employee and project distribution across departments for the selected year.")
    col1, col2 = st.columns(2, gap="medium")

    # 3.1 Employee Distribution
    with col1:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>👔 Employee Distribution</h6>", unsafe_allow_html=True)
        dept_counts = active_curr["Department"].value_counts().reset_index()
        dept_counts.columns = ["Department","Count"]
        dept_counts = dept_counts.sort_values("Count", ascending=True)

        fig_dept = px.bar(
            dept_counts,
            x="Count", y="Department",
            orientation="h",
            text="Count",
            color="Count",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_dept.update_traces(textposition="outside")
        fig_dept.update_layout(
            xaxis_title="Number of Employees",
            yaxis_title=None,
            height=350,
            margin=dict(t=20,b=20,l=20,r=20),
            coloraxis_showscale=False,
            xaxis=dict(range=[0, dept_counts["Count"].max()*1.1])
        )
        st.plotly_chart(fig_dept, use_container_width=True)

    # 3.2 Project Distribution
    with col2:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>📁 Department Projects</h6>", unsafe_allow_html=True)
        project_counts = active_curr.groupby("Department")["SpecialProjectsCount"].sum().reset_index()
        project_counts = project_counts.sort_values("SpecialProjectsCount", ascending=True)

        fig_project = px.bar(
            project_counts,
            x="SpecialProjectsCount", y="Department",
            orientation="h",
            text="SpecialProjectsCount",
            color="SpecialProjectsCount",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_project.update_traces(textposition="outside")
        fig_project.update_layout(
            xaxis_title="Number of Projects",
            yaxis_title=None,
            height=350,
            margin=dict(t=20,b=20,l=20,r=20),
            coloraxis_showscale=False,
            xaxis=dict(range=[0, project_counts["SpecialProjectsCount"].max()*1.1])
        )
        st.plotly_chart(fig_project, use_container_width=True)
    
    # Insight utama Employee & Project Distribution by Department
    with st.expander(f"📌 Quick Insights Employee & Project Distribution by Department ({selected_year})"):
        # employee dist
        emp_max = dept_counts.loc[dept_counts["Count"].idxmax()]
        emp_min = dept_counts.loc[dept_counts["Count"].idxmin()]
        st.write(f"👔 Most employees: **{emp_max['Department']}** ({emp_max['Count']})")
        st.write(f"👔 Least employees: **{emp_min['Department']}** ({emp_min['Count']})")
        # project dist
        proj_max = project_counts.loc[project_counts["SpecialProjectsCount"].idxmax()]
        proj_min = project_counts.loc[project_counts["SpecialProjectsCount"].idxmin()]
        st.write(f"📁 Most projects: **{proj_max['Department']}** ({proj_max['SpecialProjectsCount']})")
        st.write(f"📁 Least projects: **{proj_min['Department']}** ({proj_min['SpecialProjectsCount']})")
    
    # ===============================
    # 4. Turnover Trend & Reason Term
    # ===============================
    # 4.1 Turnover Trend
    st.markdown("<br>", unsafe_allow_html=True)
    col_note, col_filter = st.columns([3, 1])

    with col_note:
        st.markdown("<h3>📈 Turnover Trend</h3>", unsafe_allow_html=True)
        st.markdown("This filter exclusively modifies the Turnover Trend chart.", unsafe_allow_html=True)

    with col_filter:
        st.write("") 
        period_options = ["Weekly", "Monthly", "Yearly"]
        period_option = st.selectbox("", period_options, index=0) 

    turnover_df = df[df["DateofTermination"].notna()].copy()
    turnover_df["TermDate"] = pd.to_datetime(turnover_df["DateofTermination"])
    if period_option == "Weekly":
        turnover_trend = turnover_df.groupby(turnover_df["TermDate"].dt.to_period("W")).size().reset_index(name="Jumlah_Turnover")
        turnover_trend["TermDate"] = turnover_trend["TermDate"].dt.start_time
    elif period_option == "Monthly":
        turnover_trend = turnover_df.groupby(turnover_df["TermDate"].dt.to_period("M")).size().reset_index(name="Jumlah_Turnover")
        turnover_trend["TermDate"] = turnover_trend["TermDate"].dt.to_timestamp()
    elif period_option == "Yearly":
        turnover_trend = turnover_df.groupby(turnover_df["TermDate"].dt.year).size().reset_index(name="Jumlah_Turnover")
        turnover_trend.rename(columns={"TermDate":"Year"}, inplace=True)

    # Rata-rata turnover
    avg_turnover = turnover_trend["Jumlah_Turnover"].mean()
    fig_turnover = px.line(
        turnover_trend,
        x="TermDate" if period_option != "Yearly" else "Year",
        y="Jumlah_Turnover",
        line_shape="linear"
    )

    fig_turnover.add_hline(
        y=avg_turnover,
        line_dash="dash",
        line_color="darkorange",
        annotation_text=f"Average: {avg_turnover:.2f}",
        annotation_position="top left"
    )

    fig_turnover.update_layout(
        xaxis_title="Date" if period_option != "Yearly" else "Year",
        yaxis_title="Number of Employees Left",
        height=400,
        margin=dict(t=20, b=20, l=60, r=20),
    )

    st.plotly_chart(fig_turnover, use_container_width=True) 

    # Insigt utama Turnover trend
    with st.expander(f"📌 Quick Insight Turnover Trend ({period_option})"):
        total_turnover = turnover_trend["Jumlah_Turnover"].sum()
        max_turnover_row = turnover_trend.loc[turnover_trend["Jumlah_Turnover"].idxmax()]
        min_turnover_row = turnover_trend.loc[turnover_trend["Jumlah_Turnover"].idxmin()]

        def format_period(row):
            if period_option == "Yearly":
                return str(int(row["Year"]))
            else:
                return pd.to_datetime(row["TermDate"]).strftime("%Y-%m-%d")

        st.write(f"📊 Total turnover: **{total_turnover} employees**")
        st.write(f"📈 Average turnover: **{avg_turnover:.2f} employees**")
        st.write(f"⬆️ Highest turnover: **{max_turnover_row['Jumlah_Turnover']}** employees on **{format_period(max_turnover_row)}**")
        st.write(f"⬇️ Lowest turnover: **{min_turnover_row['Jumlah_Turnover']}** employees on **{format_period(min_turnover_row)}**")
        
    # 4.1 Term Reason
    st.markdown("<br>", unsafe_allow_html=True)
    col_note, col_filter = st.columns([3, 1])

    with col_note:
        st.markdown("<h3>⚠️ Employee Termination Reasons</h3>", unsafe_allow_html=True)
        st.markdown("This visualization shows the distribution of reasons why employees left the company.", unsafe_allow_html=True)
    with col_filter:
        st.write("")  

    left_employees = df[df["TermYear"].notna()].copy()
    term_reason_counts = left_employees["TermReason"].value_counts().reset_index()
    term_reason_counts.columns = ["Reason", "Count"]
    
    fig_tt = px.treemap(
        term_reason_counts,
        path=["Reason"],
        values="Count",
        color="Count",
        color_continuous_scale="Blues",
        title=""
    )

    fig_tt.update_layout(
        width=500,
        height=300,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig_tt, use_container_width=True)

    # Insight utama Term Reason
    with st.expander("📌 Quick Insight Termination Reasons"):
        max_reason_row = term_reason_counts.loc[term_reason_counts["Count"].idxmax()]
        min_reason_row = term_reason_counts.loc[term_reason_counts["Count"].idxmin()]

        st.write(f"⬆️ Most common reason: **{max_reason_row['Reason']}** with **{max_reason_row['Count']}** employees")
        st.write(f"⬇️ Least common reason: **{min_reason_row['Reason']}** with **{min_reason_row['Count']}** employees")

        
    # ===============================
    # 5.Workforce Score & Satisfaction
    # ===============================
    st.markdown("<h3>📑 Workforce Score & Satisfaction</h3>", unsafe_allow_html=True)
    st.markdown("Bar chart showing distribution of performance, engagement, and satisfaction scores for active employees.", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    # 5.1 Performance Score (1-4)
    with col1:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>🎯 Performance Score</h6>", unsafe_allow_html=True)
        perf_scores = np.round(active_curr['PerformanceScore']).astype(int)
        perf_scores = perf_scores[(perf_scores >= 1) & (perf_scores <= 4)]
        perf_counts = perf_scores.value_counts().sort_index()
        fig_perf = px.bar(
            x=perf_counts.index.astype(str),
            y=perf_counts.values,
            labels={'x': 'Performance Score', 'y': 'Number of Employees'},
            color_discrete_sequence=['#1E3A8A']
        )
        st.plotly_chart(fig_perf, use_container_width=True)

    # 5.2 Engagement Survey (1-5)
    with col2:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>📈 Engagement Survey</h6>", unsafe_allow_html=True)
        eng_scores = np.round(active_curr['EngagementSurvey']).astype(int)
        eng_scores = eng_scores[(eng_scores >= 1) & (eng_scores <= 5)]
        eng_counts = eng_scores.value_counts().sort_index()
        fig_eng = px.bar(
            x=eng_counts.index.astype(str),
            y=eng_counts.values,
            labels={'x': 'Engagement Survey', 'y': 'Number of Employees'},
            color_discrete_sequence=['#3B82F6']
        )
        st.plotly_chart(fig_eng, use_container_width=True)

    # 5.3 Employee Satisfaction (1-5)
    with col3:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>😃 Employee Satisfaction</h6>", unsafe_allow_html=True)
        satis_scores = np.round(active_curr['EmpSatisfaction']).astype(int)
        satis_scores = satis_scores[(satis_scores >= 1) & (satis_scores <= 5)]
        satis_counts = satis_scores.value_counts().sort_index()
        fig_satis = px.bar(
            x=satis_counts.index.astype(str),
            y=satis_counts.values,
            labels={'x': 'Employee Satisfaction', 'y': 'Number of Employees'},
            color_discrete_sequence=['#BFDBFE']
        )
        st.plotly_chart(fig_satis, use_container_width=True)

    # Insight utama Workforce Score & Satisfaction
    with st.expander(f"📌 Quick Insight Workforce Score & Satisfaction ({selected_year})"):
        st.write(f"💡 There are **{active_curr.shape[0]}** active employees in {selected_year}.")
        # performance score
        most_perf = perf_scores.mode()[0]
        avg_perf = active_curr['PerformanceScore'].mean()
        st.write(f"🎯 Average Performance Score is **{avg_perf:.2f}**, with the most common score being **{most_perf}**.")
        # engagement survey
        most_eng = eng_scores.mode()[0]
        avg_eng = active_curr['EngagementSurvey'].mean()
        st.write(f"📈 Average Engagement Survey score is **{avg_eng:.2f}**, with the most employees score being **{most_eng}**.")
        # employee satisfaction
        most_satis = satis_scores.mode()[0]
        avg_satis = active_curr['EmpSatisfaction'].mean()
        st.write(f"😃 Average Employee Satisfaction is **{avg_satis:.2f}**, with the most common score being **{most_satis}**.")

# ===============================
# B. EMPLOYEE DETAILS
# ===============================
with tab2:
    st.markdown("### 👥 Employee Directory")
    st.markdown("This section provides an interactive overview of employee to explore key information about employee profiles.")

    if "Age" not in df.columns:
        df["Age"] = ((pd.to_datetime("today") - pd.to_datetime(df["DOB"], errors="coerce")).dt.days / 365.25).round(1)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1.2])
    # 1. Filter
    with col1:
        employment_status_filter = st.selectbox("📊 Employment Status",["All"] + sorted(df["EmploymentStatus"].dropna().unique()))
    with col2:
        dept_filter = st.selectbox("🏢 Department",["All"] + sorted(df["Department"].dropna().unique()))
    with col3:
        pos_filter = st.selectbox("💼 Position",["All"] + sorted(df["Position"].dropna().unique()))
    with col4:
        manager_filter = st.selectbox("👨‍💼 Manager",["All"] + sorted(df["ManagerName"].dropna().unique()))
    with col5:
        search_name = st.text_input("🔍 Search Employee Name", placeholder="Enter employee name...")
        
    detail_df = df.copy()

    if employment_status_filter != "All":
        detail_df = detail_df[detail_df["EmploymentStatus"] == employment_status_filter]
    if dept_filter != "All":
        detail_df = detail_df[detail_df["Department"] == dept_filter]
    if pos_filter != "All":
        detail_df = detail_df[detail_df["Position"] == pos_filter]
    if manager_filter != "All":
        detail_df = detail_df[detail_df["ManagerName"] == manager_filter]
    if search_name:
        detail_df = detail_df[
            detail_df["Employee_Name"].str.contains(search_name, case=False, na=False)]

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Tabel Detail informasi karyawan
    with st.expander("📋 View Employees (Click)", expanded=False):
        columns_to_show = [
            "EmpID", "Employee_Name", "Position", "Department", "Employee Status", "Age", "Sex", "MaritalDesc",
            "RaceDesc", "State", "TenureYears", "DateofHire", "DateofTermination",
            "MonthlyPay", "ManagerName", "PerformanceScore", "EngagementSurvey", "EmpSatisfaction"]
        
        columns_to_show = [col for col in columns_to_show if col in detail_df.columns]
        table_df = detail_df[columns_to_show].copy()

        table_df["Age"] = table_df["Age"].round(2)
        if "TenureYears" in table_df.columns:
            table_df["TenureYears"] = table_df["TenureYears"].round(2)
        for col in ["EngagementSurvey","EmpSatisfaction"]:
            if col in table_df.columns:
                table_df[col] = table_df[col].round(2)
        if "MonthlyPay" in table_df.columns:
            table_df["MonthlyPay"] = table_df["MonthlyPay"].astype(int)
            
        for col in ["DateofHire", "DateofTermination"]:
            if col in table_df.columns:
                table_df[col] = pd.to_datetime(table_df[col], errors='coerce').dt.date
        st.dataframe(table_df, use_container_width=True, height=300)

    
    # 3. Card Employee
    
    # mapping warna berdasarkan EmploymentStatus
    status_colors = {
        "Active": "#2ecc71",
        "Leave of Absence": "#f6e05e",
        "Voluntarily Terminated": "#feb2b2",
        "Terminated for Cause": "#e53e3e",
        "Future Start": "#63b3ed"}
    columns_to_show = [
        "EmpID", "Employee_Name", "Position", "Department", "Employee Status", "Age", "Sex", "MaritalDesc",
        "RaceDesc", "State", "TenureYears", "DateofHire", "DateofTermination",
        "MonthlyPay", "ManagerName", "PerformanceScore", "EngagementSurvey", "EmpSatisfaction"]
    columns_to_show = [col for col in columns_to_show if col in detail_df.columns]
    
    # Employee Profile
    col_header, col_sort1, col_sort2 = st.columns([3, 1, 1])
    with col_header:
        st.markdown("### 🧾 Employee Profile")
        st.markdown(f"**Total Employees Displayed:** {len(detail_df)}")
    with col_sort1:
        sort_column = st.selectbox(
            "Sort By:",
            options=columns_to_show,
            index=0)
    with col_sort2:
        sort_order = st.selectbox(
            "Order:",
            options=["⬆️ Ascending", "⬇️ Descending"],
            index=0)
    detail_df = detail_df.sort_values(
        by=sort_column,
        ascending=True if sort_order == "⬆️ Ascending" else False)

    for i, row in detail_df.iterrows():
        status_color = status_colors.get(row["EmploymentStatus"], "#A0AEC0")

        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 15px;
            padding: 16px;
            margin-bottom: 15px;
            background-color: #fafafa;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0;">👤 {row['Employee_Name']}</h4>
                <span style="color: white; background-color: {status_color};
                    padding: 5px 10px; border-radius: 8px; font-size: 12px;">
                    {row['EmploymentStatus']}
                </span>
            </div>
            <p style="margin: 5px 0 10px 0; font-weight: 500; color: #555;">{row['Position']} - {row['Department']}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; color: #333;">
                <div>📅 <b>Tenure:</b> {row['TenureYears']:.1f} Years</div>
                <div>💰 <b>Salary:</b> ${row['MonthlyPay']:,.0f}</div>
                <div>👨‍💼 <b>Manager:</b> {row['ManagerName']}</div>
                <div>🎯 <b>Performance:</b> {row['PerformanceScore']}</div>
            </div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #eee;">
            <div style="font-size: 13px; color: #555;">
                🧠 <b>Gender:</b> {row['Sex']} &nbsp;&nbsp;|&nbsp;&nbsp;
                🎂 <b>Age:</b> {row['Age']} &nbsp;&nbsp;|&nbsp;&nbsp;
                💍 <b>Marital Status:</b> {row['MaritalDesc']} &nbsp;&nbsp;|&nbsp;&nbsp;
                🌏 <b>Race:</b> {row['RaceDesc']} &nbsp;&nbsp;|&nbsp;&nbsp;
                📍 <b>State:</b> {row['State']}
            </div>
        </div>
        """, unsafe_allow_html=True)
