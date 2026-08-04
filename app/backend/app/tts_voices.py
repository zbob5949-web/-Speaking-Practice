"""可用陪练老师音色列表（edge-tts 英文音色）。

id 为 edge-tts 的 voice 名；default 由后端当前默认音色动态标记，
默认音色取自配置 TTS_VOICE（未设置时为 en-US-JennyNeural）。
"""

TTS_VOICES: list[dict[str, object]] = [
    {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "女", "accent": "美式", "description": "自然亲切的美式女声"},
    {"id": "en-US-AriaNeural", "name": "Aria", "gender": "女", "accent": "美式", "description": "明快清晰的美式女声"},
    {"id": "en-US-MichelleNeural", "name": "Michelle", "gender": "女", "accent": "美式", "description": "友好温暖的美式女声"},
    {"id": "en-US-AnaNeural", "name": "Ana", "gender": "女", "accent": "美式", "description": "柔和甜美的美式女声"},
    {"id": "en-US-EmmaNeural", "name": "Emma", "gender": "女", "accent": "美式", "description": "沉稳知性的美式女声"},
    {"id": "en-US-GuyNeural", "name": "Guy", "gender": "男", "accent": "美式", "description": "爽朗明亮的美式男声"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "男", "accent": "美式", "description": "低沉沉稳的美式男声"},
    {"id": "en-US-EricNeural", "name": "Eric", "gender": "男", "accent": "美式", "description": "成熟自然的美式男声"},
    {"id": "en-US-AndrewNeural", "name": "Andrew", "gender": "男", "accent": "美式", "description": "阳光热情的美式男声"},
    {"id": "en-US-RogerNeural", "name": "Roger", "gender": "男", "accent": "美式", "description": "稳重可靠的美式男声"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "gender": "女", "accent": "英式", "description": "优雅知性的英式女声"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "男", "accent": "英式", "description": "绅士沉稳的英式男声"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha", "gender": "女", "accent": "澳式", "description": "随和自然的澳式女声"},
    {"id": "en-AU-WilliamNeural", "name": "William", "gender": "男", "accent": "澳式", "description": "洒脱亲切的澳式男声"},
]
