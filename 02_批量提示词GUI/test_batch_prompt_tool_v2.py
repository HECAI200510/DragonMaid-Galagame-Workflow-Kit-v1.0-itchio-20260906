import unittest

from batch_prompt_tool_v2 import (
    combine_prompt,
    combine_prompt_parts,
    convert_ui_workflow_to_api,
    find_prompt_targets,
    parse_prompt_document,
    pair_entries_by_number,
    PromptEntry,
    align_prompt_documents,
    build_dynamic_region_workflow,
    consecutive_numbers,
    renumber_entries,
    smart_align_two_documents,
    parse_numbered_markdown,
)


class BatchPromptV2Tests(unittest.TestCase):
    def test_numbered_multiline_markdown(self):
        value = """# 分镜\n1. smiling, looking at viewer,\nhand on table\n\n2、angry, arms crossed\n3) crying softly"""
        rows = parse_numbered_markdown(value)
        self.assertEqual([x.number for x in rows], ["1", "2", "3"])
        self.assertIn("hand on table", rows[0].text)

    def test_fallback_blank_blocks(self):
        rows, mode = parse_prompt_document("first\n\nsecond")
        self.assertEqual(mode, "空行/分隔线")
        self.assertEqual([x.text for x in rows], ["first", "second"])

    def test_inline_numbered_prompts(self):
        rows = parse_numbered_markdown("1.smile, looking at viewer，2.angry, arms crossed，3.crying")
        self.assertEqual([x.number for x in rows], ["1", "2", "3"])
        self.assertEqual(rows[1].text, "angry, arms crossed")

    def test_combine(self):
        self.assertEqual(combine_prompt("base,", ",action"), "base, action")
        self.assertEqual(combine_prompt_parts("head", "body", "tail"), "head, body, tail")

    def test_custom_panel_conversion_and_targets(self):
        ui = {
            "nodes": [
                {
                    "id": 1,
                    "type": "DragonMaidPromptPanel",
                    "title": "正面提示词总控",
                    "inputs": [{"name": "clip", "link": 1}],
                    "widgets_values": ["quality", "smile", "pose", "identity", "outfit", "shot"],
                }
            ],
            "links": [[1, 9, 1, 1, 0, "CLIP"]],
        }
        api = convert_ui_workflow_to_api(ui)
        self.assertEqual(api["1"]["inputs"]["动作提示词"], "pose")
        targets = find_prompt_targets(api)
        self.assertEqual(len(targets), 6)
        self.assertTrue(any(x[2] == "通用提示词" for x in targets))

    def test_pair_two_documents_by_number(self):
        left = [PromptEntry("1", "A1"), PromptEntry("3", "A3")]
        right = [PromptEntry("3", "B3"), PromptEntry("1", "B1")]
        pairs = pair_entries_by_number(left, right)
        self.assertEqual([(a.text, b.text) for a, b in pairs], [("A1", "B1"), ("A3", "B3")])

    def test_pair_rejects_number_mismatch(self):
        with self.assertRaisesRegex(ValueError, "角色B缺少"):
            pair_entries_by_number([PromptEntry("1", "A1")], [PromptEntry("2", "B2")])

    def test_align_three_prompt_documents(self):
        docs = [
            [PromptEntry("1", "A1"), PromptEntry("2", "A2")],
            [PromptEntry("2", "B2"), PromptEntry("1", "B1")],
            [PromptEntry("1", "C1"), PromptEntry("2", "C2")],
        ]
        aligned = align_prompt_documents(docs)
        self.assertEqual([[x.text for x in row] for row in aligned], [["A1", "B1", "C1"], ["A2", "B2", "C2"]])

    def test_dynamic_three_person_region_workflow(self):
        base = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "base.safetensors"}, "_meta": {"title": "base"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "quality, 2girls", "clip": ["1", 1]}, "_meta": {"title": "共同画面"}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad", "clip": ["1", 1]}, "_meta": {"title": "负面"}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1216, "height": 832, "batch_size": 4}, "_meta": {"title": "画布"}},
            "5": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 30, "cfg": 5.2, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}, "_meta": {"title": "采样"}},
        }
        participants = [
            {"role": "小红", "position": "左上"},
            {"role": "管家", "position": "正中"},
            {"role": "小绿", "position": "右下"},
        ]
        workflow, prompt_ids = build_dynamic_region_workflow(base, participants)
        self.assertEqual(len(prompt_ids), 3)
        self.assertIn("3girls", workflow["2"]["inputs"]["text"])
        sampler = next(node for node in workflow.values() if node["class_type"] == "KSampler")
        self.assertEqual(sampler["inputs"]["positive"], ["21", 0])

    def test_renumber_offset_sequence(self):
        source = [PromptEntry(str(i), f"P{i}") for i in range(101, 201)]
        self.assertEqual(consecutive_numbers(source)[0], 101)
        normalized = renumber_entries(source)
        self.assertEqual((normalized[0].number, normalized[-1].number), ("1", "100"))
        self.assertEqual(source[0].number, "101")

    def test_smart_align_full_200_and_suffix_101_200(self):
        full = [PromptEntry(str(i), f"A{i}") for i in range(1, 201)]
        suffix = [PromptEntry(str(i), f"B{i}") for i in range(101, 201)]
        left, right, message = smart_align_two_documents(full, suffix)
        self.assertEqual((len(left), len(right)), (100, 100))
        self.assertEqual((left[0].number, left[-1].number), ("1", "100"))
        self.assertEqual((right[0].number, right[-1].number), ("1", "100"))
        self.assertIn("角色A包含前后两组", message)

    def test_smart_align_equal_length_offset_ranges(self):
        left = [PromptEntry(str(i), f"A{i}") for i in range(1, 101)]
        right = [PromptEntry(str(i), f"B{i}") for i in range(101, 201)]
        left, right, message = smart_align_two_documents(left, right)
        self.assertEqual(right[0].number, "1")
        self.assertEqual(right[-1].number, "100")
        self.assertIn("统一重排", message)


if __name__ == "__main__":
    unittest.main()
