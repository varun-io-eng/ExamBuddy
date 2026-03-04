"""
intelligent_question_generator.py - Compatible with AuthDatabase
Works without knowledge_nodes table
UPDATED: Enhanced context-awareness and better question generation
"""

import random
from collections import defaultdict
import numpy as np


class ConceptGraph:
    """Hierarchical concept dependency graph"""
    
    def __init__(self):
        self.concept_tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.dependencies = {}
        self.concept_difficulties = {}
        
        self._initialize_physics_concepts()
        self._initialize_chemistry_concepts()
        self._initialize_math_concepts()
    
    def _initialize_physics_concepts(self):
        """Initialize Physics concept graph"""
        self.concept_tree['Physics']['Kinematics']['Motion in 1D'] = [
            'Speed and velocity', 'Acceleration', 'Equations of motion', 'Free fall'
        ]
        self.concept_tree['Physics']['Kinematics']['Motion in 2D'] = [
            'Projectile motion', 'Relative velocity', 'Circular motion'
        ]
        self.concept_tree['Physics']['Dynamics']['Forces'] = [
            "Newton's laws", 'Free body diagrams', 'Friction', 'Tension'
        ]
        self.concept_tree['Physics']['Work-Energy']['Basic concepts'] = [
            'Work definition', 'Kinetic energy', 'Potential energy'
        ]
        self.concept_tree['Physics']['Waves']['Wave properties'] = [
            'Wave equation', 'Frequency', 'Wavelength'
        ]
        self.concept_tree['Physics']['Electromagnetism']['Electric Fields'] = [
            'Coulomb\'s law', 'Electric field intensity', 'Gauss\'s law'
        ]
        self.concept_tree['Physics']['Thermodynamics']['Heat Transfer'] = [
            'Conduction', 'Convection', 'Radiation', 'Laws of thermodynamics'
        ]
        
        self.dependencies['Motion in 2D'] = ['Motion in 1D']
        self.dependencies['Electromagnetism'] = ['Electric Fields']
    
    def _initialize_chemistry_concepts(self):
        """Initialize Chemistry"""
        self.concept_tree['Chemistry']['Atomic Structure']['Basic structure'] = [
            'Protons, neutrons, electrons', 'Atomic number', 'Isotopes'
        ]
        self.concept_tree['Chemistry']['Chemical Bonding']['Ionic bonding'] = [
            'Electronegativity', 'Ionic bond formation'
        ]
        self.concept_tree['Chemistry']['Chemical Bonding']['Covalent bonding'] = [
            'Lewis structures', 'Bond polarity', 'Molecular geometry'
        ]
        self.concept_tree['Chemistry']['Organic Chemistry']['Hydrocarbons'] = [
            'Alkanes', 'Alkenes', 'Alkynes', 'Aromatic compounds'
        ]
    
    def _initialize_math_concepts(self):
        """Initialize Mathematics"""
        self.concept_tree['Mathematics']['Algebra']['Linear equations'] = [
            'Solving equations', 'Word problems', 'Systems of equations'
        ]
        self.concept_tree['Mathematics']['Calculus']['Differentiation'] = [
            'Limits', 'Derivatives', 'Power rule', 'Chain rule'
        ]
        self.concept_tree['Mathematics']['Calculus']['Integration'] = [
            'Indefinite integrals', 'Definite integrals', 'Integration by parts'
        ]
        self.concept_tree['Mathematics']['Trigonometry']['Basic concepts'] = [
            'Sin, cos, tan', 'Identities', 'Graphs'
        ]
        
        self.dependencies['Integration'] = ['Differentiation']
    
    def get_all_concepts(self, subject=None):
        """Get all concepts"""
        concepts = []
        subjects = [subject] if subject else self.concept_tree.keys()
        
        for subj in subjects:
            if subj not in self.concept_tree:
                continue
            for topic, subtopics_dict in self.concept_tree[subj].items():
                for subtopic, micro_concepts in subtopics_dict.items():
                    for concept in micro_concepts:
                        concepts.append({
                            'subject': subj,
                            'topic': topic,
                            'subtopic': subtopic,
                            'concept': concept
                        })
        
        return concepts
    
    def get_prerequisites(self, subtopic):
        """Get prerequisites"""
        return self.dependencies.get(subtopic, [])


