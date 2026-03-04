"""
AUTOMATIC APP.PY INTEGRATION SCRIPT
====================================
Run this script to automatically integrate advanced features into app.py

Usage: python integrate_advanced_features.py
"""

import re

print("🔧 App.py Integration Script for Advanced ML Features")
print("=" * 60)

# Read the current app.py
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    print("✅ Loaded app.py successfully")
except FileNotFoundError:
    print("❌ app.py not found in current directory")
    print("   Please run this script from your project directory")
    exit(1)

# Backup original
with open('app.py.backup', 'w', encoding='utf-8') as f:
    f.write(app_content)
print("✅ Created backup: app.py.backup")

# Track modifications
modifications = []

# ============================================================================
# 1. ADD IMPORTS
# ============================================================================

import_block = '''
# ⭐ ADVANCED ML FEATURES INTEGRATION
from bayesian_knowledge_tracker import BayesianKnowledgeTracker
from intelligent_question_generator import IntelligentQuestionGenerator
from error_taxonomy_engine import ErrorTaxonomy, FixStrategyEngine
from advanced_features_ui import (
    render_bayesian_knowledge_tab,
    render_concept_coverage_tab,
    render_error_analysis_tab
)
'''

# Find where to insert (after file_processors import)
if 'from file_processors import' in app_content:
    insert_pos = app_content.find('from file_processors import')
    # Find end of that line
    line_end = app_content.find('\n', insert_pos)
    
    # Insert after that line
    app_content = (
        app_content[:line_end + 1] +
        '\n' + import_block +
        app_content[line_end + 1:]
    )
    modifications.append("✅ Added advanced features imports")
else:
    print("⚠️ Warning: Could not find file_processors import. Add imports manually.")

# ============================================================================
# 2. ADD SESSION STATE VARIABLES
# ============================================================================

session_vars = """
        # ⭐ ADVANCED ML FEATURES STATES
        'bkt_tracker': None,
        'question_generator': None,
        'error_engine': None,
        'advanced_features_initialized': False,
        'mistake_history': [],
"""

# Find the defaults dictionary in init_session_state
if "defaults = {" in app_content:
    # Find upload_negative_marking line (last item before closing)
    if "'upload_negative_marking': True," in app_content:
        insert_pos = app_content.find("'upload_negative_marking': True,")
        line_end = app_content.find('\n', insert_pos)
        
        app_content = (
            app_content[:line_end + 1] +
            '\n' + session_vars +
            app_content[line_end + 1:]
        )
        modifications.append("✅ Added session state variables")
    else:
        print("⚠️ Warning: Could not find defaults dictionary. Add session vars manually.")

# ============================================================================
# 3. ADD INITIALIZATION FUNCTION
# ============================================================================

init_function = '''

def initialize_advanced_features(db, llm):
    """Initialize all advanced ML features"""
    if not st.session_state.get('advanced_features_initialized', False):
        try:
            st.session_state.bkt_tracker = BayesianKnowledgeTracker(db)
            st.session_state.question_generator = IntelligentQuestionGenerator(
                db, llm, st.session_state.bkt_tracker
            )
            st.session_state.error_engine = FixStrategyEngine(db, llm)
            st.session_state.advanced_features_initialized = True
            return True
        except Exception as e:
            st.sidebar.warning(f"⚠️ Advanced features: {str(e)[:40]}")
            return False
    return True

'''

# Insert before main() function
if "def main():" in app_content:
    insert_pos = app_content.find("def main():")
    app_content = (
        app_content[:insert_pos] +
        init_function +
        '\n' +
        app_content[insert_pos:]
    )
    modifications.append("✅ Added initialization function")
else:
    print("⚠️ Warning: Could not find main() function")

# ============================================================================
# 4. CALL INITIALIZATION IN MAIN
# ============================================================================

# Find where llm is initialized (after st.session_state.llm = )
if "st.session_state.llm = EnhancedGeminiService" in app_content:
    # Find render_sidebar() call
    if "render_sidebar()" in app_content:
        insert_pos = app_content.find("render_sidebar()")
        
        init_call = """
    # ⭐ Initialize Advanced ML Features
    initialize_advanced_features(st.session_state.db, llm)
    
    """
        
        app_content = (
            app_content[:insert_pos] +
            init_call +
            app_content[insert_pos:]
        )
        modifications.append("✅ Added initialization call in main()")

# ============================================================================
# 5. UPDATE TABS
# ============================================================================

# Find the tabs definition
tab_pattern = r'tab1, tab2, tab3, tab4, tab5, tab6 = st\.tabs\(\['

if re.search(tab_pattern, app_content):
    # Replace with new tab structure
    new_tabs = '''tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🧠 Advanced Doubt Solver",
        "🎯 Adaptive Practice (3 Modes)",
        "📝 Upload & Take Exam",
        "📊 Analytics & Learning DNA",
        "🤖 ML Insights",
        "🧠 Knowledge State (BKT)",
        "🗺️ Concept Coverage",
        "🔬 Error Analysis",
        "🌟 Wellness"
    ])'''
    
    app_content = re.sub(
        r'tab1, tab2, tab3, tab4, tab5, tab6 = st\.tabs\(\[.*?\]\)',
        new_tabs,
        app_content,
        flags=re.DOTALL
    )
    
    # Add new tab content before the last tab (wellness)
    wellness_tab = "with tab6:"
    if wellness_tab in app_content:
        # Find it
        insert_pos = app_content.find(wellness_tab)
        
        new_tab_content = '''
    # ⭐ ADVANCED ML FEATURES TABS
    with tab6:
        if st.session_state.bkt_tracker:
            render_bayesian_knowledge_tab(
                st.session_state.user_id,
                st.session_state.db,
                st.session_state.bkt_tracker
            )
        else:
            st.error("🔧 Bayesian Knowledge Tracker not initialized. Complete some practice first.")
    
    with tab7:
        if st.session_state.question_generator:
            render_concept_coverage_tab(
                st.session_state.user_id,
                st.session_state.db,
                st.session_state.question_generator
            )
        else:
            st.error("🔧 Question Generator not initialized")
    
    with tab8:
        if st.session_state.error_engine:
            render_error_analysis_tab(
                st.session_state.user_id,
                st.session_state.db,
                st.session_state.error_engine
            )
        else:
            st.error("🔧 Error Analysis Engine not initialized")
    
    with tab9:
'''
        
        # Replace tab6 with tab9
        app_content = app_content[:insert_pos] + new_tab_content + app_content[insert_pos + len(wellness_tab) + 1:]
        modifications.append("✅ Updated tabs structure with 3 new advanced features tabs")

# ============================================================================
# SAVE MODIFIED FILE
# ============================================================================

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

print("\n" + "=" * 60)
print("📝 INTEGRATION SUMMARY")
print("=" * 60)
for mod in modifications:
    print(mod)

print("\n" + "=" * 60)
print("✅ INTEGRATION COMPLETE!")
print("=" * 60)
print("\nNext steps:")
print("1. Review app.py for any issues")
print("2. Run: streamlit run app.py")
print("3. Check the new tabs:")
print("   - 🧠 Knowledge State (BKT)")
print("   - 🗺️ Concept Coverage")
print("   - 🔬 Error Analysis")
print("\nIf anything goes wrong, restore from: app.py.backup")
print("=" * 60)