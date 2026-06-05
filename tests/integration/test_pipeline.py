"""Integration tests for Novel2Screen pipelines.
Tests fast_run and run with real (but small) novel texts using demo mode.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.core.memory import CharacterBible, MemoryManager, SemanticMemory, ShortTermMemory, WorldBible
from backend.core.preprocessor import preprocess_novel
from backend.workflows.novel2screen import Novel2ScreenWorkflow, parse_and_segment, route_mode

THREE_CHAPTER_NOVEL = """
第一章 初入江湖

夜雨潇潇，打在青石板路上发出清脆的响声。李云飞裹紧蓑衣，快步走进路边的客栈。
客栈大堂里只有三两个客人。一个白发老者在角落里自斟自饮，见他进来，微微抬头看了一眼。

"客官打尖还是住店？"掌柜的满脸堆笑。

"住店，一间上房。"李云飞从怀中摸出一块碎银放在柜台上。

第二章 恩怨情仇

第二天清晨，李云飞刚下楼，就看见昨天那个白发老者还坐在原来的位置。
"年轻人，你师傅的死，另有隐情。"老者突然开口，声音不大却清晰入耳。

李云飞脚步一顿，缓缓转过身："前辈认识我师傅？"

"何止认识。"老者叹了口气，"三十年前，我和你师傅一起在华山论剑。他输给了我，但真正害死他的，是'青冥教'的人。"

第三章 决战前夕

李云飞握紧手中的剑，指尖因用力而发白。他知道自己必须找到真相。

沿着老者给的线索，他来到了城外的一座废弃庙宇。月黑风高，远处隐约传来兵器碰撞的声音。

"来得正好。"黑暗中走出一个黑衣人，"李云飞，你师傅死得不冤。他在查的事，你也不该知道。"

李云飞缓缓拔剑："今天，我就替师傅讨个公道。"
"""


class TestParseAndRoute:
    def test_chapter_parsing(self):
        chunks = parse_and_segment(THREE_CHAPTER_NOVEL)
        assert len(chunks) >= 3

    def test_route_mode_short(self):
        assert route_mode(3) == "short"
        assert route_mode(10) == "short"

    def test_route_mode_long(self):
        assert route_mode(11) == "long"
        assert route_mode(100) == "long"

    def test_no_chapter_markers(self):
        chunks = parse_and_segment("This is a plain text without any chapter markers.\n\nJust paragraphs here.\n\nMore content to split.")
        assert len(chunks) >= 1


class TestSemanticMemory:
    def test_index_and_search(self):
        sem = SemanticMemory(chunk_size=500, overlap=100, persist_dir="./data/test_chroma")
        sem.index(THREE_CHAPTER_NOVEL, source_label="test")
        results = sem.search("李云飞 师傅", top_k=3)
        assert len(results) >= 1
        assert any("李云飞" in r["chunk"] for r in results)

    def test_retrieve_context(self):
        sem = SemanticMemory(chunk_size=500, overlap=100, persist_dir="./data/test_chroma")
        sem.index(THREE_CHAPTER_NOVEL, source_label="test")
        context = sem.retrieve_context(["李云飞", "师傅", "仇人"], top_k=3)
        assert len(context) > 0

    def test_keyword_fallback(self):
        sem = SemanticMemory(chunk_size=500, overlap=100, persist_dir="./data/test_chroma")
        sem._chunks = ["李云飞走进客栈", "老者在角落", "剑客握紧手中的剑"]
        sem._indexed = True
        results = sem.search("剑客 手中的", top_k=2)
        assert len(results) >= 1

    def test_empty_search(self):
        sem = SemanticMemory()
        results = sem.search("anything")
        assert results == []


class TestMemoryManager:
    def test_full_memory_stack(self):
        stm = ShortTermMemory()
        cb = CharacterBible()
        wb = WorldBible()
        sem = SemanticMemory(chunk_size=500, persist_dir="./data/test_chroma")
        sem.index(THREE_CHAPTER_NOVEL, "test")

        mm = MemoryManager(stm=stm, char_bible=cb, world_bible=wb, sem_mem=sem)

        cb.add_or_update({"id": "char_001", "name": "李云飞", "role": "protagonist", "goal": "复仇"})
        stm.add_turn("char_001", "今天，我就替师傅讨个公道。")

        ctx = mm.get_context(query="师傅 仇人")
        assert len(ctx["characters"]) >= 1
        assert len(ctx["recent_dialogue"]) >= 1
        assert "char_001" in str(ctx["recent_dialogue"])
        assert "semantic_hits" in ctx

    def test_persist_and_load(self):
        stm = ShortTermMemory()
        cb = CharacterBible()
        wb = WorldBible()
        mm = MemoryManager(stm=stm, char_bible=cb, world_bible=wb)

        cb.add_or_update({"id": "char_001", "name": "Test", "role": "protagonist"})
        wb.set_rules([{"domain": "magic", "description": "Test"}])

        mm.persist_all()

        cb2 = CharacterBible()
        wb2 = WorldBible()
        mm2 = MemoryManager(stm=ShortTermMemory(), char_bible=cb2, world_bible=wb2)
        mm2.load_all()

        assert len(cb2.get_all()) >= 1
        assert len(wb2.get_rules()) >= 1


class TestPreprocessor:
    def test_preprocess_demo_mode(self):
        chapters = parse_and_segment(THREE_CHAPTER_NOVEL)
        result = preprocess_novel(chapters, mode="short")
        assert "theme" in result
        assert "major_events" in result
        assert "characters" in result
        assert len(result["major_events"]) >= 1
        assert len(result["characters"]) >= 1


class TestWorkflow:
    def test_fast_run_demo(self):
        wf = Novel2ScreenWorkflow()
        state = wf.fast_run(
            novel_text=THREE_CHAPTER_NOVEL,
            novel_title="江湖风雨录",
            genre="xuanhuan",
        )
        assert state.get("completed") is True
        assert len(state.get("screenplay_yaml", "")) > 100

    def test_run_demo(self):
        wf = Novel2ScreenWorkflow()
        state = wf.run(
            novel_text=THREE_CHAPTER_NOVEL,
            novel_title="江湖风雨录",
            genre="xuanhuan",
        )
        assert state.get("completed") is True
        assert state.get("critic_score", 0) >= 0
        yaml_content = state.get("screenplay_yaml", "")
        assert len(yaml_content) > 50

    def test_consistency_check(self):
        wf = Novel2ScreenWorkflow()
        report = wf.run_consistency_check(
            novel_chunks=parse_and_segment(THREE_CHAPTER_NOVEL),
            screenplay_yaml="title: Test\nlogline: L\ngenre: Drama\ntheme: T",
        )
        assert "alignment_score" in report
