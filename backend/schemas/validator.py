from __future__ import annotations

import yaml

from backend.schemas.models import Beat, BeatType, Character, CharacterRole, Episode, Scene, Screenplay, Transition, ValidationReport


def screenplay_to_yaml(screenplay: Screenplay) -> str:
    data = {
        "title": screenplay.title,
        "logline": screenplay.logline,
        "genre": screenplay.genre,
        "theme": screenplay.theme,
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role.value,
                "goal": c.goal,
                "fear": c.fear,
                "arc": c.arc,
                "voice_style": c.voice_style,
            }
            for c in screenplay.characters
        ],
        "episodes": [
            {
                "id": ep.id,
                "title": ep.title,
                "summary": ep.summary,
                "scenes": [
                    {
                        "scene_id": s.scene_id,
                        "location": s.location,
                        "time": s.time,
                        "visual_focus": s.visual_focus,
                        "sound_effect": s.sound_effect,
                        "voice_over": s.voice_over,
                        "transition": s.transition.value,
                        "duration_estimate": s.duration_estimate,
                        "beats": [
                            {
                                "type": b.type.value,
                                "character_id": b.character_id,
                                "content": b.content,
                                "emotion": b.emotion,
                            }
                            for b in s.beats
                        ],
                    }
                    for s in ep.scenes
                ],
            }
            for ep in screenplay.episodes
        ],
    }
    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def yaml_to_screenplay(yaml_str: str) -> Screenplay:
    data = yaml.safe_load(yaml_str)
    if not isinstance(data, dict):
        raise ValueError("YAML must be a dictionary at top level")

    characters = [
        Character(
            id=c["id"],
            name=c["name"],
            role=CharacterRole(c["role"]),
            goal=c.get("goal", ""),
            fear=c.get("fear", ""),
            arc=c.get("arc", ""),
            voice_style=c.get("voice_style", ""),
        )
        for c in data.get("characters", [])
    ]

    episodes = []
    for ep_data in data.get("episodes", []):
        scenes = []
        for s_data in ep_data.get("scenes", []):
            beats = [
                Beat(
                    type=BeatType(b["type"]),
                    character_id=b.get("character_id"),
                    content=b.get("content", ""),
                    emotion=b.get("emotion"),
                )
                for b in s_data.get("beats", [])
            ]
            scenes.append(
                Scene(
                    scene_id=s_data["scene_id"],
                    location=s_data.get("location", ""),
                    time=s_data.get("time", ""),
                    visual_focus=s_data.get("visual_focus"),
                    sound_effect=s_data.get("sound_effect"),
                    voice_over=s_data.get("voice_over"),
                    beats=beats,
                    transition=Transition(s_data.get("transition", "cut")),
duration_estimate="60s",
                )
            )
        episodes.append(
            Episode(
                id=ep_data["id"],
                title=ep_data.get("title", ""),
                summary=ep_data.get("summary", ""),
                scenes=scenes,
            )
        )

    return Screenplay(
        title=data.get("title", ""),
        logline=data.get("logline", ""),
        genre=data.get("genre", ""),
        theme=data.get("theme", ""),
        characters=characters,
        episodes=episodes,
    )


def validate_screenplay_yaml(yaml_str: str) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        screenplay = yaml_to_screenplay(yaml_str)
    except Exception as e:
        return ValidationReport(valid=False, errors=[f"YAML parse error: {e}"])

    if not screenplay.title:
        errors.append("Screenplay title is missing")
    if not screenplay.logline:
        warnings.append("Logline is empty")
    if not screenplay.characters:
        warnings.append("No characters defined")
    if not screenplay.episodes:
        errors.append("No episodes defined")

    char_ids = {c.id for c in screenplay.characters}
    for ep in screenplay.episodes:
        for sc in ep.scenes:
            for beat in sc.beats:
                if beat.character_id and beat.character_id not in char_ids:
                    errors.append(
                        f"Beat in scene {sc.scene_id} references unknown character {beat.character_id}"
                    )

    return ValidationReport(valid=len(errors) == 0, errors=errors, warnings=warnings)


