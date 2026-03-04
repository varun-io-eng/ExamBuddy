"""
rag_retriever.py - True Retrieval-Augmented Generation
UPGRADES: gemini_service.py answer_doubt_advanced()

Instead of pasting student context into every prompt (token-limited),
this builds a local ChromaDB vector store from:
  1. Your existing ConceptGraph definitions (immediate, zero extra work)
  2. Any text you add (textbook excerpts, PYQ explanations, etc.)

When a student asks a doubt:
  - Query is embedded and matched against the knowledge base
  - Top-3 most relevant chunks are retrieved
  - LLM answers using THAT retrieved content → cites sources
  - Minimises hallucination, provides "See HC Verma Ch.7"-style citations

No API key needed. ChromaDB runs 100% locally.
Falls back to direct LLM if ChromaDB not installed.
"""

import os
import json
from typing import Optional

# ── optional deps ────────────────────────────────────────────────────────────
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# BUILT-IN KNOWLEDGE BASE  (seeded from ConceptGraph + curated content)
# ═══════════════════════════════════════════════════════════════════════════

KNOWLEDGE_BASE = [
    # ── Physics ──────────────────────────────────────────────────────────
    {
        "id": "phy_kinematics_1",
        "source": "HC Verma Vol.1 Ch.3",
        "subject": "Physics",
        "topic": "Kinematics",
        "content": (
            "Equations of motion for uniform acceleration: v = u + at, "
            "s = ut + ½at², v² = u² + 2as. These only apply when acceleration is constant. "
            "For free fall, a = g = 9.8 m/s². "
            "Key JEE insight: always define a positive direction before applying equations."
        )
    },
    {
        "id": "phy_kinematics_2",
        "source": "HC Verma Vol.1 Ch.3",
        "subject": "Physics",
        "topic": "Projectile Motion",
        "content": (
            "Projectile motion: horizontal velocity is constant (no air resistance), "
            "vertical motion has acceleration g downward. "
            "Range R = u²sin(2θ)/g. Maximum range at θ=45°. "
            "Time of flight T = 2u·sinθ/g. "
            "Common JEE mistake: forgetting that at maximum height, vertical velocity = 0 but horizontal velocity ≠ 0."
        )
    },
    {
        "id": "phy_newton_1",
        "source": "HC Verma Vol.1 Ch.5",
        "subject": "Physics",
        "topic": "Newton's Laws",
        "content": (
            "Newton's Second Law: F = ma (net force, not applied force). "
            "Free Body Diagram technique: isolate each body, draw all forces on it only. "
            "Normal force is perpendicular to surface. "
            "Friction f ≤ μN (static), f = μN (kinetic). "
            "JEE tip: for connected bodies, use system method for acceleration, then isolation for tension."
        )
    },
    {
        "id": "phy_work_energy",
        "source": "HC Verma Vol.1 Ch.8",
        "subject": "Physics",
        "topic": "Work Energy Theorem",
        "content": (
            "Work-energy theorem: Net work done on a body = Change in kinetic energy. "
            "W_net = ΔKE = ½mv² - ½mu². "
            "Conservative forces: work done is path-independent (gravity, spring). "
            "Non-conservative forces: work done is path-dependent (friction). "
            "Energy conservation: KE + PE = constant (when only conservative forces act)."
        )
    },
    {
        "id": "phy_circular",
        "source": "HC Verma Vol.1 Ch.7",
        "subject": "Physics",
        "topic": "Circular Motion",
        "content": (
            "Centripetal acceleration a = v²/r = ω²r directed toward center. "
            "Centripetal force is not a separate force — it is provided by existing forces (tension, gravity, normal). "
            "For vertical circle: minimum speed at top v_min = √(gR). "
            "JEE insight: pseudo-force in rotating frame = mω²r (centrifugal, outward)."
        )
    },
    {
        "id": "phy_waves",
        "source": "HC Verma Vol.1 Ch.15",
        "subject": "Physics",
        "topic": "Waves",
        "content": (
            "Wave equation: y = A·sin(kx - ωt). k = 2π/λ (wave number), ω = 2πf. "
            "Speed v = fλ = ω/k. "
            "Standing waves: nodes (zero displacement), antinodes (max displacement). "
            "For string fixed at both ends: f_n = n·v/(2L). "
            "Doppler effect: f' = f·(v+v_o)/(v-v_s)."
        )
    },
    {
        "id": "phy_electrostatics",
        "source": "HC Verma Vol.2 Ch.29",
        "subject": "Physics",
        "topic": "Electrostatics",
        "content": (
            "Coulomb's law: F = kq₁q₂/r². Electric field E = F/q. "
            "Gauss's law: ∮E·dA = Q_enclosed/ε₀. "
            "Electric potential V = kQ/r. Work done = q(V_A - V_B). "
            "JEE tip: use Gauss's law for symmetric charge distributions (sphere, cylinder, plane). "
            "E = -dV/dr (negative gradient of potential)."
        )
    },
    {
        "id": "phy_thermodynamics",
        "source": "HC Verma Vol.2 Ch.26",
        "subject": "Physics",
        "topic": "Thermodynamics",
        "content": (
            "First Law: ΔU = Q - W (heat added minus work done BY gas). "
            "Isothermal: ΔU = 0, so Q = W. Adiabatic: Q = 0, ΔU = -W. "
            "Carnot efficiency η = 1 - T_cold/T_hot. "
            "Specific heat: Cv = (f/2)R, Cp = Cv + R. γ = Cp/Cv. "
            "JEE common error: sign convention for work — work done BY gas is positive."
        )
    },

    # ── Chemistry ────────────────────────────────────────────────────────
    {
        "id": "chem_bonding_1",
        "source": "NCERT Chemistry Part 1 Ch.4",
        "subject": "Chemistry",
        "topic": "Chemical Bonding",
        "content": (
            "VSEPR theory: electron pairs repel each other. "
            "Lone pair–lone pair repulsion > lone pair–bond pair > bond pair–bond pair. "
            "Bond angles: CH₄ (109.5°), NH₃ (107°), H₂O (104.5°). "
            "Hybridisation: sp³ (tetrahedral), sp² (trigonal planar), sp (linear). "
            "JEE insight: count all electron pairs (bonding + lone) to determine geometry."
        )
    },
    {
        "id": "chem_equilibrium",
        "source": "NCERT Chemistry Part 1 Ch.7",
        "subject": "Chemistry",
        "topic": "Chemical Equilibrium",
        "content": (
            "Le Chatelier's principle: equilibrium shifts to oppose any change. "
            "Kc = [products]/[reactants] (molar concentrations at equilibrium). "
            "Kp = Kc(RT)^Δn where Δn = moles of gaseous products - reactants. "
            "Adding inert gas at constant volume: no shift. At constant pressure: shifts toward more moles. "
            "JEE tip: catalyst does not change equilibrium position, only rate."
        )
    },
    {
        "id": "chem_organic_1",
        "source": "Morrison Boyd Ch.3",
        "subject": "Chemistry",
        "topic": "Organic Reactions",
        "content": (
            "SN1 reaction: two-step, carbocation intermediate, racemisation. "
            "Favoured by: 3° > 2° carbons, polar protic solvents (H₂O, ROH). "
            "SN2 reaction: one-step, backside attack, inversion of configuration. "
            "Favoured by: 1° carbons, polar aprotic solvents (DMSO, DMF). "
            "JEE insight: allylic and benzylic halides can undergo both SN1 and SN2."
        )
    },
    {
        "id": "chem_electrochemistry",
        "source": "NCERT Chemistry Part 1 Ch.3",
        "subject": "Chemistry",
        "topic": "Electrochemistry",
        "content": (
            "Nernst equation: E = E° - (RT/nF)lnQ = E° - (0.059/n)logQ at 25°C. "
            "EMF = E_cathode - E_anode. Positive EMF → spontaneous. "
            "Faraday's laws: mass deposited = (M/nF) × charge. "
            "Conductance increases with temperature for electrolytes. "
            "JEE tip: always write reduction half-reactions for standard electrode potentials."
        )
    },

    # ── Mathematics ──────────────────────────────────────────────────────
    {
        "id": "math_calculus_1",
        "source": "RD Sharma Calculus Ch.11",
        "subject": "Mathematics",
        "topic": "Differentiation",
        "content": (
            "Chain rule: d/dx[f(g(x))] = f'(g(x))·g'(x). "
            "Product rule: (uv)' = u'v + uv'. Quotient rule: (u/v)' = (u'v - uv')/v². "
            "Standard: d/dx[xⁿ] = nxⁿ⁻¹, d/dx[eˣ] = eˣ, d/dx[ln x] = 1/x. "
            "JEE tip: for implicit differentiation, differentiate both sides and collect dy/dx terms."
        )
    },
    {
        "id": "math_integration",
        "source": "RD Sharma Calculus Ch.19",
        "subject": "Mathematics",
        "topic": "Integration",
        "content": (
            "Integration by parts: ∫u dv = uv - ∫v du. ILATE rule for choosing u. "
            "∫xⁿ dx = xⁿ⁺¹/(n+1) + C. ∫eˣ dx = eˣ + C. ∫1/x dx = ln|x| + C. "
            "Definite integral: ∫[a,b] f(x)dx = F(b) - F(a). "
            "JEE insight: for ∫[0,a] f(x)dx, use property f(x) + f(a-x) = constant to simplify."
        )
    },
    {
        "id": "math_trigonometry",
        "source": "SL Loney Trigonometry",
        "subject": "Mathematics",
        "topic": "Trigonometry",
        "content": (
            "sin²θ + cos²θ = 1. sec²θ = 1 + tan²θ. cosec²θ = 1 + cot²θ. "
            "sin(A±B) = sinA·cosB ± cosA·sinB. cos(A±B) = cosA·cosB ∓ sinA·sinB. "
            "tan(A+B) = (tanA + tanB)/(1 - tanA·tanB). "
            "JEE tip: for range problems, express in form R·sin(θ+φ), range is [-R, R]."
        )
    },
    {
        "id": "math_matrices",
        "source": "NCERT Mathematics Part 1 Ch.3",
        "subject": "Mathematics",
        "topic": "Matrices",
        "content": (
            "Matrix multiplication: (AB)ᵢⱼ = Σ Aᵢₖ·Bₖⱼ. Not commutative: AB ≠ BA generally. "
            "Determinant: |AB| = |A||B|. Inverse: A⁻¹ = adj(A)/|A|. "
            "For 2×2: |A| = ad-bc, adj = [[d,-b],[-c,a]]. "
            "JEE insight: if |A| = 0, matrix is singular (no inverse). System has no unique solution."
        )
    },

    # ── Computer Science ─────────────────────────────────────────────────
    {
        "id": "cs_complexity",
        "source": "CLRS Introduction to Algorithms Ch.3",
        "subject": "Computer Science",
        "topic": "Time Complexity",
        "content": (
            "Big-O notation: O(1) constant, O(log n) logarithmic, O(n) linear, "
            "O(n log n) linearithmic, O(n²) quadratic, O(2ⁿ) exponential. "
            "Binary search: O(log n). Merge sort: O(n log n). "
            "GATE tip: always identify the dominant term. Drop constants and lower-order terms."
        )
    },
    {
        "id": "cs_dp",
        "source": "CLRS Introduction to Algorithms Ch.15",
        "subject": "Computer Science",
        "topic": "Dynamic Programming",
        "content": (
            "DP applies when: optimal substructure + overlapping subproblems. "
            "Two approaches: top-down (memoization) and bottom-up (tabulation). "
            "Classic problems: Fibonacci, 0/1 Knapsack, LCS, LIS, Matrix chain multiplication. "
            "GATE tip: state definition is everything. Clearly define what dp[i] represents before coding."
        )
    },
    {
        "id": "cs_os_scheduling",
        "source": "Galvin Operating Systems Ch.6",
        "subject": "Computer Science",
        "topic": "CPU Scheduling",
        "content": (
            "FCFS: non-preemptive, convoy effect. SJF: optimal average waiting time, "
            "but needs burst time prediction. Round Robin: preemptive, time quantum q. "
            "Priority scheduling: starvation possible → aging solution. "
            "GATE tip: for Gantt chart problems, calculate waiting time = turnaround - burst. "
            "Turnaround = completion - arrival."
        )
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# SIMPLE TF-IDF FALLBACK  (when ChromaDB / SentenceTransformers unavailable)
# ═══════════════════════════════════════════════════════════════════════════

class TFIDFRetriever:
    """Pure-numpy TF-IDF retrieval — no external deps required."""

    def __init__(self, docs):
        self.docs  = docs
        self.texts = [d['content'] + ' ' + d['topic'] + ' ' + d['subject'] for d in docs]
        self._build_index()

    def _tokenize(self, text):
        import re
        return re.findall(r'[a-zA-Z0-9]+', text.lower())

    def _build_index(self):
        from collections import Counter, defaultdict
        import math
        N = len(self.texts)
        self.vocab = {}
        df = defaultdict(int)
        tok_docs = []
        for text in self.texts:
            tokens = self._tokenize(text)
            tok_docs.append(Counter(tokens))
            for t in set(tokens):
                df[t] += 1
                if t not in self.vocab:
                    self.vocab[t] = len(self.vocab)

        V = len(self.vocab)
        self.tfidf = np.zeros((N, V), dtype=np.float32)
        for i, counts in enumerate(tok_docs):
            total = sum(counts.values())
            for term, cnt in counts.items():
                if term in self.vocab:
                    tf  = cnt / total
                    idf = math.log((N + 1) / (df[term] + 1)) + 1
                    self.tfidf[i, self.vocab[term]] = tf * idf
        # L2 normalise
        norms = np.linalg.norm(self.tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.tfidf /= norms

    def query(self, text, k=3):
        from collections import Counter
        tokens = self._tokenize(text)
        counts = Counter(tokens)
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for term, cnt in counts.items():
            if term in self.vocab:
                vec[self.vocab[term]] = cnt
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        sims = self.tfidf @ vec
        top_k = np.argsort(sims)[::-1][:k]
        return [
            {'doc': self.docs[i], 'score': float(sims[i])}
            for i in top_k if sims[i] > 0.01
        ]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RAG RETRIEVER
# ═══════════════════════════════════════════════════════════════════════════

class RAGRetriever:
    """
    Retrieval-Augmented Generation engine.
    Uses ChromaDB + sentence-transformers when available,
    falls back to TF-IDF otherwise.
    """

    PERSIST_DIR = './rag_db'

    def __init__(self):
        self._chroma_col = None
        self._tfidf      = None
        self._initialised = False

    def initialize(self):
        """Call once at app startup."""
        if self._initialised:
            return
        if CHROMA_AVAILABLE:
            self._init_chroma()
        else:
            self._init_tfidf()
        self._initialised = True

    # ── ChromaDB path ─────────────────────────────────────────────────────
    def _init_chroma(self):
        try:
            client = chromadb.PersistentClient(path=self.PERSIST_DIR)
            ef = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name='all-MiniLM-L6-v2'
                ) if ST_AVAILABLE
                else embedding_functions.DefaultEmbeddingFunction()
            )
            self._chroma_col = client.get_or_create_collection(
                name='exam_knowledge',
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
            # Seed if empty
            if self._chroma_col.count() == 0:
                self._seed_chroma()
        except Exception as e:
            print(f"ChromaDB init failed ({e}), falling back to TF-IDF")
            self._init_tfidf()

    def _seed_chroma(self):
        ids      = [d['id']      for d in KNOWLEDGE_BASE]
        texts    = [d['content'] for d in KNOWLEDGE_BASE]
        metas    = [{'source': d['source'], 'subject': d['subject'],
                     'topic': d['topic']}   for d in KNOWLEDGE_BASE]
        # Chroma accepts batches of ≤ 5461
        batch = 100
        for i in range(0, len(ids), batch):
            self._chroma_col.add(
                ids=ids[i:i+batch],
                documents=texts[i:i+batch],
                metadatas=metas[i:i+batch]
            )

    # ── TF-IDF path ───────────────────────────────────────────────────────
    def _init_tfidf(self):
        self._tfidf = TFIDFRetriever(KNOWLEDGE_BASE)

    # ── public API ────────────────────────────────────────────────────────

    def add_document(self, doc_id: str, content: str, source: str,
                     subject: str, topic: str):
        """Add a new chunk to the knowledge base at runtime."""
        entry = {'id': doc_id, 'content': content, 'source': source,
                 'subject': subject, 'topic': topic}
        if self._chroma_col is not None:
            try:
                self._chroma_col.add(
                    ids=[doc_id], documents=[content],
                    metadatas=[{'source': source, 'subject': subject, 'topic': topic}]
                )
                return
            except Exception:
                pass
        if self._tfidf is not None:
            KNOWLEDGE_BASE.append(entry)
            self._tfidf = TFIDFRetriever(KNOWLEDGE_BASE)

    def retrieve(self, query: str, subject: str = None, k: int = 3) -> list:
        """
        Retrieve top-k relevant knowledge chunks for a query.
        Returns list of dicts: {content, source, subject, topic, score}
        """
        if not self._initialised:
            self.initialize()

        if self._chroma_col is not None:
            return self._chroma_retrieve(query, subject, k)
        elif self._tfidf is not None:
            return self._tfidf_retrieve(query, k)
        return []

    def _chroma_retrieve(self, query, subject, k):
        try:
            where = {'subject': subject} if subject else None
            results = self._chroma_col.query(
                query_texts=[query], n_results=min(k, self._chroma_col.count()),
                where=where
            )
            out = []
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                dist = results['distances'][0][i] if 'distances' in results else 0.5
                out.append({
                    'content': doc,
                    'source':  meta.get('source', 'Unknown'),
                    'subject': meta.get('subject', ''),
                    'topic':   meta.get('topic', ''),
                    'score':   round(1 - dist, 3)
                })
            return out
        except Exception:
            return self._tfidf_retrieve(query, k) if self._tfidf else []

    def _tfidf_retrieve(self, query, k):
        results = self._tfidf.query(query, k)
        return [
            {
                'content': r['doc']['content'],
                'source':  r['doc']['source'],
                'subject': r['doc']['subject'],
                'topic':   r['doc']['topic'],
                'score':   round(r['score'], 3)
            }
            for r in results
        ]

    def build_rag_prompt(self, question: str, subject: str = None,
                          student_context: str = '') -> str:
        """
        Build a RAG-enhanced prompt for the LLM.
        Retrieved content replaces generic LLM imagination with cited facts.
        """
        chunks = self.retrieve(question, subject=subject, k=3)

        if not chunks:
            return question  # fallback: pass through unchanged

        context_block = "\n\n".join([
            f"[Source: {c['source']} | {c['subject']} – {c['topic']}]\n{c['content']}"
            for c in chunks
        ])

        sources_list = ", ".join(
            f"{c['source']}" for c in chunks if c['score'] > 0.1
        )

        prompt = f"""You are an expert tutor for competitive exams (JEE/NEET/GATE).

RETRIEVED KNOWLEDGE (use this as your primary source):
{context_block}

{f"STUDENT PROFILE: {student_context}" if student_context else ""}

STUDENT QUESTION: {question}

Instructions:
- Answer primarily using the retrieved knowledge above
- Cite your source (e.g., "According to {chunks[0]['source']}...")  
- If retrieved content doesn't fully cover the question, supplement with your knowledge and say so
- Keep answer focused, accurate, and exam-relevant
- End with: "📚 Sources consulted: {sources_list}"
"""
        return prompt

    def get_citation_context(self, question: str, subject: str = None) -> dict:
        """
        Returns retrieved chunks + formatted citation string.
        Use this to show 'View Sources' in the UI.
        """
        chunks = self.retrieve(question, subject=subject, k=3)
        return {
            'chunks': chunks,
            'citation_text': '\n'.join(
                f"• {c['source']} ({c['topic']})" for c in chunks
            ),
            'has_sources': len(chunks) > 0
        }


# ── singleton ────────────────────────────────────────────────────────────────
_retriever: Optional[RAGRetriever] = None

def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
        _retriever.initialize()
    return _retriever


__all__ = ['RAGRetriever', 'get_retriever', 'KNOWLEDGE_BASE']
