"""
MANUAL INTEGRATION GUIDE - Step by Step
========================================

If the automatic script doesn't work, follow these steps manually.
"""

# ============================================================================
# STEP 1: Add imports at the top of app.py (around line 37-45)
# ============================================================================

"""
Find this section in app.py:
    from file_processors import AudioProcessor, FileProcessor

Add AFTER it:
"""

# ⭐ ADVANCED ML FEATURES INTEGRATION
from bayesian_knowledge_tracker import BayesianKnowledgeTracker
from intelligent_question_generator import IntelligentQuestionGenerator
from error_taxonomy_engine import ErrorTaxonomy, FixStrategyEngine
from advanced_features_ui import (
    render_bayesian_knowledge_tab,
    render_concept_coverage_tab,
    render_error_analysis_tab
)


# ============================================================================
# STEP 2: Add session state variables in init_session_state() function
# ============================================================================

"""
Find the 'defaults = {' dictionary (around line 104)
Find this line:
    'upload_negative_marking': True,

Add AFTER it:
"""

        # ⭐ ADVANCED ML FEATURES STATES
        'bkt_tracker': None,
        'question_generator': None,
        'error_engine': None,
        'advanced_features_initialized': False,
        'mistake_history': [],


# ============================================================================
# STEP 3: Add initialization function BEFORE main() function
# ============================================================================

"""
Find the line:
    def main():

Add this function BEFORE it:
"""

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


# ============================================================================
# STEP 4: Call initialization in main() function
# ============================================================================

"""
In the main() function, find this line (around line 312):
    llm = st.session_state.llm
    render_sidebar()

Add BETWEEN those two lines:
"""

    # ⭐ Initialize Advanced ML Features
    initialize_advanced_features(st.session_state.db, llm)


# ============================================================================
# STEP 5: Update the tabs section
# ============================================================================

"""
Find this section (around line 315):
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧠 Advanced Doubt Solver",
        "🎯 Adaptive Practice (3 Modes)",
        "📝 Upload & Take Exam",
        "📊 Analytics & Learning DNA",
        "🤖 ML Insights",
        "🌟 Wellness"
    ])

REPLACE IT WITH:
"""

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🧠 Advanced Doubt Solver",
        "🎯 Adaptive Practice (3 Modes)",
        "📝 Upload & Take Exam",
        "📊 Analytics & Learning DNA",
        "🤖 ML Insights",
        "🧠 Knowledge State (BKT)",      # ⭐ NEW
        "🗺️ Concept Coverage",            # ⭐ NEW
        "🔬 Error Analysis",              # ⭐ NEW
        "🌟 Wellness"
    ])


# ============================================================================
# STEP 6: Add content for new tabs
# ============================================================================

"""
Find the existing tab content (with tab1:, with tab2:, etc.)
Find the LAST tab (with tab6: for wellness)

BEFORE that tab, add these three new tabs:
"""

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

"""
Then change the wellness tab from 'with tab6:' to 'with tab9:'
"""


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================

"""
After making all changes, verify:

✅ 1. Imports added at top
✅ 2. Session state variables added
✅ 3. initialize_advanced_features() function added
✅ 4. Function called in main()
✅ 5. Tabs updated from 6 to 9
✅ 6. Three new tab contents added (tab6, tab7, tab8)
✅ 7. Wellness moved to tab9

Then run:
    streamlit run app.py

Expected result:
- App loads without errors
- 9 tabs appear
- Last 4 tabs are: ML Insights, Knowledge State, Concept Coverage, Error Analysis, Wellness
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
If you get ImportError:
- Make sure all .py files are in the same directory as app.py
- Especially check: advanced_features_ui.py

If tabs don't show:
- Check the tab variable names (tab1, tab2, ... tab9)
- Make sure all 'with tabX:' blocks are present

If features show "not initialized":
- Complete at least 5-10 practice questions first
- The systems need data to work with

If you see "NoneType" errors:
- The initialize_advanced_features() function might not have run
- Check if it's being called in main()
"""

print("""
========================================
MANUAL INTEGRATION GUIDE
========================================

Follow the 6 steps above to manually integrate the advanced features.

Quick summary:
1. Add imports (Step 1)
2. Add session variables (Step 2)  
3. Add init function (Step 3)
4. Call init in main (Step 4)
5. Update tabs from 6 to 9 (Step 5)
6. Add new tab content (Step 6)

Time required: ~10 minutes

Good luck! 🚀
========================================
""")