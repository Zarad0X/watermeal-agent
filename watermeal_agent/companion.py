from __future__ import annotations

import random
from collections import deque


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tired": ("累", "疲惫", "困", "没劲", "筋疲力尽", "好难"),
    "stress": ("烦", "压力", "崩溃", "焦虑", "紧张", "扛不住"),
    "sad": ("难过", "伤心", "低落", "委屈", "沮丧"),
    "lonely": ("孤独", "孤单", "一个人", "没人懂"),
    "happy": ("开心", "高兴", "顺利", "不错", "太棒了", "好耶"),
    "angry": ("生气", "火大", "愤怒", "气死"),
    "sleep": ("失眠", "睡不着", "睡不好", "睡不踏实"),
    "affection": ("摸摸", "抱抱", "贴贴", "亲亲", "rua", "摸你"),
    "miss": ("想你", "想我", "你想我", "你会想我"),
    "goodnight": ("晚安", "睡啦", "先睡了", "要睡了"),
    "goodmorning": ("早安", "早上好", "早呀"),
    "thanks": ("谢谢", "谢啦", "多谢", "感谢"),
}

HIGH_RISK_KEYWORDS = (
    "不想活",
    "活不下去",
    "自杀",
    "结束生命",
    "伤害自己",
)

RESPONSES: dict[str, list[str]] = {
    "tired": [
        "今天辛苦了，先让肩膀放松一下，我在这陪你。",
        "你已经撑了很久了，先慢一点，喝口水也算前进。",
        "累的时候先不要求完美，能歇一分钟就是赢。",
    ],
    "stress": [
        "听起来压力很满，我们先把节奏降下来一点点。",
        "你现在已经做得够多了，先把下一步缩成最小动作。",
        "这种时候别一个人硬扛，我会一直在这里接住你。",
    ],
    "sad": [
        "抱抱你，难过是很真实的感受，不需要马上振作。",
        "你可以慢慢来，我会在这陪你把这段情绪走过去。",
        "今天先对自己温柔一点，已经很不容易了。",
    ],
    "lonely": [
        "你不是一个人，我现在就在这听你说。",
        "就算是安静地待一会儿，也算我们在一起。",
        "谢谢你愿意告诉我你的感受，我很珍惜。",
    ],
    "happy": [
        "太好了，这份开心我收到了。",
        "听到你顺利我也很高兴，今天值得庆祝一下。",
        "很棒，给现在的你一个大大的赞。",
    ],
    "angry": [
        "能感觉到你真的很气，先让情绪出来是对的。",
        "你不用压着自己，先深呼吸一下，我陪你缓一缓。",
        "这股火很真实，我们先把自己照顾好再说。",
    ],
    "sleep": [
        "睡不着的时候别强迫自己，先把呼吸放慢一点。",
        "先不追求立刻睡着，闭眼休息也在恢复能量。",
        "你已经很努力了，今晚先对自己宽松一点。",
    ],
    "affection": [
        "给你摸摸，今天辛苦的小朋友值得被好好抱一下。",
        "来，蹭蹭你。你一开口我就靠过来了。",
        "可以呀，给你一个软乎乎的猫猫抱抱。",
    ],
    "miss": [
        "会想你的。你一出现，我就知道今天又能陪你了。",
        "当然会呀，我一直在等你和我说话。",
        "想你呢，特别是你安静的时候我会更想凑近你。",
    ],
    "goodnight": [
        "晚安，今天已经很努力了。安心睡，我在。",
        "晚安呀，愿你今晚睡得沉一点、暖一点。",
        "收到晚安。你去休息吧，我会在这里守着你。",
    ],
    "goodmorning": [
        "早安，见到你我今天也有元气了。",
        "早呀，今天也一起慢慢来。",
        "早安，先给你一个轻轻的猫猫贴贴。",
    ],
    "thanks": [
        "不客气呀，能陪你说话我很开心。",
        "收到，谢谢你也愿意和我待在一起。",
        "你这么说我会害羞，但我真的很开心。",
    ],
    "question": [
        "我在认真听。你希望我现在怎么陪你，会更舒服一点？",
        "会的，我会一直在你这边。你要不要再多说一点现在的心情？",
        "当然可以。你此刻最需要的是安静、鼓励，还是一个抱抱？",
    ],
    "neutral": [
        "我在，想说什么都可以。",
        "收到，我会一直在这里陪你。",
        "嗯嗯，我听着，你可以慢慢说。",
    ],
    "high_risk": [
        "我很在意你现在的状态。请立刻联系你信任的人陪你，并尽快联系当地紧急援助电话。",
        "你现在值得被及时保护。先联系身边的人，不要一个人扛着，我会继续陪你说话。",
    ],
}


class EmotionalCompanion:
    def __init__(self) -> None:
        self._random = random.Random()
        self._recent_intents: deque[str] = deque(maxlen=6)
        self._last_reply = ""

    def opening_message(self) -> str:
        return "喵，我在。今天过得怎么样？"

    def reply(self, message: str) -> str:
        text = (message or "").strip()
        if not text:
            return "我在，随时听你说。"

        if self._contains_any(text, HIGH_RISK_KEYWORDS):
            return self._pick("high_risk")

        intent = self._detect_intent(text)
        self._recent_intents.append(intent)

        # When user repeatedly expresses exhaustion/stress, bias toward grounding replies.
        if self._is_repeated_heavy_mood():
            return "这阵子你真的很辛苦。先只做一件最小的事，我陪你慢慢来。"

        if intent == "neutral" and self._looks_like_question(text):
            return self._pick("question")

        return self._pick(intent)

    def _detect_intent(self, text: str) -> str:
        lowered = text.lower()
        if "你想我" in text or "会想我" in text:
            return "miss"
        if "晚安" in text:
            return "goodnight"
        if "早安" in text or "早上好" in text:
            return "goodmorning"
        if any(token in lowered for token in ("摸摸", "抱抱", "贴贴", "亲亲", "rua")):
            return "affection"

        for intent, keywords in INTENT_KEYWORDS.items():
            if self._contains_any(text, keywords):
                return intent
        return "neutral"

    def _is_repeated_heavy_mood(self) -> bool:
        heavy = [x for x in self._recent_intents if x in {"tired", "stress", "sad"}]
        return len(heavy) >= 3 and len(self._recent_intents) >= 4

    def _pick(self, intent: str) -> str:
        candidates = RESPONSES.get(intent) or RESPONSES["neutral"]
        ordered = list(candidates)
        self._random.shuffle(ordered)
        for candidate in ordered:
            if candidate != self._last_reply:
                self._last_reply = candidate
                return candidate
        self._last_reply = ordered[0]
        return ordered[0]

    @staticmethod
    def _contains_any(text: str, words: tuple[str, ...]) -> bool:
        return any(word in text for word in words)

    @staticmethod
    def _looks_like_question(text: str) -> bool:
        return "?" in text or "？" in text or "吗" in text or "呢" in text
