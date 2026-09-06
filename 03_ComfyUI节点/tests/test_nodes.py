import unittest

from dragonmaid_batch_prompt_node.nodes import (
    DragonMaidBatchPromptList,
    DragonMaidBatchPromptMultiList,
    DragonMaidBatchPromptPreview,
    PromptEntry,
    parse_prompt_document,
    parse_numbered_markdown,
    smart_align_two_documents,
)


class BatchPromptNodeTests(unittest.TestCase):
    def test_numbered_multiline_markdown(self):
        value = """# 分镜
1. smiling, looking at viewer,
hand on table

2、angry, arms crossed
3) crying softly"""
        rows = parse_numbered_markdown(value)
        self.assertEqual([item.number for item in rows], ["1", "2", "3"])
        self.assertIn("hand on table", rows[0].text)

    def test_inline_and_blank_block_parsing(self):
        inline = parse_numbered_markdown("1.smile，2.angry，3.crying")
        self.assertEqual([item.text for item in inline], ["smile", "angry", "crying"])
        blocks, mode = parse_prompt_document("first\n\nsecond")
        self.assertEqual(mode, "空行/分隔线")
        self.assertEqual([item.text for item in blocks], ["first", "second"])

    def test_single_node_prefix_slice_repeat_and_seeds(self):
        node = DragonMaidBatchPromptList()
        prompts, job_ids, seeds, total, preview = node.build(
            "1. smile\n2. wave\n3. read a book",
            "quality",
            "SFW",
            2,
            2,
            2,
            100,
        )
        self.assertEqual(prompts, ["quality, wave, SFW", "quality, wave, SFW", "quality, read a book, SFW", "quality, read a book, SFW"])
        self.assertEqual(job_ids, ["2_01", "2_02", "3_01", "3_02"])
        self.assertEqual(seeds, [100, 101, 102, 103])
        self.assertEqual(total, 4)
        self.assertIn("3_02", preview)

    def test_smart_align_full_and_suffix(self):
        full = [PromptEntry(str(index), f"A{index}") for index in range(1, 7)]
        suffix = [PromptEntry(str(index), f"B{index}") for index in range(4, 7)]
        left, right, note = smart_align_two_documents(full, suffix)
        self.assertEqual([item.number for item in left], ["1", "2", "3"])
        self.assertEqual([item.number for item in right], ["1", "2", "3"])
        self.assertIn("角色A包含前后两组", note)

    def test_multi_node_aligns_offset_documents(self):
        node = DragonMaidBatchPromptMultiList()
        result = node.build(
            3,
            "1. A1\n2. A2",
            "101. B1\n102. B2",
            "201. C1\n202. C2",
            "",
            "",
            "",
            "quality",
            "SFW",
            1,
            0,
            1,
            900,
        )
        self.assertEqual(result[0], ["quality, A1, SFW", "quality, A2, SFW"])
        self.assertEqual(result[1], ["quality, B1, SFW", "quality, B2, SFW"])
        self.assertEqual(result[2], ["quality, C1, SFW", "quality, C2, SFW"])
        self.assertEqual(result[6], ["1_01", "2_01"])
        self.assertEqual(result[7], [900, 901])
        self.assertEqual(result[8], 2)
        self.assertIn("连续编号起点", result[10])
        self.assertEqual(result[3], ["", ""])

    def test_multi_node_rejects_missing_number(self):
        node = DragonMaidBatchPromptMultiList()
        with self.assertRaisesRegex(ValueError, "角色B缺少"):
            node.build(2, "1. A1\n2. A2", "1. B1", "", "", "", "", "", "", 1, 0, 1, 1)

    def test_list_contract_and_preview_output(self):
        self.assertEqual(DragonMaidBatchPromptList.OUTPUT_IS_LIST, (True, True, True, False, False))
        self.assertEqual(len(DragonMaidBatchPromptMultiList.OUTPUT_IS_LIST), len(DragonMaidBatchPromptMultiList.RETURN_TYPES))
        value = DragonMaidBatchPromptPreview().show(["one", "two"])
        self.assertEqual(value, {"ui": {"text": ["one", "two"]}})


if __name__ == "__main__":
    unittest.main()
