"""对话逐字流式输出与 tool-call 泄漏守卫。

此前最终回答是把所有 chunk 攒完再一次性 yield，客户端每轮只收到一个 token 事件；
现在改为按「安全前缀」增量下发，同时保留原有的泄漏检测语义。
"""

from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.agents.chat_agent as chat_agent  # noqa: E402
from app.models.chat_schemas import ChatContext, ChatMessage  # noqa: E402


class FakeChunk:
    """模拟 langchain 的 AIMessageChunk：支持 + 累加。"""

    def __init__(self, content: str = "", tool_call_chunks=None, tool_calls=None):
        self.content = content
        self.tool_call_chunks = list(tool_call_chunks or [])
        self.tool_calls = list(tool_calls or [])
        self.id = "fake-chunk"

    def __add__(self, other: "FakeChunk") -> "FakeChunk":
        return FakeChunk(
            content=self.content + other.content,
            tool_call_chunks=self.tool_call_chunks + other.tool_call_chunks,
            tool_calls=self.tool_calls + other.tool_calls,
        )


class FakeBoundLLM:
    def __init__(self, chunks, on_invoke=None):
        self._chunks = chunks
        self._on_invoke = on_invoke

    def stream(self, messages):
        return iter(self._chunks)

    def invoke(self, messages):
        if self._on_invoke is None:
            raise AssertionError("不应回退到 invoke")
        return self._on_invoke(messages)


class FakeLLM:
    def __init__(self, chunks, on_invoke=None):
        self._chunks = chunks
        self._on_invoke = on_invoke

    def bind_tools(self, tool_defs):
        return FakeBoundLLM(self._chunks, self._on_invoke)

    def stream(self, messages):
        return iter(self._chunks)


def collect_text(events) -> str:
    return "".join(event["text"] for event in events if event.get("type") == "token")


# --- _safe_prefix_length ---------------------------------------------------


def test_safe_prefix_length_passes_plain_text() -> None:
    text = "大理适合慢节奏游玩。"
    assert chat_agent._safe_prefix_length(text) == len(text)


def test_safe_prefix_length_holds_back_partial_marker() -> None:
    """标记被切在两个 chunk 之间时，尾部要留在缓冲区。"""
    assert chat_agent._safe_prefix_length("正文<tool") == len("正文")
    assert chat_agent._safe_prefix_length("正文<") == len("正文")
    assert chat_agent._safe_prefix_length("正文<FUNCTION=") == len("正文")


# --- _emit_stream ----------------------------------------------------------


def test_emit_stream_yields_incrementally() -> None:
    """每个 chunk 都应该单独下发，而不是攒到最后一次性发出。"""
    state = chat_agent._StreamState()
    chunks = [FakeChunk("大理"), FakeChunk("适合"), FakeChunk("慢游。")]

    events = list(chat_agent._emit_stream(iter(chunks), state, stop_on_tool_calls=False))

    assert len(events) == 3
    assert collect_text(events) == "大理适合慢游。"
    assert state.emitted_any is True
    assert state.suppressed is False
    assert state.text == "大理适合慢游。"


def test_emit_stream_suppresses_split_leak_marker() -> None:
    """跨 chunk 拼出的泄漏标记不能漏到客户端。"""
    state = chat_agent._StreamState()
    chunks = [FakeChunk("好的"), FakeChunk("<tool"), FakeChunk("_call>{}")]

    events = list(chat_agent._emit_stream(iter(chunks), state, stop_on_tool_calls=False))

    assert collect_text(events) == "好的"
    assert state.suppressed is True


def test_emit_stream_stops_when_tool_calls_appear() -> None:
    """出现工具调用后立即停止直出文本，交回工具循环。"""
    state = chat_agent._StreamState()
    chunks = [
        FakeChunk("我先查一下"),
        FakeChunk("", tool_call_chunks=[{"name": "get_weather_forecast"}]),
        FakeChunk("这段不该出现"),
    ]

    events = list(chat_agent._emit_stream(iter(chunks), state, stop_on_tool_calls=True))

    assert collect_text(events) == "我先查一下"
    assert state.suppressed is True


def test_emit_stream_skips_leading_whitespace() -> None:
    """开头的纯空白不单独成帧。"""
    state = chat_agent._StreamState()
    chunks = [FakeChunk("\n\n"), FakeChunk("正文")]

    events = list(chat_agent._emit_stream(iter(chunks), state, stop_on_tool_calls=False))

    assert [event["text"] for event in events] == ["正文"]


def test_emit_stream_flushes_guarded_tail() -> None:
    """流结束时，被守卫扣住的尾部要补发出去。"""
    state = chat_agent._StreamState()
    chunks = [FakeChunk("结论是"), FakeChunk("<")]

    events = list(chat_agent._emit_stream(iter(chunks), state, stop_on_tool_calls=False))

    assert collect_text(events) == "结论是<"
    assert state.suppressed is False


# --- _stream_final_answer --------------------------------------------------


def test_stream_final_answer_streams_incrementally() -> None:
    llm = FakeLLM([FakeChunk("洱海"), FakeChunk("很美")])

    events = list(
        chat_agent._stream_final_answer(llm, [], used_tools=False, tool_summaries=[])
    )

    assert [event["text"] for event in events] == ["洱海", "很美"]


