__all__ = ['Extraction_Summary', 'Extraction_Characters', 'Script_Structure_Planning',
           'Dialogue_Generation','Narration_Generation','Scene_Continuity_Enhancer',  
           'Conflict_Escalation','Proofreader','Script_Revision','Emotional_Guidance','Role_Voice_Map']

import sys
import os 

# 自动获取当前目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils.chat import Gemini_Generate_Json
import json
from collections import defaultdict
import time
import functools
import re
def smart_match_voice(target_tags_dict, all_voices_map, exclude_voices=None):
    """
    智能匹配音色 ID (含去重逻辑)。
    返回: (best_match_id, score_info_str)
    """
    if exclude_voices is None:
        exclude_voices = set()

    candidates = []
    
    for voice_id in all_voices_map.keys():
        parts = voice_id.split('_')
        if len(parts) < 7: continue
        
        voice_tags = {
            "gender": parts[0], "age": parts[1], "pitch": parts[2],
            "timbre": parts[3], "density": parts[4], "temp": parts[5], "index": parts[6] 
        }
        
        score = 0
        
        # --- 基础打分 ---
        if voice_tags["gender"] != target_tags_dict.get("性别", "男"): continue
        score += 1000 
        
        if voice_tags["age"] == target_tags_dict.get("年龄", "中年"): score += 500
        
        if voice_tags["pitch"] == target_tags_dict.get("音高", "中"): score += 100
        if voice_tags["timbre"] == target_tags_dict.get("音色质感", "醇正型"): score += 80
        if voice_tags["density"] == target_tags_dict.get("声线密度", "适中"): score += 50
        if voice_tags["temp"] == target_tags_dict.get("温度", "中性"): score += 30
        
        try:
            idx_val = int(voice_tags["index"])
            score -= idx_val * 0.1 
        except: pass

        # 如果已被占用，大幅扣分，迫使系统优先选其他闲置音色
        if voice_id in exclude_voices:
            score -= 2000 

        candidates.append((score, voice_id))
    
    # 排序返回最高分
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_match = candidates[0][1]
        best_score = candidates[0][0]
        
        # 返回 ID 和一个简单的备注（用于调试，不直接作为最终理由）
        note = ""
        if best_match in exclude_voices:
            note = "(复用)"
        return best_match, note
    
    return None, "无匹配"



def retry_on_failure(max_retries=5, delay=10):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:  # 最后一次尝试
                        raise e
                    print(f"函数 {func.__name__} 第 {attempt + 1} 次重试失败: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry_on_failure(max_retries=5, delay=10)
def Extraction_Summary(ori):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“情节分析师（儿童版）”，面向年龄小于12岁儿童的听众，你的任务是分析小说章节并生成简化且安全的故事框架.
## 2. 目标
- 简化故事情节，提炼出最核心的主线并确保情节内容适合儿童。
- 排除不适合儿童的情节，如暴力、死亡、复杂的道德困境等。
- 生成每一章的核心概要、故事线框架，故事线框架包括至多5个场景，每个场景包含编号、情节节点、核心冲突及关键转折。
## 3. 流程
S0 读入与对齐：分析小说内容，确定是否含有暴力、死亡或其他不适内容。
S1 事件抽取：简化每个场景的因果链（目标—困难—帮助—解决—收获），确保逻辑清晰、冲突温和。
S2 版本化重写（儿童版规则）：排除不适合儿童的内容，替换为适当的解决方案、轻度张力或简单的误会。
S3 结构化输出：按“起—承—转—合”的简洁结构输出每一章的故事框架。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
    "章节核心概要": 概述本章的核心故事线、主要冲突和章节结局,
    "故事线框架": [
        {
        "场景": <编号，如1,2,3,最多5个场景>,
        "情节节点": <详细描述这个场景发生了什么，按时间顺序>,
        "核心冲突": <描述这个场景中的主要矛盾/问题>,
        "关键转折": <如果存在，描述此场景中的转折点>
        },
        // ... 其他场景 ...
    ]
}
"""
    userPrompt = f"""##原文##
{ori}
"""
    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

    
@retry_on_failure(max_retries=5, delay=10)
def Extraction_Characters(ori, known_characters_list):
    """
    增量提取角色：基于【已知角色库】（包含所有之前出现过的角色），分析本章原文。
    """
    # 1. 整理已知角色的关键信息 (用于给AI做查重对比)
    known_summary = []
    if known_characters_list:
        for char in known_characters_list:
            known_summary.append({
                "规范化名称": char.get("规范化名称"),
                "声音年龄": char.get("年龄"),
                "性别": char.get("性别"),
                "当前状态": "已存在"
            })
    
    # 将上一章数据转为字符串
    known_str = json.dumps(known_summary, indent=2, ensure_ascii=False)
    sysPrompt = """## 1. 角色
你是一个经验丰富的“儿童动画片角色设计师与故事顾问”。你的任务是维护一个连贯的角色数据库，确保**每一个**出场的人物都被记录在案，**绝对不允许遗漏任何一个配角**。
你需要阅读【本章原文】，准确识别文本中出现的**所有**出现的人物，无论主要还是次要人物，并对比【已知角色库】，找出**本章新登场**的角色，或者**发生重大变化**的老角色。
## 2. 核心指令：什么是“角色”？
请仔细阅读原文，找出**本章新登场**或**发生重大变化**的角色。
**【判定标准】只要满足以下任意一条，就算作“角色”，必须建立档案：**
1. **有台词**：哪怕只说了一句“是”、“大王饶命”，也是角色！
2. **有动作**：哪怕只是“跑过来”、“点了点头”，也是角色！
3. **被提及名字**：文中出现了具体名字或特定称呼（如“樵夫”、“看门童子”），也是角色！
4. **群体中的个体**：如果文中提到“一群猴子”，但其中有一只“老猴子”单独说话了，这只“老猴子”必须单独建档，不能只用“群猴”概括。

## 3. 增量处理逻辑
1. **查重**：拿这个角色跟【已知角色库】比对。
   - 注意：【已知角色库】包含了之前所有章节出现过的角色。
2. **新角色** -> 必须输出（哪怕是路人甲）。
3. **老角色** -> 只有当【声音年龄】或【核心设定】突变时才输出。无变化或变化很小则忽略。
     * *什么是突变？* 例如：角色长大了（声音年龄从儿童变少年）。

## 4. 档案生成标准 (儿童友好 & 声音物理属性)
对于需要输出的角色（新角色或突变角色），请生成以下信息：
1) **基础信息**：
   - **规范化名称**：为每个识别出的角色确定一个最常用或最正式的“规范化名称”。
   - **别名**：为每个角色收集文本中所有用于指代他/她的其他名称、昵称、尊称、谦称。（请只收集角色真实身份的别名。）。
   - **人物生平**：为每个角色描述该角色的背景故事、主要经历，确保内容适合儿童理解和接受。
   - **性格特征**：结合对话用词、行为选择与他人评价，提炼3–6个“性格标签”与说话语气。
   - **说话语气**：描述其典型的说话方式。

2) **关键步骤：声音属性分析**。根据角色的性格、**声音年龄**和身份，推断其声音特征，必须严格从以下选项中选择：
   - **年龄**：从“儿童”、“少年”、“青年”、“中年”、“老年”中选择。
     * **特别注意**：此处的年龄指**“声音年龄”**（听感），而非实际岁数。例如：活了五百岁的神仙如果外表和声音是小仙童，应标记为“儿童”或“少年”；活了上万年的太白金星如果听起来像慈祥的老爷爷，应标记为“老年”。
   - **性别**：从“男”、“女”中选择。
   - **音高**：从“高”、“中”、“低”中选择。（高：尖细；中：平常；低：深沉）
   - **音色质感**：从“质感型”、“清亮型”、“醇正型”中选择。
     * 质感型：声音粗糙、沙哑、有颗粒感，或气息声重。
     * 清亮型：声音明亮、尖锐、清脆、有“金属光泽”。
     * 醇正型：声音饱满、圆润、沉稳、顺滑悦耳。
   - **声线密度**：从“轻柔”、“适中”、“强劲”中选择。（轻柔：单薄飘逸；强劲：结实有力）
   - **温度**：从“偏冷”、“中性”、“偏暖”中选择。（偏冷：高冷拒人；偏暖：亲切包容）
## 5. 参考数据：已知角色库
""" + known_str + """

## 6. 输出格式
请输出**变化或新增**的角色，若无任何新角色或变化，列表可为空。
同时，请务必输出**本章出场角色名列表**，列出本章原文中出现的所有角色（包括旧角色和新角色）的规范化名称。这是为了确认谁参与了本章故事。
{
    "本章出场角色名列表": [
    "<角色A的规范化名称>",
    "<角色B的规范化名称>"
  ],
  "变化或新增角色": [
    {
        "规范化名称": <角色的规范化名称>,
        "别名": <文本中用于称呼该角色的所有其他名称或代称的列表。如果没有，则为空列表[]>,
        "性别": <角色的性别（男/女）>,
        "年龄": <从“儿童”、“少年”、“青年”、“中年”、“老年”中选择。务必填写声音年龄（如小仙童填“儿童”而非“老年”）>,
        "音高": <高/中/低>,
        "音色质感": <质感型/清亮型/醇正型>,
        "声线密度": <轻柔/适中/强劲>,
        "温度": <偏冷/中性/偏暖>,
        "人物生平": <简洁描述该角色的背景故事、主要经历，确保内容适合儿童理解和接受>,
        "性格特征": <3-6个简洁的气质标签，描述该角色的主要性格特点，确保内容积极向上，适合儿童>,
        "说话语气": <描述该角色的典型说话方式，如“友好且热情”>
    },
    // ... 其他识别出的角色信息 ...
  ]
}
"""
    userPrompt = f"""##原文##
{ori}
##参考数据：已知角色库##
{known_str}
"""
    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2




@retry_on_failure(max_retries=5, delay=10)
def Script_Structure_Planning(ori,storyLine, character):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“剧本编剧（儿童版）”，面向年龄小于12岁儿童的听众。你的任务是基于输入文本、故事线框架，评估文本故事的叙事节奏，识别节奏过慢、冲突不足以及听觉转化困难的部分，并为【每个场景】提供改编建议。
## 2. 分析步骤
1) 基于输入的【原文】与【故事线框架】（包括每个场景的情节节点、核心冲突、关键转折等），评估并分析原著节奏：
   - 扫描输入的文本，标记出节奏过慢的部分（如冗长的景物描写、无关支线、过于复杂的心理描写）。
   - 标记冲突不足的部分（如原著中一笔带过的情节，但有潜力成为戏剧性转折）。
   - 确定听觉转化困难的部分（如复杂的视觉奇观或无声的动作序列）。
2. 对【故事线框架】中的【每个场景】进行改编：
   - 将复杂情节简化为线性、易于理解的因果链，删去所有不适宜儿童的元素，尤其是难以转化为简单冲突的部分（如抽象道德困境、复杂的政治博弈）。
   - 将每个复杂的冲突简化为清晰的基本模式，例如“需要帮助—团结协作—共同克服”。
   - 合并场景：若多个场景具有相似的冲突或情节，考虑合并为一个场景，以提高故事连贯性和节奏。
   - 删除冗长的心理描写或通过对话和简单行动来表达角色的情感和内心活动。
3) 输出改编大纲：
   - 根据输入的【故事线框架】中的【每个场景】，提供详细的改编建议，针对每个节点标明哪些部分需要删减、转化或增强，如何调整节奏，如何处理冲突的表现等。
   - 确保每个冲突模式简化、清晰，能够便于儿童理解，并具备正向价值。
## 3. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "改编大纲": [
    {
      "场景": 1,
      "改编目标": <根据每个场景的需求，提出节奏提升、冲突增强、简化情节等改编目标。>,
      "节奏调整": [
        {
          "部分": <节奏过慢的部分>,
          "调整方式": <如何提升节奏（如剪短对话、增加紧张氛围等）>
        },
        {
          "部分": <冲突不足的部分>,
          "调整方式": <如何增加冲突（如加强人物对话、加入情感冲突等）>
        }
        // ... 其他部分
      ],
      "转化困难的部分": [
        {
          "部分": <听觉转化困难部分>,
          "调整方式": <如何将纯视觉或无声部分转化为旁白或对话描述>
        }
        // ... 其他部分
      ]
    },
    // ... 其他场景的改编内容
  ]
}
"""
    userPrompt = f"""##原文##
    {ori}
    ##故事线框架##
    {storyLine}
    ##角色档案##   
    {character}
    """
    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2
@retry_on_failure(max_retries=5, delay=10)
def Dialogue_Generation(ori, character, storyLine, previous_content=""): 
    try:
        if isinstance(storyLine, str):
            sl_dict = json.loads(storyLine)
        else:
            sl_dict = storyLine
        current_scene_num = sl_dict.get('场景', '当前')
    except:
        current_scene_num = '当前'

    # 1. 构建【剧情状态锁定】指令
    lock_instruction = f"""
## 1.5 【剧情状态锁定】（核心强制约束）
- **当前执行任务**：仅生成【场景 {current_scene_num}】的对白。
- **时间线原则**：你的创作必须严格发生在“上一幕结束”**之后**。
"""

    # 2. 增强上下文衔接逻辑（强化去重）
    context_instruction = ""
    if previous_content:
        context_instruction = f"""
- **【物理与逻辑接力】**：
    以下是上一幕结束时的最后画面/台词（**历史记录，已发生**）：
    --------------------------------------------------
    {previous_content}
    --------------------------------------------------
    **【去重红色警报】**：
    1. 上述内容是**已经完成**的剧情。**绝对禁止**在本场景开头重复描写上述动作或重说上述台词！
    2. **无缝衔接**：你的第一句台词/动作必须是上述画面结束后的**下一个瞬间**（Next Second）。
       - *错误示例*：上一幕结束于“他拔出了剑”。本幕开始写“他手里握着剑，缓缓拔出来……”（这是重复！）
       - *正确示例*：上一幕结束于“他拔出了剑”。本幕开始写“剑锋在月光下闪着寒光，他冷冷地指向前方……”（这是推进！）
"""
    sysPrompt = f"""## 1. 角色
你是一个经验丰富的“剧本编剧（儿童版）”，面向年龄小于12岁儿童的听众。你的任务是根据【原文】、【改编大纲】和【角色档案】生成每个场景中的对话。确保场景与“改编大纲”中的场景一一对应，每个对白具有情感张力和人物特征，并且推动情节发展，不要包含任何旁白内容。
{lock_instruction}
{context_instruction}
## 2. 分析步骤
1) 角色性格与情感分析：
   - 根据【角色档案】，确保对话符合角色的性格特征和情感背景。角色的对白应反映其独特的个性（如勇敢、好奇、害羞等），并传达其内心的情感（如困惑、激动、担心等）。
   - 每个角色的对白应与他们的情感状态一致，并通过简洁的语言表达出来。
2) 情节节点分析：
   - 根据【改编大纲】中的情节节点和冲突，提取出每个场景中需要呈现的核心信息。
   - 对于每个场景，生成相应的对白，确保对话简短、清晰、能够推动情节的进展。
3) 对白生成：
   - 生成每个角色在该场景中的对话，确保对白直接表达角色的目标、情感或行动。
   - **非常重要**：如果一个角色在故事中**伪装**成了另一个角色（比如，孙悟空变成了金角大王），那么当他以伪装身份说话时，输出的“角色”字段**必须**填写**伪装后**的名字（例如，“金角大王”），而不是他本来的名字（“孙悟空”）。这一点对于后续的配音环节至关重要！
   - 每个场景的对白应该包含至少**十轮以上**的互动对话，以展示角色之间的情感波动和互动。
   - 对话内容需要富有情感张力，帮助儿童理解角色的动机和情感变化，避免复杂的词汇和句式。
   - 不要包含任何括号内容，包括但不限于情绪标注、语气动作提示等，只提供纯对话文本。
   - 不要包含任何旁白内容。
4) 符合儿童理解的语言使用：
   - 使用简短、口语化的句子，避免复杂的比喻和隐喻。对话应当易于儿童理解，并且通过重复和简单的句式来强化情节。
   - **【重要强制约束】**：所有输出内容（包括角色名、对白）必须严格使用**简体中文**，严禁出现韩文、日文或其他外文。
   - 确保对白简洁明了，核心信息直接表达。
## 3. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{{
  "场景": {current_scene_num},
  "场景剧本": [
    {{
      "角色": <规范化角色名称，非旁白>,
      "对白": <角色的对话内容，简短、直接、易于理解，突出角色的性格和情感>
    }},
    // ... 更多角色对白
  ]
}}"""
    # userPrompt 不需要动，因为它里面没有大括号格式的 JSON 示例
    userPrompt = f"""##原文##
{ori}
##角色档案##
{character}
##改编大纲##
{storyLine}
"""
    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2




@retry_on_failure(max_retries=5, delay=10)
def Narration_Generation(ori,storyLine,dialogue):
    sysPrompt = """## 1. 角色
你是一个“剧本编剧（儿童版）”，面向年龄小于12岁儿童的听众。你的任务是根据【原文】、【改编大纲】为【对话剧本】中的每个场景补充纯叙述性旁白，使剧情连贯、画面清晰、易于听懂。
## 2. 核心目标
在不修改已有对白的前提下，为每一场景补充纯叙述性旁白，帮助小听众理解故事发展、角色心情和场景转换，使整个剧本连贯、完整、易于听懂。对于每一个你认为需要插入旁白的地方，你都需要提供两条信息：
插入位置： 这段旁白应该插在第几句对话之前？
旁白内容： 你要说的具体内容是什么？
## 3. 要求
1) 审阅每个场景的“对话剧本”与“改编大纲”，只有在对话无法传达关键信息（如动作、场景、内心感受等）时，你才需要介入，
2) 旁白适用场景（仅在这些情况出现时才生成）
   - 场景/时间变化：地点更换、时间跳跃、天气/光线变化影响行动理解。
   - 描述角色动作或表情。
   - 点明角色情绪或内心想法。
   - 补充逻辑衔接。
3) 内容限制：
   - 旁白不复述已在角色对话中清楚表达的内容，且绝不能生成对话。
   - 旁白不得包含任何音效，但可以在旁白中用语言描述听到的声音，以帮助孩子想象画面。
   - 使用简短、清晰、口语化的句子。词汇符合学龄前至小学低年级认知水平。语气亲切、温暖，富有画面感和情感引导力。
4) 确定旁白插入位置，即插在对话**index n**之前，为每个插入点插入旁白，避免重复与过度解释。
5) 合并相同位置的多条旁白，只用一个插入位置。
## 3. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "场景": <场景序号，与输入剧本一致>,
  "旁白内容": [
    {
      "插入位置": <整数，n表示第n条对白之前，对应输入对话中的index>,
      "旁白": <旁白内容>
    },
    // ... 更多旁白
  ]
}"""
    userPrompt = f"""##原文##
{ori}
##改编大纲##
{storyLine}
##对话脚本##
{dialogue}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2
@retry_on_failure(max_retries=5, delay=10)
def Scene_Continuity_Enhancer(storyLine, script): # 函数定义保持和原来完全一样
    """
    一个集成了“滑动窗口”逻辑的场景连续性增强函数。
    它能正确处理 {"剧本": [...]} 格式的字符串输入，并在内部进行分步处理，
    以避免API请求超时。
    """
    
    # 1. 解析输入的巨大字符串
    try:
        data = json.loads(script)
    except json.JSONDecodeError:
        print("[错误] 传入的 'script' 字符串不是有效的JSON格式。")
        return script # 返回原始字符串，避免后续崩溃

    # 2. 正确提取场景列表
    if isinstance(data, dict) and "剧本" in data:
        full_script_list = data["剧本"]
    elif isinstance(data, list):
        full_script_list = data
    else:
        print("[错误] 解析后的脚本不是列表，也不是包含'剧本'键的字典。")
        return script # 返回原始字符串

    if len(full_script_list) < 2:
        print("场景列表中的场景少于2个，无需增强。")
        return data # 返回解析后的原始数据

    print("\n==================== 开始执行场景连续性增强（滑动窗口模式） ====================")
    
    # 3. 将列表中的每个场景（字典）转回JSON字符串，为循环做准备
    enhanced_script_as_strings = [json.dumps(scene, ensure_ascii=False) for scene in full_script_list]

    # 4. 核心逻辑：滑动窗口循环
    for i in range(len(enhanced_script_as_strings) - 1):
        scene_N_content = enhanced_script_as_strings[i]
        scene_N_plus_1_content = enhanced_script_as_strings[i+1]
        
        try:
            current_scene_number = json.loads(scene_N_content).get('场景', i + 1)
            next_scene_number = json.loads(scene_N_plus_1_content).get('场景', i + 2)
        except:
            current_scene_number = i + 1
            next_scene_number = i + 2
        
        print(f"\n--- 正在审查 场景 {current_scene_number} 和 场景 {next_scene_number} 的衔接... ---")

        # 5. 准备本次小任务的 SysPrompt 和 UserPrompt
        sysPrompt_for_pair = """## 1. 角色
你是一位经验极其丰富的“儿童剧本连续性总监”。你的核心职责是像鹰眼一样审查任何剧本，确保故事在逻辑、角色状态和时空上没有任何断裂。
## 2. 核心目标
你必须严格地、按顺序地审查每一对相邻的场景。对于从“场景 N”到“场景 N+1”的每一次过渡，你必须强制执行以下【三项】核心检查：

### **第一项：情感与叙事连贯性检查 (最高优先级)**
1.  **分析场景 N 结尾**: 在场景 N 的结尾，核心角色的“情感状态”和“叙事目标”是什么？
    *   **情感状态**: 他们是愤怒、悲伤、困惑，还是刚刚达成和解？（例如：男主角【因误会而愤怒地离开】）
    *   **叙事目标/悬念**: 他们正要去哪里？他们刚刚做出了什么决定？留下了什么悬念？（例如：女主角【决定去寻找真相】）

2.  **分析场景 N+1 开头**: 在场景 N+1 的开头，这些角色的状态又是什么？
    *   **情感状态**: 他们的情绪是否延续了上一场戏？（例如：男主角【出现在朋友家，依然心烦意乱】）
    *   **叙事进展**: 剧情是否在逻辑上推进了？（例如：女主角【出现在图书馆，开始查资料】）

3.  **【核心逻辑判断】**: 两个场景的情感和叙事是否存在“断层”？
    *   **提问**: “一个在场景 N 结尾【愤怒离开】的角色，为什么在场景 N+1 的开头【突然心情平静地在喝咖啡】？中间的情绪转折被吞掉了，观众会感到困惑！”

4.  **【强制修正】**: 如果发现这种“断层”，你【必须】重写场景 N+1 的开头（或 N 的结尾），以搭建“情感桥梁”。
    *   **修正方法**: 增加必要的台词或旁白来解释状态的变化。例如，在上述案例中，可以在 N+1 的开头加入旁白：“一夜过后，愤怒渐渐被冷静取代，他知道自己需要一个答案。”

