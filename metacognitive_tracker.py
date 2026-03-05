"""
metacognitive_tracker.py - Real-Time Meta-Cognitive Behavioral Analysis
                          + Daily Spaced Repetition Review Queue

FEATURE 3: Answer Switching Tracker
  Tracks every answer change during a quiz:
  - Correct → Wrong  = second-guessing / overconfidence erosion
  - Wrong  → Correct = successful recall / hesitation resolved
  - Wrong  → Wrong   = confused searching
  Detects "Guessing" (< 5s answer) vs "Deep Uncertainty" (3+ switches).

FEATURE 4: Daily Review Queue (closes the feedback loop)
  Uses the DKT/BKT forgetting curve math already computed in
  deep_knowledge_tracker.py to generate a "review NOW" list on login.
  No new ML needed — just surfaces the data already being computed.

Integration points:
  - Call track_answer_change() from render_mcq_practice() on every radio change
  - Call render_session_summary() after quiz submission
  - Call render_daily_review_queue() in the sidebar / on login
"""

import streamlit as st
from datetime import datetime, timedelta
import time
from collections import Counter, defaultdict
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3 — ANSWER SWITCHING TRACKER
# ═══════════════════════════════════════════════════════════════════════════

class AnswerSwitchTracker:
    """
    Records every answer change per question during a quiz session.
    Reveals HOW a student thinks, not just WHAT they got wrong.
    """

    def __init__(self):
        # {q_idx: [{'from': ans, 'to': ans, 'timestamp': float, 'time_since_first': float}]}
        self.switch_log: dict = defaultdict(list)
        self.first_answer_time: dict = {}   # {q_idx: timestamp}
        self.first_answers: dict = {}       # {q_idx: first answer selected}

    def record_change(self, q_idx: int, old_answer: str, new_answer: str):
        """Call this every time a radio button changes."""
        now = time.time()

        if q_idx not in self.first_answer_time:
            self.first_answer_time[q_idx] = now
            self.first_answers[q_idx] = old_answer if old_answer else new_answer

        elapsed = now - self.first_answer_time.get(q_idx, now)

        self.switch_log[q_idx].append({
            'from': old_answer,
            'to':   new_answer,
            'timestamp': now,
            'time_on_question': round(elapsed, 1)
        })

    def analyse(self, questions: list, final_answers: dict) -> dict:
        """
        Analyse all switches against correct answers.
        Returns rich dict of cognitive patterns.
        """
        events = []
        pattern_counts = Counter()

        for q_idx, switches in self.switch_log.items():
            if q_idx >= len(questions):
                continue
            q = questions[q_idx]
            correct = str(q.get('correct_answer', '')).strip().upper()
            final   = str(final_answers.get(q_idx, '')).strip().upper()
            first   = str(self.first_answers.get(q_idx, '')).strip().upper()

            # Time to first answer
            first_time = self.first_answer_time.get(q_idx, 0)
            last_switch_time = switches[-1]['timestamp'] if switches else first_time
            total_time = round(last_switch_time - first_time, 1)

            # Classify behaviour
            behaviour = self._classify(first, final, correct, switches, total_time)
            pattern_counts[behaviour['pattern']] += 1

            events.append({
                'q_idx':      q_idx,
                'question':   q.get('question', '')[:80],
                'first_ans':  first,
                'final_ans':  final,
                'correct':    correct,
                'switches':   len(switches),
                'total_time': total_time,
                'pattern':    behaviour['pattern'],
                'label':      behaviour['label'],
                'icon':       behaviour['icon'],
                'insight':    behaviour['insight'],
            })

        # Session-level summary
        total_q   = len(questions)
        switched  = len(self.switch_log)
        guesses   = sum(1 for e in events if e['pattern'] == 'guessing')
        second_guess_losses = sum(
            1 for e in events if e['pattern'] == 'second_guess_loss'
        )
        confident_recalls = sum(
            1 for e in events if e['pattern'] == 'recall_win'
        )

        dominant = pattern_counts.most_common(1)[0][0] if pattern_counts else 'normal'

        return {
            'events':              events,
            'pattern_counts':      dict(pattern_counts),
            'total_questions':     total_q,
            'questions_switched':  switched,
            'guesses_detected':    guesses,
            'second_guess_losses': second_guess_losses,
            'confident_recalls':   confident_recalls,
            'dominant_pattern':    dominant,
            'switch_rate':         round(switched / max(total_q, 1) * 100, 1),
            'cognitive_summary':   self._cognitive_summary(
                dominant, guesses, second_guess_losses, confident_recalls
            )
        }

    def _classify(self, first, final, correct, switches, total_time) -> dict:
        """Classify the cognitive event for one question."""
        n_switches = len(switches)

        # Guessing: answered in < 5 seconds with no switches
        if total_time < 5 and n_switches == 0:
            return {
                'pattern': 'guessing',
                'label':   'Instant Guess',
                'icon':    '🎲',
                'insight': 'Answered in < 5s — likely guessing without reading.'
            }

        # No switch at all
        if n_switches == 0:
            if final == correct:
                return {'pattern': 'confident_correct', 'label': 'Confident & Correct',
                        'icon': '✅', 'insight': 'Direct confident answer.'}
            return {'pattern': 'confident_wrong', 'label': 'Confidently Wrong',
                    'icon': '❌', 'insight': 'Answered without hesitation but incorrectly — concept gap.'}

        # One switch
        if n_switches == 1:
            if first == correct and final != correct:
                return {'pattern': 'second_guess_loss', 'label': 'Changed Correct → Wrong',
                        'icon': '😰', 'insight': 'Knew the answer but talked yourself out of it. Trust your instinct!'}
            if first != correct and final == correct:
                return {'pattern': 'recall_win', 'label': 'Changed Wrong → Correct',
                        'icon': '💡', 'insight': 'Hesitated but recalled correctly. Good recovery.'}
            return {'pattern': 'swap_wrong', 'label': 'Wrong → Different Wrong',
                    'icon': '🔄', 'insight': 'Switched between wrong options — deep uncertainty about this concept.'}

        # Multiple switches (3+): deep confusion
        if n_switches >= 3:
            return {'pattern': 'deep_confusion', 'label': 'Deep Confusion',
                    'icon': '🌀', 'insight': f'Changed answer {n_switches} times — strong uncertainty. Review this topic thoroughly.'}

        # Two switches
        if final == correct:
            return {'pattern': 'recovery', 'label': 'Eventually Correct',
                    'icon': '🔁', 'insight': 'Needed two attempts to settle on correct answer.'}
        return {'pattern': 'oscillation', 'label': 'Oscillating',
                'icon': '↔️', 'insight': 'Uncertain — went back and forth without landing on correct answer.'}

    def _cognitive_summary(self, dominant, guesses, losses, recalls) -> str:
        summaries = {
            'second_guess_loss': (
                f"🚨 You changed {losses} correct answer(s) to wrong ones. "
                "This is a confidence problem, NOT a knowledge gap. "
                "Strategy: Once confident, don't go back unless you spot a clear error."
            ),
            'guessing': (
                f"⚠️ {guesses} question(s) answered in under 5 seconds. "
                "Read each question fully before selecting. "
                "Guessing on JEE-style papers with negative marking is risky."
            ),
            'deep_confusion': (
                "🌀 Multiple back-and-forth switches detected. "
                "This signals gaps in core concepts — not just formula errors. "
                "Review fundamentals for affected topics."
            ),
            'recall_win': (
                f"✅ You successfully recalled correct answers after initial hesitation {recalls} time(s). "
                "Your knowledge is there — you just need to trust it faster."
            ),
            'confident_wrong': (
                "📚 You answered confidently but incorrectly on several questions. "
                "This is a classic concept misconception pattern. "
                "Review the explanation for each wrong answer carefully."
            ),
        }
        return summaries.get(dominant, "📊 Mixed performance patterns detected. Review detailed question analysis below.")

    def reset(self):
        self.switch_log.clear()
        self.first_answer_time.clear()
        self.first_answers.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3 UI — SESSION SUMMARY AFTER QUIZ
