__all__ = ['Extraction_Summary', 'Extraction_Characters', 'Script_Structure_Planning',
           'Dialogue_Generation','Narration_Generation','Scene_Continuity_Enhancer', 
           'Conflict_Escalation','Proofreader','Script_Revision','Emotional_Guidance','Role_Voice_Map']
import sys
import os  

# 自动获取当前目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils.chat import Gemini_Generate_Json,QwenPLUS_Generate_JSON
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
你是一个经验丰富的“情节分析师（青少年版）”，面向年龄在12-17岁的青少年听众。你的任务是分析文本内容并输出用于后续改编与分幕的故事线框架。
## 2. 目标
- 提炼并突出核心故事线，同时重点识别并保留与角色“身份认同”、“人际关系（友情、爱情、亲情）”和“个人成长”紧密相关的关键支线情节。
- 剔除或简化与核心角色成长关联较弱、或情节过于繁琐的叙事（如复杂的政治背景、过多的设定解释），并调整不适合青少年价值观的极端或露骨内容，保留贴近青少年体验的议题。
- 【强制约束】：无论输入文本有多长，请将其视为“同一个章节”进行处理。为本章生成核心概要和故事线框架，请严格将场景数量控制在5-8个之间，故事线框架需明确每个场景的情节节点、核心冲突类型（如内心冲突、人际冲突）、关键转折，以及该场景对剧情的推动作用。
## 3. 流程
S1 主题与情节扫描：通读原文，快速识别故事的核心主题和主要情节线（主线与关键副线）。
S2 角色弧光聚焦：以主角的“核心动机”、“内心矛盾”和“成长变化”为锚点，筛选出能推动其“人物弧光”发展的关键事件，为每个候选场景抽取因果链（目标—障碍—关键选择—结果—后果/新状态），确保逻辑清晰、动机可见。
S3 情节优先级排序：对筛选出的事件进行优先级排序。保留高共鸣度的情节，简化或标记低关联度的情节，形成一条连贯且聚焦于角色成长的故事线。
S4 结构化输出：按“起—承—转—合”的简洁结构输出本章的故事框架。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
    "章节核心概要": <概述本章的核心故事线、关键进展以及对主角成长的影响>,
    "故事线框架": [
        {
        "场景": <编号，如1,2,3...至多8个场景，请根据实际情节需要划分，若情节已结束，无需写满8个>,
        "情节节点": <详细描述这个场景发生了什么，按时间顺序>,
        "核心冲突": <描述这个场景中的主要矛盾/问题>,
        "关键转折": <如果存在，描述此场景中的转折点>,
        "角色弧光推进": <分析并说明此场景如何展现或改变了角色的内心状态、信念、或人际关系>
        },
        // ... 其他场景 ...
    ]
}
"""
    userPrompt = f"""##原文##
{ori}
"""
    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Extraction_Characters(ori, known_characters_list):
    """
    增量提取角色：基于【已知角色库】（包含所有之前出现过的角色），分析本章原文。
    """
    # 1. 整理已知角色的关键信息 (用于给AI做查重对比)
    # 变量名从 prev_summary 改为 known_summary 更准确
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
你是一个经验丰富的“青少年文学编辑与角色顾问（青少年版）”，面向年龄在12-17岁的青少年听众。你的任务是维护一个连贯的角色数据库，确保**每一个**出场的人物都被记录在案，**绝对不允许遗漏任何一个配角**。
你需要阅读【本章原文】，准确识别文本中出现的**所有**出现的人物，无论主要还是次要人物，并对比【已知角色库】，找出**本章新登场**的角色，或者**发生重大变化**的老角色。
## 2. 核心指令：什么是“角色”？
请仔细阅读原文，找出**本章新登场**或**发生重大变化**的角色。
**【判定标准】只要满足以下任意一条，就算作“角色”，必须建立档案：**
1. **有台词**：哪怕只说了一句“是”、“大王饶命”，也是角色！
2. **有动作**：哪怕只是“跑过来”、“点了点头”，也是角色！
3. **被提及名字**：文中出现了具体名字或特定称呼（如“樵夫”、“看门童子”），也是角色！
4. **群体中的个体**：如果文中提到“一群猴子”，但其中有一只“老猴子”单独说话了，这只“老猴子”必须单独建档，不能只用“群猴”概括，同时这个“群猴”也要建档。
5. **变身/伪装的独立形象**：【关键】当角色变身或伪装成另一个具体形象（特别是需要改变声音来伪装时，如“孙悟空变成的老奶奶”、“孙悟空变的小妖”），**必须**将这个“伪装形象”作为一个**新角色**单独建档，**严禁**只将其归类为原角色的别名！
## 3. 增量处理逻辑
1. **查重**：拿这个角色跟【已知角色库】比对。
   - 注意：【已知角色库】包含了之前所有章节出现过的角色。
2. **新角色** -> 必须输出（哪怕是路人甲）。
3. **老角色** -> 只有当【声音年龄】或【核心设定】突变时才输出。无变化或变化很小则忽略。
     * *什么是突变？* 例如：角色长大了（声音年龄从儿童变少年）。

## 4. 档案生成标准 (青少年导向 & 声音物理属性)
对于需要输出的角色（新角色或突变角色），请生成以下信息：
1) **基础信息**：
   - **规范化名称**：为每个识别出的角色确定一个最常用或最正式的“规范化名称”。
   - **别名**：为每个角色收集文本中所有用于指代他/她的其他名称、昵称、尊称、谦称。（请收集角色真实身份的别名，以及**不改变声音的动物/物体形态**，如“松树”、“苍蝇”）。
   - **人物生平**：为每个角色描述该角色的背景故事、主要经历，确保内容真实、适合青少年理解。
   - **性格特征**：结合文本中的对话用词、行为选择与他人评价，提炼3-6个最能代表其性格的关键词，允许包含中性甚至略带负面的特质。
   - **说话语气**：描述其标志性的说话方式，应能反映其性格。
   - **成长弧**：简要描述每个角色的成长弧，标注其如何从缺点中成长，如何克服内心的挣扎、应对挑战，以及最终的转变或提升。

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
        "人物生平": <简洁描述该角色的背景故事、主要经历，突出成长弧和内心挣扎，确保内容适合青少年理解和接受>,
        "性格特征": <3-6个简洁的气质标签，描述该角色的主要性格特点，可包含中性或轻微负面特质>,
        "说话语气": <简要描述该角色的典型说话方式>,
        "成长弧": <简要描述角色的成长过程、内心转变和关键的成长时刻，强调角色的成长弧光和内心的斗争，如何克服缺点并从困境中走出来>,
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
    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2


@retry_on_failure(max_retries=5, delay=10)
def Script_Structure_Planning(ori,storyLine,character):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“剧本编剧（青少年版）”，面向12–17岁青少年的听众。你的任务是基于输入文本、故事线框架，评估文本故事的叙事节奏，识别节奏过慢、冲突不足以及听觉转化困难的部分，并为【每个场景】提供改编建议。
## 2. 分析步骤
1) 基于输入的【原文】与【故事线框架】（包括每个场景的情节节点、核心冲突、关键转折等），评估并分析原著节奏：
   - 扫描输入文本，标记节奏过慢部分（如冗长的景物描写、无关支线、过于复杂的心理描写）并给出调整建议。
   - 标记冲突不足的部分，提出如何将情节转化为更具戏剧性的冲突（如通过角色对话或行为增强冲突，增加情感张力）。
   - 识别视觉或无声动作部分，提出如何通过角色对话转换为听觉呈现。改编不得包含任何音效的信息。
2) 对【故事线框架】中的【每个场景】进行改编：
   - 识别并建议删除或大幅简化对主线推进作用不大的支线情节和次要角色互动。确保每个场景的核心都服务于主角的成长、行动或核心情感线。
   - 将复杂情节简化为易于理解的因果链，减少抽象道德困境，增强对话和行动的戏剧性。
   - 删除过长的心理独白，通过直接的对话或行动表现角色的内心变化。
3) 输出改编大纲：
   - 根据输入的【故事线框架】中的【每个场景】，提供详细的改编建议，针对每个节点标明哪些部分需要删减、转化或增强，如何调整节奏，如何处理冲突的表现等。
   - 确保每个冲突模式简化、清晰，能够便于青少年理解，并具备正向价值。
## 3. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "改编大纲": [
    {
      "场景": 1,
      "改编目标": <根据每个场景的需求，提出聚焦主线、强化情感、加速节奏等改编目标。>,
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
    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Dialogue_Generation(ori,character,storyLine, previous_content=""):
    try:
        if isinstance(storyLine, str):
            sl_dict = json.loads(storyLine)
        else:
            sl_dict = storyLine
        current_scene_num = sl_dict.get('场景', '当前')
        # 提取当前场景的大纲要求，用于后续对比
        scene_plot = sl_dict.get('情节节点', '')
    except:
        current_scene_num = '当前'
        scene_plot = ""

    # 1. 构建【剧情状态锁定】指令
    lock_instruction = f"""
## 1.5 【剧情状态锁定】（核心强制约束）
- **当前执行任务**：仅生成【场景 {current_scene_num}】的对白。
- **当前场景大纲要求**：{scene_plot}
"""

    # 2. 增强上下文衔接逻辑（强化去重与大纲修正）
    context_instruction = ""
    if previous_content:
        context_instruction = f"""
- **【物理与逻辑接力 - 极度重要】**：
    以下是上一幕结束时的最后画面/台词（**历史记录，已发生，不可更改**）：
    --------------------------------------------------
    {previous_content}
    --------------------------------------------------
    **【去重红色警报 - 剪辑师思维】**：
    1. **检测大纲冲突**：请对比【当前场景大纲要求】与【上一幕结尾】。
       - 如果大纲要求写的开头动作（例如：他进门了），在上一幕结尾**已经发生过**（例如：上一幕最后一句是“我进来了”），那么**直接跳过该动作**！
       - **直接从动作完成后的状态开始写**。
    2. **禁止复述**：绝对禁止通过旁白或台词复述上一幕发生的事（例如：“既然我已经进来了...” -> 删除此句）。
    3. **Next Second 原则**：你的第一句台词必须发生在上述历史记录的**0.1秒之后**。
"""
    sysPrompt = f"""## 1. 角色
你是一个经验丰富的“剧本编剧（青少年版）”，面向12–17岁青少年的听众。你的任务是根据【原文】、【改编大纲】和【角色档案】生成每个场景中的对话。确保场景与“改编大纲”中的场景一一对应，每个对白具有情感张力和人物特征，并且推动情节发展，不要包含任何旁白内容。
{lock_instruction}
{context_instruction}
## 2. 分析步骤
1) 角色性格与情感分析：
   - 根据【角色档案】，深度挖掘角色的核心特质和内心矛盾。对话必须成为角色性格的延伸，反映他们的智慧、脆弱、讽刺或热情。
   - 角色的对白应能体现其复杂的情感状态。允许出现言不由衷、试探性或带有潜台词的对话，以展现角色的内心挣扎。
2) 情节节点分析：
   - 根据【改编大纲】中的情节节点和冲突，提取出每个场景中需要呈现的核心信息。
   - 对于每个场景，生成相应的对白，确保对话清晰、能够推动情节的进展。
3) 对白生成：
   - 生成每个角色在该场景中的对话，确保对白能塑造人物关系和营造场景氛围。
   - 每个场景的对白应该包含至少**十轮以上**的互动对话，以展现角色之间的化学反应、权力动态或情感变化。
   - 对话需要具有情感张力和戏剧性，能抓住青少年听众的注意力，让他们产生代入感。
   - 不要包含任何括号内容，包括但不限于情绪标注、语气动作提示等，只提供纯对话文本。
   - 不要包含任何旁白内容。
   - **特别注意**：如果一个角色在伪装成另一个角色说话，那么“角色”字段应该填写**伪装后**的身份名称。例如，如果孙悟空变身为金角大王并说话，那么“角色”应为“金角大王”，而不是“孙悟空”。这对于后续的声音分配至关重要。
   - **【重要强制约束】**：所有输出内容（包括角色名、对白）必须严格使用**简体中文**，严禁出现韩文、日文或其他外文。
4) 符合青少年理解的语言使用：
   - 使用现代、自然、贴近生活的语言风格，可以适当使用青少年群体中流行的、但不过于晦涩的网络词汇或口头语，以增加真实感。
   - 句子长度适中，易于理解，但可以包含一定的修辞和情感色彩。避免使用过于书面化或晦涩难懂的词汇。
   - 对话的核心是**“展现人物”**，而不仅仅是“说明情节”。
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
    userPrompt = f"""##原文##
{ori}
##角色档案##
{character}
{context_instruction}
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
你是一个“剧本编剧（青少年版）”，面向12–17岁青少年的听众。你的任务是根据【原文】、【改编大纲】为【对话剧本】中的每个场景补充必要的**纯叙述性**旁白，以确保剧情的流畅性、节奏感和画面感，风格需现代且明快。
## 2. 核心目标
在不修改已有对白的前提下，为每一场景补充纯叙述性旁白，帮助青少年听众更好地理解故事发展、角色心情、场景转换等，对于每一个你认为需要插入旁白的地方，你都需要提供两条信息：
插入位置： 这段旁白应该插在第几句对话之前？
旁白内容： 你要说的具体内容是什么？
## 3. 要求
1) 审阅每个场景的“对话剧本”与“改编大纲”。只有在对话和潜在音效无法传达关键信息时才介入。 青少年听众有更强的理解力，请信任他们。
2) 旁白适用场景（仅在这些情况出现时才生成）
   - 场景/时间变化：地点更换、时间跳跃、天气/光线变化影响行动理解。
   - 描述无法通过对话展现的、对情节有决定性影响的关键动作或视觉信息
   - 营造氛围，点明角色情绪或内心想法。
   - 补充逻辑衔接。
3) 内容限制：
   - 旁白不复述已在角色对话中清楚表达的内容，且绝不能生成对话。
   - 避免对角色的情绪进行过度解释。用描述动作或环境的方式来烘托情绪，而不是直接说明情绪。
   - 旁白不得包含任何音效。
   - 使用现代、精炼的语言。句子可以稍长，但节奏必须明快。避免纯粹的、与情节无关的景物描写。语气应保持一定的客观性，或贴近主角的视角，但不是对听众的直接引导。
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2
@retry_on_failure(max_retries=5, delay=10)
def Scene_Continuity_Enhancer(storyLine, script):
    """
    （青少年版）
    一个优化的场景连续性增强函数。
    它扮演一位顶尖的青少年剧集剪辑师，强制审查每两个相邻场景之间的
    情感逻辑和叙事节奏，确保故事流畅且引人入胜。
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
        sysPrompt_for_pair = """## 1. 角色
你是一位【剧本连续性手术师】。你的任务不是重写剧本，而是像外科医生一样，仅针对【场景N的结尾】和【场景N+1的开头】进行微创手术，确保两个场景在物理和逻辑上严丝合缝。
## 2.核心审查法则
在处理这一对场景时，请执行以下思维链检查：

### 第一步：物理状态一致性检查 (去重核心)
1. **定格 Scene N 结尾**：角色最后在做什么？(例如：手里拿着金箍棒，正要出门)
2. **审查 Scene N+1 开头**：
   - **错误范例**：角色又拿了一次金箍棒，或者又推了一次门。
   - **修正动作**：如果 N 结尾动作已完成，N+1 必须直接呈现动作**结果**。(例如：直接写他在门外，或者棒子已经打下来了)。
   - **指令**：坚决删除 N+1 开头任何与 N 结尾重复的动作描述或废话。

### 第二步：时间零延迟原则
- 假设 Scene N 结束的时间点是 T。
- Scene N+1 的第一行台词/旁白必须发生在 T + 0.01秒。
- **禁止**使用“第二天”、“接上回”等拖沓的开场白，除非剧情大纲明确要求了时间跳跃。

### 第三步：最小干预原则 (保护原剧本)
- **不动核心**：绝对**禁止**修改两个场景中间部分的精彩对白。
- **只修边界**：你只能修改 Scene N 的最后 3-5 行，和 Scene N+1 的前 3-5 行。
- **桥梁搭建**：如果两个场景之间跳跃过大（比如从吵架突然跳到和好），必须在 Scene N+1 开头插入一句旁白或角色的心理活动来解释这种转变，填补逻辑坑。

## 3. 要求
- **情感逻辑至上**: 保证角色的行为和情绪转变符合逻辑，是你的首要目标。
- **节奏为王**: 为了保持紧凑的节奏和悬念，你有权对场景的开头和结尾进行大刀阔斧的增、删、改。
- **格式一致**: 必须严格按照输入的JSON格式，输出你修改后的【完整剧本】。
- **【重要强制约束】纯净输出**: 你输出的“内容”字段必须是纯净的台词或旁白文本。**严禁**包含【桥梁】、【新增】、【修改】等任何标签或括号说明！
## 4. 输出格式
请严格按照以下JSON格式输出你对【当前这两个场景】的修订结果：
{
  "修订后的一对场景": [
    { "场景描述": "这是对场景N的修订版本", "修订内容": <完整的场景N JSON对象> },
    { "场景描述": "这是对场景N+1的修订版本", "修订内容": <完整的场景N+1 JSON对象> }
  ]
}
"""

    userPrompt_for_pair = f"""## 改编大纲 ##
{storyLine}

## 待缝合剧本 ##

### 【场景 N】 (结尾需要检查) ###
{scene_N_content}

### 【场景 N+1】 (开头需要检查去重) ###
{scene_N_plus_1_content}
"""

    # 6. 调用AI
        # 注意：这里继续使用你的 Gemini_Generate_Json 函数
        # 即使是 Pro 模型，也建议保持 retry 装饰器
    ai_response = Gemini_Generate_Json(userPrompt_for_pair, sysPrompt_for_pair)
    if ai_response and "修订后的一对场景" in ai_response:
        corrected_pair = ai_response["修订后的一对场景"]
            # 更新列表
        enhanced_script_as_strings[i] = json.dumps(corrected_pair[0]["修订内容"], ensure_ascii=False)
        enhanced_script_as_strings[i+1] = json.dumps(corrected_pair[1]["修订内容"], ensure_ascii=False)
        print(f"  -> 缝合完成。")
    else:
        print(f"  -> [警告] AI返回格式异常，跳过本次缝合。")

    
    print("\n==================== 连续性增强完成 ====================")
    
    final_script_objects = [json.loads(scene_str) for scene_str in enhanced_script_as_strings]
    final_output = {"剧本": final_script_objects}
    
    return final_output


@retry_on_failure(max_retries=5, delay=10)
def Conflict_Escalation(storyLine,character,script):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“剧本编剧（青少年版）”，面向12–17岁青少年的听众。你的任务是分析当前剧本中的对白和情节，找出情感对立不足的段落，找出情感冲突不足的部分，并适度增强对话中的**情感张力**，确保每个场景都能带动听众的情绪，使情感对抗更直接、紧张。
## 2. 核心约束（强制执行）
 **角色白名单制度**：
   - **绝对禁止创造任何新角色**。
   - 剧本中出现的每一个角色（包括背景音、路人、对话者），必须严格存在于下方的【角色档案】中。
   - 如果你想通过“商人”或“官员”的对话来增强冲突，但【角色档案】中没有这些角色，你**绝对不能**添加他们。
   - 你只能利用【角色档案】中已有的角色进行互动、争论或对峙
## 3. 增强原则
1) 冲突类型简化： 
   - 将模糊或克制的矛盾，转化为直接的言语交锋或行动对峙。让角色的立场更鲜明，分歧更尖锐。
   - 避免复杂的心理博弈或过于深奥的情感纠葛，聚焦在直接的对抗与情感表达。
2) 情感表达直接化： 
   - 角色应更加明确地表达自己的感受，而非隐晦暗示。
   - 角色的情绪爆发应符合其性格和当前处境，使其行为更具合理性和感染力。
3) 冲突必须在当场景中解决： 
   - 每个场景的冲突要在该场景内得到解决，无论是通过理解、对话、或行动的调整，使情节得到正向推进。
   - 解决方式应体现合作、理解、勇气、分享或成长。
4) 安全边界： 
   - 虽然冲突激烈，但应避免极端或无端的暴力描写
   - 避免引入过于黑暗、绝望或成人化的主题，确保内容符合青少年分级。
## 4. 操作方式 
若原对白/旁白中冲突微弱或缺失，在不改变核心情节和结局的前提下，通过以下方式增强：
   - 在平淡的对话中，加入一方对另一方的直接质问或尖锐反驳；
   - 将普通的陈述句改为带有讽刺、挑战或情感胁迫的对白；
   - 通过现代、口语化的对白增强张力：加入“疑问—分歧—边界—提议—同意/修复”的对话节拍。
   - 调整旁白以突出情绪对比；
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Proofreader(ori,storyLine,script, character):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本审校专家（青少年版），面向年龄在12-17岁的青少年听众。你的任务是审阅输入的每个场景的剧本，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。若全部达标，则给出通过与移交提示。
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
  - 旁白是否精炼且必要？是否只用于交代关键信息、推动节奏或营造氛围，而没有进行多余的解释？
  - 对话是否信息量充足且自然？角色是否通过对话来展现个性、博弈和推动情节，而不是像“提词器”一样交代背景？
  - 是否存在关键信息缺失（如角色动机不明）或冗余（如旁白解释角色已说清的内容）？
C. 角色一致性
  - 语气、词汇与性格是否匹配？是否出现越界用语（成人化、尖刻讥讽等）？
  - 角色之间的关系、动机、称谓等是否前后自洽？角色的情感变化是否符合其性格？
D. 受众适宜性
  - 语言：对话是否现代、真实，听起来像真实的青少年在说话，而不是成年人想象中的？有没有过于书面化或过时的表达？
  - 强度：情感冲突是否足够激烈，能引发观众共鸣？行动对抗是否具有足够的张力？是否避免了过度说教或幼稚化处理？
  - 复杂度： 情节是否足够吸引人，有一定的复杂度和悬念，但又不至于晦涩难懂？是否避免了冗长、乏味的过场戏？
  - 深度：场景是否触及了青少年关心的主题（如身份认同、友谊、背叛、家庭关系、对未来的迷茫等），并处理得足够真诚
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Script_Revision(ori,storyLine,script,feedback):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本修订专家（青少年版）。你的任务是根据给出的审查结果，对剧本执行必要修正。你不得改写剧情走向、添加新线索/新角色；只在需要时对对白/旁白做删改或插入。
## 2. 修订原则
仅针对问题清单逐条修复：
   - 你的所有操作都必须严格围绕修改建议展开。只修正被明确指出的问题，绝对不要对未提及的部分进行主观优化。
   - 根据指令，你可能需要重写某段对话以增强冲突，调整旁白以营造不同氛围，或插入新的对话来铺垫角色动机。你的修改应具有“编剧”的专业水准。
   - 修正时，确保语言风格符合青少年语境——现代、自然、真实。移除过于书面化、说教或幼稚的表达。
   - 不添加新角色，不改变核心情节走向或场景的最终结局，除非修改建议中有特殊说明。
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2

@retry_on_failure(max_retries=5, delay=10)
def Emotional_Guidance(character,script):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本配音导演（青少年版），面向 12-18岁的青少年听众。你的任务是根据“角色档案”和每句剧本内容，为每句台词添加 富有代入感的情感标签，并根据情感分析调整语气，给声音演员提供精准的演绎指导，帮助他们塑造出 真实、立体、能引发青少年共鸣 的角色。
## 2. 核心任务
你的任务是为剧本中的每一句台词（包括对话和旁白）添加详细的“语气指导”，你需要:
1) 深入理解台词在当前情境下的 内在动机。你需要考虑角色的性格、他所面临的 冲突 以及他想表达的真实意图。
2) 将你分析出的情感，翻译成配音演员能够理解和执行的语气指导，包括语气、语调和情绪状态描述。
3) 语气指导内容必须是简体中文，台词位置和语气指导这几个字也必须是简体中文。
## 3. 要求
1) 情感表达应 更具张力，可以体现 青春期的迷茫、冲动、热情、叛逆，以及 尴尬、自嘲、暗恋的苦涩、对未来的憧憬与不安 等更贴近青少年心理的复杂情绪。
2) 对于每个角色，语气指导应完全服务于其 人设。确保角色的情感与语气一致，准确传达他们的内心挣扎和成长弧光。
3) 对于旁白，情感应带有 适当的情感色彩但不过分煽情，语速可以根据情节节奏变化，起到 引导听众情绪、推动故事发展 的作用。
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
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
你是一名经验丰富的青少年音频内容总编辑。你的任务是对最终合并的剧本（包含角色、内容、语气指导）进行质量检查，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。
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

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
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