class IntelligentQuestionGenerator:
    """
    Question generation compatible with AuthDatabase
    Works with: subject, topic columns (no node_id)
    ENHANCED: Better context awareness from student history
    """
    
    def __init__(self, db, gemini_service, bkt_tracker):
        self.db = db
        self.gemini = gemini_service
        self.bkt = bkt_tracker
        self.concept_graph = ConceptGraph()
    
    def analyze_concept_coverage(self, user_id, subject):
        """
        Analyze concept coverage using subject/topic from database
        """
        all_concepts = self.concept_graph.get_all_concepts(subject)
        
        # Get user's mastery levels
        user_masteries = self.bkt.get_all_concept_masteries(user_id)
        
        # Create lookup
        mastery_lookup = {}
        for m in user_masteries:
            if m['subject'] == subject:
                key = f"{m['topic']}"
                mastery_lookup[key] = m['mastery_probability']
        
        # Categorize
        coverage = {
            'not_attempted': [],
            'weak': [],
            'developing': [],
            'mastered': []
        }
        
        # Group concepts by topic
        seen_topics = set()
        
        for concept in all_concepts:
            topic_key = f"{concept['topic']}"
            
            # Only process each topic once
            if topic_key in seen_topics:
                continue
            seen_topics.add(topic_key)
            
            mastery = mastery_lookup.get(topic_key, None)
            
            if mastery is None:
                coverage['not_attempted'].append(concept)
            elif mastery < 0.5:
                coverage['weak'].append({**concept, 'mastery': mastery})
            elif mastery < 0.7:
                coverage['developing'].append({**concept, 'mastery': mastery})
            else:
                coverage['mastered'].append({**concept, 'mastery': mastery})
        
        return coverage
    
    def get_concept_focus_areas(self, user_id, subject):
        """Determine which concepts to focus on"""
        coverage = self.analyze_concept_coverage(user_id, subject)
        
        focus_areas = []
        
        # Priority 1: Weak concepts
        for weak_concept in coverage['weak'][:3]:
            focus_areas.append({
                'concept': weak_concept,
                'priority': 'high',
                'reason': f"Low mastery: {weak_concept['mastery']*100:.0f}%",
                'focus_type': 'remediation'
            })
        
        # Priority 2: Not attempted
        for new_concept in coverage['not_attempted'][:5]:
            focus_areas.append({
                'concept': new_concept,
                'priority': 'medium',
                'reason': 'New concept - ready to learn',
                'focus_type': 'new_learning'
            })
        
        return focus_areas[:10]
    
    def generate_targeted_questions(self, user_id, subject, count=10, difficulty='adaptive'):
        """
        Generate questions with concept coverage awareness
        ENHANCED: Uses student's recent performance context
        """
        # Get recent performance context
        recent_context = self._get_student_context(user_id, subject)
        
        focus_areas = self.get_concept_focus_areas(user_id, subject)
        
        if not focus_areas:
            return self._generate_general_questions(subject, count, recent_context)
        
        allocations = {
            'remediation': int(count * 0.4),
            'new_learning': int(count * 0.4),
            'progression': int(count * 0.2)
        }
        
        questions_by_type = defaultdict(list)
        for area in focus_areas:
            questions_by_type[area['focus_type']].append(area)
        
        all_questions = []
        
        for focus_type, allocation in allocations.items():
            if allocation == 0 or not questions_by_type[focus_type]:
                continue
            
            areas = questions_by_type[focus_type]
            questions_per_area = max(1, allocation // len(areas))
            
            for area in areas[:allocation]:
                concept = area['concept']
                topic = concept.get('topic', subject)
                
                # Determine difficulty
                if difficulty == 'adaptive':
                    mastery = concept.get('mastery', 0.5)
                    if mastery < 0.4:
                        q_difficulty = 'easy'
                    elif mastery < 0.7:
                        q_difficulty = 'medium'
                    else:
                        q_difficulty = 'hard'
                else:
                    q_difficulty = difficulty
                
                generated = self._generate_concept_questions(
                    subject, topic, None, q_difficulty, 
                    questions_per_area, area['reason'], recent_context
                )
                
                all_questions.extend(generated)
                
                if len(all_questions) >= count:
                    break
            
            if len(all_questions) >= count:
                break
        
        # Fill remaining
        while len(all_questions) < count and questions_by_type.get('remediation'):
            area = random.choice(questions_by_type['remediation'])
            concept = area['concept']
            generated = self._generate_concept_questions(
                subject, concept['topic'], None, 'medium', 1, None, recent_context
            )
            all_questions.extend(generated)
            if len(all_questions) >= count:
                break
        
        return all_questions[:count]
    
    def _get_student_context(self, user_id, subject):
        """
        Get recent student performance context for better question generation
        CONTEXT-AWARE FEATURE: Analyzes recent mistakes and patterns
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT question, is_correct, topic, difficulty
            FROM attempts
            WHERE user_id = ? AND subject = ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (user_id, subject))
        
        recent_attempts = cursor.fetchall()
        
        if not recent_attempts:
            return {
                'accuracy': 0.5,
                'weak_topics': [],
                'common_mistakes': [],
                'difficulty_level': 'medium'
            }
        
        # Calculate recent accuracy
        correct_count = sum(1 for a in recent_attempts if a[1])
        accuracy = correct_count / len(recent_attempts)
        
        # Find weak topics
        topic_performance = defaultdict(lambda: {'correct': 0, 'total': 0})
        for _, is_correct, topic, _ in recent_attempts:
            if topic:
                topic_performance[topic]['total'] += 1
                if is_correct:
                    topic_performance[topic]['correct'] += 1
        
        weak_topics = [
            topic for topic, perf in topic_performance.items()
            if perf['total'] >= 2 and (perf['correct'] / perf['total']) < 0.5
        ]
        
        # Determine appropriate difficulty
        if accuracy >= 0.8:
            difficulty_level = 'hard'
        elif accuracy >= 0.6:
            difficulty_level = 'medium'
        else:
            difficulty_level = 'easy'
        
        return {
            'accuracy': accuracy,
            'weak_topics': weak_topics[:3],
            'common_mistakes': [],  # Can be enhanced with mistake pattern analysis
            'difficulty_level': difficulty_level,
            'recent_topics': list(topic_performance.keys())[:5]
        }
    
    def _generate_concept_questions(self, subject, topic, subtopic, difficulty, count, focus_reason=None, context=None):
        """
        Generate questions for a specific concept
        ENHANCED: Uses context to generate more relevant questions
        """
        # Build context-aware prompt
        context_info = ""
        if context:
            if context['weak_topics']:
                context_info += f"\nStudent struggles with: {', '.join(context['weak_topics'])}"
            context_info += f"\nStudent's current accuracy: {context['accuracy']*100:.0f}%"
        
        prompt = f"""Generate {count} UNIQUE multiple choice questions on:
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

{f"Focus: {focus_reason}" if focus_reason else ""}
{context_info}

IMPORTANT: Make questions clear, educational, and progressively challenging.
Avoid repetitive patterns. Include practical applications where possible.

Return ONLY JSON array (no markdown, no extra text):
[
  {{
    "question": "...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "A",
    "explanation": "...",
    "subtopic": "{topic}"
  }}
]"""
        
        try:
            response = self.gemini.chat(prompt, temperature=0.8)
            import re, json
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                for q in questions:
                    q['subject'] = subject
                    q['topic'] = topic
                    q['difficulty'] = difficulty
                    q['generated_by'] = 'intelligent_generator'
                return questions
        except Exception as e:
            print(f"Error generating questions: {e}")
        
        return []
    
    def _generate_general_questions(self, subject, count, context=None):
        """Fallback general questions with context awareness"""
        context_info = ""
        if context and context.get('weak_topics'):
            context_info = f"Focus on topics: {', '.join(context['weak_topics'][:3])}"
        
        prompt = f"""Generate {count} multiple choice questions on {subject}.
{context_info}
Return ONLY JSON array (no markdown):
[{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct_answer": "A", "explanation": "..."}}]"""
        
        try:
            response = self.gemini.chat(prompt, temperature=0.7)
            import re, json
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                for q in questions:
                    q['subject'] = subject
                    q['topic'] = subject
                return questions
        except Exception as e:
            print(f"Error: {e}")
        
        return []
    
    def get_coverage_report(self, user_id, subject):
        """Generate coverage report"""
        coverage = self.analyze_concept_coverage(user_id, subject)
        
        # Count unique topics
        seen = set()
        for cat in coverage.values():
            for item in cat:
                if isinstance(item, dict) and 'topic' in item:
                    seen.add(item['topic'])
        
        total_topics = len(seen) if seen else len(coverage['not_attempted']) + len(coverage['weak']) + len(coverage['developing']) + len(coverage['mastered'])
        
        return {
            'subject': subject,
            'total_concepts': total_topics,
            'not_attempted_count': len(coverage['not_attempted']),
            'weak_count': len(coverage['weak']),
            'developing_count': len(coverage['developing']),
            'mastered_count': len(coverage['mastered']),
            'coverage_percentage': round(
                (total_topics - len(coverage['not_attempted'])) / max(total_topics, 1) * 100, 1
            ) if total_topics > 0 else 0,
            'mastery_percentage': round(
                len(coverage['mastered']) / max(total_topics, 1) * 100, 1
            ) if total_topics > 0 else 0,
            'coverage_by_category': {
                'not_attempted': coverage['not_attempted'][:5],
                'weak': coverage['weak'][:5],
                'developing': coverage['developing'][:5],
                'mastered': coverage['mastered'][:5]
            }
        }


__all__ = ['ConceptGraph', 'IntelligentQuestionGenerator']