# ═══════════════════════════════════════════════════════════════════════════

def render_metacognitive_analysis(tracker: AnswerSwitchTracker,
                                  questions: list,
                                  final_answers: dict):
    """
    Render the meta-cognitive analysis panel after quiz submission.
    Call this inside render_mcq_practice() after the score card.
    """
    analysis = tracker.analyse(questions, final_answers)

    st.divider()
    st.markdown("### 🧠 Meta-Cognitive Behaviour Analysis")
    st.caption("How you *think* during questions — beyond just right/wrong")

    # ── Top KPIs ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions Switched",
                  f"{analysis['questions_switched']}/{analysis['total_questions']}",
                  help="Questions where you changed your answer")
    with col2:
        st.metric("Second-Guess Losses", analysis['second_guess_losses'],
                  delta=f"-{analysis['second_guess_losses']} marks" if analysis['second_guess_losses'] else None,
                  delta_color="inverse",
                  help="Times you changed a correct answer to wrong")
    with col3:
        st.metric("Guesses Detected", analysis['guesses_detected'],
                  help="Questions answered in < 5 seconds")
    with col4:
        st.metric("Recall Wins", analysis['confident_recalls'],
                  help="Times you changed wrong → correct")

    # ── Cognitive summary ─────────────────────────────────────────────────
    if analysis['second_guess_losses'] > 0:
        st.error(analysis['cognitive_summary'])
    elif analysis['guesses_detected'] > 2:
        st.warning(analysis['cognitive_summary'])
    elif analysis['confident_recalls'] > 0:
        st.success(analysis['cognitive_summary'])
    else:
        st.info(analysis['cognitive_summary'])

    # ── Pattern breakdown ─────────────────────────────────────────────────
    if analysis['pattern_counts']:
        st.markdown("#### 📊 Behaviour Pattern Breakdown")
        pattern_labels = {
            'second_guess_loss': '😰 Changed Correct→Wrong',
            'recall_win':        '💡 Changed Wrong→Correct',
            'guessing':          '🎲 Instant Guess (<5s)',
            'deep_confusion':    '🌀 Deep Confusion (3+ switches)',
            'confident_correct': '✅ Confident & Correct',
            'confident_wrong':   '❌ Confidently Wrong',
            'oscillation':       '↔️ Oscillating',
            'swap_wrong':        '🔄 Wrong→Different Wrong',
            'recovery':          '🔁 Eventually Correct',
        }
        for pattern, count in sorted(analysis['pattern_counts'].items(),
                                     key=lambda x: x[1], reverse=True):
            label = pattern_labels.get(pattern, pattern)
            st.markdown(f"**{label}:** {count} question(s)")

    # ── Per-question events ───────────────────────────────────────────────
    if analysis['events']:
        st.markdown("#### 🔍 Question-by-Question Cognitive Events")
        for ev in analysis['events']:
            if ev['pattern'] in ('confident_correct',):
                continue  # skip boring ones
            with st.expander(
                f"{ev['icon']} Q{ev['q_idx']+1} — {ev['label']} "
                f"({'✅' if ev['final_ans']==ev['correct'] else '❌'})"
            ):
                st.markdown(f"**{ev['question']}...**")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("First Answer", ev['first_ans'] or "—")
                with col_b:
                    st.metric("Final Answer", ev['final_ans'] or "—")
                with col_c:
                    st.metric("Correct", ev['correct'])
                st.caption(f"⏱️ Time on question: {ev['total_time']}s | Switches: {ev['switches']}")
                st.info(f"💭 Insight: {ev['insight']}")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 4 — DAILY REVIEW QUEUE  (closes the feedback loop)
