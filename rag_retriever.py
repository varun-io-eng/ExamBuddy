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
# NOTE: Use bare Exception (not ImportError) because ChromaDB raises
# pydantic.v1.errors.ConfigError on Python 3.14 — an upstream bug.
# This ensures the app never crashes on import regardless of Python version.
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except Exception:
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

    # ── Mathematics — Probability & Statistics ───────────────────────────
    {
        "id": "math_probability_1",
        "source": "RD Sharma Probability Ch.31",
        "subject": "Mathematics",
        "topic": "Probability",
        "content": (
            "Probability of event A: P(A) = favourable outcomes / total outcomes. "
            "Addition rule: P(A∪B) = P(A) + P(B) - P(A∩B). "
            "Mutually exclusive events: P(A∪B) = P(A) + P(B). "
            "Complement: P(A') = 1 - P(A). "
            "JEE tip: always check if events are mutually exclusive before applying addition rule."
        )
    },
    {
        "id": "math_probability_2",
        "source": "RD Sharma Probability Ch.32",
        "subject": "Mathematics",
        "topic": "Conditional Probability",
        "content": (
            "Conditional probability: P(A|B) = P(A∩B) / P(B). "
            "Multiplication rule: P(A∩B) = P(A) × P(B|A). "
            "Independent events: P(A∩B) = P(A) × P(B), so P(A|B) = P(A). "
            "Bayes theorem: P(A|B) = P(B|A)·P(A) / P(B). "
            "JEE insight: Bayes theorem is used for reverse conditional problems — "
            "given the outcome, find the cause probability."
        )
    },
    {
        "id": "math_probability_3",
        "source": "RD Sharma Probability Ch.33",
        "subject": "Mathematics",
        "topic": "Binomial Distribution",
        "content": (
            "Binomial distribution: P(X=r) = nCr × p^r × (1-p)^(n-r). "
            "Mean = np, Variance = np(1-p), Standard deviation = sqrt(np(1-p)). "
            "Conditions: fixed n trials, each trial is independent, only 2 outcomes (success/failure). "
            "JEE tip: for large n and small p, binomial approaches Poisson distribution."
        )
    },
    {
        "id": "math_permcomb",
        "source": "RD Sharma Permutations Ch.16",
        "subject": "Mathematics",
        "topic": "Permutation and Combination",
        "content": (
            "Permutation (order matters): nPr = n! / (n-r)!. "
            "Combination (order doesn't matter): nCr = n! / (r!(n-r)!). "
            "nCr = nC(n-r). nC0 = nCn = 1. "
            "Circular permutation of n objects: (n-1)!. "
            "JEE tip: identify if order matters. 'Arrangements' → permutation. 'Selections/groups' → combination."
        )
    },
    {
        "id": "math_statistics",
        "source": "NCERT Mathematics Statistics Ch.15",
        "subject": "Mathematics",
        "topic": "Statistics",
        "content": (
            "Mean = sum of all values / number of values. "
            "Median = middle value when sorted; for even n, average of two middle values. "
            "Mode = most frequently occurring value. "
            "Variance = average of squared deviations from mean. "
            "Standard deviation = sqrt(variance). "
            "JEE insight: for grouped data, use step deviation method to simplify calculation."
        )
    },
    {
        "id": "math_sequences",
        "source": "RD Sharma Sequences Ch.19",
        "subject": "Mathematics",
        "topic": "Sequences and Series",
        "content": (
            "AP: nth term = a + (n-1)d. Sum = n/2 × (2a + (n-1)d). "
            "GP: nth term = ar^(n-1). Sum = a(1-r^n)/(1-r) for r≠1. "
            "Sum of infinite GP = a/(1-r) for |r| < 1. "
            "Harmonic Progression: reciprocals form an AP. "
            "JEE tip: AM ≥ GM ≥ HM for positive numbers. Equality when all numbers are equal."
        )
    },
    {
        "id": "math_sets_relations",
        "source": "NCERT Mathematics Sets Ch.1",
        "subject": "Mathematics",
        "topic": "Sets and Relations",
        "content": (
            "Set operations: A∪B (union), A∩B (intersection), A-B (difference), A' (complement). "
            "De Morgan's laws: (A∪B)' = A'∩B', (A∩B)' = A'∪B'. "
            "Number of subsets of a set with n elements = 2^n. "
            "Relation R is an equivalence relation if reflexive, symmetric, and transitive. "
            "JEE insight: bijective function = one-one AND onto. Check both conditions separately."
        )
    },

    # ── Mathematics — Algebra & Complex Numbers ──────────────────────────
    {
        "id": "math_complex",
        "source": "RD Sharma Complex Numbers Ch.13",
        "subject": "Mathematics",
        "topic": "Complex Numbers",
        "content": (
            "Complex number z = a + ib. Modulus |z| = sqrt(a²+b²). Argument = arctan(b/a). "
            "Conjugate of z: z̄ = a - ib. z × z̄ = |z|². "
            "Euler's form: z = |z| × e^(iθ). De Moivre: (cosθ + i sinθ)^n = cos(nθ) + i sin(nθ). "
            "Cube roots of unity: 1, ω, ω² where ω = e^(2πi/3). 1 + ω + ω² = 0. "
            "JEE tip: for locus problems, write z = x + iy and find the equation in x and y."
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
            return self._tfidf_retrieve(query, k, subject=subject)
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

    def _tfidf_retrieve(self, query, k, subject=None):
        """TF-IDF retrieval with subject filtering when subject is provided"""
        # If subject given, filter knowledge base to that subject first
        if subject:
            subject_lower = subject.lower()
            filtered_docs = [
                d for d in KNOWLEDGE_BASE
                if d['subject'].lower() == subject_lower
            ]
            # Only use filtered if we have enough docs, else fall back to all
            if len(filtered_docs) >= 2:
                filtered_retriever = TFIDFRetriever(filtered_docs)
                results = filtered_retriever.query(query, k)
            else:
                results = self._tfidf.query(query, k)
        else:
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

    @staticmethod
    def detect_subject(question: str) -> str:
        """
        Detect subject from question text so RAG fetches the right book.
        Maths doubt  → RD Sharma / SL Loney (NOT HC Verma)
        Physics doubt → HC Verma
        Chem doubt   → NCERT Chemistry / Morrison Boyd
        Uses SCORED matching so the strongest signal wins, not first match.
        """
        import re
        q = question.lower()
        # Normalize: remove punctuation noise
        q = re.sub(r"[^a-z0-9 ]", " ", q)

        scores = {
            'Mathematics':      0,
            'Physics':          0,
            'Chemistry':        0,
            'Biology':          0,
            'Computer Science': 0,
        }

        # ── Mathematics (high-weight unique terms) ───────────────────────
        math_keywords = {
            # Probability & Statistics — the most commonly misrouted topic
            'probability': 5, 'bayes': 5, 'conditional probability': 5,
            'random variable': 5, 'expectation': 4, 'variance': 4,
            'standard deviation': 4, 'binomial distribution': 5,
            'poisson': 5, 'normal distribution': 5, 'permutation': 5,
            'combination': 5, 'factorial': 4, 'sample space': 5,
            'event': 3, 'mutually exclusive': 5,
            # Calculus
            'integral': 5, 'integrate': 5, 'differentiate': 5,
            'derivative': 5, 'limit': 4, 'continuity': 4,
            'differentiability': 5, 'calculus': 5, 'rolle': 5,
            'lagrange': 4, 'taylor': 4, 'maclaurin': 5,
            # Algebra & misc
            'matrix': 5, 'determinant': 5, 'quadratic': 4,
            'polynomial': 4, 'sequence': 3, 'arithmetic progression': 5,
            'geometric progression': 5, 'binomial theorem': 5,
            'complex number': 5, 'logarithm': 4, 'log base': 5,
            # Trigonometry
            'trigonometry': 5, 'sin': 2, 'cos': 2, 'tan': 2,
            'sine': 4, 'cosine': 4, 'tangent': 4, 'cotangent': 5,
            'cosec': 5, 'sec ': 3, 'inverse trig': 5,
            # Geometry
            'parabola': 5, 'ellipse': 5, 'hyperbola': 5,
            'coordinate geometry': 5, 'straight line': 4,
            'circle': 3, 'conic': 5, 'vector': 3,
        }

        # ── Physics ───────────────────────────────────────────────────────
        physics_keywords = {
            'velocity': 5, 'acceleration': 5, 'newton': 5,
            'force': 4, 'momentum': 5, 'projectile': 5,
            'circular motion': 5, 'gravitation': 5, 'torque': 5,
            'work energy': 5, 'kinetic energy': 5, 'potential energy': 5,
            'simple harmonic': 5, 'wave': 4, 'sound': 3,
            'optics': 5, 'refraction': 5, 'reflection': 4, 'lens': 4,
            'mirror': 4, 'electric field': 5, 'magnetic field': 5,
            'capacitor': 5, 'resistor': 5, 'inductor': 5,
            'thermodynamics': 5, 'heat': 3, 'temperature': 3,
            'photon': 5, 'electron': 4, 'nucleus': 4,
            'radioactive': 5, 'friction': 4, 'viscosity': 5,
            'surface tension': 5, 'pressure': 3, 'buoyancy': 5,
        }

        # ── Chemistry ─────────────────────────────────────────────────────
        chemistry_keywords = {
            'molecule': 4, 'atom': 3, 'bond': 3, 'ionic': 4,
            'covalent': 5, 'reaction': 3, 'acid': 4, 'base': 3,
            'salt': 3, 'organic': 5, 'inorganic': 5,
            'oxidation': 5, 'reduction': 4, 'redox': 5,
            'mole': 4, 'molarity': 5, 'molality': 5,
            'enthalpy': 5, 'entropy': 5, 'gibbs': 5,
            'catalyst': 5, 'enzyme': 3, 'polymer': 5,
            'hydrocarbon': 5, 'alkane': 5, 'alkene': 5, 'alkyne': 5,
            'alcohol': 4, 'aldehyde': 5, 'ketone': 5, 'amine': 5,
            'benzene': 5, 'aromatic': 5, 'electrolysis': 5,
            'electrode': 4, 'periodic table': 5, 'valence': 4,
            'hybridisation': 5, 'hybridization': 5, 'isomer': 5,
            'ph': 3, 'buffer': 4, 'titration': 5,
            'equilibrium constant': 5, 'le chatelier': 5,
        }

        # ── Biology ───────────────────────────────────────────────────────
        biology_keywords = {
            'cell': 3, 'tissue': 4, 'organ': 3,
            'dna': 5, 'rna': 5, 'protein': 4, 'enzyme': 4,
            'photosynthesis': 5, 'respiration': 4, 'mitosis': 5,
            'meiosis': 5, 'genetics': 5, 'chromosome': 5,
            'mutation': 4, 'evolution': 4, 'ecosystem': 5,
            'biodiversity': 5, 'hormone': 4, 'nervous system': 5,
            'digestion': 4, 'circulation': 4, 'excretion': 4,
            'reproduction': 4, 'bacteria': 4, 'virus': 4, 'fungi': 4,
        }

        # ── Computer Science ──────────────────────────────────────────────
        cs_keywords = {
            'algorithm': 5, 'array': 4, 'linked list': 5,
            'tree': 4, 'graph': 4, 'stack': 5, 'queue': 4,
            'sorting': 5, 'searching': 4, 'dynamic programming': 5,
            'recursion': 5, 'time complexity': 5, 'space complexity': 5,
            'big o': 5, 'binary search': 5, 'hash': 4, 'heap': 5,
            'bfs': 5, 'dfs': 5, 'dijkstra': 5, 'database': 4,
            'sql': 5, 'operating system': 5, 'process': 3,
            'thread': 4, 'compiler': 5, 'pointer': 4, 'memory': 3,
        }

        all_kw = [
            ('Mathematics',      math_keywords),
            ('Physics',          physics_keywords),
            ('Chemistry',        chemistry_keywords),
            ('Biology',          biology_keywords),
            ('Computer Science', cs_keywords),
        ]

        for subj, kw_dict in all_kw:
            for kw, weight in kw_dict.items():
                if kw in q:
                    scores[subj] += weight

        best_subject = max(scores, key=scores.get)
        best_score   = scores[best_subject]

        # Only return a subject if we have confident signal (score >= 3)
        if best_score >= 3:
            return best_subject

        return None  # Genuinely ambiguous — search all subjects

    def get_citation_context(self, question: str, subject: str = None) -> dict:
        """
        Returns retrieved chunks + formatted citation string.
        Auto-detects subject if not provided so correct book is cited.
        """
        # Auto-detect subject from question if not explicitly provided
        detected_subject = subject or self.detect_subject(question)
        
        chunks = self.retrieve(question, subject=detected_subject, k=3)
        
        # If subject-filtered retrieval returned nothing, try without filter
        if not chunks and detected_subject:
            chunks = self.retrieve(question, subject=None, k=3)
        
        return {
            'chunks': chunks,
            'citation_text': '\n'.join(
                f"• {c['source']} ({c['topic']})" for c in chunks
            ),
            'has_sources': len(chunks) > 0,
            'detected_subject': detected_subject
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