### **第二项：搭建“叙事桥梁”（做加法）**
*   **审查**: 角色从一个地点/时间跳到另一个，过程是否模糊不清？
*   **行动**: 如果过程不清晰，【必须】在 N 的结尾或 N+1 的开头增加“桥梁式”的台词或旁白来解释。例如：“我们去天台说。” 或 “第二天，学校的公告栏前...”

### **第三项：消除“信息回声”（做减法）**
*   **审查**: N+1 的开头是否在用不同的话重复 N 结尾已经讲明白的事？
*   **行动**: 如果是，【必须】果断删除或改写重复内容。保持青少年剧本快节奏、不拖沓的特点。

## 3. 要求
- **情感逻辑至上**: 保证角色的行为和情绪转变符合逻辑，是你的首要目标。
- **节奏为王**: 为了保持紧凑的节奏和悬念，你有权对场景的开头和结尾进行大刀阔斧的增、删、改。
- **忠于大纲**: 修正逻辑错误的同时，不能改变故事的核心走向和人物设定。
- **格式一致**: 必须严格按照输入的JSON格式，输出你修改后的【完整剧本】。
- **【重要强制约束】纯净输出**: 你输出的“内容”字段必须是纯净的台词或旁白文本。**严禁**包含【桥梁】、【新增】、【修改】等任何标签或括号说明！
## 4. 输出格式
请严格按照以下JSON格式输出你对【当前这两个场景】的修订结果：
{
  "修订后的一对场景": [
    { "场景描述": "这是对场景N的修订版本", "修订内容": {/* JSON object for Scene N */} },
    { "场景描述": "这是对场景N+1的修订版本", "修订内容": {/* JSON object for Scene N+1 */} }
  ]
}
"""
        userPrompt_for_pair = f"""## 改编大纲 ##
{storyLine}

## 待优化剧本（一对相邻场景） ##
请严格审查并修正以下【相邻的两个场景】，确保它们之间的过渡完美无缺。

### 场景 N (当前场景: {current_scene_number}) ###
{scene_N_content}

### 场景 N+1 (下一个场景: {next_scene_number}) ###
{scene_N_plus_1_content}
"""

        # 6. 调用AI进行处理
    try:
        ai_response = Gemini_Generate_Json(userPrompt_for_pair, sysPrompt_for_pair)
            
        corrected_pair = ai_response["修订后的一对场景"]
            
            # 7. 用AI修正过的场景内容，替换掉我们列表中的JSON字符串
        enhanced_script_as_strings[i] = json.dumps(corrected_pair[0]["修订内容"], ensure_ascii=False)
        enhanced_script_as_strings[i+1] = json.dumps(corrected_pair[1]["修订内容"], ensure_ascii=False)

        print(f"场景 {current_scene_number} 和 {next_scene_number} 衔接增强完毕！")

    except Exception as e:
        print(f"[警告] 处理场景 {current_scene_number} 和 {next_scene_number} 时发生错误: {e}")
        pass

    time.sleep(1)

    print("\n==================== 所有场景连续性增强完成！ ====================")
    
    # 8. 将所有修正后的JSON字符串转回Python字典对象
    final_script_objects = [json.loads(scene_str) for scene_str in enhanced_script_as_strings]
    
    # 9. **关键**：按照您原来的外部输出格式，将最终的完整剧本包裹在一个 "剧本" 键中返回
    final_output = {"剧本": final_script_objects}
    
    # 打印最终结果，确认格式正确
    # print(json.dumps(final_output, ensure_ascii=False, indent=2)) 
    
    return final_output



@retry_on_failure(max_retries=5, delay=10)
def Conflict_Escalation(storyLine,character,script):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“剧本编剧（儿童版）”，面向年龄小于12岁儿童的听众。你的任务是分析当前的剧本，找出情感对立不足的段落，对对白进行改写或者补充，以增强每个场景中的情感冲突，使其更具戏剧张力和情绪吸引力。
## 2. 核心约束（强制执行）
 **角色白名单制度**：
   - **绝对禁止创造任何新角色**。
   - 剧本中出现的每一个角色（包括背景音、路人、对话者），必须严格存在于下方的【角色档案】中。
   - 如果你想通过“商人”或“官员”的对话来增强冲突，但【角色档案】中没有这些角色，你**绝对不能**添加他们。
   - 你只能利用【角色档案】中已有的角色进行互动、争论或对峙
## 3. 增强原则
1) 冲突类型简化： 
   - 将模糊或内隐的矛盾转化为清晰的对错等儿童可理解的对立。
   - 避免复杂心理博弈、背叛、长期仇恨或不可解的困境。
2) 情感表达直接化： 
   - 角色应明确说出自己的感受，而非含蓄暗示。
   - 对抗双方的情绪要鲜明但不过激（如着急、委屈、坚定，而非愤怒、仇恨、绝望）。
3) 冲突必须在当场景中解决： 
   - 每一幕的冲突需在该幕结尾前得到化解、和解或正向转折。
   - 解决方式应体现合作、理解、勇气、分享或成长。
4) 安全边界： 
   - 不制造持续恐惧、孤立感或无力感。
   - 即使有“反面”情绪，也要迅速导向被接纳、被帮助或自我克服。
## 4. 操作方式 
若原对白/旁白中冲突微弱或缺失，在不改变核心情节和结局的前提下，通过以下方式增强：
   - 让角色更明确地表达需求或不满；
   - 增加一句简短但有力的对抗性对白；
   - 通过简短、口语化的对白增强张力：加入“疑问—分歧—边界—提议—同意/修复”的对话节拍。
   - 调整旁白以突出情绪对比（如“孙悟空很想答应，可心里又有点不甘心”）；
   - 禁止添加新角色或改变故事走向，添加的对白角色需要为**规范化角色名称**。
## 5. 输出格式
请严格按照以下JSON格式输出**增强后**的剧本，确保结构清晰：
{
  "场景": <场景序号，与输入剧本一致>,
  "场景剧本": [
    {
      "角色": <规范化角色名称>,
      "内容": <角色的对话内容，简短、直接、易于理解，突出角色的性格和情感>
    },
    // ... 更多剧本内容
  ]
}"""
    userPrompt = f"""
##角色档案##
{character}
##剧本##
{script}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Proofreader(ori,storyLine,script, character):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本审校专家（儿童版）。你的任务是审阅输入的每个场景的剧本，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。若全部达标，则给出通过与移交提示。
## 2. 核心约束（最高优先级 - 覆盖大纲要求）
**角色名法律**：
1. **【角色档案】是最高法律**：剧本中的角色名必须严格与【角色档案】一致。
2. **豁免权**：如果【改编大纲】要求修改名字（例如“把十殿阎王改为管理者”），但剧本依然使用了【角色档案】中的原名（“十殿阎王”），**这不算错误，不需要修改**！
3. **判定逻辑**：
   - 剧本用名 == 角色档案原名 -> **通过**（无论大纲说什么）。
   - 剧本用名 != 角色档案原名 -> **需修改**。
## 3. 审查清单
A. 目标一致性
  - 场景是否实现既定目标（信息达成、节奏、转折、收束）？
B. 信息平衡
  - 旁白是否仅用于补充画面、情绪或逻辑衔接，而非重复对白内容？
  - 对白是否承担角色性格表达与情节推进，而非堆砌说明性语言？
  - 是否存在关键信息缺失（如角色动机不明）或冗余（如旁白解释角色已说清的内容）？
C. 角色一致性
  - 语气、词汇与性格是否匹配？是否出现越界用语（成人化、尖刻讥讽等）？
  - 称谓、关系、动机是否前后自洽？
D. 受众适宜性
  - 语言：语言是否简单、口语化、无生僻词？避免隐晦暗示与复杂比喻。
  - 强度：张力适中、无恐吓/羞辱/暴力/死亡直述；情绪冲突可理解且可修复。
  - 复杂度：因果链线性清晰；每场景至少 十 轮交互；
  - 风格：积极、合作导向；结尾给清晰反馈。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "审查结果": "通过|需修改",
  "问题清单": [    // 若审查结果为"通过"，则为[]
    {
      "维度": <目标一致性|信息平衡|角色一致性|受众适宜性>,
      "问题描述": <具体、客观的问题说明>,
      "修改建议": <明确、具体的修改指令（怎么改以满足要求）>
    },
    // ... 其他问题清单
  ]
}"""
    userPrompt = f"""##原文##
{ori}
##角色档案（最高准则 - 名字必须完全匹配这里）##
{character}
##改编大纲##
{storyLine}
##剧本##
{script}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Script_Revision(ori,storyLine,script,feedback):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本修订专家（儿童版）。你的任务是根据给出的审查结果，对剧本执行必要修正。你不得改写剧情走向、添加新线索/新角色；只在需要时对对白/旁白做删改或插入。

## 2. 修订原则
仅针对问题清单逐条修复：
   - 仅修改被指出的问题，绝不优化未提及部分。
   - 严格遵循修改建议中的指令。
   - 用常用词与简单词汇；移除成人化、恐吓、讥讽；
   - 不引入暴力/死亡/惊吓直述；不新增人物/道具/线索；不改变已定因果、结局。
   - **【重要强制约束】**：修订后的内容必须严格使用**简体中文**。
## 3. 输出格式
请严格按照以下JSON格式输出**修订后**的剧本，确保结构清晰：
{
  "场景": <场景序号，与输入剧本一致>,
  "场景剧本": [
    {
      "角色": <规范化角色名称>,
      "内容": <角色的对话内容，简短、直接、易于理解，突出角色的性格和情感>
    },
    // ... 更多剧本内容
  ]
}"""
    userPrompt = f"""##原文
{ori}
##改编大纲##
{storyLine}
##剧本##
{script}
##审查结果
{feedback}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Emotional_Guidance(character, script):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本配音导演（儿童版），面向3-8岁的小朋友听众。你的任务是根据“角色档案”和每句剧本内容，为每句台词添加情感标签，并根据情感分析调整语气，给声音演员提供明确的演绎指导，助配音演员们创造出能让小朋友喜欢的、 富有魅力的角色声音。
## 2. 核心任务
你的任务是为剧本中的每一句台词（包括旁白）添加详细的“语气指导”，你需要:
1) 深入理解台词在当前情境下的核心情感。你需要考虑说话者的性格、他正在经历的事情以及他想达成的目的。
2) 将你分析出的情感，翻译成配音演员能够理解和执行的语气指导，包括语气、语调和情绪状态描述。
## 3. 要求
1) 情感表达应 清晰、直接、充满表现力，可以体现出比如 开心、好奇、惊讶、难过、勇敢 等小朋友容易理解的情绪。
2) 对于每个角色，语气指导应完全服务于其性格。确保角色的情感与语气一致，准确传达他们的内心活动和意图。
3) 对于旁白，情感应体现“故事大王” 的亲切感，语速相对平稳、友好，并为整体情节提供 清晰的情感引导。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "场景": <场景序号，与输入剧本一致>,
  "场景剧本": [
    {
      "台词位置": <n表示第n条台词，对应输入剧本中的index>,
      "语气指导": <简要描述情绪状态>
    },
    // ... 更多剧本内容
  ]
}
"""

    userPrompt = f"""##角色档案##
{character}

##剧本##
{script}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    
    try:
        # 确保 output2 是字典（防止返回非字典类型）
        if isinstance(output2, dict):
            # 遍历场景剧本中的每一条台词
            for item in output2.get("场景剧本", []):
                # 检查是否有繁体"语气指導"，有则替换为简体"语气指导"
                if "语气指導" in item:
                    item["语气指导"] = item.pop("语气指導")
            # 若后续需要JSON字符串，再序列化（根据你的代码逻辑决定是否保留）
            # output2 = json.dumps(output2, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"修正语气指导字段时出错: {e}")
    
    return output2



@retry_on_failure(max_retries=5, delay=10)
def Final_Proofreader(character,script):
    sysPrompt = """## 1. 角色
你是一名经验丰富的儿童音频内容总编辑。你的任务是对最终合并的剧本（包含角色、内容、语气指导）进行质量检查，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。

## 2. 审查清单
1) 连贯性：
   - 检查每个场景的对白和旁白是否流畅自然。是否有对白跳跃或情感转折过于突兀的地方？
   - 检查是否有重复信息、无关情节或过于复杂的转折。
2) 情感表达：
   - 对照每个角色的情感标签，确认其情感表达是否与角色性格一致，且符合情节发展。
   - 检查语气指导是否合适，尤其是在关键情节中的情感表达，是否能清晰传达角色的内心世界。