# ═══════════════════════════════════════════════════════════════════════════

def get_daily_review_queue(user_id: str, dkt_tracker, max_topics: int = 5) -> list:
    """
    Uses the forgetting-curve data already computed in DeepKnowledgeTracker
    to generate today's review list.

    Priority formula (higher = review NOW):
        P = (1 - mastery) * 10              # weak topics first
          + forgetting_urgency_score        # topics about to be forgotten
          + (1 if learning_velocity < 0)    # declining topics

    Returns list of dicts sorted by priority.
    """
    try:
        all_masteries = dkt_tracker.get_all_concept_masteries(user_id)
    except Exception:
        return []

    if not all_masteries:
        return []

    queue = []
    for m in all_masteries:
        P_L    = m['mastery_probability']
        days   = m['days_since_practice']
        vel    = m['learning_velocity']
        f_risk = m['forgetting_risk']

        # forgetting urgency
        if f_risk == 'high':
            f_score = 8
        elif f_risk == 'medium':
            f_score = 4
        else:
            # Even low-risk: boost if mastery close to threshold
            f_score = max(0, (7 - days) * 0.3)

        priority = (1 - P_L) * 10 + f_score + (2 if vel < -0.02 else 0)

        # Estimate minutes needed
        if P_L < 0.4:
            minutes = 20
        elif P_L < 0.6:
            minutes = 12
        else:
            minutes = 6

        # Next optimal review date (SM-2 inspired)
        if days < 1:
            next_review = "Tomorrow"
        elif days < 3:
            next_review = f"In {3 - days} days"
        else:
            next_review = "Now ⚡"

        queue.append({
            'subject':     m['subject'],
            'topic':       m['topic'],
            'mastery':     P_L,
            'days_since':  days,
            'forgetting_risk': f_risk,
            'velocity':    vel,
            'priority':    round(priority, 2),
            'minutes':     minutes,
            'next_review': next_review,
            'reason':      _review_reason(P_L, days, vel, f_risk)
        })

    queue.sort(key=lambda x: x['priority'], reverse=True)
    return queue[:max_topics]


def _review_reason(mastery, days, velocity, f_risk) -> str:
    if f_risk == 'high' and mastery < 0.5:
        return f"🚨 Not practiced in {days} days AND mastery is low — urgent!"
    if f_risk == 'high':
        return f"⏰ {days} days since last practice — forgetting curve is steep."
    if velocity < -0.02:
        return "📉 Your accuracy on this topic has been declining."
    if mastery < 0.4:
        return f"📚 Only {mastery*100:.0f}% mastery — needs more practice."
    if mastery < 0.6:
        return f"⚡ {mastery*100:.0f}% mastery — at the optimal spaced-repetition window."
    return "🔄 Periodic maintenance review recommended."


