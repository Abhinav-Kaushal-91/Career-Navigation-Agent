"""One authorized HF inference request; saved public posting, no candidate data."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from compare_saved_extractions import SAVED_RUN, PostingCandidateAssessment, replay
from huggingface_hub import InferenceClient

from ai_career_navigator.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    saved = json.loads(SAVED_RUN.read_text(encoding="utf-8"))
    original = next(e["payload"] for e in saved["model_events"] if e["event"] == "request")
    original_messages = original["messages"]
    assert [m["role"] for m in original_messages] == ["system", "system", "user"]
    messages = [
        {"role": "system", "content": "\n\n".join(
            m["content"] for m in original_messages if m["role"] == "system")},
        original_messages[-1],
    ]
    request = {
        "model": "Qwen/Qwen3.8-27B",
        "messages": messages,
        "temperature": original["temperature"],
        "max_tokens": original["max_tokens"],
        "stream": False,
        "response_format": original["response_format"],
        "extra_body": {"chat_template_kwargs": original["chat_template_kwargs"]},
    }
    assert request["max_tokens"] == 20000
    assert all(m["content"] in messages[0]["content"] for m in original_messages[:2])
    assert messages[-1] == original_messages[-1]
    if not args.live:
        print("Offline check passed: original contents, merged system messages, 20k; no call.")
        return
    settings = Settings(_env_file=root / "src/ai_career_navigator/.env")
    if settings.hf_token is None:
        raise SystemExit("HF_TOKEN is not configured; no call made.")
    output = root / "outputs/qwen-live-extraction" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    (output / "request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
    print(f"Starting one Qwen request; artifacts: {output}", flush=True)
    client = InferenceClient(api_key=settings.hf_token.get_secret_value(), timeout=600)
    started = perf_counter()
    try:
        response = client.chat_completion(**request)
    except Exception as exc:
        message = str(exc).replace(settings.hf_token.get_secret_value(), "[REDACTED]")
        message = re.sub(r"hf_[A-Za-z0-9]+", "[REDACTED]", message)
        failure = {"error_category": type(exc).__name__, "elapsed_seconds": perf_counter()-started,
                   "status_code": getattr(getattr(exc, "response", None), "status_code", None),
                   "sanitized_message": message[:2000],
                   "application_retries": 0}
        (output / "failure.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print(json.dumps(failure), flush=True)
        raise SystemExit(1) from None
    elapsed = perf_counter() - started
    choice = response.choices[0]
    content = choice.message.content or ""
    # Persist final answer only, never provider reasoning fields or embedded traces.
    embedded_reasoning_removed = "<think>" in content or "</think>" in content
    if "</think>" in content:
        content = content.rsplit("</think>", 1)[1].strip()
    elif "<think>" in content:
        content = ""
    (output / "response.txt").write_text(content, encoding="utf-8")
    usage = response.usage
    metrics = {
        "model_requested": request["model"], "model_returned": response.model,
        "routing": "HF default automatic provider selection",
        "transport_adjustment": "Two original system messages joined with two newlines",
        "elapsed_seconds": round(elapsed, 3), "finish_reason": choice.finish_reason,
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "thinking_requested": False, "thinking_honored": "not independently verified",
        "embedded_reasoning_removed": embedded_reasoning_removed,
        "application_retries": 0,
        "messages_sha256": hashlib.sha256(json.dumps(request["messages"]).encode()).hexdigest(),
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    assessment = PostingCandidateAssessment.model_validate(saved["postings"][0]["assessment"])
    result = replay("qwen_live_original", content, assessment, datetime.now(UTC))
    (output / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"metrics": metrics, "quality": result["quality"],
                      "accepted_counts": result["accepted_counts"],
                      "decisions": result["decision_counts"]}), flush=True)


if __name__ == "__main__":
    main()
