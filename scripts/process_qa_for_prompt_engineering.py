#!/usr/bin/env python3
"""Process Q&A JSON files for prompt engineering.

Cleans Q&A data by:
- Removing "Not computable" entries
- Converting structured answers to natural language
- Filtering out low-quality entries
- Saving cleaned data for prompt engineering use
"""

import json
import math
from pathlib import Path
from typing import Any


def is_nan(value: Any) -> bool:
    """Check if value is NaN."""
    if isinstance(value, float):
        return math.isnan(value)
    return False


def convert_structured_to_natural_language(question: str, answer: Any) -> str | None:
    """
    Convert structured answer data to natural language.
    
    Returns None if answer should be filtered out.
    """
    # Filter out "Not computable" entries
    if isinstance(answer, str):
        if answer.lower().startswith("not computable"):
            return None
        if answer.lower().startswith("partially computable"):
            # Keep but note it's partial
            return answer
        if answer.lower() == "computed in file.":
            return None  # Too vague
        # Return natural language strings as-is
        return answer
    
    # Handle dictionary answers
    if isinstance(answer, dict):
        # Check for empty or minimal data
        if not answer or len(answer) == 0:
            return None
        
        # Handle specific structured formats
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
                if not is_nan(answer.get("odds_ratio")):
                    or_val = answer.get("odds_ratio")
                    natural_parts.append(f"The odds ratio is {or_val:.2f}.")
        
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
                # Count flags
                nsaid_count = sum(1 for f in flags if f.get("has_peri_nsaid", False))
                folic_count = sum(1 for f in flags if f.get("has_folic_prior", False))
                b12_count = sum(1 for f in flags if f.get("has_b12_prior", False))
                dexa_count = sum(1 for f in flags if f.get("has_dexa_premed", False))
                
                natural_parts.append(
                    f"Drug interaction analysis for {len(flags)} patients: "
                    f"{nsaid_count} with peri-dose NSAID, {folic_count} with prior folic acid, "
                    f"{b12_count} with prior B12, {dexa_count} with dexamethasone premedication. "
                )
                
                if definitions:
                    def_text = " ".join([f"{k}: {v}" for k, v in definitions.items()])
                    natural_parts.append(f"Definitions: {def_text}")
        
        # Site lag statistics
        elif "site_lag_stats_top10" in answer:
            stats = answer.get("site_lag_stats_top10", [])
            note = answer.get("note", "")
            
            if len(stats) > 0:
                natural_parts.append(
                    f"Time-to-randomization analysis for top 10 sites: "
                )
                site_details = []
                for stat in stats[:5]:  # Top 5 for brevity
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
                f"{pct:.1%} meet ECOG 0-1 criteria (required for inclusion). "
            )
            
            if len(sample) > 0:
                ecog_0 = sum(1 for s in sample if s.get("ECOG") == 0.0)
                ecog_1 = sum(1 for s in sample if s.get("ECOG") == 1.0)
                natural_parts.append(
                    f"Sample of {len(sample)} patients: {ecog_0} with ECOG 0, {ecog_1} with ECOG 1. "
                )
            
            if note:
                natural_parts.append(note)
        
        # If we couldn't convert, check if it has meaningful data
        else:
            # Try to extract any meaningful information
            if len(answer) > 0:
                # Keep as JSON string if it has data
                return json.dumps(answer, indent=2)
            return None
        
        if natural_parts:
            return " ".join(natural_parts)
        return None
    
    # Filter out other types (lists without context, numbers, etc.)
    return None


def process_qa_file(input_path: Path, output_path: Path) -> None:
    """Process Q&A JSON file and save cleaned version."""
    print(f"📖 Reading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"📊 Original entries: {len(data)}")
    
    cleaned_data = []
    removed_count = 0
    
    for question, answer in data.items():
        # Convert structured answer to natural language
        natural_answer = convert_structured_to_natural_language(question, answer)
        
        if natural_answer is None:
            removed_count += 1
            continue
        
        cleaned_data.append({
            "question": question,
            "answer": natural_answer,
            "source": "S130_QA_ALL",
        })
    
    print(f"✅ Kept {len(cleaned_data)} entries")
    print(f"❌ Removed {removed_count} entries")
    
    # Save cleaned data
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved to {output_path}")
    
    # Print sample entries
    print("\n📝 Sample entries:")
    for i, entry in enumerate(cleaned_data[:3], 1):
        print(f"\n{i}. Q: {entry['question'][:80]}...")
        print(f"   A: {entry['answer'][:150]}...")


if __name__ == "__main__":
    import sys
    
    # Default paths
    input_file = Path("data/S130_QA_ALL.json")
    output_file = Path("data/prompt_engineering/S130_QA_ALL_cleaned.json")
    
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"❌ Error: {input_file} not found")
        sys.exit(1)
    
    process_qa_file(input_file, output_file)

