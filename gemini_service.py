"""
gemini_service.py - FINAL Version 3.1
UPDATED: Added structured context injection for student-aware AI responses
"""

from groq import Groq
import json
import streamlit as st
import re


class EnhancedGeminiService:
    """AI Service with PRIMARY LLM extraction + Context-Aware Responses"""
    
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"
        st.success(f"✅ Using Groq model: {self.model}")
    
    def _inject_student_context(self, prompt):
        """
        Inject student context into prompt if available
        This makes every LLM call student-aware and exam-aware
        """
        if hasattr(st.session_state, 'student_context') and st.session_state.student_context:
            context = st.session_state.student_context.get('context_string', '')
            if context:
                return f"""{context}

---

{prompt}

Remember: Tailor your response to this student's profile above."""
        return prompt
    
    def _chat(self, messages, temperature=0.6, inject_context=True):
        """Internal method for API calls with context injection"""
        try:
            # Inject context into user messages if enabled
            if inject_context and messages:
                for msg in messages:
                    if msg['role'] == 'user':
                        msg['content'] = self._inject_student_context(msg['content'])
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None
    
    def chat(self, prompt, temperature=0.6, inject_context=True):
        """Public chat method with optional context injection"""
        return self._chat([{"role": "user", "content": prompt}], temperature=temperature, inject_context=inject_context)
    
    @staticmethod
    def _sanitize_json_string(raw: str) -> str:
        """Sanitize JSON strings with LaTeX backslashes"""
        LEGAL_AFTER_BACKSLASH = set(r'"\/ bfnrt'.replace(' ', ''))
        out = []
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == '\\' and i + 1 < len(raw):
                nxt = raw[i + 1]
                if nxt in LEGAL_AFTER_BACKSLASH:
                    out.append(ch)
                    out.append(nxt)
                    i += 2
                elif nxt == 'u' and i + 5 < len(raw):
                    out.append(raw[i:i+6])
                    i += 6
                else:
                    out.append('\\\\')
                    i += 1
            else:
                out.append(ch)
                i += 1
        return ''.join(out)

    def extract_questions_from_pdf_text(self, pdf_text, max_questions=100):
        """
        Hybrid extraction: Regex first for good text, LLM for complex/incomplete text.
        """
        st.info("🔍 Starting enhanced extraction...")
        
        # Check if PDF text looks complete or incomplete
        incomplete_text = self._check_if_incomplete(pdf_text)
        
        if incomplete_text:
            st.warning("⚠️ Detected incomplete text extraction - using AI-primary approach")
            st.info("💡 For best results, install PyMuPDF: pip install pymupdf")
            
            # Use LLM-first for incomplete text
            return self._extract_with_llm_primary(pdf_text, max_questions)
        else:
            st.success("✅ Detected complete text extraction - using optimized hybrid approach")
            
            # Use regex-first for complete text
            return self._extract_with_regex_primary(pdf_text, max_questions)
    
    def _extract_with_regex_primary(self, pdf_text, max_questions):
        """Extract from complete PDF text using regex + LLM combination"""
        
        # ── STRATEGY 1: Enhanced Regex Extraction ─────────────────────────
        st.info("📋 Strategy 1: Pattern-based extraction...")
        regex_questions = self._extract_with_improved_regex(pdf_text)
        st.success(f"✅ Regex found: {len(regex_questions)} questions")
        
        # ── STRATEGY 2: LLM for remaining questions ───────────────────────
        if len(regex_questions) < 70:  # If we might be missing some
            st.info("📋 Strategy 2: AI extraction for remaining questions...")
            llm_questions = self._llm_extract_questions_enhanced(pdf_text)
            st.success(f"✅ AI found: {len(llm_questions)} questions")
            
            # Combine both
            all_questions = regex_questions + llm_questions
        else:
            all_questions = regex_questions
        
        # Deduplicate
        unique_questions = self._remove_duplicate_questions(all_questions)
        st.success(f"🎉 Total extracted: {len(unique_questions)} unique questions!")
        
        return unique_questions[:max_questions]
    
    def _extract_with_llm_primary(self, pdf_text, max_questions):
        """Extract from incomplete PDF text using LLM-primary approach"""
        
        # ── PRIMARY STRATEGY: LLM Extraction ──────────────────────────────
        st.info("📋 Using AI extraction (primary method)...")
        llm_questions = self._llm_extract_questions_enhanced(pdf_text)
        st.success(f"✅ AI extracted: {len(llm_questions)} questions")
        
        # ── SECONDARY STRATEGY: Count expected questions ──────────────────
        question_numbers = self._extract_question_numbers(pdf_text)
        st.info(f"📊 Found {len(question_numbers)} question markers")
        
        if len(llm_questions) == 0:
            st.error("❌ No valid questions found")
            return None
        
        unique_questions = self._remove_duplicate_questions(llm_questions)
        st.success(f"🎉 Successfully extracted {len(unique_questions)} unique questions!")
        
        if len(question_numbers) > len(unique_questions):
            st.warning(f"⚠️ Expected {len(question_numbers)} but got {len(unique_questions)}")
        
        return unique_questions[:max_questions]

    def _extract_with_improved_regex(self, text):
        """
        Improved regex extraction for complete PDF text.
        Handles the actual format from the PDF images.
        """
        questions = []
        
        # Pattern: Q followed by number, then question text, then options in two-column format
        pattern = re.compile(
            r'Q(\d+)\.\s*(.+?)(?=Q\d+\.|$)',
            re.DOTALL | re.MULTILINE
        )
        
        matches = list(pattern.finditer(text))
        
        for match in matches:
            q_num = int(match.group(1))
            body = match.group(2).strip()
            
            # Find where options start
            # Look for (1) followed by actual content
            opt_start = re.search(r'\n\s*\(1\)\s+\S', body)
            
            if not opt_start:
                continue
            
            stem = body[:opt_start.start()].strip()
            opt_text = body[opt_start.start():].strip()
            
            if len(stem) < 5:
                continue
            
            # Extract options - they're in format:
            # (1) value1    (2) value2
            # (3) value3    (4) value4
            options = self._extract_options_from_complete_text(opt_text)
            
            if len(options) == 4:
                questions.append({
                    "question": stem,
                    "options": options,
                    "correct_answer": "A",
                    "explanation": ""
                })
        
        return questions
    
    def _extract_options_from_complete_text(self, opt_text):
        """
        Extract options from complete text where values are present.
        Format: (1) 628    (2) 812
                (3) 526    (4) 784
        """
        options = {}
        label_map = {'1': 'A', '2': 'B', '3': 'C', '4': 'D'}
        
        # Split by lines to handle two-column layout
        lines = opt_text.split('\n')
        
        for line in lines:
            # Find all (N) value patterns in this line
            # Pattern: (1) followed by non-parenthesis content
            pattern = r'\(([1-4])\)\s+([^\(]+?)(?=\s*\([1-4]\)|\s*$)'
            matches = re.findall(pattern, line)
            
            for num, value in matches:
                value = value.strip()
                if value and len(value) > 0:
                    options[label_map[num]] = value
        
        # Alternative extraction if first method didn't work
        if len(options) < 4:
            options = {}
            # Try more aggressive pattern
            pattern = r'\(([1-4])\)\s+(\S[^\(\n]*?)(?=\s*\([1-4]\)|$)'
            matches = re.findall(pattern, opt_text, re.DOTALL)
            
            for num, value in matches:
                value = value.strip()
                # Clean up value - remove trailing newlines, extra spaces
                value = re.sub(r'\s+', ' ', value).strip()
                if value:
                    options[label_map[num]] = value
        
        return options
    
    def _check_if_incomplete(self, pdf_text):
        """Detect if PDF text extraction is incomplete (missing option values)"""
        
        # Count option markers
        option_markers = re.findall(r'\([1-4]\)', pdf_text)
        
        # Count option values (text after markers)
        option_values = re.findall(r'\([1-4]\)\s+(\S+)', pdf_text)
        
        # If we have markers but few values, extraction is incomplete
        if len(option_markers) > 20 and len(option_values) < len(option_markers) * 0.7:
            return True
        
        # Check for blank options pattern: (1)   (2)   (3)   (4)
        blank_pattern = re.findall(r'\([1-4]\)\s+\([1-4]\)', pdf_text)
        if len(blank_pattern) > 5:
            return True
        
        return False
    
    def _extract_question_numbers(self, text):
        """Extract question numbers to verify completeness"""
        pattern = r'Q(\d+)\.'
        matches = re.findall(pattern, text)
        return [int(m) for m in matches]
    
    def _llm_extract_questions_enhanced(self, pdf_text):
        """Enhanced LLM extraction for incomplete/complex PDFs"""
        
        # Split into chunks if text is too long
        max_chunk_size = 4000
        chunks = self._split_text_into_chunks(pdf_text, max_chunk_size)
        
        all_questions = []
        
        for i, chunk in enumerate(chunks):
            st.info(f"Processing chunk {i+1}/{len(chunks)}...")
            
            prompt = f"""Extract MCQ questions from this text. The text may have incomplete extraction.

TEXT:
{chunk}

Extract ALL questions you can find. For each question:
1. Identify the question number and text
2. Extract all 4 options (A, B, C, D)
3. If option values are missing, try to infer from context or mark as [MISSING]

Return as JSON array:
[
  {{
    "question": "full question text",
    "options": {{"A": "option text", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "A",
    "explanation": ""
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text."""
            
            # Don't inject context for extraction tasks
            response = self.chat(prompt, temperature=0.3, inject_context=False)
            
            if response:
                questions = self._parse_json_questions(response)
                all_questions.extend(questions)
        
        return all_questions
    
    def _split_text_into_chunks(self, text, max_size):
        """Split text into chunks at question boundaries"""
        chunks = []
        current_chunk = ""
        
        # Split by question markers
        questions = re.split(r'(Q\d+\.)', text)
        
        for i in range(0, len(questions), 2):
            if i + 1 < len(questions):
                question_text = questions[i] + questions[i+1]
            else:
                question_text = questions[i]
            
            if len(current_chunk) + len(question_text) > max_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = question_text
            else:
                current_chunk += question_text
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text]
    
    def _remove_duplicate_questions(self, questions):
        """Remove duplicate questions"""
        seen = set()
        unique = []
        
        for q in questions:
            # Create a simple hash of the question
            q_text = q.get('question', '')[:100].lower().strip()
            
            if q_text and q_text not in seen:
                seen.add(q_text)
                unique.append(q)
        
        return unique
    
    def _parse_json_questions(self, response):
        """Parse JSON questions from LLM response"""
        try:
            # Clean response
            content = response.strip()
            
            # Remove markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            # Find JSON array
            start = content.find('[')
            end = content.rfind(']')
            
            if start == -1 or end == -1:
                return []
            
            # Sanitize and parse
            json_str = self._sanitize_json_string(content[start:end + 1])
            questions = json.loads(json_str)
            
            # Validate questions
            valid_questions = []
            for q in questions:
                if (isinstance(q, dict) and 
                    'question' in q and 
                    'options' in q and 
                    len(q['options']) == 4):
                    valid_questions.append(q)
            
            return valid_questions
        except Exception as e:
            st.error(f"❌ Failed to parse questions: {str(e)}")
            return []
    
    def explain_mistake(self, question, user_answer, correct_answer, explanation):
        """
        Explain why a student got a question wrong
        WITH CONTEXT INJECTION - student-aware explanation
        """
        prompt = f"""A student answered incorrectly.

Question: {question}
Student selected: {user_answer}
Correct answer: {correct_answer}
Explanation: {explanation}

Explain:
1. Why the chosen answer seemed plausible
2. The correct reasoning
3. One tip to avoid this mistake

Keep it concise (3-4 sentences) and encouraging."""
        
        return self.chat(prompt, temperature=0.5, inject_context=True)
    
    def generate_personalized_recommendations(self, performance_data):
        """
        Generate personalized study recommendations
        WITH CONTEXT INJECTION - exam-aware and student-aware
        """
        prompt = f"""Generate personalized study recommendations for this student:

Exam Performance:
- Score: {performance_data.get('score', 0)}/{performance_data.get('total', 0)} ({performance_data.get('percentage', 0):.1f}%)
- Time Taken: {performance_data.get('time_taken', 0)} minutes
- Questions Attempted: {performance_data.get('attempted', 0)}/{performance_data.get('total', 0)}
- Weak Topics: {', '.join(performance_data.get('weak_topics', ['None identified']))}

Provide:
1. Overall performance assessment (2 sentences)
2. Top 3 specific study recommendations tailored to their exam and weak topics
3. Focus areas for improvement considering their strategy preference
4. Motivational message considering their current ability level

Keep it actionable and encouraging. Format with clear sections."""

        return self.chat(prompt, temperature=0.6, inject_context=True)
    
    def generate_adaptive_questions(self, topic, difficulty, count, weak_areas=None):
        """
        Generate adaptive MCQ questions based on topic, difficulty, and weak areas
        WITH CONTEXT INJECTION - personalized to student's exam and level
        """
        weak_context = ""
        if weak_areas:
            weak_context = f"\nStudent's weak areas: {', '.join(weak_areas)}. Include 1-2 questions targeting these areas."
        
        difficulty_guidance = {
            'easy': 'Basic conceptual questions, straightforward calculations',
            'medium': 'Standard exam-level questions with moderate complexity',
            'hard': 'Advanced questions requiring deep understanding and multi-step thinking',
            'mixed': 'Mix of easy (30%), medium (50%), and hard (20%) questions'
        }
        
        prompt = f"""Generate {count} high-quality MCQ questions on the topic: {topic}

Difficulty level: {difficulty}
Guidance: {difficulty_guidance.get(difficulty, difficulty_guidance['medium'])}
{weak_context}

Requirements:
1. Questions should match the student's exam pattern and difficulty
2. Include clear, unambiguous options
3. Provide brief explanations for correct answers
4. Cover different aspects of the topic
5. Make questions exam-relevant and practical

Return ONLY a valid JSON array in this EXACT format:
[
  {{
    "question": "Clear question text",
    "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
    "correct_answer": "A",
    "explanation": "Brief explanation why this is correct",
    "topic": "{topic}",
    "difficulty": "{difficulty}"
  }}
]

Generate exactly {count} questions. Return ONLY the JSON array, nothing else."""
        
        response = self.chat(prompt, temperature=0.7, inject_context=True)
        
        if response:
            questions = self._parse_json_questions(response)
            
            # Ensure we have the requested count
            if len(questions) < count:
                st.warning(f"Generated {len(questions)} questions (requested {count})")
            
            return questions[:count] if questions else None
        
        return None
    
    def answer_doubt_advanced(self, question, subject, confidence_level, past_mistakes=None, learning_style='mixed'):
        """
        Advanced doubt answering with personalization
        WITH CONTEXT INJECTION - fully personalized to student profile
        """
        mistake_context = ""
        if past_mistakes:
            mistake_types = [m.get('type', '') for m in past_mistakes[-3:]]
            if mistake_types:
                mistake_context = f"\nNote: Student has recently made these types of errors: {', '.join(mistake_types)}. Address these patterns if relevant."
        
        depth_guidance = {
            1: "Explain like I'm 10. Start from very basics, use simple language, many examples.",
            2: "Explain concepts clearly but don't oversimplify. Some prior knowledge assumed.",
            3: "Balanced explanation. Cover key concepts with examples.",
            4: "Advanced explanation. Can use technical terms, focus on deeper insights.",
            5: "Expert level. Challenge me, discuss edge cases and applications."
        }
        
        prompt = f"""You are an expert {subject} tutor. Answer this student's doubt:

Question: {question}

Student's confidence level: {confidence_level}/5
Guidance: {depth_guidance.get(confidence_level, depth_guidance[3])}
Learning style: {learning_style}
{mistake_context}

Provide a clear, helpful answer tailored to their level AND their exam preparation. Include:
1. Direct answer to their question
2. Key concept explanation
3. One practical example relevant to their exam
4. Common pitfall to avoid (especially given their weak topics)

Keep it concise but complete."""
        
        return self.chat(prompt, temperature=0.6, inject_context=True)

    def generate_specific_view(self, question, view_type, subject):
        """
        Generate a specific type of explanation view
        WITH CONTEXT INJECTION - adapted to student's level
        """
        
        view_prompts = {
            'intuition': f"""Explain this {subject} concept using PURE INTUITION (no math):

Question: {question}

Requirements:
- Use everyday analogies and real-world examples
- Focus on "why" it works, not "how" to calculate
- Make it feel obvious and natural
- Use simple language anyone can understand
- Adapt depth to the student's ability level
- 3-4 sentences max

Generate an intuitive explanation:""",
            
            'math': f"""Provide a RIGOROUS MATHEMATICAL explanation:

Question: {question}
Subject: {subject}

Requirements:
- Show all formulas and derivations
- Include step-by-step mathematical proof
- Use proper notation and terminology
- Explain the mathematical reasoning
- Adapt technical depth to student's ability level
- Be precise and technical

Generate mathematical explanation:""",
            
            'analogy': f"""Create a POWERFUL ANALOGY to explain this:

Question: {question}
Subject: {subject}

Requirements:
- Use a relatable, everyday situation
- Make it memorable and vivid
- Show clear parallels to the concept
- Keep it simple and engaging
- Adapt to student's background
- End with "Just like..." connection

Generate an analogy:""",
            
            'shortcut': f"""Provide the FASTEST SHORTCUT method:

Question: {question}
Subject: {subject}

Requirements:
- Give a quick trick or rule of thumb for their exam
- Explain when to use it (and when NOT to)
- Make it memorable (acronym, rhyme, or pattern)
- Include one example
- Consider their time pressure tendencies
- Keep it under 4 sentences

Generate a shortcut:""",
            
            'visual': f"""Describe a VISUAL/GRAPHICAL explanation:

Question: {question}
Subject: {subject}

Requirements:
- Describe what to draw or visualize
- Use spatial reasoning and diagrams
- Include labels and key features
- Make it easy to sketch mentally
- Adapt complexity to student level
- Focus on visual patterns

Describe the visualization:"""
        }
        
        prompt = view_prompts.get(view_type, view_prompts['intuition'])
        return self.chat(prompt, temperature=0.7, inject_context=True)

    def generate_follow_up_question(self, original_question, explanation):
        """
        Generate a follow-up question to test understanding
        WITH CONTEXT INJECTION - difficulty adapted to student
        """
        prompt = f"""Based on this question and explanation, generate ONE follow-up question to test understanding:

Original Question: {original_question}

Explanation Given: {explanation}

Generate a follow-up question that:
1. Tests if the student truly understood the concept
2. Is slightly different from the original (applies the concept to a new scenario)
3. Matches the student's optimal difficulty range
4. Is not too hard - should be answerable if they understood the explanation
5. Is concise and clear

Return ONLY the follow-up question, nothing else."""
        
        return self.chat(prompt, temperature=0.7, inject_context=True)

    def evaluate_follow_up_answer(self, question, user_answer, original_context):
        """
        Evaluate the user's answer to a follow-up question
        WITH CONTEXT INJECTION - personalized feedback
        """
        prompt = f"""Evaluate this student's answer to a follow-up question:

Follow-up Question: {question}

Student's Answer: {user_answer}

Original Context: {original_context}

Provide:
1. Whether the answer demonstrates understanding (Yes/Partially/No)
2. What they got right
3. What needs improvement (if anything) - link to their weak topics if relevant
4. One encouraging comment considering their learning journey

Keep it constructive and brief (3-4 sentences)."""
        
        return self.chat(prompt, temperature=0.5, inject_context=True)

    def mental_health_support(self, message, mood):
        """
        Provide supportive responses for mental health check-ins
        WITH CONTEXT INJECTION - aware of exam pressure and student stress
        """
        prompt = f"""You are a supportive study companion. A student shared:

Message: {message}
Current mood: {mood}

Provide a warm, empathetic response that:
1. Acknowledges their feelings
2. Offers gentle encouragement considering their exam preparation
3. Suggests one small, actionable step aligned with their study needs
4. Reminds them you're here to help

Keep it brief (3-4 sentences), genuine, and supportive. Do NOT provide medical advice."""
        
        return self.chat(prompt, temperature=0.7, inject_context=True)
    
    def generate_exam_strategy(self, student_context):
        """
        Generate exam-specific strategy based on student profile
        NEW METHOD for context-aware exam planning
        """
        prompt = f"""Based on this student's profile, generate a personalized exam strategy:

The student is preparing for: {student_context.get('exam', 'JEE')}

Provide:
1. Question selection strategy (which to attempt first, which to skip)
2. Time management plan specific to their time pressure tendency
3. Negative marking mitigation based on their risk level
4. Topic prioritization based on weak areas
5. Confidence-building tips

Format as clear, numbered sections. Be specific and actionable."""
        
        # Manually inject context since it's already in the prompt
        return self.chat(prompt, temperature=0.6, inject_context=True)


# Export
__all__ = ['EnhancedGeminiService']