"""
ui_professional.py - Professional UI with Dark/Light Theme Toggle
"""

import streamlit as st


def apply_theme(theme='dark'):
    """Apply professional theme with toggle support"""
    
    if theme == 'dark':
        # Dark theme - Professional Blue/Purple gradient
        st.markdown("""
        <style>
            /* Dark Theme Colors */
            :root {
                --primary: #6366f1;
                --secondary: #8b5cf6;
                --accent: #ec4899;
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-tertiary: #334155;
                --text-primary: #f8fafc;
                --text-secondary: #cbd5e1;
                --success: #10b981;
                --warning: #f59e0b;
                --error: #ef4444;
                --border: rgba(148, 163, 184, 0.1);
            }
            
            /* Main app */
            .stApp {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            }
            
            /* Sidebar */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
                border-right: 1px solid var(--border);
            }
            
            [data-testid="stSidebar"] * {
                color: var(--text-primary) !important;
            }
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: var(--text-primary) !important;
                font-weight: 700 !important;
                margin: 0.5rem 0 !important;
            }
            
            h1 {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            /* Text */
            p, span, div, label {
                color: var(--text-secondary) !important;
                line-height: 1.5 !important;
            }
            
            /* Buttons */
            .stButton>button {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white !important;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 1.5rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
            }
            
            .stButton>button[kind="primary"] {
                background: linear-gradient(135deg, var(--secondary) 0%, var(--accent) 100%);
            }
            
            /* Input fields */
            .stTextInput>div>div>input,
            .stTextArea>div>div>textarea,
            .stSelectbox>div>div>select,
            .stNumberInput>div>div>input {
                background: var(--bg-secondary) !important;
                border: 1px solid var(--border) !important;
                border-radius: 8px !important;
                color: var(--text-primary) !important;
                padding: 0.6rem !important;
            }
            
            .stTextInput>div>div>input:focus,
            .stTextArea>div>div>textarea:focus,
            .stSelectbox>div>div>select:focus {
                border-color: var(--primary) !important;
                box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
            }
            
            /* Cards */
            .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
                background: var(--bg-secondary) !important;
                border-radius: 10px !important;
                border: 1px solid var(--border) !important;
                padding: 1rem !important;
                margin: 0.5rem 0 !important;
            }
            
            /* Metrics */
            [data-testid="stMetricValue"] {
                color: var(--primary) !important;
                font-size: 1.8rem !important;
                font-weight: 700 !important;
            }
            
            [data-testid="stMetricLabel"] {
                color: var(--text-secondary) !important;
                font-size: 0.85rem !important;
            }
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                background: var(--bg-secondary);
                border-radius: 10px;
                padding: 0.3rem;
                gap: 0.3rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                color: var(--text-secondary);
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                font-weight: 500;
            }
            
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white !important;
            }
            
            /* Divider */
            hr {
                border-color: var(--border) !important;
                margin: 1rem 0 !important;
            }
            
            /* File uploader */
            [data-testid="stFileUploader"] {
                background: var(--bg-secondary);
                border: 2px dashed var(--border);
                border-radius: 12px;
                padding: 1.5rem;
            }
            
            /* Progress bar */
            .stProgress>div>div>div>div {
                background: linear-gradient(90deg, var(--primary) 0%, var(--success) 100%);
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background: var(--bg-secondary);
                border-radius: 8px;
                border: 1px solid var(--border);
                color: var(--text-primary) !important;
            }
            
            /* Remove extra spacing */
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 1rem !important;
            }
            
            /* Compact spacing */
            .element-container {
                margin-bottom: 0.5rem !important;
            }
        </style>
        """, unsafe_allow_html=True)
    
    else:
        # Light theme - Professional Clean Design
        st.markdown("""
        <style>
            /* Light Theme Colors */
            :root {
                --primary: #4f46e5;
                --secondary: #7c3aed;
                --accent: #db2777;
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --bg-tertiary: #e2e8f0;
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --success: #059669;
                --warning: #d97706;
                --error: #dc2626;
                --border: rgba(100, 116, 139, 0.2);
            }
            
            /* Main app */
            .stApp {
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            }
            
            /* Sidebar */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border-right: 1px solid var(--border);
            }
            
            [data-testid="stSidebar"] * {
                color: var(--text-primary) !important;
            }
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: var(--text-primary) !important;
                font-weight: 700 !important;
                margin: 0.5rem 0 !important;
            }
            
            h1 {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            /* Text */
            p, span, div, label {
                color: var(--text-secondary) !important;
                line-height: 1.5 !important;
            }
            
            /* Buttons */
            .stButton>button {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white !important;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 1.5rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4);
            }
            
            .stButton>button[kind="primary"] {
                background: linear-gradient(135deg, var(--secondary) 0%, var(--accent) 100%);
            }
            
            /* Input fields */
            .stTextInput>div>div>input,
            .stTextArea>div>div>textarea,
            .stSelectbox>div>div>select,
            .stNumberInput>div>div>input {
                background: var(--bg-primary) !important;
                border: 1px solid var(--border) !important;
                border-radius: 8px !important;
                color: var(--text-primary) !important;
                padding: 0.6rem !important;
            }
            
            .stTextInput>div>div>input:focus,
            .stTextArea>div>div>textarea:focus,
            .stSelectbox>div>div>select:focus {
                border-color: var(--primary) !important;
                box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2) !important;
            }
            
            /* Cards */
            .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
                background: var(--bg-primary) !important;
                border-radius: 10px !important;
                border: 1px solid var(--border) !important;
                padding: 1rem !important;
                margin: 0.5rem 0 !important;
            }
            
            /* Metrics */
            [data-testid="stMetricValue"] {
                color: var(--primary) !important;
                font-size: 1.8rem !important;
                font-weight: 700 !important;
            }
            
            [data-testid="stMetricLabel"] {
                color: var(--text-secondary) !important;
                font-size: 0.85rem !important;
            }
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                background: var(--bg-secondary);
                border-radius: 10px;
                padding: 0.3rem;
                gap: 0.3rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                color: var(--text-secondary);
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                font-weight: 500;
            }
            
            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white !important;
            }
            
            /* Divider */
            hr {
                border-color: var(--border) !important;
                margin: 1rem 0 !important;
            }
            
            /* File uploader */
            [data-testid="stFileUploader"] {
                background: var(--bg-primary);
                border: 2px dashed var(--border);
                border-radius: 12px;
                padding: 1.5rem;
            }
            
            /* Progress bar */
            .stProgress>div>div>div>div {
                background: linear-gradient(90deg, var(--primary) 0%, var(--success) 100%);
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background: var(--bg-secondary);
                border-radius: 8px;
                border: 1px solid var(--border);
                color: var(--text-primary) !important;
            }
            
            /* Remove extra spacing */
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 1rem !important;
            }
            
            /* Compact spacing */
            .element-container {
                margin-bottom: 0.5rem !important;
            }
        </style>
        """, unsafe_allow_html=True)