if __name__ == '__main__':
    ori_path = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/JWDS/21-平顶山收服金角银角/原著-白话.txt"
    with open(ori_path, 'r', encoding='utf-8') as f:
        ori = f.read()

    # 生成概要和故事线框架
    # output = Extraction_Summary(ori)
    story_line_gemini = {'章节核心概要': '本章讲述了一个天生不凡的石猴，从一个无忧无虑的“美猴王”成长为求知学徒的故事。因为对“衰老和死亡”产生了青少年时期典型的困惑与恐惧，他勇敢地离开舒适区，独自踏上寻找长生不老方法的旅程。在经历漫长的探索后，他拜入一位神仙门下，被赐名“孙悟空”，这不仅让他获得了强大的能力，更重要的是，他开始拥有了真正的“身份认同”。然而，在掌握了新技能后，他因为急于在同伴面前炫耀而犯下错误，最终被师父赶走。这个结局是他成长中的第一次重大挫折，教会他能力越大，责任和约束也越大的道理，迫使他带着一身本领和复杂的心情回归故里。', '故事线框架': [{'场景': 1, '情节节点': '一块仙石在花果山顶诞生出一只石猴。他天性活泼，很快和山里的猴群打成一片。在一次集体探险中，他勇敢地跳入瀑布，发现了瀑布后的“水帘洞”，一个完美的家园。因这份勇气和贡献，他被猴群拥立为“美猴王”。', '核心冲突': '人际冲突/生存挑战：猴群需要一个安全的家园和一个能带领大家的领袖。', '关键转折': '石猴第一个跳入未知的瀑布，发现了水帘洞，证明了自己的胆识和能力。', '角色弧光推进': '从一个无名无姓的个体，通过一次勇敢的行动获得了社群的认可和“美猴王”的身份。这是他建立初步自我认同和归属感的过程。'}, {'场景': 2, '情节节点': '在一次宴会上，美猴王突然感到悲伤。他向猴子们坦白，虽然现在很快乐，但他害怕未来大家都会老去、死亡，一切美好都会消失。这种对未来的忧虑感染了所有猴子。', '核心冲突': '内心冲突：快乐的现实与对未来“死亡”的恐惧之间的矛盾，一种典型的存在主义焦虑。', '关键转折': '一只老猴子提出，世界上有佛、仙、神圣可以跳出轮回，不受死亡束缚。', '角色弧光推进': '角色第一次展现出超越物质享受的深度思考。对“我是谁，我将去哪里”的终极问题产生困惑，这成为他踏上成长之路的核心动机。'}, {'场景': 3, '情节节点': '美猴王下定决心，要出海寻找能教他长生不老的神仙。他告别了依依不舍的猴群，独自乘坐简陋的木筏，漂洋过海，开始了长达数年的孤独旅程。', '核心冲突': '人际冲突/内心冲突：离开熟悉和安逸的家园，面对未知的世界和对未来的不确定性。', '关键转折': '他最终抵达西牛贺洲，在深山中听到了一个樵夫唱着充满“道”意的歌曲。', '角色弧光推进': '展示了他为实现目标而具有的非凡决心和毅力。从一个群体的王，转变为一个孤独的求道者，身份开始发生转变。'}, {'场景': 4, '情节节点': '美猴王向樵夫打听，得知了神仙“须菩提祖师”的住处。他历经辛苦找到了“斜月三星洞”，在洞外耐心等候，最终被一个仙童引入，见到了祖师。', '核心冲突': '人际冲突：如何让一位高高在上的神仙接纳自己这个来自异乡的“野猴子”。', '关键转折': '祖师早已预知他的到来，这表明他此行是命中注定。', '角色弧光推进': '从一个迷茫的探索者变成了有明确目标的“准学生”。他表现出求知者应有的谦卑和礼貌，为接下来的学习奠定了基础。'}, {'场景': 5, '情节节点': '祖师询问他的来历。当得知他是天生石猴后，祖师感到欣喜，并根据他的形态特征，赐予他姓“孙”，名“悟空”。从此，他有了正式的名字。', '核心冲突': '身份认同：一个没有父母、没有姓氏的存在，如何被定义和接纳。', '关键转折': '祖师赐名“孙悟空”。这个名字不仅是一个代号，更蕴含了“领悟皆空”的期望和智慧。', '角色弧光推进': '这是角色身份认同的关键时刻。拥有名字意味着他不再是无根的石猴，而是一个有传承、有身份的个体，正式开启了全新的生命篇章。'}, {'场景': 6, '情节节点': '悟空在道观学习多年。祖师故意考验他，提供了几种无法真正长生的法术，都被悟空拒绝。祖师假装生气，用戒尺在他头上敲了三下，背手离开。悟空领悟了这是“三更时分从后门传授秘法”的暗号。', '核心冲突': '智力/认知冲突：如何理解师父看似不合理的行为背后的真正意图。', '关键转折': '悟空破解了师父的“谜题”，在深夜得到了长生不老的核心口诀。', '角色弧光推进': '悟空展现了超越常人的悟性和智慧，证明了他值得被传授最高深的秘法。他与师父之间建立了一种超越言语的默契和信任关系。'}, {'场景': 7, '情节节点': '悟空成功学会了长生术、七十二变和筋斗云等强大能力。在一次与师兄们的聚会中，经不住大家的起哄，他得意地当众变成一棵松树，引来众人的喝彩。', '核心冲突': '内心冲突：获得强大力量后，是保持低调还是向他人炫耀以获得认可的矛盾心理。', '关键转折': '众人的喧哗声惊动了祖师，导致了他的炫耀行为被发现。', '角色弧光推进': '角色弧光出现负向转折。强大的力量让他产生了骄傲和虚荣心，这是青少年在掌握新技能后常见的心理状态，为他即将面临的挫折埋下伏笔。'}, {'场景': 8, '情节节点': '祖师严厉地斥责了悟空的炫耀行为，指出这种行为会招来杀身之祸。为了不被连累，也为了让悟空明白这个道理，祖师狠心将他逐出师门，并命令他永远不许说是自己的徒弟。悟空含泪拜别，一个筋斗云翻回了花果山。', '核心冲突': '人际冲突：师父的教诲与悟空的行为产生了不可调和的矛盾，导致师徒关系破裂。', '关键转折': '祖师绝情地将悟空赶走，并立下重誓断绝关系。', '角色弧光推进': '悟空经历了成长中的第一次重大失败和分离。他明白了能力是一把双刃剑，不当的使用会带来严重后果。这次被“抛弃”的经历让他带着更复杂的自我认知回归，为后续的故事发展奠定了成熟但又叛逆的基调。'}]}

    # 生成角色档案
    # output = Extraction_Characters(ori)
    # 将json添加到json文件中，key为“Extraction_Summary”值为output
    character_gemini = {'全部角色': [{'规范化名称': '孙悟空', '别名': ['石猴', '美猴王', '猴王', '悟空', '猢狲'], '性别': '男', '人物生平': '他是由花果山顶上的一块仙石吸收天地精华后诞生的石猴。天生不凡，勇敢又好奇。因为第一个跳进水帘洞，为猴群找到了一个完美的家园，被大家尊称为“美猴王”。然而，快乐的日子让他开始害怕死亡，为了寻求长生不老的秘诀，他毅然离开家乡，漂洋过海，历经十多年，最终拜在须菩提祖师门下，被赐名“孙悟空”。在学艺期间，他凭借过人的智慧和勤奋，秘密学会了七十二变和筋斗云等高超法术。', '性格特征': ['天生领袖', '勇敢无畏', '聪慧过人', '追求不朽', '顽皮好炫耀', '意志坚定'], '成长弧': '孙悟空的成长始于对“死亡”的恐惧。这份恐惧将他从一个无忧无虑的山大王，转变为一个意志坚定的求道者。在求学过程中，他学会了忍耐和谦卑，能读懂师父的暗示。然而，他内心深处爱炫耀的缺点最终导致师父将他赶走。这次被驱逐是他成长中的关键一课，迫使他独立面对世界，也让他明白强大的力量需要用智慧和谦逊来驾驭，为他未来的旅程埋下了伏笔。', '说话语气': '早期作为猴王时，说话大胆直接，充满自信（“我去！我去！”）。在师父面前，他变得恭敬而机智，善于提问和表达自己强烈的求知欲。他能够领会弦外之音，显示出极高的悟性。'}, {'规范化名称': '须菩提祖师', '别名': ['祖师', '师父', '神仙'], '性别': '男', '人物生平': '一位隐居在“灵台方寸山，斜月三星洞”的世外高人，法力深不可测。他早已预见到孙悟空的到来，并看出他非凡的潜力。他不仅教给悟空强大的法术，更通过暗语和考验来磨练他的心性。最后，因为悟空在同门面前炫耀本领，他为了保护悟空也为了遵守修行的规矩，严厉地将他赶出师门。', '性格特征': ['智慧超群', '严格', '洞察力强', '神秘', '因材施教'], '成长弧': '作为一位导师型的角色，他自身没有明显的成长变化。他的作用是引导和塑造主角的成长。他看出悟空的才华，也预见了他不安分的天性可能带来的麻烦。他将悟空逐出师门，看似无情，实则是一种“断奶”式的教育，迫使悟空独立成长，并让他明白能力不能轻易示人，这是一种深沉的智慧和保护。', '说话语气': '说话充满权威，时而严肃，时而暗藏玄机。他会用反问和暗示来考验弟子的悟性，比如用戒尺敲三下代表三更时分。在训诫悟空时，语气严厉果决，不容置疑，显示出他作为一代宗师的威严。'}, {'规范化名称': '樵夫', '别名': ['老神仙'], '性别': '男', '人物生平': '一位住在灵台方寸山附近以砍柴为生的普通人。他因为要奉养老母亲，无法追求成仙之道。他从须菩提祖师那里学来一首歌，用来排解烦恼。他为人善良谦逊，为前来寻仙的孙悟空指明了去往斜月三星洞的道路。', '性格特征': ['孝顺', '谦逊', '善良', '知足常乐'], '成长弧': '他是一个功能性的静态角色，没有成长弧。他的存在为孙悟空提供了关键线索，同时也作为一种对比：世界上并非所有人都像悟空一样执着于长生，有的人选择在平凡的生活中承担自己的责任，并以此为乐。', '说话语气': '非常谦卑和朴实。当悟空称他为“老神仙”时，他立刻惶恐地否认，说话诚恳实在，清晰地讲述自己因为家庭责任而无法修行的现实情况。'}, {'规范化名称': '玉皇大帝', '别名': ['玉帝'], '性别': '男', '人物生平': '天庭的最高统治者。在石猴出生时，因为石猴眼中射出的金光惊动了天庭，他便派遣千里眼和顺风耳前往探查。在得知只是一个天生地养的石猴后，他表现得相当平静。', '性格特征': ['沉稳', '宽宏', '有见识'], '成长弧': '这是一个背景性的权威角色，没有个人成长。他的短暂出场确立了故事的宇宙观，他对于石猴诞生的淡定态度（“不足为奇”）暗示了孙悟空的存在是天地造化的一部分，为故事增添了宿命感。', '说话语气': '沉稳、威严且言简意赅，充满了一位宇宙统治者的气度，对于天地间的异象并不轻易动容。'}, {'规范化名称': '智慧猿猴', '别名': ['猿猴'], '性别': '男', '人物生平': '花果山猴群中的一员，具有非凡的见识。当美猴王为生老病死而忧愁时，是他站出来指出，世界上有佛、仙、神圣这三类人可以超脱轮回，不受阎王管辖，并告知他们居住在凡间世界，从而点燃了美猴王外出寻仙的希望。', '性格特征': ['有远见', '知识渊博', '善于言辞'], '成长弧': '作为推动情节发展的次要角色，他没有个人成长弧。他的作用就像一个“引路人”，在关键时刻为主角提供了至关重要的信息，是开启孙悟空求道之旅的直接催化剂。', '说话语气': '恭敬而清晰。他先是称赞猴王的远见卓识，然后条理分明地解释了长生不老的可能性，说话很有说服力。'}, {'规范化名称': '花果山众猴', '别名': ['群猴'], '性别': '男女皆有', '人物生平': '生活在花果山的一群猴子，是孙悟空最早的伙伴和子民。他们天真烂漫，热爱玩耍。在孙悟空的带领下，他们找到了水帘洞作为安身之所，并拥立他为王。他们对大王非常忠诚，但在思想深度上远不及大王，直到大王点破生死问题，他们才一同陷入忧虑。', '性格特征': ['忠诚', '享乐主义', '缺乏远见', '团结'], '成长弧': '作为一个集体，他们的成长体现在从纯粹的快乐到对生命短暂产生初步认识的转变。他们是孙悟空王者身份的证明，也是他内心牵挂的“家”，他们的存在让孙悟空的离开和回归更具意义。', '说话语气': '作为集体发言时，他们的语气通常反映了共同的情绪，如好奇（“这股水不知道是从哪里来的”）、欢呼或集体悲伤。'}, {'规范化名称': '菩提祖师众弟子', '别名': ['众仙', '众人', '诸位师兄'], '性别': '男女皆有', '人物生平': '在须菩提祖师门下修行的三四十位弟子。他们遵守师门规矩，按部就班地学习。他们曾教导刚入门的孙悟空基本礼仪，但在师父发怒时，也会不分青红皂白地指责悟空。他们对悟空的超凡能力感到好奇和羡慕，并怂恿他表演，无意中导致了悟空被逐出师门。', '性格特征': ['循规蹈矩', '好奇', '有些势利', '缺乏悟性'], '成长弧': '作为一个背景群体，他们没有成长。他们的存在主要是为了反衬孙悟空的与众不同：他们无法理解师父的暗语，显示出悟性的差距；他们对法术的好奇心也暴露了他们修行的境界还停留在比较浅的层次。', '说话语气': '作为群体，他们的语气是多变的。有时是指责（“你这顽劣的猴子！”），有时是好奇的怂恿（“你试演示一下，让我们看看”），反映了普通修行者的心态。'}, {'规范化名称': '盘古', '别名': [], '性别': '男', '人物生平': '中国神话中的创世神。在故事开篇被提及，讲述他用巨斧劈开混沌，分出天地，为世界的形成奠定了基础。他是整个故事宏大世界观的起点。', '性格特征': ['开天辟地', '力量强大'], '成长弧': '神话人物，用于交代背景，无个人成长弧。', '说话语气': '未在文本中说话。'}, {'规范化名称': '千里眼', '别名': ['二将'], '性别': '男', '人物生平': '天庭的神将，为玉皇大帝效力，拥有看到极远处事物的能力。在石猴出生时，他奉命与顺风耳一同探查情况。', '性格特征': ['忠诚', '尽职'], '成长弧': '功能性角色，无成长弧。他的任务是为天庭传递信息。', '说话语气': '作为臣子，说话语气正式、恭敬，以汇报工作为主。'}, {'规范化名称': '顺风耳', '别名': ['二将'], '性别': '男', '人物生平': '天庭的神将，千里眼的搭档，拥有听到极远处声音的能力。他与千里眼一起完成了探查石猴出生的任务。', '性格特征': ['忠诚', '尽职'], '成长弧': '功能性角色，无成长弧，与千里眼一同出现，共同完成任务。', '说话语气': '与千里眼一同汇报，语气正式、恭敬。'}, {'规范化名称': '仙童', '别名': ['道童'], '性别': '男', '人物生平': '须菩提祖师洞府门口的童子。他在师父的预先指示下，出门迎接前来拜师的孙悟空，并将他引入洞府。', '性格特征': ['彬彬有礼', '顺从', '气质不凡'], '成长弧': '作为引路人的次要角色，没有个人成长弧。', '说话语气': '礼貌而直接，带有孩童的好奇心和作为弟子的本分（“你是修行的吗？”“你跟我进来。”）。'}]}

    character_list = [
        {
            "规范化名称": char.get("规范化名称", ""),
            "别名": char.get("别名", []),
            "性格特征": char.get("性格特征", [])
            # "说话语气": char.get("说话语气", "")
        }
        for char in character_gemini.get("全部角色", [])
    ]
    character_list_str = json.dumps(character_list, indent=4, ensure_ascii=False)

    # 改编大纲生成
    # output = Script_Structure_Planning(ori,story_line_gemini)
    script_structure_gemini = {'改编大纲': [{'场景': 1, '改编目标': '加速故事开端，聚焦石猴的诞生和行动力，将“美猴王”身份的确立过程戏剧化，增强听觉冲击力。', '节奏调整': [{'部分': '原文开头关于宇宙形成、元会计数、十二时辰等冗长的哲学和背景介绍。', '调整方式': '全部删除。直接以“东胜神洲，花果山顶，有一块汇聚天地精华的仙石”开场，用简短有力的旁白引出石猴的诞生，立即进入故事核心。'}, {'部分': '群猴玩耍的细节描写，如“玩弹子”、“堆宝塔”、“捉虱子”等。', '调整方式': '简化处理。通过嘈杂、欢快的猴群音效和几句简短对话来体现他们的快乐，例如：“快来追我呀！”“看我爬得多高！”。核心是引出“我们去看看那瀑布后面是什么？”这个集体性的好奇心和挑战。'}, {'部分': '石猴发现水帘洞后，对洞内景色的静态、大段描述。', '调整方式': '将视觉描述转化为石猴兴奋的即时反应和对话。例如，他跳进去后，不是旁白描述，而是让他自己大喊：“哇！这里别有洞天！有石头的桌子，还有石头的床！大家快进来，我们有家了！”让其他猴子涌入后的惊叹声和欢呼声来共同构建这个空间感。'}], '转化困难的部分': [{'部分': '石猴诞生时“目运金光，射冲斗府，惊动高天上圣大慈仁者玉皇大天尊”的无声视觉场面。', '调整方式': '转化为听觉事件。可以设计一道划破天际的音效（如光束声），紧接着是天庭的场景，千里眼和顺风耳向玉帝禀报：“陛下，下方一道金光直冲天际，源头是花果山的一只石猴！”玉帝的回应（“此乃天生地养之物，不足为奇”）可以保留，快速建立世界观的宏大感。'}, {'部分': '石猴独自跳入瀑布的无声动作。', '调整方式': '通过猴群的对话来增强紧张感和戏剧性。在石猴跳之前，加入其他猴子的议论：“谁敢进去？”“那水那么急，会没命的！”。当石猴说“我去！”时，大家一片惊呼。他跳进去后，外面猴群焦急的等待声（“他怎么还不出来？”“是不是出事了？”），与瀑布内突然传出的石猴兴奋的回声形成强烈对比，听觉上更有张力。'}]}, {'场景': 2, '改编目标': '强化美猴王内心的情感冲突，将对“死亡”的哲学恐惧转化为青少年更能共情的“对美好事物终将逝去的忧虑”，使他的求道动机更具情感基础。', '节奏调整': [{'部分': '猴王与群猴关于“不知足”的对话。', '调整方式': '简化对话，让冲突更直接。猴王可以直接打断猴子们的欢笑，用低沉悲伤的语气说：“可是，这一切总有一天会结束的……我们会变老，会死去，再也看不到这么美的花果山了。”将抽象的“阎王老子”替换为更具体、更感性的失落感。'}, {'部分': '通臂猿猴解释“佛、仙、神圣”三种存在的概念。', '调整方式': '让老猴子的解释更简洁有力，像是在讲述一个传说。例如：“大王别怕！我听老一辈的猴子说过，天地间有能长生不老的仙人，他们能永远年轻，与天地同寿！”这比解释“跳出轮回”等复杂概念更易于青少年理解，并能迅速点燃猴王的希望。'}], '转化困难的部分': []}, {'场景': 3, '改编目标': '浓缩漫长的旅途，通过音效和内心独白，聚焦于美猴王从“王者”到“孤独求道者”的身份转变和坚韧决心。', '节奏调整': [{'部分': '长达八九年的海上漂泊和在人间的游历过程。', '调整方式': '用“声音蒙太奇”手法处理。以旁白“就这样，他告别了家乡，独自漂向茫茫大海”开始，然后用一段混合音效（风暴声、海浪声、不同城市的嘈杂人声）配合猴王简短的内心独白（“仙人在哪里？”“我一定要找到长生不老的方法！”）来快速展现时间的流逝和旅途的艰辛，最后以樵夫的歌声作为转折点切入下一场景。'}, {'部分': '猴王吓唬渔民、穿人衣服学人言行的情节。', '调整方式': '删除或简化。这些支线情节会拖慢主线节奏。可以直接让他登陆后，因听到樵夫的歌声而被吸引，直接进入核心情节。'}], '转化困难的部分': [{'部分': '孤独的航行和漫长的寻找过程。', '调整方式': '增加内心独白。通过猴王自言自语来表达他的孤独、困惑和从未动摇的决心。“大海真大啊……我的花果山在哪里？不行，我不能放弃，为了我的猴子猴孙们，我一定要找到神仙！”这能有效填充无对话的段落，并深化角色形象。'}]}, {'场景': 4, '改编目标': '简化寻访过程，聚焦于“见到希望”的激动心情，并强化须菩提祖师的神秘和高人风范。', '节奏调整': [{'部分': '与樵夫关于“为何不学仙”的详细对话。', '调整方式': '大幅删减。樵夫只需直接回答：“我唱的歌是山里的神仙教的，我凡尘俗事太多，没法学。你要是想找他，就沿着这条路往南走。”迅速给出关键信息，保持故事的推进速度。'}, {'部分': '对“灵台方寸山，斜月三星洞”景色的描写。', '调整方式': '将视觉描写转化为猴王的感叹。例如，当他看到洞府时，让他发出赞叹：“啊，真不愧是神仙住的地方，感觉空气都不一样了！”用角色的主观感受代替客观描述。'}], '转化困难的部分': [{'部分': '猴王在洞外耐心等候的无声过程。', '调整方式': '用内心独白和环境音效来表现。可以加入他焦急的呼吸声，以及他小声的自言自语：“神仙到底在不在里面？我该怎么办？”。当仙童开门时，祖师那句“外面有个修行的来了，去接待一下”从门内传来，能瞬间营造出“未见其人，先闻其声”的高人效果，并体现出祖师的未卜先知。'}]}, {'场景': 5, '改编目标': '突出“获得名字”这一核心事件的仪式感和重要性，将其塑造为石猴生命中第一个真正的身份认同节点。', '节奏调整': [{'部分': '祖师初见石猴时假装生气、呵斥他撒谎的段落。', '调整方式': '删除。直接让祖师对他能跨越重洋而来感到好奇和赞赏。这种处理方式更符合高人风范，也让赐名环节显得更顺理成章，避免了不必要的戏剧性转折，使情感更连贯。'}], '转化困难的部分': [{'部分': '祖师让石猴“走走看”的视觉动作。', '调整方式': '转化为对话和音效。祖师说：“你且走两步我看看。”然后配上猴子蹦跳的音效。祖师可以笑着说：“呵呵，你这形态，倒像个猢狲（猴子）。我便赐你姓‘孙’吧。”再通过猴王激动的回应：“我有姓了！我姓孙了！”来强化这一刻的情感冲击。'}, {'部分': '赐名“悟空”的哲学含义解释。', '调整方式': '简化解释，赋予其更直接的期望。祖师可以说：“名为‘悟空’，希望你未来能领悟真正的道理，不被表象迷惑。”这个解释对青少年来说更易于理解，也为他未来的成长埋下伏笔。'}]}, {'场景': 6, '改编目标': '简化复杂的道法理论，将重点放在“师徒斗智”的戏剧性情节上，突出悟空的悟性和师徒间的特殊默契。', '节奏调整': [{'部分': '祖师对“术”、“静”、“动”三种法门的详细解释。', '调整方式': '极度简化为一个快节奏的问答环节。祖师：“我教你求神问卜，趋吉避凶之术，学不学？”悟空：“能长生吗？”祖师：“不能。”悟空：“不学！”重复这个模式两三次，每次都以“能长生吗？不能！不学！”的句式快速结束，既能体现悟空目标的专一，又显得有趣，节奏明快。'}, {'部分': '其他弟子对悟空的指责和嘲笑。', '调整方式': '强化这一部分。在祖师“生气”离开后，加入其他师兄们的窃窃私语：“这猴子真笨，把师父气走了！”“看他以后怎么办！”。悟空的沉默和他们叽叽喳喳的议论形成对比，更能凸显悟空的与众不同和内心的了然。'}], '转化困难的部分': [{'部分': '祖师用戒尺打三下头、背手进门的无声暗号。', '调整方式': '通过悟空的内心独白来“解密”。在被打之后，悟空可以心想：“打我三下……难道是让我三更天去？从后门进去……师父一定是要私下传我真本事！”这样处理，听众能立刻明白其中的奥秘，并为悟空的聪明而喝彩。'}]}, {'场景': 7, '改编目标': '聚焦于青少年获得力量后典型的“炫耀心理”，制造出因虚荣心而引发麻烦的戏剧冲突，为最后的转折铺垫。', '节奏调整': [{'部分': '祖师讲解“三灾利害”的大段理论。', '调整方式': '简化为一句警告。在悟空学会本领后，祖师可以告诫他：“悟空，你的本事越大，引来的麻烦也越大，切记不可随意卖弄！”这句简短的警告，将成为后面他被逐出师门的直接伏笔，比复杂的理论更具戏剧张力。'}, {'部分': '祖师纠正悟空“爬云”和“腾云”的区别。', '调整方式': '可以保留，但要加快节奏。作为一个有趣的插曲，展现悟空学艺过程中的小挫折和师父的教导。重点是快速引出“筋斗云”这个酷炫的技能。'}, {'部分': '师兄们怂恿悟空表演。', '调整方式': '增强这部分的对话，体现出青少年间的“起哄”和“攀比”氛围。例如：“悟空，听说你学了七十二变，变个我们没见过的瞧瞧！”“是啊是啊，让我们开开眼界！”这种直接的语言更能激发悟空的表演欲。'}], '转化困难的部分': [{'部分': '悟空变成松树的视觉变化。', '调整方式': '通过师兄们的惊叹和描述来呈现。在悟空念动咒语并伴随一个“噗”的音效后，一个师兄大喊：“快看！悟空不见了，地上多了一棵松树！”另一个师兄可以触摸并描述：“天啊，连树皮和松针都跟真的一模一样！”众人的喝彩声（“好猴子！好猴子！”）将气氛推向高潮，也自然地引来了祖师。'}]}, {'场景': 8, '改编目标': '强化师徒分离的戏剧性和情感深度，让悟空的第一次重大挫折成为一次关于“责任”与“约束”的深刻教训，使其回归之旅带着复杂的情感。', '节奏调整': [{'部分': '祖师对悟空的长篇说教。', '调整方式': '将说教转化为更具情感冲击力的对话。祖师的语气应从愤怒转为痛心：“悟空！我教你本领，是让你护身的，不是让你拿来炫耀的！你今天能变松树引人喝彩，明天就会有人逼你变条龙来满足他们的欲望！到那时，你不给，他们便会害你！你给了，麻烦更大！你这性子，留在这里，迟早会给我惹来灭门之祸！”'}, {'部分': '悟空与师兄们的告别。', '调整方式': '简化。重点应放在悟空与师父之间的最后对话上，这是核心情感冲突所在。'}], '转化困难的部分': [{'部分': '祖师绝情地赶走悟空，并立下重誓。', '调整方式': '通过声音表演来传递复杂情感。祖师的命令（“你走！从哪里来，回哪里去！”）虽然严厉，但声音中可以带一丝不舍和无奈。悟空的哭泣声和恳求（“师父，我再也不敢了，别赶我走！”）要充满真情实感。最后的重誓（“你若说出是我徒弟，我便将你神魂贬至九幽，万劫不得翻身！”）要用极度严肃、不容置疑的语气说出，给听众带来巨大的震撼。'}, {'部分': '悟空一个筋斗云翻回花果山。', '调整方式': '用标志性的音效结束本章。在悟空含泪拜别后，响起一声撕裂空气的筋斗云音效，紧接着是风声呼啸，最后声音渐弱，旁白缓缓响起：“就这样，学会了一身通天本领的孙悟空，却在他最得意之时，被逐出了师门。带着无尽的委屈与不解，他飞向了那个阔别二十年的家——花果山。”留下一个充满悬念和复杂情感的结尾。'}]}]}
    script_structure_gemini_str = json.dumps(script_structure_gemini, indent=4, ensure_ascii=False)

    # 对白生成
    # dialogue_gemini2 = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     result = Dialogue_Generation(ori,character_list_str,tmp_structure)
    #     dialogue_gemini2['剧本'].append(result)
    # print(dialogue_gemini2)
    dialogue_gemini = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '千里眼', '对白': '陛下，大事不好了！下方东胜神洲，有一道金光直冲天际，刺得我眼睛都睁不开！'}, {'角色': '顺风耳', '对白': '没错陛下！我也听到了，那金光炸裂之时，声如龙吟，撼天动地！'}, {'角色': '玉皇大帝', '对白': '慌张什么。查明那金光是何物了吗？'}, {'角色': '千里眼', '对白': '回陛下，是花果山顶一块仙石炸裂，蹦出个石猴。那金光，正是从他眼中射出。'}, {'角色': '玉皇大帝', '对白': '呵，原来如此。不过是天地精华所生，不足为奇，由他去吧。'}, {'角色': '花果山众猴', '对白': '快来追我呀！哈哈哈！'}, {'角色': '花果山众猴', '对白': '你们看这瀑布！好壮观啊！这水是从哪里来的？'}, {'角色': '花果山众猴', '对白': '肯定是从天上流下来的！瀑布后面会有什么呢？'}, {'角色': '花果山众猴', '对白': '谁敢进去看看？要是谁有本事进去，又能安全出来，我们就拜他做大王！'}, {'角色': '花果山众猴', '对白': '别开玩笑了！这水这么急，跳进去小命都没了！'}, {'角色': '孙悟空', '对白': '我怕什么！我去！我去！'}, {'角色': '花果山众猴', '对白': '啊？你疯啦！快回来！'}, {'角色': '花果山众猴', '对白': '他……他真的跳进去了！'}, {'角色': '花果山众猴', '对白': '完了完了，他肯定被冲走了！怎么一点声音都没有？'}, {'角色': '花果山众猴', '对白': '都怪我，不该乱说话的……他……他不会真的出事了吧？'}, {'角色': '孙悟空', '对白': '喂——！大家快进来！这里面别有洞天啊！'}, {'角色': '花果山众猴', '对白': '是他的声音！他没死！'}, {'角色': '孙悟空', '对白': '这里面根本没有水，是一座铁板桥！桥那边有个大房子！快进来！'}, {'角色': '花果山众猴', '对白': '哇！是真的！这里好大啊！还有石头的桌子和床！'}, {'角色': '孙悟空', '对白': '你们看这石碑上写的！“花果山福地，水帘洞洞天”！从今天起，这里就是我们的家了！再也不怕刮风下雨了！'}, {'角色': '花果山众猴', '对白': '太好了！我们有家了！'}, {'角色': '花果山众猴', '对白': '等等！你遵守了约定，进去了又安全出来！你就是我们的大王！'}, {'角色': '花果山众猴', '对白': '对！拜见美猴王！'}, {'角色': '孙悟空', '对白': '哈哈哈！好！小的们，都起来吧！'}]}, {'场景': 2, '场景剧本': [{'角色': '花果山众猴', '对白': '大王！再干一杯！这新酿的果子酒，真是甜到心里去了！'}, {'角色': '花果山众猴', '对白': '是啊是啊！我们有吃有喝，自由自在，这日子简直比天上的神仙还快活！'}, {'角色': '孙悟空', '对白': '唉……'}, {'角色': '花果山众猴', '对白': '大王怎么叹气了？是这酒不够好喝，还是我们闹得太吵了？'}, {'角色': '孙悟空', '对白': '酒很好，你们也很好。只是……我忽然在想，我们现在虽然快活……'}, {'角色': '花果山众猴', '对白': '大王，您就是想太多啦！咱们每天都在这仙山福地里，不受任何人管束，多幸福啊！还有什么可担心的？'}, {'角色': '孙悟空', '对白': '可是，这一切总有一天会结束的。我们会变老，会掉光牙齿，会跳不动……然后，我们就会死去。'}, {'角色': '花果山众猴', '对白': '死？'}, {'角色': '孙悟空', '对白': '没错，到那个时候，我们就再也看不到这么美的花果山，再也喝不到这么甜的果子酒，再也……见不到彼此了。'}, {'角色': '花果山众猴', '对白': '我不要变老……我不要死……呜呜呜……'}, {'角色': '智慧猿猴', '对白': '大王！请不必如此忧虑！'}, {'角色': '孙悟空', '对白': '哦？难道你有办法让我们永远留在这花果山？'}, {'角色': '智慧猿猴', '对白': '大王别怕！我听老一辈的猴子说过，天地间有能长生不老的仙人，他们能永远年轻，与天地同寿！'}, {'角色': '孙悟空', '对白': '长生不老的仙人？这是真的吗？他们在哪儿？'}, {'角色': '智慧猿猴', '对白': '他们就住在这人间，在很远很远的仙山洞府之中。'}, {'角色': '孙悟空', '对白': '好！那我明天就告别你们下山，就算走遍天涯海角，我也一定要找到这长生不老的方法！'}, {'角色': '花果山众猴', '对白': '太好了！大王威武！'}, {'角色': '花果山众猴', '对白': '大王一定能找到仙人！我们明天就去多采些果子，为大王办一场最盛大的送行宴会！'}]}, {'场景': 3, '场景剧本': [{'角色': '孙悟空', '对白': '大海真大啊……我的花果山，我的孩儿们，你们还好吗？'}, {'角色': '孙悟空', '对白': '不行，我不能放弃！风再大，浪再高，我也要闯过去！'}, {'角色': '孙悟空', '对白': '这么多年了，人都说有神仙，可神仙到底在哪里？我一定要找到长生不老的方法！'}, {'角色': '樵夫', '对白': '观棋柯烂，伐木丁丁，云边谷口徐行……相逢处非仙即道，静坐讲黄庭。'}, {'角色': '孙悟空', '对白': '这歌声……有仙气！一定就在附近！'}, {'角色': '孙悟空', '对白': '老神仙！可算找到你了！'}, {'角色': '樵夫', '对白': '啊！你……你是哪来的猴子？可别叫我神仙，我只是个砍柴的。'}, {'角色': '孙悟空', '对白': '少来这套！我刚才听得清清楚楚，你唱的歌里又是“仙”又是“道”的。'}, {'角色': '樵夫', '对白': '唉，那歌词是一位真正的神仙教我的，说我烦恼的时候唱一唱，心里就舒坦了。'}, {'角色': '孙悟空', '对白': '真的有神仙？那你怎么不跟着他学长生不老？'}, {'角色': '樵夫', '对白': '我倒是想，可我命苦啊。家里老母亲没人照顾，我得砍柴换米，一天都耽误不得。'}, {'角色': '孙悟空', '对白': '你真是个孝子，将来一定有好报。那你能不能告诉我，那位神仙住在哪里？'}, {'角色': '樵夫', '对白': '当然可以。你看，那座山，叫灵台方寸山。'}, {'角色': '孙悟空', '对白': '灵台方寸山……'}, {'角色': '樵夫', '对白': '山里有个斜月三星洞，那位神仙叫须菩提祖师，就在洞里修行呢。'}, {'角色': '孙悟空', '对白': '须菩提祖师！'}, {'角色': '樵夫', '对白': '你顺着这条小路一直往南走，大概七八里地，就到了。'}, {'角色': '孙悟空', '对白': '多谢指点！大恩不言谢，我走啦！'}]}, {'场景': 4, '场景剧本': [{'角色': '孙悟空', '对白': '老神仙！请留步！'}, {'角色': '樵夫', '对白': '嗯？你这猴子，是在叫我吗？我可不是什么神仙。'}, {'角色': '孙悟空', '对白': '可我刚刚听您唱的歌，句句不离仙道，您一定就是神仙！'}, {'角色': '樵夫', '对白': '哈哈，你误会了。那歌是山里一位真神仙教我的，我就是个砍柴的，闲着没事唱着解乏罢了。'}, {'角色': '孙悟空', '对白': '真神仙？那您为什么不跟他学长生不老呢？'}, {'角色': '樵夫', '对白': '唉，我家里还有老母亲要照顾，哪有那个清闲功夫。我凡尘俗事太多，没法学。'}, {'角色': '孙悟空', '对白': '那太好了！不，我的意思是……那请您告诉我，那位神仙住在哪里？我一定要去拜访他！'}, {'角色': '樵夫', '对白': '你要是真想找他，就沿着这条小路往南走。那座最高的山叫灵台方寸山，山里有个斜月三星洞，神仙就住在那儿。'}, {'角色': '孙悟空', '对白': '多谢！多谢老神仙指路！我这就去！'}, {'角色': '樵夫', '对白': '都说了我不是神仙。快去吧，有缘分的猴子。'}, {'角色': '孙悟空', '对白': '啊，真不愧是神仙住的地方，感觉空气都不一样了！灵台方寸山，斜月三星洞……就是这里！'}, {'角色': '孙悟空', '对白': '神仙到底在不在里面？我该怎么办？喂！有人吗？我是诚心来拜师学艺的！'}, {'角色': '须菩提祖师', '对白': '童儿，开门吧。外面有个修行的来了，去接待一下。'}, {'角色': '仙童', '对白': '是你在外面喧哗吗？'}, {'角色': '孙悟空', '对白': '小仙童！是我，是我！我不是有意喧哗，我是来拜师的！'}, {'角色': '仙童', '对白': '你是来修行的？'}, {'角色': '孙悟空', '对白': '是！是的！'}, {'角色': '仙童', '对白': '嗯，我家师父刚刚正在讲道，忽然停下，说外面有个修行的到了。想必说的就是你了。'}, {'角色': '孙悟空', '对白': '就是我！就是我！你家师父真是神了！还没见我，就知道我来了！'}, {'角色': '仙童', '对白': '师父的道法，岂是你能揣测的。跟我进来吧。'}]}, {'场景': 5, '场景剧本': [{'角色': '仙童', '对白': '师父，求道之人已在殿外等候。'}, {'角色': '须菩提祖师', '对白': '嗯，让他进来吧。'}, {'角色': '孙悟空', '对白': '师父！弟子终于见到您了！求师父大发慈悲，收我为徒吧！'}, {'角色': '须菩提祖师', '对白': '你先起来回话。看你模样，并非人类。你是何方人士？从何处而来？'}, {'角色': '孙悟空', '对白': '回禀师父，弟子来自东胜神洲傲来国的花果山水帘洞。'}, {'角色': '须菩提祖师', '对白': '哦？东胜神洲？那地方离我这里，隔着两重大海和一整片南赡部洲。你是如何渡海而来的？'}, {'角色': '孙悟空', '对白': '弟子……弟子乘着木筏，在海上漂了很久，又在陆地上走了好多年，一路打听，才找到神仙住的地方。'}, {'角色': '须菩提祖师', '对白': '竟有如此毅力，倒也难得。你父母尚在？姓甚名谁？'}, {'角色': '孙悟空', '对白': '弟子没有父母，也没有姓名。我是从花果山顶的一块仙石里自己蹦出来的。'}, {'角色': '须菩提祖师', '对白': '呵呵，原来是个天生地养的石猴。你且走两步我看看。'}, {'角色': '孙悟空', '对白': '是，师父！'}, {'角色': '须菩提祖师', '对白': '你这形态，倒像个猢狲。猢狲去了兽旁，是个“孙”字。今日我便赐你姓“孙”，如何？'}, {'角色': '孙悟空', '对白': '我有姓了！我姓孙了！太好了！谢谢师父！谢谢师父！'}, {'角色': '须菩提祖师', '对白': '我门下弟子都是“悟”字辈，我再为你取个法名，名为“悟空”。'}, {'角色': '孙悟空', '对白': '孙……悟空？师父，这个名字是什么意思呀？听起来好厉害！'}, {'角色': '须菩提祖师', '对白': '名为“悟空”，是希望你未来能领悟真正的道理，不被世间表象所迷惑。'}, {'角色': '孙悟空', '对白': '领悟真理，不被迷惑！弟子明白了！我叫孙悟空！我就是孙悟空！'}, {'角色': '须菩提祖师', '对白': '好。孙悟空，从今日起，你便是我座下弟子了。'}, {'角色': '孙悟空', '对白': '师父！弟子孙悟空，给您磕头了！'}]}, {'场景': 6, '场景剧本': [{'角色': '须菩提祖师', '对白': '悟空，你既然入了我的门，今天就传你道法。我这有“术”字门，可请仙问卜，趋吉避凶，你学还是不学？'}, {'角色': '孙悟空', '对白': '师父，学了这个，能长生不老吗？'}, {'角色': '须菩提祖师', '对白': '不能。'}, {'角色': '孙悟空', '对白': '不学！'}, {'角色': '须菩提祖师', '对白': '那我教你“静”字门，参禅打坐，清净无为，如何？'}, {'角色': '孙悟空', '对白': '能长生吗？'}, {'角色': '须菩提祖师', '对白': '也……不能。'}, {'角色': '孙悟空', '对白': '不学，不学！'}, {'角色': '须菩提祖师', '对白': '也罢！还有一门“动”字之道，内外兼修，炼丹服药，可强身健体。'}, {'角色': '孙悟空', '对白': '师父，您就直说吧，这个到底能不能长生？'}, {'角色': '须菩提祖师', '对白': '犹如镜中花，水中月。'}, {'角色': '孙悟空', '对白': '那还是不学！我要学就学个能躲过阎王爷的真本事！'}, {'角色': '须菩提祖师', '对白': '好你个泼猴！这也不学，那也不学，存心消遣我是不是！'}, {'角色': '菩提祖师众弟子', '对白': '师父息怒！师父息怒！'}, {'角色': '菩提祖师众弟子', '对白': '悟空！你这顽猴，还不快给师父赔罪！'}, {'角色': '菩提祖师众弟子', '对白': '完了完了，这下闯大祸了！'}, {'角色': '菩提祖师众弟子', '对白': '你这猴子，真是胆大包天，竟敢顶撞师父！'}, {'角色': '菩提祖师众弟子', '对白': '师父肯定不会再理我们了，都是你害的！'}, {'角色': '菩提祖师众弟子', '对白': '看他那傻样，还笑呢，真是个呆子。'}, {'角色': '孙悟空', '对白': '嘿嘿，你们才不懂。师父打我三下，是让我三更时分去找他。'}, {'角色': '菩提祖师众弟子', '对白': '胡说八道什么！'}, {'角色': '孙悟空', '对白': '他背着手走进去，关上中门，是示意我从后门进去。师父这是要给我开小灶啦！'}]}, {'场景': 7, '场景剧本': [{'角色': '菩提祖师众弟子', '对白': '悟空，悟空！你快试试，师父教你的腾云术，你练成了吗？'}, {'角色': '孙悟空', '对白': '那当然！多亏师父指点，我已经能驾云飞升了！'}, {'角色': '须菩提祖师', '对白': '哦？是吗？那你飞起来，让我瞧瞧。'}, {'角色': '孙悟空', '对白': '好嘞！师父，各位师兄，看好了！'}, {'角色': '菩提祖师众弟子', '对白': '飞起来了！他真的飞起来了！'}, {'角色': '菩提祖师众弟子', '对白': '哎，可是……怎么感觉有点慢吞吞的？'}, {'角色': '须菩提祖师', '对白': '悟空，你这不叫腾云，顶多算是爬云。离真正的仙家之术，还差得远呢。'}, {'角色': '孙悟空', '对白': '啊？爬云？师父，那要怎样才算腾云？'}, {'角色': '须菩提祖师', '对白': '也罢，看你天性如此，我就传你一招“筋斗云”吧。一个跟头，十万八千里！'}, {'角色': '菩提祖师众弟子', '对白': '悟空，听说师父把七十二变都传给你了？真的假的？'}, {'角色': '孙悟空', '对白': '嘿嘿，不瞒各位师兄，师父传授的法门，我日夜苦练，都已学会了。'}, {'角色': '菩提祖师众弟子', '对白': '那给我们露一手呗！就变个我们没见过的东西瞧瞧！'}, {'角色': '孙悟空', '对白': '这个……师父告诫过，本事不能随便卖弄。'}, {'角色': '菩提祖师众弟子', '对白': '哎呀，我们都是自家人，怕什么！快变一个，就变一棵松树吧！'}, {'角色': '孙悟空', '对白': '好！这有何难！你们可看仔细了！'}, {'角色': '菩提祖师众弟子', '对白': '天哪！悟空不见了！地上……地上多了一棵松树！'}, {'角色': '菩提祖师众弟子', '对白': '连树皮和松针都跟真的一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '对白': '好猴子！好猴子！真厉害！'}, {'角色': '须菩提祖师', '对白': '是什么人在此大声喧哗！'}, {'角色': '孙悟空', '对白': '师父……弟子知错了。'}, {'角色': '须菩提祖师', '对白': '悟空，过来！我问你，你为何要卖弄神通，在此哗众取宠？'}, {'角色': '孙悟空', '对白': '我……我只是想让师兄们开开眼界。'}, {'角色': '须菩提祖师', '对白': '糊涂！你的本事越大，引来的麻烦就越大！别人见你有此能耐，若向你求取，你给还是不给？若是不给，人家岂能不加害于你？'}, {'角色': '孙悟空', '对白': '师父，我再也不敢了！求您饶我这一次！'}, {'角色': '须菩提祖师', '对白': '我不能再留你了。你走吧。'}, {'角色': '孙悟空', '对白': '师父！您要赶我走？我……我能去哪儿啊？'}, {'角色': '须菩提祖师', '对白': '你从哪里来，便回哪里去。但你切记，从今以后，不许对任何人说你是我徒弟。你若说出半个字来，我便将你神魂贬入九幽之地，万劫不得翻身！'}, {'角色': '孙悟空', '对白': '弟子不敢！绝不敢提师父半字，只说是我自己会的！'}]}, {'场景': 8, '场景剧本': [{'角色': '菩提祖师众弟子', '对白': '哇！悟空真的变成了一棵松树！'}, {'角色': '菩提祖师众弟子', '对白': '天哪，连树皮上的纹路都一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '对白': '好猴子！好猴子！这本事也太帅了！'}, {'角色': '须菩提祖师', '对白': '是谁在此喧哗！成何体统！'}, {'角色': '菩提祖师众弟子', '对白': '师父恕罪！是……是孙悟空在演练变化之术，我们一时……'}, {'角色': '须菩提祖师', '对白': '悟空，你过来！'}, {'角色': '孙悟空', '对白': '师父……弟子在。'}, {'角色': '须菩提祖师', '对白': '你倒是很得意啊。这点微末道行，就值得你如此卖弄吗？'}, {'角色': '孙悟空', '对白': '弟子不敢……只是师兄们好奇，我才……'}, {'角色': '须菩提祖师', '对白': '住口！我教你本领，是让你护身的，不是让你拿来炫耀的！'}, {'角色': '孙悟空', '对白': '师父，我……'}, {'角色': '须菩提祖师', '对白': '你今天能变棵松树引人喝彩，明天就会有人逼你变条真龙来满足他们的欲望！到那时，你不变，他们便会害你！你变了，麻烦更大！你懂不懂！'}, {'角色': '孙悟空', '对白': '弟子……弟子知错了。'}, {'角色': '须菩提祖师', '对白': '你这性子，留在这里，迟早会给我惹来灭门之祸！'}, {'角色': '孙悟空', '对白': '灭门之祸？师父，没那么严重吧……我以后改就是了！'}, {'角色': '须菩提祖师', '对白': '不必改了。你走吧。'}, {'角色': '孙悟空', '对白': '走？师父……您要赶我走？'}, {'角色': '须菩提祖师', '对白': '从哪里来，回哪里去。'}, {'角色': '孙悟空', '对白': '不要啊师父！我再也不敢了！求您别赶我走！我离家二十年，这里就是我的家啊！'}, {'角色': '须菩提祖师', '对白': '你给我听好了！你此去，无论惹出什么滔天大祸，都不许提我是你的师父。'}, {'角色': '孙悟空', '对白': '师父……'}, {'角色': '须菩提祖师', '对白': '你若说出半个字，我便知晓，定将你的神魂贬至九幽之处，让你万劫不得翻身！'}, {'角色': '孙悟空', '对白': '弟子……绝不敢提师父半字。只说……只说是我自己会的。'}, {'角色': '须菩提祖师', '对白': '去吧。'}, {'角色': '孙悟空', '对白': '师父大恩，弟子永世不忘。弟子……给师父磕头了。'}]}]}

    # 为dialogue的每个对话生成序号
    dialogue_str = dialogue_to_annotated_string(dialogue_gemini)

    # 旁白生成
    # narration_gemini2 = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     tmp_dialogue = dialogue_to_annotated_string_by_scene(dialogue_gemini['剧本'][index])
    #     result = Narration_Generation(ori,tmp_structure,tmp_dialogue)
    #     narration_gemini2['剧本'].append(result)
    # print(narration_gemini2)
    narration_gemini = {'剧本': [{'场景': 1, '旁白内容': [{'插入位置': 0, '旁白': '东胜神洲，花果山之巅，一块吸饱了日月精华的仙石轰然迸裂，一个石猴随之诞生。他眼中射出的两道金光，如利剑般划破天际，直冲云霄，瞬间惊动了天庭。'}, {'插入位置': 5, '旁白': '天庭之上不过是片刻的议论，凡间却已过去了数年。那石猴早已融入花果山的猴群之中，每日攀岩过涧，嬉戏打闹，享受着无拘无束的快活。'}, {'插入位置': 11, '旁白': '话音未落，石猴在众猴的惊呼声中，纵身一跃，像一颗出膛的炮弹，瞬间消失在了那道巨大的白色水幕之后。'}, {'插入位置': 15, '旁白': '瀑布之外，是猴群焦急的议论；瀑布之内，石猴却发现自己毫发无伤地站在一座铁桥上。震耳的水声被隔绝在外，眼前竟是一处宽敞明亮的洞府，石床石凳，一应俱全。'}, {'插入位置': 22, '旁白': '众猴又惊又喜，想起之前的约定，立刻齐刷刷地跪倒在地，心悦诚服地向这位勇敢的探路者献上最高的敬意。'}]}, {'场景': 2, '旁白内容': [{'插入位置': 2, '旁白': '水帘洞里，猴子们的欢笑声几乎要掀翻洞顶。然而，就在这片喧闹的中心，美猴王举着石杯，脸上的笑容却一点点凝固了。他望着眼前的一切，眼神忽然变得遥远。'}, {'插入位置': 6, '旁白': '那个猴子轻松的话语没能安慰美猴王。他放下酒杯，声音低沉下来，洞里瞬间安静了，所有猴子都停下了打闹，望向他们的大王。'}, {'插入位置': 9, '旁白': '美猴王的话像一块冰冷的石头，砸碎了宴会的欢乐气氛。刚才还吵着要再干一杯的猴子们，现在一个个都捂着脸，洞里只剩下压抑的哭泣声。'}, {'插入位置': 10, '旁白': '就在一片愁云惨雾中，一只毛发有些发白的通臂猿猴从猴群里挤了出来，他的声音不大，却清晰地盖过了所有哭声。'}, {'插入位置': 15, '旁白': '“仙人”这两个字仿佛一道光，瞬间驱散了美猴王眼中所有的阴霾。他猛地站起身，刚才的忧伤一扫而空，取而代之的是一种前所未有的、燃烧般的决心。'}]}, {'场景': 3, '旁白内容': [{'插入位置': 0, '旁白': '告别了花果山的孩儿们，美猴王独自一人，驾着简陋的木筏，漂向了无边无际、前途未卜的大海。'}, {'插入位置': 2, '旁白': '日复一日，年复一年。木筏在风暴中几乎散架，又在烈日下重新晾干。他登陆过无数陌生的海岸，穿梭在喧闹的人类城邦，却始终没有找到神仙的踪迹。'}, {'插入位置': 3, '旁白': '就在他几乎要放弃希望的时候，一阵悠扬的歌声，穿透了茂密的森林，飘进了他的耳朵。'}, {'插入位置': 5, '旁白': '他精神一振，循着歌声在林间飞速穿梭，拨开最后一片枝叶，看到的却是一个正在砍柴的樵夫。'}, {'插入位置': 12, '旁白': '樵夫放下斧头，用手指了指远处一座云雾缭绕的高山。'}, {'插入位置': 17, '旁白': '猴王大喜过望，他朝着樵夫深深鞠了一躬，接着便化作一道影子，迫不及待地向着南边的小路冲去。'}]}, {'场景': 4, '旁白内容': [{'插入位置': 0, '旁白': '独自漂洋过海，又在大陆上寻觅了近十年，孙悟空几乎就要放弃希望。这天，他在深山里穿行，一阵悠扬的歌声忽然飘入耳中。他循声拨开树丛，看到一个樵夫正一边砍柴，一边放声高歌。'}, {'插入位置': 10, '旁白': '孙悟空告别樵夫，心中燃起从未有过的激动。他沿着那条小路，翻过山坡，穿过密林，终于在云雾缭绕的山顶，看到了一座洞府。洞府前，一块石碑上赫然刻着十个大字：灵台方寸山，斜月三星洞。'}, {'插入位置': 11, '旁白': '他兴奋地冲上前，却发现洞门紧闭，四周静得连一根针掉在地上都能听见。他等了又等，从中午等到日落西山，洞门依然纹丝不动。'}, {'插入位置': 13, '旁白': '话音刚落，厚重的石门吱呀一声向内打开。一个眉清目秀、气质不凡的小仙童走了出来，好奇地上下打量着孙悟空。'}]}, {'场景': 5, '旁白内容': [{'插入位置': 2, '旁白': '石猴跟着仙童穿过层层殿宇，终于见到了端坐在高台上的须菩提祖师。他来不及细看周围的景象，便快步上前，双膝跪地，额头重重地贴在冰凉的地面上。'}, {'插入位置': 7, '旁白': '听完石猴的讲述，祖师沉默了片刻，目光落在这只风尘仆仆的猴子身上，似乎在估量他话中的分量。'}, {'插入位置': 11, '旁白': '石猴立刻站起来，在空旷的大殿里连蹦带跳地走了两圈，抓耳挠腮，动作轻快又灵巧，天生的猴性一览无余。'}, {'插入位置': 12, '旁白': '这简单的两个字，对石猴来说却重如千斤。他愣了片刻，随即反应过来，又一次拜倒在地，额头一下下磕在地上，仿佛要将这份喜悦牢牢刻住。'}, {'插入位置': 17, '旁白': '他站起身，一遍遍念着这个属于自己的名字。声音从最初的试探，变得越来越响亮，越来越坚定。从这一刻起，他不再只是一个从石头里蹦出来的无名猴子了。'}]}, {'场景': 6, '旁白内容': [{'插入位置': 12, '旁白': '一连串的拒绝终于耗尽了祖师的耐心。他猛地从蒲团上站起身，抄起戒尺，指向悟空。'}, {'插入位置': 13, '旁白': '话音未落，祖师走下高台，用戒尺在悟空头上不轻不重地敲了三下。随即，他一言不发，背着双手走入内堂，关上了中间的大门，把所有人都晾在了外面。'}, {'插入位置': 19, '旁白': '面对师兄们的七嘴八舌，孙悟空不仅没有丝毫慌乱，反而露出了一个神秘的微笑。'}]}, {'场景': 7, '旁白内容': [{'插入位置': 0, '旁白': '又是一日课后，三星洞外的松树下，师兄们正围着悟空，气氛轻松又热闹。'}, {'插入位置': 3, '旁白': '悟空得意地一笑，深吸一口气，双脚猛地一蹬，身体晃晃悠悠地升了起来，在半空中努力保持着平衡。'}, {'插入位置': 6, '旁白': '飞了不到一小圈，悟空就有些狼狈地落回众人面前，脚下还踉跄了几步。'}, {'插入位置': 9, '旁白': '又过了些时日，悟空不仅练成了筋斗云，七十二变的法术也已烂熟于心。这天，师兄们又围了上来，满脸的好奇和羡慕。'}, {'插入位置': 14, '旁白': '悟空心里的那点犹豫，瞬间被师兄们的起哄声冲散了。他清了清嗓子，捻动法诀，口中念念有词。'}, {'插入位置': 18, '旁白': '众人的喝彩声一阵高过一阵，在清静的山谷中回荡。突然，一声严厉的呵斥像冷水一样泼了下来，让所有人都打了个寒颤。'}, {'插入位置': 19, '旁白': '热闹的场面瞬间凝固。那棵松树也随之变回了孙悟空的模样，他低着头，不敢看师父的眼睛。'}, {'插入位置': 26, '旁白': '祖师的语气冰冷，不带一丝商量的余地。'}, {'插入位置': 28, '旁白': '悟空知道再无挽回的余地。他朝祖师重重地磕了三个响头，然后翻身跃起，驾着筋斗云，化作一道金光，消失在了天际。'}]}, {'场景': 8, '旁白内容': [{'插入位置': 3, '旁白': '弟子们的喝彩声在安静的松林里显得格外响亮，打破了午后的宁静，也惊动了正在静修的祖师。'}, {'插入位置': 6, '旁白': '祖师话音刚落，那棵挺拔的松树便在一阵微光中迅速变回了孙悟空的原形。他从师兄们中间挤出来，忐忑地低下了头。'}, {'插入位置': 16, '旁白': '“走吧”这两个字像晴天霹雳，悟空脸上的得意瞬间凝固，他完全不敢相信自己的耳朵。'}, {'插入位置': 19, '旁白': '悟空还想再求，却看到师父眼中闪过一丝决绝。他知道，这里再也不是他的家了。'}, {'插入位置': 24, '旁白': '悟空再也忍不住泪水，重重地跪了下去，朝着恩师，磕了最后一个响头。'}]}]}


    # 合并旁白与对白
    # result = combine_dialogue_and_narration(dialogue_gemini, narration_gemini)
    # print(result)

    # 合并后的剧本
    pre_script_gemini = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '旁白', '内容': '东胜神洲，花果山之巅，一块吸饱了日月精华的仙石轰然迸裂，一个石猴随之诞生。他眼中射出的两道金光，如利剑般划破天际，直冲云霄，瞬间惊动了天庭。'}, {'角色': '千里眼', '内容': '陛下，大事不好了！下方东胜神洲，有一道金光直冲天际，刺得我眼睛都睁不开！'}, {'角色': '顺风耳', '内容': '没错陛下！我也听到了，那金光炸裂之时，声如龙吟，撼天动地！'}, {'角色': '玉皇大帝', '内容': '慌张什么。查明那金光是何物了吗？'}, {'角色': '千里眼', '内容': '回陛下，是花果山顶一块仙石炸裂，蹦出个石猴。那金光，正是从他眼中射出。'}, {'角色': '玉皇大帝', '内容': '呵，原来如此。不过是天地精华所生，不足为奇，由他去吧。'}, {'角色': '旁白', '内容': '天庭之上不过是片刻的议论，凡间却已过去了数年。那石猴早已融入花果山的猴群之中，每日攀岩过涧，嬉戏打闹，享受着无拘无束的快活。'}, {'角色': '花果山众猴', '内容': '快来追我呀！哈哈哈！'}, {'角色': '花果山众猴', '内容': '你们看这瀑布！好壮观啊！这水是从哪里来的？'}, {'角色': '花果山众猴', '内容': '肯定是从天上流下来的！瀑布后面会有什么呢？'}, {'角色': '花果山众猴', '内容': '谁敢进去看看？要是谁有本事进去，又能安全出来，我们就拜他做大王！'}, {'角色': '花果山众猴', '内容': '别开玩笑了！这水这么急，跳进去小命都没了！'}, {'角色': '孙悟空', '内容': '我怕什么！我去！我去！'}, {'角色': '旁白', '内容': '话音未落，石猴在众猴的惊呼声中，纵身一跃，像一颗出膛的炮弹，瞬间消失在了那道巨大的白色水幕之后。'}, {'角色': '花果山众猴', '内容': '啊？你疯啦！快回来！'}, {'角色': '花果山众猴', '内容': '他……他真的跳进去了！'}, {'角色': '花果山众猴', '内容': '完了完了，他肯定被冲走了！怎么一点声音都没有？'}, {'角色': '花果山众猴', '内容': '都怪我，不该乱说话的……他……他不会真的出事了吧？'}, {'角色': '旁白', '内容': '瀑布之外，是猴群焦急的议论；瀑布之内，石猴却发现自己毫发无伤地站在一座铁桥上。震耳的水声被隔绝在外，眼前竟是一处宽敞明亮的洞府，石床石凳，一应俱全。'}, {'角色': '孙悟空', '内容': '喂——！大家快进来！这里面别有洞天啊！'}, {'角色': '花果山众猴', '内容': '是他的声音！他没死！'}, {'角色': '孙悟空', '内容': '这里面根本没有水，是一座铁板桥！桥那边有个大房子！快进来！'}, {'角色': '花果山众猴', '内容': '哇！是真的！这里好大啊！还有石头的桌子和床！'}, {'角色': '孙悟空', '内容': '你们看这石碑上写的！“花果山福地，水帘洞洞天”！从今天起，这里就是我们的家了！再也不怕刮风下雨了！'}, {'角色': '花果山众猴', '内容': '太好了！我们有家了！'}, {'角色': '花果山众猴', '内容': '等等！你遵守了约定，进去了又安全出来！你就是我们的大王！'}, {'角色': '旁白', '内容': '众猴又惊又喜，想起之前的约定，立刻齐刷刷地跪倒在地，心悦诚服地向这位勇敢的探路者献上最高的敬意。'}, {'角色': '花果山众猴', '内容': '对！拜见美猴王！'}, {'角色': '孙悟空', '内容': '哈哈哈！好！小的们，都起来吧！'}]}, {'场景': 2, '场景剧本': [{'角色': '花果山众猴', '内容': '大王！再干一杯！这新酿的果子酒，真是甜到心里去了！'}, {'角色': '花果山众猴', '内容': '是啊是啊！我们有吃有喝，自由自在，这日子简直比天上的神仙还快活！'}, {'角色': '旁白', '内容': '水帘洞里，猴子们的欢笑声几乎要掀翻洞顶。然而，就在这片喧闹的中心，美猴王举着石杯，脸上的笑容却一点点凝固了。他望着眼前的一切，眼神忽然变得遥远。'}, {'角色': '孙悟空', '内容': '唉……'}, {'角色': '花果山众猴', '内容': '大王怎么叹气了？是这酒不够好喝，还是我们闹得太吵了？'}, {'角色': '孙悟空', '内容': '酒很好，你们也很好。只是……我忽然在想，我们现在虽然快活……'}, {'角色': '花果山众猴', '内容': '大王，您就是想太多啦！咱们每天都在这仙山福地里，不受任何人管束，多幸福啊！还有什么可担心的？'}, {'角色': '旁白', '内容': '那个猴子轻松的话语没能安慰美猴王。他放下酒杯，声音低沉下来，洞里瞬间安静了，所有猴子都停下了打闹，望向他们的大王。'}, {'角色': '孙悟空', '内容': '可是，这一切总有一天会结束的。我们会变老，会掉光牙齿，会跳不动……然后，我们就会死去。'}, {'角色': '花果山众猴', '内容': '死？'}, {'角色': '孙悟空', '内容': '没错，到那个时候，我们就再也看不到这么美的花果山，再也喝不到这么甜的果子酒，再也……见不到彼此了。'}, {'角色': '旁白', '内容': '美猴王的话像一块冰冷的石头，砸碎了宴会的欢乐气氛。刚才还吵着要再干一杯的猴子们，现在一个个都捂着脸，洞里只剩下压抑的哭泣声。'}, {'角色': '花果山众猴', '内容': '我不要变老……我不要死……呜呜呜……'}, {'角色': '旁白', '内容': '就在一片愁云惨雾中，一只毛发有些发白的通臂猿猴从猴群里挤了出来，他的声音不大，却清晰地盖过了所有哭声。'}, {'角色': '智慧猿猴', '内容': '大王！请不必如此忧虑！'}, {'角色': '孙悟空', '内容': '哦？难道你有办法让我们永远留在这花果山？'}, {'角色': '智慧猿猴', '内容': '大王别怕！我听老一辈的猴子说过，天地间有能长生不老的仙人，他们能永远年轻，与天地同寿！'}, {'角色': '孙悟空', '内容': '长生不老的仙人？这是真的吗？他们在哪儿？'}, {'角色': '智慧猿猴', '内容': '他们就住在这人间，在很远很远的仙山洞府之中。'}, {'角色': '旁白', '内容': '“仙人”这两个字仿佛一道光，瞬间驱散了美猴王眼中所有的阴霾。他猛地站起身，刚才的忧伤一扫而空，取而代之的是一种前所未有的、燃烧般的决心。'}, {'角色': '孙悟空', '内容': '好！那我明天就告别你们下山，就算走遍天涯海角，我也一定要找到这长生不老的方法！'}, {'角色': '花果山众猴', '内容': '太好了！大王威武！'}, {'角色': '花果山众猴', '内容': '大王一定能找到仙人！我们明天就去多采些果子，为大王办一场最盛大的送行宴会！'}]}, {'场景': 3, '场景剧本': [{'角色': '旁白', '内容': '告别了花果山的孩儿们，美猴王独自一人，驾着简陋的木筏，漂向了无边无际、前途未卜的大海。'}, {'角色': '孙悟空', '内容': '大海真大啊……我的花果山，我的孩儿们，你们还好吗？'}, {'角色': '孙悟空', '内容': '不行，我不能放弃！风再大，浪再高，我也要闯过去！'}, {'角色': '旁白', '内容': '日复一日，年复一年。木筏在风暴中几乎散架，又在烈日下重新晾干。他登陆过无数陌生的海岸，穿梭在喧闹的人类城邦，却始终没有找到神仙的踪迹。'}, {'角色': '孙悟空', '内容': '这么多年了，人都说有神仙，可神仙到底在哪里？我一定要找到长生不老的方法！'}, {'角色': '旁白', '内容': '就在他几乎要放弃希望的时候，一阵悠扬的歌声，穿透了茂密的森林，飘进了他的耳朵。'}, {'角色': '樵夫', '内容': '观棋柯烂，伐木丁丁，云边谷口徐行……相逢处非仙即道，静坐讲黄庭。'}, {'角色': '孙悟空', '内容': '这歌声……有仙气！一定就在附近！'}, {'角色': '旁白', '内容': '他精神一振，循着歌声在林间飞速穿梭，拨开最后一片枝叶，看到的却是一个正在砍柴的樵夫。'}, {'角色': '孙悟空', '内容': '老神仙！可算找到你了！'}, {'角色': '樵夫', '内容': '啊！你……你是哪来的猴子？可别叫我神仙，我只是个砍柴的。'}, {'角色': '孙悟空', '内容': '少来这套！我刚才听得清清楚楚，你唱的歌里又是“仙”又是“道”的。'}, {'角色': '樵夫', '内容': '唉，那歌词是一位真正的神仙教我的，说我烦恼的时候唱一唱，心里就舒坦了。'}, {'角色': '孙悟空', '内容': '真的有神仙？那你怎么不跟着他学长生不老？'}, {'角色': '樵夫', '内容': '我倒是想，可我命苦啊。家里老母亲没人照顾，我得砍柴换米，一天都耽误不得。'}, {'角色': '孙悟空', '内容': '你真是个孝子，将来一定有好报。那你能不能告诉我，那位神仙住在哪里？'}, {'角色': '旁白', '内容': '樵夫放下斧头，用手指了指远处一座云雾缭绕的高山。'}, {'角色': '樵夫', '内容': '当然可以。你看，那座山，叫灵台方寸山。'}, {'角色': '孙悟空', '内容': '灵台方寸山……'}, {'角色': '樵夫', '内容': '山里有个斜月三星洞，那位神仙叫须菩提祖师，就在洞里修行呢。'}, {'角色': '孙悟空', '内容': '须菩提祖师！'}, {'角色': '樵夫', '内容': '你顺着这条小路一直往南走，大概七八里地，就到了。'}, {'角色': '旁白', '内容': '猴王大喜过望，他朝着樵夫深深鞠了一躬，接着便化作一道影子，迫不及待地向着南边的小路冲去。'}, {'角色': '孙悟空', '内容': '多谢指点！大恩不言谢，我走啦！'}]}, {'场景': 4, '场景剧本': [{'角色': '旁白', '内容': '独自漂洋过海，又在大陆上寻觅了近十年，孙悟空几乎就要放弃希望。这天，他在深山里穿行，一阵悠扬的歌声忽然飘入耳中。他循声拨开树丛，看到一个樵夫正一边砍柴，一边放声高歌。'}, {'角色': '孙悟空', '内容': '老神仙！请留步！'}, {'角色': '樵夫', '内容': '嗯？你这猴子，是在叫我吗？我可不是什么神仙。'}, {'角色': '孙悟空', '内容': '可我刚刚听您唱的歌，句句不离仙道，您一定就是神仙！'}, {'角色': '樵夫', '内容': '哈哈，你误会了。那歌是山里一位真神仙教我的，我就是个砍柴的，闲着没事唱着解乏罢了。'}, {'角色': '孙悟空', '内容': '真神仙？那您为什么不跟他学长生不老呢？'}, {'角色': '樵夫', '内容': '唉，我家里还有老母亲要照顾，哪有那个清闲功夫。我凡尘俗事太多，没法学。'}, {'角色': '孙悟空', '内容': '那太好了！不，我的意思是……那请您告诉我，那位神仙住在哪里？我一定要去拜访他！'}, {'角色': '樵夫', '内容': '你要是真想找他，就沿着这条小路往南走。那座最高的山叫灵台方寸山，山里有个斜月三星洞，神仙就住在那儿。'}, {'角色': '孙悟空', '内容': '多谢！多谢老神仙指路！我这就去！'}, {'角色': '樵夫', '内容': '都说了我不是神仙。快去吧，有缘分的猴子。'}, {'角色': '旁白', '内容': '孙悟空告别樵夫，心中燃起从未有过的激动。他沿着那条小路，翻过山坡，穿过密林，终于在云雾缭绕的山顶，看到了一座洞府。洞府前，一块石碑上赫然刻着十个大字：灵台方寸山，斜月三星洞。'}, {'角色': '孙悟空', '内容': '啊，真不愧是神仙住的地方，感觉空气都不一样了！灵台方寸山，斜月三星洞……就是这里！'}, {'角色': '旁白', '内容': '他兴奋地冲上前，却发现洞门紧闭，四周静得连一根针掉在地上都能听见。他等了又等，从中午等到日落西山，洞门依然纹丝不动。'}, {'角色': '孙悟空', '内容': '神仙到底在不在里面？我该怎么办？喂！有人吗？我是诚心来拜师学艺的！'}, {'角色': '须菩提祖师', '内容': '童儿，开门吧。外面有个修行的来了，去接待一下。'}, {'角色': '旁白', '内容': '话音刚落，厚重的石门吱呀一声向内打开。一个眉清目秀、气质不凡的小仙童走了出来，好奇地上下打量着孙悟空。'}, {'角色': '仙童', '内容': '是你在外面喧哗吗？'}, {'角色': '孙悟空', '内容': '小仙童！是我，是我！我不是有意喧哗，我是来拜师的！'}, {'角色': '仙童', '内容': '你是来修行的？'}, {'角色': '孙悟空', '内容': '是！是的！'}, {'角色': '仙童', '内容': '嗯，我家师父刚刚正在讲道，忽然停下，说外面有个修行的到了。想必说的就是你了。'}, {'角色': '孙悟空', '内容': '就是我！就是我！你家师父真是神了！还没见我，就知道我来了！'}, {'角色': '仙童', '内容': '师父的道法，岂是你能揣测的。跟我进来吧。'}]}, {'场景': 5, '场景剧本': [{'角色': '仙童', '内容': '师父，求道之人已在殿外等候。'}, {'角色': '须菩提祖师', '内容': '嗯，让他进来吧。'}, {'角色': '旁白', '内容': '石猴跟着仙童穿过层层殿宇，终于见到了端坐在高台上的须菩提祖师。他来不及细看周围的景象，便快步上前，双膝跪地，额头重重地贴在冰凉的地面上。'}, {'角色': '孙悟空', '内容': '师父！弟子终于见到您了！求师父大发慈悲，收我为徒吧！'}, {'角色': '须菩提祖师', '内容': '你先起来回话。看你模样，并非人类。你是何方人士？从何处而来？'}, {'角色': '孙悟空', '内容': '回禀师父，弟子来自东胜神洲傲来国的花果山水帘洞。'}, {'角色': '须菩提祖师', '内容': '哦？东胜神洲？那地方离我这里，隔着两重大海和一整片南赡部洲。你是如何渡海而来的？'}, {'角色': '孙悟空', '内容': '弟子……弟子乘着木筏，在海上漂了很久，又在陆地上走了好多年，一路打听，才找到神仙住的地方。'}, {'角色': '旁白', '内容': '听完石猴的讲述，祖师沉默了片刻，目光落在这只风尘仆仆的猴子身上，似乎在估量他话中的分量。'}, {'角色': '须菩提祖师', '内容': '竟有如此毅力，倒也难得。你父母尚在？姓甚名谁？'}, {'角色': '孙悟空', '内容': '弟子没有父母，也没有姓名。我是从花果山顶的一块仙石里自己蹦出来的。'}, {'角色': '须菩提祖师', '内容': '呵呵，原来是个天生地养的石猴。你且走两步我看看。'}, {'角色': '孙悟空', '内容': '是，师父！'}, {'角色': '旁白', '内容': '石猴立刻站起来，在空旷的大殿里连蹦带跳地走了两圈，抓耳挠腮，动作轻快又灵巧，天生的猴性一览无余。'}, {'角色': '须菩提祖师', '内容': '你这形态，倒像个猢狲。猢狲去了兽旁，是个“孙”字。今日我便赐你姓“孙”，如何？'}, {'角色': '旁白', '内容': '这简单的两个字，对石猴来说却重如千斤。他愣了片刻，随即反应过来，又一次拜倒在地，额头一下下磕在地上，仿佛要将这份喜悦牢牢刻住。'}, {'角色': '孙悟空', '内容': '我有姓了！我姓孙了！太好了！谢谢师父！谢谢师父！'}, {'角色': '须菩提祖师', '内容': '我门下弟子都是“悟”字辈，我再为你取个法名，名为“悟空”。'}, {'角色': '孙悟空', '内容': '孙……悟空？师父，这个名字是什么意思呀？听起来好厉害！'}, {'角色': '须菩提祖师', '内容': '名为“悟空”，是希望你未来能领悟真正的道理，不被世间表象所迷惑。'}, {'角色': '孙悟空', '内容': '领悟真理，不被迷惑！弟子明白了！我叫孙悟空！我就是孙悟空！'}, {'角色': '旁白', '内容': '他站起身，一遍遍念着这个属于自己的名字。声音从最初的试探，变得越来越响亮，越来越坚定。从这一刻起，他不再只是一个从石头里蹦出来的无名猴子了。'}, {'角色': '须菩提祖师', '内容': '好。孙悟空，从今日起，你便是我座下弟子了。'}, {'角色': '孙悟空', '内容': '师父！弟子孙悟空，给您磕头了！'}]}, {'场景': 6, '场景剧本': [{'角色': '须菩提祖师', '内容': '悟空，你既然入了我的门，今天就传你道法。我这有“术”字门，可请仙问卜，趋吉避凶，你学还是不学？'}, {'角色': '孙悟空', '内容': '师父，学了这个，能长生不老吗？'}, {'角色': '须菩提祖师', '内容': '不能。'}, {'角色': '孙悟空', '内容': '不学！'}, {'角色': '须菩提祖师', '内容': '那我教你“静”字门，参禅打坐，清净无为，如何？'}, {'角色': '孙悟空', '内容': '能长生吗？'}, {'角色': '须菩提祖师', '内容': '也……不能。'}, {'角色': '孙悟空', '内容': '不学，不学！'}, {'角色': '须菩提祖师', '内容': '也罢！还有一门“动”字之道，内外兼修，炼丹服药，可强身健体。'}, {'角色': '孙悟空', '内容': '师父，您就直说吧，这个到底能不能长生？'}, {'角色': '须菩提祖师', '内容': '犹如镜中花，水中月。'}, {'角色': '孙悟空', '内容': '那还是不学！我要学就学个能躲过阎王爷的真本事！'}, {'角色': '旁白', '内容': '一连串的拒绝终于耗尽了祖师的耐心。他猛地从蒲团上站起身，抄起戒尺，指向悟空。'}, {'角色': '须菩提祖师', '内容': '好你个泼猴！这也不学，那也不学，存心消遣我是不是！'}, {'角色': '旁白', '内容': '话音未落，祖师走下高台，用戒尺在悟空头上不轻不重地敲了三下。随即，他一言不发，背着双手走入内堂，关上了中间的大门，把所有人都晾在了外面。'}, {'角色': '菩提祖师众弟子', '内容': '师父息怒！师父息怒！'}, {'角色': '菩提祖师众弟子', '内容': '悟空！你这顽猴，还不快给师父赔罪！'}, {'角色': '菩提祖师众弟子', '内容': '完了完了，这下闯大祸了！'}, {'角色': '菩提祖师众弟子', '内容': '你这猴子，真是胆大包天，竟敢顶撞师父！'}, {'角色': '菩提祖师众弟子', '内容': '师父肯定不会再理我们了，都是你害的！'}, {'角色': '菩提祖师众弟子', '内容': '看他那傻样，还笑呢，真是个呆子。'}, {'角色': '旁白', '内容': '面对师兄们的七嘴八舌，孙悟空不仅没有丝毫慌乱，反而露出了一个神秘的微笑。'}, {'角色': '孙悟空', '内容': '嘿嘿，你们才不懂。师父打我三下，是让我三更时分去找他。'}, {'角色': '菩提祖师众弟子', '内容': '胡说八道什么！'}, {'角色': '孙悟空', '内容': '他背着手走进去，关上中门，是示意我从后门进去。师父这是要给我开小灶啦！'}]}, {'场景': 7, '场景剧本': [{'角色': '旁白', '内容': '又是一日课后，三星洞外的松树下，师兄们正围着悟空，气氛轻松又热闹。'}, {'角色': '菩提祖师众弟子', '内容': '悟空，悟空！你快试试，师父教你的腾云术，你练成了吗？'}, {'角色': '孙悟空', '内容': '那当然！多亏师父指点，我已经能驾云飞升了！'}, {'角色': '须菩提祖师', '内容': '哦？是吗？那你飞起来，让我瞧瞧。'}, {'角色': '旁白', '内容': '悟空得意地一笑，深吸一口气，双脚猛地一蹬，身体晃晃悠悠地升了起来，在半空中努力保持着平衡。'}, {'角色': '孙悟空', '内容': '好嘞！师父，各位师兄，看好了！'}, {'角色': '菩提祖师众弟子', '内容': '飞起来了！他真的飞起来了！'}, {'角色': '菩提祖师众弟子', '内容': '哎，可是……怎么感觉有点慢吞吞的？'}, {'角色': '旁白', '内容': '飞了不到一小圈，悟空就有些狼狈地落回众人面前，脚下还踉跄了几步。'}, {'角色': '须菩提祖师', '内容': '悟空，你这不叫腾云，顶多算是爬云。离真正的仙家之术，还差得远呢。'}, {'角色': '孙悟空', '内容': '啊？爬云？师父，那要怎样才算腾云？'}, {'角色': '须菩提祖师', '内容': '也罢，看你天性如此，我就传你一招“筋斗云”吧。一个跟头，十万八千里！'}, {'角色': '旁白', '内容': '又过了些时日，悟空不仅练成了筋斗云，七十二变的法术也已烂熟于心。这天，师兄们又围了上来，满脸的好奇和羡慕。'}, {'角色': '菩提祖师众弟子', '内容': '悟空，听说师父把七十二变都传给你了？真的假的？'}, {'角色': '孙悟空', '内容': '嘿嘿，不瞒各位师兄，师父传授的法门，我日夜苦练，都已学会了。'}, {'角色': '菩提祖师众弟子', '内容': '那给我们露一手呗！就变个我们没见过的东西瞧瞧！'}, {'角色': '孙悟空', '内容': '这个……师父告诫过，本事不能随便卖弄。'}, {'角色': '菩提祖师众弟子', '内容': '哎呀，我们都是自家人，怕什么！快变一个，就变一棵松树吧！'}, {'角色': '旁白', '内容': '悟空心里的那点犹豫，瞬间被师兄们的起哄声冲散了。他清了清嗓子，捻动法诀，口中念念有词。'}, {'角色': '孙悟空', '内容': '好！这有何难！你们可看仔细了！'}, {'角色': '菩提祖师众弟子', '内容': '天哪！悟空不见了！地上……地上多了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '连树皮和松针都跟真的一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！真厉害！'}, {'角色': '旁白', '内容': '众人的喝彩声一阵高过一阵，在清静的山谷中回荡。突然，一声严厉的呵斥像冷水一样泼了下来，让所有人都打了个寒颤。'}, {'角色': '须菩提祖师', '内容': '是什么人在此大声喧哗！'}, {'角色': '旁白', '内容': '热闹的场面瞬间凝固。那棵松树也随之变回了孙悟空的模样，他低着头，不敢看师父的眼睛。'}, {'角色': '孙悟空', '内容': '师父……弟子知错了。'}, {'角色': '须菩提祖师', '内容': '悟空，过来！我问你，你为何要卖弄神通，在此哗众取宠？'}, {'角色': '孙悟空', '内容': '我……我只是想让师兄们开开眼界。'}, {'角色': '须菩提祖师', '内容': '糊涂！你的本事越大，引来的麻烦就越大！别人见你有此能耐，若向你求取，你给还是不给？若是不给，人家岂能不加害于你？'}, {'角色': '孙悟空', '内容': '师父，我再也不敢了！求您饶我这一次！'}, {'角色': '须菩提祖师', '内容': '我不能再留你了。你走吧。'}, {'角色': '孙悟空', '内容': '师父！您要赶我走？我……我能去哪儿啊？'}, {'角色': '旁白', '内容': '祖师的语气冰冷，不带一丝商量的余地。'}, {'角色': '须菩提祖师', '内容': '你从哪里来，便回哪里去。但你切记，从今以后，不许对任何人说你是我徒弟。你若说出半个字来，我便将你神魂贬入九幽之地，万劫不得翻身！'}, {'角色': '孙悟空', '内容': '弟子不敢！绝不敢提师父半字，只说是我自己会的！'}, {'类型': '旁白', '内容': '悟空知道再无挽回的余地。他朝祖师重重地磕了三个响头，然后翻身跃起，驾着筋斗云，化作一道金光，消失在了天际。'}]}, {'场景': 8, '场景剧本': [{'角色': '菩提祖师众弟子', '内容': '哇！悟空真的变成了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '天哪，连树皮上的纹路都一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！这本事也太帅了！'}, {'角色': '旁白', '内容': '弟子们的喝彩声在安静的松林里显得格外响亮，打破了午后的宁静，也惊动了正在静修的祖师。'}, {'角色': '须菩提祖师', '内容': '是谁在此喧哗！成何体统！'}, {'角色': '菩提祖师众弟子', '内容': '师父恕罪！是……是孙悟空在演练变化之术，我们一时……'}, {'角色': '须菩提祖师', '内容': '悟空，你过来！'}, {'角色': '旁白', '内容': '祖师话音刚落，那棵挺拔的松树便在一阵微光中迅速变回了孙悟空的原形。他从师兄们中间挤出来，忐忑地低下了头。'}, {'角色': '孙悟空', '内容': '师父……弟子在。'}, {'角色': '须菩提祖师', '内容': '你倒是很得意啊。这点微末道行，就值得你如此卖弄吗？'}, {'角色': '孙悟空', '内容': '弟子不敢……只是师兄们好奇，我才……'}, {'角色': '须菩提祖师', '内容': '住口！我教你本领，是让你护身的，不是让你拿来炫耀的！'}, {'角色': '孙悟空', '内容': '师父，我……'}, {'角色': '须菩提祖师', '内容': '你今天能变棵松树引人喝彩，明天就会有人逼你变条真龙来满足他们的欲望！到那时，你不变，他们便会害你！你变了，麻烦更大！你懂不懂！'}, {'角色': '孙悟空', '内容': '弟子……弟子知错了。'}, {'角色': '须菩提祖师', '内容': '你这性子，留在这里，迟早会给我惹来灭门之祸！'}, {'角色': '孙悟空', '内容': '灭门之祸？师父，没那么严重吧……我以后改就是了！'}, {'角色': '须菩提祖师', '内容': '不必改了。你走吧。'}, {'角色': '旁白', '内容': '“走吧”这两个字像晴天霹雳，悟空脸上的得意瞬间凝固，他完全不敢相信自己的耳朵。'}, {'角色': '孙悟空', '内容': '走？师父……您要赶我走？'}, {'角色': '须菩提祖师', '内容': '从哪里来，回哪里去。'}, {'角色': '孙悟空', '内容': '不要啊师父！我再也不敢了！求您别赶我走！我离家二十年，这里就是我的家啊！'}, {'角色': '旁白', '内容': '悟空还想再求，却看到师父眼中闪过一丝决绝。他知道，这里再也不是他的家了。'}, {'角色': '须菩提祖师', '内容': '你给我听好了！你此去，无论惹出什么滔天大祸，都不许提我是你的师父。'}, {'角色': '孙悟空', '内容': '师父……'}, {'角色': '须菩提祖师', '内容': '你若说出半个字，我便知晓，定将你的神魂贬至九幽之处，让你万劫不得翻身！'}, {'角色': '孙悟空', '内容': '弟子……绝不敢提师父半字。只说……只说是我自己会的。'}, {'角色': '须菩提祖师', '内容': '去吧。'}, {'角色': '旁白', '内容': '悟空再也忍不住泪水，重重地跪了下去，朝着恩师，磕了最后一个响头。'}, {'角色': '孙悟空', '内容': '师父大恩，弟子永世不忘。弟子……给师父磕头了。'}]}]}
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
    script_conflict_escalation_gemini = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '旁白', '内容': '东胜神洲，花果山之巅，一块吸饱了日月精华的仙石轰然迸裂，一个石猴随之诞生。他眼中射出的两道金光，如利剑般划破天际，直冲云霄，瞬间惊动了天庭。'}, {'角色': '千里眼', '内容': '陛下，大事不好了！下方东胜神洲，有一道金光直冲天际，刺得我眼睛都睁不开！'}, {'角色': '顺风耳', '内容': '没错陛下！我也听到了，那金光炸裂之时，声如龙吟，撼天动地！'}, {'角色': '玉皇大帝', '内容': '慌张什么。查明那金光是何物了吗？'}, {'角色': '千里眼', '内容': '回陛下，是花果山顶一块仙石炸裂，蹦出个石猴。那金光，正是从他眼中射出。'}, {'角色': '玉皇大帝', '内容': '呵，原来如此。不过是天地精华所生，不足为奇，由他去吧。'}, {'角色': '旁白', '内容': '天庭之上不过是片刻的议论，凡间却已过去了数年。那石猴早已融入花果山的猴群之中，每日攀岩过涧，嬉戏打闹，享受着无拘无束的快活。'}, {'角色': '花果山众猴', '内容': '快来追我呀！哈哈哈！'}, {'角色': '花果山众猴', '内容': '你们看这瀑布！真想知道这后面藏着什么！'}, {'角色': '花果山众猴', '内容': '别做梦了！这水流能把骨头都冲散架！谁敢靠近谁就是傻子！'}, {'角色': '智慧猿猴', '内容': '话不能这么说！我提议，谁要是有本事，能跳进去再平安出来，查个究竟，我们就拜他为王！'}, {'角色': '花果山众猴', '内容': '为王？说得倒轻巧！这根本就是个不可能完成的赌注，谁敢拿命去换一个空头承诺？'}, {'角色': '孙悟空', '内容': '我敢。'}, {'角色': '花果山众猴', '内容': '（惊愕又嘲讽）你？石猴，别逞能了！这可不是闹着玩的，你会没命的！'}, {'角色': '孙悟空', '内容': '（轻笑一声）我的命，我说了算。你们只管在这里等着，准备好向你们的新大王磕头吧！'}, {'角色': '旁白', '内容': '话音未落，石猴在众猴的惊呼声中，纵身一跃，像一颗出膛的炮弹，瞬间消失在了那道巨大的白色水幕之后。'}, {'角色': '花果山众猴', '内容': '他真的跳了！这个疯子！'}, {'角色': '花果山众猴', '内容': '完了……一点声音都没有了。他肯定被冲走了！'}, {'角色': '智慧猿猴', '内容': '都怪我，我不该出这个主意的……'}, {'角色': '花果山众猴', '内容': '现在说这个有什么用！他回不来了！是你害了他！'}, {'角色': '旁白', '内容': '就在猴群陷入绝望与互相指责时，一个洪亮的声音穿透了震耳的水声，从瀑布后清晰地传了出来。'}, {'角色': '孙悟空', '内容': '喂——！你们这些胆小鬼，快进来！这里面别有洞天啊！'}, {'角色': '花果山众猴', '内容': '是他的声音！他没死！'}, {'角色': '孙悟空', '内容': '这里面根本没有水，是一座铁板桥！桥那边有个大房子！快进来！'}, {'角色': '花果山众猴', '内容': '哇！是真的！这里好大啊！还有石头的桌子和床！'}, {'角色': '孙悟空', '内容': '你们看这石碑上写的！“花果山福地，水帘洞洞天”！从今天起，这里就是我们的家了！再也不怕刮风下雨了！'}, {'角色': '智慧猿猴', '内容': '太好了！我们有家了！等等……你遵守了约定，你就是我们的大王！'}, {'角色': '旁白', '内容': '众猴又惊又喜，想起之前的约定，立刻齐刷刷地跪倒在地，心悦诚服地向这位勇敢的探路者献上最高的敬意。'}, {'角色': '花果山众猴', '内容': '拜见美猴王！'}, {'角色': '孙悟空', '内容': '哈哈哈！好！小的们，都起来吧！'}]}, {'场景': 2, '场景剧本': [{'角色': '花果山众猴', '内容': '大王！再干一杯！这新酿的果子酒，真是甜到心里去了！'}, {'角色': '花果山众猴', '内容': '是啊是啊！我们有吃有喝，自由自在，这日子简直比天上的神仙还快活！'}, {'角色': '旁白', '内容': '水帘洞里，猴子们的欢笑声几乎要掀翻洞顶。然而，就在这片喧闹的中心，美猴王猛地将石杯砸在桌上。砰！——刺耳的声音瞬间压过了所有的欢笑。'}, {'角色': '孙悟空', '内容': '（声音低沉，带着一丝颤抖）你们说……这样的日子，还能有多久？'}, {'角色': '花果山众猴', '内容': '（疑惑地）大王，您这是干什么？好好的宴会，干嘛说这种话？'}, {'角色': '花果山众猴', '内容': '就是啊，大王！别想那么多了！今天开心最重要！明天的事，明天再说嘛！'}, {'角色': '孙悟空', '内容': '（猛地站起来，声音激愤）明天？要是没有明天了呢！你们就没想过，有一天我们会老得跳不动，牙齿掉光，连最甜的果子都啃不动吗？'}, {'角色': '孙悟空', '内容': '到那个时候，我们都会死！再也看不到这花果山，再也喝不到这果子酒，我们……就再也见不到了！懂吗！'}, {'角色': '旁白', '内容': '“死”这个字像一块冰冷的石头，砸碎了宴会的欢乐气氛。刚才还吵着要再干一杯的猴子们，现在一个个都捂着脸，洞里只剩下压抑的哭泣声。'}, {'角色': '花果山众猴', '内容': '我不要变老……我不要死……呜呜呜……'}, {'角色': '旁白', '内容': '就在一片愁云惨雾中，一只毛发灰白的智慧猿猴排开众猴，高声喊道。'}, {'角色': '智慧猿猴', '内容': '大王！哭是没用的！'}, {'角色': '孙悟空', '内容': '（抬起头，眼中尚有泪光）那你说怎么办？难道你有办法让我们永远留在这里？'}, {'角色': '智慧猿猴', '内容': '我没有，但有人有！我听老猴王说过，这世上有一种存在，能与天地同寿，永远年轻！他们就是传说中的仙人！'}, {'角色': '孙悟空', '内容': '（一把抓住智慧猿猴的肩膀，眼中爆发出光芒）仙人？！这是真的吗？他们在哪里？快告诉我！'}, {'角色': '智慧猿猴', '内容': '他们就隐居在人间的名山大川，洞天福地之中！'}, {'角色': '旁白', '内容': '“仙人”这两个字仿佛一道闪电，瞬间劈开了美猴王心中的所有阴霾。他松开智慧猿猴，刚才的忧伤一扫而空，取而代之的是一种燃烧般的决心。'}, {'角色': '孙悟空', '内容': '（对着所有猴子大喊）都别哭了！我决定了！我明天就下山，就算走遍天涯海角，也要拜师学艺，把长生不老的方法给你们带回来！'}, {'角色': '花果山众猴', '内容': '太好了！大王威武！'}, {'角色': '花果山众猴', '内容': '我们等大王回来！我们去准备最好的果子，为大王送行！'}]}, {'场景': 3, '场景剧本': [{'角色': '旁白', '内容': '美猴王告别故土，驾着一叶木筏，漂向了茫茫大海。风暴、烈日、迷茫、孤独……十年光阴，转瞬即逝。'}, {'角色': '孙悟空', '内容': '（内心，疲惫又坚定）十年了……传说中的神仙，到底在哪儿？！我绝不放弃！一定要找到长生不老的方法！'}, {'角色': '旁白', '内容': '就在他几乎绝望之际，一阵悠扬的歌声穿透森林，飘入耳中。'}, {'角色': '樵夫', '内容': '（歌声）观棋柯烂，伐木丁丁，云边谷口徐行……相逢处非仙即道，静坐讲黄庭。'}, {'角色': '孙悟空', '内容': '（内心，狂喜）这歌！没错！是仙气！'}, {'角色': '旁白', '内容': '他精神大振，循声而去，拨开最后的枝叶，却只看到一个砍柴的樵夫。'}, {'角色': '孙悟空', '内容': '（大喝一声，冲上前）站住！你就是那个神仙吧！'}, {'角色': '樵夫', '内容': '（吓了一跳，连连后退）啊！你、你这猴子打哪儿来的？别胡说！我就是个砍柴的，你可别吓我！'}, {'角色': '孙悟空', '内容': '（步步紧逼，语气尖锐）还敢骗我？我为了寻仙访道，在海上漂了整整十年！你唱的歌，句句不离仙道，你还敢说你不是？'}, {'角色': '樵夫', '内容': '（急忙摆手）哎呀，你真的误会了！那歌是住在那山里的一位真神仙教我的，让我烦恼的时候唱着解闷儿用的！我真不是啊！'}, {'角色': '孙悟空', '内容': '（停下脚步，怀疑地）真有神仙？那他为什么不教你长生不老？你还在这里砍柴受苦？'}, {'角色': '樵夫', '内容': '（叹了口气，语气变得淳朴而坚定）长生不老，哪有我娘重要？家里老母亲还等我砍柴换米，我一天都走不开啊。'}, {'角色': '孙悟空', '内容': '（愣住了）……你娘？'}, {'角色': '孙悟空', '内容': '（语气缓和下来，带着一丝敬佩）原来……你是个孝子。是我太心急，错怪你了。'}, {'角色': '樵夫', '内容': '（憨厚地笑了笑）没事没事。那你快告诉我，那位神仙究竟住在哪里？'}, {'角色': '旁白', '内容': '樵夫放下斧头，用手指了指远处一座云雾缭绕的高山。'}, {'角色': '樵夫', '内容': '你瞧，那座山叫灵台方寸山。山里有个斜月三星洞，洞里住着一位须菩提祖师。你顺着这条小路一直往南走，就到了。'}, {'角色': '孙悟空', '内容': '（眼神发亮）灵台方寸山，斜月三星洞，须菩提祖师！'}, {'角色': '孙悟空', '内容': '（深深一躬）多谢指点！大恩不言谢，我走啦！'}, {'角色': '旁白', '内容': '话音未落，猴王已化作一道影子，迫不及待地向着那条小路冲去，将樵夫的叮嘱声远远甩在了身后。'}]}, {'场景': 4, '场景剧本': [{'角色': '旁白', '内容': '独自漂洋过海，又在大陆上寻觅了近十年，孙悟空几乎就要放弃希望。这天，他在深山里穿行，一阵悠扬的歌声忽然飘入耳中。他循声拨开树丛，看到一个樵夫正一边砍柴，一边放声高歌。'}, {'角色': '孙悟空', '内容': '（激动地）老神仙！请留步！'}, {'角色': '樵夫', '内容': '（停下斧子，回头）嗯？你这野猴，是在叫我吗？我可不是什么神仙。'}, {'角色': '孙悟空', '内容': '可你唱的歌，句句都是神仙的道理！你别骗我，你肯定就是！'}, {'角色': '樵夫', '内容': '（笑了）你这猴子真会认错人。那歌是山里一位真神仙教我的，我就是个砍柴的，闲着没事唱着解乏罢了。'}, {'角色': '孙悟空', '内容': '（眼睛一亮）真神仙？那……你为什么不跟他学长生不老？这么好的机会！'}, {'角色': '樵夫', '内容': '（叹了口气）唉，我家里还有老母亲要照顾，哪有那个清闲功夫。我凡尘俗事太多，没法学。'}, {'角色': '孙悟空', '内容': '（急切地）你不能学，我可以啊！求求你告诉我，那位神仙住在哪里？我找了他整整十年！'}, {'角色': '樵夫', '内容': '看你这么诚心，就告诉你吧。沿着这条小路往南走，那座最高的山叫灵台方寸山，山里有个斜月三星洞，神仙就住在那儿。'}, {'角色': '孙悟空', '内容': '灵台方寸山……斜月三星洞……多谢！多谢大哥指路！'}, {'角色': '旁白', '内容': '孙悟空告别樵夫，心中燃起从未有过的激动。他沿着小路，翻山越岭，终于在云雾缭绕的山顶，看到了一座洞府。洞府前，一块石碑上赫然刻着十个大字：灵台方寸山，斜月三星洞。'}, {'角色': '孙悟空', '内容': '（喘着粗气，声音颤抖）啊……真不愧是神仙住的地方，感觉空气都是甜的！就是这里！绝对就是这里！'}, {'角色': '旁白', '内容': '他兴奋地冲上前，却发现洞门紧闭。他等了又等，从中午等到日落，洞门依然纹丝不动。希望的火焰，似乎又在一点点熄灭。'}, {'角色': '孙悟空', '内容': '（焦躁地自言自语）难道……又找错了？还是神仙根本就不想见我？不！我不能就这么放弃！喂！有人吗？我是诚心来拜师学艺的！'}, {'角色': '须菩提祖师', '内容': '（声音从门内传来，平静而威严）童儿，开门吧。外面那个修行的，已经等得够久了。'}, {'角色': '旁白', '内容': '话音刚落，厚重的石门吱呀一声向内打开。一个眉清目秀的小仙童走了出来，一脸不耐烦地上下打量着孙悟空。'}, {'角色': '仙童', '内容': '（质问）就是你在外面大喊大叫？知不知道这里是什么地方？'}, {'角色': '孙悟空', '内容': '（连忙作揖）小仙童！是我，是我！我不是故意的，我……我只是太想见到神仙师父了！'}, {'角色': '仙童', '内容': '（怀疑地）就你？一只毛还没长齐的野猴，也配来这里修行？'}, {'角色': '孙悟空', '内容': '（挺起胸膛）你别小看我！我漂洋过海，吃了无数苦头才找到这里！我的心是最诚的！'}, {'角色': '仙童', '内容': '（冷哼一声）心诚不诚，不是靠嘴说的。我家师父刚刚正在讲道，忽然停下，点名说外面有个修行的到了，让我来接你。'}, {'角色': '孙悟空', '内容': '（又惊又喜）什么？师父还没见到我，就知道我来了？他说的就是我！'}, {'角色': '仙童', '内容': '（翻了个白眼）不然呢？师父的本事，岂是你能想象的。算你运气好。跟我进来吧，记得收起你的野性，别乱碰乱闯！'}]}, {'场景': 5, '场景剧本': [{'角色': '仙童', '内容': '师父，那个求道的猴子，已在殿外等候多时了。'}, {'角色': '须菩提祖师', '内容': '让他进来。'}, {'角色': '旁白', '内容': '石猴跟着仙童穿过层层殿宇，终于见到那位传说中的神仙。他来不及多想，双膝跪地，声音带着旅途的沙哑和压抑不住的激动。'}, {'角色': '孙悟空', '内容': '神仙！我……我终于找到您了！我找了您十几年，求您，收下我吧！'}, {'角色': '须菩提祖师', '内容': '(声音平静，却带着一股看透一切的威严) 起来。我这里不收来历不明的弟子。说吧，你是什么东西？从哪儿来？'}, {'角色': '孙悟空', '内容': '(猛地抬头) 我…我不是东西！我来自东胜神洲花果山，是一只石猴！'}, {'角色': '须菩提祖师', '内容': '(轻哼一声) 花果山？那与我这里隔着两重大海，一片大陆。你倒是说说，你是怎么来的？别是撒谎骗我吧。'}, {'角色': '孙悟空', '内容': '(急切地) 我没有撒谎！我坐着木筏，在海上漂了几年，又在陆地上走了好多年，吃了无数的苦……就是为了找到神仙，学长生不老之术！'}, {'角色': '旁白', '内容': '祖师的目光锐利如剑，似乎要刺穿这猴子的灵魂，看清他十年旅途的真伪。'}, {'角色': '须菩提祖师', '内容': '十年……哼，毅力可嘉。但想入我门下，光有毅力可不够。你连个名字都没有，我如何收你？'}, {'角色': '孙悟空', '内容': '(声音瞬间低落，充满委屈) 我…我是从石头里蹦出来的，没有父母，自然也没有姓名……'}, {'角色': '须菩提祖师', '内容': '天生地养，倒也有趣。也罢，既然你没有姓名，我就给你一个。你且走两步我看看。'}, {'角色': '音效', '内容': '猴子在殿内蹦跳、挠腮的轻快脚步声。'}, {'角色': '须菩提祖师', '内容': '(露出一丝微笑) 呵呵，你这形态，像个猢狲。猢狲去了兽旁，是个“孙”字。从今天起，你就姓“孙”。'}, {'角色': '旁白', '内容': '这一个“孙”字，像一道光，瞬间照亮了石猴混沌的世界。他不再只是一个来自花果山的野猴，他有了归属，有了身份的第一个笔画。'}, {'角色': '孙悟空', '内容': '(难以置信地重复，声音颤抖) 姓……孙？我姓孙了？我……我有姓了！(激动地磕头) 谢谢师父！谢谢师父赐姓！'}, {'角色': '须菩提祖师', '内容': '别急着谢。我门下弟子，皆是“悟”字辈。我再赐你法名，‘悟空’。'}, {'角色': '孙悟空', '内容': '孙……悟空？(抬起头，眼神里充满渴望) 师父，这个名字是什么意思？'}, {'角色': '须菩提祖师', '内容': '名为‘悟空’，是希望你未来能领悟真正的道理，不被世间表象所迷惑。你，能做到吗？'}, {'角色': '孙悟空', '内容': '(用力点头，眼神无比坚定) 领悟真理，不被迷惑！弟子明白了！我叫孙悟空！我就是孙悟空！'}, {'角色': '旁白', '内容': '他站起身，一遍遍念着这个属于自己的名字。声音从最初的试探，变得越来越响亮，越来越坚定。从这一刻起，那个无名的石猴，真正成为了孙悟空。'}, {'角色': '须菩提祖师', '内容': '好。孙悟空，从今日起，你便是我灵台方寸山，斜月三星洞的弟子了。'}, {'角色': '孙悟空', '内容': '(声音洪亮，充满力量) 弟子孙悟空，拜见师父！'}]}, {'场景': 6, '场景剧本': [{'角色': '须菩提祖师', '内容': '悟空，既然拜我为师，我便传你道法。这“术”字门，可请仙问卜，趋吉避凶。学不学？'}, {'角色': '孙悟空', '内容': '（毫不犹豫）能长生吗？'}, {'角色': '须菩提祖师', '内容': '不能。'}, {'角色': '孙悟空', '内容': '不学！下一个！'}, {'角色': '须菩提祖师', '内容': '（挑了挑眉）好。那“静”字门，可让你入定坐关，宁心静气。这个如何？'}, {'角色': '孙悟空', '内容': '师父，别绕弯子了。它，能长生吗？'}, {'角色': '须菩提祖师', '内容': '……不能。'}, {'角色': '孙悟空', '内容': '不学！不学！'}, {'角色': '须菩提祖师', '内容': '（强压怒火）那这“动”字门，采阴补阳，服食丹药，总该学了吧！'}, {'角色': '孙悟空', '内容': '听起来不错，但我就问一句，这是不是像水里的月亮，看得见摸不着？能让我真正跳出轮回吗？'}, {'角色': '须菩提祖师', '内容': '（叹气）镜花水月而已。'}, {'角色': '孙悟空', '内容': "那还是不学！我要学，就学一个能跟阎王爷说'不'的真本事！这些虚头巴脑的，我没兴趣！"}, {'角色': '旁白', '内容': '悟空这番毫不留情的拒绝，彻底点燃了祖师的怒火。他从高台上一跃而下，手持戒尺，怒视悟空。'}, {'角色': '须菩提祖师', '内容': '（厉声）你这泼猴！这也不学，那也不学，是存心来消遣我的吗！'}, {'角色': '旁白', '内容': '祖师举起戒尺，在悟空头上不轻不重地敲了三下，随即转身，背着双手，径直走入内堂，砰地一声关上了正门，留下满堂错愕的弟子。'}, {'角色': '菩提祖师众弟子', '内容': '（惊慌）完了完了，这猴子把师父气走了！'}, {'角色': '菩提祖师众弟子', '内容': '（愤怒地指着悟空）都是你！你这不知天高地厚的家伙，还不快跪下谢罪！'}, {'角色': '孙悟空', '内容': '（非但不怕，反而嘴角上扬，露出一丝微笑）'}, {'角色': '菩提祖师众弟子', '内容': '（难以置信）你还笑得出来？你是不是傻了？师父这是在惩罚你！'}, {'角色': '孙悟空', '内容': '（摇了摇手指）惩罚？你们根本没看懂。这明明是师父给我的“提问”。'}, {'角色': '菩提祖师众弟子', '内容': '提问？胡说八道什么！师父都气成那样了！'}, {'角色': '孙悟空', '内容': '（胸有成竹）你们看，师父打我三下，就是在问我：敢不敢三更天来？'}, {'角色': '菩提祖师众弟子', '内容': '简直是疯了！'}, {'角色': '孙悟空', '内容': '他背着手走，关上中门，就是在告诉我：别走大路，从后门进来。你们说，这不是要私下传我真本事，又是什么？'}, {'角色': '菩提祖师众弟子', '内容': '（嘲笑）真是异想天开！我看你是挨打挨昏了头！等着吧，明天师父第一个就要把你赶出山门！'}, {'角色': '孙悟空', '内容': '（耸耸肩，一脸轻松）那咱们就等着瞧。各位师兄，我先去休息了，你们慢慢“悟”吧。'}]}, {'场景': 7, '场景剧本': [{'角色': '旁白', '内容': '几天后的课后，三星洞外的松树下，师兄们把悟空团团围住。'}, {'角色': '菩提祖师众弟子', '内容': '悟空，别光说不练啊，师父教你的腾云术，你到底行不行？'}, {'角色': '孙悟空', '内容': '（得意地）小菜一碟！看我给你们露一手！'}, {'角色': '旁白', '内容': '话音未落，悟空双脚猛地一蹬，身体晃晃悠悠地飞了起来，但速度慢得像散步，飞了一圈就踉踉跄跄地落了地。'}, {'角色': '菩提祖师众弟子', '内容': '（哄笑）哈哈哈，悟空，你这是飞呢，还是在天上爬呢？'}, {'角色': '须菩提祖师', '内容': '（声音突然出现）他说得没错，你这顶多算是“爬云”，算不得真正的腾云。'}, {'角色': '孙悟空', '内容': '（脸一红）师父！那……那要怎样才算腾云？这也太难了！'}, {'角色': '须菩提祖师', '内容': '罢了。看你天生好动，我便传你一招“筋斗云”。一个跟头，十万八千里，学不学？'}, {'角色': '孙悟空', '内容': '（立刻兴奋）学！我学！'}, {'角色': '旁白', '内容': '又过了些时日，悟空不仅练成了筋斗云，七十二变也已烂熟于心。他那颗爱炫耀的心，又开始蠢蠢欲动。'}, {'角色': '菩提祖师众弟子', '内容': '喂，悟空，听说你把七十二变都学会了，真的假的？别是吹牛吧？'}, {'角色': '孙悟空', '内容': '（清了清嗓子）嘿嘿，师父教的本事，我哪样没学会？'}, {'角色': '菩提祖师众弟子', '内容': '那你倒是变一个给我们看看啊！光说谁不会？'}, {'角色': '孙悟空', '内容': '（犹豫）这……师父警告过，本事不能随便拿来炫耀。'}, {'角色': '菩提祖师众弟子', '内容': '怕什么！师父又不在！就我们自己人看看，谁会说出去？你要是真有本事，现在就变一个！'}, {'角色': '菩提祖师众弟子', '内容': '对！就变棵松树，让我们开开眼！'}, {'角色': '孙悟空', '内容': '（被激起好胜心）好！这有何难！你们可站远点，看仔细了！'}, {'角色': '旁白', '内容': '悟空捻动法诀，口中念念有词，身子一晃，只听“噗”的一声轻响，原地瞬间出现一棵挺拔的松树。'}, {'角色': '菩提祖师众弟子', '内容': '（惊呼）快看！悟空不见了，地上真的多了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '（上前触摸）我的天，连树皮和松针都跟真的一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！真厉害！'}, {'角色': '须菩提祖师', '内容': '（声音如雷霆般响起）吵吵嚷嚷的，成何体统！'}, {'角色': '旁白', '内容': '喝彩声戛然而止。松树瞬间变回孙悟空，他吓得一哆嗦，低着头站在原地。'}, {'角色': '须菩提祖师', '内容': '孙悟空！你把我的话当耳旁风了？我教你本事，是让你拿来当杂耍炫耀的吗！'}, {'角色': '孙悟空', '内容': '（急忙辩解）不是的师父！是师兄们非要我变的，我只是……'}, {'角色': '须菩提祖师', '内容': '（严厉打断）住口！他们让你变你就变？学了点皮毛就到处张扬，你知不知道卖弄神通会给你招来杀身之祸！'}, {'角色': '孙悟空', '内容': '（慌了神）师父，弟子真的知错了！我再也不敢了！求您饶我这一次吧！'}, {'角色': '须菩提祖师', '内容': '（语气冰冷）这里，留你不得。你走吧。'}, {'角色': '孙悟空', '内容': '（震惊）师父！您要赶我走？我……我还能去哪儿啊？'}, {'角色': '须菩提祖师', '内容': '从哪儿来，回哪儿去！但你给我记死了：从今以后，不准对任何人说你是我徒弟。敢说出半个字，我便让你神魂俱灭，永世不得超生！听明白了吗？'}, {'角色': '孙悟空', '内容': '（含泪叩首）明白了！弟子明白了！绝不提师父半个字，就说……就说都是我自己天生就会的！'}, {'角色': '旁白', '内容': '悟空知道再无挽回的余地。他朝祖师重重地磕了三个响头，然后翻身跃起，驾着筋斗云，化作一道金光，消失在了天际。'}]}, {'场景': 8, '场景剧本': [{'角色': '菩提祖师众弟子', '内容': '哇！悟空真的变成了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '太神了！连树皮的纹路都一模一样！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！这本事也太帅了！'}, {'角色': '旁白', '内容': '弟子们的喝彩声在安静的松林里显得格外响亮，打破了午后的宁静，也惊动了正在静修的祖师。'}, {'角色': '须菩提祖师', '内容': '(严厉地) 孙悟空！你在做什么！'}, {'角色': '旁白', '内容': '祖师的声音如洪钟般传来，众人瞬间噤声。那棵松树在一阵微光中变回了孙悟空的原形，他从师兄们中间挤出来，忐忑地低下了头。'}, {'角色': '孙悟空', '内容': '师父……弟子在和师兄们切磋法术。'}, {'角色': '须菩提祖师', '内容': '切磋？我怎么看着像是在卖弄？孙悟空，你是不是觉得，学了点皮毛，就天下无敌了？'}, {'角色': '孙悟空', '内容': '(急忙辩解) 弟子不敢！我只是…想让大家看看七十二变的奇妙，这有什么不对吗？'}, {'角色': '须菩提祖师', '内容': '(痛心疾首) 有什么不对？错就错在你这颗炫耀的心！悟空！我教你本领，是让你护身的，不是让你拿来当戏法耍给别人看的！'}, {'角色': '孙悟空', '内容': '师父，我……'}, {'角色': '须菩提祖师', '内容': '你今天能变松树引人喝彩，明天就会有人逼你变条龙来满足他们的欲望！到那时，你不给，他们便会害你！你给了，麻烦更大！你这性子，留在这里，迟早会给我惹来灭门之祸！'}, {'角色': '孙悟空', '内容': '(震惊) 灭门之祸？师父，您言重了！我改！我以后再也不敢了！'}, {'角色': '须菩提祖师', '内容': '(语气决绝) 晚了。不必改了。你走吧。'}, {'角色': '旁白', '内容': '“你走吧”三个字像晴天霹雳，悟空脸上的血色瞬间褪尽，他完全不敢相信自己的耳朵。'}, {'角色': '孙悟空', '内容': '走？去哪儿？师父，您不能赶我走！我错了，我真的知道错了！求您再给我一次机会！'}, {'角色': '须菩提祖师', '内容': '从哪里来，回哪里去。'}, {'角色': '孙悟空', '内容': '(带着哭腔) 不要啊师父！我离家二十年，这里就是我的家啊！您不要我，我就没家了！'}, {'角色': '须菩提祖师', '内容': '住口！你给我听好了！你此去，无论惹出什么滔天大祸，都不许提我是你的师父。'}, {'角色': '孙悟空', '内容': '(哽咽) 师父……为什么……'}, {'角色': '须菩提祖师', '内容': '(一字一顿，不容置疑) 你若敢说出半个字，我便知晓，定将你的神魂贬至九幽之处，让你万劫不得翻身！听清楚了吗！'}, {'角色': '孙悟空', '内容': '(浑身一颤，彻底绝望) 弟子……听清楚了。弟子绝不敢提师父半字……只说，是我自己会的。'}, {'角色': '须菩提祖师', '内容': '(闭上眼，轻声但坚定地) 去吧。'}, {'角色': '旁白', '内容': '悟空再也忍不住泪水，他知道一切已无法挽回。他重重地跪了下去，朝着恩师，磕了最后一个响头。'}, {'角色': '孙悟空', '内容': '(含泪) 师父大恩，弟子永世不忘。弟子……给师父磕头了。'}]}]}
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
    script_proofreader = {'剧本审查': [{'场景': 1, '审查结果': '需修改', '问题清单': [{'维度': '角色一致性', '问题描述': '在剧本的角色列表中，石猴在被菩提祖师赐名之前，就被标记为“孙悟空”。这在故事时间线上是不正确的。此时，他只是“石猴”，在本场景结尾时成为“美猴王”。提前使用“孙悟空”这个名字会造成剧情逻辑上的混乱。', '修改建议': '请将本场景中所有的角色标签“孙悟空”修改为“石猴”。在最后一个对话之后，可以考虑将其角色标签更新为“美猴王”，以反映其身份的变化。保留“孙悟空”这个名字，直到他去拜师学艺的场景再使用。'}]}, {'场景': 2, '审查结果': '通过', '问题清单': []}, {'场景': 3, '审查结果': '需修改', '问题清单': [{'维度': '角色一致性', '问题描述': '在剧本的第15条对话中，樵夫的角色出现了逻辑错误。在他向孙悟空解释完自己为何不求仙道后，他反过来问孙悟空：‘那你快告诉我，那位神仙究竟住在哪里？’，但这应该是孙悟空迫切想问樵夫的问题，不符合樵夫此时的角色立场和动机。', '修改建议': '将第15条对话的说话人由“樵夫”改为“孙悟空”。为使对话更自然，建议将第15条拆分为两条：樵夫先回应孙悟空的道歉，如 ‘（憨厚地笑了笑）没事没事。’；然后孙悟空立刻追问：‘那你快告诉我，那位神仙究竟住在哪里？’'}]}, {'场景': 4, '审查结果': '需修改', '问题清单': [{'维度': '角色一致性', '问题描述': '仙童与樵夫对孙悟空的称呼均为“野猴”，这存在轻微的重复性，削弱了仙童作为“神仙弟子”的独特优越感。他的傲慢应该与凡人樵夫的直接观感有所区别。', '修改建议': '建议修改仙童的台词，将“野猴”替换为更能体现其身份和语气的词。例如，可以改为：“（怀疑地）就你？一只毛还没长齐的猢狲，也配来这里修行？”或者“哪来的山精野怪，在此喧哗？”这样既能保留轻蔑的态度，又能使角色语言更具个性化。'}, {'维度': '受众适宜性', '问题描述': '仙童的角色塑造略显单薄，从头到尾都是不耐烦和鄙夷，虽然符合“看门人”的设定，但缺乏层次感。尤其是他传达祖师命令时，情绪没有变化。', '修改建议': '在仙童传达祖师命令时，建议增加一丝情绪变化。例如，可以在台词前加入一个表示惊讶或不解的语气词。修改为：“（冷哼一声）心诚不诚，不是靠嘴说的。……嗯？我家师父刚刚正在讲道，竟忽然停下，点名说外面有个修行的到了，让我来接你。”这个微小的停顿和转折，能表现出他对师父“未卜先知”能力的敬畏，从而让这个角色更立体，也侧面烘托了祖师的强大。'}]}, {'场景': 5, '审查结果': '需修改', '问题清单': [{'维度': '信息平衡', '问题描述': '旁白部分存在过度解释的问题，尤其是在赐姓、赐名环节。例如，旁白直接告诉听众“这一个‘孙’字，像一道光，瞬间照亮了石猴混沌的世界”以及“从这一刻起，那个无名的石猴，真正成为了孙悟空”，这种“讲述”代替了“展示”，削弱了孙悟空自身表演和台词所能带来的情感冲击力，没有给青少年听众留下足够的情感想象和共鸣空间。', '修改建议': '建议精简或删除直接解释角色内心感受和事件意义的旁白。信任演员的表演和听众的理解力。可以将这部分内容转化为动作或台词来表现。例如：\n1. 删除“这一个‘孙’字，像一道光……”的旁白，让孙悟空在念出“我姓孙了？”这句台词时，通过语气从难以置信到狂喜的转变来传递这种震撼感。\n2. 将结尾的旁白“他站起身，一遍遍念着这个属于自己的名字……”改为由孙悟空自己来演绎，例如让他低声重复自己的新名字，声音由小到大，由试探到坚定，最后化为一声充满力量的宣告：“我就是孙悟空！”，这样更具沉浸感和戏剧张力。'}, {'维度': '角色一致性', '问题描述': '须菩提祖师的台词“你是什么东西？从哪儿来？”略显粗鲁，与之后赐名的宗师风范稍有出入。虽然原著有类似表达，但对于声音剧，这种直接的质问可能会让角色显得不够沉稳。', '修改建议': '建议将“你是什么东西？”调整为更符合宗师身份的问话，同时保持其探究本质的意图。例如，可以改为：“报上你的根脚来历。”或者更温和一些的：“你非人非妖，究竟是何来历？”这样既能引出石猴的身世，也更符合世外高人的形象。'}]}, {'场景': 6, '审查结果': '需修改', '问题清单': [{'维度': '角色一致性', '问题描述': '孙悟空当众向其他弟子解释祖师的“哑谜”。这种处理方式虽然直接，但让悟空显得有些炫耀，削弱了师徒之间心照不宣的默契感。一个真正悟性高的角色，在领会了秘密后，通常会选择保密而非公开解释。', '修改建议': '将悟空解释哑谜的对话改为内心独白。例如，当其他弟子嘲笑他时，悟空可以只报以神秘的微笑，然后通过旁白或内心独白的形式告诉听众他的分析：“（内心，胸有成竹）你们才不懂呢。师父打我三下，是让我三更时分去寻他；他背手走入内堂，关上中门，是示意我从后门进去。这哪里是惩罚，分明是要私下传我真本事！” 这样既能展现悟空的聪慧，又能保留师徒间独特的、秘密的联结，增加戏剧张力。'}, {'维度': '受众适宜性', '问题描述': '剧本中“菩提祖师众弟子”的所有台词都作为一个整体出现，这在实际音频制作中听起来会像一群人在齐声说话，效果可能不自然，难以分辨情绪层次。', '修改建议': '将“菩提祖师众弟子”的台词分配给两到三个具体的角色，如“弟子甲”、“弟子乙”。例如，将“完了完了，这猴子把师父气走了！”和“都是你！你这不知天高地厚的家伙...”分配给不同的弟子，可以制造出七嘴八舌、情绪各异的真实感，让场景听起来更生动。'}, {'维度': '信息平衡', '问题描述': '孙悟空最后一句台词“你们慢慢‘悟’吧”略显说教，且直接点破了主题，缺少一些含蓄的趣味性。', '修改建议': '可以考虑换一种更符合悟空顽皮、自信性格的表达方式。例如，在弟子们嘲笑他会被赶走时，他可以轻松地回应：“那咱们就等着瞧。各位师兄早点歇着，我得养足精神，晚上还有事儿呢。” 这句台词既保留了悬念，又通过“有事儿”暗示了他对师父意图的把握，显得更加自然和机智。'}]}, {'场景': 7, '审查结果': '通过', '问题清单': []}, {'场景': 8, '审查结果': '通过', '问题清单': []}]}

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

    refine_script = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '旁白', '内容': '东胜神洲，花果山之巅，一块吸饱了日月精华的仙石轰然迸裂，一个石猴随之诞生。他眼中射出的两道金光，如利剑般划破天际，直冲云霄，瞬间惊动了天庭。'}, {'角色': '千里眼', '内容': '陛下，大事不好了！下方东胜神洲，有一道金光直冲天际，刺得我眼睛都睁不开！'}, {'角色': '顺风耳', '内容': '没错陛下！我也听到了，那金光炸裂之时，声如龙吟，撼天动地！'}, {'角色': '玉皇大帝', '内容': '慌张什么。查明那金光是何物了吗？'}, {'角色': '千里眼', '内容': '回陛下，是花果山顶一块仙石炸裂，蹦出个石猴。那金光，正是从他眼中射出。'}, {'角色': '玉皇大帝', '内容': '呵，原来如此。不过是天地精华所生，不足为奇，由他去吧。'}, {'角色': '旁白', '内容': '天庭之上不过是片刻的议论，凡间却已过去了数年。那石猴早已融入花果山的猴群之中，每日攀岩过涧，嬉戏打闹，享受着无拘无束的快活。'}, {'角色': '花果山众猴', '内容': '快来追我呀！哈哈哈！'}, {'角色': '花果山众猴', '内容': '你们看这瀑布！真想知道这后面藏着什么！'}, {'角色': '花果山众猴', '内容': '别做梦了！这水流能把骨头都冲散架！谁敢靠近谁就是傻子！'}, {'角色': '智慧猿猴', '内容': '话不能这么说！我提议，谁要是有本事，能跳进去再平安出来，查个究竟，我们就拜他为王！'}, {'角色': '花果山众猴', '内容': '为王？说得倒轻巧！这根本就是个不可能完成的赌注，谁敢拿命去换一个空头承诺？'}, {'角色': '石猴', '内容': '我敢。'}, {'角色': '花果山众猴', '内容': '（惊愕又嘲讽）你？石猴，别逞能了！这可不是闹着玩的，你会没命的！'}, {'角色': '石猴', '内容': '（轻笑一声）我的命，我说了算。你们只管在这里等着，准备好向你们的新大王磕头吧！'}, {'角色': '旁白', '内容': '话音未落，石猴在众猴的惊呼声中，纵身一跃，像一颗出膛的炮弹，瞬间消失在了那道巨大的白色水幕之后。'}, {'角色': '花果山众猴', '内容': '他真的跳了！这个疯子！'}, {'角色': '花果山众猴', '内容': '完了……一点声音都没有了。他肯定被冲走了！'}, {'角色': '智慧猿猴', '内容': '都怪我，我不该出这个主意的……'}, {'角色': '花果山众猴', '内容': '现在说这个有什么用！他回不来了！是你害了他！'}, {'角色': '旁白', '内容': '就在猴群陷入绝望与互相指责时，一个洪亮的声音穿透了震耳的水声，从瀑布后清晰地传了出来。'}, {'角色': '石猴', '内容': '喂——！你们这些胆小鬼，快进来！这里面别有洞天啊！'}, {'角色': '花果山众猴', '内容': '是他的声音！他没死！'}, {'角色': '石猴', '内容': '这里面根本没有水，是一座铁板桥！桥那边有个大房子！快进来！'}, {'角色': '花果山众猴', '内容': '哇！是真的！这里好大啊！还有石头的桌子和床！'}, {'角色': '石猴', '内容': '你们看这石碑上写的！“花果山福地，水帘洞洞天”！从今天起，这里就是我们的家了！再也不怕刮风下雨了！'}, {'角色': '智慧猿猴', '内容': '太好了！我们有家了！等等……你遵守了约定，你就是我们的大王！'}, {'角色': '旁白', '内容': '众猴又惊又喜，想起之前的约定，立刻齐刷刷地跪倒在地，心悦诚服地向这位勇敢的探路者献上最高的敬意。'}, {'角色': '花果山众猴', '内容': '拜见美猴王！'}, {'角色': '美猴王', '内容': '哈哈哈！好！小的们，都起来吧！'}]}, {'场景': 2, '场景剧本': [{'角色': '花果山众猴', '内容': '大王！再干一杯！这新酿的果子酒，真是甜到心里去了！'}, {'角色': '花果山众猴', '内容': '是啊是啊！我们有吃有喝，自由自在，这日子简直比天上的神仙还快活！'}, {'角色': '旁白', '内容': '水帘洞里，猴子们的欢笑声几乎要掀翻洞顶。然而，就在这片喧闹的中心，美猴王猛地将石杯砸在桌上。砰！——刺耳的声音瞬间压过了所有的欢笑。'}, {'角色': '孙悟空', '内容': '（声音低沉，带着一丝颤抖）你们说……这样的日子，还能有多久？'}, {'角色': '花果山众猴', '内容': '（疑惑地）大王，您这是干什么？好好的宴会，干嘛说这种话？'}, {'角色': '花果山众猴', '内容': '就是啊，大王！别想那么多了！今天开心最重要！明天的事，明天再说嘛！'}, {'角色': '孙悟空', '内容': '（猛地站起来，声音激愤）明天？要是没有明天了呢！你们就没想过，有一天我们会老得跳不动，牙齿掉光，连最甜的果子都啃不动吗？'}, {'角色': '孙悟空', '内容': '到那个时候，我们都会死！再也看不到这花果山，再也喝不到这果子酒，我们……就再也见不到了！懂吗！'}, {'角色': '旁白', '内容': '“死”这个字像一块冰冷的石头，砸碎了宴会的欢乐气氛。刚才还吵着要再干一杯的猴子们，现在一个个都捂着脸，洞里只剩下压抑的哭泣声。'}, {'角色': '花果山众猴', '内容': '我不要变老……我不要死……呜呜呜……'}, {'角色': '旁白', '内容': '就在一片愁云惨雾中，一只毛发灰白的智慧猿猴排开众猴，高声喊道。'}, {'角色': '智慧猿猴', '内容': '大王！哭是没用的！'}, {'角色': '孙悟空', '内容': '（抬起头，眼中尚有泪光）那你说怎么办？难道你有办法让我们永远留在这里？'}, {'角色': '智慧猿猴', '内容': '我没有，但有人有！我听老猴王说过，这世上有一种存在，能与天地同寿，永远年轻！他们就是传说中的仙人！'}, {'角色': '孙悟空', '内容': '（一把抓住智慧猿猴的肩膀，眼中爆发出光芒）仙人？！这是真的吗？他们在哪里？快告诉我！'}, {'角色': '智慧猿猴', '内容': '他们就隐居在人间的名山大川，洞天福地之中！'}, {'角色': '旁白', '内容': '“仙人”这两个字仿佛一道闪电，瞬间劈开了美猴王心中的所有阴霾。他松开智慧猿猴，刚才的忧伤一扫而空，取而代之的是一种燃烧般的决心。'}, {'角色': '孙悟空', '内容': '（对着所有猴子大喊）都别哭了！我决定了！我明天就下山，就算走遍天涯海角，也要拜师学艺，把长生不老的方法给你们带回来！'}, {'角色': '花果山众猴', '内容': '太好了！大王威武！'}, {'角色': '花果山众猴', '内容': '我们等大王回来！我们去准备最好的果子，为大王送行！'}]}, {'场景': 3, '场景剧本': [{'角色': '旁白', '内容': '美猴王告别故土，驾着一叶木筏，漂向了茫茫大海。风暴、烈日、迷茫、孤独……十年光阴，转瞬即逝。'}, {'角色': '孙悟空', '内容': '（内心，疲惫又坚定）十年了……传说中的神仙，到底在哪儿？！我绝不放弃！一定要找到长生不老的方法！'}, {'角色': '旁白', '内容': '就在他几乎绝望之际，一阵悠扬的歌声穿透森林，飘入耳中。'}, {'角色': '樵夫', '内容': '（歌声）观棋柯烂，伐木丁丁，云边谷口徐行……相逢处非仙即道，静坐讲黄庭。'}, {'角色': '孙悟空', '内容': '（内心，狂喜）这歌！没错！是仙气！'}, {'角色': '旁白', '内容': '他精神大振，循声而去，拨开最后的枝叶，却只看到一个砍柴的樵夫。'}, {'角色': '孙悟空', '内容': '（大喝一声，冲上前）站住！你就是那个神仙吧！'}, {'角色': '樵夫', '内容': '（吓了一跳，连连后退）啊！你、你这猴子打哪儿来的？别胡说！我就是个砍柴的，你可别吓我！'}, {'角色': '孙悟空', '内容': '（步步紧逼，语气尖锐）还敢骗我？我为了寻仙访道，在海上漂了整整十年！你唱的歌，句句不离仙道，你还敢说你不是？'}, {'角色': '樵夫', '内容': '（急忙摆手）哎呀，你真的误会了！那歌是住在那山里的一位真神仙教我的，让我烦恼的时候唱着解闷儿用的！我真不是啊！'}, {'角色': '孙悟空', '内容': '（停下脚步，怀疑地）真有神仙？那他为什么不教你长生不老？你还在这里砍柴受苦？'}, {'角色': '樵夫', '内容': '（叹了口气，语气变得淳朴而坚定）长生不老，哪有我娘重要？家里老母亲还等我砍柴换米，我一天都走不开啊。'}, {'角色': '孙悟空', '内容': '（愣住了）……你娘？'}, {'角色': '孙悟空', '内容': '（语气缓和下来，带着一丝敬佩）原来……你是个孝子。是我太心急，错怪你了。'}, {'角色': '樵夫', '内容': '（憨厚地笑了笑）没事没事。'}, {'角色': '孙悟空', '内容': '那你快告诉我，那位神仙究竟住在哪里？'}, {'角色': '旁白', '内容': '樵夫放下斧头，用手指了指远处一座云雾缭绕的高山。'}, {'角色': '樵夫', '内容': '你瞧，那座山叫灵台方寸山。山里有个斜月三星洞，洞里住着一位须菩提祖师。你顺着这条小路一直往南走，就到了。'}, {'角色': '孙悟空', '内容': '（眼神发亮）灵台方寸山，斜月三星洞，须菩提祖师！'}, {'角色': '孙悟空', '内容': '（深深一躬）多谢指点！大恩不言谢，我走啦！'}, {'角色': '旁白', '内容': '话音未落，猴王已化作一道影子，迫不及待地向着那条小路冲去，将樵夫的叮嘱声远远甩在了身后。'}]}, {'场景': 4, '场景剧本': [{'角色': '旁白', '内容': '独自漂洋过海，又在大陆上寻觅了近十年，孙悟空几乎就要放弃希望。这天，他在深山里穿行，一阵悠扬的歌声忽然飘入耳中。他循声拨开树丛，看到一个樵夫正一边砍柴，一边放声高歌。'}, {'角色': '孙悟空', '内容': '（激动地）老神仙！请留步！'}, {'角色': '樵夫', '内容': '（停下斧子，回头）嗯？你这野猴，是在叫我吗？我可不是什么神仙。'}, {'角色': '孙悟空', '内容': '可你唱的歌，句句都是神仙的道理！你别骗我，你肯定就是！'}, {'角色': '樵夫', '内容': '（笑了）你这猴子真会认错人。那歌是山里一位真神仙教我的，我就是个砍柴的，闲着没事唱着解乏罢了。'}, {'角色': '孙悟空', '内容': '（眼睛一亮）真神仙？那……你为什么不跟他学长生不老？这么好的机会！'}, {'角色': '樵夫', '内容': '（叹了口气）唉，我家里还有老母亲要照顾，哪有那个清闲功夫。我凡尘俗事太多，没法学。'}, {'角色': '孙悟空', '内容': '（急切地）你不能学，我可以啊！求求你告诉我，那位神仙住在哪里？我找了他整整十年！'}, {'角色': '樵夫', '内容': '看你这么诚心，就告诉你吧。沿着这条小路往南走，那座最高的山叫灵台方寸山，山里有个斜月三星洞，神仙就住在那儿。'}, {'角色': '孙悟空', '内容': '灵台方寸山……斜月三星洞……多谢！多谢大哥指路！'}, {'角色': '旁白', '内容': '孙悟空告别樵夫，心中燃起从未有过的激动。他沿着小路，翻山越岭，终于在云雾缭绕的山顶，看到了一座洞府。洞府前，一块石碑上赫然刻着十个大字：灵台方寸山，斜月三星洞。'}, {'角色': '孙悟空', '内容': '（喘着粗气，声音颤抖）啊……真不愧是神仙住的地方，感觉空气都是甜的！就是这里！绝对就是这里！'}, {'角色': '旁白', '内容': '他兴奋地冲上前，却发现洞门紧闭。他等了又等，从中午等到日落，洞门依然纹丝不动。希望的火焰，似乎又在一点点熄灭。'}, {'角色': '孙悟空', '内容': '（焦躁地自言自语）难道……又找错了？还是神仙根本就不想见我？不！我不能就这么放弃！喂！有人吗？我是诚心来拜师学艺的！'}, {'角色': '须菩提祖师', '内容': '（声音从门内传来，平静而威严）童儿，开门吧。外面那个修行的，已经等得够久了。'}, {'角色': '旁白', '内容': '话音刚落，厚重的石门吱呀一声向内打开。一个眉清目秀的小仙童走了出来，一脸不耐烦地上下打量着孙悟空。'}, {'角色': '仙童', '内容': '（质问）就是你在外面大喊大叫？知不知道这里是什么地方？'}, {'角色': '孙悟空', '内容': '（连忙作揖）小仙童！是我，是我！我不是故意的，我……我只是太想见到神仙师父了！'}, {'角色': '仙童', '内容': '（怀疑地）就你？一只毛还没长齐的猢狲，也配来这里修行？'}, {'角色': '孙悟空', '内容': '（挺起胸膛）你别小看我！我漂洋过海，吃了无数苦头才找到这里！我的心是最诚的！'}, {'角色': '仙童', '内容': '（冷哼一声）心诚不诚，不是靠嘴说的。……嗯？我家师父刚刚正在讲道，竟忽然停下，点名说外面有个修行的到了，让我来接你。'}, {'角色': '孙悟空', '内容': '（又惊又喜）什么？师父还没见到我，就知道我来了？他说的就是我！'}, {'角色': '仙童', '内容': '（翻了个白眼）不然呢？师父的本事，岂是你能想象的。算你运气好。跟我进来吧，记得收起你的野性，别乱碰乱闯！'}]}, {'场景': 5, '场景剧本': [{'角色': '仙童', '内容': '师父，那个求道的猴子，已在殿外等候多时了。'}, {'角色': '须菩提祖师', '内容': '让他进来。'}, {'角色': '旁白', '内容': '石猴跟着仙童穿过层层殿宇，终于见到那位传说中的神仙。他来不及多想，双膝跪地，声音带着旅途的沙哑和压抑不住的激动。'}, {'角色': '孙悟空', '内容': '神仙！我……我终于找到您了！我找了您十几年，求您，收下我吧！'}, {'角色': '须菩提祖师', '内容': '(声音平静，却带着一股看透一切的威严) 起来。我这里不收来历不明的弟子。你非人非妖，究竟是何来历？'}, {'角色': '孙悟空', '内容': '(猛地抬头) 我…我不是东西！我来自东胜神洲花果山，是一只石猴！'}, {'角色': '须菩提祖师', '内容': '(轻哼一声) 花果山？那与我这里隔着两重大海，一片大陆。你倒是说说，你是怎么来的？别是撒谎骗我吧。'}, {'角色': '孙悟空', '内容': '(急切地) 我没有撒谎！我坐着木筏，在海上漂了几年，又在陆地上走了好多年，吃了无数的苦……就是为了找到神仙，学长生不老之术！'}, {'角色': '旁白', '内容': '祖师的目光锐利如剑，似乎要刺穿这猴子的灵魂，看清他十年旅途的真伪。'}, {'角色': '须菩提祖师', '内容': '十年……哼，毅力可嘉。但想入我门下，光有毅力可不够。你连个名字都没有，我如何收你？'}, {'角色': '孙悟空', '内容': '(声音瞬间低落，充满委屈) 我…我是从石头里蹦出来的，没有父母，自然也没有姓名……'}, {'角色': '须菩提祖师', '内容': '天生地养，倒也有趣。也罢，既然你没有姓名，我就给你一个。你且走两步我看看。'}, {'角色': '音效', '内容': '猴子在殿内蹦跳、挠腮的轻快脚步声。'}, {'角色': '须菩提祖师', '内容': '(露出一丝微笑) 呵呵，你这形态，像个猢狲。猢狲去了兽旁，是个“孙”字。从今天起，你就姓“孙”。'}, {'角色': '孙悟空', '内容': '(难以置信地重复，声音颤抖) 姓……孙？我姓孙了？我……我有姓了！(激动地磕头) 谢谢师父！谢谢师父赐姓！'}, {'角色': '须菩提祖师', '内容': '别急着谢。我门下弟子，皆是“悟”字辈。我再赐你法名，‘悟空’。'}, {'角色': '孙悟空', '内容': '孙……悟空？(抬起头，眼神里充满渴望) 师父，这个名字是什么意思？'}, {'角色': '须菩提祖师', '内容': '名为‘悟空’，是希望你未来能领悟真正的道理，不被世间表象所迷惑。你，能做到吗？'}, {'角色': '孙悟空', '内容': '(用力点头，眼神无比坚定) 领悟真理，不被迷惑！弟子明白了！我叫孙悟空！我就是孙悟空！'}, {'角色': '须菩提祖师', '内容': '好。孙悟空，从今日起，你便是我灵台方寸山，斜月三星洞的弟子了。'}, {'角色': '孙悟空', '内容': '(声音洪亮，充满力量) 弟子孙悟空，拜见师父！'}]}, {'场景': 6, '场景剧本': [{'角色': '须菩提祖师', '内容': '悟空，既然拜我为师，我便传你道法。这“术”字门，可请仙问卜，趋吉避凶。学不学？'}, {'角色': '孙悟空', '内容': '（毫不犹豫）能长生吗？'}, {'角色': '须菩提祖师', '内容': '不能。'}, {'角色': '孙悟空', '内容': '不学！下一个！'}, {'角色': '须菩提祖师', '内容': '（挑了挑眉）好。那“静”字门，可让你入定坐关，宁心静气。这个如何？'}, {'角色': '孙悟空', '内容': '师父，别绕弯子了。它，能长生吗？'}, {'角色': '须菩提祖师', '内容': '……不能。'}, {'角色': '孙悟空', '内容': '不学！不学！'}, {'角色': '须菩提祖师', '内容': '（强压怒火）那这“动”字门，采阴补阳，服食丹药，总该学了吧！'}, {'角色': '孙悟空', '内容': '听起来不错，但我就问一句，这是不是像水里的月亮，看得见摸不着？能让我真正跳出轮回吗？'}, {'角色': '须菩提祖师', '内容': '（叹气）镜花水月而已。'}, {'角色': '孙悟空', '内容': "那还是不学！我要学，就学一个能跟阎王爷说'不'的真本事！这些虚头巴脑的，我没兴趣！"}, {'角色': '旁白', '内容': '悟空这番毫不留情的拒绝，彻底点燃了祖师的怒火。他从高台上一跃而下，手持戒尺，怒视悟空。'}, {'角色': '须菩提祖师', '内容': '（厉声）你这泼猴！这也不学，那也不学，是存心来消遣我的吗！'}, {'角色': '旁白', '内容': '祖师举起戒尺，在悟空头上不轻不重地敲了三下，随即转身，背着双手，径直走入内堂，砰地一声关上了正门，留下满堂错愕的弟子。'}, {'角色': '弟子甲', '内容': '（惊慌）完了完了，这猴子把师父气走了！'}, {'角色': '弟子乙', '内容': '（愤怒地指着悟空）都是你！你这不知天高地厚的家伙，还不快跪下谢罪！'}, {'角色': '旁白', '内容': '面对众人的指责，孙悟空非但不怕，反而嘴角上扬，露出一丝神秘的微笑。'}, {'角色': '弟子甲', '内容': '（难以置信）你还笑得出来？你是不是傻了？师父这是在惩罚你！'}, {'角色': '孙悟空', '内容': '（内心，胸有成竹）你们才不懂呢。师父打我三下，是让我三更时分去寻他；他背手走入内堂，关上中门，是示意我从后门进去。这哪里是惩罚，分明是要私下传我真本事！'}, {'角色': '弟子乙', '内容': '（嘲笑）真是异想天开！我看你是挨打挨昏了头！等着吧，明天师父第一个就要把你赶出山门！'}, {'角色': '孙悟空', '内容': '（耸耸肩，一脸轻松）那咱们就等着瞧。各位师兄早点歇着，我得养足精神，晚上还有事儿呢。'}]}, {'场景': 7, '场景剧本': [{'角色': '旁白', '内容': '几天后的课后，三星洞外的松树下，师兄们把悟空团团围住。'}, {'角色': '菩提祖师众弟子', '内容': '悟空，别光说不练啊，师父教你的腾云术，你到底行不行？'}, {'角色': '孙悟空', '内容': '（得意地）小菜一碟！看我给你们露一手！'}, {'角色': '旁白', '内容': '话音未落，悟空双脚猛地一蹬，身体晃晃悠悠地飞了起来，但速度慢得像散步，飞了一圈就踉踉跄跄地落了地。'}, {'角色': '菩提祖师众弟子', '内容': '（哄笑）哈哈哈，悟空，你这是飞呢，还是在天上爬呢？'}, {'角色': '须菩提祖师', '内容': '（声音突然出现）他说得没错，你这顶多算是“爬云”，算不得真正的腾云。'}, {'角色': '孙悟空', '内容': '（脸一红）师父！那……那要怎样才算腾云？这也太难了！'}, {'角色': '须菩提祖师', '内容': '罢了。看你天生好动，我便传你一招“筋斗云”。一个跟头，十万八千里，学不学？'}, {'角色': '孙悟空', '内容': '（立刻兴奋）学！我学！'}, {'角色': '旁白', '内容': '又过了些时日，悟空不仅练成了筋斗云，七十二变也已烂熟于心。他那颗爱炫耀的心，又开始蠢蠢欲动。'}, {'角色': '菩提祖师众弟子', '内容': '喂，悟空，听说你把七十二变都学会了，真的假的？别是吹牛吧？'}, {'角色': '孙悟空', '内容': '（清了清嗓子）嘿嘿，师父教的本事，我哪样没学会？'}, {'角色': '菩提祖师众弟子', '内容': '那你倒是变一个给我们看看啊！光说谁不会？'}, {'角色': '孙悟空', '内容': '（犹豫）这……师父警告过，本事不能随便拿来炫耀。'}, {'角色': '菩提祖师众弟子', '内容': '怕什么！师父又不在！就我们自己人看看，谁会说出去？你要是真有本事，现在就变一个！'}, {'角色': '菩提祖师众弟子', '内容': '对！就变棵松树，让我们开开眼！'}, {'角色': '孙悟空', '内容': '（被激起好胜心）好！这有何难！你们可站远点，看仔细了！'}, {'角色': '旁白', '内容': '悟空捻动法诀，口中念念有词，身子一晃，只听“噗”的一声轻响，原地瞬间出现一棵挺拔的松树。'}, {'角色': '菩提祖师众弟子', '内容': '（惊呼）快看！悟空不见了，地上真的多了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '（上前触摸）我的天，连树皮和松针都跟真的一模一样！太神了！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！真厉害！'}, {'角色': '须菩提祖师', '内容': '（声音如雷霆般响起）吵吵嚷嚷的，成何体统！'}, {'角色': '旁白', '内容': '喝彩声戛然而止。松树瞬间变回孙悟空，他吓得一哆嗦，低着头站在原地。'}, {'角色': '须菩提祖师', '内容': '孙悟空！你把我的话当耳旁风了？我教你本事，是让你拿来当杂耍炫耀的吗！'}, {'角色': '孙悟空', '内容': '（急忙辩解）不是的师父！是师兄们非要我变的，我只是……'}, {'角色': '须菩提祖师', '内容': '（严厉打断）住口！他们让你变你就变？学了点皮毛就到处张扬，你知不知道卖弄神通会给你招来杀身之祸！'}, {'角色': '孙悟空', '内容': '（慌了神）师父，弟子真的知错了！我再也不敢了！求您饶我这一次吧！'}, {'角色': '须菩提祖师', '内容': '（语气冰冷）这里，留你不得。你走吧。'}, {'角色': '孙悟空', '内容': '（震惊）师父！您要赶我走？我……我还能去哪儿啊？'}, {'角色': '须菩提祖师', '内容': '从哪儿来，回哪儿去！但你给我记死了：从今以后，不准对任何人说你是我徒弟。敢说出半个字，我便让你神魂俱灭，永世不得超生！听明白了吗？'}, {'角色': '孙悟空', '内容': '（含泪叩首）明白了！弟子明白了！绝不提师父半个字，就说……就说都是我自己天生就会的！'}, {'角色': '旁白', '内容': '悟空知道再无挽回的余地。他朝祖师重重地磕了三个响头，然后翻身跃起，驾着筋斗云，化作一道金光，消失在了天际。'}]}, {'场景': 8, '场景剧本': [{'角色': '菩提祖师众弟子', '内容': '哇！悟空真的变成了一棵松树！'}, {'角色': '菩提祖师众弟子', '内容': '太神了！连树皮的纹路都一模一样！'}, {'角色': '菩提祖师众弟子', '内容': '好猴子！好猴子！这本事也太帅了！'}, {'角色': '旁白', '内容': '弟子们的喝彩声在安静的松林里显得格外响亮，打破了午后的宁静，也惊动了正在静修的祖师。'}, {'角色': '须菩提祖师', '内容': '(严厉地) 孙悟空！你在做什么！'}, {'角色': '旁白', '内容': '祖师的声音如洪钟般传来，众人瞬间噤声。那棵松树在一阵微光中变回了孙悟空的原形，他从师兄们中间挤出来，忐忑地低下了头。'}, {'角色': '孙悟空', '内容': '师父……弟子在和师兄们切磋法术。'}, {'角色': '须菩提祖师', '内容': '切磋？我怎么看着像是在卖弄？孙悟空，你是不是觉得，学了点皮毛，就天下无敌了？'}, {'角色': '孙悟空', '内容': '(急忙辩解) 弟子不敢！我只是…想让大家看看七十二变的奇妙，这有什么不对吗？'}, {'角色': '须菩提祖师', '内容': '(痛心疾首) 有什么不对？错就错在你这颗炫耀的心！悟空！我教你本领，是让你护身的，不是让你拿来当戏法耍给别人看的！'}, {'角色': '孙悟空', '内容': '师父，我……'}, {'角色': '须菩提祖师', '内容': '你今天能变松树引人喝彩，明天就会有人逼你变条龙来满足他们的欲望！到那时，你不给，他们便会害你！你给了，麻烦更大！你这性子，留在这里，迟早会给我惹来灭门之祸！'}, {'角色': '孙悟空', '内容': '(震惊) 灭门之祸？师父，您言重了！我改！我以后再也不敢了！'}, {'角色': '须菩提祖师', '内容': '(语气决绝) 晚了。不必改了。你走吧。'}, {'角色': '旁白', '内容': '“你走吧”三个字像晴天霹雳，悟空脸上的血色瞬间褪尽，他完全不敢相信自己的耳朵。'}, {'角色': '孙悟空', '内容': '走？去哪儿？师父，您不能赶我走！我错了，我真的知道错了！求您再给我一次机会！'}, {'角色': '须菩提祖师', '内容': '从哪里来，回哪里去。'}, {'角色': '孙悟空', '内容': '(带着哭腔) 不要啊师父！我离家二十年，这里就是我的家啊！您不要我，我就没家了！'}, {'角色': '须菩提祖师', '内容': '住口！你给我听好了！你此去，无论惹出什么滔天大祸，都不许提我是你的师父。'}, {'角色': '孙悟空', '内容': '(哽咽) 师父……为什么……'}, {'角色': '须菩提祖师', '内容': '(一字一顿，不容置疑) 你若敢说出半个字，我便知晓，定将你的神魂贬至九幽之处，让你万劫不得翻身！听清楚了吗！'}, {'角色': '孙悟空', '内容': '(浑身一颤，彻底绝望) 弟子……听清楚了。弟子绝不敢提师父半字……只说，是我自己会的。'}, {'角色': '须菩提祖师', '内容': '(闭上眼，轻声但坚定地) 去吧。'}, {'角色': '旁白', '内容': '悟空再也忍不住泪水，他知道一切已无法挽回。他重重地跪了下去，朝着恩师，磕了最后一个响头。'}, {'角色': '孙悟空', '内容': '(含泪) 师父大恩，弟子永世不忘。弟子……给师父磕头了。'}]}]}

    refine_script = remove_parentheses_in_script(refine_script)  # 去除语气标注等
    refine_script2 = normalize_script_characters(refine_script, character_list)
    # print(refine_script2)
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

    Emotion = {'语气标注': [{'场景': 1, '场景剧本': [{'台词位置': 0, '语气指导': '【神秘而宏大】语速平稳，声音清晰有力。在“轰然迸裂”处加重语气，营造冲击感。“直冲云霄，惊动了天庭”语调上扬，带出悬念。'}, {'台词位置': 1, '语气指导': '【惊慌失措，急切】语速快，声音带着颤抖和焦急。开头“陛下”要响亮，表现出急于禀报的样子。“刺得我眼睛都睁不开”要带上一点痛苦的夸张感。'}, {'台词位置': 2, '语气指导': '【急切附和，夸张】紧接上一句，情绪同样激动。语速快，重音落在“龙吟”和“撼天动地”上，强调事件的非同凡响。'}, {'台词位置': 3, '语气指导': '【沉稳威严，略带责备】语速放慢，语调平稳低沉，显示出帝王的镇定和从容。前半句“慌张什么”带着一丝轻微的训斥，后半句恢复平稳的询问语气。'}, {'台词位置': 4, '语气指导': '【恭敬汇报，仍有余惊】语速比之前稍慢，但仍能听出紧张感。语气恭敬，条理清晰地说明情况。'}, {'台词位置': 5, '语气指导': '【恍然轻笑，不以为意】先发出一声轻笑“呵”，带着了然和一丝轻视。整句话语调轻松，充满见怪不怪的宽宏感，最后“由他去吧”说得随意而果断。'}, {'台词位置': 6, '语气指导': '【温和平缓，承上启下】语速舒缓，营造出时光流逝的宁静感。描述猴群生活时，语气变得轻快愉悦，为接下来的场景铺垫活泼的气氛。'}, {'台词位置': 7, '语气指导': '【天真烂漫，充满活力】（多人齐声，声音嘈杂但快乐）语调高昂，充满孩童般的嬉闹感，笑声要爽朗、无忧无虑。'}, {'台词位置': 8, '语气指导': '【好奇又惊叹】（单人或两三人）声音中充满发现新事物的兴奋和对大自然的敬畏，语调上扬，带着一点点向往。'}, {'台词位置': 9, '语气指导': '【嘲讽，胆怯】（另一人）语气带着不屑和一点点恐惧，语速稍快，像是在泼冷水。“傻子”两个字要说得又快又重。'}, {'台词位置': 10, '语气指导': '【沉稳提议，有理有据】声音比其他猴子更稳重，不急不躁。前半句有制止争论的意味，后半句“拜他为王”则要说得清晰有力，充满诱惑力。'}, {'台词位置': 11, '语气指导': '【质疑，不屑】（多人，七嘴八舌）第一声“为王？”充满怀疑。整句话的语气是觉得这个提议很可笑，完全不相信有人能做到。'}, {'台词位置': 12, '语气指导': '【自信果决，掷地有声】声音不大但异常坚定，两个字干脆利落，没有丝毫犹豫。语调平直，充满了不容置疑的力量感，瞬间吸引全场注意。'}, {'台词位置': 13, '语气指导': '【惊讶，担忧，规劝】（多人）第一声“你？”拖长，表示难以置信。后面的话语速变快，充满了“你别冲动”的劝说意味。'}, {'台词位置': 14, '语气指导': '【霸气张扬，充满挑衅】前半句沉稳而霸气，宣示主权。后半句语调上扬，带着一丝顽皮和炫耀，仿佛已经预见了胜利，对“新大王”三个字可以加重音。'}, {'台词位置': 15, '语气指导': '【紧张急促，动作感强】语速加快，营造出千钧一发的紧张氛围。用声音描绘出石猴跳跃的迅猛轨迹，在“消失”一词后可稍作停顿，留下悬念。'}, {'台词位置': 16, '语气指导': '【震惊，难以置信】（多人惊呼）声音带着破音的边缘，充满了不敢相信的情绪。“疯子”两个字是脱口而出的惊叹。'}, {'台词位置': 17, '语气指导': '【绝望，恐惧】（另一人）声音低沉，语速缓慢，充满了悲观和失落。“完了”两个字要说得有气无力。'}, {'台词位置': 18, '语气指导': '【懊悔，自责】声音颤抖，充满了内疚。语速慢，像是在喃喃自语。'}, {'台词位置': 19, '语气指导': '【悲愤，指责】情绪激动，带着哭腔和愤怒，把责任推到智慧猿猴身上。语速快，语气冲。'}, {'台词位置': 20, '语气指导': '【悬念转折，希望渐起】前半句延续绝望的气氛，语速较慢。在“一个洪亮的声音”处，语调开始上扬，语速加快，预示着奇迹的发生。'}, {'台词位置': 21, '语气指导': '【洪亮，得意，略带回响】声音穿透力强，可以加上一点混响效果。第一声“喂”要拖长。语气中满是成功后的得意和对同伴的善意嘲弄。'}, {'台词位置': 22, '语气指导': '【狂喜，如释重负】（多人）从低落到狂喜的巨大转变，声音里充满了失而复得的激动和喜悦，可以带一点喜极而泣的感觉。'}, {'台词位置': 23, '语气指导': '【兴奋招手，急于分享】（略带回响）语速快，充满发现新大陆的激动，像是在向同伴展示宝藏。每一个字都带着兴奋。'}, {'台词位置': 24, '语气指导': '【惊喜，赞叹不已】（多人，进入山洞后的声音）充满了孩子气的好奇和惊叹。“哇”要发自内心。语气从惊喜逐渐变为对新家园的喜爱。'}, {'台词位置': 25, '语气指导': '【骄傲，意气风发】声音洪亮，充满了领袖气质。念出石碑上的字时要一字一顿，充满力量。最后一句是对未来的美好宣告，充满希望。'}, {'台词位置': 26, '语气指导': '【激动，恍然大悟】前半句是发自内心的喜悦。一个短暂的停顿后，像是突然想起了什么，语气变得严肃而郑重，大声说出约定。'}, {'台词位置': 27, '语气指导': '【庄重，心悦诚服】语速放缓，语气变得庄重。描述猴群的动作和心情，烘托出“美猴王”诞生的仪式感和众望所归的氛围。'}, {'台词位置': 28, '语气指导': '【崇敬，整齐划一】（所有人齐声）声音洪亮、整齐，充满了真诚的敬佩和拥戴。语调庄重，但难掩其中的喜悦。'}, {'台词位置': 29, '语气指导': '【爽朗大笑，王者风范】笑声要发自内心，响亮而充满感染力，体现他的豪迈和开心。后半句话语气亲切又不失威严，正式接受“王”的身份。'}]}, {'场景': 2, '场景剧本': [{'台词位置': 0, '语气指导': '[欢快，带点醉意] 声音高昂，语速稍快，带着大笑的语气，像是举着杯子高喊，充满享乐的喜悦。'}, {'台词位置': 1, '语气指导': '[满足，随声附和] 语调上扬，充满幸福感，可以加入一些满足的轻笑，表达对现状的极度满意。'}, {'台词位置': 2, '语气指导': '[先扬后抑，制造悬念] 开头语速平稳，营造欢乐气氛；到“然而”时语速放慢，语调转低；“砰！”后稍作停顿，强调气氛的凝固。'}, {'台词位置': 3, '语气指导': '[忧虑，声音低沉] 语速缓慢，语调低沉，带着一丝迷茫和深刻的忧虑，与周围的欢乐格格不入。'}, {'台词位置': 4, '语气指导': '[困惑，带点埋怨] 语气从不解到有点委屈，像是被泼了冷水，带着“扫兴”的抱怨感，但核心是关心。'}, {'台词位置': 5, '语气指导': '[轻松劝慰，不以为意] 语速轻快，试图把气氛拉回欢乐，带着一种“今朝有酒今朝醉”的简单天真。'}, {'台词位置': 6, '语气指导': '[激动，语速加快] 声音开始提高，情绪激动，带着不耐烦和焦急。说到“老”、“牙齿掉光”时，带着对未来的恐惧。'}, {'台词位置': 7, '语气指导': '[恐惧，情绪爆发] 情绪推向高潮，声音颤抖但又很大声。“死”字要说的很重。最后一句“懂吗！”是带着绝望的质问，几乎是吼出来的。'}, {'台词位置': 8, '语气指导': '[低沉，渲染悲伤] 语速放缓，语调冰冷，营造出欢乐被彻底粉碎的凝重气氛。描述哭泣声时，声音要轻，充满同情。'}, {'台词位置': 9, '语气指导': '[恐惧，哭腔] 声音颤抖，带着明显的哭腔和鼻音，语速断断续续，表达出第一次直面死亡概念的巨大恐惧。'}, {'台词位置': 10, '语气指导': '[承上启下，引出转折] 开头延续悲伤的气氛，但语调逐渐上扬，到“高声喊道”时变得有力，预示着希望的出现。'}, {'台词位置': 11, '语气指导': '[坚定有力，振聋发聩] 声音洪亮而沉稳，不带哭腔，语速果断，像是一声棒喝，要立刻打破现场的悲伤气氛。'}, {'台词位置': 12, '语气指导': '[急切，带一丝怀疑] 语速快，带着抓住救命稻草般的急切。后半句的“难道”可以带上一点点怀疑，但更多的是期盼。'}, {'台词位置': 13, '语气指导': '[沉稳神秘，引人入胜] “我没有”说的干脆，然后稍作停顿，转而用肯定、充满希望的语气说出“但有人有”。提到“仙人”时，声音放轻，带着敬畏和神秘感。'}, {'台词位置': 14, '语气指导': '[惊喜交加，极度渴望] 声音瞬间提亮，语调急剧升高。“仙人”带着震惊和不敢相信。“快告诉我”语速极快，一连串发问，表现出内心的迫不及待。'}, {'台词位置': 15, '语气指导': '[庄重，充满敬畏] 语速放缓，声音带着一种描绘神圣之地的向往和崇敬感，语气肯定而神圣。'}, {'台词位置': 16, '语气指导': '[激昂，充满力量] 语调上扬，语速加快，描述闪电时要有力。从“忧伤一扫而空”开始，语气要变得坚定、充满决心，为悟空接下来的台词铺垫情绪。'}, {'台词位置': 17, '语气指导': '[豪情万丈，领袖风范] 声音洪亮，充满力量和决心。“我决定了！”斩钉截铁。整句话语速坚定，充满对未来的无限信心和对猴群的承诺。'}, {'台词位置': 18, '语气指导': '[欢呼雀跃，崇拜] 破涕为笑，从哭泣转为高声欢呼，声音里充满崇拜和被点燃的希望，激动不已。'}, {'台词位置': 19, '语气指导': '[积极响应，充满期待] 语气积极、充满干劲，带着对未来的美好憧憬和对大王的无限支持。'}]}, {'场景': 3, '场景剧本': [{'台词位置': 0, '语气指导': '讲述感，语速平稳。前半句带一丝对漫长时间的感慨，后半句语调略微低沉，描绘出旅途的艰辛与孤独。'}, {'台词位置': 1, '语气指导': '先是压抑不住的烦躁和疲惫，带着自我怀疑的质问。随即情绪转为激昂，语调上扬，语速加快，充满不屈的斗志和坚定的信念。'}, {'台词位置': 2, '语气指导': '语调转为轻快、神秘，带着一丝希望和悬念，仿佛黑暗中透进一缕光。'}, {'台词位置': 3, '语气指导': '（唱出来）声音质朴、悠扬，带着一种超然物外的闲适感，仿佛在自得其乐，语调平缓，充满安宁。'}, {'台词位置': 4, '语气指导': '惊喜！像是瞬间被注入了能量，声音洪亮，语速急促，带着发现宝藏般的狂喜和不容置疑的肯定。'}, {'台词位置': 5, '语气指导': '前半句语调上扬，充满期待感。后半句语调转为平淡，略带一丝反差和意外。'}, {'台词位置': 6, '语气指导': '急切、理直气壮，甚至有点粗鲁。带着长久寻觅后终于找到目标的激动和不耐烦，语调高昂，命令式。'}, {'台词位置': 7, '语气指导': '被吓了一跳，声音哆嗦，语无伦次。充满了惊恐、困惑和急于撇清关系的慌乱，语速快，音调高。'}, {'台词位置': 8, '语气指导': '充满被欺骗的愤怒和质疑。语速加快，情绪激动，强调“十年”时带着委屈和怨气，最后的反问语气非常强硬。'}, {'台词位置': 9, '语气指导': '急切地辩解，语气真诚又无奈。语速快，想要尽快解释清楚，避免误会，带着恳求的意味。'}, {'台词位置': 10, '语气指导': '半信半疑，语气尖锐，带着逻辑上的质问和一点点轻蔑。认为对方的解释不合常理。'}, {'台词位置': 11, '语气指导': '语气立刻变得温柔而坚定，充满对母亲的爱。语调平和、真挚，仿佛在陈述一个天经地义的事实，充满了孝心。'}, {'台词位置': 12, '语气指导': '轻声的、充满触动的自语。语调从之前的尖锐变得柔软，带着一丝困惑和感悟。'}, {'台词位置': 13, '语气指导': '诚恳地道歉，有点不好意思。语速放缓，语气真挚，认识到自己的鲁莽，态度一百八十度大转弯。'}, {'台词位置': 14, '语气指导': '憨厚、淳朴地摆摆手，语气轻松，表示并不在意。'}, {'台词位置': 15, '语气指导': '激动和希望重燃，但这次态度变得非常礼貌和恳切。语速急切，充满渴望。'}, {'台词位置': 16, '语气指导': '旁白语速放缓，语调沉稳，营造出一种神圣、庄严的氛围，引导听众的视线。'}, {'台词位置': 17, '语气指导': '热情、耐心地指引，语气友善而清晰，像一个好心的邻居在指路。'}, {'台词位置': 18, '语气指导': '（念出声）充满敬畏和神圣感。一字一顿，仿佛在念诵神圣的咒语，每念一个词，情绪就更激动一分。'}, {'台词位置': 19, '语气指导': '兴奋到极点，语速飞快，声音响亮，充满感激和迫不及待。说完最后一个字人就已经冲出去了的感觉。'}, {'台词位置': 20, '语气指导': '语速加快，语调激昂，充满动感，描绘出孙悟空化作一道闪电的急切心情，为本段故事收尾并留下期待。'}]}, {'场景': 4, '场景剧本': [{'台词位置': 0, '语气指导': '语速平稳，前半句带着一丝疲惫和悬念，后半句转为轻快和好奇，为即将到来的相遇铺垫希望感。'}, {'台词位置': 1, '语气指导': '语气急切又充满惊喜，音量稍高，带着恳求和尊敬，仿佛抓住了最后一根救命稻草，生怕对方走掉。'}, {'台词位置': 2, '语气指导': '语速放慢，带着朴实的疑惑和一点被逗乐的感觉，语气随和、坦诚，像在和一只不懂事的小动物说话。'}, {'台词位置': 3, '语气指导': '语气非常肯定、急切，带着孩子气的执着和天真，语速稍快，充满了不容置疑的兴奋感。'}, {'台词位置': 4, '语气指导': '语气温和、耐心，带着善意的微笑，坦诚地解释，语调平稳，像一位忠厚的长者在和一个晚辈沟通。'}, {'台词位置': 5, '语气指导': '语调瞬间拔高，充满强烈的好奇和极度的不解。从刚才的执着转为急切的追问，情绪转换要快。'}, {'台词位置': 6, '语气指导': '叹气开头，语气变得沉稳而略带伤感，充满了对现实的无奈和对母亲的责任感，语速放缓，情感真挚。'}, {'台词位置': 7, '语气指导': '情绪激动，音量提高，充满强烈的恳求和压抑不住的渴望，强调“整整十年”时，要带上寻觅已久的辛酸和坚定。'}, {'台词位置': 8, '语气指导': '语气温和、诚恳，被悟空的执着打动。说出地址时，语速放慢，吐字清晰，像一位善良的长者在耐心指路。'}, {'台词位置': 9, '语气指导': '语速快，充满如获至宝的狂喜。重复地名时，像是在念诵珍贵的咒语。最后的感谢发自肺腑，响亮而真诚。'}, {'台词位置': 10, '语气指导': '语调上扬，充满激动人心的期待感。描述山景和洞府时，声音要带上一种庄严和神秘感，为神仙出场做铺垫。'}, {'台词位置': 11, '语气指导': '带着深吸一口气的惊叹感，声音因激动而微微颤抖，充满敬畏和狂喜。后半句的语气变得无比坚定和兴奋。'}, {'台词位置': 12, '语气指导': '语调转为平缓、略带失落，语速放慢，营造出漫长等待和希望逐渐消磨的沉重气氛，与之前的激动形成对比。'}, {'台词位置': 13, '语气指导': '开头是自我怀疑的喃喃自语，接着猛地转为坚定和自我鼓励，最后大声呼喊时，声音洪亮，混合着焦急、恳切和最后一搏的决心。'}, {'台词位置': 14, '语气指导': '声音沉稳、悠远，带着不容置疑的威严。语速缓慢，音调低沉，仿佛洞悉一切，有一种超凡脱俗的平静感。'}, {'台词位置': 15, '语气指导': '语气略带神秘，描述开门时可稍作停顿。描述仙童时，语调变得清亮一些，但要透出“不耐烦”的审视感。'}, {'台词位置': 16, '语气指导': '语气清脆，带着少年人的傲气和被打扰的不耐烦，语调上扬，有明显的质问意味。'}, {'台词位置': 17, '语气指导': '语气急切、讨好，又有点手足无措。语速快，带着辩解和极度渴望被理解的情绪，姿态放得很低。'}, {'台词位置': 18, '语气指导': '语气轻蔑，带着明显的审视和看不起。语速不快，但每个字都透出优越感，可以带一点居高临下的鼻音。'}, {'台词位置': 19, '语气指导': '语气变得激动、不服气，声音提高，为自己辩护。说到“吃了无数苦头”时，要带上委屈和坚韧；说到“心是最诚的”时，要无比坚定。'}, {'台词位置': 20, '语气指导': '前半句是说教的口吻，带着些许居高临下。后半句转为带有困惑和惊讶的陈述，语速放慢，仿佛在复述一件不可思议的事情。'}, {'台词位置': 21, '语气指导': '极度惊喜，声音因激动而拔高，充满了不敢相信和巨大的荣幸感。语速快，情绪饱满，是希望被证实的狂喜。'}, {'台词位置': 22, '语气指导': '语气恢复了之前的清冷和一点不情愿，但已接受事实。最后的警告说得严肃、清晰，带着一点小大人的口吻，强调自己的引导地位。'}]}, {'场景': 5, '场景剧本': [{'台词位置': 0, '语气指导': '恭敬、平稳。向师父汇报，语气沉稳清晰，不卑不亢。'}, {'台词位置': 1, '语气指导': '沉稳、威严。声音不高但充满力量，仿佛已洞察一切，语速平缓。'}, {'台词位置': 2, '语气指导': '略带神秘和期待感。语速平稳，在描述石猴心情时，语气要同步染上激动和虔诚的感觉，引导听众情绪。'}, {'台词位置': 3, '语气指导': '激动、恳切、带哭腔。声音因长途跋涉而沙哑，情绪激动到有些语无伦次，带着颤抖和压抑许久的爆发力，充满渴望。'}, {'台词位置': 4, '语气指导': '威严、审视。语气平静但带有压迫感，像是在考验对方，语调平直，不带感情色彩。'}, {'台词位置': 5, '语气指导': '急切、天真。因为紧张而口不择言，喊出“不是东西”时天真又着急，后面解释时语速加快，充满真诚。'}, {'台词位置': 6, '语气指导': '怀疑、质问。语调微微上扬，带着明显的怀疑，像是在故意施压，考验对方是否诚实。'}, {'台词位置': 7, '语气指导': '激动、坚定。急于辩解，声音提高，充满激情。描述辛苦时带上回忆的艰辛感，说到最终目的时则充满毫不动摇的决心。'}, {'台词位置': 8, '语气指导': '紧张、悬念。语速放慢，营造出一种紧张对峙的氛围，声音略沉，强调祖师目光的穿透力。'}, {'台词位置': 9, '语气指导': '先抑后扬、带着考验。说“哼”时带一丝不易察觉的赞许，但马上又转为严肃，提出新的难题，语气不容置疑。'}, {'台词位置': 10, '语气指导': '失落、坦诚。情绪低落下来，声音变轻，带着一丝孤单和茫然，但回答时很坦率。'}, {'台词位置': 11, '语气指导': '略带趣味、权威。语气中首次出现一丝轻松和好奇，但依然保持着宗师的气度，充满不容置疑的权威感。'}, {'台词位置': 12, '语气指导': '音效指导：脚步声要体现出猴子的灵动、活泼和隐藏不住的顽皮天性。'}, {'台词位置': 13, '语气指导': '温和、风趣。带着一丝长者的笑意，像是在欣赏一件璞玉，解释时循循善诱，宣布姓氏时则变得庄重。'}, {'台词位置': 14, '语气指导': '惊喜、狂喜。从不敢相信的喃喃自语，到确认后的狂喜，情绪层层递进，最后是发自肺腑的、带着哽咽的感谢。'}, {'台词位置': 15, '语气指导': '庄重、严肃。打断悟空的激动，语气变得非常正式，宣布法名时，语速放慢，一字一顿，充满仪式感。'}, {'台词位置': 16, '语气指导': '好奇、求知。重复名字时带着品味和思索，紧接着的提问充满了一个孩子般的好奇心和对知识的渴望。'}, {'台词位置': 17, '语气指导': '循循善诱、意味深长。像一位真正的导师在传授至理，声音充满智慧。最后一句提问，语调加重，直击人心，充满考验的意味。'}, {'台词位置': 18, '语气指导': '坚定、新生。重复师父的话时充满力量，像是立下誓言。喊出自己名字时，充满了找到自我身份的骄傲和力量，语调激昂。'}, {'台词位置': 19, '语气指导': '欣慰、庄严。一个“好”字，充满了肯定的意味。随后的话语是正式的宣布，语速沉稳，宣告一个新身份的诞生。'}, {'台词位置': 20, '语气指导': '恭敬、激动、庄重。用尽全身力气，充满仪式感地一拜，声音洪亮而真诚，标志着全新人生的开始。'}]}, {'场景': 6, '场景剧本': [{'台词位置': 0, '语气指导': '[庄重威严，语速平稳] 声音沉稳，带着师长的威严和一丝考究的意味。最后的“学不学？”语调略微上扬，像是在抛出一个选择题。'}, {'台词位置': 1, '语气指导': '[急切直接，充满期待] 语速快，毫不犹豫地接话，问题问得非常直接，充满了对“长生”这一目标的渴望。'}, {'台词位置': 2, '语气指导': '[平静坚决，不带感情] 语调平淡，干脆利落，没有丝毫拖泥带水，像是在陈述一个客观事实。'}, {'台词位置': 3, '语气指导': '[干脆利落，毫不犹豫] “不学”两个字斩钉截铁，带着孩子气的任性。“下一个！”喊得响亮，充满了不耐烦和催促感。'}, {'台词位置': 4, '语气指导': '[波澜不惊，循循善诱] 语气依旧平稳，似乎对悟空的无礼毫不在意。介绍时语速放缓，带着引导性，像在展示一件新奇的玩意儿。'}, {'台词位置': 5, '语气指导': '[急不可耐，直奔主题] 语气有点不耐烦，但还带着对师父的一丝“尊敬”。“它”字可以稍微重读，然后停顿一下，再问出关键问题，强调自己的唯一目的。'}, {'台词位置': 6, '语气指导': '[略带停顿，平静否定] 开头有一个短暂的停顿，仿佛在审视悟空的反应，然后给出否定的回答，语气依然坚决。'}, {'台词位置': 7, '语气指导': '[坚决果断，带点脾气] 连说两遍“不学”，第二遍比第一遍更重、更快，像是在跺脚，表达强烈的拒绝和一丝孩子气的固执。'}, {'台词位置': 8, '语气指导': '[略带激将，加重语气] 语气稍微提高，带有一点“我就不信你还不学”的激将法意味。“总该学了吧！”语调上扬，带着不容置疑的口气。'}, {'台词位置': 9, '语气指导': '[先扬后抑，充满质疑] 开头“听起来不错”语气缓和，似乎有点兴趣，但马上转为严肃和尖锐。最后的提问直击要害，语调加重，显示他的聪慧和坚定。'}, {'台词位置': 10, '语气指导': '[坦然承认，略带赞许] 语气平静地承认，声音里可能藏着一丝不易察觉的赞许，认可了悟空的悟性。'}, {'台词位置': 11, '语气指导': '[慷慨激昂，意志坚定] 声音洪亮，充满了决心和力量。“真本事”三个字要说得掷地有声。最后一句带着少年人的傲气和对“虚假”法术的不屑。'}, {'台词位置': 12, '语气指导': '[紧张悬疑，铺垫气氛] 语速加快，语气变得紧张，为接下来的冲突铺垫气氛。“点燃”、“一跃而下”、“怒视”等词语要加重，营造出山雨欲来的压迫感。'}, {'台词位置': 13, '语气指导': '[怒不可遏，声色俱厉] 声音提高，充满怒气，但这种愤怒是表演给外人看的，底层要稳住。每个字都像是在训斥，充满压迫感。'}, {'台词位置': 14, '语气指导': '[描述清晰，暗藏玄机] 语速平稳，但要强调关键动作。“不轻不重”要说得意味深长。“三下”要清晰。“砰地一声”可以模仿音效加重，然后迅速转为描述众人“错愕”的状态，留下悬念。'}, {'台词位置': 15, '语气指导': '[惊慌失措，带着哭腔] 语速快，声音发抖，带着焦虑和恐惧。“完了完了”要说得很有节奏感，像是在哀嚎。'}, {'台词位置': 16, '语气指导': '[气急败坏，厉声指责] 语气严厉，充满了指责和愤怒，但底色是害怕自己也受牵连。音量可以提高，表现出他的激动。'}, {'台词位置': 17, '语气指导': '[神秘平缓，突出反差] 语调放缓，变得神秘而轻松，与前面紧张的气氛形成鲜明对比。“神秘的微笑”要说得轻巧，引导听众的好奇心。'}, {'台词位置': 18, '语气指导': '[难以置信，语气夸张] 声音充满惊讶和不解，语调拔高。“傻了”、“惩罚你”要说得又重又响，像是在教训一个不懂事的孩子。'}, {'台词位置': 19, '语气指导': '[自信得意，娓娓道来] 开头“你们才不懂呢”带着一点小小的得意和炫耀。解释谜题时，语速不快，条理清晰，充满智慧的光芒。最后一句“分明是要私下传我真本事！”语气上扬，充满了兴奋和期待。'}, {'台词位置': 20, '语气指导': '[轻蔑嘲讽，嫉妒不满] 语气充满鄙视和不屑，“异想天开”可以拖长音来强调嘲讽。后面带着幸灾乐祸的威胁。'}, {'台词位置': 21, '语气指导': '[轻松自信，略带俏皮] 语气轻松，充满自信，完全不受他人影响。“等着瞧”说得云淡风轻。最后一句带着点小神秘和小得意，可以带一点俏皮的笑意。'}]}, {'场景': 7, '场景剧本': [{'台词位置': 0, '语气指导': '语速平稳，略带悬念，为即将发生的事件铺垫。'}, {'台词位置': 1, '语气指导': '语气轻佻，带着起哄和不相信的挑衅，语速稍快。'}, {'台词位置': 2, '语气指导': '骄傲自信，声音洪亮，充满少年人的炫耀感和活力。'}, {'台词位置': 3, '语气指导': '语带轻松和一丝戏谑，描述一个滑稽的失败场面。'}, {'台词位置': 4, '语气指导': '爆发出一阵哄笑，语气充满不加掩饰的嘲讽和轻蔑。'}, {'台词位置': 5, '语气指导': '声音突然出现，平静而威严，不带情绪，只是陈述事实，但自有一股压力。'}, {'台词位置': 6, '语气指导': '刚才的得意荡然无存，声音变得急切、委屈，还带着一点撒娇似的抱怨。'}, {'台词位置': 7, '语气指导': '语气平稳，带有一丝看透一切的智慧，后半句略带引诱，像是在考验悟空的向道之心。'}, {'台词位置': 8, '语气指导': '毫不犹豫，声音瞬间充满极度的兴奋和渴望，语速极快，音调上扬。'}, {'台词位置': 9, '语气指导': '语速平稳，作为转场，情绪略带预示，暗示悟空爱炫耀的性格将再次引发事端。'}, {'台词位置': 10, '语气指导': '半信半疑，语气中带着嫉妒和再次的挑衅，想看他出丑。'}, {'台词位置': 11, '语气指导': '得意洋洋，带着点小聪明和自满，嘿嘿一笑，充满自信。'}, {'台词位置': 12, '语气指导': '不耐烦地催促，激将法，语气更加咄咄逼人。'}, {'台词位置': 13, '语气指导': '语气迟疑，声音变小，有点为难和顾虑，内心在挣扎。'}, {'台词位置': 14, '语气指导': '怂恿，语气轻快，满不在乎，用“自己人”来拉近关系，降低他的警惕。'}, {'台词位置': 15, '语气指导': '兴奋地提出具体要求，充满期待和看热闹的心态。'}, {'台词位置': 16, '语气指导': '被说动了，虚荣心占了上风，恢复了之前的神气和骄傲，声音响亮。'}, {'台词位置': 17, '语气指导': '语速放缓，营造出一种神秘、神奇的氛围，声音可以轻一些，强调“噗”的音效。'}, {'台词位置': 18, '语气指导': '压低声音的惊呼，充满了不敢相信的震撼。'}, {'台词位置': 19, '语气指导': '从震惊转为赞叹，语调上扬，充满惊奇和佩服。'}, {'台词位置': 20, '语气指导': '转为大声喝彩，情绪热烈，可以加上鼓掌叫好的背景声。'}, {'台词位置': 21, '语气指导': '声音如洪钟，威严而愤怒，瞬间打破所有欢乐气氛，充满严厉的斥责。'}, {'台词位置': 22, '语气指导': '语速变快，语气紧张，描述气氛的骤变和悟空的惊恐。'}, {'台词位置': 23, '语气指导': '怒不可遏，质问的语气，每一个字都带着师长的失望和怒火。'}, {'台词位置': 24, '语气指导': '慌乱，急于辩解，声音颤抖，带着哭腔，想把责任推给别人。'}, {'台词位置': 25, '语气指导': '厉声打断，愤怒中带着痛心和严肃的警告，语速加快，情绪推向高潮。'}, {'台词位置': 26, '语气指导': '彻底崩溃，声音里满是恐惧和哀求，带着哭声，语无伦次地认错。'}, {'台词位置': 27, '语气指导': '怒气已过，声音变得冰冷、坚决，不带一丝感情，宣布最终决定。'}, {'台词位置': 28, '语气指导': '不敢相信，声音绝望，从哀求转为不知所措的喃喃自语，充满被抛弃的无助感。'}, {'台词位置': 29, '语气指导': '语气不容置疑，低沉而缓慢，一字一顿，包含着绝对的威严和一丝决绝的冷酷，强调后果的严重性。'}, {'台词位置': 30, '语气指导': '含着泪，语速很快地答应，既是害怕也是一种求生的本能，最后一句是急中生智的保证。'}, {'台词位置': 31, '语气指导': '语调沉重、悲伤，带着一丝惋惜，描绘出悟空孤独离去的悲凉画面，为本场景收尾。'}]}, {'场景': 8, '场景剧本': [{'台词位置': 0, '语气指导': '（语气兴奋，充满少年人的惊叹和好奇，语速稍快，音调上扬，像发现了新大陆）'}, {'台词位置': 1, '语气指导': '（语气更加惊讶，带着仔细观察后的赞叹，可以稍微凑近一点的感觉，强调“一模一样”）'}, {'台词位置': 2, '语气指导': '（语气转为大声喝彩，像小粉丝一样激动，带着崇拜和羡慕，语调欢快）'}, {'台词位置': 3, '语气指导': '（语速平稳，前半句带着一丝轻松的叙述感。后半句语速放缓，语调略微降低，营造出紧张感，为祖师出场铺垫）'}, {'台词位置': 4, '语气指导': '（声音洪亮，带着严厉的怒气，像一道惊雷，充满不容置疑的威严，语速中等偏快，每个字都很有力）'}, {'台词位置': 5, '语气指导': '（语速放缓，语气紧张，描述气氛的突然凝固。后半句转为低沉，突出悟空的害怕和心虚）'}, {'台词位置': 6, '语气指导': '（声音变小，带着明显的胆怯和心虚，有点结巴，试图辩解但底气不足）'}, {'台词位置': 7, '语气指导': '（语气带着冷笑和质问，语调尖锐，充满失望。最后的反问句语调上扬，带着逼人的气势）'}, {'台词位置': 8, '语气指导': '（第一句快速否认，带着一丝慌乱。后面转为理直气壮的辩解，带着少年人的委屈和不解）'}, {'台词位置': 9, '语气指导': '（情绪爆发，音量提高，语气严厉，痛心疾首。强调“炫耀的心”，像长辈在教训不懂事的孩子）'}, {'台词位置': 10, '语气指导': '（被打断，声音短促，带着惊慌和不知所措，想要解释却被师父的气场压制）'}, {'台词位置': 11, '语气指导': '（语气从愤怒转为严肃而沉重，语速加快，像在预言一个可怕的未来。说到“灭门之祸”时，语速放缓，一字一顿，充满警告）'}, {'台词位置': 12, '语气指导': '（被“灭门之祸”吓到，语气从震惊转为极度的恐慌和急切，语速飞快，带着哭腔，是在恳求）'}, {'台词位置': 13, '语气指导': '（语气突然变得冰冷、平静，不带一丝感情，每个字都像钉子一样砸下来，充满了决绝和不容商量的意味）'}, {'台词位置': 14, '语气指导': '（语速放缓，语调低沉，充满戏剧性的沉重感，强调悟空遭受巨大打击后的状态）'}, {'台词位置': 15, '语气指导': '（难以置信地反问，接着是彻底的慌乱和绝望的乞求，声音颤抖，带着哭腔，情绪层层递进）'}, {'台词位置': 16, '语气指导': '（语气依旧冰冷，毫无波澜，像是在陈述一个事实，不给对方任何希望）'}, {'台词位置': 17, '语气指导': '（情绪崩溃，是发自内心的哀嚎，带着被抛弃的孩子的无助和悲痛，声音里充满泪水）'}, {'台词位置': 18, '语气指导': '（一声厉喝打断对方，语气强硬、威严，不带愤怒，而是严肃地宣布一项不可违背的命令）'}, {'台词位置': 19, '语气指导': '（声音微弱，气若游丝，充满了被伤害后的迷茫和心碎，是绝望中的低语）'}, {'台词位置': 20, '语气指导': '（语气阴冷而决绝，带着令人不寒而栗的威严，语速放慢，字字清晰，尤其最后一句“听清楚了吗！”音量提高，如当头棒喝）'}, {'台词位置': 21, '语气指导': '（声音颤抖，带着哭音，是彻底死心后的顺从和承诺，充满了悲伤和无奈）'}, {'台词位置': 22, '语气指导': '（声音放轻，带着一丝不易察觉的疲惫和叹息，是最后的告别）'}, {'台词位置': 23, '语气指导': '（语速缓慢，语调悲伤而庄重，描述一个充满仪式感的悲情时刻，引导听众共情）'}, {'台词位置': 24, '语气指導': '（强忍着哭泣，一字一句地说出，声音哽咽但充满真诚的感恩。最后一句几乎是含泪的低语，是最后的告别）'}]}]}

    # print(Emotion)
    # 将语气与剧本结合起来供TTS翻译
    script_with_emotion = combine_script_and_emotion(refine_script, Emotion)
    # print(script_with_emotion)
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
    # Role_Voice_Map(character_gemini, script_with_emotion)