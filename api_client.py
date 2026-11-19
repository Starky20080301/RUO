# -*- coding: utf-8 -*-
"""LLM API 客户端。

支持两种协议，均为 SSE 流式输出：
- OpenAI 兼容 (/chat/completions)：DeepSeek、Kimi、智谱GLM、通义千问、豆包、OpenAI 等
- Anthropic 原生 (/v1/messages)：Claude 系列

Agent 扩展点：将来要加函数调用（function calling），在 stream 中增加 tools 参数、
并在 ChatEngine 中处理 tool_calls 片段即可，见 main.py 的 ChatEngine 与 README。
"""

import json

import requests


class LLMError(Exception):
    """LLM 调用失败；message 为可直接展示给用户的中文描述。"""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _sse_payloads(resp):
    """解析 SSE 流，逐个产出 "data: " 之后的字符串。"""
    resp.encoding = "utf-8"
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw.strip()
        if line.startswith("data:"):
            yield line[len("data:"):].strip()


def _network_hint(exc):
    text = str(exc)
    if "ProxyError" in text:
        return "网络/代理错误，请检查系统代理是否可用。"
    if "SSLError" in text:
        return "SSL 证书错误，若使用代理请检查其 HTTPS 配置。"
    if "timed out" in text or "Timeout" in text or "timeout" in text:
        return "请求超时，请检查网络后重试。"
    if "ConnectionError" in text:
        return "无法连接到 API 服务器，请检查网络或 base_url。"
    return f"网络错误: {text[:200]}"


def _post_stream(url, headers, body, timeout):
    """发起流式 POST；网络层错误统一转为 LLMError，非 200 带上响应摘要。"""
    try:
        resp = requests.post(url, headers=headers, json=body, stream=True, timeout=(10, timeout))
    except requests.RequestException as exc:
        raise LLMError(_network_hint(exc)) from None
    if resp.status_code != 200:
        try:
            detail = (resp.text or "")[:300]
        except Exception:
            detail = ""
        hint = ""
        if resp.status_code == 401:
            hint = "（API Key 可能不正确或未生效）"
        elif resp.status_code == 404:
            hint = "（请检查 base_url 是否正确；OpenAI 兼容协议通常需要 /v1 结尾）"
        elif resp.status_code == 429:
            hint = "（调用过于频繁或额度不足）"
        raise LLMError(f"HTTP {resp.status_code}{hint}: {detail}", resp.status_code)
    return resp


class OpenAICompatClient:
    protocol = "openai"

    def __init__(self, base_url, api_key, model, timeout=180.0):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model or ""
        self.timeout = timeout

    def stream(self, system_prompt, history, temperature, max_tokens):
        if not self.base_url:
            raise LLMError("base_url 未配置，请在「设置」中填写。")
        if not self.api_key:
            raise LLMError("API Key 未配置，请右键桌宠 → 设置 填写。")
        url = self.base_url + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in history)
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = _post_stream(url, headers, body, self.timeout)
        with resp:
            for payload in _sse_payloads(resp):
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                if data.get("error"):
                    err = data["error"]
                    msg = err.get("message", "") if isinstance(err, dict) else str(err)
                    raise LLMError(f"API 返回错误: {msg or err}")
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")  # 推理型模型的 reasoning_content 等字段直接忽略
                if piece:
                    yield piece


class AnthropicClient:
    protocol = "anthropic"

    def __init__(self, base_url, api_key, model, timeout=180.0):
        base = (base_url or "https://api.anthropic.com").rstrip("/")
        # 兼容用户填到 /v1 或只填根地址两种写法
        self.url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
        self.api_key = (api_key or "").strip()
        self.model = model or ""
        self.timeout = timeout

    @staticmethod
    def _sanitize(history):
        """Anthropic 要求消息严格 user/assistant 交替：合并连续同角色，去掉开头的 assistant。"""
        merged = []
        for msg in history:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            content = msg.get("content") or ""
            if merged and merged[-1]["role"] == role:
                merged[-1]["content"] += "\n" + content
            else:
                merged.append({"role": role, "content": content})
        while merged and merged[0]["role"] != "user":
            merged.pop(0)
        return merged

    def stream(self, system_prompt, history, temperature, max_tokens):
        if not self.api_key:
            raise LLMError("API Key 未配置，请右键桌宠 → 设置 填写。")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": self._sanitize(history),
            "max_tokens": max(64, int(max_tokens)),  # Anthropic 必填
            "temperature": min(float(temperature), 1.0),  # Anthropic 只接受 0~1
            "stream": True,
        }
        if system_prompt:
            body["system"] = system_prompt
        resp = _post_stream(self.url, headers, body, self.timeout)
        with resp:
            for payload in _sse_payloads(resp):
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                kind = data.get("type")
                if kind == "content_block_delta":
                    delta = data.get("delta") or {}
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield delta["text"]
                elif kind == "message_stop":
                    break
                elif kind == "error":
                    err = data.get("error") or {}
                    raise LLMError(f"API 返回错误: {err.get('message') or err}")


def make_client(profile):
    """根据档案的 protocol 字段创建对应客户端。"""
    protocol = (profile or {}).get("protocol", "openai")
    cls = AnthropicClient if protocol == "anthropic" else OpenAICompatClient
    return cls(
        base_url=profile.get("base_url", ""),
        api_key=profile.get("api_key", ""),
        model=profile.get("model", ""),
    )
