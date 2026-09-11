"""Isolated, cancellable Fireworks transport. Credentials travel only over stdin."""

import json
import sys

import httpx

from ai_career_navigator.models.providers.fireworks import FIREWORKS_CHAT_COMPLETIONS_URL


def collect_stream(lines, model):
    content = []
    usage = {}
    finish = None
    response_id = None
    done = False
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            done = True
            break
        packet = json.loads(data)
        if "error" in packet:
            raise ValueError("in-stream error")
        response_id = packet.get("id", response_id)
        model = packet.get("model", model)
        values = packet.get("usage") or {}
        # Keep token counts only; never copy provider reasoning fields.
        for key in ("prompt_tokens", "completion_tokens"):
            if values.get(key) is not None:
                usage[key] = values[key]
        for choice in packet.get("choices", []):
            content.append(choice.get("delta", {}).get("content") or "")
            finish = choice.get("finish_reason") or finish
    if not done or finish not in {"stop", "length"}:
        raise ValueError("incomplete stream")
    final = "".join(content)
    if "</think>" in final:
        final = final.rsplit("</think>", 1)[-1].strip()
    elif "<think>" in final:
        raise ValueError("no final answer")
    return {
        "id": response_id,
        "model": model,
        "usage": usage,
        "choices": [{"message": {"content": final}, "finish_reason": finish}],
    }


def main():
    try:
        parameters = json.load(sys.stdin)
        with httpx.Client(timeout=parameters["timeout"]) as client:
            with client.stream(
                "POST",
                FIREWORKS_CHAT_COMPLETIONS_URL,
                headers={"Authorization": "Bearer " + parameters["api_key"]},
                json=parameters["payload"],
            ) as response:
                if response.is_error:
                    result = {"error_status": response.status_code}
                else:
                    result = collect_stream(response.iter_lines(), parameters["payload"]["model"])
    except httpx.TimeoutException:
        result = {"worker_error": "timeout"}
    except httpx.RequestError:
        result = {"worker_error": "transport"}
    except Exception:
        result = {"worker_error": "invalid_stream"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
