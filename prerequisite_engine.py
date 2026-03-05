"""
prerequisite_engine.py - Semantic Knowledge Graph & Prerequisite Engine

When a student fails a topic repeatedly, this engine:
1. Queries the prerequisite DAG to find root-cause gaps
2. Calculates mastery of each prerequisite from DB
3. Shows an intervention card: "You lack X because Y is weak"
4. Pivots practice to the weakest prerequisite first
5. Unlocks original topic once prerequisites are mastered

Feature 2 from the advanced roadmap.
"""

from collections import defaultdict, deque

# ═══════════════════════════════════════════════════════════════════════════
# PREREQUISITE DAG
# Directed graph: topic → list of prerequisites
# If you fail "Kinematics", you need "Trigonometry" and "Vectors" first
# ═══════════════════════════════════════════════════════════════════════════

PREREQ_DAG = {
    # ── Physics ──────────────────────────────────────────────────────────
    "Kinematics":           ["Trigonometry", "Basic Vectors"],
    "Projectile Motion":    ["Kinematics", "Trigonometry"],
    "Newton's Laws":        ["Kinematics"],
    "Circular Motion":      ["Newton's Laws", "Trigonometry"],
    "Work Energy Theorem":  ["Newton's Laws", "Calculus Basics"],
    "Rotational Motion":    ["Newton's Laws", "Circular Motion"],
    "Gravitation":          ["Newton's Laws", "Calculus Basics"],
    "Waves":                ["Trigonometry", "Simple Harmonic Motion"],
    "Simple Harmonic Motion": ["Newton's Laws", "Trigonometry"],
    "Electrostatics":       ["Basic Vectors", "Calculus Basics"],
    "Current Electricity":  ["Electrostatics"],
    "Magnetism":            ["Current Electricity", "Basic Vectors"],
    "Electromagnetic Induction": ["Magnetism", "Calculus Basics"],
    "Optics":               ["Trigonometry", "Waves"],
    "Thermodynamics":       ["Kinetic Theory"],
    "Kinetic Theory":       ["Newton's Laws"],
    "Modern Physics":       ["Electrostatics", "Waves"],

    # ── Mathematics ──────────────────────────────────────────────────────
    "Calculus Basics":      ["Algebra", "Trigonometry"],
    "Differentiation":      ["Calculus Basics", "Algebra"],
    "Integration":          ["Differentiation"],
    "Differential Equations": ["Integration"],
    "Coordinate Geometry":  ["Algebra", "Trigonometry"],
    "Vectors":              ["Algebra", "Trigonometry"],
    "Basic Vectors":        ["Trigonometry"],
    "3D Geometry":          ["Vectors", "Coordinate Geometry"],
    "Matrices":             ["Algebra"],
    "Determinants":         ["Matrices"],
    "Probability":          ["Permutation Combination"],
    "Permutation Combination": ["Algebra"],
    "Binomial Theorem":     ["Algebra"],
    "Sequences Series":     ["Algebra"],
    "Complex Numbers":      ["Algebra", "Trigonometry"],
    "Limits":               ["Calculus Basics"],
    "Continuity":           ["Limits"],
    "Differentiability":    ["Continuity", "Differentiation"],

    # ── Chemistry ────────────────────────────────────────────────────────
    "Chemical Bonding":     ["Atomic Structure"],
    "Atomic Structure":     ["Basic Chemistry"],
    "Periodic Table":       ["Atomic Structure"],
    "Chemical Equilibrium": ["Mole Concept", "Thermodynamics Chem"],
    "Ionic Equilibrium":    ["Chemical Equilibrium"],
    "Electrochemistry":     ["Redox Reactions", "Chemical Equilibrium"],
    "Redox Reactions":      ["Mole Concept"],
    "Thermodynamics Chem":  ["Mole Concept"],
    "Mole Concept":         ["Basic Chemistry"],
    "Basic Chemistry":      [],
    "Organic Reactions":    ["Chemical Bonding", "Basic Organic"],
    "Basic Organic":        ["Chemical Bonding"],
    "Aromatic Compounds":   ["Organic Reactions"],
    "Polymers":             ["Organic Reactions"],
    "Biomolecules":         ["Basic Organic"],
    "Surface Chemistry":    ["Chemical Equilibrium"],
    "Coordination Compounds": ["Chemical Bonding", "Periodic Table"],

    # ── Computer Science ─────────────────────────────────────────────────
    "Arrays":               [],
    "Linked List":          ["Arrays", "Pointers"],
    "Pointers":             ["Arrays"],
    "Stack":                ["Arrays"],
    "Queue":                ["Arrays"],
    "Trees":                ["Recursion", "Arrays"],
    "Binary Search Tree":   ["Trees"],
    "Graphs":               ["Trees", "Recursion"],
    "Recursion":            ["Arrays"],
    "Dynamic Programming":  ["Recursion", "Arrays"],
    "Sorting":              ["Arrays"],
    "Searching":            ["Arrays"],
    "Hashing":              ["Arrays"],
    "Heaps":                ["Trees"],
    "BFS DFS":              ["Graphs"],
    "Shortest Path":        ["Graphs", "Dynamic Programming"],
    "Time Complexity":      ["Sorting", "Searching"],
    "Database":             ["Basic Programming"],
    "SQL":                  ["Database"],
    "Operating Systems":    ["Basic Programming"],
    "Process Thread":       ["Operating Systems"],
    "Basic Programming":    [],

    # ── Biology ──────────────────────────────────────────────────────────
    "Genetics":             ["Cell Biology", "DNA RNA"],
    "DNA RNA":              ["Cell Biology"],
    "Cell Biology":         [],
    "Photosynthesis":       ["Cell Biology", "Biochemistry"],
    "Respiration":          ["Cell Biology", "Biochemistry"],
    "Biochemistry":         ["Cell Biology"],
    "Evolution":            ["Genetics"],
    "Human Physiology":     ["Cell Biology"],
    "Plant Physiology":     ["Cell Biology", "Photosynthesis"],
    "Ecosystem":            ["Evolution"],
    "Reproduction":         ["Cell Biology", "Genetics"],
}

