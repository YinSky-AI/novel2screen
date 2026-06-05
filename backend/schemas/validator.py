"""
YAML Schema validation for Novel2Screen.
Provides safe YAML serialization and deserialization for Screenplay models.
"""
import json
import yaml
from pydantic import ValidationError
from .models import Screenplay

_DEMO_SCREENPLAY_YAML = """\
title: "\u6c5f\u6e56\u98ce\u96e8\u5f55"
genre: Drama
mode: short
episodes:
- episode_id: 1
  title: "\u521d\u5165\u6c5f\u6e56"
  synopsis: "\u674e\u4e91\u98de\u521d\u5165\u6c5f\u6e56\uff0c\u5728\u5ba2\u6808\u9047\u5230\u4e86\u4e00\u4e2a\u5947\u602a\u7684\u8001\u4eba\u3002"
  duration_estimate: 45min
  scenes:
  - scene_id: "1_1"
    location: "\u5ba2\u6808\u5927\u5802"
    time_of_day: "\u591c\u665a"
    characters_present:
    - "\u674e\u4e91\u98de"
    - "\u8001\u4eba"
    beats:
    - beat_id: "1_1_1"
      type: action
      description: "\u674e\u4e91\u98de\u8d70\u8fdb\u5ba2\u6808\uff0c\u6296\u843d\u6597\u7bf7\u4e0a\u7684\u96e8\u6c34\u3002"
      characters_involved:
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u4e2d\u666f\uff0c\u8ddf\u62cd"
    - beat_id: "1_1_2"
      type: dialogue
      description: "\u8001\u4eba\uff1a\u201c\u4f60\u5e08\u7236\u7684\u6b7b\uff0c\u53e6\u6709\u9690\u60c5\u3002\u201d"
      characters_involved:
      - "\u8001\u4eba"
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u7279\u5199\uff0c\u8001\u4eba\u8138\u90e8"
    transition: "\u6de1\u5165\u6de1\u51fa"
- episode_id: 2
  title: "\u6069\u6028\u60c5\u4ec7"
  synopsis: "\u674e\u4e91\u98de\u8c03\u67e5\u5e08\u7236\u6b7b\u56e0\uff0c\u53d1\u73b0\u6c5f\u6e56\u4e0a\u6709\u4e00\u4e2a\u795e\u79d8\u7ec4\u7ec7\u3002"
  duration_estimate: 45min
  scenes:
  - scene_id: "2_1"
    location: "\u5c71\u95f4\u5c0f\u5e99"
    time_of_day: "\u9ec4\u660f"
    characters_present:
    - "\u674e\u4e91\u98de"
    - "\u795e\u79d8\u4eba"
    beats:
    - beat_id: "2_1_1"
      type: action
      description: "\u674e\u4e91\u98de\u6cbf\u7740\u7ebf\u7d22\u627e\u5230\u5c71\u95f4\u5c0f\u5e99\u3002"
      characters_involved:
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u8fdc\u666f\uff0c\u5c55\u793a\u5c71\u95f4\u73af\u5883"
    - beat_id: "2_1_2"
      type: dialogue
      description: "\u795e\u79d8\u4eba\uff1a\u201c\u4f60\u6765\u665a\u4e86\uff0c\u4ed6\u4eec\u5df2\u7ecf\u884c\u52a8\u4e86\u3002\u201d"
      characters_involved:
      - "\u795e\u79d8\u4eba"
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u4e2d\u666f\u5bf9\u8bdd"
    transition: "\u5207\u6362"
- episode_id: 3
  title: "\u51b3\u6218\u524d\u5915"
  synopsis: "\u771f\u76f8\u5927\u767d\uff0c\u674e\u4e91\u98de\u51b3\u5b9a\u4e0e\u795e\u79d8\u7ec4\u7ec7\u505a\u6700\u540e\u4e86\u65ad\u3002"
  duration_estimate: 45min
  scenes:
  - scene_id: "3_1"
    location: "\u57ce\u5916\u5e9f\u589f"
    time_of_day: "\u6df1\u591c"
    characters_present:
    - "\u674e\u4e91\u98de"
    beats:
    - beat_id: "3_1_1"
      type: action
      description: "\u674e\u4e91\u98de\u63e1\u7d27\u624b\u4e2d\u7684\u5251\uff0c\u773c\u795e\u575a\u5b9a\u5982\u94c1\u3002"
      characters_involved:
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u7279\u5199\uff0c\u624b\u63e1\u5251\u67c4"
    - beat_id: "3_1_2"
      type: dialogue
      description: "\u674e\u4e91\u98de\uff1a\u201c\u8fd9\u4e00\u6b65\u8d70\u51fa\u53bb\uff0c\u5c31\u518d\u4e5f\u56de\u4e0d\u4e86\u5934\u4e86\u3002\u201d"
      characters_involved:
      - "\u674e\u4e91\u98de"
      camera_suggestion: "\u4e2d\u666f\uff0c\u80cc\u5f71\u526a\u5f71"
    transition: "\u6e10\u9ed1\u7ed3\u5c3e"
metadata:
  created_at: "2024-01-15T10:30:00Z"
  tool: Novel2Screen-Demo
  total_episodes: 3
  total_scenes: 3
"""



def screenplay_to_yaml(screenplay: Screenplay) -> str:
    data = screenplay.model_dump(mode='json', exclude_none=True)
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

def yaml_to_screenplay(yaml_str: str) -> Screenplay:
    data = yaml.safe_load(yaml_str)
    return Screenplay(**data)

def validate_screenplay_yaml(yaml_str: str) -> tuple:
    errors = []
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]
    if not isinstance(data, dict):
        return False, ["Root value must be a mapping"]
    try:
        Screenplay(**data)
        return True, []
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(p) for p in err["loc"])
            errors.append(f"{loc}: {err["msg"]}")
        return False, errors