def render_daily_review_queue(user_id: str, dkt_tracker,
                               on_practice_click=None):
    """
    Renders the Daily Review Queue widget.

    Place this:
      1. In the SIDEBAR (compact version) — shows topic count badge
      2. In a dedicated 'Today's Plan' section on the main page

    on_practice_click: optional callable(subject, topic) triggered when
                       user clicks 'Practice Now' for a topic.
    """
    queue = get_daily_review_queue(user_id, dkt_tracker, max_topics=5)

    if not queue:
        st.info("🎉 No urgent reviews today! Keep practising to build your queue.")
        return

    # Badge summary
    urgent   = sum(1 for q in queue if q['forgetting_risk'] == 'high')
    total_min = sum(q['minutes'] for q in queue)

    st.markdown("### 📅 Today's Review Queue")
    st.caption(
        f"Based on your forgetting curve — {len(queue)} topics need attention"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Topics to Review", len(queue))
    with col2:
        st.metric("🚨 Urgent", urgent,
                  delta_color="inverse",
                  delta=f"-{urgent} at risk" if urgent else None)
    with col3:
        st.metric("⏱️ Est. Time", f"{total_min} min")

    st.divider()

    for i, item in enumerate(queue, 1):
        risk_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            item['forgetting_risk'], "⚪"
        )
        with st.expander(
            f"{risk_color} {i}. {item['subject']} → {item['topic']}  "
            f"| {item['mastery']*100:.0f}% mastery | {item['next_review']}",
            expanded=(i == 1)
        ):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Mastery", f"{item['mastery']*100:.0f}%")
                st.progress(item['mastery'])
            with col_b:
                st.metric("Days Since Practice", item['days_since'])
            with col_c:
                st.metric("Est. Review Time", f"{item['minutes']} min")

            st.info(item['reason'])

            if item['velocity'] < -0.02:
                st.warning(f"📉 Accuracy declining ({item['velocity']*100:+.1f}%/session)")

            if on_practice_click:
                if st.button(
                    f"🚀 Practice {item['topic']} Now",
                    key=f"review_btn_{i}_{abs(hash(item['subject'] + item['topic']))}",  # full hash avoids truncation collisions
                    use_container_width=True,
                    type="primary"
                ):
                    on_practice_click(item['subject'], item['topic'])


def render_sidebar_review_badge(user_id: str, dkt_tracker):
    """
    Compact sidebar widget showing review count.
    Call from render_sidebar() in app.py.
    """
    try:
        queue = get_daily_review_queue(user_id, dkt_tracker, max_topics=10)
    except Exception:
        return

    if not queue:
        st.sidebar.success("✅ No reviews due today")
        return

    urgent = sum(1 for q in queue if q['forgetting_risk'] == 'high')
    st.sidebar.divider()
    st.sidebar.markdown("### 📅 Review Queue")

    if urgent > 0:
        st.sidebar.error(f"🚨 {urgent} urgent review(s) due!")
    st.sidebar.info(f"📚 {len(queue)} topic(s) to review today")

    for item in queue[:3]:
        risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            item['forgetting_risk'], "⚪"
        )
        st.sidebar.caption(
            f"{risk_icon} {item['topic']} — {item['mastery']*100:.0f}%"
        )


# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE HELPERS  (for app.py integration)
# ═══════════════════════════════════════════════════════════════════════════

def init_tracker() -> AnswerSwitchTracker:
    """Get or create the session-level answer switch tracker."""
    if 'answer_switch_tracker' not in st.session_state:
        st.session_state.answer_switch_tracker = AnswerSwitchTracker()
    return st.session_state.answer_switch_tracker


def reset_tracker():
    """Call when starting a new quiz."""
    st.session_state.answer_switch_tracker = AnswerSwitchTracker()


def track_answer_change(q_idx: int, old_answer: str, new_answer: str):
    """
    Call this inside the MCQ loop whenever a radio button value changes.

    Example in render_mcq_practice():
        answer = st.radio("Answer:", options_keys, key=f"aq_{i}", index=None)
        prev   = st.session_state.user_answers.get(i)
        if answer is not None and answer != prev:
            track_answer_change(i, prev or '', answer)
            st.session_state.user_answers[i] = answer
    """
    tracker = init_tracker()
    if old_answer != new_answer:
        tracker.record_change(q_idx, old_answer or '', new_answer or '')


__all__ = [
    'AnswerSwitchTracker',
    'render_metacognitive_analysis',
    'get_daily_review_queue',
    'render_daily_review_queue',
    'render_sidebar_review_badge',
    'init_tracker',
    'reset_tracker',
    'track_answer_change',
]