# Mastery threshold to consider a prerequisite "adequate"
PREREQ_MASTERY_THRESHOLD = 0.55  # 55%
FAILURE_THRESHOLD = 3            # failures before triggering intervention


# ═══════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class PrerequisiteEngine:

    def __init__(self, db):
        self.db = db

    # ── Public API ────────────────────────────────────────────────────────

    def check_intervention_needed(self, user_id: str, topic: str) -> dict | None:
        """
        Call this after a wrong answer.
        Returns intervention dict if student needs prerequisite help, else None.

        intervention = {
            'trigger_topic':   'Kinematics',
            'chain':           ['Trigonometry', 'Basic Vectors', 'Kinematics'],
            'gaps':            [{'topic': 'Trigonometry', 'mastery': 0.32, 'is_gap': True}, ...],
            'weakest':         'Trigonometry',
            'weakest_subject': 'Mathematics',
            'message':         'Your Kinematics struggles trace back to Trigonometry (32% mastery)'
        }
        """
        failure_count = self._get_recent_failure_count(user_id, topic)
        if failure_count < FAILURE_THRESHOLD:
            return None

        prereqs = PREREQ_DAG.get(topic, [])
        if not prereqs:
            return None

        # Build full chain (topological) up to depth 2
        chain = self._get_prereq_chain(topic, depth=2)
        if not chain:
            return None

        # Get mastery for each node in chain
        gaps = []
        for prereq_topic in chain[:-1]:  # exclude the trigger topic itself
            mastery = self._get_topic_mastery(user_id, prereq_topic)
            gaps.append({
                'topic':    prereq_topic,
                'mastery':  mastery,
                'is_gap':   mastery < PREREQ_MASTERY_THRESHOLD,
                'subject':  self._guess_subject(prereq_topic)
            })

        real_gaps = [g for g in gaps if g['is_gap']]
        if not real_gaps:
            return None

        # Weakest prerequisite = root cause
        weakest = min(real_gaps, key=lambda g: g['mastery'])

        msg = (
            f"You've failed **{topic}** {failure_count} times. "
            f"Root cause detected: **{weakest['topic']}** "
            f"({weakest['mastery']*100:.0f}% mastery) — "
            f"this is a prerequisite you need to strengthen first."
        )

        return {
            'trigger_topic':   topic,
            'failure_count':   failure_count,
            'chain':           chain,
            'gaps':            gaps,
            'real_gaps':       real_gaps,
            'weakest':         weakest['topic'],
            'weakest_mastery': weakest['mastery'],
            'weakest_subject': weakest['subject'],
            'message':         msg
        }

    def get_prereq_chain_with_mastery(self, user_id: str, topic: str) -> list:
        """
        Returns the full prerequisite chain for a topic with mastery levels.
        Used by Knowledge Graph to highlight broken chains.
        """
        chain = self._get_prereq_chain(topic, depth=3)
        result = []
        for t in chain:
            mastery = self._get_topic_mastery(user_id, t)
            result.append({
                'topic':   t,
                'mastery': mastery,
                'is_gap':  mastery < PREREQ_MASTERY_THRESHOLD,
                'subject': self._guess_subject(t),
                'is_target': t == topic
            })
        return result

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_prereq_chain(self, topic: str, depth: int = 2) -> list:
        """BFS to get prerequisite chain up to given depth, returns ordered list."""
        if topic not in PREREQ_DAG:
            return []

        visited = []
        queue = deque([(topic, 0)])
        seen = set()

        while queue:
            current, d = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if d > 0:  # don't add the trigger topic yet
                visited.append(current)
            if d < depth:
                for prereq in PREREQ_DAG.get(current, []):
                    if prereq not in seen:
                        queue.append((prereq, d + 1))

        visited.reverse()      # deepest prerequisites first
        visited.append(topic)  # trigger topic at end
        return visited

    def _get_recent_failure_count(self, user_id: str, topic: str) -> int:
        """Count recent failures on a topic (last 10 attempts)."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT is_correct FROM attempts
                    WHERE user_id=? AND topic LIKE ?
                    ORDER BY timestamp DESC LIMIT 10
                ) WHERE is_correct = 0
            """, (user_id, f'%{topic}%'))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def _get_topic_mastery(self, user_id: str, topic: str) -> float:
        """Get mastery (0-1) for a topic from attempts table."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT
                    CAST(SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)
                FROM attempts
                WHERE user_id=? AND topic LIKE ?
            """, (user_id, f'%{topic}%'))
            result = cursor.fetchone()
            if result and result[0] is not None:
                return float(result[0])
            return 0.0   # no data = assume 0 mastery
        except Exception:
            return 0.0

    def _guess_subject(self, topic: str) -> str:
        """Guess subject from topic name for redirect purposes."""
        physics_topics = {
            "Kinematics", "Newton's Laws", "Circular Motion", "Waves",
            "Electrostatics", "Magnetism", "Optics", "Thermodynamics",
            "Gravitation", "Modern Physics", "Simple Harmonic Motion",
            "Work Energy Theorem", "Rotational Motion", "Projectile Motion",
            "Current Electricity", "Electromagnetic Induction", "Kinetic Theory"
        }
        math_topics = {
            "Trigonometry", "Basic Vectors", "Vectors", "Algebra",
            "Calculus Basics", "Differentiation", "Integration", "Matrices",
            "Probability", "Coordinate Geometry", "Complex Numbers", "Limits",
            "Continuity", "Differentiability", "3D Geometry", "Determinants",
            "Permutation Combination", "Binomial Theorem", "Sequences Series",
            "Differential Equations"
        }
        chem_topics = {
            "Atomic Structure", "Chemical Bonding", "Mole Concept",
            "Chemical Equilibrium", "Organic Reactions", "Electrochemistry",
            "Thermodynamics Chem", "Redox Reactions", "Periodic Table",
            "Ionic Equilibrium", "Basic Chemistry", "Basic Organic",
            "Aromatic Compounds", "Polymers", "Biomolecules", "Surface Chemistry",
            "Coordination Compounds"
        }
        cs_topics = {
            "Arrays", "Linked List", "Trees", "Graphs", "Recursion",
            "Dynamic Programming", "Sorting", "Searching", "Stack", "Queue",
            "Hashing", "Heaps", "BFS DFS", "Shortest Path", "Time Complexity",
            "Pointers", "SQL", "Database", "Operating Systems", "Process Thread",
            "Binary Search Tree", "Basic Programming"
        }
        bio_topics = {
            "Cell Biology", "Genetics", "DNA RNA", "Photosynthesis",
            "Respiration", "Evolution", "Human Physiology", "Plant Physiology",
            "Ecosystem", "Reproduction", "Biochemistry"
        }

        if topic in physics_topics:
            return "Physics"
        if topic in math_topics:
            return "Mathematics"
        if topic in chem_topics:
            return "Chemistry"
        if topic in cs_topics:
            return "Computer Science"
        if topic in bio_topics:
            return "Biology"
        return "General"


