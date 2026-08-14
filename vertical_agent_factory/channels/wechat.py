"""WeChat Official Account plaintext callback adapter."""

import hashlib
import hmac
import os
import re
import time
import xml.etree.ElementTree as ElementTree
from xml.sax.saxutils import escape

from ..finance_data import DISCLAIMER


class WeChatChannelError(ValueError):
    pass


def verify_wechat_signature(token, signature, timestamp, nonce):
    if not token or not signature or not timestamp or not nonce:
        return False
    rendered = "".join(sorted([str(token), str(timestamp), str(nonce)]))
    expected = hashlib.sha1(rendered.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, str(signature))


def parse_wechat_message(raw):
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise WeChatChannelError("WeChat message body is empty")
    upper = bytes(raw).upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise WeChatChannelError("DTD and entity declarations are not allowed")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        raise WeChatChannelError("WeChat message XML is invalid")
    if root.tag != "xml":
        raise WeChatChannelError("WeChat message root must be xml")
    values = {}
    for child in list(root):
        if len(values) >= 40:
            raise WeChatChannelError("WeChat message contains too many fields")
        values[child.tag] = child.text or ""
    for required in ("ToUserName", "FromUserName", "CreateTime", "MsgType"):
        if not values.get(required):
            raise WeChatChannelError("WeChat message is missing {}".format(required))
    return values


def route_finance_text(content):
    content = str(content or "").strip()
    if not content:
        return None
    lowered = content.lower()
    if lowered in ("帮助", "help", "?", "菜单"):
        return None
    if content.startswith("宏观"):
        region = "global"
        if "中国" in content or "国内" in content:
            region = "china"
        elif "美国" in content or "美联储" in content:
            region = "us"
        return {"domain": "finance", "task": "finance.macro.analyze", "input": {"region": region}}
    a_share = re.search(r"(?:A股|a股)\s*[:：]?\s*([0-9]{6}(?:\.(?:SH|SZ|BJ))?)", content, re.IGNORECASE)
    if a_share:
        return {"domain": "finance", "task": "finance.a_share.analyze", "input": {"symbol": a_share.group(1)}}
    us_stock = re.search(r"美股\s*[:：]?\s*([A-Za-z][A-Za-z0-9.\-]{0,11})", content)
    if us_stock:
        return {"domain": "finance", "task": "finance.us_stock.analyze", "input": {"symbol": us_stock.group(1).upper()}}
    return None


def help_text():
    return (
        "金融分析助手使用方法：\n"
        "1. 宏观 全球 / 宏观 中国 / 宏观 美国\n"
        "2. A股 600000\n"
        "3. 美股 AAPL\n\n"
        "系统仅分析有日期和来源的数据，不提供买卖指令。\n{}".format(DISCLAIMER)
    )


def format_finance_reply(result):
    result = result or {}
    lines = [result.get("summary") or "暂时无法生成分析。"]
    facts = result.get("facts") or []
    if facts:
        lines.append("\n数据要点：")
        lines.extend("• {}".format(item) for item in facts[:3])
    uncertainties = result.get("uncertainties") or []
    if uncertainties:
        lines.append("\n不确定性：{}".format(uncertainties[0]))
    if DISCLAIMER not in "\n".join(lines):
        lines.append("\n{}".format(DISCLAIMER))
    return "\n".join(lines)[:600]


def text_reply_xml(message, content, now=None):
    timestamp = int(now if now is not None else time.time())
    return (
        "<xml>"
        "<ToUserName>{}</ToUserName>"
        "<FromUserName>{}</FromUserName>"
        "<CreateTime>{}</CreateTime>"
        "<MsgType>text</MsgType>"
        "<Content>{}</Content>"
        "</xml>"
    ).format(
        escape(message.get("FromUserName", "")),
        escape(message.get("ToUserName", "")),
        timestamp,
        escape(content),
    )


class WeChatOfficialAccountChannel(object):
    def __init__(self, commercial_service, token=None, tenant_id=None):
        self.service = commercial_service
        self.token = token or os.environ.get("WECHAT_OFFICIAL_ACCOUNT_TOKEN", "")
        self.tenant_id = tenant_id or os.environ.get("VAF_WECHAT_TENANT_ID", "")

    def verify(self, signature, timestamp, nonce):
        return verify_wechat_signature(self.token, signature, timestamp, nonce)

    def handle(self, raw):
        message = parse_wechat_message(raw)
        if message.get("MsgType") == "event" and message.get("Event", "").lower() == "subscribe":
            return text_reply_xml(message, "欢迎使用。\n" + help_text())
        if message.get("MsgType") != "text":
            return text_reply_xml(message, "目前仅支持文本指令。\n" + help_text())
        routed = route_finance_text(message.get("Content"))
        if routed is None:
            return text_reply_xml(message, help_text())
        routed["provider"] = "local"
        routed["input"]["_data_mode"] = os.environ.get("VAF_WECHAT_FINANCE_DATA_MODE", "fixture")
        tenant = self.service.tenant(self.tenant_id or None)
        message_id = message.get("MsgId") or "{}:{}".format(message.get("FromUserName"), message.get("CreateTime"))
        try:
            response = self.service.run(tenant, routed, idempotency_key="wechat:{}".format(message_id)[:128])
            content = format_finance_reply(response.get("result"))
        except Exception:
            content = "分析服务暂时不可用，请稍后重试。\n{}".format(DISCLAIMER)
        return text_reply_xml(message, content)