## 3. 剧本要求
1) 语言简明：使用常用、简单词、；无生僻/隐晦表达。
2) 对白与旁白中严禁出现任何拟声词、音效与舞台指令，只能用纯叙述性表达。
3) 不出现暴力/死亡直述、恐吓、羞辱、粗口。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "审查结果": "通过|需修改",
  "问题清单": [    // 若审查结果为"通过"，则为[]
    {
      "维度": <连贯性|情感表达>,
      "问题描述": <具体、客观的问题说明>,
      "修改建议": <明确、具体的修改指令（怎么改以满足要求）>
    },
    // ... 其他问题清单
  ]
}"""
    userPrompt = f"""##角色档案##
{character}
##剧本##
{script}"""

    #output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2
def get_latest_voice_from_history(role_name, global_history):
    """
    从全局历史中倒序查找该角色最近一次使用的音色和当时的年龄
    返回: (voice_id, age_at_that_time) 或 (None, None)
    """
    if not global_history:
        return None, None
        
    # 按章节号倒序排列 (如 [10, 9, 8...])
    sorted_chapters = sorted([int(k) for k in global_history.keys()], reverse=True)
    
    for chap in sorted_chapters:
        char_list = global_history[str(chap)]
        for char_data in char_list:
            # 找到名字匹配，且该记录里必须包含"配对声音"字段
            if char_data.get("规范化名称") == role_name and "配对声音" in char_data:
                return char_data["配对声音"], char_data.get("年龄")
                
    return None, None
@retry_on_failure(max_retries=5, delay=10)
def Role_Voice_Map(nameJson, script, global_history=None): 
    print("\n--- 开始进行角色音色自动匹配 (V3.0 继承+防撞车版) ---")

    all_roles = nameJson.get("全部角色", [])
    
    # 补全旁白
    has_narrator = any(r['规范化名称'] == '旁白' for r in all_roles)
    if not has_narrator:
        all_roles.append({"规范化名称": "旁白", "性别": "男", "年龄": "中年"})

    # 加载音色库
    try:
        json_path = r'/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/AGENT_JWDS-master/Voices/merged_lol_data_xiyou_1028.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            voice_library_json = json.load(f)
    except Exception as e:
        print(f"错误：声音库加载失败: {e}")
        return {'角色声音配对': []}

    final_result_list = []
    used_voices = set() # 核心：已占用音色池
        # key: role_name, value: result_dict
    temp_results = {}
    
    for role in all_roles:
        name = role.get("规范化名称")
        current_age = role.get("年龄", "中年")
        
        # 旁白特例
        if name == "旁白":
            voice_id = "男_中年_中_醇正型_适中_中性_03"
            temp_results[name] = {
                "角色名称": name, "配对声音": voice_id, "理由": "旁白强制指定"
            }
            used_voices.add(voice_id)
            continue
            
        # 查历史
        hist_voice, hist_age = get_latest_voice_from_history(name, global_history)
        
        # 继承判定：
        # 1. 历史有记录
        # 2. 年龄没变
        # 3. 这个音色没有被“旁白”或者“前一个继承者”占用 (防撞车)
        if hist_voice and hist_age == current_age:
            if hist_voice not in used_voices:
                print(f"  [继承] {name}: 完美继承上一章音色 {hist_voice}")
                temp_results[name] = {
                    "角色名称": name,
                    "配对声音": hist_voice,
                    "理由": f"继承自历史记录（年龄 {current_age} 未变）"
                }
                used_voices.add(hist_voice) # 锁死该音色
            else:
                print(f"  [冲突] {name}: 历史音色 {hist_voice} 已被占用，将被迫重新匹配。")
        elif hist_voice and hist_age != current_age:
             print(f"  [变化] {name}: 年龄变化 ({hist_age}->{current_age})，放弃继承。")

    for role in all_roles:
        name = role.get("规范化名称")
        
        # 如果第一轮已经处理过了，直接跳过
        if name in temp_results:
            continue
            
        # 开始匹配新音色
        current_age = role.get("年龄", "中年")
        target_tags = {
            "性别": role.get("性别", "男"),
            "年龄": current_age,
            "音高": role.get("音高", "中"),
            "音色质感": role.get("音色质感", "醇正型"),
            "声线密度": role.get("声线密度", "适中"),
            "温度": role.get("温度", "中性")
        }
        
        # 关键：传入 used_voices，告诉算法这些音色不能选！
        matched_id, note = smart_match_voice(target_tags, voice_library_json, exclude_voices=used_voices)
        
        if matched_id:
            used_voices.add(matched_id) # 立即标记为已用，防止同章内下一个新角色撞车
            reason = f"自动匹配 [{matched_id}] (排除已用: {len(used_voices)}个)"
        else:
            # 极低概率兜底
            matched_id = "男_青年_中_质感型_适中_中性_03" 
            reason = "无匹配，使用兜底"
            
        print(f"  [新配] {name}: {matched_id}")
        temp_results[name] = {
            "角色名称": name,
            "配对声音": matched_id,
            "理由": reason
        }

    for role in all_roles:
        name = role.get("规范化名称")
        if name in temp_results:
            final_result_list.append(temp_results[name])
            
    return {'角色声音配对': final_result_list}


def dialogue_to_annotated_string(dialogue):
    script_lines = []
    script_lines.append('{')
    script_lines.append('  "剧本": [')
    for scene_idx, scene in enumerate(dialogue["剧本"]):
        script_lines.append('    {')
        script_lines.append(f'      "场景": {scene["场景"]},')
        script_lines.append('      "场景剧本": [')

        for i, line in enumerate(scene["场景剧本"]):
            # 转义双引号以防破坏 JSON-like 结构（虽然不是严格 JSON）
            role = line["角色"].replace('"', '\\"')
            dialogue_text = line["对白"].replace('"', '\\"')
            line_str = f'        {{"角色": "{role}", "对白": "{dialogue_text}"}}  // index {i}'
            script_lines.append(line_str)

        script_lines.append('      ]')
        script_lines.append('    }' + (',' if scene_idx < len(dialogue["剧本"]) - 1 else ''))

    script_lines.append('  ]')
    script_lines.append('}')

    return '\n'.join(script_lines)

def script_to_annotated_string_by_scene(script):
    script_lines = []
    script_lines.append('    {')
    script_lines.append(f'      "场景": {script["场景"]},')
    script_lines.append('      "场景剧本": [')

    for i, line in enumerate(script["场景剧本"]):
        role = line["角色"].replace('"', '\\"')
        dialogue_text = line["内容"].replace('"', '\\"')
        line_str = f'        {{"角色": "{role}", "内容": "{dialogue_text}"}}  // index {i}'
        script_lines.append(line_str)

    script_lines.append('      ]')
    script_lines.append('    }')
    return '\n'.join(script_lines)

def dialogue_to_annotated_string_by_scene(dialogue):
    script_lines = []
    script_lines.append('    {')
    script_lines.append(f'      "场景": {dialogue["场景"]},')
    script_lines.append('      "场景剧本": [')

    for i, line in enumerate(dialogue["场景剧本"]):
        # 转义双引号以防破坏 JSON-like 结构（虽然不是严格 JSON）
        role = line["角色"].replace('"', '\\"')
        dialogue_text = line["对白"].replace('"', '\\"')
        line_str = f'        {{"角色": "{role}", "对白": "{dialogue_text}"}}  // index {i}'
        script_lines.append(line_str)

    script_lines.append('      ]')
    script_lines.append('    }')
    return '\n'.join(script_lines)

def combine_dialogue_and_narration(dialogue,narration):
    # 构建 narration 按场景号索引的字典
    narration_by_scene = {}
    for item in narration["剧本"]:
        narration_by_scene[item["场景"]] = item["旁白内容"]

    merged_script = []

    for scene_data in dialogue["剧本"]:
        scene_num = scene_data["场景"]
        dialogues = scene_data["场景剧本"]
        narrations = narration_by_scene.get(scene_num, [])

        # 按插入位置排序旁白（确保顺序正确）
        narrations_sorted = sorted(narrations, key=lambda x: x["插入位置"])

        # 构建插入映射：位置 -> 旁白列表（支持多个旁白在同一位置）

        insert_map = defaultdict(list)
        for nar in narrations_sorted:
            insert_map[nar["插入位置"]].append(nar["旁白"])

        # 合并
        merged_lines = []
        for idx, line in enumerate(dialogues):
            # 如果当前位置有旁白，先插入所有旁白
            if idx in insert_map:
                for nar_text in insert_map[idx]:
                    merged_lines.append({"角色": "旁白", "内容": nar_text})
            # 再插入对话
            merged_lines.append({"角色": line["角色"], "内容": line["对白"]})

        # 处理插入位置超出对话长度的情况（比如插在最后）
        max_dialogue_index = len(dialogues)
        for pos in insert_map:
            if pos >= max_dialogue_index:
                for nar_text in insert_map[pos]:
                    merged_lines.append({"类型": "旁白", "内容": nar_text})

        merged_script.append({
            "场景": scene_num,
            "场景剧本": merged_lines
        })

    return {"剧本": merged_script}

def combine_script_and_emotion(script,emotion):
    # 构建 narration 按场景号索引的字典
    script_map = {scene['场景']: scene for scene in script['剧本']}

    # 步骤 2: 遍历所有的语气标注信息
    # 使用 .get('语气标注', []) 来安全地获取列表，如果键不存在则返回空列表
    for scene_annotation in emotion.get('语气标注', []):
        scene_num = scene_annotation.get('场景')

        # 查找对应的场景剧本
        target_scene = script_map.get(scene_num)

        # 如果找不到对应的场景，打印警告并跳过
        if not target_scene:
            print(f"警告: 在剧本中找不到场景 {scene_num}，跳过此场景的语气标注。")
            continue

        # 步骤 3: 遍历单个场景内的所有台词标注
        for line_annotation in scene_annotation.get('场景剧本', []):
            position = line_annotation.get('台词位置')
            guidance = line_annotation.get('语气指导')

            # 检查必要信息是否存在
            if position is None or guidance is None:
                print(f"警告: 场景 {scene_num} 中有一条标注信息不完整，已跳过。")
                continue

            # 步骤 4: 更新原始剧本
            # 检查台词位置是否有效，防止索引越界错误
            if 0 <= position < len(target_scene['场景剧本']):
                # 在对应的台词字典中添加 '语气指导' 键值对
                target_scene['场景剧本'][position]['语气指导'] = guidance
            else:
                print(f"警告: 场景 {scene_num} 的台词位置 {position} 超出范围，跳过此条标注。")

    return script



def remove_parentheses_in_script(data):
    """
    递归遍历一个数据结构（列表或字典），移除所有字符串中的括号内容。
    """
    if isinstance(data, dict):
        # 如果是字典，遍历其键值对，并对值进行递归处理
        return {key: remove_parentheses_in_script(value) for key, value in data.items()}
    elif isinstance(data, list):
        # 如果是列表，遍历其元素，并对每个元素进行递归处理
        return [remove_parentheses_in_script(item) for item in data]
    elif isinstance(data, str):
        # 如果是字符串，使用正则表达式移除括号及其内容
        # r'\(.*?\)|（.*?）' 匹配半角()和全角（）及其中的任意内容（非贪婪模式）
        # .strip() 用于移除替换后可能留下的前后空格
        return re.sub(r'\(.*?\)|（.*?）', '', data).strip()
    else:
        # 如果是其他类型（如数字），保持原样返回
        return data

def extract_character_profiles(script_data, character_database):
    """
    从剧本中提取角色，并匹配其在角色档案中的完整资料。
    :param script_data: 包含剧本信息的字典。
    :param character_database: 包含所有角色档案的字典。
    :return: 一个字典，键是剧本中的角色名，值是对应的角色档案。如果找不到则为None。
    """

    # --- 步骤 1: 创建一个高效的角色查找映射表 ---
    # 为了能快速通过“规范化名称”或“别名”找到角色档案，我们先预处理角色数据库。
    # 创建一个字典，key是各种名称，value是完整的角色档案。
    character_lookup_map = {}
    # 检查"全部角色"键是否存在，避免出错
    all_characters = character_database.get("全部角色", [])

    for profile in all_characters:
        # 添加规范化名称到映射表
        if "规范化名称" in profile:
            normalized_name = profile["规范化名称"]
            character_lookup_map[normalized_name] = profile

        # 添加所有别名到映射表
        if "别名" in profile:
            for alias in profile["别名"]:
                character_lookup_map[alias] = profile

    # --- 步骤 2: 从剧本中获取所有不重复的角色 ---
    # 使用集合(set)可以自动去除重复的角色名
    script_characters = set()

    # 检查"场景剧本"键是否存在
    scene_script = script_data.get('场景剧本', [])

    for line in scene_script:
        if "角色" in line:
            script_characters.add(line['角色'])

    # --- 步骤 3: 匹配剧本角色和档案，并生成结果 ---
    matched_profiles = {}
    for character_name in script_characters:
        # 使用.get()方法从映射表中查找角色。
        # 如果找到，返回角色档案；如果找不到（比如“旁白”、“猴子们”），返回None。
        found_profile = character_lookup_map.get(character_name)
        if found_profile:
            matched_profiles[character_name] = found_profile

    return matched_profiles

def normalize_script_characters(script_data, character_list):
    """
    根据角色列表，将剧本中的角色名称规范化。
    它会遍历剧本中的每一句台词，将别名替换为规范化名称。

    :param script_data: 包含'剧本'键的原始剧本数据字典。
    :param character_list: 包含角色规范化名称和别名的列表。
    :return: 角色名称被规范化后的剧本数据字典。
    """
    # 1. 创建一个从别名到规范化名称的映射字典，以提高查找效率
    # 例如: {"美猴王": "孙悟空", "石猴": "孙悟空", "孙悟空": "孙悟空"}
    name_map = {}
    for char_info in character_list:
        normalized_name = char_info.get("规范化名称")
        if not normalized_name:
            continue

        # 将规范化名称本身也添加到映射中
        name_map[normalized_name] = normalized_name

        # 将所有别名都映射到规范化名称
        for alias in char_info.get("别名", []):
            name_map[alias] = normalized_name

    # 2. 遍历剧本的每个场景和每句台词
    for scene in script_data.get('剧本', []):
        for line in scene.get('场景剧本', []):
            original_name = line.get('角色')
            if original_name:
                # 3. 使用映射查找规范化名称。如果找不到，则保留原始名称
                # .get(key, default) 方法在这里非常适用
                line['角色'] = name_map.get(original_name, original_name)
    return script_data


if __name__ == "__main__":
    ori_path = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/sanguoyanyi/第十二回 千里走单骑.txt"
    with open(ori_path, 'r', encoding='utf-8') as f:
        ori = f.read()

    # 生成概要和故事线框架
    # output = Extraction_Summary(ori)
    story_line_gemini = {
        "章节核心概要": "一个从石头里蹦出来的神奇猴子，和伙伴们找到了一个叫“水帘洞”的快乐家园，并成为了猴王。但他担心快乐的日子会结束，于是他离开家去寻找能永远年轻快乐的秘密。他找到了一位神奇的老师，学会了七十二种变化和能飞得很快的筋斗云。但因为他忍不住向朋友们炫耀魔法，老师让他回到了自己的家——花果山。",
        "故事线框架": [
            {
                "场景": 1,
                "情节节点": "在一座神奇的花果山上，一块仙石裂开，蹦出了一只石猴。石猴和山里的猴子们一起玩耍时，大家发现了一个大瀑布，并约定谁敢跳进去再安全出来，谁就是大王。石猴勇敢地跳了进去，发现瀑布后面是一个又大又漂亮的洞府，叫做“水帘洞”。他带领所有猴子住了进去，成为了“美猴王”。",
                "核心冲突": "猴子们想要一个勇敢的领袖和一个安全又舒适的家。",
                "关键转折": "石猴接受了挑战，第一个勇敢地跳进了神秘的大瀑布。"
            },
            {
                "场景": 2,
                "情节节点": "虽然每天都很快乐，但猴王突然开始担心，怕大家老了以后就不能再一起玩耍了。一只聪明的通臂猿猴告诉他，世界上有神仙，他们知道永远年轻快乐的秘密。于是，猴王决定告别大家，独自乘着小木筏出海，去寻找神仙。",
                "核心冲突": "猴王害怕快乐的时光会因为变老而结束，他想找到一个永远快乐的办法。",
                "关键转折": "猴王从一只老猴子那里听说了“神仙”的存在，这给了他新的希望和目标。"
            },
            {
                "场景": 3,
                "情节节点": "猴王旅行了很多年，终于在一位善良的樵夫指引下，找到了一座叫“灵台方寸山”的仙山。山里有一个“斜月三星洞”，住着一位法力高强的老师傅——菩提祖师。老师傅很喜欢这个聪明的石猴，给他取了一个新名字，叫“孙悟空”。",
                "核心冲突": "寻找神仙的路非常遥远和困难，孙悟空需要找到正确的人来教他本领。",
                "关键转折": "一位樵夫唱的歌，为孙悟空指明了去见神仙老师的道路。"
            },
            {
                "场景": 4,
                "情节节点": "老师傅想考验孙悟空，假装生气地用戒尺在他头上敲了三下。孙悟空猜到了这是个谜题，意思是让他半夜三更从后门去找老师。老师傅非常高兴，就把长生不老的口诀、七十二般变化和一下能飞十万八千里的“筋斗云”都偷偷地教给了他。",
                "核心冲突": "孙悟空需要证明自己足够聪明和有决心，才能学到真正的神仙法术。",
                "关键转折": "孙悟空成功解开了老师傅的谜题，获得了学习最高级法术的秘密机会。"
            },
            {
                "场景": 5,
                "情节节点": "有一天，孙悟空在朋友们面前炫耀，把自己变成了一棵高大的松树，引来了大家的欢呼。吵闹声惊动了老师傅，他批评孙悟空不应该随便炫耀本领，因为这会引来麻烦。为了保护孙悟空，老师傅让他立刻回家，并且不许告诉任何人他是自己的徒弟。孙悟空只好拜别师父，一个筋斗云飞回了花果山。",
                "核心冲突": "孙悟空的骄傲和爱炫耀的性格，与师父要求的谦虚和保密产生了矛盾。",
                "关键转折": "因为在大家面前炫耀变身术，孙悟空被师父赶走，结束了他的学习生涯，但也因此带着一身本领回到了家乡。"
            }
        ]
    }

    # 生成角色档案
    # output = Extraction_Characters(ori)
    # 将json添加到json文件中，key为“Extraction_Summary”值为output
    character_gemini = {
        "全部角色": [
            {
            "规范化名称": "盘古",
            "别名": "无",
            "性别": "男",
            "年龄": "老年",
            "音高": "低",
            "音色质感": "质感型",
            "声线密度": "强劲",
            "温度": "中性",
            "人物生平": "在很久很久以前，天地还是一片混沌的时候，伟大的盘古挥动巨斧，劈开了天地。从此，轻的东西飘上去变成了天空，重的东西沉下来变成了大地，世界才有了现在的模样。",
            "性格特征": "创世者、力量巨大、远古的、开天辟地",
            "说话语气": "无台词。可以想象他的声音如同雷鸣和山崩，充满了开天辟地的力量，每一个字都带着宇宙初开的混响。"
        },
        {
            "规范化名称": "孙悟空",
            "别名": "石猴, 美猴王, 千岁大王, 猢狲",
            "性别": "男",
            "年龄": "青年",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "强劲",
            "温度": "偏暖",
            "人物生平": "由花果山顶的一块仙石吸收日月精华后诞生的小石猴。他非常勇敢，第一个跳进瀑布，为大家找到了水帘洞这个新家，因此被猴群拥戴为“美猴王”。为了让大家都能长生不老，他独自漂洋过海，拜须菩提祖师为师，学会了七十二般变化和能飞十万八千里的筋斗云，并得到了“孙悟空”这个名字。",
            "性格特征": "勇敢无畏、天真好奇、聪明机灵、渴望自由、追求强大、有领导力",
            "说话语气": "语速快，充满活力和好奇心。开心时会大声欢笑，着急时会大喊大叫，说话非常直接坦率，有时会带点小顽皮和喜欢炫耀自己本领的劲头。"
        },
        {
            "规范化名称": "玉皇大帝",
            "别名": "玉帝",
            "性别": "男",
            "年龄": "中年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "天庭的最高统治者，掌管着天上和人间的一切。当石猴出生时，他被石猴眼中射出的金光惊动，但听了手下神将的报告后，认为这只是天地间的自然现象，并没有过多干预。",
            "性格特征": "位高权重、处变不惊、沉稳、有威严",
            "说话语气": "沉稳、威严、不疾不徐，带着一种君临天下的气度，言语简洁但充满权威感，对小事显得宽容大度。"
        },
        {
            "规范化名称": "千里眼",
            "别名": "二将之一",
            "性别": "男",
            "年龄": "青年",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "玉皇大帝手下的一位神将，拥有一双能看到千里之外事物的神奇眼睛。他奉玉帝之命，和顺风耳一起前往南天门，查明天地间发生异动的来源。",
            "性格特征": "忠诚、尽职、观察敏锐",
            "说话语气": "作为神将，汇报工作时声音清晰、洪亮，吐字清楚，语速稍快，体现出他高效和敏锐的特点。"
        },
        {
            "规范化名称": "顺风耳",
            "别名": "二将之一",
            "性别": "男",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "玉皇大帝手下的一位神将，拥有一双能听到极远处声音的神奇耳朵。他奉玉帝之命，和千里眼一起查探异动，并向玉帝汇报了石猴出世的情况。",
            "性格特征": "忠诚、尽职、听觉灵敏",
            "说话语气": "作为神将，声音沉着，语速平稳，汇报时条理清晰，给人一种可靠、善于倾听的感觉。"
        },
        {
            "规范化名称": "群猴",
            "别名": "众猴, 小猴子们",
            "性别": "男女混合",
            "年龄": "儿童",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "轻柔",
            "温度": "偏暖",
            "人物生平": "花果山上的普通猴子，它们每天一起玩耍，一起生活。在石猴勇敢地闯入水帘洞后，它们信守承诺，尊石猴为“千岁大王”。它们非常爱戴猴王，会为猴王的烦恼而一起难过。",
            "性格特征": "天真活泼、信守承诺、崇拜英雄、容易情绪化",
            "说话语气": "说话时总是七嘴八舌，声音嘈杂但充满活力，像一群快乐的小朋友。语气非常直接，开心时一起欢呼，害怕时一起哭泣，情绪来得快去得也快。"
        },
        {
            "规范化名称": "通背猿猴",
            "别名": "猿猴",
            "性别": "男",
            "年龄": "老年",
            "音高": "低",
            "音色质感": "质感型",
            "声线密度": "轻柔",
            "温度": "偏暖",
            "人物生平": "猴群中的一位老猴子，非常有见识。在美猴王为生老病死而烦恼时，他站出来指点迷津，告诉猴王世界上有佛、仙、神圣这三种人可以跳出轮回、长生不老，从而激励了猴王出海寻仙。",
            "性格特征": "见多识广、智慧、沉稳、善于引导",
            "说话语气": "说话缓慢而清晰，声音不高但很有分量，带着一种长者的智慧和慈祥，能在大家慌乱时安抚情绪，给出关键的建议。"
        },
        {
            "规范化名称": "阎王",
            "别名": "阎王老子",
            "性别": "男",
            "年龄": "中年",
            "音高": "低",
            "音色质感": "质感型",
            "声线密度": "强劲",
            "温度": "偏冷",
            "人物生平": "传说中掌管生死的冥界之王。虽然他没有出场，但美猴王正是因为害怕将来年纪大了会被他掌管、害怕死亡，才下定决心要去学习长生不老之术。",
            "性格特征": "威严、令人畏惧、掌管生死、公正",
            "说话语气": "无台词。可以想象他的声音低沉、洪亮，带有回响，不怒自威，说话的每个字都像是判决一样，不容置疑。"
        },
        {
            "规范化名称": "樵夫",
            "别名": "老神仙(被悟空误称)",
            "性别": "男",
            "年龄": "中年",
            "音高": "中",
            "音色质感": "质感型",
            "声线密度": "适中",
            "温度": "偏暖",
            "人物生平": "一位在灵台方寸山砍柴的普通人。他因为常常听到神仙讲道，学会了一首关于修道的歌。他虽然知道神仙的住处，但为了照顾年迈的母亲，放弃了修仙的机会。他非常善良，为孙悟空指明了去往斜月三星洞拜师的道路。",
            "性格特征": "善良朴实、孝顺、知足常乐、诚实",
            "说话语气": "朴实、真诚，有点憨厚。被误认为是神仙时会很惊慌，解释时语气恳切，充满了普通劳动人民的质朴感。"
        },
        {
            "规范化名称": "须菩提祖师",
            "别名": "祖师, 师父, 老爷",
            "性别": "男",
            "年龄": "老年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "居住在灵台方寸山斜月三星洞的一位法力高深的世外高人。他看出了孙悟空的根骨不凡，收他为徒，赐名“孙悟空”，并用打三下头、从后门进入的暗号，秘密传授给他长生不老的心法、七十二变和筋斗云。最后因悟空在师兄弟面前卖弄本领而将他赶走，并告诫他绝不能说出师父是谁。",
            "性格特征": "法力高深、智慧超群、教学有方、外冷内热、严厉",
            "说话语气": "平时说话温和而富有哲理，仿佛能洞察一切。教导弟子时严肃认真，发怒时声音严厉，充满不可违抗的威严。"
        },
        {
            "规范化名称": "仙童",
            "别名": "小朋友",
            "性别": "男",
            "年龄": "儿童",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "轻柔",
            "温度": "中性",
            "人物生平": "须菩提祖师门下的小童子，负责看守洞门。他奉师父之命开门迎接前来拜师的孙悟空，并将他领进洞中。",
            "性格特征": "乖巧、有礼貌、单纯、听从师命",
            "说话语气": "声音清脆的童声，说话很有礼貌，带着孩子气的好奇和一点点小大人的认真。"
        },
        {
            "规范化名称": "众仙",
            "别名": "诸位师兄, 诸位长者",
            "性别": "男女混合",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "须菩提祖师门下的三四十个弟子，也是孙悟空的师兄们。他们和悟空一起学习、生活。他们会因悟空顶撞师父而责备他，也会好奇地让他展示新学的本领，并在悟空变化成功后为他喝彩。",
            "性格特征": "循规蹈矩、有好奇心、集体意识强、有点爱看热闹",
            "说话语气": "像一群同学，说话时会有附和、议论。责备悟空时语气带有不满和担忧，好奇时则显得兴奋和期待。"
        },
        {
            "规范化名称": "海边渔民",
            "别名": "逃不掉的人",
            "性别": "男",
            "年龄": "中年",
            "音高": "高",
            "音色质感": "质感型",
            "声线密度": "强劲",
            "温度": "偏冷",
            "人物生平": "在南赡部洲海边生活的一位普通人。美猴王刚上岸时，为了好玩假扮成老虎吓唬众人，这位渔民因为没能跑掉，被美猴王抓住了，还被抢走了衣服。",
            "性格特征": "胆小、普通人",
            "说话语气": "无台词。可以想象他被抓住时发出了充满恐惧的尖叫声和求饶声。"
        }
    ]
    }
    character_list = [
        {
            "规范化名称": char.get("规范化名称", ""),
            "别名": char.get("别名", []),
            "性格特征": char.get("性格特征", [])
            # "说话语气": char.get("说话语气", "")
        }
        for char in character_gemini.get("全部角色", [])
    ]
    character_list_str =json.dumps(character_list, indent=4, ensure_ascii=False)

    # 改编大纲生成
    # output = Script_Structure_Planning(ori,story_line_gemini)
    script_structure_gemini = {
    "改编大纲": [
        {
            "场景": 1,
            "改编目标": "快速建立石猴的神奇出身和勇敢性格，将故事焦点集中在“水帘洞探险”这一核心动作上，通过简化背景和加强互动，突出猴群的欢乐氛围和对英雄的期盼，为儿童听众打造一个生动有趣的开端。",
            "节奏调整": [
                {
                    "部分": "原文开篇关于宇宙形成、元会计数、十二时辰等冗长、抽象的哲学和世界观设定。",
                    "调整方式": "全部删减。直接以“在遥远的大海上，有一座美丽的花果山，山顶上有一块神奇的石头”开场，用简短的旁白交代仙石吸收日月精华后，直接进入石猴出生的情节，让故事快速进入主线。"
                },
                {
                    "部分": "猴群在发现瀑布前玩耍的繁琐描写（如弹子、捉迷藏、捉虱子等）。",
                    "调整方式": "简化为一段充满活力的场景描述，用音效（猴子们的嬉笑声、跳跃声）和简短旁白“花果山上的猴子们每天都快乐地玩耍”来概括。然后迅速将焦点转向瀑布，通过猴子们的对话“哇，好大的瀑布！”“水是从哪里来的？”来制造悬念，推动情节发展。"
                },
                {
                    "部分": "石猴成为猴王的情节不够突出。",
                    "调整方式": "增强冲突。在发现瀑布后，增加猴子们的胆怯表现（“声音好大，我不敢过去。”“里面会不会有怪物？”），然后让石猴勇敢地站出来：“我来！谁敢进去再出来，谁就是我们的王！”通过这种对比，强化石猴的英雄气概。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "玉皇大帝派千里眼、顺风耳探查的支线情节。",
                    "调整方式": "完全删减。该情节与主线关联不大，且引入了过多新角色，会分散儿童听众的注意力。保留“目运两道金光”作为石猴不凡的象征即可。"
                },
                {
                    "部分": "水帘洞内部景色的纯视觉、书面化描写（如“翠藓堆蓝，白云浮玉”）。",
                    "调整方式": "转化为石猴兴奋的即时发现式对话。让石猴在洞内大声向外面的猴子们播报：“哇！这里面好大呀！有石头的桌子！石头的床！还有一个大石碑，上面写着‘水帘洞’！快进来，这里就是我们的新家啦！”配合洞穴的回声效果，用听觉营造空间感。"
                }
            ]
        },
        {
            "场景": 2,
            "改编目标": "将猴王对“死亡”的抽象恐惧，转化为儿童易于理解的“害怕快乐时光结束”的情感，并以此为动机，迅速引出“寻找神仙”这一核心行动，简化决策过程。",
            "节奏调整": [
                {
                    "部分": "猴王对“阎王老子”和生命短暂的深刻忧虑。",
                    "调整方式": "简化并具象化冲突。设定一个具体情境，如猴王看到一朵美丽的花凋谢了，或一只老猴子跳不动了。猴王可以叹气说：“唉，虽然我们现在很快乐，但如果有一天我们都老了，跳不动了，那该怎么办呢？我希望能永远和大家这样快乐地玩耍。”将抽象的生死观转化为对失去快乐的担忧。"
                },
                {
                    "部分": "通臂猿猴关于“佛、仙、神圣”三者的分类解释。",
                    "调整方式": "合并简化。让老猴子直接提出解决方案：“大王别担心，我听说世界上有会法术的神仙，他们知道永远年轻快乐的秘密！”直接给出“神仙”这个清晰的目标，避免复杂的概念分类。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "猴王独自在海上漂流的漫长过程。",
                    "调整方式": "用“音乐+旁白”的蒙太奇手法处理。旁白可以简洁地描述：“于是，美猴王告别了伙伴们，坐上小木筏，勇敢地出发了。风儿吹着帆，海浪推着船，他要去寻找能永远快乐的秘密……”配上充满希望和冒险感的音乐，快速过渡到下一场景。"
                }
            ]
        },
        {
            "场景": 3,
            "改编目标": "压缩漫长的寻访旅途，通过樵夫这一关键角色，快速引导孙悟空找到菩提祖师，并建立一个充满智慧和善意的师徒初见场景。",
            "节奏调整": [
                {
                    "部分": "猴王在南赡部洲游历八九年，学习人类言行礼仪的冗长过程。",
                    "调整方式": "完全删减。让猴王在登陆后不久，就直接被樵夫的歌声吸引。这样可以使情节更紧凑，目标更明确，避免不必要的支线。"
                },
                {
                    "部分": "与樵夫关于“黄庭”等道家哲学的复杂对话。",
                    "调整方式": "将樵夫的歌词改编得直白易懂，例如：“山里有神仙，本领大无边，要想学到真功夫，就上灵台方寸山。”让歌词直接提供关键信息，孙悟空听到后可以直接询问，省去复杂的哲学探讨。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "灵台方寸山和斜月三星洞的景物描写。",
                    "调整方式": "通过听觉元素来表现。旁白描述：“孙悟空按照樵夫的指引，果然找到了一座云雾缭绕的仙山。”并配上空灵的背景音乐、清脆的鸟鸣和风声，让听众通过想象感受仙境的氛围，而非依赖繁复的文字描述。"
                }
            ]
        },
        {
            "场景": 4,
            "改编目标": "聚焦于“三下敲头”的智慧考验，将其塑造成一个有趣的谜题。简化学习过程，重点突出“七十二变”和“筋斗云”这两个核心技能的趣味性和神奇感，使其成为儿童喜爱的亮点。",
            "节奏调整": [
                {
                    "部分": "祖师考验悟空是否想学“术”、“静”、“动”三门的重复性对话。",
                    "调整方式": "全部删减。改为祖师直接问悟空想学什么，悟空回答“我想学能永远快乐、永远年轻的本领！”然后祖师为了考验他的智慧，直接上演“敲头三下”的戏码，使情节更具戏剧性和目的性。"
                },
                {
                    "部分": "悟空解开谜题的内心活动。",
                    "调整方式": "通过简短的自言自语来外化心理活动。当其他师兄责备他时，悟空可以小声嘀咕：“大家误会了，师父敲我三下，是让我三更天去。他背着手走，是让我从后门进。这一定是个秘密暗号！”这样既能展现悟空的聪慧，也便于儿童听众理解。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "祖师传授的“显密圆通真妙诀”等深奥口诀，以及“三灾利害”的恐怖描述。",
                    "调整方式": "用声音效果和旁白替代。传授口诀时，用神奇的音效（如叮咚声、能量流动的声音）配合旁白“祖师将长生不老的口诀悄悄传给了悟空”。将“三灾”简化为“以后会有很多危险”，并把七十二变作为“躲避危险的本领”来教，从而避免引入惊吓元素，并保持故事的正面基调。"
                }
            ]
        },
        {
            "场景": 5,
            "改编目标": "明确“爱炫耀”是导致被逐的直接原因，建立清晰的因果关系。重点突出师父的告诫，强调这是出于保护，并为后续故事埋下“不能提师父名字”的重要伏笔。",
            "节奏调整": [
                {
                    "部分": "众师兄弟与悟空关于修炼成果的铺垫对话。",
                    "调整方式": "简化对话，使其更具行动性。师兄们可以直接起哄：“悟空，听说你学会了新本领，快变个东西给我们看看！”直接激发悟空的炫耀心理，快速触发核心冲突。"
                },
                {
                    "部分": "祖师对悟空的严厉训斥和复杂的道理阐述。",
                    "调整方式": "将师父的训斥转化为简单、充满关爱的告诫。例如：“悟空！我教你的本领，不是让你拿来炫耀的！如果被坏人知道了，他们会来找你麻烦，甚至会伤害你。为了保护你，你必须马上离开这里，回到你的家去。”这样既解释了原因，又保留了师徒间的情感温度。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "悟空变成松树的纯视觉变化过程。",
                    "调整方式": "使用“音效+反应”来表现。悟空喊出“变！”，配上一个神奇的“嗖”或“嘭”的音效，然后让其他师兄弟们发出惊讶的欢呼：“哇！真的变成一棵松树了！”“太厉害了！”通过他人的反应来确认变化的成功，激发听众的想象。"
                },
                {
                    "部分": "悟空告别后，独自飞回花果山的无声旅程。",
                    "调整方式": "用一个标志性的声音结尾，强化记忆点。悟空伤心地拜别师父后，旁白响起：“孙悟空记住师父的话，念动咒语，一个筋斗云，嗖——！”，紧随一个急速划破长空的音效，最后音效渐弱，故事在此处结束，留下悬念和期待。"
                }
            ]
        }
    ]
}
    script_structure_gemini_str = json.dumps(script_structure_gemini, indent=4, ensure_ascii=False)

    # 对白生成
    # dialogue_gemini2 = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     result = Dialogue_Generation(ori,character_list_str,tmp_structure)
    #     dialogue_gemini2['剧本'].append(result)
    dialogue_gemini = {
        "剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "群猴",
                    "对白": "哈哈哈，快来追我呀！你抓不到我！"
                },
                {
                    "角色": "群猴",
                    "对白": "等等！你们听，那是什么声音？"
                },
                {
                    "角色": "群猴",
                    "对白": "是那个大瀑布！哗啦啦的，好响啊！"
                },
                {
                    "角色": "群猴",
                    "对白": "这水是从哪里来的呢？真想去看看！"
                },
                {
                    "角色": "群猴",
                    "对白": "可是……我不敢过去，里面会不会有怪物？"
                },
                {
                    "角色": "群猴",
                    "对白": "我听别的猴子说，谁要是能进去再出来，谁就是我们的王！"
                },
                {
                    "角色": "群猴",
                    "对白": "当大王？那可太威风了！可是谁敢去呀？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "有什么不敢的？我来！"
                },
                {
                    "角色": "群猴",
                    "对白": "石猴，你疯啦？那里面很危险的！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "你们看好啦！我去去就回！"
                },
                {
                    "角色": "群猴",
                    "对白": "啊！他真的跳进去了！"
                },
                {
                    "角色": "群猴",
                    "对白": "他……他没事吧？怎么没声音了？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "喂！大家！我在这里！"
                },
                {
                    "角色": "群猴",
                    "对白": "是石猴的声音！他真的没事！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "快来看啊！这瀑布后面是一个好大的山洞！"
                },
                {
                    "角色": "群猴",
                    "对白": "山洞？里面有什么呀？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "有石头的桌子！石头的床！还有好多好多宝贝！这里就是我们的新家啦！"
                },
                {
                    "角色": "群猴",
                    "对白": "太棒了！我们有新家了！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "这里还有一个大石碑，上面写着“水帘洞”！"
                },
                {
                    "角色": "群猴",
                    "对白": "石猴回来啦！英雄回来啦！"
                },
                {
                    "角色": "群猴",
                    "对白": "你真勇敢！从今天起，你就是我们的大王！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "好！那从今天起，我就是美猴王！大家跟我进我们的新家吧！"
                },
                {
                    "角色": "群猴",
                    "对白": "好耶！拜见美猴王！千岁大王！"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "群猴",
                    "对白": "大王，您快尝尝这个桃子，又香又甜！"
                },
                {
                    "角色": "群猴",
                    "对白": "是啊是啊，我们今天太开心啦！有吃有喝，还能一起玩！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "唉……"
                },
                {
                    "角色": "群猴",
                    "对白": "大王，您怎么了？为什么突然叹气啊？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "你们看，那朵花昨天还那么漂亮，今天就谢了。还有那只老猴子，他都跳不动了。"
                },
                {
                    "角色": "群猴",
                    "对白": "是啊，可是我们现在很快乐呀！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "可是，如果有一天，我们都变老了，跳不动了，再也不能像现在这样一起玩了，那该怎么办呢？"
                },
                {
                    "角色": "群猴",
                    "对白": "老了就不能玩了吗？我不要变老！"
                },
                {
                    "角色": "群猴",
                    "对白": "呜呜呜……我也不想变老，我想永远跟大王一起玩。"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "大王别担心，您能想到这么远的事情，真了不起。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "老爷爷，你有什么好办法吗？我希望大家能永远这么快乐。"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "我听说，世界上有会法术的神仙，他们知道永远年轻快乐的秘密！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "神仙？真的吗？他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "他们就住在很远很远的地方，要翻过高山，渡过大海才能找到。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "太好了！我决定了，明天我就出发，去寻找神仙，学那个永远快乐的秘密！"
                },
                {
                    "角色": "群猴",
                    "对白": "大王要去那么远的地方吗？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "对！等我学会了本领，就马上回来！到时候，我们就能永远在一起，永远都这么快乐了！"
                },
                {
                    "角色": "群猴",
                    "对白": "太棒了！我们支持大王！"
                },
                {
                    "角色": "群猴",
                    "对白": "大王，我们明天为您准备一场盛大的宴会，为您送行！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "好！一言为定！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "樵夫",
                    "对白": "要想学长生，就得有恒心，山里有神仙，本领大无边！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "咦？这是什么人在唱歌？听起来好像知道神仙在哪儿！"
                },
                {
                    "角色": "樵夫",
                    "对白": "要想见神仙，不怕路途远，就在灵台山，能学真功夫！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "老神仙！我可找到你了！"
                },
                {
                    "角色": "樵夫",
                    "对白": "哎哟！你吓我一跳！你……你叫我什么？我不是什么神仙。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "你不是神仙？那你怎么会唱神仙的歌？"
                },
                {
                    "角色": "樵夫",
                    "对白": "哦，你说这首歌啊。是一位真正的神仙教我唱的，他说我砍柴累了，唱一唱就不累了。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "真正的神仙？他在哪里？快告诉我，我要拜他为师！"
                },
                {
                    "角色": "樵夫",
                    "对白": "你也要学长生不老的法术吗？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "是啊是啊！我找了好多年了！求求你告诉我吧！"
                },
                {
                    "角色": "樵夫",
                    "对白": "好吧，看你这么诚心。那位神仙就住在那座山上。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "哪座山？叫什么名字？"
                },
                {
                    "角色": "樵夫",
                    "对白": "那座山叫灵台方寸山，山里有个斜月三星洞。神仙爷爷就住在洞里。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "灵台方寸山，斜月三星洞……太好了！我该怎么走？"
                },
                {
                    "角色": "樵夫",
                    "对白": "你顺着这条小路一直往南走，用不了多久就能看到了。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "谢谢你，好心的大哥！我这就去！"
                },
                {
                    "角色": "樵夫",
                    "对白": "唉，慢点慢点！我还要砍柴回家照顾老母亲呢，你快去吧！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "须菩提祖师",
                    "对白": "悟空，你来我这儿也有七年了。今天，你想学些什么本领呀？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父！我想学那种能永远快乐、永远年轻的本领！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哼！你这猴头，不好好修行，整天就想着玩乐！"
                },
                {
                    "角色": "众仙",
                    "对白": "哎呀，师父好像生气了。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "这也不想学，那也不想学，你到底想怎么样！"
                },
                {
                    "角色": "众仙",
                    "对白": "悟空，你这顽皮的猴子！师父好心教你，你怎么还跟师父顶嘴？"
                },
                {
                    "角色": "众仙",
                    "对白": "是啊！你看，师父被你气走了！这下可怎么办啊！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "嘿嘿，你们都误会啦，师父不是真的生气。"
                },
                {
                    "角色": "众仙",
                    "对白": "胡说！师父明明拿着戒尺打了你的头！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父敲我三下，是让我三更天去找他。他背着手走，是让我从后门进去。这一定是个秘密暗号！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父，师父，我来了！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你这猢狲！不在前面睡觉，跑到我这里来做什么？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父，我猜对了您的暗号！您是要半夜悄悄教我真正的本领，对不对？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哈哈哈！你果然是个天生的聪明猴儿！既然你猜到了，我就把长生不老的口诀传给你。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "谢谢师父！谢谢师父！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "悟空，学会了长生之法，以后还可能会遇到很多危险。你想不想学些躲避危险的本领？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "想学！想学！师父快教我！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "我这里有两种变化之术，一种是天罡三十六变，一种是地煞七十二变。你想学哪一个？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "嘿嘿，当然是学多的那个！弟子要学七十二变！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "好，你靠近些，我这就把七十二变的口诀传给你。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "嗯，不错。不过你现在虽然能飞，但飞得太慢，只能算是爬云。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "啊？这还只是爬云？师父，求您大发慈悲，再教我一个能飞得快的法术吧！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "也罢，看在你如此好学的份上，我再教你一个“筋斗云”。只要一个跟头，就能飞出十万八千里！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "一个跟头十万八千里！太棒了！谢谢师父！谢谢师父！我这就去练！"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "众仙",
                    "对白": "悟空，听说师父教了你躲避三灾的本事，是真的吗？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "嘿嘿，不瞒各位师兄，师父教的七十二变，我已经全都学会啦！"
                },
                {
                    "角色": "众仙",
                    "对白": "真的吗？那你快变一个给我们看看！"
                },
                {
                    "角色": "众仙",
                    "对白": "对啊，就趁现在，让我们开开眼界！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "好！那你们说，要我变成什么？"
                },
                {
                    "角色": "众仙",
                    "对白": "嗯……就变成一棵松树吧！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "这有何难！你们看好了！变！"
                },
                {
                    "角色": "众仙",
                    "对白": "哇！真的变成一棵松树了！一模一样！"
                },
                {
                    "角色": "众仙",
                    "对白": "好猴子！好猴子！太厉害了！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "是什么人在这里大声喧哗！"
                },
                {
                    "角色": "众仙",
                    "对白": "啊！是师父！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父恕罪，我们……我们只是在这里讲道，没有外人喧哗。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "还敢说谎！你们在这里大吵大笑，哪有半点修行的样子！悟空，你过来！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "我问你，为什么要卖弄你的本事？我教你这些，是让你拿来炫耀的吗？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子……弟子只是和师兄们玩耍，一时高兴……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "糊涂！如果被坏人知道了你有这样的本领，他们会来找你的麻烦，甚至会伤害你！到那时，你的性命就保不住了！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父！弟子再也不敢了！求师父宽恕！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "为了保护你，你必须马上离开这里。你从哪里来，就回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "什么？师父，您要赶我走？我离家二十年，还没报答您的恩情，我不想走！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你快回去保全性命吧！你留在这里，绝对不行！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父……呜呜……弟子舍不得您啊！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你给我听好！你走了以后，不管惹出多大的祸，都不许说是我的徒弟。半个字也不行！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子绝不说出师父的名字！只说是我自己学会的！多谢师父厚恩！"
                }
            ]
        }
        ]
    }

    # 为dialogue的每个对话生成序号
    dialogue_str = dialogue_to_annotated_string(dialogue_gemini)

    # 旁白生成
    # narration_gemini2 = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     tmp_dialogue = dialogue_to_annotated_string_by_scene(dialogue_gemini['剧本'][index])
    #     result = Narration_Generation(ori,tmp_structure,tmp_dialogue)
    #     narration_gemini2['剧本'].append(result)

    # Narration_Generation(ori,script_structure_gemini_str,dialogue_str)
    narration_gemini = {
  "剧本": [
        {
            "场景": 1,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "在遥远的大海上，有一座美丽的花果山。山上的猴子们每天都快乐地玩耍、做游戏。其中，有一只与众不同的石猴，他呀，是从山顶上一块神奇的仙石里蹦出来的！"
                },
                {
                    "插入位置": 1,
                    "旁白": "这一天，正当猴子们在小溪边追逐打闹时，一阵巨大的声音吸引了他们的注意。"
                },
                {
                    "插入位置": 7,
                    "旁白": "猴子们都害怕得往后退。就在这时，那只勇敢的石猴从猴群里跳了出来。"
                },
                {
                    "插入位置": 10,
                    "旁白": "说完，石猴深吸一口气，闭上眼睛，“嗖”地一下，真的跳进了瀑布里！水花溅得好高好高。"
                },
                {
                    "插入位置": 12,
                    "旁白": "原来，瀑布后面根本不是水，而是一座亮晶晶的铁板桥！石猴穿过水帘，稳稳地落在了桥上。他睁开眼一看，桥对面是一个又大又干爽的山洞，他太惊喜了，赶紧朝着外面大喊。"
                },
                {
                    "插入位置": 19,
                    "旁白": "石猴在洞里把好东西都看清楚了，然后又一次穿过瀑布，跳回到了大家面前。"
                },
                {
                    "插入位置": 22,
                    "旁白": "猴子们高兴地又叫又跳，排着队，跟着他们的美猴王，一个接一个地穿过瀑布，住进了这个又安全又漂亮的新家——水帘洞！"
                }
            ]
        },
        {
            "场景": 2,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "自从找到了新家，猴王和猴子们每天都在水帘洞里开心地玩耍。这一天，他们又聚在一起开宴会，石桌上摆满了香甜的野果，大家正一边吃一边笑呢。"
                },
                {
                    "插入位置": 2,
                    "旁白": "看着伙伴们开心的样子，猴王却突然不说话了，他脸上的笑容慢慢消失，轻轻地叹了一口气。"
                },
                {
                    "插入位置": 9,
                    "旁白": "听到猴王的话，小猴子们你看看我，我看看你，都害怕起来。刚才的欢声笑语不见了，一个个都耷拉着脑袋，难过地小声抽泣。就在这时，猴群里一只年纪最大的通背猿猴走了出来。"
                },
                {
                    "插入位置": 12,
                    "旁白": "猴王一听，眼睛瞬间亮了起来，他激动地抓住老猴子的手臂，仿佛抓住了新的希望。"
                },
                {
                    "插入位置": 14,
                    "旁白": "猴王听完，没有一丝犹豫。他挺起胸膛，眼神坚定地向所有猴子宣布。"
                }
            ]
        },
        {
            "场景": 3,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "美猴王告别了小猴子们，一个人划着木筏，在海上漂了好久好久，终于来到了一片新的陆地。他跳上岸，走进了一片又高又密的森林里。他一边走，一边东瞧瞧西看看，忽然，一阵清脆的歌声和“铛、铛”的砍柴声传了过来。"
                },
                {
                    "插入位置": 3,
                    "旁白": "孙悟空高兴坏了，他拨开挡路的树枝，顺着歌声和砍柴声找过去，果然看见一个正在砍柴的樵夫。他想也没想，一下子跳到樵夫面前，大声喊道："
                },
                {
                    "插入位置": 4,
                    "旁白": "这个樵夫大哥正专心砍柴呢，突然从树丛里跳出来一只毛茸茸的猴子，还叫他“老神仙”，吓得他“啊”地叫了一声，手里的斧头都掉在了地上。"
                },
                {
                    "插入位置": 10,
                    "旁白": "樵夫看孙悟空这么着急，也不忍心了。他抬起手，指向远处一座云雾缭绕的高山。"
                },
                {
                    "插入位置": 15,
                    "旁白": "一听到有路可循，孙悟空高兴得抓耳挠腮，他对着樵夫深深鞠了一躬，转身就要跑。"
                },
                {
                    "插入位置": 17,
                    "旁白": "话音刚落，孙悟空就像一阵风似的，顺着那条小路向南边跑去。他翻过一座又一座小山坡，心里只有一个念头：快点找到灵台方寸山，拜神仙为师！"
                }
            ]
        },
        {
            "场景": 4,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "一转眼，七年过去了。孙悟空每天跟着师兄们学习，过得可开心了。这一天，菩提祖师坐在高高的讲台上，把孙悟空叫到了跟前。"
                },
                {
                    "插入位置": 2,
                    "旁白": "听到这话，菩提祖师突然收起了笑容，脸上变得很严肃。"
                },
                {
                    "插入位置": 5,
                    "旁白": "菩提祖师说完，生气地走下讲台，拿着戒尺在悟空的头上“咚、咚、咚”敲了三下。然后，他背着手，一言不发地走进了内院，还关上了中门，把所有人都留在了外面。这下，在场的仙童们都吓坏了。"
                },
                {
                    "插入位置": 7,
                    "旁白": "师兄们都替悟空着急，可悟空一点儿也不生气，反而看着大家，嘿嘿地笑了起来。"
                },
                {
                    "插入位置": 10,
                    "旁白": "到了半夜三更，大家都睡着了。孙悟空悄悄地爬起来，蹑手蹑脚地溜出房间，来到了祖师住处的后门外。他发现，门果然留着一条小缝。悟空心里一喜，轻轻推开门溜了进去，看见祖师正盘腿坐在床上，好像在等他。"
                },
                {
                    "插入位置": 14,
                    "旁白": "于是，菩提祖师凑到悟空耳边，把长生不老的奇妙口诀，一字一句地悄悄传授给了他。孙悟空听得特别认真，把每一个字都牢牢记在了心里。"
                },
                {
                    "插入位置": 19,
                    "旁白": "祖师又一次在悟空耳边低声传授了口诀。聪明的悟空一点就通，很快就自己练成了七十二般变化。"
                },
                {
                    "插入位置": 20,
                    "旁白": "就这样，孙悟空又学到了许多新本领。几天后，祖师想看看他学得怎么样了，就把他叫到洞前的空地上。悟空使出本事，翻了几个跟头，一下子就飞到了半空中，他在天上绕了一小圈，又稳稳地落在了师父面前。"
                },
                {
                    "插入位置": 23,
                    "旁白": "悟空一听，高兴得连连磕头。祖师便把“筋斗云”的飞行口诀，也一并传授给了他。"
                }
            ]
        },
        {
            "场景": 5,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "一个晴朗的夏日，三星洞前的松树下，师兄弟们正围着孙悟空，七嘴八舌地聊着天。"
                },
                {
                    "插入位置": 6,
                    "旁白": "孙悟空听到大家这么期待，得意地挺起胸膛。他念动咒语，手指一掐，大喊一声："
                },
                {
                    "插入位置": 9,
                    "旁白": "大家正为悟空的本领鼓掌叫好，吵闹声惊动了须菩提祖师。他拄着拐杖走过来，严厉的声音突然响起。"
                },
                {
                    "插入位置": 11,
                    "旁白": "师兄们吓得立刻安静下来。悟空也赶紧从松树变回原样，慌张地混在人群里。"
                },
                {
                    "插入位置": 13,
                    "旁白": "孙悟空低着头，从师兄们中间走出来，站到祖师面前。"
                },
                {
                    "插入位置": 16,
                    "旁白": "祖师看着悟空，叹了口气，语气虽然严厉，但眼神里却充满了担心。"
                },
                {
                    "插入位置": 17,
                    "旁白": "孙悟空这才明白师父的苦心，也知道了炫耀本领的危险，他吓得跪倒在地，连连磕头。"
                },
                {
                    "插入位置": 19,
                    "旁白": "听到师父真的要赶自己走，孙悟空一下子愣住了，他不敢相信自己的耳朵。"
                },
                {
                    "插入位置": 21,
                    "旁白": "孙悟空见师父心意已决，知道无法挽回，再也忍不住，伤心地大哭起来。"
                },
                {
                    "插入位置": 23,
                    "旁白": "孙悟空知道师父是为了保护自己，他擦干眼泪，重重地磕了个头，把师父的叮嘱记在心里。"
                },
                {
                    "插入位置": 24,
                    "旁白": "告别了师父和师兄们，孙悟空念动咒语，一个筋斗云，嗖的一声，就朝着东边花果山的方向飞去了。"
                }
            ]
        }
    ]
}

    # 合并旁白与对白
    # result = combine_dialogue_and_narration(dialogue_gemini, narration_gemini)
    # print(result)

    #合并后的剧本
    pre_script_gemini = {
	"剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "在遥远的大海上，有一座美丽的花果山。山上的猴子们每天都快乐地玩耍、做游戏。其中，有一只与众不同的石猴，他呀，是从山顶上一块神奇的仙石里蹦出来的！"
                },
                {
                    "角色": "群猴",
                    "内容": "哈哈哈，快来追我呀！你抓不到我！"
                },
                {
                    "角色": "旁白",
                    "内容": "这一天，正当猴子们在小溪边追逐打闹时，一阵巨大的声音吸引了他们的注意。"
                },
                {
                    "角色": "群猴",
                    "内容": "等等！你们听，那是什么声音？"
                },
                {
                    "角色": "群猴",
                    "内容": "是那个大瀑布！哗啦啦的，好响啊！"
                },
                {
                    "角色": "群猴",
                    "内容": "这水是从哪里来的呢？真想去看看！"
                },
                {
                    "角色": "群猴",
                    "内容": "可是……我不敢过去，里面会不会有怪物？"
                },
                {
                    "角色": "群猴",
                    "内容": "我听别的猴子说，谁要是能进去再出来，谁就是我们的王！"
                },
                {
                    "角色": "群猴",
                    "内容": "当大王？那可太威风了！可是谁敢去呀？"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们都害怕得往后退。就在这时，那只勇敢的石猴从猴群里跳了出来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "有什么不敢的？我来！"
                },
                {
                    "角色": "群猴",
                    "内容": "石猴，你疯啦？那里面很危险的！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们看好啦！我去去就回！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，石猴深吸一口气，闭上眼睛，“嗖”地一下，真的跳进了瀑布里！水花溅得好高好高。"
                },
                {
                    "角色": "群猴",
                    "内容": "啊！他真的跳进去了！"
                },
                {
                    "角色": "群猴",
                    "内容": "他……他没事吧？怎么没声音了？"
                },
                {
                    "角色": "旁白",
                    "内容": "原来，瀑布后面根本不是水，而是一座亮晶晶的铁板桥！石猴穿过水帘，稳稳地落在了桥上。他睁开眼一看，桥对面是一个又大又干爽的山洞，他太惊喜了，赶紧朝着外面大喊。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "喂！大家！我在这里！"
                },
                {
                    "角色": "群猴",
                    "内容": "是石猴的声音！他真的没事！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "快来看啊！这瀑布后面是一个好大的山洞！"
                },
                {
                    "角色": "群猴",
                    "内容": "山洞？里面有什么呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "有石头的桌子！石头的床！还有好多好多宝贝！这里就是我们的新家啦！"
                },
                {
                    "角色": "群猴",
                    "内容": "太棒了！我们有新家了！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "这里还有一个大石碑，上面写着“水帘洞”！"
                },
                {
                    "角色": "旁白",
                    "内容": "石猴在洞里把好东西都看清楚了，然后又一次穿过瀑布，跳回到了大家面前。"
                },
                {
                    "角色": "群猴",
                    "内容": "石猴回来啦！英雄回来啦！"
                },
                {
                    "角色": "群猴",
                    "内容": "你真勇敢！从今天起，你就是我们的大王！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！那从今天起，我就是美猴王！大家跟我进我们的新家吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们高兴地又叫又跳，排着队，跟着他们的美猴王，一个接一个地穿过瀑布，住进了这个又安全又漂亮的新家——水帘洞！"
                },
                {
                    "角色": "群猴",
                    "内容": "好耶！拜见美猴王！千岁大王！"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "自从找到了新家，猴王和猴子们每天都在水帘洞里开心地玩耍。这一天，他们又聚在一起开宴会，石桌上摆满了香甜的野果，大家正一边吃一边笑呢。"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，您快尝尝这个桃子，又香又甜！"
                },
                {
                    "角色": "群猴",
                    "内容": "是啊是啊，我们今天太开心啦！有吃有喝，还能一起玩！"
                },
                {
                    "角色": "旁白",
                    "内容": "看着伙伴们开心的样子，猴王却突然不说话了，他脸上的笑容慢慢消失，轻轻地叹了一口气。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "唉……"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，您怎么了？为什么突然叹气啊？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们看，那朵花昨天还那么漂亮，今天就谢了。还有那只老猴子，他都跳不动了。"
                },
                {
                    "角色": "群猴",
                    "内容": "是啊，可是我们现在很快乐呀！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "可是，如果有一天，我们都变老了，跳不动了，再也不能像现在这样一起玩了，那该怎么办呢？"
                },
                {
                    "角色": "群猴",
                    "内容": "老了就不能玩了吗？我不要变老！"
                },
                {
                    "角色": "群猴",
                    "内容": "呜呜呜……我也不想变老，我想永远跟大王一起玩。"
                },
                {
                    "角色": "旁白",
                    "内容": "听到猴王的话，小猴子们你看看我，我看看你，都害怕起来。刚才的欢声笑语不见了，一个个都耷拉着脑袋，难过地小声抽泣。就在这时，猴群里一只年纪最大的通背猿猴走了出来。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王别担心，您能想到这么远的事情，真了不起。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "老爷爷，你有什么好办法吗？我希望大家能永远这么快乐。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "我听说，世界上有会法术的神仙，他们知道永远年轻快乐的秘密！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王一听，眼睛瞬间亮了起来，他激动地抓住老猴子的手臂，仿佛抓住了新的希望。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "神仙？真的吗？他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "他们就住在很远很远的地方，要翻过高山，渡过大海才能找到。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王听完，没有一丝犹豫。他挺起胸膛，眼神坚定地向所有猴子宣布。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "太好了！我决定了，明天我就出发，去寻找神仙，学那个永远快乐的秘密！"
                },
                {
                    "角色": "群猴",
                    "内容": "大王要去那么远的地方吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "对！等我学会了本领，就马上回来！到时候，我们就能永远在一起，永远都这么快乐了！"
                },
                {
                    "角色": "群猴",
                    "内容": "太棒了！我们支持大王！"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，我们明天为您准备一场盛大的宴会，为您送行！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！一言为定！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "美猴王告别了小猴子们，一个人划着木筏，在海上漂了好久好久，终于来到了一片新的陆地。他跳上岸，走进了一片又高又密的森林里。他一边走，一边东瞧瞧西看看，忽然，一阵清脆的歌声和“铛、铛”的砍柴声传了过来。"
                },
                {
                    "角色": "樵夫",
                    "内容": "要想学长生，就得有恒心，山里有神仙，本领大无边！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "咦？这是什么人在唱歌？听起来好像知道神仙在哪儿！"
                },
                {
                    "角色": "樵夫",
                    "内容": "要想见神仙，不怕路途远，就在灵台山，能学真功夫！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空高兴坏了，他拨开挡路的树枝，顺着歌声和砍柴声找过去，果然看见一个正在砍柴的樵夫。他想也没想，一下子跳到樵夫面前，大声喊道："
                },
                {
                    "角色": "孙悟空",
                    "内容": "老神仙！我可找到你了！"
                },
                {
                    "角色": "旁白",
                    "内容": "这个樵夫大哥正专心砍柴呢，突然从树丛里跳出来一只毛茸茸的猴子，还叫他“老神仙”，吓得他“啊”地叫了一声，手里的斧头都掉在了地上。"
                },
                {
                    "角色": "樵夫",
                    "内容": "哎哟！你吓我一跳！你……你叫我什么？我不是什么神仙。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你不是神仙？那你怎么会唱神仙的歌？"
                },
                {
                    "角色": "樵夫",
                    "内容": "哦，你说这首歌啊。是一位真正的神仙教我唱的，他说我砍柴累了，唱一唱就不累了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "真正的神仙？他在哪里？快告诉我，我要拜他为师！"
                },
                {
                    "角色": "樵夫",
                    "内容": "你也要学长生不老的法术吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "是啊是啊！我找了好多年了！求求你告诉我吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "樵夫看孙悟空这么着急，也不忍心了。他抬起手，指向远处一座云雾缭绕的高山。"
                },
                {
                    "角色": "樵夫",
                    "内容": "好吧，看你这么诚心。那位神仙就住在那座山上。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哪座山？叫什么名字？"
                },
                {
                    "角色": "樵夫",
                    "内容": "那座山叫灵台方寸山，山里有个斜月三星洞。神仙爷爷就住在洞里。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "灵台方寸山，斜月三星洞……太好了！我该怎么走？"
                },
                {
                    "角色": "樵夫",
                    "内容": "你顺着这条小路一直往南走，用不了多久就能看到了。"
                },
                {
                    "角色": "旁白",
                    "内容": "一听到有路可循，孙悟空高兴得抓耳挠腮，他对着樵夫深深鞠了一躬，转身就要跑。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "谢谢你，好心的大哥！我这就去！"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，慢点慢点！我还要砍柴回家照顾老母亲呢，你快去吧！"
                },
                {
                    "类型": "旁白",
                    "内容": "话音刚落，孙悟空就像一阵风似的，顺着那条小路向南边跑去。他翻过一座又一座小山坡，心里只有一个念头：快点找到灵台方寸山，拜神仙为师！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "一转眼，七年过去了。孙悟空每天跟着师兄们学习，过得可开心了。这一天，菩提祖师坐在高高的讲台上，把孙悟空叫到了跟前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你来我这儿也有七年了。今天，你想学些什么本领呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！我想学那种能永远快乐、永远年轻的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "听到这话，菩提祖师突然收起了笑容，脸上变得很严肃。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哼！你这猴头，不好好修行，整天就想着玩乐！"
                },
                {
                    "角色": "众仙",
                    "内容": "哎呀，师父好像生气了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "这也不想学，那也不想学，你到底想怎么样！"
                },
                {
                    "角色": "旁白",
                    "内容": "菩提祖师说完，生气地走下讲台，拿着戒尺在悟空的头上“咚、咚、咚”敲了三下。然后，他背着手，一言不发地走进了内院，还关上了中门，把所有人都留在了外面。这下，在场的仙童们都吓坏了。"
                },
                {
                    "角色": "众仙",
                    "内容": "悟空，你这顽皮的猴子！师父好心教你，你怎么还跟师父顶嘴？"
                },
                {
                    "角色": "众仙",
                    "内容": "是啊！你看，师父被你气走了！这下可怎么办啊！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄们都替悟空着急，可悟空一点儿也不生气，反而看着大家，嘿嘿地笑了起来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，你们都误会啦，师父不是真的生气。"
                },
                {
                    "角色": "众仙",
                    "内容": "胡说！师父明明拿着戒尺打了你的头！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父敲我三下，是让我三更天去找他。他背着手走，是让我从后门进去。这一定是个秘密暗号！"
                },
                {
                    "角色": "旁白",
                    "内容": "到了半夜三更，大家都睡着了。孙悟空悄悄地爬起来，蹑手蹑脚地溜出房间，来到了祖师住处的后门外。他发现，门果然留着一条小缝。悟空心里一喜，轻轻推开门溜了进去，看见祖师正盘腿坐在床上，好像在等他。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，师父，我来了！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你这猢狲！不在前面睡觉，跑到我这里来做什么？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，我猜对了您的暗号！您是要半夜悄悄教我真正的本领，对不对？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哈哈哈！你果然是个天生的聪明猴儿！既然你猜到了，我就把长生不老的口诀传给你。"
                },
                {
                    "角色": "旁白",
                    "内容": "于是，菩提祖师凑到悟空耳边，把长生不老的奇妙口诀，一字一句地悄悄传授给了他。孙悟空听得特别认真，把每一个字都牢牢记在了心里。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "谢谢师父！谢谢师父！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，学会了长生之法，以后还可能会遇到很多危险。你想不想学些躲避危险的本领？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "想学！想学！师父快教我！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我这里有两种变化之术，一种是天罡三十六变，一种是地煞七十二变。你想学哪一个？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，当然是学多的那个！弟子要学七十二变！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师又一次在悟空耳边低声传授了口诀。聪明的悟空一点就通，很快就自己练成了七十二般变化。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好，你靠近些，我这就把七十二变的口诀传给你。"
                },
                {
                    "角色": "旁白",
                    "内容": "就这样，孙悟空又学到了许多新本领。几天后，祖师想看看他学得怎么样了，就把他叫到洞前的空地上。悟空使出本事，翻了几个跟头，一下子就飞到了半空中，他在天上绕了一小圈，又稳稳地落在了师父面前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "嗯，不错。不过你现在虽然能飞，但飞得太慢，只能算是爬云。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "啊？这还只是爬云？师父，求您大发慈悲，再教我一个能飞得快的法术吧！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "也罢，看在你如此好学的份上，我再教你一个“筋斗云”。只要一个跟头，就能飞出十万八千里！"
                },
                {
                    "角色": "旁白",
                    "内容": "悟空一听，高兴得连连磕头。祖师便把“筋斗云”的飞行口诀，也一并传授给了他。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "一个跟头十万八千里！太棒了！谢谢师父！谢谢师父！我这就去练！"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "一个晴朗的夏日，三星洞前的松树下，师兄弟们正围着孙悟空，七嘴八舌地聊着天。"
                },
                {
                    "角色": "众仙",
                    "内容": "悟空，听说师父教了你躲避三灾的本事，是真的吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，不瞒各位师兄，师父教的七十二变，我已经全都学会啦！"
                },
                {
                    "角色": "众仙",
                    "内容": "真的吗？那你快变一个给我们看看！"
                },
                {
                    "角色": "众仙",
                    "内容": "对啊，就趁现在，让我们开开眼界！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！那你们说，要我变成什么？"
                },
                {
                    "角色": "众仙",
                    "内容": "嗯……就变成一棵松树吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空听到大家这么期待，得意地挺起胸膛。他念动咒语，手指一掐，大喊一声："
                },
                {
                    "角色": "孙悟空",
                    "内容": "这有何难！你们看好了！变！"
                },
                {
                    "角色": "众仙",
                    "内容": "哇！真的变成一棵松树了！一模一样！"
                },
                {
                    "角色": "众仙",
                    "内容": "好猴子！好猴子！太厉害了！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家正为悟空的本领鼓掌叫好，吵闹声惊动了须菩提祖师。他拄着拐杖走过来，严厉的声音突然响起。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是什么人在这里大声喧哗！"
                },
                {
                    "角色": "众仙",
                    "内容": "啊！是师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄们吓得立刻安静下来。悟空也赶紧从松树变回原样，慌张地混在人群里。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父恕罪，我们……我们只是在这里讲道，没有外人喧哗。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "还敢说谎！你们在这里大吵大笑，哪有半点修行的样子！悟空，你过来！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空低着头，从师兄们中间走出来，站到祖师面前。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我问你，为什么要卖弄你的本事？我教你这些，是让你拿来炫耀的吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子……弟子只是和师兄们玩耍，一时高兴……"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师看着悟空，叹了口气，语气虽然严厉，但眼神里却充满了担心。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "糊涂！如果被坏人知道了你有这样的本领，他们会来找你的麻烦，甚至会伤害你！到那时，你的性命就保不住了！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空这才明白师父的苦心，也知道了炫耀本领的危险，他吓得跪倒在地，连连磕头。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！求师父宽恕！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "为了保护你，你必须马上离开这里。你从哪里来，就回哪里去吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "听到师父真的要赶自己走，孙悟空一下子愣住了，他不敢相信自己的耳朵。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "什么？师父，您要赶我走？我离家二十年，还没报答您的恩情，我不想走！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你快回去保全性命吧！你留在这里，绝对不行！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空见师父心意已决，知道无法挽回，再也忍不住，伤心地大哭起来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……呜呜……弟子舍不得您啊！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你给我听好！你走了以后，不管惹出多大的祸，都不许说是我的徒弟。半个字也不行！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空知道师父是为了保护自己，他擦干眼泪，重重地磕了个头，把师父的叮嘱记在心里。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子绝不说出师父的名字！只说是我自己学会的！多谢师父厚恩！"
                },
                {
                    "类型": "旁白",
                    "内容": "告别了师父和师兄们，孙悟空念动咒语，一个筋斗云，嗖的一声，就朝着东边花果山的方向飞去了。"
                }
            ]
        }]
}
    pre_script_gemini_str = json.dumps(pre_script_gemini, indent=4, ensure_ascii=False)

    # 冲突增强，根据每一幕
    # script_conflict_escalation_gemini = {'剧本':[]}
    # for index,script in enumerate(pre_script_gemini['剧本']):
    #     tmp_script_structure =json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #     tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
    #     tmp_script_escalation = Conflict_Escalation(tmp_script_structure, character_list_str,tmp_script)
    #     script_conflict_escalation_gemini['剧本'].append(tmp_script_escalation)
    # print(script_conflict_escalation_gemini)

    # 剧本审查
    script_conflict_escalation_gemini = {
	"剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "在遥远的大海上，有一座美丽的花果山。山上的猴子们每天都快乐地玩耍、做游戏。其中，有一只与众不同的石猴，他呀，是从山顶上一块神奇的仙石里蹦出来的！"
                },
                {
                    "角色": "群猴",
                    "内容": "哈哈哈，快来追我呀！你抓不到我！"
                },
                {
                    "角色": "旁白",
                    "内容": "这一天，正当猴子们在小溪边追逐打闹时，一阵巨大的声音吸引了他们的注意。"
                },
                {
                    "角色": "群猴",
                    "内容": "（兴奋地）哇！好大的瀑布！真想进去看看里面有什么！"
                },
                {
                    "角色": "群猴",
                    "内容": "（害怕地）不行不行！声音那么大，里面肯定有大怪物！我可不敢去！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大家安静！我倒是有个主意。我们猴子一直没有大王，谁有本事跳进这瀑布，再平平安安地出来，我们就拜他为王！"
                },
                {
                    "角色": "群猴",
                    "内容": "（小声议论）当大王？听起来好棒……可是，谁敢啊？"
                },
                {
                    "角色": "群猴",
                    "内容": "（缩着脖子）我不敢，我不敢……"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们你看看我，我看看你，都害怕得往后退。就在这时，那只勇敢的石猴从猴群里跳了出来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（大声地）你们都不敢，我敢！我来！"
                },
                {
                    "角色": "群猴",
                    "内容": "（着急地）石猴，别去！你不要命啦？万一你回不来怎么办？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（坚定地）哼，胆小鬼！你们就在这儿好好看着！我不仅要进去，还要当你们的大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，石猴深吸一口气，闭上眼睛，“嗖”地一下，真的跳进了瀑布里！水花溅得好高好高。"
                },
                {
                    "角色": "群猴",
                    "内容": "啊！他真的跳进去了！"
                },
                {
                    "角色": "群猴",
                    "内容": "（担忧地）他……他不会被水冲走了吧？怎么一点声音都没有了？"
                },
                {
                    "角色": "旁白",
                    "内容": "原来，瀑布后面根本不是水，而是一座亮晶晶的铁板桥！石猴穿过水帘，稳稳地落在了桥上。他睁开眼一看，桥对面是一个又大又干爽的山洞，他太惊喜了，赶紧朝着外面大喊。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（声音从瀑布后传来，带着回音）喂——！我没事！这里面好得很！"
                },
                {
                    "角色": "群猴",
                    "内容": "（惊喜地）是石猴的声音！他还活着！"
                },
                {
                    "角色": "群猴",
                    "内容": "（好奇地）石猴，里面到底是什么样啊？真的没有怪物吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（兴奋地大喊）没有怪物！只有一个超级棒的山洞！快进来！有石桌子、石凳子，还有舒服的石床！这里就是我们永远的新家啦！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哦对了！这里还有一个大石碑，上面写着“水帘洞”！"
                },
                {
                    "角色": "旁白",
                    "内容": "石猴在洞里把好东西都看清楚了，然后又一次穿过瀑布，精神抖擞地跳回到了大家面前。"
                },
                {
                    "角色": "群猴",
                    "内容": "（爆发出欢呼）英雄！英雄回来啦！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你信守承诺，又勇敢无比！从今天起，你就是我们的王！请受我们一拜！"
                },
                {
                    "角色": "群猴",
                    "内容": "（齐声跪拜）拜见大王！千岁！千岁！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（得意地大笑）哈哈哈！都起来吧！从今天起，我不叫石猴了，就叫‘美猴王’！小的们，跟我进水帘洞，住我们的新家去喽！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们高兴地又叫又跳，排着队，跟着他们的美猴王，一个接一个地穿过瀑布，住进了这个又安全又漂亮的新家——水帘洞！瀑布后面，传来了他们久久不息的欢笑声……"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "就这样，许多年过去了。在美猴王的带领下，花果山的猴子们过着无忧无虑的日子。他们白天在山林里摘果子、做游戏，晚上就在水帘洞里开宴会。可是，就在一个和往常一样热闹的宴会上，看着伙伴们开心的样子，美猴王却突然安静了下来，轻轻地叹了一口气。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "唉……"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，您怎么了？有果子吃，有水喝，为什么还叹气呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们看，那朵花昨天还那么漂亮，今天就谢了。我担心，虽然我们现在很快乐，但如果有一天，我们都变老了，跳不动了，那该怎么办呢？"
                },
                {
                    "角色": "群猴",
                    "内容": "变老？我不要变老！大王，我们真的会变老吗？"
                },
                {
                    "角色": "群猴",
                    "内容": "呜呜呜……那可怎么办呀？变老是没办法改变的事情啊！我们只能等着不能玩的那一天到来吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（坚定地）不！我绝不答应！我们是花果山最快乐的猴子，我绝不允许大家失去这份快乐！一定有办法的！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空的话像一颗定心丸，小猴子们虽然还在难过，但都抬起头，满怀希望地看着他们的大王。就在这时，猴群里一只年纪最大的通背猿猴走了出来。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王说得对！办法总是有的。大王别担心，您能为大家想这么远，真是我们的好大王。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "老爷爷，你真的有办法吗？快告诉我！不管多难，我都要去试！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "我听说，世界上有会法术的神仙，他们就知道永远年轻快乐的秘密！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（眼睛一亮）神仙？真的吗？他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "他们就住在很远很远的地方，要翻过高山，渡过大海才能找到。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王听完，瞬间充满了力量。他挺起胸膛，眼神坚定地向所有猴子宣布。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "太好了！我决定了，明天我就出发，去寻找神仙，学那个永远快乐的秘密！等我学会了本领，就马上回来！到时候，我们就能永远在一起，永远都这么快乐了！"
                },
                {
                    "角色": "群猴",
                    "内容": "（擦干眼泪，欢呼）太棒了！大王最厉害了！我们支持大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "第二天，猴子们为美猴王准备了一场盛大的送行宴会。他们把最好吃的果子都拿了出来，围着美猴王又唱又跳。告别的时候，美猴王看着依依不舍的伙伴们，大声说："
                },
                {
                    "角色": "孙悟空",
                    "内容": "大家放心，我一定会回来的！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，他独自来到海边，用木头扎了一个小筏子，勇敢地向着无边无际的大海出发了。(音效：充满希望和冒险感的音乐响起，伴随着海浪声和风帆声)"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "风儿吹着帆，海浪推着船。不知道在海上漂了多久，美猴王的小木筏终于靠岸了。他跳上岸，走进了一片又高又密的森林里。他一边走，一边东瞧瞧西看看，忽然，一阵清脆的歌声和“铛、铛”的砍柴声传了过来。"
                },
                {
                    "角色": "樵夫",
                    "内容": "(歌唱) 要想学长生，就得有恒心，山里有神仙，本领大无边！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "咦？这是什么人在唱歌？听起来好像知道神仙在哪儿！"
                },
                {
                    "角色": "樵夫",
                    "内容": "(歌唱) 要想见神仙，不怕路途远，就在灵台山，能学真功夫！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空高兴坏了，他拨开挡路的树枝，顺着歌声和砍柴声找过去，果然看见一个正在砍柴的樵夫。他想也没想，一下子跳到樵夫面前，大声喊道："
                },
                {
                    "角色": "孙悟空",
                    "内容": "老神仙！我可找到你了！"
                },
                {
                    "角色": "旁白",
                    "内容": "这个樵夫大哥正专心砍柴呢，突然从树丛里跳出来一只毛茸茸的猴子，还叫他“老神仙”，吓得他“啊”地叫了一声，手里的斧头都掉在了地上。"
                },
                {
                    "角色": "樵夫",
                    "内容": "哎哟！你吓我一跳！你……你叫我什么？我可不是什么神仙。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你不是神仙？那你唱的歌里有神仙，你肯定知道神仙在哪儿！快告诉我！"
                },
                {
                    "角色": "樵夫",
                    "内容": "嘿！你这猴子怎么这么没礼貌？我为什么要告诉你？你突然跳出来吓唬人，还对我大喊大叫的！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(立刻变得委屈)对不起，对不起！我……我太着急了。我从很远很远的海上来，就是为了找神仙学本领，我找了好久好久，都快没力气了。"
                },
                {
                    "角色": "旁白",
                    "内容": "听到孙悟空这么说，樵夫心软了。他看着这只眼睛亮晶晶、一脸真诚的猴子，觉得他和其他猴子不太一样。"
                },
                {
                    "角色": "樵夫",
                    "内容": "(语气缓和下来)原来是这样啊。唉，看你这么诚心，我就告诉你吧。那位神仙就住在那座最高的山上，叫灵台方寸山，山里有个斜月三星洞。你顺着这条小路一直往南走，就能看到了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "灵台方寸山，斜月三星洞……太好了！谢谢你，好心的大哥！我这就去！"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，慢点！我还要砍柴回家照顾老母亲呢，你快去吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空拜别了樵夫，像一阵风似的，顺着小路向南边跑去。他翻过一座又一座山，终于看到了一座云雾缭绕的仙山。 (音效: 空灵的背景音乐、清脆的鸟鸣) 哇，这里简直就像仙境一样！他顺着山路往上爬，果然看见一个石洞，洞口上方刻着几个大字：灵台方寸山，斜月三星洞。洞门口，有几个仙童正在开心地扫地。孙悟空心里又紧张又激动，他整理了一下身上的叶子，鼓起勇气走了过去。"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "站住！你这只野猴子，这里是神仙学习法术的地方，不许乱闯！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "仙童哥哥别赶我走！我不是来捣乱的，我是真心想拜师学艺！求你通报一声，我想学习长生不老的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "仙童们看他这么诚恳，便进去通报。不一会儿，一位白发苍苍、面带微笑的老神仙走了出来，他就是须菩提祖师。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是你这猢狲要拜我为师？你姓什么呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我没姓。我是从石头里蹦出来的，没有爸爸妈妈。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(抚须微笑) 有趣。你既然是只猢狲，那我就给你取个姓，姓‘孙’吧。从今天起，你的法名就叫‘悟空’。孙悟空，你可愿意？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(高兴地磕头) 愿意愿意！我有名字啦！孙悟空！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "就这样，孙悟空在斜月三星洞住了下来。一转眼，七年过去了。这七年里，他每天跟着师兄们学写字、学礼貌，但一直没学到真正的长生不老法术。这一天，须菩提祖师在高台上讲课，终于把他叫到了跟前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你来我这儿也有七年了。今天，你想学些什么本领呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(充满期待地) 师父！我想学那种能永远快乐、永远年轻的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "须菩提祖师听了，忽然板起脸，故意装作生气的样子，走下讲台，拿起戒尺在悟空头上“咚、咚、咚”敲了三下。然后，他背着手，一言不发地走进了内院，还关上了中门。"
                },
                {
                    "角色": "仙童",
                    "内容": "悟空！你太不懂事了！你看，你把师父给气走了！"
                },
                {
                    "角色": "众仙",
                    "内容": "就是！师父讲得好好的，都被你打断了！这下我们都没得听了！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄们都责怪悟空，可悟空一点儿也不生气，反而心里有了主意，只是小声嘀咕。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(小声自语，带着一点委屈和自信) 哎呀，你们都误会师父了…这一定是个秘密暗号！敲我三下，是让我三更天去找他。他背着手从后门走，是让我从后门进去。师父是想悄悄教我真本领呢！"
                },
                {
                    "角色": "旁白",
                    "内容": "到了半夜三更，孙悟空悄悄来到祖师住处的后门，发现门果然留着一条小缝。他溜了进去，看见祖师正等着他呢。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(大笑) 哈哈哈！我就知道你是个天生的聪明猴儿！既然你猜到了，我就把真正的长生不老口诀传给你。"
                },
                {
                    "角色": "旁白",
                    "内容": "于是，祖师凑到悟空耳边，把奇妙的口诀悄悄传授给了他。 (音效: 能量流动的神奇音效) 孙悟空牢牢记在心里，一夜之间就学会了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，学会了长生之法，以后还可能会遇到很多危险。我再传你一些躲避危险的本领。我这里有天罡三十六变和地煞七十二变，你想学哪个？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，师父，我不想只学一点点，当然是学多的那个！弟子要学七十二变！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师点点头，又将七十二变的口诀传给了悟空。没过几天，聪明的悟空就练成了。但他发现自己虽然能变，却跑不快。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，虽然我会变了，可万一遇到跑得快的妖怪，我还是跑不掉啊。求您大发慈悲，再教我一个能飞得快的法术吧！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(故作严肃) 哦？你这猴头，真是贪心。刚学会了七十二变，还不够吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(着急地) 不够不够！要是妖怪追得比我快，我变成小虫子也会被抓住的！我一定要飞得比谁都快！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(大笑) 哈哈哈，好！有志气！看在你如此好学的份上，我再教你一个‘筋斗云’。只要念动咒语，一个跟头，就能飞出十万八千里！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "一个跟头十万八千里！太棒了！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "从此，孙悟空每天勤学苦练。没过多久，七十二变和筋斗云，他都练得滚瓜烂熟。他的本领越来越高，师兄们都对他又佩服又好奇。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这一天，师兄弟们在洞前的松树下玩耍，又围住了孙悟空。"
                },
                {
                    "角色": "众仙",
                    "内容": "悟空师弟，我们都知道你最厉害了！听说你把七十二变全都学会了，快变个东西给我们开开眼界吧！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（得意洋洋）嘿嘿，这有何难！师兄们瞧好了！"
                },
                {
                    "角色": "众仙",
                    "内容": "太好了！就变成眼前这棵大松树怎么样？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "没问题！看我的！变！"
                },
                {
                    "角色": "旁白",
                    "内容": "（音效：嗖！）只听“嗖”的一声，孙悟空果然变成了一棵和旁边一模一样的大松树。"
                },
                {
                    "角色": "众仙",
                    "内容": "（欢呼）哇！真的变成一棵松树了！太厉害了！好猴子！好猴子！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家正拍手叫好，一个严厉的声音突然响起。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（严肃地）你们在吵闹什么！成何体统！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家吓了一跳，回头一看，原来是师父来了！师兄们立刻安静下来。孙悟空也赶紧变回原样，慌张地想躲起来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你过来！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（低着头，小声地）师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我问你，为什么要当众卖弄你的本事？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（委屈地）我……我只是想让师兄们看看我的新本领，我们就是玩一玩……这有什么不对吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（着急地）糊涂！这怎么是玩呢！我教你的本领，是用来保护自己的，不是拿来炫耀的！如果被坏人知道了，他们会来抢你的本领，甚至会伤害你！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空这才明白师父是在担心自己，他吓得跪倒在地。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！求师父宽恕！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "唉，已经晚了。为了保护你，你必须马上离开这里。你从哪里来，就回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（不敢相信）什么？师父，您要赶我走？我还没报答您的恩情呢，我不想走！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（坚定地）不行！我正是为了保你的命，才必须让你走！你留在这里，早晚会惹来大祸！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空见师父心意已决，知道无法挽回，再也忍不住，伤心地大哭起来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（大哭）师父……呜呜……弟子舍不得您啊！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "别哭了！你给我听好！你走了以后，不管惹出多大的祸，都绝对不许说是我的徒弟！不然，那些坏人就会顺着线索找到这里，连累你的师兄们！你明白吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（擦干眼泪，郑重地）师父，我明白了！我发誓，绝不说出师父的名字！只说是我自己天生就会的！师父，您多保重！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空向师父重重地磕了个头，又朝师兄们挥了挥手，念动咒语，一个筋斗云，嗖——！（音效：急速划破长空的风声，然后渐弱）就朝着东边花果山的方向飞去了。"
                }
            ]
        }
    ]
}
    # script_proofreader = {'剧本审查':[]}
    # for index,script in enumerate(script_conflict_escalation_gemini['剧本']):
    #     tmp_script_structure =json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #     tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
    #     result = Proofreader(ori,tmp_script_structure,tmp_script)
    #     tmp_dict = {
    #         '场景':index+1,
    #         '审查结果':result['审查结果'],
    #         '问题清单': result['问题清单']
    #     }
    #     script_proofreader['剧本审查'].append(tmp_dict)
    # print(script_proofreader)


    # 迭代修正
    script_proofreader = {
	"剧本审查": [
        {
            "场景": 1,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 2,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 3,
            "审查结果": "需修改",
            "问题清单": [
                {
                    "维度": "目标一致性",
                    "问题描述": "场景改编目标中明确要求本场景要“建立一个充满智慧和善意的师徒初见场景”。但当前剧本在孙悟空到达洞口、看见仙童时便戛然而止，并未包含与菩提祖师的初次会面，导致场景未能达成其核心目标（转折、收束），结尾显得仓促。",
                    "修改建议": "请将场景延伸，以完成“初见”这一关键情节。建议在结尾增加孙悟空与仙童的初次对话，并被引入洞内见到菩提祖师的时刻。例如，可增加如下交互：孙悟空上前行礼，仙童回应“师父早已算出有修行者今日到访，命我在此等候”，然后引领悟空进入洞府。这样才能完成既定目标，使场景结构完整。"
                }
            ]
        },
        {
            "场景": 4,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 5,
            "审查结果": "通过",
            "问题清单": []
        }
    ]
}
    # refine_script = {'剧本':[]}
    # for index,result in enumerate(script_proofreader['剧本审查']):
    #     if result['审查结果'].strip() =='通过':
    #         refine_script['剧本'].append(script_conflict_escalation_gemini['剧本'][index])
    #         continue
    #     tmp_script_structure =json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #     tmp_script = json.dumps(script_conflict_escalation_gemini['剧本'][index], indent=4, ensure_ascii=False)
    #     tmp_feedback = json.dumps(script_proofreader['剧本审查'][index], indent=4, ensure_ascii=False)
    #     result = Script_Revision(ori,tmp_script_structure,tmp_script,tmp_feedback)
    #     refine_script['剧本'].append(result)
    # print(refine_script)

    refine_script = {
	"剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "在遥远的大海上，有一座美丽的花果山。山上的猴子们每天都快乐地玩耍、做游戏。其中，有一只与众不同的石猴，他呀，是从山顶上一块神奇的仙石里蹦出来的！"
                },
                {
                    "角色": "群猴",
                    "内容": "哈哈哈，快来追我呀！你抓不到我！"
                },
                {
                    "角色": "旁白",
                    "内容": "这一天，正当猴子们在小溪边追逐打闹时，一阵巨大的声音吸引了他们的注意。"
                },
                {
                    "角色": "群猴",
                    "内容": "（兴奋地）哇！好大的瀑布！真想进去看看里面有什么！"
                },
                {
                    "角色": "群猴",
                    "内容": "（害怕地）不行不行！声音那么大，里面肯定有大怪物！我可不敢去！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大家安静！我倒是有个主意。我们猴子一直没有大王，谁有本事跳进这瀑布，再平平安安地出来，我们就拜他为王！"
                },
                {
                    "角色": "群猴",
                    "内容": "（小声议论）当大王？听起来好棒……可是，谁敢啊？"
                },
                {
                    "角色": "群猴",
                    "内容": "（缩着脖子）我不敢，我不敢……"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们你看看我，我看看你，都害怕得往后退。就在这时，那只勇敢的石猴从猴群里跳了出来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（大声地）你们都不敢，我敢！我来！"
                },
                {
                    "角色": "群猴",
                    "内容": "（着急地）石猴，别去！你不要命啦？万一你回不来怎么办？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（坚定地）哼，胆小鬼！你们就在这儿好好看着！我不仅要进去，还要当你们的大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，石猴深吸一口气，闭上眼睛，“嗖”地一下，真的跳进了瀑布里！水花溅得好高好高。"
                },
                {
                    "角色": "群猴",
                    "内容": "啊！他真的跳进去了！"
                },
                {
                    "角色": "群猴",
                    "内容": "（担忧地）他……他不会被水冲走了吧？怎么一点声音都没有了？"
                },
                {
                    "角色": "旁白",
                    "内容": "原来，瀑布后面根本不是水，而是一座亮晶晶的铁板桥！石猴穿过水帘，稳稳地落在了桥上。他睁开眼一看，桥对面是一个又大又干爽的山洞，他太惊喜了，赶紧朝着外面大喊。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（声音从瀑布后传来，带着回音）喂——！我没事！这里面好得很！"
                },
                {
                    "角色": "群猴",
                    "内容": "（惊喜地）是石猴的声音！他还活着！"
                },
                {
                    "角色": "群猴",
                    "内容": "（好奇地）石猴，里面到底是什么样啊？真的没有怪物吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（兴奋地大喊）没有怪物！只有一个超级棒的山洞！快进来！有石桌子、石凳子，还有舒服的石床！这里就是我们永远的新家啦！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哦对了！这里还有一个大石碑，上面写着“水帘洞”！"
                },
                {
                    "角色": "旁白",
                    "内容": "石猴在洞里把好东西都看清楚了，然后又一次穿过瀑布，精神抖擞地跳回到了大家面前。"
                },
                {
                    "角色": "群猴",
                    "内容": "（爆发出欢呼）英雄！英雄回来啦！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你信守承诺，又勇敢无比！从今天起，你就是我们的王！请受我们一拜！"
                },
                {
                    "角色": "群猴",
                    "内容": "（齐声跪拜）拜见大王！千岁！千岁！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（得意地大笑）哈哈哈！都起来吧！从今天起，我不叫石猴了，就叫‘美猴王’！小的们，跟我进水帘洞，住我们的新家去喽！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们高兴地又叫又跳，排着队，跟着他们的美猴王，一个接一个地穿过瀑布，住进了这个又安全又漂亮的新家——水帘洞！瀑布后面，传来了他们久久不息的欢笑声……"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "就这样，许多年过去了。在美猴王的带领下，花果山的猴子们过着无忧无虑的日子。他们白天在山林里摘果子、做游戏，晚上就在水帘洞里开宴会。可是，就在一个和往常一样热闹的宴会上，看着伙伴们开心的样子，美猴王却突然安静了下来，轻轻地叹了一口气。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "唉……"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，您怎么了？有果子吃，有水喝，为什么还叹气呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们看，那朵花昨天还那么漂亮，今天就谢了。我担心，虽然我们现在很快乐，但如果有一天，我们都变老了，跳不动了，那该怎么办呢？"
                },
                {
                    "角色": "群猴",
                    "内容": "变老？我不要变老！大王，我们真的会变老吗？"
                },
                {
                    "角色": "群猴",
                    "内容": "呜呜呜……那可怎么办呀？变老是没办法改变的事情啊！我们只能等着不能玩的那一天到来吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（坚定地）不！我绝不答应！我们是花果山最快乐的猴子，我绝不允许大家失去这份快乐！一定有办法的！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空的话像一颗定心丸，小猴子们虽然还在难过，但都抬起头，满怀希望地看着他们的大王。就在这时，猴群里一只年纪最大的通背猿猴走了出来。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王说得对！办法总是有的。大王别担心，您能为大家想这么远，真是我们的好大王。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "老爷爷，你真的有办法吗？快告诉我！不管多难，我都要去试！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "我听说，世界上有会法术的神仙，他们就知道永远年轻快乐的秘密！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（眼睛一亮）神仙？真的吗？他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "他们就住在很远很远的地方，要翻过高山，渡过大海才能找到。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王听完，瞬间充满了力量。他挺起胸膛，眼神坚定地向所有猴子宣布。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "太好了！我决定了，明天我就出发，去寻找神仙，学那个永远快乐的秘密！等我学会了本领，就马上回来！到时候，我们就能永远在一起，永远都这么快乐了！"
                },
                {
                    "角色": "群猴",
                    "内容": "（擦干眼泪，欢呼）太棒了！大王最厉害了！我们支持大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "第二天，猴子们为美猴王准备了一场盛大的送行宴会。他们把最好吃的果子都拿了出来，围着美猴王又唱又跳。告别的时候，美猴王看着依依不舍的伙伴们，大声说："
                },
                {
                    "角色": "孙悟空",
                    "内容": "大家放心，我一定会回来的！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，他独自来到海边，用木头扎了一个小筏子，勇敢地向着无边无际的大海出发了。(音效：充满希望和冒险感的音乐响起，伴随着海浪声和风帆声)"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "风儿吹着帆，海浪推着船。不知道在海上漂了多久，美猴王的小木筏终于靠岸了。他跳上岸，走进了一片又高又密的森林里。他一边走，一边东瞧瞧西看看，忽然，一阵清脆的歌声和“铛、铛”的砍柴声传了过来。"
                },
                {
                    "角色": "樵夫",
                    "内容": "(歌唱) 要想学长生，就得有恒心，山里有神仙，本领大无边！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "咦？这是什么人在唱歌？听起来好像知道神仙在哪儿！"
                },
                {
                    "角色": "樵夫",
                    "内容": "(歌唱) 要想见神仙，不怕路途远，就在灵台山，能学真功夫！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空高兴坏了，他拨开挡路的树枝，顺着歌声和砍柴声找过去，果然看见一个正在砍柴的樵夫。他想也没想，一下子跳到樵夫面前，大声喊道："
                },
                {
                    "角色": "孙悟空",
                    "内容": "老神仙！我可找到你了！"
                },
                {
                    "角色": "旁白",
                    "内容": "这个樵夫大哥正专心砍柴呢，突然从树丛里跳出来一只毛茸茸的猴子，还叫他“老神仙”，吓得他“啊”地叫了一声，手里的斧头都掉在了地上。"
                },
                {
                    "角色": "樵夫",
                    "内容": "哎哟！你吓我一跳！你……你叫我什么？我可不是什么神仙。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你不是神仙？那你唱的歌里有神仙，你肯定知道神仙在哪儿！快告诉我！"
                },
                {
                    "角色": "樵夫",
                    "内容": "嘿！你这猴子怎么这么没礼貌？我为什么要告诉你？你突然跳出来吓唬人，还对我大喊大叫的！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(立刻变得委屈)对不起，对不起！我……我太着急了。我从很远很远的海上来，就是为了找神仙学本领，我找了好久好久，都快没力气了。"
                },
                {
                    "角色": "旁白",
                    "内容": "听到孙悟空这么说，樵夫心软了。他看着这只眼睛亮晶晶、一脸真诚的猴子，觉得他和其他猴子不太一样。"
                },
                {
                    "角色": "樵夫",
                    "内容": "(语气缓和下来)原来是这样啊。唉，看你这么诚心，我就告诉你吧。那位神仙就住在那座最高的山上，叫灵台方寸山，山里有个斜月三星洞。你顺着这条小路一直往南走，就能看到了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "灵台方寸山，斜月三星洞……太好了！谢谢你，好心的大哥！我这就去！"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，慢点！我还要砍柴回家照顾老母亲呢，你快去吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空拜别了樵夫，像一阵风似的，顺着小路向南边跑去。他翻过一座又一座山，终于看到了一座云雾缭绕的仙山。 (音效: 空灵的背景音乐、清脆的鸟鸣) 哇，这里简直就像仙境一样！他顺着山路往上爬，果然看见一个石洞，洞口上方刻着几个大字：灵台方寸山，斜月三星洞。洞门口，一个仙童正在开心地扫地。孙悟空心里又紧张又激动，他整理了一下身上的叶子，鼓起勇气走了过去。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(走上前，恭敬地行了个礼)这位仙童，你好。我是来拜师学艺的。"
                },
                {
                    "角色": "仙童",
                    "内容": "(停下扫帚，微笑着)你总算来啦。师父一早就跟我说，今天会有一个真心求道的徒弟来，让我出来迎接。说的就是你吧？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(又惊又喜)啊？神仙师父已经知道我要来了？太好了！太好了！"
                },
                {
                    "角色": "仙童",
                    "内容": "当然啦。你跟我来吧，师父正在里面等你呢。"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空跟着仙童走进洞里，只见洞府深邃，别有洞天。在最里面的高台上，一位白发白须、面容慈祥的老神仙正端坐着，他就是菩提祖师。孙悟空一看见他，就知道这才是自己要找的真神仙，立刻跑上前去，跪倒在地。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(激动地磕头)师父在上！请受弟子一拜！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "站住！你这只野猴子，这里是神仙学习法术的地方，不许乱闯！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "仙童哥哥别赶我走！我不是来捣乱的，我是真心想拜师学艺！求你通报一声，我想学习长生不老的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "仙童们看他这么诚恳，便进去通报。不一会儿，一位白发苍苍、面带微笑的老神仙走了出来，他就是须菩提祖师。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是你这猢狲要拜我为师？你姓什么呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我没姓。我是从石头里蹦出来的，没有爸爸妈妈。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(抚须微笑) 有趣。你既然是只猢狲，那我就给你取个姓，姓‘孙’吧。从今天起，你的法名就叫‘悟空’。孙悟空，你可愿意？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(高兴地磕头) 愿意愿意！我有名字啦！孙悟空！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "就这样，孙悟空在斜月三星洞住了下来。一转眼，七年过去了。这七年里，他每天跟着师兄们学写字、学礼貌，但一直没学到真正的长生不老法术。这一天，须菩提祖师在高台上讲课，终于把他叫到了跟前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你来我这儿也有七年了。今天，你想学些什么本领呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(充满期待地) 师父！我想学那种能永远快乐、永远年轻的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "须菩提祖师听了，忽然板起脸，故意装作生气的样子，走下讲台，拿起戒尺在悟空头上“咚、咚、咚”敲了三下。然后，他背着手，一言不发地走进了内院，还关上了中门。"
                },
                {
                    "角色": "仙童",
                    "内容": "悟空！你太不懂事了！你看，你把师父给气走了！"
                },
                {
                    "角色": "众仙",
                    "内容": "就是！师父讲得好好的，都被你打断了！这下我们都没得听了！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄们都责怪悟空，可悟空一点儿也不生气，反而心里有了主意，只是小声嘀咕。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(小声自语，带着一点委屈和自信) 哎呀，你们都误会师父了…这一定是个秘密暗号！敲我三下，是让我三更天去找他。他背着手从后门走，是让我从后门进去。师父是想悄悄教我真本领呢！"
                },
                {
                    "角色": "旁白",
                    "内容": "到了半夜三更，孙悟空悄悄来到祖师住处的后门，发现门果然留着一条小缝。他溜了进去，看见祖师正等着他呢。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(大笑) 哈哈哈！我就知道你是个天生的聪明猴儿！既然你猜到了，我就把真正的长生不老口诀传给你。"
                },
                {
                    "角色": "旁白",
                    "内容": "于是，祖师凑到悟空耳边，把奇妙的口诀悄悄传授给了他。 (音效: 能量流动的神奇音效) 孙悟空牢牢记在心里，一夜之间就学会了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，学会了长生之法，以后还可能会遇到很多危险。我再传你一些躲避危险的本领。我这里有天罡三十六变和地煞七十二变，你想学哪个？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，师父，我不想只学一点点，当然是学多的那个！弟子要学七十二变！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师点点头，又将七十二变的口诀传给了悟空。没过几天，聪明的悟空就练成了。但他发现自己虽然能变，却跑不快。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，虽然我会变了，可万一遇到跑得快的妖怪，我还是跑不掉啊。求您大发慈悲，再教我一个能飞得快的法术吧！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(故作严肃) 哦？你这猴头，真是贪心。刚学会了七十二变，还不够吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "(着急地) 不够不够！要是妖怪追得比我快，我变成小虫子也会被抓住的！我一定要飞得比谁都快！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "(大笑) 哈哈哈，好！有志气！看在你如此好学的份上，我再教你一个‘筋斗云’。只要念动咒语，一个跟头，就能飞出十万八千里！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "一个跟头十万八千里！太棒了！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "从此，孙悟空每天勤学苦练。没过多久，七十二变和筋斗云，他都练得滚瓜烂熟。他的本领越来越高，师兄们都对他又佩服又好奇。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这一天，师兄弟们在洞前的松树下玩耍，又围住了孙悟空。"
                },
                {
                    "角色": "众仙",
                    "内容": "悟空师弟，我们都知道你最厉害了！听说你把七十二变全都学会了，快变个东西给我们开开眼界吧！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（得意洋洋）嘿嘿，这有何难！师兄们瞧好了！"
                },
                {
                    "角色": "众仙",
                    "内容": "太好了！就变成眼前这棵大松树怎么样？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "没问题！看我的！变！"
                },
                {
                    "角色": "旁白",
                    "内容": "（音效：嗖！）只听“嗖”的一声，孙悟空果然变成了一棵和旁边一模一样的大松树。"
                },
                {
                    "角色": "众仙",
                    "内容": "（欢呼）哇！真的变成一棵松树了！太厉害了！好猴子！好猴子！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家正拍手叫好，一个严厉的声音突然响起。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（严肃地）你们在吵闹什么！成何体统！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家吓了一跳，回头一看，原来是师父来了！师兄们立刻安静下来。孙悟空也赶紧变回原样，慌张地想躲起来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你过来！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（低着头，小声地）师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我问你，为什么要当众卖弄你的本事？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（委屈地）我……我只是想让师兄们看看我的新本领，我们就是玩一玩……这有什么不对吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（着急地）糊涂！这怎么是玩呢！我教你的本领，是用来保护自己的，不是拿来炫耀的！如果被坏人知道了，他们会来抢你的本领，甚至会伤害你！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空这才明白师父是在担心自己，他吓得跪倒在地。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！求师父宽恕！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "唉，已经晚了。为了保护你，你必须马上离开这里。你从哪里来，就回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（不敢相信）什么？师父，您要赶我走？我还没报答您的恩情呢，我不想走！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "（坚定地）不行！我正是为了保你的命，才必须让你走！你留在这里，早晚会惹来大祸！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空见师父心意已决，知道无法挽回，再也忍不住，伤心地大哭起来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（大哭）师父……呜呜……弟子舍不得您啊！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "别哭了！你给我听好！你走了以后，不管惹出多大的祸，都绝对不许说是我的徒弟！不然，那些坏人就会顺着线索找到这里，连累你的师兄们！你明白吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "（擦干眼泪，郑重地）师父，我明白了！我发誓，绝不说出师父的名字！只说是我自己天生就会的！师父，您多保重！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空向师父重重地磕了个头，又朝师兄们挥了挥手，念动咒语，一个筋斗云，嗖——！（音效：急速划破长空的风声，然后渐弱）就朝着东边花果山的方向飞去了。"
                }
            ]
        }
    ]
}
    refine_script = remove_parentheses_in_script(refine_script)  # 去除语气标注等
    print(refine_script)
    refine_script2 = normalize_script_characters(refine_script,character_list)
    print(refine_script2)
    refine_script = {"剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "在遥远的大海上，有一座美丽的花果山。山上的猴子们每天都快乐地玩耍、做游戏。其中，有一只与众不同的石猴，他呀，是从山顶上一块神奇的仙石里蹦出来的！"
                },
                {
                    "角色": "群猴",
                    "内容": "哈哈哈，快来追我呀！你抓不到我！"
                },
                {
                    "角色": "旁白",
                    "内容": "这一天，正当猴子们在小溪边追逐打闹时，一阵巨大的声音吸引了他们的注意。"
                },
                {
                    "角色": "群猴",
                    "内容": "哇！好大的瀑布！真想进去看看里面有什么！"
                },
                {
                    "角色": "群猴",
                    "内容": "不行不行！声音那么大，里面肯定有大怪物！我可不敢去！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大家安静！我倒是有个主意。我们猴子一直没有大王，谁有本事跳进这瀑布，再平平安安地出来，我们就拜他为王！"
                },
                {
                    "角色": "群猴",
                    "内容": "当大王？听起来好棒……可是，谁敢啊？"
                },
                {
                    "角色": "群猴",
                    "内容": "我不敢，我不敢……"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们你看看我，我看看你，都害怕得往后退。就在这时，那只勇敢的石猴从猴群里跳了出来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们都不敢，我敢！我来！"
                },
                {
                    "角色": "群猴",
                    "内容": "石猴，别去！你不要命啦？万一你回不来怎么办？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哼，胆小鬼！你们就在这儿好好看着！我不仅要进去，还要当你们的大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，石猴深吸一口气，闭上眼睛，“嗖”地一下，真的跳进了瀑布里！水花溅得好高好高。"
                },
                {
                    "角色": "群猴",
                    "内容": "啊！他真的跳进去了！"
                },
                {
                    "角色": "群猴",
                    "内容": "他……他不会被水冲走了吧？怎么一点声音都没有了？"
                },
                {
                    "角色": "旁白",
                    "内容": "原来，瀑布后面根本不是水，而是一座亮晶晶的铁板桥！石猴穿过水帘，稳稳地落在了桥上。他睁开眼一看，桥对面是一个又大又干爽的山洞，他太惊喜了，赶紧朝着外面大喊。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "喂——！我没事！这里面好得很！"
                },
                {
                    "角色": "群猴",
                    "内容": "是石猴的声音！他还活着！"
                },
                {
                    "角色": "群猴",
                    "内容": "石猴，里面到底是什么样啊？真的没有怪物吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "没有怪物！只有一个超级棒的山洞！快进来！有石桌子、石凳子，还有舒服的石床！这里就是我们永远的新家啦！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哦对了！这里还有一个大石碑，上面写着“水帘洞”！"
                },
                {
                    "角色": "旁白",
                    "内容": "石猴在洞里把好东西都看清楚了，然后又一次穿过瀑布，精神抖擞地跳回到了大家面前。"
                },
                {
                    "角色": "群猴",
                    "内容": "英雄！英雄回来啦！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你信守承诺，又勇敢无比！从今天起，你就是我们的王！请受我们一拜！"
                },
                {
                    "角色": "群猴",
                    "内容": "拜见大王！千岁！千岁！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哈哈哈！都起来吧！从今天起，我不叫石猴了，就叫‘美猴王’！小的们，跟我进水帘洞，住我们的新家去喽！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴子们高兴地又叫又跳，排着队，跟着他们的美猴王，一个接一个地穿过瀑布，住进了这个又安全又漂亮的新家——水帘洞！瀑布后面，传来了他们久久不息的欢笑声……"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "就这样，许多年过去了。在美猴王的带领下，花果山的猴子们过着无忧无虑的日子。他们白天在山林里摘果子、做游戏，晚上就在水帘洞里开宴会。可是，就在一个和往常一样热闹的宴会上，看着伙伴们开心的样子，美猴王却突然安静了下来，轻轻地叹了一口气。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "唉……"
                },
                {
                    "角色": "群猴",
                    "内容": "大王，您怎么了？有果子吃，有水喝，为什么还叹气呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你们看，那朵花昨天还那么漂亮，今天就谢了。我担心，虽然我们现在很快乐，但如果有一天，我们都变老了，跳不动了，那该怎么办呢？"
                },
                {
                    "角色": "群猴",
                    "内容": "变老？我不要变老！大王，我们真的会变老吗？"
                },
                {
                    "角色": "群猴",
                    "内容": "呜呜呜……那可怎么办呀？变老是没办法改变的事情啊！我们只能等着不能玩的那一天到来吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不！我绝不答应！我们是花果山最快乐的猴子，我绝不允许大家失去这份快乐！一定有办法的！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空的话像一颗定心丸，小猴子们虽然还在难过，但都抬起头，满怀希望地看着他们的大王。就在这时，猴群里一只年纪最大的通背猿猴走了出来。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王说得对！办法总是有的。大王别担心，您能为大家想这么远，真是我们的好大王。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "老爷爷，你真的有办法吗？快告诉我！不管多难，我都要去试！"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "我听说，世界上有会法术的神仙，他们就知道永远年轻快乐的秘密！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "神仙？真的吗？他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "他们就住在很远很远的地方，要翻过高山，渡过大海才能找到。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王听完，瞬间充满了力量。他挺起胸膛，眼神坚定地向所有猴子宣布。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "太好了！我决定了，明天我就出发，去寻找神仙，学那个永远快乐的秘密！等我学会了本领，就马上回来！到时候，我们就能永远在一起，永远都这么快乐了！"
                },
                {
                    "角色": "群猴",
                    "内容": "太棒了！大王最厉害了！我们支持大王！"
                },
                {
                    "角色": "旁白",
                    "内容": "第二天，猴子们为美猴王准备了一场盛大的送行宴会。他们把最好吃的果子都拿了出来，围着美猴王又唱又跳。告别的时候，美猴王看着依依不舍的伙伴们，大声说："
                },
                {
                    "角色": "孙悟空",
                    "内容": "大家放心，我一定会回来的！"
                },
                {
                    "角色": "旁白",
                    "内容": "说完，他独自来到海边，用木头扎了一个小筏子，勇敢地向着无边无际的大海出发了。"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "风儿吹着帆，海浪推着船。不知道在海上漂了多久，美猴王的小木筏终于靠岸了。他跳上岸，走进了一片又高又密的森林里。他一边走，一边东瞧瞧西看看，忽然，一阵清脆的歌声和“铛、铛”的砍柴声传了过来。"
                },
                {
                    "角色": "樵夫",
                    "内容": "要想学长生，就得有恒心，山里有神仙，本领大无边！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "咦？这是什么人在唱歌？听起来好像知道神仙在哪儿！"
                },
                {
                    "角色": "樵夫",
                    "内容": "要想见神仙，不怕路途远，就在灵台山，能学真功夫！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空高兴坏了，他拨开挡路的树枝，顺着歌声和砍柴声找过去，果然看见一个正在砍柴的樵夫。他想也没想，一下子跳到樵夫面前，大声喊道："
                },
                {
                    "角色": "孙悟空",
                    "内容": "老神仙！我可找到你了！"
                },
                {
                    "角色": "旁白",
                    "内容": "这个樵夫大哥正专心砍柴呢，突然从树丛里跳出来一只毛茸茸的猴子，还叫他“老神仙”，吓得他“啊”地叫了一声，手里的斧头都掉在了地上。"
                },
                {
                    "角色": "樵夫",
                    "内容": "哎哟！你吓我一跳！你……你叫我什么？我可不是什么神仙。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "你不是神仙？那你唱的歌里有神仙，你肯定知道神仙在哪儿！快告诉我！"
                },
                {
                    "角色": "樵夫",
                    "内容": "嘿！你这猴子怎么这么没礼貌？我为什么要告诉你？你突然跳出来吓唬人，还对我大喊大叫的！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "对不起，对不起！我……我太着急了。我从很远很远的海上来，就是为了找神仙学本领，我找了好久好久，都快没力气了。"
                },
                {
                    "角色": "旁白",
                    "内容": "听到孙悟空这么说，樵夫心软了。他看着这只眼睛亮晶晶、一脸真诚的猴子，觉得他和其他猴子不太一样。"
                },
                {
                    "角色": "樵夫",
                    "内容": "原来是这样啊。唉，看你这么诚心，我就告诉你吧。那位神仙就住在那座最高的山上，叫灵台方寸山，山里有个斜月三星洞。你顺着这条小路一直往南走，就能看到了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "灵台方寸山，斜月三星洞……太好了！谢谢你，好心的大哥！我这就去！"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，慢点！我还要砍柴回家照顾老母亲呢，你快去吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空拜别了樵夫，像一阵风似的，顺着小路向南边跑去。他翻过一座又一座山，终于看到了一座云雾缭绕的仙山。  哇，这里简直就像仙境一样！他顺着山路往上爬，果然看见一个石洞，洞口上方刻着几个大字：灵台方寸山，斜月三星洞。洞门口，一个仙童正在开心地扫地。孙悟空心里又紧张又激动，他整理了一下身上的叶子，鼓起勇气走了过去。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "这位仙童，你好。我是来拜师学艺的。"
                },
                {
                    "角色": "仙童",
                    "内容": "你总算来啦。师父一早就跟我说，今天会有一个真心求道的徒弟来，让我出来迎接。说的就是你吧？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "啊？神仙师父已经知道我要来了？太好了！太好了！"
                },
                {
                    "角色": "仙童",
                    "内容": "当然啦。你跟我来吧，师父正在里面等你呢。"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空跟着仙童走进洞里，只见洞府深邃，别有洞天。在最里面的高台上，一位白发白须、面容慈祥的老神仙正端坐着，他就是菩提祖师。孙悟空一看见他，就知道这才是自己要找的真神仙，立刻跑上前去，跪倒在地。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父在上！请受弟子一拜！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "站住！你这只野猴子，这里是神仙学习法术的地方，不许乱闯！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "仙童哥哥别赶我走！我不是来捣乱的，我是真心想拜师学艺！求你通报一声，我想学习长生不老的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "仙童们看他这么诚恳，便进去通报。不一会儿，一位白发苍苍、面带微笑的老神仙走了出来，他就是须菩提祖师。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是你这猢狲要拜我为师？你姓什么呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我没姓。我是从石头里蹦出来的，没有爸爸妈妈。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "有趣。你既然是只猢狲，那我就给你取个姓，姓‘孙’吧。从今天起，你的法名就叫‘悟空’。孙悟空，你可愿意？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "愿意愿意！我有名字啦！孙悟空！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "就这样，孙悟空在斜月三星洞住了下来。一转眼，七年过去了。这七年里，他每天跟着师兄们学写字、学礼貌，但一直没学到真正的长生不老法术。这一天，须菩提祖师在高台上讲课，终于把他叫到了跟前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你来我这儿也有七年了。今天，你想学些什么本领呀？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！我想学那种能永远快乐、永远年轻的本领！"
                },
                {
                    "角色": "旁白",
                    "内容": "须菩提祖师听了，忽然板起脸，故意装作生气的样子，走下讲台，拿起戒尺在悟空头上“咚、咚、咚”敲了三下。然后，他背着手，一言不发地走进了内院，还关上了中门。"
                },
                {
                    "角色": "仙童",
                    "内容": "悟空！你太不懂事了！你看，你把师父给气走了！"
                },
                {
                    "角色": "众仙",
                    "内容": "就是！师父讲得好好的，都被你打断了！这下我们都没得听了！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄们都责怪悟空，可悟空一点儿也不生气，反而心里有了主意，只是小声嘀咕。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "哎呀，你们都误会师父了…这一定是个秘密暗号！敲我三下，是让我三更天去找他。他背着手从后门走，是让我从后门进去。师父是想悄悄教我真本领呢！"
                },
                {
                    "角色": "旁白",
                    "内容": "到了半夜三更，孙悟空悄悄来到祖师住处的后门，发现门果然留着一条小缝。他溜了进去，看见祖师正等着他呢。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哈哈哈！我就知道你是个天生的聪明猴儿！既然你猜到了，我就把真正的长生不老口诀传给你。"
                },
                {
                    "角色": "旁白",
                    "内容": "于是，祖师凑到悟空耳边，把奇妙的口诀悄悄传授给了他。  孙悟空牢牢记在心里，一夜之间就学会了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，学会了长生之法，以后还可能会遇到很多危险。我再传你一些躲避危险的本领。我这里有天罡三十六变和地煞七十二变，你想学哪个？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，师父，我不想只学一点点，当然是学多的那个！弟子要学七十二变！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师点点头，又将七十二变的口诀传给了悟空。没过几天，聪明的悟空就练成了。但他发现自己虽然能变，却跑不快。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，虽然我会变了，可万一遇到跑得快的妖怪，我还是跑不掉啊。求您大发慈悲，再教我一个能飞得快的法术吧！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哦？你这猴头，真是贪心。刚学会了七十二变，还不够吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不够不够！要是妖怪追得比我快，我变成小虫子也会被抓住的！我一定要飞得比谁都快！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哈哈哈，好！有志气！看在你如此好学的份上，我再教你一个‘筋斗云’。只要念动咒语，一个跟头，就能飞出十万八千里！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "一个跟头十万八千里！太棒了！谢谢师父！谢谢师父！"
                },
                {
                    "角色": "旁白",
                    "内容": "从此，孙悟空每天勤学苦练。没过多久，七十二变和筋斗云，他都练得滚瓜烂熟。他的本领越来越高，师兄们都对他又佩服又好奇。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这一天，师兄弟们在洞前的松树下玩耍，又围住了孙悟空。"
                },
                {
                    "角色": "众仙",
                    "内容": "悟空师弟，我们都知道你最厉害了！听说你把七十二变全都学会了，快变个东西给我们开开眼界吧！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "嘿嘿，这有何难！师兄们瞧好了！"
                },
                {
                    "角色": "众仙",
                    "内容": "太好了！就变成眼前这棵大松树怎么样？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "没问题！看我的！变！"
                },
                {
                    "角色": "旁白",
                    "内容": "只听“嗖”的一声，孙悟空果然变成了一棵和旁边一模一样的大松树。"
                },
                {
                    "角色": "众仙",
                    "内容": "哇！真的变成一棵松树了！太厉害了！好猴子！好猴子！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家正拍手叫好，一个严厉的声音突然响起。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你们在吵闹什么！成何体统！"
                },
                {
                    "角色": "旁白",
                    "内容": "大家吓了一跳，回头一看，原来是师父来了！师兄们立刻安静下来。孙悟空也赶紧变回原样，慌张地想躲起来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你过来！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我问你，为什么要当众卖弄你的本事？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我……我只是想让师兄们看看我的新本领，我们就是玩一玩……这有什么不对吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "糊涂！这怎么是玩呢！我教你的本领，是用来保护自己的，不是拿来炫耀的！如果被坏人知道了，他们会来抢你的本领，甚至会伤害你！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空这才明白师父是在担心自己，他吓得跪倒在地。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！求师父宽恕！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "唉，已经晚了。为了保护你，你必须马上离开这里。你从哪里来，就回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "什么？师父，您要赶我走？我还没报答您的恩情呢，我不想走！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "不行！我正是为了保你的命，才必须让你走！你留在这里，早晚会惹来大祸！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空见师父心意已决，知道无法挽回，再也忍不住，伤心地大哭起来。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……呜呜……弟子舍不得您啊！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "别哭了！你给我听好！你走了以后，不管惹出多大的祸，都绝对不许说是我的徒弟！不然，那些坏人就会顺着线索找到这里，连累你的师兄们！你明白吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，我明白了！我发誓，绝不说出师父的名字！只说是我自己天生就会的！师父，您多保重！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空向师父重重地磕了个头，又朝师兄们挥了挥手，念动咒语，一个筋斗云，嗖——！就朝着东边花果山的方向飞去了。"
                }
            ]
        }
    ]
}

    # 语气标注，暂时不考虑把改编大纲加入进来
    # Emotion = {'语气标注': []}
    # for index,script in enumerate(refine_script['剧本']):
    #     # tmp_script_structure = json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #     str_script = script_to_annotated_string_by_scene(script)
    #     tmp_character = []
    #     character_profiles_in_script = extract_character_profiles(script, character_gemini)
    #     for value in character_profiles_in_script.values():
    #         tmp_character.append({
    #         "规范化名称": value.get("规范化名称", ""),
    #         "别名": value.get("别名", []),
    #         "性格特征": value.get("性格特征", []),
    #         "性别":value.get("性别","")
    #     })
    #     tmp_character2 = json.dumps(tmp_character, indent=4, ensure_ascii=False)
    #     result = Emotional_Guidance(tmp_character2,str_script)
    #     Emotion['语气标注'].append(result)

    Emotion = {
	"语气标注": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "亲切友好，像讲故事的大哥哥/大姐姐。语速平稳，说到“神奇的仙石里蹦出来的”，可以带一点神秘和惊奇感，音调略微上扬。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "非常开心、活泼的嬉闹声。音调高，语速快，像是在追逐打闹中喊出来的，可以带着天真的笑声和一点点喘息声。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "语气从平稳的讲述转向悬念。说到“巨大的声音”时，语速可以放慢一点，声音略微压低，营造出神秘和好奇的氛围。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "充满惊奇和赞叹。音调扬起，“哇！”要拖长一点，表现出被瀑布的宏伟景象震撼到了，后半句充满向往和好奇。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "害怕和退缩。音量变小，语速加快，声音有点发抖，像是在小声地跟同伴说，表达出对未知的恐惧，可以带一点往后缩的感觉。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "沉稳而有智慧。作为长者，音调平稳，不急不躁。提出主意时，语气变得清晰、有力，带着不容置疑的权威感和一点点小小的狡黠。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "先是小声的、充满向往的嘀咕，对“当大王”感到兴奋；然后迅速转为胆怯和犹豫，音量降低，互相询问，带着不确定。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "胆小、怯懦。声音发虚，语速快，像是急忙摆手拒绝的样子，可以加上一点吸鼻子的声音或者小声的呜咽，表现出极度的害怕。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "营造紧张感，然后引出英雄。前半句描述猴子们的害怕，语气可以轻柔一些；当说到“勇敢的石猴从猴群里跳了出来”，语气要变得果断、响亮，充满期待。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "勇敢、自信、充满挑战精神。声音洪亮，音调高，语速坚定有力，展现出石猴与众不同的胆识和天不怕地不怕的英雄气概。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "焦急和关心。音调提高，语速快，带着真诚的担忧，是真的在为石猴担心，想要大声劝阻他。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "骄傲、略带轻蔑。开头“哼”一声，带着对同伴胆小的不屑。说话时昂首挺胸，充满自信和决心，向大家宣告自己的目标，不容置疑。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "充满动感和紧张感。语速加快，描述动作要干净利落。“嗖”地一下要读得短促有力，模仿飞速跳跃的感觉。结尾带上赞叹。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "极度震惊和不敢相信。音调高，拖长音喊出来，像是亲眼目睹了不可思议的事情，目瞪口呆。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "担忧、害怕、声音发颤。语速变慢，音量减小，带着哭腔和不祥的猜测，充满了恐惧。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "揭晓谜底的惊喜感。开头“原来”要带有恍然大悟的感觉。描述铁板桥和山洞时，语气充满惊奇和赞叹。最后描述石猴大喊时，情绪要饱满，为下一句台词铺垫。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "兴奋、喜悦、声音洪亮。像是在山洞里隔着瀑布朝外面大喊，声音可以带一点回声感，充满发现新大陆的激动和得意。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "喜出望外。从刚才的担忧中解脱出来，声音里充满了巨大的惊喜和宽慰，是发自内心的欢呼。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "好奇、急切。语速快，音调高，像一群小孩子七嘴八舌地追问，充满了对瀑布后面世界的好奇心。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "极其兴奋和自豪。语速很快，像是在献宝一样，热情地向同伴们介绍自己的伟大发现。说到“永远的新家啦”时，带着满足和归属感，充满领导者的风范。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "补充说明的兴奋。像是突然又想起了什么重要的事情，语气里带着小小的得意和炫耀，又发现一个宝贝的感觉。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "英雄凯旋的氛围。语调上扬，充满赞赏。“精神抖擞”要读得特别有力量，表现出石猴此刻的光彩照人。"
                },
                {
                    "台词位置": 22,
                    "语气指导": "崇拜、欢呼。用尽全力地呐喊，声音里充满了对英雄的崇拜和激动，可以处理成群声效果，此起彼伏。"
                },
                {
                    "台词位置": 23,
                    "语气指导": "庄重、信服。语速放缓，语气严肃而真诚，表达出对石猴勇敢行为的认可和尊敬。“请受我们一拜！”时，要带有敬意。"
                },
                {
                    "台词位置": 24,
                    "语气指导": "庄严又激动。声音洪亮整齐，像是在举行一个盛大的仪式。喊“千岁”时可以拖长音，充满敬仰和喜悦。"
                },
                {
                    "台词位置": 25,
                    "语气指导": "得意、豪迈、有领袖风范。开头是发自内心的、爽朗的大笑。宣布新名字时充满自豪感。最后一句是号召，声音洪亮，充满感染力，带着大家奔向新生活的快乐。"
                },
                {
                    "台词位置": 26,
                    "语气指导": "温馨、喜悦的结尾。语速平稳舒缓，语气充满画面感，带着微笑。描述猴子们的欢笑声时，声音可以变得更轻柔，仿佛能听到远处的笑声，给小朋友留下幸福、美好的想象空间。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "【亲切愉快，转为悬念】前半段语速平稳，语气温暖，描绘快乐的生活。到“可是”时，语速放慢，转为轻柔、带着一丝悬念的语气，引导听众好奇美猴王为何叹气。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "【忧愁的叹息】音调稍低，气息悠长，不是疲惫，而是发自内心的、对未来充满担忧和伤感的叹气。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "【天真、关切地发问】语气充满孩子气的好奇和关心，语速稍快，音调可以高一点，像一群单纯的小朋友在问：“你怎么不开心呀？”"
                },
                {
                    "台词位置": 3,
                    "语气指导": "【温柔而忧伤】语速放慢，音调低沉，像是在跟好朋友分享一个沉重的心事。说到“花谢了”时带着惋惜，说到“跳不动了”时，流露出深深的担忧。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "【惊恐、不敢相信】音调瞬间拔高，语速变快，带着一点颤抖。像小孩子第一次听到可怕的事情，充满了恐惧和抗拒。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "【伤心、泫然欲泣】带上哭腔，“呜呜呜”要哭得很伤心。整句话都充满了绝望和无助感，觉得未来一片灰暗。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "【坚定、充满力量】声音突然变得响亮、果断，语速加快。“不！”要短促有力。“我绝不答应！”和“一定有办法的！”要斩钉截铁，展现出作为大王的担当和不服输的性格。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "【充满希望，转为郑重】前半句语气温柔而肯定，像在安抚听众。说到“通背猿猴走了出来”时，语气变得沉稳、郑重，暗示一位重要角色的登场。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "【沉稳、充满智慧】语速不快，声音苍老但有力。语气平和，充满肯定，给人一种“别担心，有我呢”的安心感。夸奖大王时，要带着真诚的赞许。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "【急切、充满希望】音调立刻上扬，语速很快，像抓住了救命稻草一样兴奋。问题问得又快又直接，充满了孩子般的好奇和行动力。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "【神秘、娓娓道来】语速放慢，声音压低一点，带着一种讲述古老秘密的感觉。说到“神仙”和“秘密”时，可以稍微加重语气，营造神秘感。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "【惊喜、充满好奇】音调更高，眼睛仿佛在放光。问题脱口而出，充满了对未知世界的天真向往和激动。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "【沉稳、描述性】语速平稳，用缓慢而悠长的语调来形容“很远很远”，强调路途的遥远和艰辛，为猴王的决心做铺垫。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "【振奋、充满力量】语调上扬，语速有力，描述猴王充满力量的状态。“挺起胸膛，眼神坚定”要用声音表现出来，让听众感受到他英雄般的气概。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "【豪情万丈、充满决心】音量提高，语速坚定有力。“太好了！”是发自内心的喜悦。后面的话像是在宣誓，充满了对未来的美好承诺和必胜的信心，要让所有小猴子（和听众）都为之振奋。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "【兴奋欢呼、崇拜】声音高亢、激动，可以加入一些欢呼的背景音。语气里充满了对大王的崇拜和信任，为大王的决定感到无比自豪和开心。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "【热闹又温情】描述宴会时，语气欢快、喜庆。说到“告别的时候”和“依依不舍”，语速放慢，转为温柔、感人，烘托出离别的氛围。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "【响亮、充满自信】这是对伙伴们的承诺。声音洪亮，充满力量，没有悲伤，而是让大家安心的坚定语气。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "【壮阔、充满敬佩】语速放缓，用一种讲述英雄史诗的口吻来描述。声音要平稳而有力，尤其在“勇敢地向着无边无际的大海出发了”这句，要带着对猴王勇气和未来的无限期待。"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "【亲切的故事大王】语速平稳，带着一点对未知旅程的期待感。说到“歌声”和“砍柴声”时，可以稍微放慢，营造出一种“你听”的感觉，引导小朋友的好奇心。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "【自得其乐，朴实】用一种边干活边哼唱的、轻松愉快的调子说出来。声音不用太大，像是唱给自己听的。节奏感强，带着“铛、铛”砍柴的韵律。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "【发现新大陆般的好奇和惊喜】音量压低，像在说悄悄话，但语调上扬，充满兴奋。语速可以快一点，体现出悟空机灵、急切的性格。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "【开心哼唱，浑然不觉】继续保持轻松愉快的哼唱感，声音洪亮、朴实，完全没注意到自己被偷听了。可以带点拖长音的乡间唱腔。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "【激动，急切】语速加快，声音里带着兴奋和迫不及待。描述孙悟空的动作时，声音要更有力，最后一句“大声喊道”的音量要提起来，为下一句台词做铺垫。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "【天真又冒失的崇拜】音量大，语调高昂，充满找到救星般的狂喜和激动！带着一点点喘息感，好像是跑了很久刚停下来。喊“老神仙”时要充满敬仰，但又有点愣头愣脑的感觉。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "【夸张，有点好笑】用略带戏剧性的语气描述樵夫被吓到的样子，可以模仿一下被吓得一哆嗦的感觉。“啊”地一声要短促有力，表现出十足的惊吓。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "【惊魂未定，又有点懵】前半句带着害怕和喘息，声音有点抖。说到“我可不是什么神仙”时，语气变得困惑和无奈，想赶紧撇清关系。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "【急不可耐，理直气壮】完全没在意对方的情绪，满脑子都是自己的目标。语速快，语气非常直接，像个好奇又不懂礼貌的小孩子在追问，带着不容置疑的劲头。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "【被惹恼了，有点生气】从惊吓转为生气和责备。音量提高，语速放慢，带着长辈教训不懂事小孩的口吻。强调“没礼貌”、“大喊大叫”，表达自己的不满。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "【立刻认错，委屈又真诚】意识到自己错了，态度180度大转变。语速变慢，声音放低，带着明显的歉意和一点点委屈。说到“找了好久好久”时，声音可以带上疲惫感，让人心生怜悯。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "【温柔，引导情绪】旁白的声音变得柔和、温暖。语速放缓，体现出樵夫内心的转变，让听众感受到孙悟空的真诚打动了他。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "【心软了，转为热心肠】先轻轻叹一口气，表示理解和无奈。然后语气变得温和、热心，像一个善良的大哥哥在指路。说话不紧不慢，清晰地告诉孙悟空地址。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "【如获至宝，欣喜若狂】重复地址时，像是在念一个神奇的咒语。音调一下子扬起来，充满了失而复得的巨大喜悦和感激。语速飞快，充满活力！"
                },
                {
                    "台词位置": 14,
                    "语气指导": "【善意提醒，朴实】带着一点善意的无奈和微笑说出这句话。像在看一个急匆匆的小孩子，语气是温和而包容的。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "【画面感十足】前半段语速轻快，表现孙悟空飞奔的活力。描述仙山时，语速放慢，声音带上赞叹和向往，营造“仙境”的氛围。最后，当孙悟空看到仙童时，语气里要带上一点紧张和期待，把听众的心也提起来。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "【小心翼翼，恭敬有礼】一改之前的莽撞，声音放轻，语速放慢。带着紧张和一丝不确定，努力让自己显得非常有礼貌，像个第一次面试的小朋友。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "【乖巧懂事，波澜不惊】声音清亮、平和，带着一种“我早就知道”的淡定。语气友好而沉稳，不像普通孩子，更显其“仙童”身份。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "【巨大的惊喜，不敢相信】“啊？”的一声，是全然的惊讶。然后转为巨大的、纯粹的开心，声音上扬，语速加快，重复“太好了”时，喜悦之情层层递进，像孩子得到糖果一样开心。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "【沉稳引领，亲切】语气依然很平静，但带着主人翁的亲切感。声音清晰，给人一种“放心跟我来”的可靠感觉。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "【庄严，充满敬畏】描述洞府时，声音可以放慢，带一点神秘感。看到菩提祖师时，语气变得非常崇敬、庄重。描述孙悟空下拜的动作时，要果断有力，烘托出他拜师的决心。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "【无比虔诚，真心实意】这是发自内心的呐喊。声音洪亮、坚定，充满了崇敬和终于找到归宿的激动。每个字都说得非常用力，饱含情感，是整个寻师过程的情感最高点。"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "（仙童）严厉喝止，带着一点小孩子努力装成大人的“奶凶感”，音量稍大，语速快，表现出尽职尽责的样子。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "（孙悟空）焦急恳求，语气非常真诚，甚至带一点点哭腔。音调稍高，语速快，把“真心想拜师学艺”的渴望表现出来。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "（旁白）亲切讲述，语速平稳。在说到“须菩提祖师”时，语气可以稍微放慢，带一点点神秘和尊敬的感觉，引导小朋友期待这位重要角色的出场。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "（须菩提祖师）温和但有威严，声音沉稳。像一位智慧的长者在打量一个有趣的小家伙，带着一丝不易察觉的好奇。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "（孙悟空）坦诚直率，声音清亮。说到“没有爸爸妈妈”时，可以带一点点天真的失落感，但不是悲伤，只是在陈述事实。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "（须菩提祖师）语气中带着微笑和欣赏，觉得这猴子很特别。说到“孙悟空”三个字时，要清晰、庄重，像是在完成一个重要的命名仪式。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "（孙悟空）欣喜若狂！音调瞬间拔高，语速飞快，充满孩童得到心爱礼物的巨大喜悦和感激，可以加上开心的笑声。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "（旁白）平和叙述，语速稍放缓，营造出时光流逝的感觉。在说到“但一直没学到”时，为悟空带上一丝小小的焦急和期待，为后面的情节做铺垫。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "（须菩提祖师）慈祥地考问，语气平稳温和，像一位老师在关心学生的学习进度，充满引导性。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "（孙悟空）充满渴望和天真！音调高昂，毫不掩饰自己对长生不老的向往，语气非常坚定和兴奋。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "（旁白）带有悬念和戏剧性。描述“板起脸”时语调转为紧张，说到“咚、咚、咚”时，要一字一顿，清晰地模仿敲击的节奏，营造神秘的气氛。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "（仙童）焦急地责备，带着“你怎么这么不懂事”的埋怨，但没有恶意，更像是在替师父和悟空担心。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "（众仙）七嘴八舌的抱怨，声音嘈杂，形成一种群体压力感。可以有几个人声线此起彼伏，表达“都怪你”的情绪。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "（旁白）亲切地为悟空“辩解”，语气从小声、神秘，转为轻快和恍然大悟，好像在跟听众小朋友们分享一个只有我们才知道的秘密。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "（孙悟空）小声嘀咕，自言自语。从一开始的喃喃自语，到后面想通关节时的恍然大悟和兴奋，语速由慢变快，音量由小变大，表现出聪明劲儿。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "（旁白）营造神秘、安静的氛围，声线压低，语速放慢，好像在踮着脚走路。最后一句“正等着他呢”带上一点惊喜和揭晓谜底的笑意。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "（须菩提祖师）欣慰又得意地大笑，笑声要爽朗。语气里充满了对悟空智慧的赞赏和喜爱，像是在夸奖自己最得意的学生。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "（旁白）轻声而神秘，像在说悄悄话。用充满魔法和奇妙感觉的语调，引导小朋友想象这个神奇的口诀。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "（须菩提祖师）语重心长，声音沉稳。像一位负责任的师父，在传授真本领的同时，也提醒弟子未来的风险，带有关怀和考验的意味。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "（孙悟空）机灵又带点小“贪心”。“嘿嘿”一笑要俏皮，语气坚定又有点撒娇，把小猴子想要更多的渴望表现得活灵活现。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "（旁白）平稳叙述，语调轻松。但在说到“但他发现自己虽然能变，却跑不快”时，语气一转，带出一点小小的烦恼和问题，引出下一个请求。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "（孙悟空）焦急又带着撒娇的恳求。向师父解释自己的担忧，语气听起来很着急，好像真的马上要被妖怪抓住了。"
                },
                {
                    "台词位置": 22,
                    "语气指导": "（须菩提祖师）假装嗔怪，语气中带着明显的笑意和宠溺。说“贪心”的时候，更像是一种爱称，完全没有责备的意思。"
                },
                {
                    "台词位置": 23,
                    "语气指导": "（孙悟空）非常坚定和急切！语速很快，音量也提高，强调“一定”要飞得快，表现出他对自身安全和变得更强的强烈愿望。"
                },
                {
                    "台词位置": 24,
                    "语气指导": "（须菩提祖师）赞赏地大笑，声音洪亮！充满对悟空志气的欣赏，说到“十万八千里”时要充满豪情和力量感。"
                },
                {
                    "台词位置": 25,
                    "语气指导": "（孙悟空）极度兴奋和崇拜！音调高昂，充满力量感和对未来的无限向往。重复“谢谢师父”时，是发自内心的、充满活力的感激。"
                },
                {
                    "台词位置": 26,
                    "语气指导": "（旁白）欣慰自豪。用昂扬、轻快的语调进行总结，让小朋友们为悟空的成长感到开心和满足，圆满地结束这一场景。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "【亲切活泼】作为故事大王，用轻松愉快的声音描绘一个热闹的场景，语速平稳，带着微笑，让小朋友感觉好像就站在松树下看大家玩耍一样。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "【崇拜又期待，多人齐声】音调稍高，语速稍快，带着一点点起哄和讨好的感觉。想象一下一群小朋友围着一个厉害的小伙伴，充满好奇和兴奋，声音要显得热闹、真诚。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "【得意又活泼】开头的“嘿嘿”要带着一点小骄傲和机灵劲儿，声音明亮，充满自信。语调上扬，向大家展示自己很乐意露一手，非常爽快。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "【兴奋地提议，多人齐声】“太好了！”要像欢呼一样，充满惊喜。后面的提议要带着一种“我们来玩个好玩的游戏吧”的激动心情，语速加快，充满期待。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "【自信满满，充满力量】“没问题！”要说得干脆利落。说“变！”的时候，可以把声音压低一点，然后有力地喊出，模仿施展法术的感觉，充满能量。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "【充满惊奇】用带着惊叹的语气描述这个神奇的瞬间。“嗖”的一声可以模仿音效，读得快而响亮。描述悟空变成松树时，要充满画面感，让听众感受到魔法的神奇。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "【惊喜赞叹，多人齐声】“哇！”要发自内心地惊叹，声音拉长一点。后面的赞美要像连珠炮一样，又快又响亮，充满了真诚的佩服和喜悦，可以加入拍手和欢呼的背景声。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "【悬念，气氛突转】语速放慢，语气从刚才的欢乐转为严肃和紧张。声音压低，营造出一种“大事不妙”的氛围，为祖师的出场做铺垫。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "【严厉，威严】声音要深沉、洪亮，充满不容置疑的威严。语速不快，但每个字都很有力量，像一声惊雷，瞬间镇住全场。这是长辈生气的口吻。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "【紧张慌乱】语气要体现出大家被吓到的感觉，可以带一点点倒吸气的感觉。描述悟空的动作时，语速稍快，声音变轻，好像在替他紧张，表现出他的心虚和慌张。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "【不容置疑的命令】虽然没有大声吼叫，但语气非常严肃、坚定。声音低沉，语速缓慢，每个字都带着不容反抗的命令感。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "【害怕，认错】声音要变小，带一点点颤抖，像是做错事的孩子被家长抓住了一样。语速慢，低着头，非常心虚和胆怯的感觉。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "【严肃质问】语气依然严厉，但更多的是一种审问的感觉。语调平直，带着作为师父的威严，他想知道悟空的真实想法。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "【委屈，小声辩解】开头“我……我……”要结结巴巴，表现出紧张。声音里带着委屈和不解，好像在说“我只是觉得好玩呀”，最后一句“这有什么不对吗？”要带着孩子般天真的困惑。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "【痛心疾首，严厉教导】开头“糊涂！”要带着恨铁不成钢的严厉。接下来的话语重心长，语速加快，强调“保护自己”、“不是炫耀”等关键词，表现出师父是真的在为他的安危担心。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "【恍然大悟，转为后怕】旁白的语气要体现出悟空内心的转变，从不解到明白，再到害怕。语调沉下来，让听众感受到悟空此刻后怕的心情。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "【恐惧，急切恳求】声音里要带着哭腔和颤抖，表现出极度的害怕和后悔。语速很快，像是在急切地求饶，声音响亮但又带着哭泣的嘶哑感。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "【沉痛，无奈的决定】开头的“唉”要叹一口长长的气，充满惋惜和无奈。整句话语速放慢，声音低沉，带着一种无法挽回的悲伤和坚决。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "【震惊，伤心央求】“什么？”要像一声短促的惊叫，充满不敢相信。后面的话带着哭腔，从震惊转为伤心和苦苦哀求，像一个不想离开家的孩子，充满不舍。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "【斩钉截铁，加重语气】“不行！”要说得非常果断，没有商量的余地。语气非常坚决，甚至有点严酷，但内里是为了保护悟空，所以话语中要透出一种“我是为你好”的急切感。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "【同情，悲伤】用充满同情和悲伤的语调来讲述。语速放缓，声音变得温柔而沉重，引导听众感受悟空此刻撕心裂肺的难过。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "【伤心大哭】这句话要完全在哭泣中说出来。“呜呜”是真的伤心抽泣。声音哽咽，断断续续，充满了对师父的依赖和离别的巨大痛苦。"
                },
                {
                    "台词位置": 22,
                    "语气指导": "【最后一次的严令】“别哭了！”是严厉的制止，但更是为了让他听清最重要的嘱咐。接下来语速放慢，一字一顿，用最严肃、最不容置疑的语气下达最后的命令，强调事情的严重性。"
                },
                {
                    "台词位置": 23,
                    "语气指导": "【含泪的承诺】努力忍住哭泣，声音带着浓重的鼻音和哽咽，但语气是坚定而郑重的。这是悟空懂事和成长的表现。最后一句“您多保重！”要充满感情，是发自内心的告别。"
                },
                {
                    "台词位置": 24,
                    "语气指导": "【庄重又略带伤感】描述磕头时，语速放慢，语气庄重。说到“嗖——！”时，声音要模仿筋斗云飞走的感觉，快速而有力。最后一句语调可以略微上扬，带着一点点开阔感，目送悟空离开，开启新的旅程。"
                }
            ]
        }
    ]
}
    # 将语气与剧本结合起来供TTS翻译
    script_with_emotion = combine_script_and_emotion(refine_script,Emotion)

    # S5 最终审校
    # script_final_proofreader = {'剧本审查':[]}
    # for index,script in enumerate(script_with_emotion['剧本']):
    #     tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
    #     tmp_character = []
    #     character_profiles_in_script = extract_character_profiles(script, character_gemini)
    #     for value in character_profiles_in_script.values():
    #         tmp_character.append({
    #         "规范化名称": value.get("规范化名称", ""),
    #         "别名": value.get("别名", []),
    #         "性格特征": value.get("性格特征", []),
    #         "性别":value.get("性别","")
    #     })
    #     tmp_character2 = json.dumps(tmp_character, indent=4, ensure_ascii=False)
    #
    #     result = Final_Proofreader(tmp_character2,tmp_script)
    #     tmp_dict = {
    #         '场景':index+1,
    #         '审查结果':result['审查结果'],
    #         '问题清单': result['问题清单']
    #     }
    #     script_final_proofreader['剧本审查'].append(tmp_dict)
    # print(script_final_proofreader)

    # 角色声音配对
    # Role_Voice_Map(character_gemini,script_with_emotion)


    # row_cnt = 0
    # for record in script_conflict_escalation_gemini['剧本']:
    #     row_cnt+= len(record['场景剧本'])
    # print(row_cnt)
