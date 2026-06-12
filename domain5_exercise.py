"""
domain5_exercise.py
====================
Domain 5 Build Exercise — Context Management & Reliability

What this demonstrates (mapped to task statements):

  5.1 → Persistent case facts block injected verbatim at the TOP of every
         prompt. Conversational context can be compressed; case facts never are.
         Tool results trimmed to relevant fields before context injection.

  5.3 → Structured error propagation with all four required components:
         failure_type, what_was_attempted, partial_results, potential_alternatives.
         Workflow continues with partial results — not terminated on single failure.

  5.4 → Summary injection: Subagent A's findings summarised and injected into
         Subagent B's prompt. Subagent B never sees the verbose discovery process —
         only structured output. Coordinator maintains high-level state.

  5.6 → Structured claim-source mappings preserved through synthesis.
         Conflicting figures (same metric, same year, different methodology):
           both values annotated with full attribution — neither discarded.
         Coverage annotation for timed-out source — gap is surfaced, not hidden.
         Content-appropriate rendering: table for numerical comparisons.

Architecture:
  coordinator()
    └── run_subagent_a()   — collection: three sources, one timeout
    └── run_subagent_b()   — synthesis: conflict annotation + coverage gap

Cost: ~4 API calls, all claude-haiku-4-5. Expect < $0.01 to run.

Setup:
  source .venv/bin/activate
  python domain5_exercise.py
"""

import json
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5"


# ─────────────────────────────────────────────────────────────────────────────
# CASE FACTS BLOCK
#
# 5.1 concept: transactional facts extracted into a persistent structured block.
# Injected verbatim at the TOP of every system prompt in this pipeline.
# Never summarised. Never compressed. Survives multi-turn conversations intact.
#
# Placement at TOP is deliberate — benefits from reliable beginning-of-context
# processing ("lost in the middle" mitigation).
# ─────────────────────────────────────────────────────────────────────────────
CASE_FACTS = {
    "research_topic": "Global renewable energy capacity growth (2023)",
    "requestor": "Climate Policy Unit",
    "request_id": "CPR-2024-0041",
    "mandate": (
        "Preserve all source attribution. "
        "Surface conflicts. "
        "Annotate coverage gaps explicitly. "
        "Do not resolve conflicts — let the consumer decide."
    ),
    "required_fields": ["growth_pct", "source", "publication_date", "methodology"],
    "delivery_format": "Structured markdown report — tables for numerical comparisons",
}


