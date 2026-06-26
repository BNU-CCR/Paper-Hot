"""通知推送模块"""

import os
import http.client
import urllib.parse
from typing import Optional
from pathlib import Path
import yaml

from .config import get_config


class NotificationSender:
    """通知发送器"""

    def __init__(self):
        config = get_config()
        self.config = config.notification_config

    def send_wechat(self, title: str, desp: str) -> bool:
        """
        通过 Server酱 发送微信通知

        Args:
            title: 通知标题
            desp: 通知内容

        Returns:
            bool: 是否发送成功
        """
        sckey = self.config.get("serverchan_sckey")
        if not sckey:
            print("Server酱 SCKEY 未配置")
            return False

        try:
            conn = http.client.HTTPSConnection("sctapi.ftqq.com")
            payload = urllib.parse.urlencode({
                "title": title,
                "desp": desp
            })
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            conn.request("POST", f"/{sckey}.send", payload, headers)
            response = conn.getresponse()
            result = response.read().decode()
            conn.close()

            if "success" in result.lower() or "0" in result:
                print(f"微信通知发送成功: {title}")
                return True
            else:
                print(f"微信通知发送失败: {result}")
                return False
        except Exception as e:
            print(f"微信通知发送异常: {e}")
            return False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        发送邮件通知（需要SMTP配置）

        目前仅打印日志，实际发送需要配置SMTP
        """
        print(f"[Email] To: {to}")
        print(f"[Email] Subject: {subject}")
        print(f"[Email] Body: {body[:200]}...")
        # TODO: 实现实际邮件发送
        return True

    def send_paper_notification(self, paper: dict) -> bool:
        """
        发送论文通知

        Args:
            paper: 论文信息字典，包含 title, journal, relevance, reason, summary, link
        """
        relevance = paper.get("relevance", "Unknown")
        title = paper.get("title", "无标题")

        # 只有 High/Medium 才发送通知
        if relevance not in ["High", "Medium"]:
            return False

        # 构建通知内容
        emoji = "🔥" if relevance == "High" else "📄"
        notify_title = f"{emoji} [{relevance}] 新论文"

        desp = f"""## {title}

- **期刊**: {paper.get('journal', '未知')}
- **相关性**: {relevance}
- **判断理由**: {paper.get('reason', '无')}
- **摘要**: {paper.get('summary', '无')[:200]}

**链接**: {paper.get('link', '无')}"""

        # 发送微信通知
        wechat_enabled = self.config.get("enable_wechat", False)
        if wechat_enabled:
            self.send_wechat(notify_title, desp)

        # 发送邮件通知
        email_enabled = self.config.get("enable_email", False)
        email_to = self.config.get("email_to")
        if email_enabled and email_to:
            self.send_email(email_to, notify_title, desp)

        return True

    def send_batch_notification(self, papers: list) -> int:
        """
        批量发送论文通知

        Returns:
            int: 成功发送的通知数量
        """
        if not papers:
            return 0
        if not self.config.get("enable_wechat", False):
            return 0

        success_count = 0
        high_papers = [p for p in papers if p.get("relevance") == "High"]
        medium_papers = [p for p in papers if p.get("relevance") == "Medium"]

        # 汇总通知
        if high_papers:
            titles = "\n".join([f"- {p.get('title', '')[:50]}" for p in high_papers[:5]])
            if len(high_papers) > 5:
                titles += f"\n- ... 还有 {len(high_papers) - 5} 篇"

            self.send_wechat(
                f"🔥 【High】发现 {len(high_papers)} 篇高相关论文",
                f"## 高相关论文 ({len(high_papers)} 篇)\n{titles}"
            )
            success_count += 1

        if medium_papers:
            titles = "\n".join([f"- {p.get('title', '')[:50]}" for p in medium_papers[:5]])
            if len(medium_papers) > 5:
                titles += f"\n- ... 还有 {len(medium_papers) - 5} 篇"

            self.send_wechat(
                f"📄 【Medium】发现 {len(medium_papers)} 篇中等相关论文",
                f"## 中等相关论文 ({len(medium_papers)} 篇)\n{titles}"
            )
            success_count += 1

        return success_count
