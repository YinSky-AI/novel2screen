from __future__ import annotations

from backend.schemas.models import Character, CharacterRole, Screenplay, Scene, Beat, BeatType, Transition, Episode
from backend.schemas.validator import screenplay_to_yaml, yaml_to_screenplay


class TestCharacterRoleMapping:
    def test_chinese_protagonist_maps_to_enum(self) -> None:
        c = Character(id="char_001", name="林风", role="主角", goal="冒险", arc="成长")
        assert c.role == CharacterRole.PROTAGONIST

    def test_chinese_antagonist_maps_to_enum(self) -> None:
        c = Character(id="char_002", name="魔王", role="反派", goal="毁灭", arc="堕落")
        assert c.role == CharacterRole.ANTAGONIST

    def test_chinese_supporting_maps_to_enum(self) -> None:
        c = Character(id="char_003", name="村民", role="配角", goal="帮助", arc="不变")
        assert c.role == CharacterRole.SUPPORTING

    def test_english_protagonist_maps_to_enum(self) -> None:
        c = Character(id="char_001", name="Hero", role="protagonist", goal="Win", arc="Growth")
        assert c.role == CharacterRole.PROTAGONIST

    def test_unknown_role_falls_back_to_supporting(self) -> None:
        c = Character(id="char_001", name="Someone", role="random_role", goal="?", arc="?")
        assert c.role == CharacterRole.SUPPORTING

    def test_int_role_converts_to_supporting(self) -> None:
        c = Character(id="char_001", name="X", role=123, goal="?", arc="?")
        assert c.role == CharacterRole.SUPPORTING


class TestYAMLLanguageOutput:
    def test_chinese_yaml_uses_chinese_role_labels(self) -> None:
        characters = [
            Character(id="char_001", name="林风", role="主角", goal="冒险", arc="成长"),
            Character(id="char_002", name="艾琳", role="配角", goal="帮助", arc="无"),
        ]
        sp = Screenplay(
            title="测试",
            logline="测试故事",
            genre="drama",
            theme="courage",
            characters=characters,
            episodes=[],
        )
        yaml_str = screenplay_to_yaml(sp, language="chinese")
        assert "主角" in yaml_str
        assert "配角" in yaml_str
        assert "protagonist" not in yaml_str

    def test_english_yaml_uses_english_role_labels(self) -> None:
        characters = [
            Character(id="char_001", name="Hero", role=CharacterRole.PROTAGONIST, goal="Win", arc="Growth"),
        ]
        sp = Screenplay(
            title="Test",
            logline="A test",
            genre="drama",
            theme="courage",
            characters=characters,
            episodes=[],
        )
        yaml_str = screenplay_to_yaml(sp, language="english")
        assert "protagonist" in yaml_str
        assert "主角" not in yaml_str


class TestFullScreenplayIntegrity:
    def test_screenplay_with_scenes_roundtrip(self) -> None:
        sp = Screenplay(
            title="命运之戒",
            logline="少年发现神秘戒指后被传送到异世界",
            genre="fantasy",
            theme="勇气与成长",
            characters=[
                Character(id="char_001", name="林风", role="主角", goal="回到原来的世界", arc="从普通少年成长为英雄"),
                Character(id="char_002", name="艾琳", role="配角", goal="拯救族人", arc="从孤独到信任"),
            ],
            episodes=[
                Episode(
                    id="ep_001",
                    title="启程",
                    summary="林风发现戒指，踏上旅程",
                    scenes=[
                        Scene(
                            scene_id="sc_001",
                            location="村口古树下",
                            time="黄昏",
                            visual_focus="夕阳下的古树和少年背影",
                            sound_effect="风吹树叶的沙沙声",
                            beats=[
                                Beat(type=BeatType.ACTION, content="林风站在古树下，紧握戒指", emotion="决心"),
                                Beat(type=BeatType.DIALOGUE, character_id="char_001", content="我必须走", emotion="坚定"),
                                Beat(type=BeatType.SILENCE, content="风吹过，树叶飘落", emotion=None),
                            ],
                            transition=Transition.CUT,
                            duration_estimate="45s",
                        )
                    ],
                )
            ],
        )
        yaml_str = screenplay_to_yaml(sp, language="chinese")
        assert "命运之戒" in yaml_str
        assert "林风" in yaml_str
        assert "sc_001" in yaml_str
        assert "风吹树叶" in yaml_str

        # Roundtrip
        sp2 = yaml_to_screenplay(yaml_str)
        assert sp2.title == sp.title
        assert len(sp2.characters) == 2
        assert len(sp2.episodes) == 1