def render_metric_card(value, label, icon="📊"):
    """Render professional metric card"""
    st.markdown(f"""
    <div style="background: var(--bg-secondary); border-radius: 10px; padding: 1rem; 
                text-align: center; border: 1px solid var(--border);">
        <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{icon}</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: var(--primary); margin-bottom: 0.3rem;">{value}</div>
        <div style="color: var(--text-secondary); font-size: 0.85rem;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_score_display(score, total, percentage):
    """Render score display"""
    if percentage >= 80:
        emoji = "🏆"
        message = "Excellent!"
    elif percentage >= 60:
        emoji = "👍"
        message = "Good Job!"
    else:
        emoji = "💪"
        message = "Keep Practicing!"
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                border-radius: 15px; padding: 2rem; text-align: center; 
                box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{emoji}</div>
        <div style="color: white; font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem;">
            {score}/{total}
        </div>
        <div style="color: white; font-size: 1.8rem; margin-bottom: 0.5rem;">{percentage:.1f}%</div>
        <div style="color: white; font-size: 1.3rem; font-weight: 600;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def render_progress_bar(percentage, label="Progress"):
    """Render custom progress bar"""
    if percentage >= 70:
        color = "var(--success)"
    elif percentage >= 40:
        color = "var(--warning)"
    else:
        color = "var(--error)"
    
    st.markdown(f"""
    <div style="margin: 0.5rem 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
            <span style="color: var(--text-secondary); font-size: 0.85rem;">{label}</span>
            <span style="color: {color}; font-weight: 600; font-size: 0.85rem;">{percentage:.1f}%</span>
        </div>
        <div style="background: var(--bg-tertiary); border-radius: 8px; height: 10px; overflow: hidden;">
            <div style="background: {color}; height: 100%; width: {percentage}%; 
                        transition: width 0.5s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# Export
__all__ = ['apply_theme', 'render_metric_card', 'render_score_display', 'render_progress_bar']