def test_stream_final_answer_falls_back_when_fully_leaked() -> None:
    """整段都是泄漏内容时，行为与改动前一致：完全替换成兜底摘要。"""
    llm = FakeLLM([FakeChunk("<tool_call>{}</tool_call>")])

    events = list(
        chat_agent._stream_final_answer(
            llm, [], used_tools=True, tool_summaries=["大理未来三天以晴为主"]
        )
    )
    text = collect_text(events)

    assert "<tool_call" not in text
    assert "大理未来三天以晴为主" in text


def test_stream_final_answer_appends_fallback_after_clean_prefix() -> None:
    """已下发的干净前缀无法撤回，兜底内容追加在其后而不是整段替换。"""
    llm = FakeLLM([FakeChunk("先说结论："), FakeChunk("<tool_call>leak")])

    events = list(
        chat_agent._stream_final_answer(
            llm, [], used_tools=True, tool_summaries=["大理未来三天以晴为主"]
        )
    )
    text = collect_text(events)

    assert text.startswith("先说结论：")
    assert "<tool_call" not in text
    assert "大理未来三天以晴为主" in text


def test_stream_final_answer_falls_back_on_empty_stream() -> None:
    llm = FakeLLM([FakeChunk("   ")])

    events = list(
        chat_agent._stream_final_answer(
            llm, [], used_tools=True, tool_summaries=["大理未来三天以晴为主"]
        )
    )

    assert "大理未来三天以晴为主" in collect_text(events)


# --- iter_assistant_events -------------------------------------------------


def test_first_round_without_tools_streams_token_by_token(monkeypatch) -> None:
    """不需要工具的对话（占多数）在第一轮就应该逐字下发。"""
    chunks = [FakeChunk("大理"), FakeChunk("三天"), FakeChunk("足够了。")]
    monkeypatch.setattr(
        chat_agent, "_build_chat_llm", lambda *, streaming: FakeLLM(chunks)
    )

    events = list(
        chat_agent.iter_assistant_events(
            [ChatMessage(role="user", content="大理玩几天合适")],
            ChatContext(),
        )
    )
    token_events = [event for event in events if event["type"] == "token"]

    assert len(token_events) == 3, "应该逐 chunk 下发，而不是一次性发出整段"
    assert collect_text(events) == "大理三天足够了。"


def test_tool_round_then_streamed_final_answer(monkeypatch) -> None:
    """有工具调用时：本轮文本不直出，工具执行后最终回答仍逐字下发。"""
    rounds = [
        # 第一轮：模型边说话边发起工具调用
        [
            FakeChunk("我先查一下天气"),
            FakeChunk(
                "",
                tool_call_chunks=[{"name": "get_weather_forecast"}],
                tool_calls=[
                    {"id": "call_1", "name": "get_weather_forecast", "args": {"city": "大理"}}
                ],
            ),
        ],
        # 第二轮：没有工具调用，直接给最终回答
        [FakeChunk("大理"), FakeChunk("未来三天以晴为主。")],
    ]

    class QueuedLLM:
        def bind_tools(self, tool_defs):
            return self

        def stream(self, messages):
            return iter(rounds.pop(0) if rounds else [])

        def invoke(self, messages):
            raise AssertionError("不应回退到 invoke")

    class FakeToolResult:
        name = "get_weather_forecast"
        ok = True
        summary = "大理未来三天以晴为主"
        error = None

        def to_llm_content(self):
            return '{"ok": true, "tool": "get_weather_forecast"}'

    monkeypatch.setattr(chat_agent, "_build_chat_llm", lambda *, streaming: QueuedLLM())
    monkeypatch.setattr(chat_agent, "execute_tool", lambda name, args: FakeToolResult())

    events = list(
        chat_agent.iter_assistant_events(
            [ChatMessage(role="user", content="大理这几天天气怎么样")],
            ChatContext(),
        )
    )
    types = [event["type"] for event in events]

    assert "tool_start" in types
    assert "tool_result" in types
    # 第一轮的"我先查一下天气"允许作为前言下发，但最终回答必须是逐字的
    final_tokens = [
        event["text"] for event in events if event["type"] == "token"
    ]
    assert "大理" in final_tokens and "未来三天以晴为主。" in final_tokens
    assert types.index("tool_result") < types.index("token", types.index("tool_result"))


def test_streaming_failure_falls_back_to_invoke(monkeypatch) -> None:
    """供应商不支持流式且尚未下发内容时，退回一次性调用而不是报错。"""

    class ExplodingBound(FakeBoundLLM):
        def stream(self, messages):
            raise RuntimeError("provider does not support streaming")

    class ExplodingLLM(FakeLLM):
        def bind_tools(self, tool_defs):
            return ExplodingBound(
                [], on_invoke=lambda messages: FakeChunk("退回一次性调用的回答。")
            )

    monkeypatch.setattr(
        chat_agent, "_build_chat_llm", lambda *, streaming: ExplodingLLM([])
    )

    events = list(
        chat_agent.iter_assistant_events(
            [ChatMessage(role="user", content="大理玩几天合适")],
            ChatContext(),
        )
    )

    assert collect_text(events) == "退回一次性调用的回答。"
