"""Reasoning and tracing infrastructure for the CDU Pump Health Agent.

Captures tool calls, reasoning steps, and evidence chains for visualization
and groundedness evaluation.
"""

import json
import time
from dataclasses import dataclass, field


@dataclass
class ToolTrace:
    tool_name: str
    input_params: dict
    output_summary: str
    source_citations: list
    duration_ms: float
    timestamp: float


@dataclass
class ReasoningStep:
    step_number: int
    description: str
    tool_traces: list[ToolTrace] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class InvocationTrace:
    """Full trace of a single agent invocation."""
    query: str
    steps: list[ReasoningStep] = field(default_factory=list)
    total_tool_calls: int = 0
    total_duration_ms: float = 0.0
    citations: list[dict] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    response_text: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_tool_calls": self.total_tool_calls,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "steps": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "tools": [
                        {
                            "name": t.tool_name,
                            "input": t.input_params,
                            "output_summary": t.output_summary[:200],
                            "sources": t.source_citations,
                            "duration_ms": round(t.duration_ms, 1),
                        }
                        for t in s.tool_traces
                    ],
                    "evidence": s.evidence,
                }
                for s in self.steps
            ],
            "citations": self.citations,
        }


class TraceCollector:
    """Collects traces during agent execution via Strands hooks."""

    def __init__(self):
        self.current_trace: InvocationTrace | None = None
        self._current_step: ReasoningStep | None = None
        self._step_counter = 0
        self._tool_start_times: dict[str, float] = {}

    def start_invocation(self, query: str):
        self._step_counter = 0
        self.current_trace = InvocationTrace(
            query=query,
            start_time=time.time(),
        )
        self._start_step("Analyzing query and planning tool calls")

    def _start_step(self, description: str):
        self._step_counter += 1
        self._current_step = ReasoningStep(
            step_number=self._step_counter,
            description=description,
            timestamp=time.time(),
        )
        self.current_trace.steps.append(self._current_step)

    def record_tool_call(self, tool_name: str, tool_input: dict, tool_output, duration_ms: float):
        if self.current_trace is None:
            return

        self.current_trace.total_tool_calls += 1

        citations = []
        output_summary = ""
        if isinstance(tool_output, dict):
            output_summary = json.dumps({k: v for k, v in tool_output.items()
                                          if k in ("status", "pump_id", "overall_zone", "top_diagnosis",
                                                    "top_confidence", "total_count", "total_readings")},
                                         default=str)[:300]
            if "source" in tool_output:
                citations.append(tool_output["source"])
            if "sources" in tool_output:
                citations.extend(tool_output["sources"] if isinstance(tool_output["sources"], list) else [tool_output["sources"]])
        elif isinstance(tool_output, str):
            output_summary = tool_output[:200]

        trace = ToolTrace(
            tool_name=tool_name,
            input_params=tool_input,
            output_summary=output_summary,
            source_citations=citations,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )

        if self._current_step:
            self._current_step.tool_traces.append(trace)
            for c in citations:
                self._current_step.evidence.append(c)

        self.current_trace.citations.extend(citations)

    def advance_step(self, description: str):
        if self.current_trace:
            self._start_step(description)

    def finish_invocation(self, response_text: str = ""):
        if self.current_trace:
            self.current_trace.end_time = time.time()
            self.current_trace.total_duration_ms = (
                self.current_trace.end_time - self.current_trace.start_time
            ) * 1000
            self.current_trace.response_text = response_text

    def get_trace(self) -> dict | None:
        if self.current_trace:
            return self.current_trace.to_dict()
        return None