_DEMO_SCREENPLAY_YAML = """\
title: "命运之轮"
logline: "一个普通程序员意外发现自己能通过代码改变现实，但每一次修改都会引发不可预知的后果。"
genre: "科幻悬疑"
theme: "科技与人性的边界"
characters:
  - id: "char_001"
    name: "林峰"
    role: "protagonist"
    goal: "找到控制能力的方法，保护所爱之人"
    fear: "失去自我，变成代码的一部分"
    arc: "从逃避责任到主动承担，从恐惧能力到驾驭能力"
    voice_style: "内敛理性，偶尔自嘲，关键时刻爆发力强"
  - id: "char_002"
    name: "苏瑶"
    role: "supporting"
    goal: "帮助林峰对抗神秘组织，同时查明父亲失踪的真相"
    fear: "被组织洗脑控制"
    arc: "从对林峰的不信任到成为最坚定的盟友"
    voice_style: "冷静果断，偶尔流露出脆弱"
  - id: "char_003"
    name: "K"
    role: "antagonist"
    goal: "夺取林峰的能力，掌控世界运行规则"
    fear: "被自己创造的系统反噬"
    arc: "从看似帮助林峰到暴露真实意图"
    voice_style: "优雅从容，暗藏锋芒，每一句话都像精心设计"
episodes:
  - id: "ep_001"
    title: "代码里的世界"
    summary: "林峰在一次加班中发现自己的代码在现实世界产生了实际影响。"
    scenes:
      - scene_id: "sc_001"
        location: "科技公司办公室 - 深夜"
        time: "凌晨2点"
        visual_focus: "屏幕上流动的异常代码"
        sound_effect: "键盘敲击声"
        transition: "cut"
        duration_estimate: "120s"
        beats:
          - type: "action"
            content: "林峰盯着屏幕，手指快速敲击键盘，额头上渗出细密的汗珠。"
            emotion: "紧张"
          - type: "dialogue"
            character_id: "char_001"
            content: "这不可能...这条日志记录的是今天下午发生的事情，但这段代码我五分钟前才写的。"
            emotion: "震惊"
          - type: "reaction"
            content: "他揉了揉眼睛，重新查看时间戳。确认无误后，手指微微颤抖。"
            emotion: "恐惧"
          - type: "silence"
            content: "办公室里只剩下空调的嗡嗡声和远处服务器机房的低鸣。"
      - scene_id: "sc_002"
        location: "林峰公寓"
        time: "凌晨4点"
        visual_focus: "昏暗房间中笔记本屏幕的冷光"
        sound_effect: "窗外偶尔驶过的车辆声"
        transition: "dissolve"
        duration_estimate: "90s"
        beats:
          - type: "action"
            content: "林峰坐在床边，笔记本放在膝盖上，手指悬停在键盘上方。"
            emotion: "犹豫"
          - type: "dialogue"
            character_id: "char_001"
            content: "再试一次...只要改一行代码，看看会发生什么。"
            emotion: "决心"
          - type: "action"
            content: "他输入了一行改变变量的代码，按下回车。窗外路灯突然全部熄灭，又瞬间亮起。"
            emotion: "惊骇"
          - type: "reaction"
            content: "林峰猛地合上笔记本，大口喘气，眼睛瞪得浑圆。"
            emotion: "恐惧"
  - id: "ep_002"
    title: "蝴蝶效应"
    summary: "林峰尝试用能力修复过去的错误，却发现每一次修改都会带来更糟糕的结果。"
    scenes:
      - scene_id: "sc_003"
        location: "咖啡馆"
        time: "下午3点"
        visual_focus: "林峰手中的平板电脑，屏幕上显示着一个复杂的流程图"
        sound_effect: "轻柔的爵士乐，咖啡机的蒸汽声"
        transition: "cut"
        duration_estimate: "150s"
        beats:
          - type: "dialogue"
            character_id: "char_001"
            content: "我尝试修复了三件事。第一天，我救了一个车祸中的人。第二天，他变成了连环杀手。"
            emotion: "绝望"
          - type: "dialogue"
            character_id: "char_002"
            content: "这说明你不应该随意改变既定事实。但你有没有想过，也许这个能力根本不是用来'修复'的？"
            emotion: "冷静"
          - type: "reaction"
            character_id: "char_001"
            content: "林峰愣住了，手中的咖啡杯停在半空。"
            emotion: "困惑"
          - type: "silence"
            content: "两人对视，咖啡馆的背景音乐仿佛在这一刻被抹去。"
      - scene_id: "sc_004"
        location: "废弃的服务器机房"
        time: "深夜"
        visual_focus: "一排排闪烁的服务器指示灯，地面上散落的电缆"
        sound_effect: "服务器的嗡鸣，远处传来脚步声"
        transition: "fade"
        duration_estimate: "180s"
        beats:
          - type: "action"
            content: "林峰和苏瑶小心翼翼地穿过布满灰尘的机柜走廊。"
            emotion: "紧张"
          - type: "dialogue"
            character_id: "char_003"
            content: "林峰，你以为自己是第一个发现这个秘密的人吗？欢迎来到真正的世界。"
            emotion: "神秘"
          - type: "action"
            content: "K从阴影中走出，轻轻鼓掌，面带微笑。他身后的巨型屏幕突然亮起，显示出一个庞大的数据网络。"
            emotion: "震撼"
          - type: "reaction"
            character_id: "char_001"
            content: "林峰下意识地挡在苏瑶前面，手指紧握。"
            emotion: "警觉"
          - type: "dialogue"
            character_id: "char_002"
            content: "你就是那个给我父亲发邮件的人。"
            emotion: "愤怒"
"""


def get_demo_screenplay() -> Screenplay:
    return yaml_to_screenplay(_DEMO_SCREENPLAY_YAML)