# ═══════════════════════════════════════════════════════════════════════════
# UI — INTERVENTION CARD
# ═══════════════════════════════════════════════════════════════════════════

def render_prerequisite_intervention(intervention: dict, on_fix_click=None):
    """
    Renders the intervention card when a prerequisite gap is detected.

    intervention: dict returned by PrerequisiteEngine.check_intervention_needed()
    on_fix_click: callback(subject, topic) when student clicks "Fix Now"
    """
    import streamlit as st

    trigger  = intervention['trigger_topic']
    chain    = intervention['chain']
    gaps     = intervention['gaps']
    weakest  = intervention['weakest']
    failures = intervention['failure_count']

    st.markdown("---")
    st.error(f"🔍 **Root Cause Detected** — You've failed **{trigger}** {failures} times")

    with st.container():
        st.markdown(
            """
            <div style="background:#1a1a2e;border:1px solid #e74c3c;
                        border-radius:12px;padding:20px;margin:8px 0;">
            """,
            unsafe_allow_html=True
        )

        # Prerequisite chain visualization
        st.markdown("#### 🔗 Prerequisite Chain")

        chain_parts = []
        for t in chain:
            gap_data = next((g for g in gaps if g['topic'] == t), None)
            if t == trigger:
                chain_parts.append(f"**{t}** ← *you're stuck here*")
            elif gap_data and gap_data['is_gap']:
                pct = gap_data['mastery'] * 100
                chain_parts.append(f"~~{t}~~ 🔴 {pct:.0f}%")
            elif gap_data:
                pct = gap_data['mastery'] * 100
                chain_parts.append(f"{t} ✅ {pct:.0f}%")
            else:
                chain_parts.append(t)

        st.markdown("  →  ".join(chain_parts))

        st.markdown("---")

        # Mastery bars for each prerequisite
        st.markdown("#### 📊 Your Mastery of Prerequisites")
        for g in gaps:
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                icon = "🔴" if g['is_gap'] else "✅"
                st.markdown(f"{icon} **{g['topic']}**")
            with col2:
                pct = g['mastery'] * 100
                bar_filled = int(pct / 10)
                bar = "█" * bar_filled + "░" * (10 - bar_filled)
                color = "#e74c3c" if g['is_gap'] else "#2ecc71"
                st.markdown(
                    f"<span style='color:{color};font-family:monospace'>{bar}</span> {pct:.0f}%",
                    unsafe_allow_html=True
                )
            with col3:
                if g['is_gap']:
                    st.markdown("← GAP")

        st.markdown("---")

        # Key insight
        weakest_data = next((g for g in gaps if g['topic'] == weakest), None)
        weakest_pct  = (weakest_data['mastery'] * 100) if weakest_data else 0
        st.markdown(
            f"💡 **\"Fixing {weakest} first ({weakest_pct:.0f}% → 60%+) will "
            f"unlock {trigger} for you\"**"
        )

        # Action buttons
        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            weakest_subject = intervention.get('weakest_subject', 'General')
            if st.button(
                f"🎯 Fix {weakest} Now",
                type="primary",
                use_container_width=True,
                key=f"fix_prereq_{weakest}"
            ):
                if on_fix_click:
                    on_fix_click(weakest_subject, weakest)
                else:
                    import streamlit as st
                    st.session_state['prereq_redirect_subject'] = weakest_subject
                    st.session_state['prereq_redirect_topic']   = weakest
                    st.session_state['prereq_intervention_active'] = True
                st.rerun()

        with col2:
            if st.button(
                f"⏭ Skip — Try {trigger} Again",
                use_container_width=True,
                key=f"skip_prereq_{trigger}"
            ):
                st.session_state['prereq_intervention_dismissed'] = trigger
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH ENHANCEMENT
# Adds prerequisite chain overlay to existing knowledge graph
# ═══════════════════════════════════════════════════════════════════════════

