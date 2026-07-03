import json
import math
import re
import hashlib
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Helper to invoke OpenAI LLM if key is available, else run mock logic."""
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI error, falling back to mock: {e}")
                # Fall back to mock below
        
        return self._generate_mock_response(prompt)

    def generate_clarifications(self, title: str, description: str) -> List[str]:
        """Ask 3 clarifying questions about the problem."""
        system_prompt = (
            "You are a Clarifier Agent. Analyze the user's problem and return exactly 3 highly specific clarifying questions "
            "that will help design a better solution. Return your answer in JSON format as {\"questions\": [\"q1\", \"q2\", \"q3\"]}"
        )
        prompt = f"Problem Title: {title}\nProblem Description: {description}"
        
        try:
            res_str = self._call_llm(prompt, system_prompt)
            data = json.loads(res_str)
            return data.get("questions", [])
        except Exception:
            return [
                f"What are the main obstacles you run into when dealing with '{title}'?",
                "How long has this issue been occurring, and what have you tried so far?",
                "What is your target timeline or desired outcome for solving this?"
            ]

    def generate_diagnosis(self, title: str, description: str, q_and_a: List[Dict[str, str]], rag_context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Diagnose the problem using 5 Whys, SWOT, and First Principles.
        
        If rag_context is provided (from Qdrant), it contains similar past cases
        that are injected into the prompt for RAG-enhanced diagnosis.
        """
        system_prompt = (
            "You are a Diagnosis Agent. Analyze the problem and clarifications. Return a JSON object with: \n"
            "1. 'root_causes': A list of strings representing a 5 Whys depth analysis.\n"
            "2. 'swot_analysis': An object with lists for 'strengths', 'weaknesses', 'opportunities', 'threats'.\n"
            "3. 'first_principles': A list of strings breaking the problem down to fundamental components.\n"
            "Format the output strictly as a JSON object."
        )
        
        qa_str = "\n".join([f"Q: {item['question']}\nA: {item.get('answer', 'N/A')}" for item in q_and_a])
        prompt = f"Problem Title: {title}\nDescription: {description}\n\nClarifications:\n{qa_str}"

        # Inject RAG context if available
        if rag_context:
            context_str = "\n\n".join([
                f"Past Case: {case.get('problem_summary', '')}\nResolution: {case.get('solution_summary', '')}"
                for case in rag_context
            ])
            prompt += f"\n\n--- Similar Previously Resolved Cases (use as reference) ---\n{context_str}"
        
        try:
            res_str = self._call_llm(prompt, system_prompt)
            return json.loads(res_str)
        except Exception:
            # Mock fallback
            return {
                "root_causes": [
                    f"Initial symptom: {title} is causing stress.",
                    "Why? There is no clear roadmap or system to execute the work.",
                    "Why? The goals are currently too abstract and undefined.",
                    "Why? You haven't broken the major objective down into individual milestones.",
                    "Root cause: Lack of systematic prioritization and habit structuring."
                ],
                "swot_analysis": {
                    "strengths": ["Strong motivation to resolve the issue", "Recognizing the need for a structural change"],
                    "weaknesses": ["Lack of daily consistency", "Analysis paralysis holding back action"],
                    "opportunities": ["Leveraging technology tools for task management", "Setting up accountability loops"],
                    "threats": ["Burnout from attempting too much at once", "Distractions pulling attention away"]
                },
                "first_principles": [
                    "Define the absolute core requirement (e.g., what is the minimal definition of progress?).",
                    "Identify non-negotiable constraints (e.g., time, resources, energy).",
                    "Construct a feedback loop to measure success on a daily basis."
                ]
            }

    def generate_solutions(self, title: str, description: str, diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate 3 potential solution strategies, ranked with scores."""
        system_prompt = (
            "You are a Strategist Agent and Critic Agent. Output 3 distinct solutions to the problem. "
            "Each solution should have a: 'title', 'strategy_details', 'impact' (1-10), 'confidence' (1-10), 'risk' (1-10), 'constraints', and 'score'.\n"
            "Score formula: (impact * 0.4) + (confidence * 0.4) - (risk * 0.2). Scale all values 1 to 10.\n"
            "Return JSON as: {\"solutions\": [ {solution1}, {solution2}, {solution3} ]}"
        )
        prompt = f"Problem: {title}\nDescription: {description}\nDiagnosis: {json.dumps(diagnosis)}"
        
        try:
            res_str = self._call_llm(prompt, system_prompt)
            data = json.loads(res_str)
            return data.get("solutions", [])
        except Exception:
            # Mock fallback
            return [
                {
                    "title": "Minimalist Action Plan (High Velocity)",
                    "strategy_details": "Focus on doing exactly one critical task per day. Timebox study/work blocks to 25 minutes using Pomodoro, and remove all physical distractions.",
                    "impact": 8.5,
                    "confidence": 9.0,
                    "risk": 2.0,
                    "constraints": "Requires high discipline during the blocks",
                    "score": 6.6
                },
                {
                    "title": "Milestone-Driven Plan (High Structure)",
                    "strategy_details": "Create weekly check-ins, build a visual progress tracker, and map out dependencies between tasks. Allocate a fixed 2-hour window every evening.",
                    "impact": 9.0,
                    "confidence": 8.0,
                    "risk": 3.0,
                    "constraints": "Takes planning overhead to maintain",
                    "score": 6.2
                },
                {
                    "title": "Accountability & Habit Stacking (External Motivation)",
                    "strategy_details": "Partner with a peer, commit to daily checkins, and pair new productive habits directly with existing daily routines (e.g. review tasks while drinking morning coffee).",
                    "impact": 7.5,
                    "confidence": 8.5,
                    "risk": 4.0,
                    "constraints": "Relies on another person's availability",
                    "score": 5.6
                }
            ]

    def generate_plan(self, problem_title: str, solution_title: str, solution_details: str) -> List[Dict[str, Any]]:
        """Generate structured tasks and milestones for execution."""
        system_prompt = (
            "You are a Planner Agent. Create a structured action checklist to implement the selected strategy. "
            "Output a JSON object containing a 'tasks' list. Each task must have a: 'title', 'priority' ('High', 'Medium', 'Low'), "
            "and 'timeline' (e.g. 'Week 1', 'Week 2', 'Day 1').\n"
            "Format: {\"tasks\": [ {\"title\": \"...\", \"priority\": \"...\", \"timeline\": \"...\"} ]}"
        )
        prompt = f"Problem: {problem_title}\nSelected Strategy: {solution_title}\nStrategy Details: {solution_details}"
        
        try:
            res_str = self._call_llm(prompt, system_prompt)
            data = json.loads(res_str)
            return data.get("tasks", [])
        except Exception:
            # Mock fallback
            return [
                {"title": "Set up a distraction-free workspace and clear off digital tabs", "priority": "High", "timeline": "Day 1"},
                {"title": "Define the single most important task for the current week", "priority": "High", "timeline": "Day 1"},
                {"title": "Execute first 25-minute focused execution block", "priority": "Medium", "timeline": "Day 2"},
                {"title": "Log daily progress and adjustments in a tracker journal", "priority": "Medium", "timeline": "Day 2-7"},
                {"title": "Conduct weekly review and schedule tasks for the next milestone block", "priority": "High", "timeline": "Week 1 End"},
                {"title": "Establish an accountability partner check-in schedule", "priority": "Low", "timeline": "Week 2"}
            ]

    def get_embedding(self, text: str) -> List[float]:
        """Get 128-dimensional embedding vector for text. Real OpenAI if key present, else local deterministic vector."""
        if self.client:
            try:
                response = self.client.embeddings.create(
                    input=[text.replace("\n", " ")],
                    model="text-embedding-3-small"
                )
                # text-embedding-3-small gives 1536 dims. We can slice to 128 for compactness or use it directly.
                # Let's slice to 128 for database compactness
                full_vector = response.data[0].embedding
                # Normalize sliced vector
                sliced = full_vector[:128]
                norm = math.sqrt(sum(x*x for x in sliced))
                if norm > 0:
                    sliced = [x/norm for x in sliced]
                return sliced
            except Exception as e:
                print(f"Embedding API error, falling back to deterministic hashing: {e}")
        
        # Deterministic mock embedding (128 dimensions)
        # We can construct this by taking the TF-IDF-like hash values of words
        vector = [0.0] * 128
        words = re.findall(r'\w+', text.lower())
        if not words:
            return vector
        
        for w in words:
            # Use md5 to hash the word into a slot
            h = hashlib.md5(w.encode('utf-8')).hexdigest()
            # Split hash into 4 chunks to distribute weights
            for i in range(4):
                val = int(h[i*8:(i+1)*8], 16)
                index = val % 128
                weight = 1.0 / (i + 1)
                vector[index] += weight
                
        # Normalize the vector to unit length
        magnitude = math.sqrt(sum(v*v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
            
        return vector

    def _generate_mock_response(self, prompt: str) -> str:
        """Generate structured mock responses depending on keywords in the prompt."""
        # Simple parser to find context
        if "questions" in prompt or "Clarifier" in prompt:
            return json.dumps({
                "questions": [
                    "What specific tools, systems, or methodologies are you currently using to manage this problem?",
                    "On a scale of 1-10, how severely does this issue impact your day-to-day productivity?",
                    "What is the single biggest bottleneck preventing you from resolving this immediately?"
                ]
            })
        elif "root_causes" in prompt or "Diagnosis" in prompt:
            return json.dumps({
                "root_causes": [
                    "The user is experiencing friction due to lack of standard operating procedures.",
                    "Why? No structured rules or boundaries have been set for tasks.",
                    "Why? The scope of work is overly broad and lacks clear definitions.",
                    "Why? The root goal was not broken down into smaller, actionable components.",
                    "Root cause: Insufficient division of labor and lack of atomic steps."
                ],
                "swot_analysis": {
                    "strengths": ["Strong motivation", "Awareness of bottlenecks"],
                    "weaknesses": ["Lack of planning framework", "Vague goals"],
                    "opportunities": ["Using ResolveAI planning models", "Establishing regular check-in schedules"],
                    "threats": ["Overwhelm from complex tasks", "Procrastination from lack of clear next-actions"]
                },
                "first_principles": [
                    "Isolate the problem into its simplest truth: what is the single basic unit of progress?",
                    "Deconstruct external constraints from self-imposed limitations.",
                    "Rebuild a minimal framework focused strictly on executing this basic unit."
                ]
            })
        elif "solutions" in prompt or "Strategist" in prompt:
            return json.dumps({
                "solutions": [
                    {
                        "title": "Strategy A: Structured Timeboxing (Pomodoro Core)",
                        "strategy_details": "Implement focused 25-minute intervals of work, separated by 5-minute breaks. Set 1 daily priority.",
                        "impact": 8.0,
                        "confidence": 8.5,
                        "risk": 1.5,
                        "constraints": "Requires sticking to the timer rigorously",
                        "score": 6.3
                    },
                    {
                        "title": "Strategy B: Kanban Milestone Tracking",
                        "strategy_details": "Map out all tasks on a visual Board with status lanes. Limit work-in-progress to maximum 2 active tasks.",
                        "impact": 9.0,
                        "confidence": 7.5,
                        "risk": 2.5,
                        "constraints": "Takes initial setup time",
                        "score": 6.1
                    },
                    {
                        "title": "Strategy C: Collaborative Accountability",
                        "strategy_details": "Pair with a partner to do weekly check-ins and share updates. Use external stakes (like public commitments) to stay driven.",
                        "impact": 7.0,
                        "confidence": 8.0,
                        "risk": 3.0,
                        "constraints": "Depends on third-party availability",
                        "score": 5.4
                    }
                ]
            })
        else:
            return json.dumps({
                "tasks": [
                    {"title": "Initial workspace setup and organizing raw materials", "priority": "High", "timeline": "Day 1"},
                    {"title": "Execute first focused task iteration block", "priority": "High", "timeline": "Day 2"},
                    {"title": "Track output logs and identify friction points", "priority": "Medium", "timeline": "Day 3"},
                    {"title": "Conduct weekly audit and adjust strategy scorecards", "priority": "High", "timeline": "Week 1 End"}
                ]
            })

ai_service = AIService()
