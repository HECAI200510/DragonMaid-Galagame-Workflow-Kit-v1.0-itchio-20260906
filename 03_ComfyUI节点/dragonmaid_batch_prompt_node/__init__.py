from .nodes import (
    DragonMaidBatchPromptList,
    DragonMaidBatchPromptMultiList,
    DragonMaidBatchPromptPreview,
)


NODE_CLASS_MAPPINGS = {
    "DragonMaidBatchPromptList": DragonMaidBatchPromptList,
    "DragonMaidBatchPromptMultiList": DragonMaidBatchPromptMultiList,
    "DragonMaidBatchPromptPreview": DragonMaidBatchPromptPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DragonMaidBatchPromptList": "龙女仆｜批量提示词输入器（单人）",
    "DragonMaidBatchPromptMultiList": "龙女仆｜批量提示词输入器（2～6人对齐）",
    "DragonMaidBatchPromptPreview": "龙女仆｜批量提示词预览",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
