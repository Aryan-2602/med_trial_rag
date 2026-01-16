"""Load and manage Q&A examples for prompt engineering."""

import json
import math
from pathlib import Path
from typing import Any


class PromptExamples:
    """Manage Q&A examples for enhancing prompts."""
    
    def __init__(self, examples_dir: Path | str | None = None):
        """
        Initialize prompt examples loader.
        
        Args:
            examples_dir: Directory containing Q&A JSON files (default: data/prompt_engineering)
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent.parent / "data" / "prompt_engineering"
        self.examples_dir = Path(examples_dir)
        self._examples: list[dict[str, Any]] = []
        self._loaded = False
        self._auto_clean = True  # Automatically clean entries when loading
    
    def _is_nan(self, value: Any) -> bool:
        """Check if value is NaN."""
        if isinstance(value, float):
            return math.isnan(value)
        return False
    
    def _clean_answer(self, question: str, answer: Any) -> str | None:
        """
        Clean and convert answer to natural language.
        
        Returns None if answer should be filtered out.
        """
        # Filter out "Not computable" entries
        if isinstance(answer, str):
            if answer.lower().startswith("not computable"):
                return None
            if answer.lower() == "computed in file.":
                return None  # Too vague
            # Keep natural language strings (including "partially computable")
            return answer
        
        # Handle dictionary answers - convert to natural language
        if isinstance(answer, dict):
            if not answer or len(answer) == 0:
                return None
            
            # Try to extract meaningful information
            natural_parts = []
            
            # Temporal co-occurrence analysis
            if "n" in answer and "a_responder_and_immune" in answer:
                n = answer.get("n", 0)
                a = answer.get("a_responder_and_immune", 0)
                b = answer.get("b_responder_no_immune", 0)
                c = answer.get("c_nonresponder_immune", 0)
                d = answer.get("d_nonresponder_no_immune", 0)
                if n > 0:
                    natural_parts.append(
                        f"Analysis of {n} patients shows: {a} responders with immune-related AEs, "
                        f"{b} responders without immune AEs, {c} non-responders with immune AEs, "
                        f"and {d} non-responders without immune AEs."
                    )
            
            # AE window counts
            elif "ae_relative_to_dose_window_counts" in answer:
                counts = answer["ae_relative_to_dose_window_counts"]
                note = answer.get("note", "")
                total = sum(counts.values())
                natural_parts.append(
                    f"Adverse events relative to dose timing: Total of {total} AEs across all time windows. "
                    f"Distribution: {', '.join([f'{k} days: {v} AEs' for k, v in counts.items()])}. "
                    f"{note}"
                )
            
            # Site statistics
            elif "outlier_sites_by_rate_grade>=3" in answer:
                outliers = answer.get("outlier_sites_by_rate_grade>=3", [])
                mean = answer.get("overall_site_rate_mean", 0)
                sd = answer.get("overall_site_rate_sd", 0)
                method = answer.get("method", "")
                if len(outliers) == 0:
                    natural_parts.append(
                        f"No outlier sites detected. Overall site rate for Grade ≥3 AEs: "
                        f"mean = {mean:.2%}, standard deviation = {sd:.2%}. {method}"
                    )
                else:
                    natural_parts.append(
                        f"Outlier sites with abnormal Grade ≥3 AE rates: {', '.join(map(str, outliers))}. "
                        f"Overall site rate: mean = {mean:.2%}, SD = {sd:.2%}. {method}"
                    )
            
            # PFS hazard ratio simulation
            elif "hepatic_gte3_vs_pfs_summary" in answer:
                summary = answer["hepatic_gte3_vs_pfs_summary"]
                caveat = answer.get("caveat", "")
                n_subjects = summary.get("n_subjects_pfs", 0)
                n_events = summary.get("n_events", 0)
                n_hepatic = summary.get("n_hepatic_gte3_subjects", 0)
                median_all = summary.get("median_pfs_events_only_all", 0)
                median_excl = summary.get("median_pfs_events_only_excluding_hepatic_gte3", 0)
                hr = summary.get("pseudo_hr_excluding_vs_all", 0)
                natural_parts.append(
                    f"Simulation of removing patients with Grade ≥3 hepatic AEs: "
                    f"Of {n_subjects} subjects with PFS data, {n_events} events occurred. "
                    f"{n_hepatic} subjects had Grade ≥3 hepatic AEs. "
                    f"Median PFS (all subjects): {median_all:.2f} months. "
                    f"Median PFS (excluding hepatic Grade ≥3): {median_excl:.2f} months. "
                    f"Pseudo-hazard ratio: {hr:.3f}. {caveat}"
                )
            
            # Drug interaction flags
            elif "per_subject_flags_sample_first_50" in answer:
                flags = answer.get("per_subject_flags_sample_first_50", [])
                definitions = answer.get("definitions", {})
                if len(flags) > 0:
                    nsaid_count = sum(1 for f in flags if f.get("has_peri_nsaid", False))
                    folic_count = sum(1 for f in flags if f.get("has_folic_prior", False))
                    b12_count = sum(1 for f in flags if f.get("has_b12_prior", False))
                    dexa_count = sum(1 for f in flags if f.get("has_dexa_premed", False))
                    natural_parts.append(
                        f"Drug interaction analysis for {len(flags)} patients: "
                        f"{nsaid_count} with peri-dose NSAID, {folic_count} with prior folic acid, "
                        f"{b12_count} with prior B12, {dexa_count} with dexamethasone premedication."
                    )
                    if definitions:
                        def_text = " ".join([f"{k}: {v}" for k, v in definitions.items()])
                        natural_parts.append(f"Definitions: {def_text}")
            
            # Site lag statistics
            elif "site_lag_stats_top10" in answer:
                stats = answer.get("site_lag_stats_top10", [])
                note = answer.get("note", "")
                if len(stats) > 0:
                    natural_parts.append("Time-to-randomization analysis for top 10 sites: ")
                    site_details = []
                    for stat in stats[:5]:
                        invid = int(stat.get("INVID", 0))
                        median = stat.get("median", 0)
                        mean = stat.get("mean", 0)
                        count = stat.get("count", 0)
                        screen_fail = stat.get("screen_fail_rate", 0)
                        site_details.append(
                            f"Site {invid}: {count} subjects, median lag {median:.1f} days "
                            f"(mean {mean:.1f}), screen fail rate {screen_fail:.1%}"
                        )
                    natural_parts.append("; ".join(site_details))
                    if note:
                        natural_parts.append(note)
            
            # Eligible patients summary
            elif "eligible_patients_summary" in answer:
                summary = answer["eligible_patients_summary"]
                n_ecog = summary.get("n_with_ecog", 0)
                pct = summary.get("pct_meet_ecog_0_1", 0)
                sample = summary.get("sample_first_50", [])
                note = answer.get("note", "")
                natural_parts.append(
                    f"Eligibility analysis: {n_ecog} patients with ECOG data. "
                    f"{pct:.1%} meet ECOG 0-1 criteria (required for inclusion)."
                )
                if len(sample) > 0:
                    ecog_0 = sum(1 for s in sample if s.get("ECOG") == 0.0)
                    ecog_1 = sum(1 for s in sample if s.get("ECOG") == 1.0)
                    natural_parts.append(
                        f"Sample of {len(sample)} patients: {ecog_0} with ECOG 0, {ecog_1} with ECOG 1."
                    )
                if note:
                    natural_parts.append(note)
            
            # If we couldn't convert, check if it has meaningful data
            else:
                # For unknown structures, try to keep if it has substantial data
                if len(str(answer)) > 50:  # Has some content
                    # Return as JSON string for now (better than nothing)
                    return json.dumps(answer, indent=2)
                return None
            
            if natural_parts:
                return " ".join(natural_parts)
            return None
        
        # Filter out other types (lists without context, numbers, etc.)
        return None
    
    def load(self) -> None:
        """Load all Q&A examples from JSON files in the examples directory."""
        if self._loaded:
            return
        
        if not self.examples_dir.exists():
            return
        
        # Find all JSON files (exclude README and other non-QA files)
        json_files = [f for f in self.examples_dir.glob("*.json") 
                     if not f.name.startswith("_")]  # Skip files starting with _
        
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Handle both list and dict formats
                if isinstance(data, list):
                    # List format: already in Q&A format
                    for item in data:
                        question = item.get("question", "")
                        answer = item.get("answer", "")
                        
                        if not question or not answer:
                            continue
                        
                        # Clean answer if auto-clean is enabled
                        if self._auto_clean:
                            cleaned_answer = self._clean_answer(question, answer)
                            if cleaned_answer is None:
                                continue  # Skip filtered entries
                            answer = cleaned_answer
                        
                        self._examples.append({
                            "question": question,
                            "answer": answer,
                            "source": json_file.stem,
                        })
                
                elif isinstance(data, dict):
                    # Dict format: keys are questions, values are answers
                    for question, answer in data.items():
                        if not question:
                            continue
                        
                        # Clean answer if auto-clean is enabled
                        if self._auto_clean:
                            cleaned_answer = self._clean_answer(question, answer)
                            if cleaned_answer is None:
                                continue  # Skip filtered entries
                            answer = cleaned_answer
                        
                        self._examples.append({
                            "question": question,
                            "answer": answer,
                            "source": json_file.stem,
                        })
            except Exception as e:
                # Skip files that can't be loaded
                continue
        
        self._loaded = True
    
    def get_examples(self, max_examples: int = 5, query: str | None = None) -> list[dict[str, Any]]:
        """
        Get Q&A examples, optionally filtered by query similarity.
        
        Args:
            max_examples: Maximum number of examples to return
            query: Optional query to filter/sort examples by relevance
        
        Returns:
            List of example dicts with 'question' and 'answer' keys
        """
        if not self._loaded:
            self.load()
        
        examples = self._examples.copy()
        
        # Simple keyword-based filtering if query provided
        if query and examples:
            query_lower = query.lower()
            scored = []
            for ex in examples:
                question = ex.get("question", "").lower()
                score = sum(1 for word in query_lower.split() if word in question)
                scored.append((score, ex))
            
            # Sort by relevance score
            scored.sort(key=lambda x: x[0], reverse=True)
            examples = [ex for _, ex in scored]
        
        return examples[:max_examples]
    
    def format_for_prompt(self, max_examples: int = 3, query: str | None = None) -> str:
        """
        Format examples as a string for inclusion in prompts.
        
        Args:
            max_examples: Maximum number of examples to include
            query: Optional query to filter examples
        
        Returns:
            Formatted string with examples
        """
        examples = self.get_examples(max_examples=max_examples, query=query)
        
        if not examples:
            return ""
        
        formatted = ["Here are some example Q&A pairs from similar queries:\n"]
        
        for i, ex in enumerate(examples, 1):
            question = ex.get("question", "")
            answer = ex.get("answer", "")
            formatted.append(f"Example {i}:")
            formatted.append(f"Q: {question}")
            formatted.append(f"A: {answer}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def count(self) -> int:
        """Get total number of loaded examples."""
        if not self._loaded:
            self.load()
        return len(self._examples)

