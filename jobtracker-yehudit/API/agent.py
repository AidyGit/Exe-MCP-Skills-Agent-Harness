"""Job-search agent on the raw Messages API: wires the harness parts together."""
from harness import compaction, context, loop, tokens
from harness.history import History
from harness.trace import log

MODEL = "claude-opus-5-5"
EFFORT = "medium"
COMPACT_THRESHOLD = 20_000  # input tokens


class Agent:
    def __init__(self, client, ws, session_id=None, resume=False, model=MODEL, effort=EFFORT,
                 compact_threshold=COMPACT_THRESHOLD, fetcher=None):
        self.client, self.ws, self.model, self.fetcher = client, ws, model, fetcher
        self.compact_threshold = compact_threshold
        self.create_kwargs = {"extra_body": {"output_config": {"effort": effort}}}
        self.history = History(ws, session_id)
        self.messages = self.history.load() if resume else []
        log("agent.py", f"session {self.history.session_id} model={model} effort={effort} resume={resume}")

    def turn(self, user_text):
        meter = tokens.TurnMeter()
        msg = {"role": "user", "content": context.enrich(self.ws, user_text)}
        self.messages.append(msg)
        self.history.append(msg)
        text, used, last_input = loop.run(self.client, self.model, context.system_text(), self.messages,
                                          self.history, meter, self.ws, self.create_kwargs, self.fetcher)
        if compaction.needs_compaction(last_input, self.compact_threshold):
            self.messages = compaction.compact(self.client, self.model, context.system_text(),
                                               self.messages, meter, self.create_kwargs)
            self.history.append({"type": "compaction", "messages": self.messages})
        return {"reply": text, **meter.report(used)}
