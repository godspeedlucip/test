from integrations import resolve_prompt_config, run_llm_task

from graph.nodes.common import run_node


def revise_node(state: dict):
    def _impl(s: dict):
        draft = s.get("answer", "")
        if not draft:
            raise RuntimeError("revise_node requires an answer draft")

        last_judge = (s.get("judge_results") or [{}])[-1]
        suggestions = last_judge.get("improvement_suggestions", [])
        unsupported = last_judge.get("unsupported_claims", [])
        hallucinated = last_judge.get("hallucinated_claims", [])

        feedback_lines = []
        if suggestions:
            feedback_lines.extend(suggestions)
        if unsupported:
            feedback_lines.extend([f"Unsupported: {x}" for x in unsupported])
        if hallucinated:
            feedback_lines.extend([f"Hallucinated: {x}" for x in hallucinated])
        if not feedback_lines:
            feedback_lines.append("Strengthen grounding and citation consistency.")
        if s.get("human_review_note"):
            feedback_lines.append(f"Human review note: {s['human_review_note']}")

        prompt_cfg = resolve_prompt_config(None, default_name="related_work")
        llm_result = run_llm_task(
            task_type="revise_related_work",
            prompt_name=prompt_cfg.prompt_name,
            prompt_version=prompt_cfg.prompt_version,
            body=(
                "Revise the related work draft using the feedback.\n"
                f"Feedback:\n- " + "\n- ".join(feedback_lines) + "\n\n"
                f"Original Draft:\n{draft}\n\n"
                "Output only the revised draft."
            ),
            requested_model=s.get("model"),
        )
        revised = llm_result.response.text.strip()
        if revised == draft:
            revised = f"{draft}\n\nRevision Notes:\n- " + "\n- ".join(feedback_lines[:3])

        revise_count = int(s.get("revise_count", 0)) + 1
        related_work = dict(s.get("related_work", {}))
        if related_work:
            related_work["related_work_text"] = revised

        llm_meta = {
            "model_name": llm_result.response.model_name,
            "prompt_name": llm_result.loaded_prompt.prompt_name,
            "prompt_version": llm_result.loaded_prompt.prompt_version,
            "token_usage": llm_result.response.token_usage,
            "latency_ms": llm_result.latency_ms,
        }
        return {
            "answer": revised,
            "related_work": related_work or s.get("related_work"),
            "revise_count": revise_count,
            "llm_meta": llm_meta,
            "artifacts": s.get("artifacts", [])
            + [
                {
                    "type": "revision",
                    "payload": {"revise_count": revise_count, "feedback_count": len(feedback_lines), **llm_meta},
                }
            ],
        }

    return run_node("revise_node", state, _impl)