def render_prereq_knowledge_graph(user_id, db):
    """
    Enhanced knowledge graph that shows prerequisite chains and highlights gaps.
    Replaces the basic render_knowledge_graph from analytics.py
    """
    import streamlit as st
    import plotly.graph_objects as go

    engine = PrerequisiteEngine(db)

    st.markdown("### 🕸️ Knowledge Graph + Prerequisite Chains")
    st.caption("Red nodes = gaps. Arrows show what you need to learn first.")

    # Get all topics the student has attempted
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT subject, topic,
               COUNT(*) as attempts,
               CAST(SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) AS FLOAT)/COUNT(*) as mastery
        FROM attempts
        WHERE user_id=? AND topic IS NOT NULL
        GROUP BY subject, topic
    """, (user_id,))
    rows = cursor.fetchall()

    if not rows:
        st.info("📚 Take an exam first to build your knowledge graph.")
        return

    # Build mastery dict
    mastery_map = {row[1]: row[3] for row in rows}

    # Find all topics with gaps and their prerequisite chains
    # Also includes topics not in DAG — any topic below threshold is a gap
    broken_chains = []
    for subj, topic, attempts, mastery in rows:
        if mastery < PREREQ_MASTERY_THRESHOLD:
            prereqs = PREREQ_DAG.get(topic, [])
            broken_chains.append({
                'topic':   topic,
                'mastery': mastery,
                'prereqs': prereqs,   # empty list if not in DAG — still shown as gap
                'subject': subj
            })

    # ── Subject-wise mastery overview ────────────────────────────────────
    subjects = {}
    for subj, topic, attempts, mastery in rows:
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append({'topic': topic, 'mastery': mastery, 'attempts': attempts})

    for subject, topics in subjects.items():
        avg = sum(t['mastery'] for t in topics) / len(topics) * 100
        color = "🟢" if avg >= 70 else "🟡" if avg >= 40 else "🔴"
        with st.expander(f"{color} **{subject}** — {avg:.0f}% avg mastery ({len(topics)} topics)", expanded=True):
            cols = st.columns(min(3, len(topics)))
            for i, t in enumerate(topics):
                with cols[i % 3]:
                    pct = t['mastery'] * 100
                    node_color = "#2ecc71" if pct >= 70 else "#f39c12" if pct >= 40 else "#e74c3c"
                    st.markdown(
                        f"<div style='background:#1a1a2e;border:2px solid {node_color};"
                        f"border-radius:8px;padding:10px;margin:4px;text-align:center'>"
                        f"<b>{t['topic']}</b><br>"
                        f"<span style='color:{node_color};font-size:18px'>{pct:.0f}%</span><br>"
                        f"<small>{t['attempts']} attempts</small></div>",
                        unsafe_allow_html=True
                    )

    # ── Broken prerequisite chains ────────────────────────────────────────
    if broken_chains:
        st.markdown("---")
        st.markdown("### 🔗 Broken Prerequisite Chains")
        st.caption("These topics are weak because their foundations are shaky")

        for bc in broken_chains[:5]:  # show top 5
            topic   = bc['topic']
            mastery = bc['mastery'] * 100
            chain   = engine.get_prereq_chain_with_mastery(user_id, topic)

            st.markdown(
                f"<div style='background:#1a1a2e;border:1px solid #e74c3c;"
                f"border-radius:10px;padding:16px;margin:8px 0'>",
                unsafe_allow_html=True
            )

            # Chain visualization
            parts = []
            for node in chain:
                pct = node['mastery'] * 100
                if node['is_target']:
                    parts.append(f"**{node['topic']}** ({pct:.0f}%)")
                elif node['is_gap']:
                    parts.append(f"🔴 {node['topic']} ({pct:.0f}%)")
                else:
                    parts.append(f"✅ {node['topic']} ({pct:.0f}%)")

            chain_str = "  →  ".join(parts)
            st.markdown(f"**{topic}** ({mastery:.0f}% mastery): {chain_str}")

            # Find weakest prereq
            prereq_nodes = [n for n in chain if not n['is_target']]
            if prereq_nodes:
                weakest = min(prereq_nodes, key=lambda n: n['mastery'])
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(
                        f"💡 Fix **{weakest['topic']}** first "
                        f"({weakest['mastery']*100:.0f}% → 60%) to unlock **{topic}**"
                    )
                with col2:
                    if st.button(
                        f"🎯 Fix {weakest['topic']}",
                        key=f"kg_fix_{topic}_{weakest['topic']}",
                        use_container_width=True
                    ):
                        st.session_state['prereq_redirect_subject'] = weakest['subject']
                        st.session_state['prereq_redirect_topic']   = weakest['topic']
                        st.info(f"✅ Go to Adaptive Practice tab → {weakest['subject']} → {weakest['topic']}")

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Only show "solid" if truly no weak topics at all
        all_mastered = all(r[3] >= PREREQ_MASTERY_THRESHOLD for r in rows)
        if all_mastered:
            st.success("✅ No broken prerequisite chains detected! All your foundations look solid.")
        else:
            # Has weak topics but none match DAG — still show them
            weak_rows = [(r[0], r[1], r[2], r[3]) for r in rows if r[3] < PREREQ_MASTERY_THRESHOLD]
            st.markdown("---")
            st.markdown("### ⚠️ Topics Needing Work")
            st.caption("These topics have low mastery — practice them to strengthen your foundation")
            for subj, topic, attempts, mastery in weak_rows:
                pct = mastery * 100
                st.markdown(
                    f"<div style='background:#1a1a2e;border:1px solid #e74c3c;"
                    f"border-radius:8px;padding:12px;margin:6px 0'>"
                    f"🔴 <b>{topic}</b> ({subj}) — "
                    f"<span style='color:#e74c3c'>{pct:.0f}% mastery</span> · "
                    f"{attempts} attempts"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # ── Stats ─────────────────────────────────────────────────────────────
    st.markdown("---")
    total = len(rows)
    mastered_count  = sum(1 for r in rows if r[3] >= 0.70)
    in_progress     = sum(1 for r in rows if 0.40 <= r[3] < 0.70)
    needs_work      = sum(1 for r in rows if r[3] < 0.40)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Topics Attempted", total)
    c2.metric("✅ Mastered (70%+)",   mastered_count)
    c3.metric("📈 In Progress",        in_progress)
    c4.metric("🔴 Needs Work",         needs_work)