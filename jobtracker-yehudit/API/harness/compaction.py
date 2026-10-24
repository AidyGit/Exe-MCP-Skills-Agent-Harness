"""Context-window management: past a token threshold, summarize the WHOLE conversation."""
from .trace import log

SUMMARY_REQUEST = ("Summarize the conversation so far for yourself: decisions, user criteria, "
                   "job ids and statuses, open questions. Be compact, no preamble.")


def needs_compaction(last_input_tokens, threshold):
    return last_input_tokens > threshold


def compact(client, model, system, messages, meter, create_kwargs):
    """Return the new, short message list (summary + ack)."""
    log("compaction.py", f"compacting {len(messages)} messages with {model}")
    resp = client.messages.create(
        model=model, max_tokens=800, system=system,
        messages=messages + [{"role": "user", "content": SUMMARY_REQUEST}], **create_kwargs)
    meter.record(resp.usage)
    summary = "".join(b.text for b in resp.content if b.type == "text")
    return [{"role": "user", "content": f"<summary of earlier conversation>\n{summary}\n</summary>"},
            {"role": "assistant", "content": [{"type": "text", "text": "Understood."}]}]