def case_facts_block() -> str:
    """
    Returns the case facts block formatted for prompt injection.
    Always call this — never inline the dict — so every prompt uses
    the same canonical representation.
    """
    return (
        "## CASE FACTS (do not summarise — preserve verbatim in all prompts)\n"
        + json.dumps(CASE_FACTS, indent=2)
        + "\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MOCK DATA SOURCES
#
# Three simulated tool calls:
#   fetch_iea_2023()       → success, 34% growth
#   fetch_bloomberg_2023() → transient timeout (structured error)
#   fetch_irena_2023()     → success, 28% growth  ← conflicts with IEA (same year)
#
# IEA and IRENA both report 2023, same metric, different values — genuine conflict.
# Different methodologies explain the gap; the consumer must decide which to use.
# ─────────────────────────────────────────────────────────────────────────────

def fetch_iea_2023() -> dict:
    """IEA 2023 renewable capacity report — returns successfully."""
    return {
        "status": "success",
        "data": {
            # Provenance fields — all required for claim-source mapping (5.6)
            "claim": "Global renewable capacity grew by 34% in 2023",
            "value": "34%",
            "metric": "renewable_capacity_growth_yoy",
            "year": 2023,
            "source_url": "https://iea.org/reports/renewables-2023",
            "document_name": "IEA Renewables 2023 Report",
            "relevant_excerpt": (
                "Global renewable capacity additions reached a record high, "
                "growing 34% year-on-year in 2023, driven by solar PV and wind."
            ),
            "publication_date": "2023-11-15",
            "methodology": "Grid-connected utility-scale capacity additions only",
            # Fields irrelevant to downstream synthesis — trimmed before injection
            "internal_report_id": "IEA-R-2023-008",
            "data_collection_region": "OECD members + G20",
            "currency_base": "USD_2022",
            "revision_flag": False,
            "embargo_lifted": "2023-11-14T09:00:00Z",
        },
    }


def fetch_bloomberg_2023() -> dict:
    """
    BloombergNEF API — simulates a transient connection timeout.

    5.3 concept: structured error context with all four required components.
    The error is NOT silently suppressed (anti-pattern 1).
    The pipeline is NOT terminated (anti-pattern 2).
    This error propagates to Subagent B as a coverage annotation.
    """
    return {
        "status": "error",
        # Component 1: failure type — determines recovery strategy
        "failure_type": "transient",
        # Component 2: exactly what was attempted
        "what_was_attempted": (
            "GET https://api.bnef.com/v1/energy/renewables "
            "params={metric: 'capacity_growth_yoy', year: 2023, region: 'global'}"
        ),
        # Component 3: partial results before failure (none here — timed out before response)
        "partial_results": [],
        # Component 4: alternative approaches for recovery
        "potential_alternatives": [
            "Retry after 30s — transient network condition",
            "Query secondary endpoint: https://api.bnef.com/v2/energy/renewables",
            "Fall back to BNEF public summary PDF (2023-annual-report.pdf)",
        ],
        "error_detail": "Connection timed out after 30s. No data received.",
        "source_name": "BloombergNEF Renewable Energy Dataset 2023",
    }


def fetch_irena_2023() -> dict:
    """
    IRENA 2023 renewable capacity statistics — returns successfully.
    Reports 28% growth vs IEA's 34% — same metric, same year.
    Methodological difference (off-grid inclusion) explains the gap.
    """
    return {
        "status": "success",
        "data": {
            "claim": "Global renewable capacity grew by 28% in 2023",
            "value": "28%",
            "metric": "renewable_capacity_growth_yoy",
            "year": 2023,
            "source_url": "https://irena.org/publications/2023/renewable-capacity",
            "document_name": "IRENA Renewable Capacity Statistics 2023",
            "relevant_excerpt": (
                "Total renewable capacity additions in 2023 represented a 28% "
                "increase over the prior year, including off-grid and distributed generation."
            ),
            "publication_date": "2023-10-22",
            "methodology": "All renewables including off-grid and distributed generation",
            # Irrelevant fields — trimmed before injection
            "internal_dataset_id": "IRENA-DS-2023-CAP-Q4",
            "regional_breakdown_available": True,
            "next_update": "2024-Q1",
            "data_completeness_pct": 94.7,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# TOOL RESULT TRIMMING
#
# 5.1 concept: trim verbose tool results to relevant fields BEFORE injecting
# into context. Prevents token budget exhaustion from accumulated irrelevant
# data across multiple tool calls.
#
# Rule: errors pass through intact — all fields may be needed for recovery.
# ─────────────────────────────────────────────────────────────────────────────

# Only these fields are relevant to downstream synthesis
RELEVANT_DATA_FIELDS = {
    "claim", "value", "metric", "year",
    "source_url", "document_name", "relevant_excerpt",
    "publication_date", "methodology",
}


def trim_tool_result(raw_result: dict) -> dict:
    """
    Trim a successful tool result to relevant fields only.
    Errors are returned intact — recovery logic may need any field.
    """
    if raw_result.get("status") != "success":
        return raw_result
    trimmed_data = {
        k: v
        for k, v in raw_result["data"].items()
        if k in RELEVANT_DATA_FIELDS
    }
    return {"status": "success", "data": trimmed_data}


# ─────────────────────────────────────────────────────────────────────────────
# SUBAGENT A — COLLECTION
#
# Fresh context, focused task. Runs three source queries.
# Returns structured claim-source mappings + structured error context.
# Coordinator receives clean structured output — not the verbose process.
#
# Demonstrates:
#   - Case facts at TOP of system prompt (5.1)
#   - Tool result trimming before context injection (5.1)
#   - Structured error propagation (5.3)
#   - Claim-source mapping structure (5.6)
# ─────────────────────────────────────────────────────────────────────────────

def run_subagent_a() -> dict:
    """
    Collection subagent: queries three data sources, returns structured findings.
    """
    print("\n── SUBAGENT A: Collection ──────────────────────────────────")

    # Execute the three tool calls
    raw_iea = fetch_iea_2023()
    raw_bloomberg = fetch_bloomberg_2023()   # Transient timeout
    raw_irena = fetch_irena_2023()

    # Trim successful results before injecting into context (5.1)
    iea = trim_tool_result(raw_iea)
    bloomberg = trim_tool_result(raw_bloomberg)   # Error — passes through intact
    irena = trim_tool_result(raw_irena)

    print(f"  IEA:        {iea['status']}")
    print(f"  Bloomberg:  {bloomberg['status']} ({bloomberg.get('failure_type', '-')})")
    print(f"  IRENA:      {irena['status']}")

    # Inject trimmed results into context
    tool_results = json.dumps(
        {"source_iea": iea, "source_bloomberg": bloomberg, "source_irena": irena},
        indent=2,
    )

    system_prompt = f"""{case_facts_block()}
You are a research collection agent. Three data source queries have been run.
Your job: return structured claim-source mappings for successful retrievals,
and structured error context for any failures.

Return a single JSON object — no prose, no markdown wrapper:
{{
  "successful_claims": [
    {{
      "claim": "...",
      "value": "...",
      "metric": "...",
      "year": ...,
      "source_url": "...",
      "document_name": "...",
      "relevant_excerpt": "...",
      "publication_date": "...",
      "methodology": "..."
    }}
  ],
  "failed_sources": [
    {{
      "source_name": "...",
      "failure_type": "transient | validation | business | permission",
      "what_was_attempted": "...",
      "partial_results": [],
      "potential_alternatives": ["..."]
    }}
  ],
  "coverage_note": "One sentence: what data is missing and why."
}}

Rules:
- Preserve ALL provenance fields from successful source data. Do not summarise.
- For failures, include all four structured error components.
- Do not invent or modify any values. Report only what the tool results contain.
"""

    user_message = f"""Tool results from three source queries:

{tool_results}

Return the structured claim-source mappings and error context as specified.
Return raw JSON only — no markdown fences."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_output = response.content[0].text.strip()

    # Parse JSON — strip markdown fences if model added them despite instructions
    json_str = raw_output
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        # Surface the parse failure — do not silently return empty (anti-pattern)
        print(f"  ⚠ Subagent A JSON parse error: {e}")
        result = {
            "successful_claims": [],
            "failed_sources": [{
                "source_name": "subagent_a_output",
                "failure_type": "internal",
                "what_was_attempted": "Parse Subagent A JSON response",
                "partial_results": [raw_output[:500]],
                "potential_alternatives": ["Retry with stricter JSON-only prompt"],
            }],
            "coverage_note": "Subagent A output could not be parsed — all findings unavailable.",
        }

    claims = len(result.get("successful_claims", []))
    errors = len(result.get("failed_sources", []))
    print(f"  → {claims} successful claim(s), {errors} failed source(s)")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SUBAGENT B — SYNTHESIS
#
# Fresh context. Receives Subagent A's structured output — never the verbose
# discovery process. Demonstrates summary injection (5.4): Phase 1 findings
# injected as structured context before Phase 2 begins.
#
# Demonstrates:
#   - Case facts at TOP of system prompt (5.1)
#   - Summary injection from Phase 1 (5.4)
#   - Conflict annotation: both values preserved, neither discarded (5.6)
#   - Coverage annotation for timed-out source (5.3 + 5.6)
#   - Content-appropriate rendering: table for figures (5.6)
# ─────────────────────────────────────────────────────────────────────────────

def run_subagent_b(subagent_a_findings: dict) -> str:
    """
    Synthesis subagent: produces structured report from Subagent A's findings.
    Receives structured output only — never the verbose collection process.
    """
    print("\n── SUBAGENT B: Synthesis ───────────────────────────────────")

    # Summary injection (5.4): Phase 1 findings at top of Phase 2 prompt.
    # Subagent B builds on this — no re-discovery needed.
    findings_summary = json.dumps(subagent_a_findings, indent=2)

    system_prompt = f"""{case_facts_block()}
## PHASE 1 COLLECTION FINDINGS (from Subagent A — do not re-derive)
{findings_summary}

You are a research synthesis agent. Produce a structured markdown report
from the findings above.

SYNTHESIS RULES — all mandatory:

1. PRESERVE ATTRIBUTION
   Every claim in the report must carry its source_url, document_name,
   and publication_date. Never drop provenance during summarisation.

2. CONFLICT HANDLING
   If two sources report different values for the same metric and the same
   year: do NOT select one. Do NOT average them.
   Present BOTH values in a side-by-side table with full source attribution.
   Add a conflict note explaining the likely reason (e.g. methodology difference).
   The consumer decides which value to use — not you.

3. COVERAGE ANNOTATION
   For any source that failed, include an explicit "Coverage Gap" section.
   State: what data is missing, which source, and why it is unavailable.
   Do not silently omit the gap.

4. CONTENT-APPROPRIATE RENDERING
   - Numerical comparisons      → markdown table with source column
   - Conflicting sources        → table with both rows + conflict note below
   - Coverage gaps              → labelled "⚠ Coverage Gap" section
   - Narrative context          → brief prose only where needed

Structure your report with these sections:
  1. Key Findings
  2. Detailed Data (table)
  3. ⚠ Conflicts Identified (if any)
  4. ⚠ Coverage Gaps (if any)
  5. Source Index
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": "Produce the synthesis report."}],
    )

    report = response.content[0].text
    print(f"  → Report generated ({len(report)} chars)")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATOR
#
# Orchestrates the two-phase pipeline. Owns the outcome.
# Responsible for:
#   - Case facts injection across all prompts
#   - Receiving structured output from Subagent A (not verbose process)
#   - Verifying Subagent A output before passing downstream
#   - Injecting Phase 1 summary into Subagent B
#   - Quality checking the final report
# ─────────────────────────────────────────────────────────────────────────────

def coordinator():
    """
    Coordinator: orchestrates Subagent A → Subagent B.

    Key pattern: coordinator receives structured outputs, never verbose
    discovery processes. Context stays clean. Attribution is preserved
    end-to-end from collection through synthesis.
    """
    print("═" * 62)
    print("COORDINATOR: Domain 5 Research Pipeline")
    print("═" * 62)
    print(f"\nCase Facts injected:\n{case_facts_block()}")

    # ── Phase 1: Collection ───────────────────────────────────────
    subagent_a_output = run_subagent_a()

    # Coordinator verifies Phase 1 output before passing downstream.
    # This is the coordinator's accountability — it owns the outcome.
    print("\n── COORDINATOR: Phase 1 Verification ──────────────────────")
    claims = subagent_a_output.get("successful_claims", [])
    errors = subagent_a_output.get("failed_sources", [])
    print(f"  Claims received:      {len(claims)}")
    print(f"  Failed sources:       {len(errors)}")

    for err in errors:
        print(
            f"  ↳ {err.get('source_name', 'unknown')} | "
            f"type={err.get('failure_type')} | "
            f"alternatives={len(err.get('potential_alternatives', []))}"
        )

    if len(claims) == 0:
        print("  ✗ No successful claims — pipeline cannot continue.")
        return None

    # Check for potential conflicts (coordinator-level, before synthesis)
    metrics = [c.get("metric") for c in claims]
    years = [c.get("year") for c in claims]
    if len(set(metrics)) < len(metrics):
        print("  ⚑ Duplicate metric detected — conflict likely. Subagent B will annotate.")

    # ── Phase 2: Synthesis ────────────────────────────────────────
    final_report = run_subagent_b(subagent_a_output)

    # ── Final output ──────────────────────────────────────────────
    print("\n" + "═" * 62)
    print("FINAL SYNTHESIS REPORT")
    print("═" * 62)
    print(final_report)

    # ── Quality check ─────────────────────────────────────────────
    # Verify the report contains what Domain 5 requires.
    report_lower = final_report.lower()
    print("\n── COORDINATOR: Quality Check ──────────────────────────────")
    checks = {
        "Attribution preserved (source names present)": any(
            kw in report_lower for kw in ["iea", "irena", "source_url", "document_name"]
        ),
        "Conflict annotated (both values present)": (
            "34" in final_report and "28" in final_report
        ),
        "Conflict flagged (not silently resolved)": any(
            kw in report_lower for kw in ["conflict", "differ", "discrepan", "methodolog"]
        ),
        "Coverage gap noted (Bloomberg absence surfaced)": any(
            kw in report_lower for kw in ["bloomberg", "unavailable", "timeout", "gap", "coverage"]
        ),
        "Table rendered (numerical comparison)": "|" in final_report,
    }
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗ FAILED"
        if not passed:
            all_passed = False
        print(f"  {status}  {check}")

    print()
    if all_passed:
        print("  ✓ All Domain 5 requirements met.")
    else:
        print("  ✗ One or more requirements not met — review synthesis rules.")

    return final_report


if __name__ == "__main__":
    coordinator()
