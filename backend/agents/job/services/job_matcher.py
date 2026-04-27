"""Job matcher service — score jobs against the knowledge bank.

Always runs algorithmic matching (skill overlap + TF-IDF).
Adds LLM deep analysis on top when a provider is configured.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from shared.algorithms.skill_matcher import compute_skill_overlap
from shared.algorithms.tfidf import compute_similarity
from shared.calibration.scorer import compute_weighted_score, DEFAULT_WEIGHTS
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.knowledge_repo import KnowledgeRepository

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider


class JobMatcherService:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        job_repo: JobRepository,
        llm_provider: LLMProvider | None = None,
    ):
        self._knowledge_repo = knowledge_repo
        self._job_repo = job_repo
        self._llm = llm_provider

    def match_job(self, job_id: int, use_llm: bool = False) -> dict:
        """Score a single job against the knowledge bank.

        use_llm: if True AND LLM is configured, run deep semantic analysis.
                 Default False to keep batch matching fast.
        """
        job = self._job_repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        parsed_data = json.loads(job["parsed_data"]) if isinstance(job["parsed_data"], str) else job["parsed_data"]
        knowledge = self._knowledge_repo.get_full_knowledge_bank()

        # Algorithmic scoring (always runs — free, fast)
        features = self._compute_features(parsed_data, knowledge)
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)

        breakdown = {**features, "weighted_score": score}

        # LLM deep analysis (only when explicitly requested)
        if use_llm and self._llm and knowledge.get("experiences"):
            try:
                from agents.job.prompts.match_job import build_prompt, SYSTEM_PROMPT

                job_for_prompt = {"title": job["title"], "company": job.get("company"), "parsed_data": parsed_data}
                prompt = build_prompt(knowledge, job_for_prompt)
                response = self._llm.complete(prompt, system=SYSTEM_PROMPT)

                # Strip markdown fences if present
                clean = response.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()

                llm_result = json.loads(clean)
                llm_score = llm_result.get("overall_score", score)
                # Blend: 40% algorithmic + 60% LLM
                score = 0.4 * score + 0.6 * llm_score
                breakdown["llm_score"] = llm_score
                breakdown["llm_analysis"] = llm_result
                breakdown["weighted_score"] = score
            except Exception as e:
                breakdown["llm_error"] = str(e)

        # Save to DB
        self._job_repo.update_match_score(job_id, score=score, breakdown=breakdown)

        return {"job_id": job_id, "score": score, "breakdown": breakdown, "llm_analysis": breakdown.get("llm_analysis")}

    def match_batch(self, job_ids: list[int]) -> list[dict]:
        """Score multiple jobs and return sorted by score descending."""
        results = [self.match_job(job_id) for job_id in job_ids]
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def _compute_features(self, parsed_data: dict, knowledge: dict) -> dict:
        """Compute algorithmic match features."""
        required_skills = parsed_data.get("required_skills", [])
        user_skill_names = [s["name"] for s in knowledge.get("skills", [])]

        # Skill overlap
        overlap = compute_skill_overlap(required_skills, user_skill_names)
        skills_score = overlap["score"]

        # TF-IDF similarity between job description and experience descriptions
        job_text = " ".join(required_skills)
        experience_text = " ".join(
            exp.get("description") or "" for exp in knowledge.get("experiences", [])
        )
        tfidf_score = compute_similarity(job_text, experience_text) if experience_text.strip() else 0.0

        return {
            "skills_overlap": skills_score,
            "tfidf": tfidf_score,
            "semantic_sim": 0.0,  # Requires Sentence Transformers
            "experience_years": 0.0,  # TODO: compute from date ranges
        }
