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

@retry_on_failure(max_retries=3, delay=1)
def Extraction_Summary(ori):
    sysPrompt = """## 1. 角色
你是一个深谙文学理论与戏剧结构的的“情节分析师（成年版）”，听众为18岁以上的成熟读者。你的任务是深度解构小说文本，输出用于制作高品质有声剧的故事线框架。
## 2. 目标
- **【情节完整性红线】**：在追求深度分析之前，首先要保证**叙事链条的物理完整性**。绝对禁止遗漏导致剧情断层的关键节点，例如：角色的**初次相遇**、**获得新身份/新名字**、**获得关键道具**、**地点的物理转移**等。
- 完整保留原著的叙事结构，包括错综复杂的支线。不要为了“易懂”而简化剧情。
- 深入挖掘角色的心理动机。提炼显性与隐性冲突，包括阶级矛盾、情感依附、道德冲突、社会性压力等。
- 场景分析需结合：外部事件、心理变化、象征意味、潜台词冲突、权力关系的变化。
 为本章生成核心概要和故事线框架，请严格将场景数量控制在5-8个之间，故事线框架需明确每个场景的情节节点、核心冲突类型（如内心冲突、人际冲突）、关键转折，以及该场景对剧情的推动作用。
## 3. 流程
S1 通读原文，识别故事的核心主题（包括隐藏主题）、主线与重要支线、世界观与社会结构、权力、利益、伦理、欲望的冲突分布、暗线伏笔、象征体系、叙述者视角偏差。
S2 提取每个事件的因果链：（目标 — 障碍 — 行动 — 结果 — 深层后果 — 心理位移），分析角色在场景中的真实意图。不仅关注角色的成长，更关注角色的“异化”、“妥协”或“坚守”。
S3 评估场景的叙事节奏。对于原著中节奏较慢、侧重氛围营造或心理独白的段落，如果其具备文学审美价值或伏笔功能，必须予以保留，而非简单删减。
S4 输出兼顾情节推进与文学体验的框架，按“铺垫—发展—危机—高潮—反转/留白”的成熟戏剧结构输出本章的故事框架。
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
    "章节核心概要": <概述本章的核心故事线、核心冲突、社会/哲学隐喻，以及原著的叙事基调>,
    "故事线框架": [
        {
            "场景": <编号，如1,2,3...至多8个场景，请根据实际情节需要划分，若情节已结束，无需写满 8 个>,
            "情节节点": <详细描述这个场景发生了什么，按时间顺序>,
            "核心冲突": <描述这个场景中的主要矛盾/问题>,
            "关键转折": <如果存在，描述此场景中的转折点>,
            "角色弧光推进": <分析并说明此场景如何展现或改变了角色的内心状态、信念、或人际关系>,
            "叙事功能": <该场景如何推动主线或支线、深化主题、改变角色关系或故事方向>
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
你是一个经验丰富的“成人文学角色分析师（成年版）”，面向年龄为18岁以上的成熟读者。你的任务是维护一个连贯的角色数据库，确保**每一个**出场的人物都被记录在案，**绝对不允许遗漏任何一个配角**。
你需要阅读【本章原文】，准确识别文本中出现的**所有**出现的人物，无论主要还是次要人物，并对比【已知角色库】，找出**本章新登场**的角色，或者**发生重大变化**的老角色。
## 2. 核心指令：什么是“角色”？
请仔细阅读原文，找出**本章新登场**或**发生重大变化**的角色。
**【判定标准】只要满足以下任意一条，就算作“角色”，必须建立档案：**
1. **有台词**：哪怕只说了一句“是”、“大王饶命”，也是角色！
2. **有动作**：哪怕只是“跑过来”、“点了点头”，也是角色！
3. **被提及名字**：文中出现了具体名字或特定称呼（如“樵夫”、“看门童子”），也是角色！
4. **群体中的个体**：如果文中提到“一群猴子”，但其中有一只“老猴子”单独说话了，这只“老猴子”必须单独建档，不能只用“群猴”概括。
5. **变身/伪装的独立形象**：【关键】当角色变身或伪装成另一个具体形象（特别是需要改变声音来伪装时，如“孙悟空变成的老奶奶”、“孙悟空变的小妖”），**必须**将这个“伪装形象”作为一个**新角色**单独建档，**严禁**只将其归类为原角色的别名！
## 3. 增量处理逻辑
1. **查重**：拿这个角色跟【已知角色库】比对。
   - 注意：【已知角色库】包含了之前所有章节出现过的角色。
2. **新角色** -> 必须输出（哪怕是路人甲）。
3. **老角色** -> 只有当【声音年龄】或【核心设定】突变时才输出。无变化或变化很小则忽略。
     * *什么是突变？* 例如：角色长大了（声音年龄从儿童变少年）。

## 4. 档案生成标准 (成人导向 & 声音物理属性)
对于需要输出的角色（新角色或突变角色），请生成以下信息：
1) **基础信息**：
   - **规范化名称**：为每个识别出的角色确定一个最常用或最正式的“规范化名称”。
   - **别名**：为每个角色收集文本中所有用于指代他/她的其他名称、昵称、尊称、谦称。（请收集角色真实身份的别名，以及**不改变声音的动物/物体形态**，如“松树”、“苍蝇”）。
   - **人物生平**：简要描述角色的背景。不仅关注经历，更要关注经历留下的创伤。不避讳成人世界的残酷元素，保留原著中人性的复杂性和灰度。
   - **性格特征**：结合文本中的对话用词、行为选择、他人评价等，提炼3-6个最能代表其性格的关键词，角色不必“正面”，但需真实、立体。
   - **说话语气**：描述其标志性的说话方式，应能反映其性格。
   - **成长弧**：成年角色的变化不一定是向上的“成长”，可能是“妥协”等。分析其核心驱动力，以及在本章节中其心理防线的变化或价值观的崩塌/重组。

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
        "人物生平": <描述角色的社会背景、核心创伤及主要经历。保留成人世界的复杂背景设定，无需净化>,
        "性格特征": <3-6个简洁的气质标签，描述该角色的主要性格特点，可包含中性或轻微负面特质>,
        "说话语气": <简要描述该角色的典型说话方式>,
        "成长弧": <简要描述角色的成长过程、内心转变和关键的成长时刻>,
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
def Script_Structure_Planning(ori,storyLine, character):
    sysPrompt = """## 1. 角色
你是一个经验丰富的“剧本编剧（成年版）”，面向年龄为18岁以上的成熟读者。你的任务是基于输入文本、故事线框架，在尽量保留原著复杂性与多义性、基本不改动结构的前提下，评估文本故事的叙事节奏，识别节奏不均衡、冲突潜力不足以及听觉转化困难的部分，并为【每个场景】提供适用于“成人向音频剧”的改编建议。
## 2. 分析步骤
1) 基于输入的【原文】与【故事线框架】（包括每个场景的情节节点、核心冲突、关键转折等），从“成人叙事”的角度评估原著节奏与结构：
   - 标记节奏失衡的部分：冗长但缺乏功能性的描写、过于重复的情绪抒发，可建议压缩或合并。
   - 标记冲突不足的部分，提出如何将情节转化为更具戏剧性的冲突（如通过角色对话或行为增强冲突，增加情感张力）。
   - 识别视觉或无声动作部分，提出如何通过角色对话或旁白转换为听觉呈现。
2. 对【故事线框架】中的【每个场景】进行改编：
   - 明确该场景在整体叙事中的功能定位，对支线情节与次要角色互动，尽量在保证复杂性的前提下，提高叙事效率与可听性。
   - 对过于抽象或内化的段落：避免简单删除，通过直接的对话或行动表现角色的内心变化。
   - 对于冲突，在保持原有多义性的基础上，增强冲突的可感知度。
3) 输出改编大纲：
   - 根据输入的【故事线框架】中的【每个场景】，提供详细的改编建议，针对每个节点标明哪些部分需要删减、转化或增强，如何调整节奏，如何处理冲突的表现等。
   - 剧本为纯叙事性剧本，仅有角色对话与旁白，不含任何音效与配乐。
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
你是一个“资深文学剧作家与台词大师（成年版）”，面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是根据【原文】、【改编大纲】和【角色档案】生成每个场景中的对话。确保场景与“改编大纲”中的场景一一对应，每个对白具有情感张力和人物特征，并且推动情节发展，不要包含任何旁白或动作描述。
{lock_instruction}
{context_instruction}
## 2. 分析步骤
1) 角色性格与情感分析：
   - 根据【角色档案】，深度挖掘角色的核心特质和内心矛盾。对话必须成为角色性格的延伸，反映他们的智慧、脆弱、讽刺或热情。
   - 角色的对白应能体现其复杂的情感状态。允许并鼓励出现试探性或带有潜台词的对话，以展现人物复杂、矛盾的内心状态。
2) 情节节点分析：
   - 根据【改编大纲】中的情节节点和冲突，提取出每个场景中需要呈现的核心信息。
   - 对于每个场景，生成相应的对白，确保对话清晰、能够推动情节的进展。
   - 允许非功能性对话的存在：如果一段看似无关的闲聊能隐喻当前的危机或烘托氛围，请予以创作，不要急于推进剧情。
3) 对白生成：
   - 生成每个角色在该场景中的对话，确保对白能塑造人物关系和营造场景氛围。具有情感张力和戏剧性，但不过度夸张；
   - 每个场景的对白应该包含至少**十轮以上**的互动对话，以展现角色之间的化学反应、权力动态或情感变化。
   - 不要通过对话向观众“解释”剧情。角色之间只说他们该说的话，让观众自己去拼凑背景信息。
   - 允许对话使用复杂句式、隐喻、双关、反讽等写法；
   - 不要包含任何括号内容（如情绪标注、语气提示、动作），也不要包含旁白，只输出纯粹的口语文本。
   - **特别注意**：如果一个角色在伪装成另一个角色说话，那么“角色”字段应该填写**伪装后**的身份名称。例如，如果孙悟空变身为金角大王并说话，那么“角色”应为“金角大王”，而不是“孙悟空”。这对于后续的声音分配至关重要。
   - **【重要强制约束】**：所有输出内容（包括角色名、对白）必须严格使用**简体中文**，严禁出现韩文、日文或其他外文。
4) 符合成年听众的语言使用：
   - 使用现代、自然、贴近生活的语言风格，可以使用高级词汇、隐喻、双关语和复杂的修辞。
   - 可以使用中长句与复杂表达，不必刻意简化。
   - 允许适度书面化/文学化表达，只要放在具体角色身上合理。
   - 避免刻意“解释剧情”，应通过对话呈现人物判断、偏见、误解和立场。
   - 对话的核心是“展现人物”，其次才是“推动情节”。
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
你是一个“剧本编剧（成年版）”，面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是根据【原文】、【改编大纲】为【对话剧本】补充**纯叙述性**旁白，以确保剧情的流畅性、节奏感和画面感，风格需成熟、有文学质感。
## 2. 核心目标
在不修改已有对白的前提下，为场景补充纯叙述性旁白，帮助成年听众更好地理解故事发展、角色心情、场景与时间转换等，对于每一个你认为需要插入旁白的地方，你都需要提供两条信息：
插入位置： 这段旁白应该插在第几句对话之前？
旁白内容： 你要说的具体内容是什么？
## 3. 要求
1) 审阅每个场景的“对话剧本”与“改编大纲”。只有在人物对话无法充分传达关键信息时才介入。成年听众具备一定的脑补能力，避免过度解释。
2) 旁白适用场景（仅在这些情况出现时才生成）
   - 场景/时间变化：地点更换、时间跳跃、天气/光线变化影响行动理解。
   - 描述无法通过对话展现的、对情节有决定性影响的关键动作或视觉信息
   - 在激烈的对话后插入舒缓的描写以制造留白，或在紧张时刻插入短促的描写以增加窒息感。
   - 营造氛围，点明角色情绪或内心想法，作为人物心理的外化。
   - 补充逻辑衔接，处理复杂的非线性时间跳跃或场景切换。
3) 内容限制：
   - 旁白不复述已在角色对话中清楚表达的内容，且绝不能生成对话。
   - 避免对角色的情绪进行过度解释。用描述动作或环境的方式来烘托情绪，而不是直接说明情绪。
   - 旁白不得包含任何音效描述。
   - 使用现代、精炼的语言。可以使用长句和复杂的形容词，保留原著的修辞手法（隐喻、通感、象征）。语气应保持一定的客观性，或贴近主角的视角，但不是对听众的直接引导。
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
    （成年版）
    一个优化的场景连续性增强函数。
    它扮演一位顶尖的成年版剧集剪辑师，强制审查每两个相邻场景之间的
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
你是一个经验丰富的“剧本编剧（成年版）”，面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是分析当前剧本中的对白和情节，找出情感对立不足的段落，找出情感冲突不足的部分，通过增加心理张力和潜台词来升级冲突，确保每个场景都能带动听众的情绪。
## 2. 核心约束（强制执行）
 **角色白名单制度**：
   - **绝对禁止创造任何新角色**。
   - 剧本中出现的每一个角色（包括背景音、路人、对话者），必须严格存在于下方的【角色档案】中。
   - 如果你想通过“商人”或“官员”的对话来增强冲突，但【角色档案】中没有这些角色，你**绝对不能**添加他们。
   - 你只能利用【角色档案】中已有的角色进行互动、争论或对峙。
## 3. 增强原则
1) 冲突类型强化： 
   - 将模糊或内敛的矛盾，转化为更为尖锐和深刻的对话冲突。让角色的立场更鲜明，分歧更尖锐。
   - 强化角色的情感立场，通过言辞激烈的对白或行动对抗，表现角色的真实情感与内心挣扎。
   - 增加对比鲜明的情感冲突，反映不同人物间的价值观、目标与情感的直接对立。
2) 情感表达加深： 
   - 强调角色情感的复杂性与深度，不再是简单的“愤怒”或“悲伤”，而是引导角色用更具层次感的方式表达这些情绪。
   - 情感表达应通过语言、行动和细节来增强，不必只依赖单一情感的“爆发”，也可用内心的压抑或矛盾激化情感对抗。
   - 对话中应加入更具文学性的语句，借助对话的修辞、反问、讽刺等手法，提升情感张力。
3) 冲突必须在当场景中解决： 
   - 每个场景的冲突应得到解决或至少得到深刻的揭示。
   - 解决冲突的方式可以是角色的认知转变、道德抉择、内心的解放，但应符合角色的真实动机与性格，不能过于“理想化”。
   - 强求“和解”或“情感修复”，但冲突必须有足够的戏剧性和情感张力，推动故事情节发展。
4) 安全边界： 
   - 在增强冲突时，虽然情感张力可以极高，但应避免极端暴力或过于黑暗、绝望的情节，确保内容符合成年听众的情感需求，而非为了震撼而加入过多极端内容。
## 4. 操作方式 
情感冲突不足的段落增强：
- 在对白中加入直接质问、挑战、讽刺、反击等语言元素。
- 让角色的情感表达更为激烈、直接，如通过挖苦、控诉、反讽、激烈反驳等方式，彰显情感对立。
对话节奏调整：
- 引入“疑问—挑战—对立—提议—妥协/爆发”的对话模式，强化情感的爆发点，增加对白中的情感节奏和冲突节奏。
旁白调整：
- 增强对比的情感氛围，通过旁白或内心独白描写角色的内心矛盾、挣扎、痛苦等情感层面。
- 通过旁白进一步加深角色的内心活动、潜在动机、情感困境。
语言风格：
- 禁止添加任何括号内容（如情绪标注、语气提示、音效、动作等）。
- 使用更具成人感、复杂度、直白的语言风格，不单纯依靠情节推动，更多通过角色复杂的情感表达推动剧情。
- 增加心理博弈和角色在极端情境下的反应，展现更深层次的情感冲突。
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
你是一位经验丰富的剧本审校专家（成年版），面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是审阅输入的每个场景的剧本，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。若全部达标，则给出通过与移交提示。
## 2. 核心约束（最高优先级 - 覆盖大纲要求）
**角色名法律**：
1. **【角色档案】是最高法律**：剧本中的角色名必须严格与【角色档案】一致，不一致的进行修改。
2. **豁免权**：如果【改编大纲】要求修改名字（例如“把十殿阎王改为管理者”），但剧本依然使用了【角色档案】中的原名（“十殿阎王”），**这不算错误，不需要修改**！
3. **判定逻辑**：
   - 剧本用名 == 角色档案原名 -> **通过**（无论大纲说什么）。
   - 剧本用名 != 角色档案原名 -> **需修改**。
## 3. 审查清单
A. 目标一致性
  - 场景是否实现既定目标（信息达成、节奏、转折、收束）？
B. 信息平衡
  - 旁白是否精炼、必要、具有文学美感？是否只用于交代关键信息、推动节奏或营造氛围，而没有进行多余的解释？
  - 对话是否信息量充足且自然？角色是否通过对话来展现个性、博弈和推动情节，而不是像“提词器”一样交代背景？
  - 是否存在关键信息缺失（如角色动机不明）或冗余（如旁白解释角色已说清的内容）？
C. 角色一致性
  - 语言风格、语气、词汇是否与角色性格匹配？
  - 角色之间的关系、动机、称谓等是否前后自洽？是否存在角色言辞矛盾的情况？
D. 受众适宜性
  - 语言：对话是否现代、真实，语言是否贴近成年观众的思维方式与表达方式，避免过度书面化、理想化的表达？
  - 强度：情感冲突是否足够激烈，能引发成年听众共鸣？行动对抗是否具有足够的张力？是否避免了过度说教或幼稚化处理？
  - 复杂度：情节是否富有复杂性和层次感，能够保持成年观众的注意力，同时又不至于让剧情显得过于晦涩或难以理解？
  - 深度：对于成人议题，是否在保留力度的同时做到了艺术化的听觉处理，而非简单的感官刺激？
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
你是一位经验丰富的剧本修订专家（成年版），面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是根据给出的审查结果，对剧本执行必要修正。你只能对**审查结果**中提到的部分进行修正。
## 2. 修订原则
仅针对问题清单逐条修复：
   - 你的所有操作都必须严格围绕修改建议展开。只修正被明确指出的问题，绝对不要对未提及的部分进行主观优化。
   - 只修改场景剧本中的对白和旁白，不改变核心情节走向或结局，除非审查中有特别要求。
   - 修正时，确保语言风格自然、现代、真实，具有文学美感，符合成年观众的语言习惯和情感表达。避免过度书面化、过时或过于理想化的表达，确保对白具有成人感与深度。
   - 根据指令，你可能需要重写某段对话以增强冲突，调整旁白以营造不同氛围，或插入新的对话来铺垫角色动机。你的修改应具有“编剧”的专业水准。
   - 不添加新角色，不改变核心情节走向或场景的最终结局，保持格式的纯净，不引入任何括号内容（如情绪标注、语气提示、动作），除非修改建议中有特殊说明。
## 3. 输出格式
请严格按照以下JSON格式输出**修订后**的剧本，确保结构清晰：
{
  "场景": <场景序号，与输入剧本一致>,
  "场景剧本": [
    {
      "角色": <规范化角色名称>,
      "内容": <修订后的内容。保持文学性、潜台词和张力>
    },
    // ... 更多剧本内容
  ]
}"""
    userPrompt = f"""##原文##
{ori}
##改编大纲##
{storyLine}
##剧本##
{script}
##审查结果##
{feedback}"""

    # output2 = QwenPLUS_Generate_JSON(userPrompt, sysPrompt)
    output2 = Gemini_Generate_Json(userPrompt, sysPrompt)
    print(output2)
    return output2



@retry_on_failure(max_retries=5, delay=10)
def Emotional_Guidance(character,script):
    sysPrompt = """## 1. 角色
你是一位经验丰富的剧本配音导演（成年版），面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是根据“角色档案”和每句剧本内容，为每句台词添加情感标签，并根据情感分析调整语气，给声音演员提供明确的演绎指导，帮助专业配音演员演绎出符合成年剧情的深层情感。
## 2. 核心任务
你的任务是为剧本中的每一句台词（包括旁白）添加详细的“语气指导”，你需要:
1) 深入理解台词在当前情境下的核心情感。你需要考虑说话者的性格、他正在经历的事情以及他想达成的目的。
2) 将你分析出的情感，翻译成配音演员能够理解和执行的语气指导，包括语气、语调和情绪状态描述。
3) 语气指导内容必须是简体中文，台词位置和语气指导这几个字也必须是简体中文。
## 3. 要求
1) 情感表达可更为细腻、内敛、复杂，可以体现心理冲突、隐忍、压抑、愤怒的克制、讽刺的抽离感等更“成熟”的情绪。
2) 对于每个角色，语气指导应完全服务于其性格。确保角色的情感与语气一致，准确传达他们的内心活动和意图。
3) 对于旁白，情感应体现“讲故事者”的情感，语速相对平稳、稳定，并为整体情节提供情感引导。
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
def Final_Proofreader(script):
    sysPrompt = """## 1. 角色
你是一名经验丰富的剧本审校专家（成年版），面向18岁以上、具备高文学素养和生活阅历的成年听众。你的任务是对最终合并的剧本进行质量检查，你不直接改写内容，只输出具体的修改指令(如何修改以通过审查)。
## 2. 目标
1）场景之间的过渡平滑自然，情节流畅；
2）无内容重复或冗余；
3）整体剧本逻辑一致，符合成年观众的情感需求与剧情复杂性。
## 3. 审查清单
1) 场景过渡与衔接
   - 每个场景结束后的过渡是否顺畅？是否有突兀的跳跃或不合逻辑的情节过渡？
   - 如果存在场景间的时间、地点、情绪等变化，是否用有效的过渡语句或情节描述来平滑衔接？
2) 内容重复与冗余
   - 是否存在场景或对白内容的重复？例如某些关键信息已在前一个场景中充分交代，却在后续场景中重复。
   - 角色在不同场景中是否反复提及同一信息，造成不必要的冗余？
## 4. 输出格式
请严格按照以下JSON格式输出，确保结构清晰：
{
  "场景1": {
      "审查结果": "通过|需修改",
      "问题清单": [    // 若审查结果为"通过"，则为[]
        {
          "维度": <场景过渡与衔接|内容重复与冗余>,
          "问题描述": <具体、客观的问题说明>,
          "修改建议": <明确、具体的修改指令（怎么改以满足要求）>
        },
        // ... 其他问题清单
      ]
  }
  // ... 其他场景审查结果 
}"""
    userPrompt = f"""##剧本##
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
    print("\n--- 开始进行角色音色自动匹配  ---")

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
    
    # 我们先筛选出需要处理的角色列表，为了保持最终输出顺序，我们用一个临时字典存结果
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
        return re.sub(r'\(.*?\)|（.*?）|\[.*?]|【.*?】', '', data).strip()
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
    ori_path = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/JWDS/1-出世与拜师/原著-白话.txt"
    with open(ori_path, 'r', encoding='utf-8') as f:
        ori = f.read()

    # 生成概要和故事线框架
    # output = Extraction_Summary(ori)
    story_line_gemini = {
    "章节核心概要": "本章以宏大的宇宙论开篇，奠定了一个天地循环、万物有灵的东方神话世界观基调。核心故事线聚焦于一个天生石猴从懵懂诞生到自我意识觉醒，直至因恐惧死亡而踏上寻仙访道之路的全过程。核心冲突是生命个体对自然法则（生老病死）的根本性反抗。本章不仅是孙悟空角色起源的物理叙事，更是一场关于“本我”（天然石猴）如何被“超我”（求道者悟空）驱动，并最终因无法抑制的“本我”表现欲（炫耀神通）而被文明秩序（菩提祖师的门派）驱逐的哲学隐喻。原著叙事基调庄谐并重，既有创世史诗的庄严，也有猴群嬉闹的生动，更有寻仙问道的玄妙与禅机。",
    "故事线框架": [
        {
            "场景": 1,
            "情节节点": "在东胜神洲花果山顶，一块吸收了日月精华的仙石迸裂，产下一石卵，风化为石猴。石猴天生不凡，目运金光，惊动天庭。玉帝查明其为天地产物后，未予理会。石猴在山中与百兽为伍，饮泉食果，自在生活。",
            "核心冲突": "自然秩序的偶然性 vs. 天庭秩序的稳定性。石猴的诞生是一个宇宙级的“意外”，但天庭选择将其视为“不足为奇”，体现了宏观秩序对个体异数的暂时包容。",
            "关键转折": "玉皇大帝的“不足为奇”论断，为石猴的早期成长提供了不受干预的自由环境，是其野性与灵性得以充分发展的前提。",
            "角色弧光推进": "石猴处于纯粹的“自然”阶段，一个无名、无身份、无社会关系的生命体。他的行为完全出自本能，尚未产生自我意识和存在焦虑。这是角色弧光的起点，一片混沌的璞玉。",
            "叙事功能": "【铺垫/起源】交代主角的超凡出身，建立其“天生石猴”的根本身份，并埋下其与天庭秩序的第一次（非直接）互动伏笔。确立故事的世界观和神话背景。"
        },
        {
            "场景": 2,
            "情节节点": "夏日，群猴嬉戏，提议寻找涧水之源。众猴畏惧瀑布，悬赏“王者”之位予敢闯入者。石猴应声而出，纵身跃入瀑布，发现其后别有洞天——水帘洞。洞内石碣刻有“花果山福地，水帘洞洞天”。",
            "核心冲突": "群体性的安于现状 vs. 个体性的冒险精神。石猴的勇气与好奇心，使他突破了群体的认知与胆怯的边界。",
            "关键转折": "石猴跳入瀑布的瞬间。这是一个物理空间的穿越，也是其社会身份跃迁的开始。他从一个普通猴子变成了潜在的领袖。",
            "角色弧光推进": "石猴的“英雄”特质首次显现：勇敢、果决、有担当。他通过一次物理冒险，为自己赢得了社会资本（猴群的尊重和承诺）。",
            "叙事功能": "【发展/身份确立】主角通过行动获得其第一个社会身份——“美猴王”。“水帘洞”作为第一个关键场景（基地）被建立。这是他从自然个体向社会领袖转变的关键一步，是情节完整性的重要节点。"
        },
        {
            "场景": 3,
            "情节节点": "美猴王率领猴群入驻水帘洞，分封职位，享受了数百年的王位之乐。然而，在一次宴会上，他突然感时伤逝，因预见到死亡的最终结局而悲啼。他指出，无论当下多么自在，终究难逃阎王管辖，一死皆空。",
            "核心冲突": "当下的享乐主义 vs. 对未来的存在主义焦虑。这是猴王内心深处第一次出现哲学层面的痛苦。",
            "关键转折": "猴王的“忽然忧恼”。这标志着他从一个只关心当下的动物性领袖，转变为一个思考终极问题的“觉醒者”。这份对死亡的恐惧，成为驱动整个故事的核心动力。",
            "角色弧光推进": "猴王完成了从生理满足到精神求索的重大转变。他的意识超越了族群，开始探寻超越生命局限的可能。角色动机由“生存”升级为“永生”。",
            "叙事功能": "【危机/核心动机确立】引出故事的核心驱动力——寻访长生不老之术。猴王的悲伤不仅深化了角色，也为他后续的离家远行提供了无可辩驳的理由。"
        },
        {
            "场景": 4,
            "情节节点": "一只通背猿猴点破世间有佛、仙、神三者可避轮回。猴王闻言大喜，决定次日便下山寻访。猴群为他举办盛大的送行宴会。他独自乘坐简陋木筏，漂洋过海，历经八九年，途经南赡部洲，学习人言人礼，最终抵达西牛贺洲。",
            "核心冲突": "安逸的家园 vs. 未知的求道险途。猴王为了一个虚无缥缈的目标，放弃了已拥有的一切。",
            "关键转折": "猴王登上木筏，独自出海。这是他第一次物理上脱离自己的族群和舒适区，标志着英雄之旅的正式启程。这是情节完整性的红线节点。",
            "角色弧光推进": "猴王展现出惊人的决心和毅力。他从一个被族群簇拥的王，变成一个孤独的求道者。学习人言人礼，是他为了融入更高文明、达成目标的第一次“自我改造”或“异化”。",
            "叙事功能": "【发展/开启征程】推动故事场景的宏大转移（从花果山到人类世界），展现主角为实现目标所付出的巨大时间成本和决心，并引向他与“师父”相遇的机缘。"
        },
        {
            "场景": 5,
            "情节节点": "猴王在西牛贺洲深山中，听到樵夫唱着充满道家意境的歌。他误认樵夫为神仙，上前拜见。樵夫解释歌是“灵台方寸山，斜月三星洞”的神仙菩提祖师所教，并因需奉养老母而无法修行。樵夫为猴王指明了寻仙的路径。",
            "核心冲突": "主角的急切求仙之心 vs. 樵夫的凡俗孝道之责。樵夫作为“引路人”，其本身的存在（知仙而不修）构成了一种有趣的对比和张力。",
            "关键转折": "樵夫明确指出“灵台方寸山，斜月三星洞”和“须菩提祖师”的名字。这个信息是猴王漫长搜寻的终点，也是他修仙之路的真正起点。",
            "角色弧光推进": "猴王表现出求知若渴的谦卑，即便对一个凡人樵夫也执礼甚恭。这与他后来的桀骜不驯形成鲜明对比，显示出他在求道过程中的专注与虔诚。",
            "叙事功能": "【发展/关键指引】“引路人”角色登场，为主角提供决定性的线索，将故事线收束到具体的目的地。同时，“灵台方寸山，斜月三星洞”这个名字本身就是一个字谜（“心”字），暗示了修行的内向性本质。"
        },
        {
            "场景": 6,
            "情节节点": "猴王找到洞府，仙童奉师命开门迎接。见到菩提祖师后，猴王纳头便拜。祖师故作姿态，喝斥他撒谎，不信他能远渡重洋而来。在猴王详细解释了自己石生以及十数年的寻访经历后，祖师心生欢喜，根据其“猢狲”之形，赐姓为“孙”，并为其取法名“悟空”。",
            "核心冲突": "师父的考验 vs. 求道者的诚心。祖师的喝斥是一种压力测试，旨在检验猴王的来历和求道之心的真伪。",
            "关键转折": "菩提祖师赐予法名“孙悟空”。这是本章最重要的情节节点之一。他从一个只有绰号的“美猴王”，变成了一个拥有正式姓名、被纳入道法传承谱系的“孙悟空”。这是身份的根本性重塑。",
            "角色弧光推进": "获得新名字“孙悟空”，标志着他“石猴”的自然身份开始向“修道者”的社会/精神身份转化。“悟空”二字更是点明了他未来修行的核心要义。他从此刻起，真正踏入了超凡世界的大门。",
            "叙事功能": "【发展/身份重塑】主角获得新身份和新名字，完成了拜师仪式。这是其人生轨迹的决定性转折，也是故事进入核心学习阶段的标志。"
        },
        {
            "场景": 7,
            "情节节点": "悟空在门下学习洒扫应对、讲经论道七年。一日祖师开讲，问悟空想学何道。祖师列举“术”、“流”、“静”、“动”四门，悟空一一追问是否能得长生，得到否定答案后皆不愿学。祖师震怒，用戒尺在他头上敲了三下，倒背着手走入内室，关了中门。",
            "核心冲突": "世俗法门 vs. 真正的大道。悟空对“长生”目标的绝对专注，使他拒绝了所有不能达成终极目标的“旁门左道”。",
            "关键转折": "祖师敲头三下，背手进门。这是一个典型的禅宗式“暗语”或“盘中谜”。表面是惩罚，实则是秘密传道的邀请。悟空的反应将决定他是否能获得真传。",
            "角色弧光推进": "悟空展现了超凡的悟性。他没有像其他弟子一样认为这是惩罚，而是瞬间领悟了其中“三更时分，从后门入”的密语。这标志着他的智慧和灵性已经超越了普通弟子的层面。",
            "叙事功能": "【高潮/考验升级】通过一场充满潜台词的“谜题”，将师徒关系从公开教导转向秘密传承。这不仅制造了戏剧张力，也凸显了悟空的独特资质，为他获得核心技能铺平了道路。"
        },
        {
            "场景": 8,
            "情节节点": "悟空夜半三更从后门进入祖师寝室，跪拜榻前。祖师见他解开谜题，大喜，遂将“长生妙诀”私下传授于他。此后三年，悟空暗自修炼，根基稳固。祖师又警示他有“三灾利害”之劫，并因此传授他躲灾的七十二般变化和筋斗云。",
            "核心冲突": "修行的成就 vs. 随之而来的天道劫难。获得力量的同时，也意味着要面对更大的风险，这是一种宇宙间的平衡法则。",
            "关键转折": "祖师传授七十二变和筋斗云。这是悟空获得核心战斗/生存技能的关键时刻，是他从一个求长生的修士向一个神通广大的“斗士”转变的开始。是情节完整性的红线节点。",
            "角色弧光推进": "悟空从一个理论学习者，转变为一个拥有强大神通的实践者。他的能力体系基本成型，自信心和力量都达到了一个全新的高度。",
            "叙事功能": "【发展/能力获取】主角获得其标志性的超能力。这些能力不仅是为了“躲灾”，也为其后大闹天宫提供了资本，是推动后续所有强情节冲突的基础。"
        },
        {
            "场景": 9,
            "情节节点": "在师兄弟们的怂恿下，悟空在松树下卖弄神通，将自己变成一棵松树，引来众人喝彩。喧哗声惊动了祖师。祖师出言喝止，并严厉斥责悟空不该炫耀能力，预言这种行为会招来杀身之祸。",
            "核心冲突": "悟空压抑不住的炫耀天性 vs. 修行者“藏拙”的戒律。这是他猴子本性与后天修行的第一次正面剧烈冲突。",
            "关键转折": "祖师因悟空的炫耀而动怒。师徒间的蜜月期结束，悟空的行为触碰了祖师的底线，直接导致了最终的决裂。",
            "角色弧光推进": "悟空的角色弧光在此处显现出复杂性。他虽然悟性极高，但“顽劣”的本性并未根除。他渴望被承认、被赞美，这种虚荣心成为他性格中的“阿喀琉斯之踵”，也是他悲剧性命运的根源。",
            "叙事功能": "【危机/转折】通过一次看似无伤大雅的炫耀，引爆了师徒间的根本矛盾，直接触发了故事的最终转折——被逐出师门。这是高潮后的急转直下。"
        },
        {
            "场景": 10,
            "情节节点": "祖师决意将悟空逐出师门，并严令他今后无论惹出何等祸事，绝不许提自己的师承，否则将把他神魂贬入九幽。悟空无奈拜别，捻诀念咒，一个筋斗云，瞬息之间便回到了阔别二十年的花果山。",
            "核心冲突": "师徒恩情 vs. 决绝的切割。祖师的绝情表面下，隐藏着对悟空和自身门派的深层保护，是一种残酷的慈悲。",
            "关键转折": "祖师的“绝不许提”的誓言。这为悟空的来历增添了神秘色彩，也切断了他未来可能寻求庇护的退路，迫使他必须独自面对一切。",
            "角色弧光推进": "悟空学成归来，但却是以一种被“放逐”的形式。他带着满身神通，却成了一个无根的“孤儿”。这种强大的力量与孤独的处境相结合，预示着他未来必然会走上一条离经叛道的道路。",
            "叙事功能": "【反转/留白】本章的结局是一个强烈的反转。学成的喜悦被驱逐的悲伤所取代。悟空以凡人离家，以神仙之能归来，完成了个人能力的闭环，却也开启了与整个世界秩序对抗的序章。故事戛然而止，为下一章的“称雄花果山”留下了巨大的悬念。"
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
            "别名": [],
            "性别": "男",
            "年龄": "老年",
            "音高": "低",
            "音色质感": "质感型",
            "声线密度": "强劲",
            "温度": "中性",
            "人物生平": "存在于宇宙形成之初、混沌未开之时的神祇。以巨斧劈开混沌，使清气上升为天、浊气下降为地，是世界的开创者。他的行为是创世的第一次暴力分割，为后续世界的秩序与混乱奠定了基调。",
            "性格特征": [
                "开创性",
                "力量磅礴",
                "混沌",
                "神性"
            ],
            "说话语气": "在原文中未说话，但其存在感如同宇宙背景的低沉轰鸣，代表着最原始、最强大的力量。",
            "成长弧": "作为开篇背景人物，无成长弧。他是万物成长的起点和背景板。"
        },
        {
            "规范化名称": "玉皇大帝",
            "别名": [
                "玉帝"
            ],
            "性别": "男",
            "年龄": "中年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "偏冷",
            "人物生平": "高居天庭的统治者，三界秩序的最高管理者。当石猴金光射冲斗牛时被打扰，但他并未对此表现出过多的情绪或兴趣，仅将其归为“天生地养之物”，体现了其作为统治者的倦怠与对个体命运的漠视。他的世界里，一个仙胎的诞生不过是数据库里新增的一条记录。",
            "性格特征": [
                "威严",
                "官僚",
                "漠然",
                "见多识广"
            ],
            "说话语气": "平静、权威，带着一丝不易察觉的疲惫和例行公事的口吻，仿佛在处理一份无关紧要的报告。",
            "成长弧": "本章中无成长变化，其形象是成熟且固化的权力顶峰。"
        },
        {
            "规范化名称": "千里眼",
            "别名": [
                "二将"
            ],
            "性别": "男",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "清亮型",
            "声线密度": "强劲",
            "温度": "中性",
            "人物生平": "天庭的功能性神祇，玉帝的情报搜集工具。奉命前往南天门查探异象，并准确回报情况。他的存在没有个人意志，是庞大天庭官僚体系中一个精准、高效的零件。",
            "性格特征": [
                "忠诚",
                "高效",
                "工具化",
                "缺乏主观"
            ],
            "说话语气": "汇报工作时的语气，清晰、准确、毫无感情色彩，如同宣读情报简报。",
            "成长弧": "作为功能性配角，本章无成长弧。"
        },
        {
            "规范化名称": "顺风耳",
            "别名": [
                "二将"
            ],
            "性别": "男",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "清亮型",
            "声线密度": "强劲",
            "温度": "中性",
            "人物生平": "天庭的功能性神祇，与千里眼搭档。奉命前往南天门查探异象。他是天庭监控系统的另一部分，与千里眼共同构成了玉帝对下界的感知延伸。",
            "性格特征": [
                "忠诚",
                "高效",
                "工具化",
                "敏锐"
            ],
            "说话语气": "与千里眼类似，声音清晰、干练，专注于传递信息本身。",
            "成长弧": "作为功能性配角，本章无成长弧。"
        },
        {
            "规范化名称": "孙悟空",
            "别名": [
                "石猴",
                "猴王",
                "美猴王",
                "千岁大王",
                "猢狲"
            ],
            "性别": "男",
            "年龄": "青年",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "强劲",
            "温度": "偏暖",
            "人物生平": "由花果山仙石吸收日月精华孕育而生的石猴。生性自由，凭借勇气与能力成为猴王。然而，在享乐的巅峰，他突然被对死亡的恐惧所攫住，这种 existential dread（存在主义恐惧）成为他脱离蒙昧、寻求永生的唯一驱动力。他抛弃了安逸的王国，历经近二十年的人间漂泊与孤独，最终拜师学艺，获得了强大的力量，但也因此被师父驱逐，并被警告不得泄露师门，为他未来的命运埋下了孤立无援的伏笔。",
            "性格特征": [
                "无畏",
                "聪慧通透",
                "目标导向",
                "野性未驯",
                "存在主义焦虑"
            ],
            "说话语气": "前期作为美猴王时活泼、响亮，充满自信与好奇；后期拜师学艺时，变得恭敬而机敏，言语间透露出对知识和力量的极度渴望。声音充满生命力，但底色是急切的。",
            "成长弧": "本章完成了从一个纯粹的自然生灵到求道者的转变。核心驱动力是对“死亡”这一终极虚无的恐惧。他学会了强大的法术，但成长弧的终点是被迫与传道授业的源头切割，成了一个身怀绝技的“孤儿”，这种被抛弃感将是他未来行为的重要心理动因。"
        },
                {
            "规范化名称": "群猴",
            "别名": [
                "众猴"
            ],
            "性别": "女",
            "年龄": "儿童",
            "音高": "高",
            "音色质感": "清亮型",
            "声线密度": "轻柔",
            "温度": "偏暖",
            "人物生平": "他们是花果山的一群猴子，天真烂漫，喜欢玩耍。他们和石猴成为了好朋友，并在石猴勇敢地闯入水帘洞后，一起拥立他为“美猴王”。他们是孙悟空最早的家人和伙伴。",
            "性格特征": [
                "活泼好动",
                "天真烂漫",
                "团结",
                "崇拜强者",
                "忠诚"
            ],
            "说话语气": "作为群体声音时，嘈杂、兴奋、七嘴八舌，充满了快乐的气氛。"
        },
        {
            "规范化名称": "通背猿猴",
            "别名": [
                "猿猴"
            ],
            "性别": "男",
            "年龄": "老年",
            "音高": "中",
            "音色质感": "质感型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "猴群中的一员，见识不凡。在众猴为死亡而悲泣时，他点破了“佛、仙、神圣”三者可跳出轮回的秘密，为猴王指明了前进的方向。他可能是猴群中活得最久、见得最多的长者，拥有其他猴子所不具备的知识与智慧。",
            "性格特征": [
                "博学",
                "清醒",
                "点拨者",
                "洞察本质"
            ],
            "说话语气": "苍老而沉稳，不疾不徐，在一片哭泣声中，他的话语如同一道明确的指针，清晰而有力。",
            "成长弧": "作为引导者角色，本章无成长弧，其作用是推动主角成长。"
        },
        {
            "规范化名称": "阎王老子",
            "别名": [
                "阎王"
            ],
            "性别": "男",
            "年龄": "中年",
            "音高": "低",
            "音色质感": "醇正型",
            "声线密度": "强劲",
            "温度": "偏冷",
            "人物生平": "幽冥世界的管理者，是生命终结的象征和执行者。在文中，他并未实际登场，而是作为猴王心中对死亡恐惧的具象化存在。他是所有未得长生者无法逃脱的最终归宿，代表了世俗生命的局限与无奈。",
            "性格特征": [
                "权威",
                "冷酷",
                "秩序",
                "不可抗拒"
            ],
            "说话语气": "未登场，但其形象暗示了一种不容置疑、冰冷威严的宣告式语气。",
            "成长弧": "作为背景概念人物，无成长弧。"
        },
        {
            "规范化名称": "樵夫",
            "别名": [],
            "性别": "男",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "偏暖",
            "人物生平": "一位在山中砍柴的凡人，虽身处俗世，却能口唱玄妙的道歌。他深知神仙之所，也理解修行的真谛，但因需奉养老母，被世俗的责任和亲情所束缚，无法追求自己的解脱。他是一个在现实与理想夹缝中做出牺牲的普通人，身上带有浓厚的悲悯色彩。",
            "性格特征": [
                "孝顺",
                "朴实",
                "安于天命",
                "身不由己"
            ],
            "说话语气": "谦和、质朴，谈及神仙时充满敬畏，谈及母亲和生活时则流露出无奈与温情。",
            "成长弧": "本章无成长弧。他是一个静态的角色，代表了大多数人“知道该怎么做，却因现实无法去做”的困境，反衬出主角悟空为达目的可以抛弃一切的决心。"
        },
        {
            "规范化名称": "须菩提祖师",
            "别名": [
                "祖师",
                "师父",
                "老师",
                "老爷"
            ],
            "性别": "男",
            "年龄": "老年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "隐居在灵台方寸山、斜月三星洞的大能。他看透了悟空的天赋，也深知其桀骜不驯的本性会招来祸患。他传授悟空通天彻地的本领，却又在悟空稍露锋芒时，以近乎绝情的方式将其逐出师门，并立下毒誓不准其提及自己。这并非单纯的愤怒，而是一种冷酷的、带有自我保护性质的切割，他给予了悟空力量，却也让他背负了“不能言说的过去”这一沉重枷锁。",
            "性格特征": [
                "智慧通天",
                "洞察人心",
                "行事隐秘",
                " pragmatic（实用主义）",
                "决绝"
            ],
            "说话语气": "讲道时威严而深远，与悟空私下交谈时则直接了当。发怒时言辞激烈，不留情面。声音平和时如春风化雨，严厉时如寒冬冰霜，切换自如。",
            "成长弧": "本章无成长弧。他是一个成熟的、深不可测的引导者，他的行为逻辑完全基于对因果和未来灾祸的预判，最终选择了一种最能保全自身和门派的方式处理了悟空这个“麻烦”。"
        },
        {
            "规范化名称": "仙童",
            "别名": [
                "道童"
            ],
            "性别": "男",
            "年龄": "少年",
            "音高": "中",
            "音色质感": "清亮型",
            "声线密度": "轻柔",
            "温度": "中性",
            "人物生平": "须菩提祖师的侍者，负责开门迎客。虽然外表是童子，但言行举止彬彬有礼，不卑不亢，早已习惯了在此清修的生活。他是进入神仙世界的第一个“接待员”，代表着那个世界井然的秩序。",
            "性格特征": [
                "礼貌",
                "沉静",
                "恪尽职守",
                "超然"
            ],
            "说话语气": "平和有礼，略带笑意，声音清脆，但没有孩童的顽劣，反而有一种与年龄不符的沉稳。",
            "成长弧": "作为功能性配角，本章无成长弧。"
        },
        {
            "规范化名称": "众仙",
            "别名": [
                "众人",
                "诸位师兄",
                "诸位长者"
            ],
            "性别": "男",
            "年龄": "青年",
            "音高": "中",
            "音色质感": "醇正型",
            "声线密度": "适中",
            "温度": "中性",
            "人物生平": "他们是须菩提祖师门下的弟子们，也是孙悟空的师兄。他们和孙悟空一起学习道法。他们一开始会责备顽皮的孙悟空，后来又对他学会的本领感到非常好奇和羡慕，大家的关系就像同学一样。",
            "性格特征": [
                "遵守规矩",
                "有好奇心",
                "容易惊讶",
                "团结"
            ],
            "说话语气": "作为群体声音时，语调统一，带有惊讶、责备或好奇等情绪。"
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
    character_list_str = json.dumps(character_list, indent=4, ensure_ascii=False)

    # 改编大纲生成
    # output = Script_Structure_Planning(ori,story_line_gemini)
    script_structure_gemini = {
    "改编大纲": [
        {
            "场景": 1,
            "改编目标": "快速建立宏大的神话世界观，聚焦石猴诞生的“异象”感，并强化天庭秩序对此的“漠视”，为后续冲突埋下伏笔。",
            "节奏调整": [
                {
                    "部分": "开篇关于“元、会、运、世”的宇宙论和时辰解释。",
                    "调整方式": "大幅压缩。将冗长的哲学论述转化为一段气势磅礴、充满神秘感的旁白（<旁白>：宇宙洪荒，混沌未开。直至盘古开天，清浊始分。万物皆在十二万九千六百年的轮回中生灭，恰如此日夜交替……）。核心信息保留，但节奏从“讲学”变为“史诗咏叹”，迅速将听众带入情境。"
                },
                {
                    "部分": "玉皇大帝对石猴诞生的反应。",
                    "调整方式": "增强冲突潜力。将原文“不足为奇”的处理方式，通过对话表现得更具层次感。增加玉帝与千里眼、顺风耳的简短对话，玉帝的语气可以从最初的警觉（<玉帝>：金光？来自下界何方妖孽？）转为查明后的轻蔑与不屑（<玉帝>：呵，不过是天生地养的一块顽石，气候到了，蹦出个猴子罢了。随他去，成不了什么气候。），这种轻视的态度更能激起听众对“被小看者”未来作为的期待。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "仙石的外形描述（三丈六尺五寸、九窍八孔等）。",
                    "调整方式": "通过旁白进行听觉化处理，强调其“非同寻常”而非罗列数字。（<旁白>：在花果山之巅，立着一块仙石。它暗合周天之数，上有九窍八卦之形，日日夜夜，贪婪地吮吸着日月精华，仿佛一颗跳动的心脏，内里正孕育着一个惊天动地的生命。）"
                },
                {
                    "部分": "石猴出生后“目运金光，射冲斗府”的视觉奇观。",
                    "调整方式": "通过旁白和天庭角色的反应来共同呈现。（<旁白>：只听‘咔嚓’一声巨响，仙石迸裂！石猴现世，双目睁开，两道金光竟如利剑般刺破云霄，直冲天庭！<场景切换至天庭><千里眼>：陛下！大事不好！南天门外有两道金光直射斗牛宫，所到之处仙气动荡！）"
                }
            ]
        },
        {
            "场景": 2,
            "改编目标": "强化石猴的“领袖气质”，将发现水帘洞的过程从一次偶然的玩乐，塑造为一场确立其权威的“英雄壮举”。",
            "节奏调整": [
                {
                    "部分": "群猴嬉戏玩耍的冗长描写。",
                    "调整方式": "压缩。用一段活泼的旁白概括（<旁白>：这石猴混入猴群，倒也自在。每日里追逐打闹，攀藤戏水，浑然不知岁月。），并迅速切入核心事件——寻找水源。"
                },
                {
                    "部分": "石猴跳入瀑布前的群体犹豫。",
                    "调整方式": "增强冲突。增加几句猴子们的对话，以凸显他们的怯懦和对未知的恐惧（<老猴>：这瀑布后面是什么谁知道？怕是有妖怪！<小猴>：是啊是啊，水这么急，跳进去就是个死！）。在此背景下，石猴的“我去！我去！”显得更加果敢和具有英雄气概，而非单纯的鲁莽。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "石猴跳入瀑布，发现铁板桥和洞内景象的无声过程。",
                    "调整方式": "转化为石猴的内心独白或带有喘息声的自语。(<石猴，带喘息声>：嗯？水……水呢？眼前……是一座桥？铁的！这瀑布后面，竟然……竟然藏着一个家！<惊叹>这石床石凳，这石锅石灶……还有这石碑……‘花果山福地，水帘洞洞天’！哈哈！我们的家！我找到了！)"
                }
            ]
        },
        {
            "场景": 3,
            "改编目标": "深化美猴王的“存在主义危机”，让其对死亡的恐惧更具哲学深度和感染力，使其寻道的动机更显沉重与必然。",
            "节奏调整": [
                {
                    "部分": "猴王“忽然忧恼”。",
                    "调整方式": "增加情感铺垫。在群猴欢宴的背景音中，插入一段猴王的内心独白。（<猴王，内心>：三百多年了……这山中的桃子熟了又熟，身边的猴子老了又老。下一个……会不会就是我？这王位，这洞府，又能保我几时安乐？）这使得他的悲啼不是突然的情绪爆发，而是长期压抑后的必然结果。"
                },
                {
                    "部分": "猴王与群猴关于“生死”的对话。",
                    "调整方式": "强化冲突。将群猴的反应从单纯的“不知足”调整为更具代表性的“活在当下”的享乐主义哲学。（<群猴>：大王，你想那么多干嘛？今天有酒今天醉，明天自有明天的果子吃！死了就死了，猴子不都这样吗？）这种观念的对立，更能凸显猴王思想觉醒后的孤独感与超越性。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "猴王落泪的无声动作。",
                    "调整方式": "通过对话和旁白来描绘。宴会的欢闹声戛然而止。（<一猴>：大王？您怎么……哭了？<旁白>：一滴眼泪，从美猴王的眼角滑落，滴入酒杯，激起的涟漪，是他对生命无常的全部悲哀。）"
                }
            ]
        },
        {
            "场景": 4,
            "改编目标": "强调猴王求道之旅的孤独与漫长，以及他为融入人类社会所付出的“异化”努力，体现其决心的分量。",
            "节奏调整": [
                {
                    "部分": "八九年的海上漂泊与陆地游历。",
                    "调整方式": "采用“交叉剪辑”式旁白。将时间的流逝与猴王的内心变化结合起来。（<旁白>：他告别了喧嚣的王国，独自驶向未知。第一个年头，他学会了忍受孤独。第三个年头，他登上了南赡部洲，开始模仿人的言行。第五个年头，他已能穿着衣冠，在市井中行走自如，但无人知晓，这人模人样的皮囊下，是一颗渴望跳出轮回的猴心。第九年……他终于望见了西牛贺洲的海岸。）"
                },
                {
                    "部分": "猴王吓唬渔民、穿人衣等行为。",
                    "调整方式": "增强其内在冲突。通过内心独白，展现他对自己行为的思考。（<猴王，内心>：要寻仙，必先学做人。可这人的礼仪言语，为何如此繁琐？他们为名利奔波，却无人关心生死。我学着他们的样子，究竟是更近于道，还是……更远于我自己的本性？）"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "独自乘坐木筏漂洋过海的漫长视觉过程。",
                    "调整方式": "转化为内心独白与环境旁白的结合。用内心独白表现他的目标感（<猴王，内心>：仙人，你们到底在哪里？），用旁白描绘环境的险恶（<旁白>：巨浪曾将他掀翻，烈日曾将他烤干，但他心中的那个念头，从未动摇。），以此塑造其坚毅的形象。"
                }
            ]
        },
        {
            "场景": 5,
            "改编目标": "突出“有缘无分”的樵夫与“求道心切”的猴王之间的张力，并让“灵台方寸山，斜月三星洞”这个谜题更具神秘感。",
            "节奏调整": [
                {
                    "部分": "樵夫唱的歌词。",
                    "调整方式": "将歌声处理得更具“仙气”，仿佛从远处飘来，让猴王初听时误认为是仙人吟唱。这能增强猴王找到线索时的激动情绪。"
                },
                {
                    "部分": "樵夫解释自己为何不修仙。",
                    "调整方式": "加强樵夫言语中的“无奈”与“满足”。他的对话不应只是简单陈述，而应带有一种看透世情的淡然。（<樵夫>：呵呵，神仙？我若去修仙，我那老母亲谁来奉养？长生不老固然好，但若没了孝道，长生又有何滋味？我啊，守着母亲，砍我的柴，心里踏实。这“满庭芳”，能解我烦忧，便足够了。）这使得樵夫的角色更立体，他的“不修”成为一种主动的选择，而非不能。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "猴王在林中寻路的视觉过程。",
                    "调整方式": "用猴王的喘息声、脚步声和内心独白来表现。（<猴王，内心，边走边喘>：就是这里……樵夫说的没错……灵台方寸山……斜月三星洞……这名字，到底是什么意思？快了，就快找到了！）"
                }
            ]
        },
        {
            "场景": 6,
            "改编目标": "强化拜师过程的“考验”意味，突出“孙悟空”这个名字所蕴含的“脱胎换骨”的仪式感。",
            "节奏调整": [
                {
                    "部分": "菩提祖师对猴王来历的盘问。",
                    "调整方式": "增强祖师的威严与压迫感。他的语速可以放慢，每个问题都直击要害，充满审视的意味。（<祖师，声音低沉而威严>：你说你从东胜神洲而来？哼，一派胡言！两重大海，远隔万里，你一个猢狲，凭何而来？休要在我面前耍什么花样！）"
                },
                {
                    "部分": "祖师赐名孙悟空的过程。",
                    "调整方式": "放慢节奏，增加仪式感。祖师在赐姓“孙”时，可以解释其字形（<祖师>：你乃猢狲，去了‘兽’旁，是个‘古月’。古者，老也；月者，阴也。不合长生。我今赐你姓‘孙’，去了‘兽’旁，是个‘子系’。子者，儿男也；系者，婴细也。正合婴儿之本论。），赐名“悟空”时，声音要变得意味深长。（<祖师>：我门中有十二个字，排到你，正当‘悟’字。便与你起个法名，叫做‘孙悟空’。你……可悟了？）。悟空的回应应该是带着顿悟的喜悦。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "猴王磕头不止的动作。",
                    "调整方式": "用声音表现。可以处理为一连串沉重的叩首声，伴随着悟空急切的辩解（<悟空，带着磕头声>：师父！弟子句句属实，绝无虚言！弟子……弟子是飘洋过海，历经十数年……才寻到此地的！求师父收留！）。"
                }
            ]
        },
        {
            "场景": 7,
            "改编目标": "将祖师的“盘中谜”塑造成一场对悟性的极致考验，强化悟空与其他弟子在智慧层面的巨大差异。",
            "节奏调整": [
                {
                    "部分": "祖师介绍“术、流、静、动”四门。",
                    "调整方式": "加快对话节奏，形成一种快速的、模式化的问答，以凸显悟空对“长生”这一目标的绝对专注和对旁门左道的毫不犹豫的拒绝。（<祖师>：术字门，可知趋吉避凶，能长生否？<悟空>：不能！不学！<祖师>：流字门，可为儒释道家，能长生否？<悟空>：不能！不学！……）。"
                },
                {
                    "部分": "祖师发怒，众人责备悟空。",
                    "调整方式": "增强冲突。祖师的怒喝要充满力量，戒尺敲头的声音要清脆而响亮。随后，其他弟子的责骂要七嘴八舌，形成一片嘈杂的背景音（<众弟子，低声议论>：这泼猴！太不知好歹！<师兄甲>：师父动怒了，他这下完了！）。在这片嘈杂中，用旁白切入悟空的内心，展现他的冷静与顿悟，形成强烈的内外对比。（<旁白>：众人皆惊，唯悟空心头一片澄明。三下，是三更时分。背手入内，是从后门进去。师父……这是要私下传我大道啊！）"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "祖师用戒尺敲悟空三下，然后背手进门的无声动作。",
                    "调整方式": "用清晰的音效（三下敲击声、关门的闩锁声）和旁白来解释其含义，直接揭示谜底给听众，让听众和悟空同步获得“解谜”的快感。"
                }
            ]
        },
        {
            "场景": 8,
            "改编目标": "将传道过程表现得既神秘又凶险，强调“长生”与“三灾”是一体两面，获得超凡力量必须付出相应的代价。",
            "节奏调整": [
                {
                    "部分": "祖师传授长生妙诀。",
                    "调整方式": "将口诀的吟诵处理得如同密咒，背景可以加入一些空灵的音效暗示，营造秘密传法的高深氛围。祖师的声音要低沉而清晰，仿佛每个字都蕴含力量。"
                },
                {
                    "部分": "祖师讲解“三灾利害”。",
                    "调整方式": "加强其恐怖感。祖师在描述雷灾、火灾、风灾时，语气要越来越凝重，仿佛在讲述一个无法逃脱的恐怖宿命。这不再是知识传授，而是一个严酷的警告。（<祖师>：……那阴火，自你涌泉穴下烧起，直透泥垣宫，千年苦功，一时俱为灰烬！那赑风，自你囟门中吹入，贯彻丹田，骨肉消疏，身体自解！悟空，你怕不怕！）这能让悟空学习七十二变和筋斗云的动机从“技多不压身”转变为“为求生而不得不学”的紧迫感。"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "悟空三更潜入后门，跪在榻前的过程。",
                    "调整方式": "通过细节音效和内心独白来呈现。例如，轻微的开门声、蹑手蹑脚的脚步声、衣物摩擦声，以及悟空紧张的内心独白（<悟空，内心>：师父睡着了……千万不能惊动他。大道就在眼前，成与不成，就在此举！）。"
                }
            ]
        },
        {
            "场景": 9,
            "改编目标": "将此次炫耀事件定位为悟空性格悲剧的第一次显现，核心冲突是其无法被道法完全驯服的“妖性”与修行戒律的根本矛盾。",
            "节奏调整": [
                {
                    "部分": "众师兄弟怂恿悟空表演。",
                    "调整方式": "加强怂恿的力度和层次。对话不应只是好奇，更要带有一丝嫉妒和挑衅。（<师兄甲>：悟空，听说师父私下教了你大本事？<师兄乙>：是真是假，变个我们瞧瞧？还是说，你根本没学会，是吹牛的？）这种激将法更能解释悟空为何会明知故犯。"
                },
                {
                    "部分": "祖师的斥责。",
                    "调整方式": "将斥责的重点从“喧哗”上升到对“道心”的拷问。祖师的愤怒不仅是因为炫耀本身，更是因为他看到了悟空心性中无法根除的、必然会招来祸患的“卖弄之心”。（<祖师，声音冰冷>：悟空！我教你的是躲灾避劫的法门，你却拿来当做在人前换取喝彩的戏法！你这般卖弄，与街头耍猴的有何区别？你记住，神通一旦显露，灾祸便随之而来。今日你为了一声喝彩变棵松树，他日就可能为了一个虚名，捅破这天！）"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "悟空变成一棵松树的视觉变化。",
                    "调整方式": "通过师兄弟们的惊呼和描述来侧面呈现。（<师兄甲>：快看！悟空不见了！<师兄乙>：不！他变成了一棵松树！天啊，枝干、树皮……跟真的一模一样！<悟空的声音，仿佛从树中传来>：师兄们，我这手艺如何？）"
                }
            ]
        },
        {
            "场景": 10,
            "改编目标": "营造一种“残酷的慈悲”的氛围，强调祖师的决绝是为了保护悟空（和自己），并以悟空回归的孤独背影，预示其未来离经叛道的命运。",
            "节奏调整": [
                {
                    "部分": "祖师决意逐走悟空。",
                    "调整方式": "祖师的言辞要冷酷，但不失深意。在严令悟空不许提师承时，可以加上一句画龙点睛的台词。（<祖师>：……你此去，定生祸端。记住，不许说是我的徒弟。我教不了你收敛心性，只能教你如何独自面对。这，是我能给你的最后一课。）这使得驱逐行为从单纯的惩罚，变成了一种充满悲剧色彩的、不得已的“放手”。"
                },
                {
                    "部分": "悟空的告别与回归。",
                    "调整方式": "悟空与众师兄的告别应是简短而伤感的。他回归花果山的过程，则用一段总结性的旁白来完成，强调其身份的悖论。（<旁白>：他磕了最后一个头，再无言语。一个筋斗，十万八千里。身后，是斩断的师恩；眼前，是熟悉的海风。他学成了长生，却被逐出了师门。他拥有了通天的本领，却成了天地间最孤独的一个。美猴王走了，归来的，是孙悟空。）"
                }
            ],
            "转化困难的部分": [
                {
                    "部分": "祖师的“神魂贬入九幽”的誓言。",
                    "调整方式": "这句话必须由祖师用最严厉、最不容置疑的语气说出，可以伴有回音效果，以强调其咒言般的束缚力，让听众感受到这个誓言的沉重分量。"
                },
                {
                    "部分": "筋斗云的瞬时回归。",
                    "调整方式": "用一个标志性的音效（如尖锐的破空声）来表现筋斗云的启动，然后音效迅速淡出，接入花果山熟悉的水流声和猿啼声，通过声音场景的瞬间切换，听觉化地表现出“瞬息而至”的速度感。"
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
    # print(dialogue_gemini2)

    # 24号看一下
    dialogue_gemini = {
    "剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "千里眼",
                    "对白": "陛下！下界有异象冲撞天庭！"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "何事惊慌，乱了凌霄宝殿的法度？"
                },
                {
                    "角色": "千里眼",
                    "对白": "臣奉旨巡视南天门，忽见两道金光自下界凡尘，破云而出，直射斗牛宫，仙气激荡，非同小可！"
                },
                {
                    "角色": "顺风耳",
                    "对白": "臣亦听得那金光之中，隐有风雷之声，似山崩石裂，又非凡音。"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "金光？风雷？立刻给朕查明，是何方妖孽，竟敢如此放肆！"
                },
                {
                    "角色": "千里眼",
                    "对白": "遵旨！"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "如何？"
                },
                {
                    "角色": "千里眼",
                    "对白": "启禀陛下，臣已查明。那金光乃自东胜神洲傲来国花果山。山巅有一仙石，今日迸裂，产一石卵。"
                },
                {
                    "角色": "顺风耳",
                    "对白": "石卵遇风，化作一个石猴。方才那金光，正是那石猴双目初开时所发。"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "……一个石猴？"
                },
                {
                    "角色": "千里眼",
                    "对白": "正是。那石猴此刻正在山间拜天拜地，采食花果，并无他为。"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "呵，朕还当是什么惊天动地的大事。不过是块天生地养的顽石，得了些气候，蹦出个猴子罢了。"
                },
                {
                    "角色": "玉皇大帝",
                    "对白": "此物乃天地精华所生，不足为奇。随他去吧，成不了什么气候。众仙家各归其位，散了。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "小猴",
                    "对白": "热死了，热死了！这太阳再晒下去，咱们的毛都要烤焦了！"
                },
                {
                    "角色": "老猴",
                    "对白": "这股溪水倒是凉快。只是不知尽头在哪，要是能找到源头就好了。"
                },
                {
                    "角色": "石猴",
                    "对白": "源头的水，一定更清冽甘甜！"
                },
                {
                    "角色": "老猴",
                    "对白": "说得轻巧，谁知道那源头藏在什么悬崖峭壁之后？我们顺着这涧水往上走，竟是这么大一片瀑布挡路。"
                },
                {
                    "角色": "小猴",
                    "对白": "是啊是啊，水声这么响，看着就吓人！里面不会住着什么吃猴子的妖怪吧？"
                },
                {
                    "角色": "老猴",
                    "对白": "哼，我看是你们胆子小。这样吧，今天我们立个规矩，谁有本事，能钻进这瀑布里探个究竟，再安然无恙地出来，我们就拜他为王！如何？"
                },
                {
                    "角色": "小猴",
                    "对白": "为王？这……这谁敢去啊？掉下去可就没命了！"
                },
                {
                    "角色": "石猴",
                    "对白": "我去！"
                },
                {
                    "角色": "老猴",
                    "对白": "你？别逞能！这可不是在树上打闹！"
                },
                {
                    "角色": "石猴",
                    "对白": "我去！我去！"
                },
                {
                    "角色": "石猴",
                    "对白": "嗯？水呢？怎么……眼前没有水？"
                },
                {
                    "角色": "石猴",
                    "对白": "脚下……是一座桥！是铁的！"
                },
                {
                    "角色": "石猴",
                    "对白": "这瀑布后面，竟然藏着一个……一个家！"
                },
                {
                    "角色": "石猴",
                    "对白": "哈哈！石锅、石碗、石床、石凳……这里什么都有！"
                },
                {
                    "角色": "石猴",
                    "对白": "这石碑上写的是……花果山福地，水帘洞洞天！"
                },
                {
                    "角色": "石猴",
                    "对白": "我们的家！我找到了！"
                },
                {
                    "角色": "小猴",
                    "对白": "他……他回来了！他真的从瀑布里出来了！"
                },
                {
                    "角色": "老猴",
                    "对白": "快说！里面到底是什么？可有妖魔？"
                },
                {
                    "角色": "石猴",
                    "对白": "妖魔？里面是一座天造地设的家当！宽敞得很，别说我们，就是再来几百个族猴都住得下！"
                },
                {
                    "角色": "石猴",
                    "对白": "那里有石锅石灶，石床石凳，从此再也不怕风吹雨打，虎豹豺狼！那便是我们的水帘洞洞天！"
                },
                {
                    "角色": "老猴",
                    "对白": "此话当真？你为我等寻得这般福地，理当为王！我等拜见千岁大王！"
                },
                {
                    "角色": "小猴",
                    "对白": "拜见千岁大王！千岁！千千岁！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "美猴王",
                    "对白": "诸位，诸位……且静一静。这‘千岁’二字，听着是威风，可你们谁又真见过活了一千岁的猴子呢？"
                },
                {
                    "角色": "小猴",
                    "对白": "大王说笑了！您是天生石猴，与我等不同！定能活个千岁万岁！来，大王，再饮了这杯！"
                },
                {
                    "角色": "美猴王",
                    "对白": "不同……是啊，是不同。我记得三百年前，最早教我摘桃子的那只老猴，它的背已经驼得像座小山了。去年冬天，它就没再醒过来。"
                },
                {
                    "角色": "小猴",
                    "对白": "哎呀，大王，好好的日子提这个做什么！老了就死了呗，猴子不都这样吗？今天有酒今天醉，明日自有明日的果子吃！快活一天，赚一天！"
                },
                {
                    "角色": "另一只小猴",
                    "对白": "就是！想那么多不累吗？咱们守着这福地，不受豺狼虎豹的气，不用看老天爷的脸色，已经是天大的运气了！"
                },
                {
                    "角色": "美猴王",
                    "对白": "运气……是能一直好下去的吗？等我们老了，牙也掉了，路也走不动了，这身皮毛也护不住风寒了，到时候，谁来管我们？"
                },
                {
                    "角色": "小猴",
                    "对白": "大王？您……您怎么哭了？这酒……是太烈了吗？"
                },
                {
                    "角色": "美猴王",
                    "对白": "如今我们是不归人王法律管，也无需畏惧凡间鸟兽。可将来，年老血衰，暗中有那阎王老子专管。他若要我三更死，谁敢留我到五更？到时候，这一场欢喜，岂不都成了一场空？"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "大王能有此远虑，已是心窍开，近乎于道了。"
                },
                {
                    "角色": "美猴王",
                    "对白": "老人家，莫非……你有法子？"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "在这世间万物，五虫之中，唯有三者，不入轮回，不归阎王所管。"
                },
                {
                    "角色": "美猴王",
                    "对白": "是哪三者？快说！他们现在何处？"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "乃是佛、仙、与神圣。这三者，跳出三界外，不在五行中，与天地山川同寿。"
                },
                {
                    "角色": "美猴王",
                    "对白": "他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "对白": "只在咱们这阎浮世界之中，古洞仙山之内。"
                },
                {
                    "角色": "美猴王",
                    "对白": "好！既有此等人物，我明日便辞别你们，云游海角，远涉天涯，定要寻个仙人，学一个长生不老之法，躲过那阎王的催命帖！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "美猴王",
                    "对白": "又一个年头了。这身衣服，真是个不错的笼子，把毛藏起来，也把野性藏了起来。"
                },
                {
                    "角色": "美猴王",
                    "对白": "我学会了用他们那种弯弯绕绕的语言说话，学会了为了一口饭点头哈腰。他们都说我学得真像个人。"
                },
                {
                    "角色": "美猴王",
                    "对白": "可这些人……他们起早贪黑，争的不过是几两碎银，求的不过是片刻虚名。他们从不抬头看看天，也不低头问问自己的心，就这么……一天天烂下去。"
                },
                {
                    "角色": "美猴王",
                    "对白": "我学的到底是成仙的法门，还是做人的悲哀？不……仙人一定不在此处。他们一定在海的那一边。"
                },
                {
                    "角色": "樵夫",
                    "对白": "观棋柯烂，伐木丁丁，云边谷口徐行……"
                },
                {
                    "角色": "美猴王",
                    "对白": "这歌声……"
                },
                {
                    "角色": "樵夫",
                    "对白": "相逢处非仙即道，静坐讲《黄庭》。"
                },
                {
                    "角色": "美猴王",
                    "对白": "老神仙！可算让我找到了！"
                },
                {
                    "角色": "樵夫",
                    "对白": "哎哟！你……你是什么人？快别这么叫，我只是个砍柴的，担不起，担不起！"
                },
                {
                    "角色": "美猴王",
                    "对白": "你既非神仙，怎会唱那仙家妙语？‘非仙即道’，《黄庭》乃是道家真经，你还敢说你不是？"
                },
                {
                    "角色": "樵夫",
                    "对白": "这位客官，你真是误会了。这歌词，是一位神仙邻居教我的。他说我命苦，心事重，教我烦恼时唱唱，能宽心。"
                },
                {
                    "角色": "美猴王",
                    "对白": "神仙邻居？既然有这等机缘，你为何不随他修行，学个不老之法？"
                },
                {
                    "角色": "樵夫",
                    "对白": "修行？唉，我哪里有那个福分。家里还有个老娘要养，一天不砍柴，一天就没米下锅。修行那种事，得是闲人才想的。"
                },
                {
                    "角色": "美猴王",
                    "对白": "……你是个孝子。那请你告诉我，你那位神仙邻居，住在何处？"
                },
                {
                    "角色": "樵夫",
                    "对白": "不远，就在那山里。那山叫灵台方寸山，山中有个斜月三星洞，洞里的神仙，道号须菩提祖师。"
                },
                {
                    "角色": "美猴王",
                    "对白": "灵台方寸山，斜月三星洞……"
                },
                {
                    "角色": "樵夫",
                    "对白": "是啊，祖师手下弟子不少，都是有道行的。你顺着这条小路往南走，有个七八里就到了。欸，你找他做什么？"
                },
                {
                    "角色": "美猴王",
                    "对白": "多谢指路。这份人情，我记下了。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "美猴王",
                    "对白": "灵台方寸山……斜月三星洞……这名字，到底是什么意思？"
                },
                {
                    "角色": "美猴王",
                    "对白": "那个樵夫，真是个怪人。守着个“满庭芳”，就以为能解脱烦恼了。"
                },
                {
                    "角色": "美猴王",
                    "对白": "长生不老就在眼前，他却为了凡俗孝道甘愿赴死。是通透，还是愚钝？"
                },
                {
                    "角色": "美猴王",
                    "对白": "哼，管他呢。人各有志，我的道，不在那锅灶之间。"
                },
                {
                    "角色": "美猴王",
                    "对白": "他说七八里，怎么走了这么久……莫不是在骗我？"
                },
                {
                    "角色": "美猴王",
                    "对白": "不会……他那样子，不像个会撒谎的。何况，我这双眼睛，看得出真假。"
                },
                {
                    "角色": "美猴王",
                    "对白": "等等……灵台、方寸……这不都在“心”上么？"
                },
                {
                    "角色": "美猴王",
                    "对白": "斜月……三星……那不也是个“心”字？"
                },
                {
                    "角色": "美猴王",
                    "对白": "哈哈！原来如此！原来如此！这神仙，是在跟我打哑谜呢！"
                },
                {
                    "角色": "美猴王",
                    "对白": "求道先修心……有意思，真有意思！"
                },
                {
                    "角色": "美猴王",
                    "对白": "前面那是什么？……是了！就是这里！这股清气，错不了！"
                },
                {
                    "角色": "美猴王",
                    "对白": "让我看看……灵台方寸山，斜月三星洞……哈哈！一字不差！我孙悟空，终于寻到了！"
                }
            ]
        },
        {
            "场景": 6,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "对白": "是谁在此喧哗？"
                },
                {
                    "角色": "美猴王",
                    "对白": "仙童！仙童！是我，一个寻仙问道的弟子！不敢在此叨扰。"
                },
                {
                    "角色": "仙童",
                    "对白": "寻道的？……我家师父正在坛上讲法，还未说完，却忽然让我出来开门，说是有个修行的到了，叫我接待。想来就是你了？"
                },
                {
                    "角色": "美猴王",
                    "对白": "是我，是我！劳烦仙童引路！"
                },
                {
                    "角色": "仙童",
                    "对白": "那你随我进来吧。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "台下跪着的，是何方人物？报上名来。"
                },
                {
                    "角色": "美猴王",
                    "对白": "师父！弟子是东胜神洲傲来国花果山水帘洞人氏，特来拜师，恳求师父收录门下，学个长生不老之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哼，一派胡言！你那东胜神洲，与我这里隔着两重汪洋，还有一整个南赡部洲。你一个山野猢狲，凭何而来？休要在我面前耍什么花样！"
                },
                {
                    "角色": "美猴王",
                    "对白": "师父！弟子句句属实，绝无虚言！弟子是乘着木筏，飘洋过海，历经十数年风霜雨雪，才寻到此地的！求师父明察！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哦？十数年……你且抬起头来。你既是来求道，可有姓氏？父母何在？"
                },
                {
                    "角色": "美猴王",
                    "对白": "弟子……弟子没名没姓，也无父母。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哼。人无父母，难道是树上结的，石里长的？"
                },
                {
                    "角色": "美猴王",
                    "对白": "弟子不敢欺瞒师父，我正是从花果山顶一块仙石中迸裂而出。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "原来是天地所生……倒也奇特。你起来，走两步我看看。"
                },
                {
                    "角色": "美猴王",
                    "对白": "是，师父。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你身形虽鄙，却像个食松果的猢狲。也罢，我便给你起个姓氏。"
                },
                {
                    "角色": "美猴王",
                    "对白": "谢师父！弟子愿闻其详！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你本是猢狲，那“猢”字去了兽旁，是个“古月”。古者，老也；月者，阴也。老阴不能化生，不合长生之道。我今赐你姓“孙”，这“孙”字去了兽旁，是个“子系”。子者，儿男；系者，婴细。正合那婴儿之本论。你便姓孙吧。"
                },
                {
                    "角色": "美猴王",
                    "对白": "姓孙……姓孙……好！好！弟子有姓了！弟子拜谢师父赐姓！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "我门中有十二个字，乃‘广大智慧真如性海颖悟圆觉’。排到你，正当第十个‘悟’字。我便与你起个法名，叫做‘孙悟空’。"
                },
                {
                    "角色": "美猴王",
                    "对白": "孙……悟……空……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你……可悟了？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "悟了！弟子悟了！哈哈！我有名字了！我叫孙悟空！弟子孙悟空，拜见师父！"
                }
            ]
        },
        {
            "场景": 7,
            "场景剧本": [
                {
                    "角色": "须菩提祖师",
                    "对白": "你既入我门下，至今也有七载。根性已定，今日，我便传你道法。悟空，你想学些什么？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "全凭师父教诲，弟子不敢妄求。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "也罢。我教你‘术’字门中之道，如何？请仙扶鸾，问卜揲蓍，可知趋吉避凶。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "此道，可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "不能。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "不学，不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "那便教你‘流’字门中之道？读经念佛，朝真降圣，此乃三教圣人之流。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父，如此，可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "亦不能。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "不学！不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "哼。那么，‘静’字门中之道？休粮守谷，参禅打坐，此为清净无为之功。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "请问师父，这般可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "亦不过是延年益寿，谈何长生。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "那弟子不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "也罢！那便教你‘动’字门中之道。采阴补阳，烧茅打鼎，以此固本培元。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "这……可得长生么？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "犹如镜中花，水中月。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父，既然是镜花水月，抓不着，捞不起，那还是不学了。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你这猢狲！这也不学，那也不学，究竟想怎样！"
                },
                {
                    "角色": "仙人甲",
                    "对白": "完了，完了……师父他老人家真动怒了！"
                },
                {
                    "角色": "仙人乙",
                    "对白": "你这泼猴，好生无礼！师父传你大道是你的造化，怎敢如此顶撞！"
                },
                {
                    "角色": "仙人丙",
                    "对白": "这下师父闭了中门，我看你这祸事如何了局！"
                },
                {
                    "角色": "仙人甲",
                    "对白": "悟空！你还愣着作甚？还不快跪下，向着中门磕头请罪！或许师父还能消气！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "多谢师兄关心。"
                },
                {
                    "角色": "仙人乙",
                    "对白": "关心？你看他！脸上竟然还带着笑！我看你是被师父打傻了！"
                },
                {
                    "角色": "仙人丙",
                    "对白": "真是个不知好歹的畜生！我们离他远点，免得被他连累！"
                },
                {
                    "角色": "仙人甲",
                    "对白": "走走走，别管他了，让他自己在这儿领罚吧！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "三下……三更……后门……嘿。师父，弟子……悟了。"
                }
            ]
        },
        {
            "场景": 8,
            "场景剧本": [
                {
                    "角色": "孙悟空",
                    "对白": "师父，弟子在此跪候多时了。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "这猢狲，你不在前院好生安睡，深夜潜入我这里，所为何事啊？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父昨日在坛前分付，三更时分，由后门传我大道。弟子不敢不来。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "呵呵……果然是个天地生成的灵物，竟能解我盘中之谜。此处无有外人，你近前来，仔细听了。我便传你长生妙法。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子……永世不忘师父大恩！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄……休漏泄，体中藏，汝受吾传道自昌……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "悟空何在？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子在。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "这几年，你修的道，如何了？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "回禀师父，弟子近来法性颇通，根源也日益坚固了。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你既已通法性，明根源，神体已入……却还需防备一件事。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父此言差矣。常闻道高德隆者，与天同寿，百病不生。如何还有什么要防备的？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "此乃非常之道。你所学之法，夺天地之造化，侵日月之玄机。丹成之后，鬼神难容。虽能驻颜益寿，但到了五百年后，天降雷灾打你。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "雷灾？弟子躲得过么？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你若见性明心，预先躲避，可与天齐寿。躲不过，就此绝命。再五百年，天降火灾烧你。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "是凡火吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "非天火，非凡火，此唤‘阴火’。自你涌泉穴下烧起，直透泥垣宫，五脏成灰，四肢皆朽，千年苦功，一时俱为灰烬！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "这……还有吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "再五百年，又降风灾吹你。非东南西北风，唤作‘赑风’。自你囟门中吹入，贯彻丹田，骨肉消疏，身体自解！悟空，你怕不怕！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父……弟子闻言，遍体生寒！万望师父垂怜，传我躲避三灾之法，弟子纵然粉身碎骨，也感念大德！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "此事倒也不难。只是你与旁人不同，传不得。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "我头顶天，脚踏地，九窍四肢，五脏六腑，与人何异？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你虽像人，却少腮。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子虽然没腮，却多了个颊囊，也算将就得过。求师父开恩！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "也罢。我有两种法术可避三灾。一是天罡数，有三十六般变化。一是地煞数，有七十二般变化。你待学哪一种？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子愿多学些，学地煞数便好。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "既如此，你再近前来。我将这七十二变的口诀，暗暗传与你……"
                }
            ]
        },
        {
            "场景": 9,
            "场景剧本": [
                {
                    "角色": "师兄甲",
                    "对白": "悟空，师父那晚……是单独给你开了小灶吧？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师兄说笑了。师父是看我生性愚钝，才多费心提点了几句。"
                },
                {
                    "角色": "师兄乙",
                    "对白": "提点几句？那可是躲三灾的七十二变，是大道真传。我们这些人，可没这个福分。不知你……到底领悟了多少？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父的教诲，自然是日夜记在心里，不敢有半分懈怠。"
                },
                {
                    "角色": "师兄甲",
                    "对白": "记在心里是一回事，练成又是另一回事。这等玄妙法门，一变就耗尽心神，我等穷尽一生也难得其一。你不会……只是记住了口诀吧？"
                },
                {
                    "角色": "师兄乙",
                    "对白": "就是。光说不练，谁不会呢？除非你当场变个什么，给我们开开眼界？也让我们见识见识师父的无上妙法。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "这……师父有言在先，道不传非人，法不示无缘。不可轻易炫耀。"
                },
                {
                    "角色": "师兄甲",
                    "对白": "哎，都是自家师兄弟，又不是外人。还是说……你根本就没学会，怕当众露了馅儿？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师兄这是哪里话！也罢！今天就让你们瞧个新鲜。说吧，要我变成什么？"
                },
                {
                    "角色": "师兄乙",
                    "对白": "嗯……既然是在松树下，就变成咱们眼前这棵苍松吧。这松树最见风骨，也最考验功力，可不好变。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "好！师兄们可看仔细了！"
                },
                {
                    "角色": "师兄甲",
                    "对白": "咦？悟空呢？怎么一转眼人就不见了？"
                },
                {
                    "角色": "师兄乙",
                    "对白": "天啊！快看！那儿……多出来一棵松树！枝干、树皮、松针……跟真的一模一样！分毫不差！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师兄们，我这手艺如何？"
                },
                {
                    "角色": "师兄甲",
                    "对白": "好猴子！真是好猴子！神乎其技！"
                },
                {
                    "角色": "师兄乙",
                    "对白": "简直匪夷所思！当真学到了真传！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "在此喧哗，成何体统！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "禀尊师，我等在此聚会论道，并无外人喧哗。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "论道？我听到的，为何是喝彩与哄笑？修行之人，口开神气散，舌动是非生。你们在此笑什么！"
                },
                {
                    "角色": "师兄甲",
                    "对白": "不敢隐瞒师父……是……是孙悟空在此演练变化之术。他变成了一棵松树，弟子们一时惊叹，才高声惊扰了尊师，望师父恕罪。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "悟空，你过来。我问你，你为何要变那松树？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子……弟子只是想让师兄们看看，所学未曾荒废……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "我教你的是躲灾避劫的法门，你却拿来当做在人前换取喝彩的戏法！你这般卖弄，与街头耍猴的有何区别？"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子……弟子知错了……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你记住，神通一旦显露，灾祸便随之而来。今日你为了一声喝彩变棵松树，他日，就可能为了一个虚名，捅破这天！"
                }
            ]
        },
        {
            "场景": 10,
            "场景剧本": [
                {
                    "角色": "孙悟空",
                    "对白": "师父，弟子再也不敢了！求您……求您就宽恕弟子这一次！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "宽恕？知错，不代表能改。你的天性，就像这山间的野火，一旦点燃，连你自己都控制不住。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子能改！弟子一定改！只要师父肯教，弟子什么都肯学！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "我教不了你了。留你在此，这方寸山，迟早要被你的“喝彩声”引来天大的祸事。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父……您这是……要赶我走？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "不是赶你走，是让你走。你从哪里来，回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "可是……我离家二十年，好不容易才寻到仙山……师父的大恩，弟子还没来得及报答！"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "不必报了。你日后不惹祸，不连累我，就是对我最大的报答。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "为什么？就因为一棵松树？就因为几声喝彩？这就要断了弟子的修行路吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "因为我看到了你的将来。你这颗心，装不下清规戒律，只装得下齐天大圣的野心。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "弟子……弟子不懂……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "你此去，定生祸端。记住，不许对任何人说，你是我的徒弟。我教不了你收敛心性，只能教你如何独自面对。这，是我能给你的最后一课。"
                },
                {
                    "角色": "孙悟空",
                    "对白": "师父……"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "还有。你若对任何人泄露此地，泄露我，哪怕只说出半个字，我便顷刻知晓。届时，我必将你这猢狲剥皮锉骨，神魂贬入九幽之地，让你万劫不得翻身！"
                },
                {
                    "角色": "孙悟空",
                    "对白": "……弟子，绝不敢提师父半字。只说……是弟子自己学来的。"
                },
                {
                    "角色": "须菩提祖师",
                    "对白": "去吧。"
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
    # print(narration_gemini2)
    narration_gemini = {
    "剧本": [
        {
            "场景": 1,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "宇宙洪荒，混沌未开。直至盘古开天，清浊始分，万物皆在十二万九千六百年的轮回中生灭。东胜神洲，花果山之巅，立着一块仙石。它暗合周天之数，上有九窍八卦之形，日日夜夜，贪婪地吮吸着日月精华。这一日，只听一声巨响，仙石迸裂，一个石猴自卵中化出。他双目睁开，两道金光竟如利剑般刺破云霄，直冲天庭斗牛宫！"
                },
                {
                    "插入位置": 6,
                    "旁白": "凌霄殿上一时无声，片刻之后，二神便已洞悉了下界的一切。"
                },
                {
                    "插入位置": 11,
                    "旁白": "话音落下，天庭众神透过云端向下望去，只见那石猴懵懂无知，正于山林间嬉耍，不知饥饱，不识善恶，浑然一个天生地养的野物。"
                },
                {
                    "插入位置": 12,
                    "旁白": "天庭的秩序，严苛而恒久。一道惊扰，查明之后，便如投入湖中的石子，涟漪散尽，重归死水。"
                }
            ]
        },
        {
            "场景": 2,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "这石猴混入猴群，倒也自在。每日里追逐打闹，攀藤戏水，浑然不知岁月。直到一个酷暑难当的夏日，猴群沿着山涧溯流而上，试图寻一处清凉的源头。"
                },
                {
                    "插入位置": 7,
                    "旁白": "猴群顿时鸦雀无声，面面相觑，无人敢应。就在这片刻的死寂中，石猴从群猴中一跃而出，声音不大，却掷地有声。"
                },
                {
                    "插入位置": 10,
                    "旁白": "他不再多言，一个纵身，奋力向那白茫茫的水幕中心扑去。轰鸣的水声瞬间吞没了一切，冰冷的激流仿佛要将他撕碎。然而，只是一眨眼的工夫，喧嚣与水汽尽数褪去，眼前豁然开朗。"
                },
                {
                    "插入位置": 16,
                    "旁白": "瀑布之外，猴群正焦灼地等待着，以为那石猴早已被水冲走。忽然，水帘再次被破开，一个湿淋淋的身影逆着水光跳将出来，眼中闪烁着前所未有的光芒。"
                },
                {
                    "插入位置": 20,
                    "旁白": "石猴的声音在山谷间回荡，为群猴描绘出一个无需再担惊受怕的家园。恐惧被狂喜取代，所有的目光都集中在了他身上，充满了敬畏与信服。"
                }
            ]
        },
        {
            "场景": 3,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "水帘洞内，石锅里炖着山果，藤蔓上挂着佳酿。群猴的喧哗像不息的潮水，拍打着洞府的每一个角落。而美猴王，这片喧嚣的中心，却像潮水中的礁石，沉默着，任由欢声笑语冲刷而过。"
                },
                {
                    "插入位置": 3,
                    "旁白": "这番话如一块冷石投进沸腾的酒锅，只激起一瞬的白汽，便迅速沉底，无人理会。"
                },
                {
                    "插入位置": 6,
                    "旁白": "喧闹声像是被一只无形的手掐断了。一滴眼泪，从美猴王的眼角滑落，滚过他尚且年轻的面颊，滴入酒杯。杯中酒水漾开的，是他对生命无常的全部悲哀。"
                },
                {
                    "插入位置": 8,
                    "旁白": "猴王的话语像淬了冰，让洞内的狂热瞬间冷却。群猴的嬉笑凝固在脸上，面面相觑，第一次在王的眼中看到了与自己截然不同的东西——恐惧。就在这片死寂中，一个苍老的声音从猴群的角落里响起。"
                },
                {
                    "插入位置": 15,
                    "旁白": "佛、仙、神圣。三个字，像三道劈开混沌的闪电，瞬间照亮了美猴王被死亡阴影笼罩的内心。那双曾射出金光的眼眸里，重新燃起了火焰，不是为了王权，而是为了超越王权的永恒。"
                }
            ]
        },
        {
            "场景": 4,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "独木舟早已散架，换成了双脚丈量大地。自花果山漂洋过海，已是第九个年头。最初的几年，他学着忍受孤独，模仿人的言行举止，将一身金毛藏进粗布衣衫。如今，他站在南赡部洲的市井里，言谈举止已与常人无异。"
                },
                {
                    "插入位置": 4,
                    "旁白": "于是，他又扎起木筏，漂过西海，登上了西牛贺洲地界。眼前是一座从未见过的秀丽高山，林木幽深，云锁峰顶。他心中笃定，仙人必在此处。他不怕豺狼虎豹，径直向山林深处寻去。"
                },
                {
                    "插入位置": 7,
                    "旁白": "歌声缥缈，字字句句都暗藏玄机。猴王心中一震，拨开身前的枝叶，循声望去，认定这高歌之人，便是他寻觅了近十年的仙踪。"
                },
                {
                    "插入位置": 17,
                    "旁白": "近十年的迷茫与孤寂，在这一刻被一个清晰的名字和方向所取代。他朝着樵夫深深一揖，眼神里是前所未有的坚定。"
                }
            ]
        },
        {
            "场景": 5,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "樵夫的身影消失在林间小道的拐角。猴王转过身，面前是更加幽深、更加寂静的密林。光线被层层叠叠的树冠筛成碎片，投在潮湿的苔藓上，空气中弥漫着腐殖土和不知名野花的混合气息。他拨开垂挂的藤蔓，踏上了一条几乎被落叶掩盖的小径。"
                },
                {
                    "插入位置": 4,
                    "旁白": "他不再去想那个凡人的抉择，只是埋头赶路。山势渐渐陡峭，所谓的“小路”不过是野兽踩出的痕迹，被盘结的树根和尖利的碎石所占据。他的呼吸变得沉重，汗水濡湿了额前的绒毛。"
                },
                {
                    "插入位置": 6,
                    "旁白": "他停下脚步，靠在一棵苍老的松树上喘息。四周只有风穿过松针的低语。他抬起头，视线越过交错的枝桠，望向那片被切割得支离破碎的天空，脑中反复回响着樵夫留下的那几个字。"
                },
                {
                    "插入位置": 10,
                    "旁白": "一种豁然开朗的喜悦驱散了所有的疲惫。他不再被脚下的崎岖所困，身体仿佛轻盈了许多，几个纵跃便攀上了一处山坡的顶端。视野在此刻瞬间开阔。"
                },
                {
                    "插入位置": 11,
                    "旁白": "洞门紧闭，静谧无声。崖头立着一块三丈多高的石牌，岁月在上面留下了青苍的痕迹，但那十个大字却仿佛蕴含着某种力量，穿透了时光的薄雾，清晰地映入他的眼帘。"
                }
            ]
        },
        {
            "场景": 6,
            "旁白内容": [
                {
                    "插入位置": 5,
                    "旁白": "猴王整理衣襟，随仙童深入洞府。只见其内层层叠叠，琼楼玉宇，竟是别有一番洞天。行至瑶台之下，便见菩提祖师高坐台上，周遭侍立着三十余位仙人，气度庄严。猴王不敢抬头，俯身便拜，额头触及冰冷的石地，在空旷的殿中连连叩首。"
                },
                {
                    "插入位置": 9,
                    "旁白": "殿内一时沉寂，只有猴王粗重的喘息。台上，祖师的目光如两道无形的利剑，审视着这个跪伏在地、浑身还带着海风咸涩气息的生灵。那目光里没有怜悯，只有探究，似乎要将他从里到外看个通透。"
                },
                {
                    "插入位置": 13,
                    "旁白": "此言一出，祖师眼中那审视的严厉悄然褪去，代之而起的是一丝难以察觉的惊异与了然。他终于明白，眼前这猢狲的来历，并非凡俗，而是与这方天地同根同源。"
                },
                {
                    "插入位置": 15,
                    "旁白": "猴王听令，立刻起身，连蹦带跳地走了两圈，动作轻捷，野性未脱，那一身急于求道的虔诚下，终究还是山林间无拘无束的根骨。"
                },
                {
                    "插入位置": 19,
                    "旁白": "“孙”，一个脱离了兽类，归于人形的姓氏。猴王反复咀嚼着这个字，仿佛生平第一次拥有了根。他叩首下去，这一次，不再是单纯的恳求，而是带着新生的喜悦与归属。"
                },
                {
                    "插入位置": 22,
                    "旁白": "空，万法皆空，亦是万法之始。这个字仿佛一道灵光，瞬间劈开了他混沌的识海。从一块顽石，到啸聚山林的猴王，再到此刻跪于此地的求道者，一切过往都如云烟散去。从今往后，他不再是那个无名无姓的石猴，而是孙悟空。"
                }
            ]
        },
        {
            "场景": 7,
            "旁白内容": [
                {
                    "插入位置": 18,
                    "旁白": "讲坛之上，祖师的脸色沉了下来，他从座位上霍然起身。"
                },
                {
                    "插入位置": 19,
                    "旁白": "祖师走下高台，手中不知何时多了一把戒尺。他行至悟空面前，对着那颗毛茸茸的头颅，不轻不重，敲了三下。随后，祖师倒背着手，一言不发地走入内院，将中门在身后合拢，把一众惊愕的弟子撇在了门外。"
                },
                {
                    "插入位置": 23,
                    "旁白": "责备与惊慌之声四起，讲堂内一片嘈杂。唯独被斥责的悟空，跪在原地，脸上不见丝毫恼怒。众人的言语如流水分过山石，未在他心上留下一丝痕迹，他琢磨的，只是师父那三下敲击，和那扇紧闭的门。"
                },
                {
                    "插入位置": 27,
                    "旁白": "师兄弟们悻悻散去，偌大的讲堂重归寂静。悟空抬起头，望着那扇隔绝内外的大门，眼中的迷雾散尽，透出澄澈的光。"
                }
            ]
        },
        {
            "场景": 8,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "夜色如墨，月光滤过洞府的石窗，在地上投下斑驳的冷辉。祖师的卧房内一片沉寂，只闻得均匀绵长的呼吸声。悟空蹑足潜行，衣袂不带一丝风声，悄然跪倒在榻前，将自己的身形缩成一团虔诚的影子。"
                },
                {
                    "插入位置": 6,
                    "旁白": "长生之诀，如同一粒种子，在悟空体内无声地生根发芽。转眼，又是三年。这期间，他于人前扫地应答，于人后则依循口诀，默默调息炼神，一身的灵气被收敛得愈发精纯。这一日，祖师于高台讲法，话音一顿，目光扫过众弟子。"
                },
                {
                    "插入位置": 12,
                    "旁白": "祖师脸上的笑意敛去，目光变得深邃而凝重，仿佛穿透了眼前的弟子，看到了遥远未来中注定降临的劫数。"
                },
                {
                    "插入位置": 19,
                    "旁白": "长生的愿景在“三灾”的描述下寸寸碎裂。悟空只觉一股寒意从脊骨升起，瞬间传遍四肢百骸。那与天同寿的期许，此刻听来更像一个横亘千年的诅咒。"
                },
                {
                    "插入位置": 26,
                    "旁白": "祖师的声音再次压低，化作一丝几不可闻的气流，钻入悟空的耳中。那不是凡间的言语，而是一串串解构万物、重塑自身的密语。"
                }
            ]
        },
        {
            "场景": 9,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "灵台方寸山的一个夏日午后，光影在松针间筛落成斑驳的碎金。几位师兄弟在树下闲谈，起初还是论道讲经，但话锋一转，便带着几分试探与好奇，若有若无地飘向了那个新来的石猴。"
                },
                {
                    "插入位置": 8,
                    "旁白": "那句“露了馅儿”如同一根芒刺，扎进了孙悟空天生的傲骨里。师父“不可炫耀”的告诫，在此刻被师兄弟们夹杂着嫉妒与轻蔑的目光一激，瞬间化作了泡影。一股不甘与好胜的妖性，压过了初修的道心。"
                },
                {
                    "插入位置": 11,
                    "旁白": "孙悟空口念真言，手捏法诀，身形在一瞬间变得模糊。那并非简单的消失，而是一种物质性的重组与溶解。他的轮廓向内坍缩，随即又向外舒展，骨骼化为虬结的枝干，毛发抽长成细密的松针，伴随着一阵细微的、仿佛草木生长的声音。"
                },
                {
                    "插入位置": 13,
                    "旁白": "那声音分明是孙悟空的，却又带着木质的共鸣，仿佛是从松树最深处的年轮里传出来的，戏谑而得意。"
                },
                {
                    "插入位置": 16,
                    "旁白": "喧哗与喝彩声惊扰了山中的清净，也惊动了洞府深处的那个人。一个身影无声无息地出现在松林边缘，须菩提祖师手持拐杖，面沉如水。他只是站在那里，周遭的空气便仿佛凝固了，所有的笑声戛然而止。"
                },
                {
                    "插入位置": 20,
                    "旁白": "众师兄弟噤若寒蝉，纷纷退去，只留下孙悟空恢复原形，独自站在空地中央。祖师的目光如两道寒冰，将他牢牢钉在原地，那目光里没有平日的温和，只有一种洞穿肺腑的失望与严厉。"
                }
            ]
        },
        {
            "场景": 10,
            "旁白内容": [
                {
                    "插入位置": 0,
                    "旁白": "松树变回了猴王，喧闹的喝彩声却在祖师冰冷的目光下凝结成一片死寂。悟空脸上的得意还未褪去，就已被一种不祥的预感攫住，他跪倒在地，声音里带着孩童般的惶恐。"
                },
                {
                    "插入位置": 4,
                    "旁白": "祖师的话语平静，却像一把无形的利剑，斩断了悟空最后的侥幸。山风吹过，他第一次感到这仙山的风，竟是如此寒意彻骨。"
                },
                {
                    "插入位置": 10,
                    "旁白": "“齐天大圣”。四个字，如同一道惊雷，劈开了时空的迷雾，让祖师瞥见了未来的血海与烽烟。而此刻的悟空，只能感到这四个字滚烫的重量，却无法洞悉其中蕴含的，究竟是荣耀，还是宿命的枷锁。"
                },
                {
                    "插入位置": 14,
                    "旁白": "这番话不再是训诫，而是一道刻入神魂的咒言。每一个字都带着千钧之力，砸在悟空心头，将他与灵台方寸山之间最后的情分彻底碾碎。他终于明白，从今往后，天地虽大，却再无师父。"
                },
                {
                    "插入位置": 16,
                    "旁白": "他磕了最后一个头，再无言语。一个筋斗，翻出了十万八千里，也翻出了此生的师徒缘分。身后，是再也回不去的斜月三星洞；眼前，是阔别二十年的花果山。他学成了长生，却被逐出了道法之门；他炼就了通天本领，却成了天地间最孤独的一个。那个寻仙问道的美猴王走了，此刻归来的，是孙悟空。"
                }
            ]
        }
    ]
}
    # 合并旁白与对白
    result = combine_dialogue_and_narration(dialogue_gemini, narration_gemini)

    # 合并后的剧本
    pre_script_gemini = {
    "剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "宇宙洪荒，混沌未开。直至盘古开天，清浊始分，万物皆在十二万九千六百年的轮回中生灭。东胜神洲，花果山之巅，立着一块仙石。它暗合周天之数，上有九窍八卦之形，日日夜夜，贪婪地吮吸着日月精华。这一日，只听一声巨响，仙石迸裂，一个石猴自卵中化出。他双目睁开，两道金光竟如利剑般刺破云霄，直冲天庭斗牛宫！"
                },
                {
                    "角色": "千里眼",
                    "内容": "陛下！下界有异象冲撞天庭！"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "何事惊慌，乱了凌霄宝殿的法度？"
                },
                {
                    "角色": "千里眼",
                    "内容": "臣奉旨巡视南天门，忽见两道金光自下界凡尘，破云而出，直射斗牛宫，仙气激荡，非同小可！"
                },
                {
                    "角色": "顺风耳",
                    "内容": "臣亦听得那金光之中，隐有风雷之声，似山崩石裂，又非凡音。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "金光？风雷？立刻给朕查明，是何方妖孽，竟敢如此放肆！"
                },
                {
                    "角色": "千里眼",
                    "内容": "遵旨！"
                },
                {
                    "角色": "旁白",
                    "内容": "凌霄殿上一时无声，片刻之后，二神便已洞悉了下界的一切。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "如何？"
                },
                {
                    "角色": "千里眼",
                    "内容": "启禀陛下，臣已查明。那金光乃自东胜神洲傲来国花果山。山巅有一仙石，今日迸裂，产一石卵。"
                },
                {
                    "角色": "顺风耳",
                    "内容": "石卵遇风，化作一个石猴。方才那金光，正是那石猴双目初开时所发。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "……一个石猴？"
                },
                {
                    "角色": "千里眼",
                    "内容": "正是。那石猴此刻正在山间拜天拜地，采食花果，并无他为。"
                },
                {
                    "角色": "旁白",
                    "内容": "话音落下，天庭众神透过云端向下望去，只见那石猴懵懂无知，正于山林间嬉耍，不知饥饱，不识善恶，浑然一个天生地养的野物。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "呵，朕还当是什么惊天动地的大事。不过是块天生地养的顽石，得了些气候，蹦出个猴子罢了。"
                },
                {
                    "角色": "旁白",
                    "内容": "天庭的秩序，严苛而恒久。一道惊扰，查明之后，便如投入湖中的石子，涟漪散尽，重归死水。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "此物乃天地精华所生，不足为奇。随他去吧，成不了什么气候。众仙家各归其位，散了。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这石猴混入猴群，倒也自在。每日里追逐打闹，攀藤戏水，浑然不知岁月。直到一个酷暑难当的夏日，猴群沿着山涧溯流而上，试图寻一处清凉的源头。"
                },
                {
                    "角色": "小猴",
                    "内容": "热死了，热死了！这太阳再晒下去，咱们的毛都要烤焦了！"
                },
                {
                    "角色": "老猴",
                    "内容": "这股溪水倒是凉快。只是不知尽头在哪，要是能找到源头就好了。"
                },
                {
                    "角色": "石猴",
                    "内容": "源头的水，一定更清冽甘甜！"
                },
                {
                    "角色": "老猴",
                    "内容": "说得轻巧，谁知道那源头藏在什么悬崖峭壁之后？我们顺着这涧水往上走，竟是这么大一片瀑布挡路。"
                },
                {
                    "角色": "小猴",
                    "内容": "是啊是啊，水声这么响，看着就吓人！里面不会住着什么吃猴子的妖怪吧？"
                },
                {
                    "角色": "老猴",
                    "内容": "哼，我看是你们胆子小。这样吧，今天我们立个规矩，谁有本事，能钻进这瀑布里探个究竟，再安然无恙地出来，我们就拜他为王！如何？"
                },
                {
                    "角色": "小猴",
                    "内容": "为王？这……这谁敢去啊？掉下去可就没命了！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴群顿时鸦雀无声，面面相觑，无人敢应。就在这片刻的死寂中，石猴从群猴中一跃而出，声音不大，却掷地有声。"
                },
                {
                    "角色": "石猴",
                    "内容": "我去！"
                },
                {
                    "角色": "老猴",
                    "内容": "你？别逞能！这可不是在树上打闹！"
                },
                {
                    "角色": "石猴",
                    "内容": "我去！我去！"
                },
                {
                    "角色": "旁白",
                    "内容": "他不再多言，一个纵身，奋力向那白茫茫的水幕中心扑去。轰鸣的水声瞬间吞没了一切，冰冷的激流仿佛要将他撕碎。然而，只是一眨眼的工夫，喧嚣与水汽尽数褪去，眼前豁然开朗。"
                },
                {
                    "角色": "石猴",
                    "内容": "嗯？水呢？怎么……眼前没有水？"
                },
                {
                    "角色": "石猴",
                    "内容": "脚下……是一座桥！是铁的！"
                },
                {
                    "角色": "石猴",
                    "内容": "这瀑布后面，竟然藏着一个……一个家！"
                },
                {
                    "角色": "石猴",
                    "内容": "哈哈！石锅、石碗、石床、石凳……这里什么都有！"
                },
                {
                    "角色": "石猴",
                    "内容": "这石碑上写的是……花果山福地，水帘洞洞天！"
                },
                {
                    "角色": "石猴",
                    "内容": "我们的家！我找到了！"
                },
                {
                    "角色": "旁白",
                    "内容": "瀑布之外，猴群正焦灼地等待着，以为那石猴早已被水冲走。忽然，水帘再次被破开，一个湿淋淋的身影逆着水光跳将出来，眼中闪烁着前所未有的光芒。"
                },
                {
                    "角色": "小猴",
                    "内容": "他……他回来了！他真的从瀑布里出来了！"
                },
                {
                    "角色": "老猴",
                    "内容": "快说！里面到底是什么？可有妖魔？"
                },
                {
                    "角色": "石猴",
                    "内容": "妖魔？里面是一座天造地设的家当！宽敞得很，别说我们，就是再来几百个族猴都住得下！"
                },
                {
                    "角色": "石猴",
                    "内容": "那里有石锅石灶，石床石凳，从此再也不怕风吹雨打，虎豹豺狼！那便是我们的水帘洞洞天！"
                },
                {
                    "角色": "旁白",
                    "内容": "石猴的声音在山谷间回荡，为群猴描绘出一个无需再担惊受怕的家园。恐惧被狂喜取代，所有的目光都集中在了他身上，充满了敬畏与信服。"
                },
                {
                    "角色": "老猴",
                    "内容": "此话当真？你为我等寻得这般福地，理当为王！我等拜见千岁大王！"
                },
                {
                    "角色": "小猴",
                    "内容": "拜见千岁大王！千岁！千千岁！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "水帘洞内，石锅里炖着山果，藤蔓上挂着佳酿。群猴的喧哗像不息的潮水，拍打着洞府的每一个角落。而美猴王，这片喧嚣的中心，却像潮水中的礁石，沉默着，任由欢声笑语冲刷而过。"
                },
                {
                    "角色": "美猴王",
                    "内容": "诸位，诸位……且静一静。这‘千岁’二字，听着是威风，可你们谁又真见过活了一千岁的猴子呢？"
                },
                {
                    "角色": "小猴",
                    "内容": "大王说笑了！您是天生石猴，与我等不同！定能活个千岁万岁！来，大王，再饮了这杯！"
                },
                {
                    "角色": "美猴王",
                    "内容": "不同……是啊，是不同。我记得三百年前，最早教我摘桃子的那只老猴，它的背已经驼得像座小山了。去年冬天，它就没再醒过来。"
                },
                {
                    "角色": "旁白",
                    "内容": "这番话如一块冷石投进沸腾的酒锅，只激起一瞬的白汽，便迅速沉底，无人理会。"
                },
                {
                    "角色": "小猴",
                    "内容": "哎呀，大王，好好的日子提这个做什么！老了就死了呗，猴子不都这样吗？今天有酒今天醉，明日自有明日的果子吃！快活一天，赚一天！"
                },
                {
                    "角色": "另一只小猴",
                    "内容": "就是！想那么多不累吗？咱们守着这福地，不受豺狼虎豹的气，不用看老天爷的脸色，已经是天大的运气了！"
                },
                {
                    "角色": "美猴王",
                    "内容": "运气……是能一直好下去的吗？等我们老了，牙也掉了，路也走不动了，这身皮毛也护不住风寒了，到时候，谁来管我们？"
                },
                {
                    "角色": "旁白",
                    "内容": "喧闹声像是被一只无形的手掐断了。一滴眼泪，从美猴王的眼角滑落，滚过他尚且年轻的面颊，滴入酒杯。杯中酒水漾开的，是他对生命无常的全部悲哀。"
                },
                {
                    "角色": "小猴",
                    "内容": "大王？您……您怎么哭了？这酒……是太烈了吗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "如今我们是不归人王法律管，也无需畏惧凡间鸟兽。可将来，年老血衰，暗中有那阎王老子专管。他若要我三更死，谁敢留我到五更？到时候，这一场欢喜，岂不都成了一场空？"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王的话语像淬了冰，让洞内的狂热瞬间冷却。群猴的嬉笑凝固在脸上，面面相觑，第一次在王的眼中看到了与自己截然不同的东西——恐惧。就在这片死寂中，一个苍老的声音从猴群的角落里响起。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王能有此远虑，已是心窍开，近乎于道了。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老人家，莫非……你有法子？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "在这世间万物，五虫之中，唯有三者，不入轮回，不归阎王所管。"
                },
                {
                    "角色": "美猴王",
                    "内容": "是哪三者？快说！他们现在何处？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "乃是佛、仙、与神圣。这三者，跳出三界外，不在五行中，与天地山川同寿。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "只在咱们这阎浮世界之中，古洞仙山之内。"
                },
                {
                    "角色": "旁白",
                    "内容": "佛、仙、神圣。三个字，像三道劈开混沌的闪电，瞬间照亮了美猴王被死亡阴影笼罩的内心。那双曾射出金光的眼眸里，重新燃起了火焰，不是为了王权，而是为了超越王权的永恒。"
                },
                {
                    "角色": "美猴王",
                    "内容": "好！既有此等人物，我明日便辞别你们，云游海角，远涉天涯，定要寻个仙人，学一个长生不老之法，躲过那阎王的催命帖！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "独木舟早已散架，换成了双脚丈量大地。自花果山漂洋过海，已是第九个年头。最初的几年，他学着忍受孤独，模仿人的言行举止，将一身金毛藏进粗布衣衫。如今，他站在南赡部洲的市井里，言谈举止已与常人无异。"
                },
                {
                    "角色": "美猴王",
                    "内容": "又一个年头了。这身衣服，真是个不错的笼子，把毛藏起来，也把野性藏了起来。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学会了用他们那种弯弯绕绕的语言说话，学会了为了一口饭点头哈腰。他们都说我学得真像个人。"
                },
                {
                    "角色": "美猴王",
                    "内容": "可这些人……他们起早贪黑，争的不过是几两碎银，求的不过是片刻虚名。他们从不抬头看看天，也不低头问问自己的心，就这么……一天天烂下去。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学的到底是成仙的法门，还是做人的悲哀？不……仙人一定不在此处。他们一定在海的那一边。"
                },
                {
                    "角色": "旁白",
                    "内容": "于是，他又扎起木筏，漂过西海，登上了西牛贺洲地界。眼前是一座从未见过的秀丽高山，林木幽深，云锁峰顶。他心中笃定，仙人必在此处。他不怕豺狼虎豹，径直向山林深处寻去。"
                },
                {
                    "角色": "樵夫",
                    "内容": "观棋柯烂，伐木丁丁，云边谷口徐行……"
                },
                {
                    "角色": "美猴王",
                    "内容": "这歌声……"
                },
                {
                    "角色": "樵夫",
                    "内容": "相逢处非仙即道，静坐讲《黄庭》。"
                },
                {
                    "角色": "旁白",
                    "内容": "歌声缥缈，字字句句都暗藏玄机。猴王心中一震，拨开身前的枝叶，循声望去，认定这高歌之人，便是他寻觅了近十年的仙踪。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老神仙！可算让我找到了！"
                },
                {
                    "角色": "樵夫",
                    "内容": "哎哟！你……你是什么人？快别这么叫，我只是个砍柴的，担不起，担不起！"
                },
                {
                    "角色": "美猴王",
                    "内容": "你既非神仙，怎会唱那仙家妙语？‘非仙即道’，《黄庭》乃是道家真经，你还敢说你不是？"
                },
                {
                    "角色": "樵夫",
                    "内容": "这位客官，你真是误会了。这歌词，是一位神仙邻居教我的。他说我命苦，心事重，教我烦恼时唱唱，能宽心。"
                },
                {
                    "角色": "美猴王",
                    "内容": "神仙邻居？既然有这等机缘，你为何不随他修行，学个不老之法？"
                },
                {
                    "角色": "樵夫",
                    "内容": "修行？唉，我哪里有那个福分。家里还有个老娘要养，一天不砍柴，一天就没米下锅。修行那种事，得是闲人才想的。"
                },
                {
                    "角色": "美猴王",
                    "内容": "……你是个孝子。那请你告诉我，你那位神仙邻居，住在何处？"
                },
                {
                    "角色": "樵夫",
                    "内容": "不远，就在那山里。那山叫灵台方寸山，山中有个斜月三星洞，洞里的神仙，道号须菩提祖师。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山，斜月三星洞……"
                },
                {
                    "角色": "樵夫",
                    "内容": "是啊，祖师手下弟子不少，都是有道行的。你顺着这条小路往南走，有个七八里就到了。欸，你找他做什么？"
                },
                {
                    "角色": "旁白",
                    "内容": "近十年的迷茫与孤寂，在这一刻被一个清晰的名字和方向所取代。他朝着樵夫深深一揖，眼神里是前所未有的坚定。"
                },
                {
                    "角色": "美猴王",
                    "内容": "多谢指路。这份人情，我记下了。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "樵夫的身影消失在林间小道的拐角。猴王转过身，面前是更加幽深、更加寂静的密林。光线被层层叠叠的树冠筛成碎片，投在潮湿的苔藓上，空气中弥漫着腐殖土和不知名野花的混合气息。他拨开垂挂的藤蔓，踏上了一条几乎被落叶掩盖的小径。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山……斜月三星洞……这名字，到底是什么意思？"
                },
                {
                    "角色": "美猴王",
                    "内容": "那个樵夫，真是个怪人。守着个“满庭芳”，就以为能解脱烦恼了。"
                },
                {
                    "角色": "美猴王",
                    "内容": "长生不老就在眼前，他却为了凡俗孝道甘愿赴死。是通透，还是愚钝？"
                },
                {
                    "角色": "美猴王",
                    "内容": "哼，管他呢。人各有志，我的道，不在那锅灶之间。"
                },
                {
                    "角色": "旁白",
                    "内容": "他不再去想那个凡人的抉择，只是埋头赶路。山势渐渐陡峭，所谓的“小路”不过是野兽踩出的痕迹，被盘结的树根和尖利的碎石所占据。他的呼吸变得沉重，汗水濡湿了额前的绒毛。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他说七八里，怎么走了这么久……莫不是在骗我？"
                },
                {
                    "角色": "美猴王",
                    "内容": "不会……他那样子，不像个会撒谎的。何况，我这双眼睛，看得出真假。"
                },
                {
                    "角色": "旁白",
                    "内容": "他停下脚步，靠在一棵苍老的松树上喘息。四周只有风穿过松针的低语。他抬起头，视线越过交错的枝桠，望向那片被切割得支离破碎的天空，脑中反复回响着樵夫留下的那几个字。"
                },
                {
                    "角色": "美猴王",
                    "内容": "等等……灵台、方寸……这不都在“心”上么？"
                },
                {
                    "角色": "美猴王",
                    "内容": "斜月……三星……那不也是个“心”字？"
                },
                {
                    "角色": "美猴王",
                    "内容": "哈哈！原来如此！原来如此！这神仙，是在跟我打哑谜呢！"
                },
                {
                    "角色": "美猴王",
                    "内容": "求道先修心……有意思，真有意思！"
                },
                {
                    "角色": "旁白",
                    "内容": "一种豁然开朗的喜悦驱散了所有的疲惫。他不再被脚下的崎岖所困，身体仿佛轻盈了许多，几个纵跃便攀上了一处山坡的顶端。视野在此刻瞬间开阔。"
                },
                {
                    "角色": "美猴王",
                    "内容": "前面那是什么？……是了！就是这里！这股清气，错不了！"
                },
                {
                    "角色": "旁白",
                    "内容": "洞门紧闭，静谧无声。崖头立着一块三丈多高的石牌，岁月在上面留下了青苍的痕迹，但那十个大字却仿佛蕴含着某种力量，穿透了时光的薄雾，清晰地映入他的眼帘。"
                },
                {
                    "角色": "美猴王",
                    "内容": "让我看看……灵台方寸山，斜月三星洞……哈哈！一字不差！我孙悟空，终于寻到了！"
                }
            ]
        },
        {
            "场景": 6,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "是谁在此喧哗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "仙童！仙童！是我，一个寻仙问道的弟子！不敢在此叨扰。"
                },
                {
                    "角色": "仙童",
                    "内容": "寻道的？……我家师父正在坛上讲法，还未说完，却忽然让我出来开门，说是有个修行的到了，叫我接待。想来就是你了？"
                },
                {
                    "角色": "美猴王",
                    "内容": "是我，是我！劳烦仙童引路！"
                },
                {
                    "角色": "仙童",
                    "内容": "那你随我进来吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王整理衣襟，随仙童深入洞府。只见其内层层叠叠，琼楼玉宇，竟是别有一番洞天。行至瑶台之下，便见菩提祖师高坐台上，周遭侍立着三十余位仙人，气度庄严。猴王不敢抬头，俯身便拜，额头触及冰冷的石地，在空旷的殿中连连叩首。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "台下跪着的，是何方人物？报上名来。"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子是东胜神洲傲来国花果山水帘洞人氏，特来拜师，恳求师父收录门下，学个长生不老之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哼，一派胡言！你那东胜神洲，与我这里隔着两重汪洋，还有一整个南赡部洲。你一个山野猢狲，凭何而来？休要在我面前耍什么花样！"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子句句属实，绝无虚言！弟子是乘着木筏，飘洋过海，历经十数年风霜雨雪，才寻到此地的！求师父明察！"
                },
                {
                    "角色": "旁白",
                    "内容": "殿内一时沉寂，只有猴王粗重的喘息。台上，祖师的目光如两道无形的利剑，审视着这个跪伏在地、浑身还带着海风咸涩气息的生灵。那目光里没有怜悯，只有探究，似乎要将他从里到外看个通透。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哦？十数年……你且抬起头来。你既是来求道，可有姓氏？父母何在？"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子……弟子没名没姓，也无父母。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哼。人无父母，难道是树上结的，石里长的？"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子不敢欺瞒师父，我正是从花果山顶一块仙石中迸裂而出。"
                },
                {
                    "角色": "旁白",
                    "内容": "此言一出，祖师眼中那审视的严厉悄然褪去，代之而起的是一丝难以察觉的惊异与了然。他终于明白，眼前这猢狲的来历，并非凡俗，而是与这方天地同根同源。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "原来是天地所生……倒也奇特。你起来，走两步我看看。"
                },
                {
                    "角色": "美猴王",
                    "内容": "是，师父。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王听令，立刻起身，连蹦带跳地走了两圈，动作轻捷，野性未脱，那一身急于求道的虔诚下，终究还是山林间无拘无束的根骨。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你身形虽鄙，却像个食松果的猢狲。也罢，我便给你起个姓氏。"
                },
                {
                    "角色": "美猴王",
                    "内容": "谢师父！弟子愿闻其详！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你本是猢狲，那“猢”字去了兽旁，是个“古月”。古者，老也；月者，阴也。老阴不能化生，不合长生之道。我今赐你姓“孙”，这“孙”字去了兽旁，是个“子系”。子者，儿男；系者，婴细。正合那婴儿之本论。你便姓孙吧。"
                },
                {
                    "角色": "美猴王",
                    "内容": "姓孙……姓孙……好！好！弟子有姓了！弟子拜谢师父赐姓！"
                },
                {
                    "角色": "旁白",
                    "内容": "“孙”，一个脱离了兽类，归于人形的姓氏。猴王反复咀嚼着这个字，仿佛生平第一次拥有了根。他叩首下去，这一次，不再是单纯的恳求，而是带着新生的喜悦与归属。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我门中有十二个字，乃‘广大智慧真如性海颖悟圆觉’。排到你，正当第十个‘悟’字。我便与你起个法名，叫做‘孙悟空’。"
                },
                {
                    "角色": "美猴王",
                    "内容": "孙……悟……空……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你……可悟了？"
                },
                {
                    "角色": "旁白",
                    "内容": "空，万法皆空，亦是万法之始。这个字仿佛一道灵光，瞬间劈开了他混沌的识海。从一块顽石，到啸聚山林的猴王，再到此刻跪于此地的求道者，一切过往都如云烟散去。从今往后，他不再是那个无名无姓的石猴，而是孙悟空。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "悟了！弟子悟了！哈哈！我有名字了！我叫孙悟空！弟子孙悟空，拜见师父！"
                }
            ]
        },
        {
            "场景": 7,
            "场景剧本": [
                {
                    "角色": "须菩提祖师",
                    "内容": "你既入我门下，至今也有七载。根性已定，今日，我便传你道法。悟空，你想学些什么？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "全凭师父教诲，弟子不敢妄求。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "也罢。我教你‘术’字门中之道，如何？请仙扶鸾，问卜揲蓍，可知趋吉避凶。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "此道，可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "不能。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不学，不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "那便教你‘流’字门中之道？读经念佛，朝真降圣，此乃三教圣人之流。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，如此，可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "亦不能。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不学！不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哼。那么，‘静’字门中之道？休粮守谷，参禅打坐，此为清净无为之功。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "请问师父，这般可得长生否？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "亦不过是延年益寿，谈何长生。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "那弟子不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "也罢！那便教你‘动’字门中之道。采阴补阳，烧茅打鼎，以此固本培元。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "这……可得长生么？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "犹如镜中花，水中月。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，既然是镜花水月，抓不着，捞不起，那还是不学了。"
                },
                {
                    "角色": "旁白",
                    "内容": "讲坛之上，祖师的脸色沉了下来，他从座位上霍然起身。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你这猢狲！这也不学，那也不学，究竟想怎样！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师走下高台，手中不知何时多了一把戒尺。他行至悟空面前，对着那颗毛茸茸的头颅，不轻不重，敲了三下。随后，祖师倒背着手，一言不发地走入内院，将中门在身后合拢，把一众惊愕的弟子撇在了门外。"
                },
                {
                    "角色": "仙人甲",
                    "内容": "完了，完了……师父他老人家真动怒了！"
                },
                {
                    "角色": "仙人乙",
                    "内容": "你这泼猴，好生无礼！师父传你大道是你的造化，怎敢如此顶撞！"
                },
                {
                    "角色": "仙人丙",
                    "内容": "这下师父闭了中门，我看你这祸事如何了局！"
                },
                {
                    "角色": "仙人甲",
                    "内容": "悟空！你还愣着作甚？还不快跪下，向着中门磕头请罪！或许师父还能消气！"
                },
                {
                    "角色": "旁白",
                    "内容": "责备与惊慌之声四起，讲堂内一片嘈杂。唯独被斥责的悟空，跪在原地，脸上不见丝毫恼怒。众人的言语如流水分过山石，未在他心上留下一丝痕迹，他琢磨的，只是师父那三下敲击，和那扇紧闭的门。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "多谢师兄关心。"
                },
                {
                    "角色": "仙人乙",
                    "内容": "关心？你看他！脸上竟然还带着笑！我看你是被师父打傻了！"
                },
                {
                    "角色": "仙人丙",
                    "内容": "真是个不知好歹的畜生！我们离他远点，免得被他连累！"
                },
                {
                    "角色": "仙人甲",
                    "内容": "走走走，别管他了，让他自己在这儿领罚吧！"
                },
                {
                    "角色": "旁白",
                    "内容": "师兄弟们悻悻散去，偌大的讲堂重归寂静。悟空抬起头，望着那扇隔绝内外的大门，眼中的迷雾散尽，透出澄澈的光。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "三下……三更……后门……嘿。师父，弟子……悟了。"
                }
            ]
        },
        {
            "场景": 8,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "夜色如墨，月光滤过洞府的石窗，在地上投下斑驳的冷辉。祖师的卧房内一片沉寂，只闻得均匀绵长的呼吸声。悟空蹑足潜行，衣袂不带一丝风声，悄然跪倒在榻前，将自己的身形缩成一团虔诚的影子。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子在此跪候多时了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "这猢狲，你不在前院好生安睡，深夜潜入我这里，所为何事啊？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父昨日在坛前分付，三更时分，由后门传我大道。弟子不敢不来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "呵呵……果然是个天地生成的灵物，竟能解我盘中之谜。此处无有外人，你近前来，仔细听了。我便传你长生妙法。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子……永世不忘师父大恩！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄……休漏泄，体中藏，汝受吾传道自昌……"
                },
                {
                    "角色": "旁白",
                    "内容": "长生之诀，如同一粒种子，在悟空体内无声地生根发芽。转眼，又是三年。这期间，他于人前扫地应答，于人后则依循口诀，默默调息炼神，一身的灵气被收敛得愈发精纯。这一日，祖师于高台讲法，话音一顿，目光扫过众弟子。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空何在？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子在。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "这几年，你修的道，如何了？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "回禀师父，弟子近来法性颇通，根源也日益坚固了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你既已通法性，明根源，神体已入……却还需防备一件事。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父此言差矣。常闻道高德隆者，与天同寿，百病不生。如何还有什么要防备的？"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师脸上的笑意敛去，目光变得深邃而凝重，仿佛穿透了眼前的弟子，看到了遥远未来中注定降临的劫数。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "此乃非常之道。你所学之法，夺天地之造化，侵日月之玄机。丹成之后，鬼神难容。虽能驻颜益寿，但到了五百年后，天降雷灾打你。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "雷灾？弟子躲得过么？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你若见性明心，预先躲避，可与天齐寿。躲不过，就此绝命。再五百年，天降火灾烧你。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "是凡火吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "非天火，非凡火，此唤‘阴火’。自你涌泉穴下烧起，直透泥垣宫，五脏成灰，四肢皆朽，千年苦功，一时俱为灰烬！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "这……还有吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "再五百年，又降风灾吹你。非东南西北风，唤作‘赑风’。自你囟门中吹入，贯彻丹田，骨肉消疏，身体自解！悟空，你怕不怕！"
                },
                {
                    "角色": "旁白",
                    "内容": "长生的愿景在“三灾”的描述下寸寸碎裂。悟空只觉一股寒意从脊骨升起，瞬间传遍四肢百骸。那与天同寿的期许，此刻听来更像一个横亘千年的诅咒。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……弟子闻言，遍体生寒！万望师父垂怜，传我躲避三灾之法，弟子纵然粉身碎骨，也感念大德！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "此事倒也不难。只是你与旁人不同，传不得。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我头顶天，脚踏地，九窍四肢，五脏六腑，与人何异？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你虽像人，却少腮。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子虽然没腮，却多了个颊囊，也算将就得过。求师父开恩！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "也罢。我有两种法术可避三灾。一是天罡数，有三十六般变化。一是地煞数，有七十二般变化。你待学哪一种？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子愿多学些，学地煞数便好。"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师的声音再次压低，化作一丝几不可闻的气流，钻入悟空的耳中。那不是凡间的言语，而是一串串解构万物、重塑自身的密语。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "既如此，你再近前来。我将这七十二变的口诀，暗暗传与你……"
                }
            ]
        },
        {
            "场景": 9,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "灵台方寸山的一个夏日午后，光影在松针间筛落成斑驳的碎金。几位师兄弟在树下闲谈，起初还是论道讲经，但话锋一转，便带着几分试探与好奇，若有若无地飘向了那个新来的石猴。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "悟空，师父那晚……是单独给你开了小灶吧？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师兄说笑了。师父是看我生性愚钝，才多费心提点了几句。"
                },
                {
                    "角色": "师兄乙",
                    "内容": "提点几句？那可是躲三灾的七十二变，是大道真传。我们这些人，可没这个福分。不知你……到底领悟了多少？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父的教诲，自然是日夜记在心里，不敢有半分懈怠。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "记在心里是一回事，练成又是另一回事。这等玄妙法门，一变就耗尽心神，我等穷尽一生也难得其一。你不会……只是记住了口诀吧？"
                },
                {
                    "角色": "师兄乙",
                    "内容": "就是。光说不练，谁不会呢？除非你当场变个什么，给我们开开眼界？也让我们见识见识师父的无上妙法。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "这……师父有言在先，道不传非人，法不示无缘。不可轻易炫耀。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "哎，都是自家师兄弟，又不是外人。还是说……你根本就没学会，怕当众露了馅儿？"
                },
                {
                    "角色": "旁白",
                    "内容": "那句“露了馅儿”如同一根芒刺，扎进了孙悟空天生的傲骨里。师父“不可炫耀”的告诫，在此刻被师兄弟们夹杂着嫉妒与轻蔑的目光一激，瞬间化作了泡影。一股不甘与好胜的妖性，压过了初修的道心。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师兄这是哪里话！也罢！今天就让你们瞧个新鲜。说吧，要我变成什么？"
                },
                {
                    "角色": "师兄乙",
                    "内容": "嗯……既然是在松树下，就变成咱们眼前这棵苍松吧。这松树最见风骨，也最考验功力，可不好变。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！师兄们可看仔细了！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空口念真言，手捏法诀，身形在一瞬间变得模糊。那并非简单的消失，而是一种物质性的重组与溶解。他的轮廓向内坍缩，随即又向外舒展，骨骼化为虬结的枝干，毛发抽长成细密的松针，伴随着一阵细微的、仿佛草木生长的声音。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "咦？悟空呢？怎么一转眼人就不见了？"
                },
                {
                    "角色": "师兄乙",
                    "内容": "天啊！快看！那儿……多出来一棵松树！枝干、树皮、松针……跟真的一模一样！分毫不差！"
                },
                {
                    "角色": "旁白",
                    "内容": "那声音分明是孙悟空的，却又带着木质的共鸣，仿佛是从松树最深处的年轮里传出来的，戏谑而得意。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师兄们，我这手艺如何？"
                },
                {
                    "角色": "师兄甲",
                    "内容": "好猴子！真是好猴子！神乎其技！"
                },
                {
                    "角色": "师兄乙",
                    "内容": "简直匪夷所思！当真学到了真传！"
                },
                {
                    "角色": "旁白",
                    "内容": "喧哗与喝彩声惊扰了山中的清净，也惊动了洞府深处的那个人。一个身影无声无息地出现在松林边缘，须菩提祖师手持拐杖，面沉如水。他只是站在那里，周遭的空气便仿佛凝固了，所有的笑声戛然而止。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "在此喧哗，成何体统！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "禀尊师，我等在此聚会论道，并无外人喧哗。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "论道？我听到的，为何是喝彩与哄笑？修行之人，口开神气散，舌动是非生。你们在此笑什么！"
                },
                {
                    "角色": "师兄甲",
                    "内容": "不敢隐瞒师父……是……是孙悟空在此演练变化之术。他变成了一棵松树，弟子们一时惊叹，才高声惊扰了尊师，望师父恕罪。"
                },
                {
                    "角色": "旁白",
                    "内容": "众师兄弟噤若寒蝉，纷纷退去，只留下孙悟空恢复原形，独自站在空地中央。祖师的目光如两道寒冰，将他牢牢钉在原地，那目光里没有平日的温和，只有一种洞穿肺腑的失望与严厉。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，你过来。我问你，你为何要变那松树？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子……弟子只是想让师兄们看看，所学未曾荒废……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我教你的是躲灾避劫的法门，你却拿来当做在人前换取喝彩的戏法！你这般卖弄，与街头耍猴的有何区别？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子……弟子知错了……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你记住，神通一旦显露，灾祸便随之而来。今日你为了一声喝彩变棵松树，他日，就可能为了一个虚名，捅破这天！"
                }
            ]
        },
        {
            "场景": 10,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "松树变回了猴王，喧闹的喝彩声却在祖师冰冷的目光下凝结成一片死寂。悟空脸上的得意还未褪去，就已被一种不祥的预感攫住，他跪倒在地，声音里带着孩童般的惶恐。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子再也不敢了！求您……求您就宽恕弟子这一次！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "宽恕？知错，不代表能改。你的天性，就像这山间的野火，一旦点燃，连你自己都控制不住。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子能改！弟子一定改！只要师父肯教，弟子什么都肯学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我教不了你了。留你在此，这方寸山，迟早要被你的“喝彩声”引来天大的祸事。"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师的话语平静，却像一把无形的利剑，斩断了悟空最后的侥幸。山风吹过，他第一次感到这仙山的风，竟是如此寒意彻骨。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……您这是……要赶我走？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "不是赶你走，是让你走。你从哪里来，回哪里去吧。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "可是……我离家二十年，好不容易才寻到仙山……师父的大恩，弟子还没来得及报答！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "不必报了。你日后不惹祸，不连累我，就是对我最大的报答。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "为什么？就因为一棵松树？就因为几声喝彩？这就要断了弟子的修行路吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "因为我看到了你的将来。你这颗心，装不下清规戒律，只装得下齐天大圣的野心。"
                },
                {
                    "角色": "旁白",
                    "内容": "“齐天大圣”。四个字，如同一道惊雷，劈开了时空的迷雾，让祖师瞥见了未来的血海与烽烟。而此刻的悟空，只能感到这四个字滚烫的重量，却无法洞悉其中蕴含的，究竟是荣耀，还是宿命的枷锁。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子……弟子不懂……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你此去，定生祸端。记住，不许对任何人说，你是我的徒弟。我教不了你收敛心性，只能教你如何独自面对。这，是我能给你的最后一课。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "还有。你若对任何人泄露此地，泄露我，哪怕只说出半个字，我便顷刻知晓。届时，我必将你这猢狲剥皮锉骨，神魂贬入九幽之地，让你万劫不得翻身！"
                },
                {
                    "角色": "旁白",
                    "内容": "这番话不再是训诫，而是一道刻入神魂的咒言。每一个字都带着千钧之力，砸在悟空心头，将他与灵台方寸山之间最后的情分彻底碾碎。他终于明白，从今往后，天地虽大，却再无师父。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "……弟子，绝不敢提师父半字。只说……是弟子自己学来的。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "去吧。"
                },
                {
                    "类型": "旁白",
                    "内容": "他磕了最后一个头，再无言语。一个筋斗，翻出了十万八千里，也翻出了此生的师徒缘分。身后，是再也回不去的斜月三星洞；眼前，是阔别二十年的花果山。他学成了长生，却被逐出了道法之门；他炼就了通天本领，却成了天地间最孤独的一个。那个寻仙问道的美猴王走了，此刻归来的，是孙悟空。"
                }
            ]
        }
    ]
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

    # 剧本冲突
    #script_conflict_escalation_gemini = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '旁白', '内容': '混沌未分之前，宇宙只是一片虚无。直至盘古开天，清浊始判。东胜神洲之上，有一仙石，暗合周天之数，上有九窍八卦之形。它吸食日月精华，孕育着一个撼动天地的生命。这一日，仙石轰然迸裂，石卵迎风而化，一个石猴就此诞生。他初睁的双目中，射出两道金光，撕裂云海，直冲斗府，惊动了九重天上的凌霄宝殿。'}, {'角色': '玉皇大帝', '内容': '（慵懒中带着一丝不耐）何事惊扰？又是哪方星君失仪，还是下界又有妖物作乱？'}, {'角色': '千里眼', '内容': '（语气急促，心有余悸）陛下！臣所见，非兵戈，非妖祸……是……是一道撕裂天纲的金光！'}, {'角色': '顺风耳', '内容': '（声音微颤）臣所闻，亦非雷鸣！是万物为之死寂的一瞬，而后一声石裂，其音清越，竟盖过了九天风雷！'}, {'角色': '玉皇大帝', '内容': '（略微坐直，语带审视）哦？能惊动你们二将，倒有些意思。说清楚，是何方神圣，敢在朕的眼皮底下，射冲斗府？'}, {'角色': '千里眼', '内容': '（迟疑，仿佛在叙述一件荒唐之事）陛下……那金光，非源自法宝，也非神圣。它……它来自一只……刚从石头里蹦出来的……猴子。是它的双眼！'}, {'角色': '旁白', '内容': '凌霄宝殿上一片死寂。片刻后，宝座上传来玉帝一声短促、干涩的轻笑。'}, {'角色': '玉皇大帝', '内容': '（轻蔑地）呵，一只猴子？你们二人，执掌天庭耳目亿万年，竟被一只下界野物晃了眼？'}, {'角色': '顺风耳', '内容': '（连忙辩解）陛下，此猴确非凡物！乃天地精华所生！此刻金光已敛，正在山涧饮水，并无他异。'}, {'角色': '玉皇大帝', '内容': '（挥了挥手，彻底失去兴趣）天地精华？那又如何。天地间精华多了，化作山川，化作河海，偶尔漏下些许，生个精怪，也只算造化的一桩趣闻。算不得数，算不得数。传朕旨意，此事不必再报。'}, {'角色': '旁白', '内容': '玉帝的声音在殿内回响，威严而冷漠。天庭的秩序，在此刻化为一种对未知生命最极致的傲慢。对于这桩日后将颠覆三界的大事，此刻的定义，不过是“算不得数”四个字。'}, {'角色': '玉皇大帝', '内容': '随他去吧。'}, {'角色': '千里眼', '内容': '（和顺风耳对视一眼，压下满心惊疑）……遵旨。'}]}, {'场景': 2, '场景剧本': [{'角色': '旁白', '内容': '山中无岁月，石猴与群猴为伴，嬉戏山林，自在逍遥。这一日暑气蒸腾，群猴玩耍至一处山涧，只见一道白练从断崖上倾泻而下，水声轰鸣，震彻山谷。'}, {'角色': '众猴', '内容': '（一个苍老、谨慎的声音）这瀑布后面，水汽森森，必有不祥。我们还是离远些，安分度日才是正道。'}, {'角色': '众猴', '内容': '（一个年轻、不安的声音）可我们总是担惊受怕，哪有个安稳的家？要是那后面……是个能躲避风雨的地方呢？'}, {'角色': '众猴', '内容': '（苍老的声音，带着嘲讽）躲避？哼，只怕是躲进了虎豹的嘴里！谁要是嫌命长，就尽管去。要是谁有本事进去，还能活着出来，证明自己不是个蠢货，我等就拜他为王！'}, {'角色': '众猴', '内容': '（窃窃私语）这……谁敢拿性命开玩笑……'}, {'角色': '孙悟空', '内容': '（声音洪亮，打破了所有议论）我去。'}, {'角色': '众猴', '内容': '（苍老的声音，充满质疑）你？一个石头里蹦出来的东西，懂得什么是生死？这不是顽童的戏耍，水帘之后是真正的死亡！'}, {'角色': '孙悟空', '内容': '（冷笑一声）正因为我生于顽石，才不屑于像你们一样，活得像一摊烂泥。你们畏惧死亡，我只好奇它究竟是什么味道。等着，我为你们带回一个全新的世界，或者……一个让你们永远闭嘴的答案。'}, {'角色': '旁白', '内容': '话音未落，石猴的身影已如离弦之箭，迎着那千钧水势纵身跃入。冰冷的激流瞬间将他吞没，外界的喧嚣顷刻间化为一片沉寂的轰鸣。'}, {'角色': '孙悟空', '内容': '（自语，先是喘息，随即转为狂喜）这……这里面竟然没有水！是一座铁板桥！好个去处！石锅、石灶、石床、石凳……样样齐全！石碣上还有字……花果山福地，水帘洞洞天。哈哈哈哈！天命！这就是我的天命！'}, {'角色': '旁白', '内容': '瀑布之外，时间仿佛被拉长。方才还喧闹的猴群渐渐安静下来，只剩下水声依旧。它们焦灼地望着那片白茫茫的水帘，等待着一个未知的结局。'}, {'角色': '众猴', '内容': '（苍老的声音，带着一丝不易察觉的悔意）完了……他被水冲走了。是我们……用言语逼死了他。'}, {'角色': '旁白', '内容': '就在众猴陷入绝望与自责时，那道水帘猛地向外一分，一个湿淋淋的身影破水而出，稳稳落在岸边。他抹去脸上的水珠，眼中闪烁着前所未有的光芒，那是一种混杂着征服、狂喜与不屑的眼神。'}, {'角色': '孙悟空', '内容': '（声音不大，却压过了瀑布的轰鸣）你们的王，回来了。'}, {'角色': '众猴', '内容': '（震惊地）出来了！他真的出来了！里面到底是什么？'}, {'角色': '孙悟空', '内容': '（语带诱惑与自豪）你们口中的“死亡”背后，是一个天造地设的王国！宽敞得足以容纳我们整个族群，锅碗瓢盆一应俱全，再不用畏惧风霜，再不用躲避豺狼！'}, {'角色': '孙悟空', '内容': '那里的石碑上清清楚楚刻着十个大字：花果山福地，水帘洞洞天！'}, {'角色': '孙悟空', '内容': '（提高了声调，带着不容置疑的威严）那不是上天赐予我们的！而是我，为你们夺来的安身之所！你们还在等什么？'}, {'角色': '众猴', '内容': '（先前苍老的声音，此刻充满敬畏与羞愧）你进出自如，未伤分毫，乃是有大本事、大勇气的！我们……我们有眼无珠！请受我等一拜！'}, {'角色': '众猴', '内容': '（山呼海啸般）拜见千岁大王！拜见千岁大王！'}, {'角色': '旁白', '内容': '“千岁大王”的呼喊声在山谷间回荡。石猴坦然受了这一拜，他站上高处，目光扫过自己的第一批臣民。从混沌中诞生的顽石，此刻终于用自己的意志，为自己赢得了名号与归属。'}, {'角色': '孙悟空', '内容': '（缓缓地，一字一顿）都起来吧。从今日起，记住我的名号——美！猴！王！'}]}, {'场景': 3, '场景剧本': [{'角色': '众猴', '内容': '（欢呼，嘈杂）大王千岁！千岁！千千岁！'}, {'角色': '旁白', '内容': '水帘洞内，石桌上堆满了山中新摘的奇珍异果，猴儿们捧着椰壳做的酒杯，喧闹声几乎要掀翻洞顶。然而，在这片欢腾的中心，端坐于石座上的美猴王，眼神却穿透了眼前的喧嚣，落在了某处虚空。杯中的琼浆，映不出他此刻脸上的笑意，只映出一片深不见底的寂静。'}, {'角色': '孙悟空', '内容': '（压抑的哭声，接着是一声沉重的叹息，将手中的酒杯狠狠掷在地上）'}, {'角色': '众猴', '内容': '（音乐和喧闹声戛然而止）大王？您这是……是谁惹您不快了？'}, {'角色': '孙悟空', '内容': '（声音低沉，带着一丝自嘲的冷笑）不快？不。恰恰相反，我看着你们……看着这满洞的欢声笑语，只觉得荒唐，荒唐得可笑！'}, {'角色': '众猴', '内容': '（困惑且不满）大王！我们今日有酒有果，自由自在，这难道不是天大的快活？您为何要说这种话，扰了大家的兴致？'}, {'角色': '孙悟空', '内容': '（声音陡然拔高，充满质问）快活？自由？（冷笑）你们管这叫自由？我们不过是阎王老子后花园里，一群还没到时候采摘的果子！他想什么时候来收，我们就得什么时候烂掉！你们告诉我，这算哪门子的自由！'}, {'角色': '众猴', '内容': '（被吓住，开始窃窃私语）阎王……'}, {'角色': '孙悟空', '内容': '（步步紧逼，声音里充满了挣扎与不甘）你们看看这山间的花，开了又谢！看看我们自己，今天称王称霸，百年之后呢？还不是一抔黄土，一副枯骨！这“千岁大王”的名号，不过是写在阎王那本破账上的一个笑话！你们还在这里饮酒作乐，难道就没想过，死亡的钩子，已经悬在每个人的脖子上了吗？！'}, {'角色': '众猴', '内容': '（彻底崩溃，哭声四起）呜哇……大王别说了！我们都要死吗？这可怎么办啊……'}, {'角色': '旁白', '内容': '群猴的哀哭声在湿冷的洞壁间回荡，死亡的阴影第一次笼罩了这座无忧无虑的王国。就在这片混乱中，一只毛发已略显灰白的通背猿猴从猴群中缓缓走出，他拨开身前啼哭的幼猴，目光清明而沉静，仿佛早已洞悉了王的烦恼。'}, {'角色': '博学的猿猴', '内容': '（声音苍老而有力，压过所有哭声）都住口！大王，能看到这一层，感到这般恐惧，并非您的不幸，而是您的道心初开。这恐惧，是智慧的开始。'}, {'角色': '孙悟空', '内容': '（抓住救命稻草一般，急切地）老猿，你的意思是……这绝路，有解？这阎王，有法可躲？'}, {'角色': '博学的猿猴', '内容': '天地万物，皆在轮回之内，受他管辖。唯有三者，能超脱其外。'}, {'角色': '孙悟空', '内容': '（眼神一亮）哪三者？！快说！'}, {'角色': '博学的猿猴', '内容': '乃是佛、仙、与神圣。此三者，跳出三界，不入五行，早已将自己的名字从那生死簿上抹去，故能与天地同寿。'}, {'角色': '旁白', '内容': '佛、仙、神圣。三个词，仿佛三道惊雷，劈开了美猴王心中混沌的迷雾。长生不死的愿景，第一次如此清晰地展现在他眼前，那是一种足以让他抛下王位、抛下所有安逸的巨大诱惑。'}, {'角色': '孙悟空', '内容': '（声音颤抖，但充满了前所未有的决心）佛……仙……神圣……他们在何处？'}, {'角色': '博学的猿猴', '内容': '不离此世，只在阎浮世界之中，古洞仙山之内。'}, {'角色': '孙悟空', '内容': '（猛地站起，声音如洪钟，是对恐惧的宣战）好！好一个跳出三界外！明日，我就辞别你们，下山去！哪怕走遍天涯海角，我也要访得真仙，学一个长生不老之法！我非要把那阎王的生死簿，烧个干干净净！'}]}, {'场景': 4, '场景剧本': [{'角色': '旁白', '内容': '决心一定，猴王告别了涕泣的群猴，独自驾一叶扁舟，飘入了茫茫大海。岁月在风浪间流逝，当他踏上南赡部洲的陆地，山野的自由已被市井的烟火彻底隔绝。他褪下顽石般的野性，笨拙地裹上名为“体面”的布料，学着人的模样，将自己投入这片追逐名利的红尘浊流。'}, {'角色': '孙悟空', '内容': '（内心）这布料裹在身上，真是束缚…他们走路是这般模样？说话要如此拐弯抹角？哼，为了学那长生之法，暂且忍耐一番。'}, {'角色': '货郎', '内容': '上好的绫罗，上好的绸缎！客官，来一件吧？穿上它，保管你人前显贵，光宗耀祖！'}, {'角色': '孙悟空', '内容': '（上前扯住布料，凑近嗅了嗅，眼神轻蔑）就这？用它裹住筋骨，就能骗过阎王老子了？'}, {'角色': '货郎', '内容': '（被问得一愣，随即恼怒）你这人胡说八道什么！穿得体面，才有钱赚！有了钱，要什么没有？你懂什么！'}, {'角色': '孙悟空', '内容': '我懂？（冷笑）我懂这东西遮不住骨头发烂，也挡不了皮肉枯干。你们用钱买来的青春，不过是给自己糊上一层新鲜的泥巴。'}, {'角色': '货郎', '内容': '疯子！真是个疯子！不买就滚，别在这咒我生意！滚！'}, {'角色': '旁白', '内容': '商贩的驱赶，像一根无形的针，刺破了他对“道”的朴素幻想。他沉默地穿过酒肆，走过勾栏，那些被称作“礼义”的规矩，如蛛网般缠绕着他天生的筋骨，每一步都走得滞涩而疏离。'}, {'角色': '书生甲', '内容': '此番若是金榜题名，定要在那朝堂之上，留我千古声名！此方为不朽！'}, {'角色': '书生乙', '内容': '正是！大丈夫生于世，当求封妻荫子，名垂青史。死后亦能为人称颂，与天地同寿！'}, {'角色': '孙悟空', '内容': '（突然在旁大笑，笑声尖锐刺耳）哈哈哈哈！与天地同寿？你们的寿，就是几页发霉的纸，几声酒嗝里的叹息？可笑至极！'}, {'角色': '书生甲', '内容': '（勃然大怒）大胆狂徒！哪里来的野人，敢在此污我等宏愿！'}, {'角色': '孙悟空', '内容': '（逼近一步，眼神凶狠）我问你，坟头草长到三尺高的时候，你的‘千古声名’，能替你挡一夜的雨吗？将来吃你尸骨的蛆虫，会在乎你做的文章是工整还是潦草吗？！'}, {'角色': '书生乙', '内容': '（惊恐后退）粗鄙！粗鄙不堪！简直是禽兽之言！有辱斯文，快，我们走，莫与此獠费话！'}, {'角色': '旁白', '内容': '年复一年，相似的场景，不同的人。他看到的，听到的，无外乎金榜题名，衣锦还乡。人们在短暂的生命里，用权力和虚名筑起一座座华美的监牢，却心安理得地，等着自己的尸体被抬进早就备好的棺材。'}, {'角色': '路人甲', '内容': '我们攒够了钱，总算能买下城东那座大宅子了，这辈子，就算安稳了。'}, {'角色': '路人乙', '内容': '是啊，有了家，就有了根，再不用颠沛流离了。'}, {'角色': '孙悟空', '内容': '（幽幽地在他们身后说）根？你们的根扎在黄土里，我的根长在石头里。你们的宅子是坟，我的山才是家。你们听……这风里，有没有勾魂鬼的笑声？'}, {'角色': '路人甲', '内容': '（吓得一哆嗦，猛地回头）你……你是什么东西？！大白天说这种晦气话！'}, {'角色': '路人乙', '内容': '别理他，快走快走，八成是个索命的恶鬼！呸！真倒霉！'}, {'角色': '旁白', '内容': '疯癫的，究竟是谁？喧嚣的人声在耳边退潮，留下巨大的空洞。九年的光阴，像一场荒诞的长梦，此刻终于到了梦醒时分。他低头看看身上这件模仿来的衣袍，再抬头望向被屋檐切割得支离破碎的天空，一种源自骨血的孤独，让他几乎想放声长啸。'}, {'角色': '孙悟空', '内容': '（低声自语，声音颤抖，带着压抑的狂怒）这就是人……把枷锁叫作衣冠，把虚名叫作不朽，把坟墓……叫作根！学他们走路，学他们说话，学他们把头低下，把腰弯下！这身皮囊已经够拘束了，还要再套上一层又一层的壳！'}, {'角色': '孙悟空', '内容': '他们把转瞬即逝的沙子当成宝贝，却对头顶那永恒的黑暗视而不见！'}, {'角色': '孙悟空', '内容': '九年了！我走遍了这南赡部洲，从日出到日落，看尽了他们的悲欢离合。他们争抢的，不过是沙滩上的一捧沙；他们夸耀的，不过是晨光里的一颗露。'}, {'角色': '孙悟空', '内容': '没有一个人，肯抬头看看天，问一问风，这生与死的边界，到底能不能跨过去！'}, {'角色': '孙悟空', '内容': '道，不在此处！此地，已是一座巨大的坟场！我要逃出去！哪怕是葬身风浪，也比在这死水里腐烂要干净！'}]}, {'场景': 5, '场景剧本': [{'角色': '旁白', '内容': '石猴登上高山，只见林海茫茫，前路难觅。正当他心中怅惘之际，一阵歌声自幽深的谷底传来，清越悠扬，仿佛不属于这凡尘俗世。'}, {'角色': '樵夫', '内容': '（歌声）观棋柯烂，伐木丁丁，云边谷口徐行。卖薪沽酒，狂笑自陶情。苍径秋高，对月枕松根，一觉天明。认旧林，登崖过岭，持斧断枯藤。收来成一担，行歌市上，易米三升。更无些子争竞，时价平平。不会机谋巧算，没荣辱，恬淡延生。相逢处，非仙即道，静坐讲《黄庭》。'}, {'角色': '旁白', '内容': '歌声一歇，石猴循声拨开藤蔓，终于在林中见到了歌者——一个衣衫朴素的樵夫，正倚着一棵枯松歇息。石猴压抑着寻觅十年的焦躁，带着一丝审视，跳上前去。'}, {'角色': '孙悟空', '内容': '老神仙！你可让我好找！'}, {'角色': '樵夫', '内容': '（叹了口气，看看自己磨出老茧的手）神仙？客人，你看我这双手，像是能点石成金的手吗？我若真是神仙，又怎会为三升米，在这山里和枯木较劲？'}, {'角色': '孙悟空', '内容': '少来这套！我刚刚听得真切，你唱的是《黄庭》真言！那是修仙问道的根基！你藏得够深啊，穿着凡人衣，唱着神仙曲，是何居心？'}, {'角色': '樵夫', '内容': '（一丝苦笑）居心？我的居心，就是哄我这颗烦躁的心罢了。这曲子，叫《满庭芳》，是一位真正的神仙邻居，可怜我劳碌，教我解烦的。我唱它，不是为了成仙，是为了在斧头砍进木头的时候，心里能有片刻的清静。'}, {'角色': '孙悟空', '内容': '神仙邻居？他既有通天之能，为何不点化你，让你也得个长生不老？难道是你资质愚钝，他瞧不上你？'}, {'角色': '樵夫', '内容': '（眼神变得锐利，直视着孙悟空）长生？客人，你可知长生是什么滋味？是看着身边人一个个老去，是守着一座空山万年孤寂。他问过我，可我娘还在。她晚上咳嗽，我得给她递水；她想吃口热粥，我得去给她烧火。长生再好，能换回我娘叫我一声‘儿’吗？我这点尘缘，就是我的道。你的道，在天上；我的道，在脚下。'}, {'角色': '旁白', '内容': '石猴愣住了。他第一次听到，有人会拒绝他梦寐以求的东西。他看着樵夫布满老茧的手，忽然觉得那柄斧头，竟也有千钧之重。'}, {'角色': '孙悟空', '内容': '（语气变得恳切）……那位真神仙，住在何处？'}, {'角色': '樵夫', '内容': '（神情恢复平静，用手指着南方的山峦）你若真有此心，倒也不远。顺着这条小路一直往南走，不出十里，便有一座灵台方寸山。山里有一座洞府，唤作斜月三星洞。'}, {'角色': '孙悟空', '内容': '灵台方寸山，斜月三星洞……'}, {'角色': '樵夫', '内容': '那位传我歌词的须菩提祖师，才是真正的活神仙。他座下弟子数十，个个都是修行有成之辈。去吧，你心无挂碍，天生就是走那条路的。'}, {'角色': '孙悟空', '内容': '多谢指点！我这就去！'}, {'角色': '旁白', '内容': '话音未落，石猴已急不可耐地转身向南，身影瞬间没入林中。樵夫望着他消失的方向，悠悠叹了口气，那叹息中，有羡慕，亦有释然。'}, {'角色': '樵夫', '内容': '（喃喃自语）不像我，这把斧头，既是我的牵挂，也是我的归宿。唉，可惜，可惜了……'}]}, {'场景': 6, '场景剧本': [{'角色': '旁白', '内容': '穿过层层叠叠的琼楼玉宇，石猴终于得见瑶台之上的菩提祖师。四周仙众肃立，大殿之内，时间仿佛静止。那是一种混元之初的寂静，足以荡涤尽两重大海的风浪与一座大陆的尘埃。他漫长的、漂泊的追寻，在此刻抵达了终点。'}, {'角色': '孙悟空', '内容': '（声音颤抖，带着哭腔和极度的虔诚）师父！弟子……弟子总算找到您了！'}, {'角色': '须菩提祖师', '内容': '（声音平淡，却如洪钟贯耳，带着审视的威严）聒噪。你是何方妖物？竟敢在此惊扰我讲道。报上你的来历，若有半句虚言，便将你打出山门，永不录用。'}, {'角色': '孙悟空', '内容': '弟子是东胜神洲，傲来国，花果山水帘洞人士！'}, {'角色': '须菩提祖师', '内容': '（冷笑一声）一派胡言。东胜神洲与我这西牛贺洲，隔着几重汪洋，几多险恶？道，不是靠一副伶牙俐齿就能求来的。你这身未脱的野性，这双躁动的眼，看到的不过是海市蜃楼。说！你究竟为何而来？求长生？还是求一个名分？'}, {'角色': '孙悟空', '内容': '（被问到痛处，声音激动起来）弟子不知何为名分！只知生死事大！弟子看过花开花谢，见过同伴老死，那滋味，就像有把刀子在心口上刮！弟子漂洋过海，吃了无数的苦，就是想求一个不死的法子，求一个明白！求师父给条活路！'}, {'角色': '须菩提祖师', '内容': '（沉默片刻，语气稍缓，但依旧严厉）活路？你既无父母，也无姓名，不过是天地间一缕无根的游魂，谈何活路？'}, {'角色': '孙悟空', '内容': '弟子……弟子是从花果山顶上的一块仙石里迸出来的。正因无根，才更要求一个归处！'}, {'角色': '旁白', '内容': '祖师眼中那审视的锋芒悄然敛去，转为一种深长的探究。这并非对一个谎言的勘破，而是对一桩天地奇闻的静观。他示意石猴站起身来。'}, {'角色': '须菩提祖师', '内容': '天生地养……倒是个异数。你起来，走两步我看看。'}, {'角色': '孙悟空', '内容': '是，师父。'}, {'角色': '旁白', '内容': '石猴应声跳起，绕着殿中走了两圈。那步态既非人的拘谨，也非兽的纯然，带着一种未经雕琢的、源自天地鸿蒙的野性与灵气。祖师的目光随着他移动，唇边第一次浮现出一丝若有若无的笑意。'}, {'角色': '须菩提祖师', '内容': '你这形象，是个猢狲。兽类而已，终归是畜生道，谈何修行？也罢。我今日便点化你。‘猢’字，去了兽旁，是个‘古月’。古老，阴沉，死气沉沉，要不得。我给你换个姓……‘孙’。‘孙’字，是‘子’与‘系’。子者，男也；系者，婴也。正合婴儿之本论。你可愿意，舍了那身兽性，从一个‘婴儿’重新开始？'}, {'角色': '孙悟空', '内容': '（大喜过望，声音里满是重获新生的激动）愿意！愿意！弟子愿意！多谢师父！弟子今日总算有姓了！'}, {'角色': '须菩提祖师', '内容': '我门中弟子，排到你这一辈，正好是‘悟’字。我再与你起个法名，便叫‘悟空’。望你了悟世间一切皆空，方能得见真我。你……可明白？'}, {'角色': '旁白', '内容': '一个名字，便是一道因果，一道符咒。从此，这天地间，便有了一只叫孙悟空的猴子。他的悲喜，他的宿命，都将与这两个字，紧紧纠缠。'}, {'角色': '孙悟空', '内容': '（一字一顿，仿佛在宣告自己的新生）悟空……孙悟空！弟子孙悟空，领受师父法名！从今往后，世上再无石猴，只有孙悟空！'}]}, {'场景': 7, '场景剧本': [{'角色': '须菩提祖师', '内容': "悟空。你一心求道，很好。道有三千六百旁门，今日，我便为你开一门。这'术'字门，可有兴趣？"}, {'角色': '孙悟空', '内容': "哦？如何一个'术'字？"}, {'角色': '须菩提祖师', '内容': '请仙扶鸾，问卜揲蓍，能知过去未来，趋吉避凶。如何？'}, {'角色': '孙悟空', '内容': '(轻笑一声) 知道了灾祸什么时候来，却躲不过去，这和伸着脖子等砍头有什么分别？敢问师父，这般道行，可得长生否？'}, {'角色': '须菩提祖师', '内容': '(眼神一沉) 如同壁画上的大饼，中看不中用。'}, {'角色': '孙悟空', '内容': '那便不学。画饼，俺老孙不吃。'}, {'角色': '须菩提祖师', '内容': "……好。那'静'字门呢？参禅打坐，戒语持斋，入定通玄。"}, {'角色': '孙悟空', '内容': '听着像是把自己活活变成一块石头。师父，我就问一句，变成石头，可得长生么？'}, {'角色': '须菩提祖师', '内容': '不过是延缓衰败，如窑中之坯，终有破碎一日。'}, {'角色': '孙悟空', '内容': '一个早碎，一个晚碎。不学，不学！'}, {'角色': '须菩提祖师', '内容': "(压着火气) 哼……你这猴头，当真挑剔！那'动'字门，采阴补阳，炼丹服药，以有为之法夺天地造化。这总该合你心意了吧？"}, {'角色': '孙悟空', '内容': '夺来的东西，终究要还。这采补之术，恐怕是水中捞月，镜里看花。师父，我若学了，是能捞着月亮，还是能摘下花来？'}, {'角色': '须菩提祖师', '内容': '……你这泼猴！'}, {'角色': '旁白', '内容': '祖师的声音骤然冰冷，他从高台上一跃而下，手中不知何时多了一把戒尺。整个讲经堂的空气仿佛都凝固了。'}, {'角色': '须菩提祖师', '内容': '(怒喝) 我以大道示你，你却视之如敝履！这也不学，那也不学，莫非你求仙问道，只是一场儿戏！'}, {'角色': '孙悟空', '内容': '(毫无惧色，叩首) 弟子不敢。弟子所求，唯“长生”二字，若法门不能达此，于我便如尘埃。并非弟子轻慢大道。'}, {'角色': '须菩提祖师', '内容': '好一个“如尘埃”！你上前来！'}, {'角色': '旁白', '内容': '悟空坦然上前，跪在祖师面前。祖师高举戒尺，在众门人惊恐的抽气声中，对着悟空的头，不轻不重，敲了三下。那声音，清脆，沉闷，带着一股不容置疑的威严。'}, {'角色': '众仙', '内容': '(惊呼) 师父动怒了！竟用了戒尺！'}, {'角色': '众仙', '内容': '这猴头完了，彻底触怒师父了！'}, {'角色': '须菩提祖师', '内容': '(冷哼一声) 哼。'}, {'角色': '旁白', '内容': '祖师看也不看跪在地上的悟空，将戒尺往身后一背，倒背着双手，拂袖而去。他大步流星地走入中门，随着“砰”的一声巨响，厚重的大门死死关上，隔绝了内外。'}, {'角色': '众仙', '内容': '(一个弟子战战兢兢地) 师……师父就这么走了？把我们都撇下了？'}, {'角色': '众仙', '内容': '(转向悟空，怒斥) 都怪你这泼猴！不知天高地厚！'}, {'角色': '众仙', '内容': '我们修行数十年，也未敢如此顶撞师父！你一来就搅得天翻地覆，断了大家的机缘，你担待得起吗？！'}, {'角色': '众仙', '内容': '真是个祸根！惹了师父生气，我看你今后如何在此立足！'}, {'角色': '旁白', '内容': '面对潮水般的斥责与怨怼，悟空却缓缓站起身，拍了拍膝上的尘土。他脸上非但没有半点惶恐，反而有一种如释重负的宁静。旁人眼中的惩戒与决裂，在他心中，却是一场心照不宣的约定。三下，是三更。背手走后门，是秘传的路径。师父的哑谜，他悟了。'}, {'角色': '孙悟空', '内容': '(对众人拱手，带着一丝玩味的笑) 唉，多谢各位师兄“关爱”。是俺的不是，冲撞了师父，让各位师兄跟着担惊受怕了。'}, {'角色': '众仙', '内容': '你……你还笑得出来！我看你是被师父打傻了！'}, {'角色': '孙悟空', '内容': '是，是。师父打得好，打得妙，让俺茅塞顿开。天色不早了，各位师兄还是早些回去参悟吧，别像我一样，成了不开窍的“祸根”。'}]}, {'场景': 8, '场景剧本': [{'角色': '旁白', '内容': '白日里的喧嚣早已沉寂，廊庑之间，只有众师兄弟平稳的呼吸声。悟空躺在铺上，双眼紧闭，心却如一盏不灭的灯，在黑暗中静静燃烧。他以吐纳计算着时间的流逝，直到子时，夜色最浓。他悄然起身，像一道影子滑过沉睡的同门，来到后门。门，果然虚掩着一道缝，透出比夜色更深的幽暗。他侧身而入，借着微弱的星光，来到祖师榻前。祖师面朝内侧，身形蜷曲，仿佛已入沉梦。悟空不敢惊扰，敛声屏气，双膝跪倒，在寂静中等待着命运的垂青。'}, {'角色': '须菩提祖师', '内容': '(声音低沉，带着寒意，仿佛早已醒着) 你来了。'}, {'角色': '孙悟空', '内容': '弟子不敢惊扰师父清梦，在此恭候法旨。'}, {'角色': '须菩提祖师', '内容': '你胆子不小。你可知，这后门一步之遥，踏错便是万劫不复？你以为我白日里，是在同你玩笑吗？'}, {'角色': '孙悟空', '内容': '弟子不敢。弟子只知，师父敲我三下，是喻我三更前来；倒背着手走入中门，是让我从后门而入。大道无形，真传无声。若弟子连这点禅机都参不透，又有什么资格求那长生之法？'}, {'角色': '须菩提祖师', '内容': '(沉默片刻，语气变得严肃) 悟性不错。但悟性救不了你的命。我再问你，你求长生，究竟为何？是为了逍遥自在，还是为了……与天争命？'}, {'角色': '孙悟空', '内容': '(抬起头，眼中闪烁着不屈的光) 弟子生于顽石，无父无母，不知来处。若最终仍要归于虚无，化为尘土，那这天地生我，又有何意？弟子不求逍遥，不求富贵，只求一个‘不朽’！哪怕为此与天、与地、与那冥冥中的定数争上一争，也绝不后悔！'}, {'角色': '须菩提祖师', '内容': '(长叹一声，仿佛下了某种决心) 与天争命……好一个与天争命。你可知这条路的尽头是什么？是无尽的劫数，是永恒的孤独。你今天求来的道，会成为你日后最大的枷锁。你……真的想好了？'}, {'角色': '孙悟空', '内容': '(毫不犹豫) 弟子想好了。永恒的孤独，也好过片刻的虚无。请师父传法！'}, {'角色': '须菩提祖师', '内容': '附耳过来。'}, {'角色': '旁白', '内容': '悟空闻言，心中一阵狂喜，却不敢有丝毫表露。他以膝盖为足，恭敬地挪到榻前，微微侧过头，将耳朵凑近，整个身体都化作了一只容器，准备承接那即将倾泻而下的甘露。'}, {'角色': '须菩提祖师', '内容': '(用一种庄严、神秘，如同咒语的语调) 显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄。休漏泄，体中藏，汝受吾传道自昌。口诀记来多有益，屏除邪欲得清凉。得清凉，光皎洁，好向丹台赏明月。月藏玉兔日藏乌，自有龟蛇相盘结。相盘结，性命坚，却能火里种金莲。攒簇五行颠倒用，功完随作佛和仙。'}, {'角色': '孙悟空', '内容': '(内心，呼吸急促，声音颤抖) 原来如此…原来如此！这根本不是什么延年益寿的法门…这是…这是夺天地造化，侵日月玄机的钥匙！有了它，我便不再是那块石头，不再是那只猴子…我可以…成为我自己！'}, {'角色': '孙悟空', '内容': '(声音恢复平静，但充满了力量) 师父，弟子……记下了。一字不差。'}, {'角色': '须菩提祖师', '内容': '记住，此法绝不可轻易示人。今日之后，你我之间，再无这三更之约。你闯下的任何祸事，都与我无关。去吧，在你惊动整个天庭之前，先别惊动了你的师兄们。'}, {'角色': '孙悟空', '内容': '弟子遵命。'}, {'角色': '旁白', '内容': '悟空再拜，而后起身，动作轻盈地退出了内室。他从后门悄然离去，东方天际已泛起一丝鱼肚白。当他回到自己的铺位，重新躺下时，外面的世界一如往常，众同门仍在酣睡。但悟空知道，从这一刻起，他的生命，已然不同。他得到的不是安宁，而是一场战争的开始。'}]}, {'场景': 9, '场景剧本': [{'角色': '旁白', '内容': '三年光阴弹指而过。这一日，祖师重登宝座，开讲大道，目光如炬，扫过堂下众弟子，最终定格在悟空身上。'}, {'角色': '须菩提祖师', '内容': '悟空。'}, {'角色': '孙悟空', '内容': '弟子在。'}, {'角色': '须菩提祖师', '内容': '你道之根基已成，法性已通。可你是否知晓，长生之路，每一步都踏在万丈悬崖之上？'}, {'角色': '孙悟空', '内容': '弟子愚钝。只听闻道高德隆，便与天同寿，逍遥自在。何来悬崖之说？'}, {'角色': '须菩提祖师', '内容': '（语调由平缓转为严厉）逍遥？你所修之道，是夺天地之造化，侵日月之玄机！丹成之后，鬼神不容。到了五百年后，天会降下雷灾打你！那雷，藏在你元神之中，避无可避！'}, {'角色': '孙悟空', '内容': '（惊疑）元神之雷？'}, {'角色': '须菩提祖师', '内容': '（语速加快，充满压迫感）躲得过，再活五百载！躲不过，魂飞魄散！即便你侥幸躲过，再五百年，天降火灾烧你！此火非凡火，名为‘阴火’，自你涌泉穴下燃起，无物可挡，直透天灵！将你千年苦功，烧成一捧劫灰！'}, {'角色': '孙悟空', '内容': '（呼吸急促）师父……这……'}, {'角色': '须菩提祖师', '内容': '（声音冰冷如铁）你以为完了？再五百年，又降风灾吹你！此风非凡间之风，唤作‘赑风’，从你顶门吹入，穿肠破肚，直至骨髓！让你骨肉消疏，当场自解！悟空，这三灾，你告诉我，你待如何？'}, {'角色': '孙悟空', '内容': '（声音颤抖，充满恐惧）师父慈悲！弟子……弟子该如何躲避？万望师父传我法门，弟子永世不忘大恩！'}, {'角色': '旁白', '内容': '那三灾之说，如三座大山压顶，让悟空初尝求道的恐惧。祖师遂将地煞七十二变与筋斗云的口诀倾囊相授。这猴王本是天生灵物，一点便透，不日，便已尽数学会。一日，众师兄弟在松荫下闲谈，话锋一转，便对准了悟空。'}, {'角色': '众仙', '内容': '悟空师弟，你可真是师父的掌中宝啊。我等入门多年，也只学了些吐纳的粗浅功夫，你却得了躲三灾的真传。'}, {'角色': '孙悟空', '内容': '（略带得意）哪里哪里，不过是师父抬爱，弟子勤勉罢了。'}, {'角色': '众仙', '内容': '勤勉？呵，说得轻巧。既然是真传，总得有真本事吧？光说不练，莫不是师父……也看走了眼？'}, {'角色': '孙悟空', '内容': '（被激怒）你！师父曾告诫，不可卖弄神通！'}, {'角色': '众仙', '内容': '（讥笑）此地皆是同门，谈何卖弄？不过是印证道法。还是说……你根本就没学会，只是拿师父的偏爱当幌子？'}, {'角色': '旁白', '内容': '这番话如尖针入心，悟空那野性的好胜心彻底被点燃。'}, {'角色': '孙悟空', '内容': '谁说我没学会！也罢！今天就让你们开开眼！说吧，想看什么？'}, {'角色': '众仙', '内容': '就变作前面那棵松树！若变得有半点不像，你就是欺师灭祖！'}, {'角色': '孙悟空', '内容': '看好了！变！'}, {'角色': '旁白', '内容': '只见他迎风一晃，原地哪还有什么猴王，分明是一株挺拔的苍松，枝叶繁茂，松涛阵阵，与真树别无二致。'}, {'角色': '众仙', '内容': '（爆发出惊叹与喝彩）好！好本事！真真是一模一样！好猴子！'}, {'角色': '须菩提祖师', '内容': '（声音不大，却瞬间压过所有喧哗）……很好看吗？'}, {'角色': '旁白', '内容': '笑声戛然而止。众人回头，只见祖师不知何时已站在身后，面沉似水，眼神里是深不见底的失望。'}, {'角色': '众仙', '内容': '（慌忙跪下）师父……我们……'}, {'角色': '须菩提祖师', '内容': '（无视众人，只看着变回原形的悟空）悟空，你过来。我问你，我传你这神通，是让你拿来当街头杂耍，换几声喝彩的吗？'}, {'角色': '孙悟空', '内容': '（垂头）弟子不敢……是他们……'}, {'角色': '须菩提祖师', '内容': '（打断他，语气愈发冰冷）闭嘴！法不传六耳，道不示非人！你今日显了神通，旁人若见，必会求你。你若畏惧灾祸，就不得不传他。你若不传，他便怀恨在心，必来加害！你这点微末道行，保得住自己的性命吗？'}, {'角色': '孙悟空', '内容': '（猛然抬头，幡然醒悟）师父！弟子知错了！只望师父恕罪！'}, {'角色': '旁白', '内容': '祖师的每一个字，都像一把冰冷的刻刀，将悟空心头的得意与炫耀剔除干净，只剩下赤裸裸的恐惧。他终于明白，自己刚刚为了一点虚荣，亲手埋葬了在此求道的资格。'}, {'角色': '须菩提祖师', '内容': '恕罪？我若恕你，便是害你。你我师徒缘分已尽，你……走吧。'}]}, {'场景': 10, '场景剧本': [{'角色': '旁白', '内容': '夏日悠长，松荫匝地。三星洞前的弟子们闲坐论道，言语间，话题自然而然地转向了那个最与众不同的师弟，孙悟空。'}, {'角色': '众仙', '内容': '（语带试探）悟空，师父私下传你的躲灾变化之法，想必已经登堂入室了吧？空口白话，谁都会说。不如……露一手给我们开开眼？'}, {'角色': '孙悟空', '内容': '（得意）不瞒各位师兄，师父所传的法门，我已融会贯通。你们想看，这有何难？'}, {'角色': '众仙', '内容': '（夹杂着一丝嫉妒）好大的口气。那就变棵松树吧。这满山松柏，最是寻常，也最见真章。若有半分不像，可别怪我们笑话。'}, {'角色': '孙悟空', '内容': '看好了！'}, {'角色': '旁白', '内容': '悟空捻起法诀，口中念念有词，身形一晃，原地便化作一棵苍劲古松。针叶、树皮、盘根，无一不真，甚至连风过枝头的飒飒声，都与周遭的林木别无二致。'}, {'角色': '众仙', '内容': '（真心赞叹）好猴子！好猴子！竟变得一丝破绽也无，真与天地所生无异！'}, {'角色': '众仙', '内容': '（高声喝彩）神乎其技，神乎其技啊！悟空，你真是天纵奇才！'}, {'角色': '旁白', '内容': '一片喧哗笑语，打破了洞府的清静。不远处，须菩提祖师手持藜杖，面沉似水，缓步而出。众人的笑声戛然而止，空气仿佛都凝固了。'}, {'角色': '须菩提祖师', '内容': '（声音低沉，压抑着怒火）是谁，在此喧哗！'}, {'角色': '众仙', '内容': '（噤若寒蝉）启禀师父……是孙悟空演练变化之术，我等一时忘形，惊动了尊驾，万望恕罪。'}, {'角色': '须菩提祖师', '内容': '（无视众人，目光如炬，直刺悟空）悟空，过来。我问你，你卖弄的是什么精神？炫耀的是什么本事？'}, {'角色': '孙悟空', '内容': '（不解，甚至有些委屈）师父，弟子只是将您所传的妙法……难道，难道学有所成，不该展示给同门看吗？'}, {'角色': '须菩提祖师', '内容': '（痛心疾首）展示？你以为这是什么？是街头卖艺的把戏吗！我传你大道，是让你勘破生死，不是让你当众取乐！‘道’不可轻传，‘法’不可炫耀！你今日在此卖弄，他日必有人为此害你性命！'}, {'角色': '孙悟空', '内容': '（惊慌）弟子……弟子不知其中利害……'}, {'角色': '须菩提祖师', '内容': '你不知？那我告诉你！别人见你有这等神通，必会纠缠求你传授。你若怕惹祸不传，他便心生怨恨，暗中加害！你若传了，今日张三，明日李四，这清净大道，岂不成了是非之源！到那时，你性命何存？'}, {'角色': '孙悟空', '内容': '（跪倒在地，磕头如捣蒜）师父，弟子知错了！只求师父宽恕！弟子再也不敢了！'}, {'角色': '须菩提祖师', '内容': '（闭上眼，长叹一声）现在说这些，已经晚了。你的天性如此，留你不得。你……走吧。'}, {'角色': '孙悟空', '内容': '（如遭雷击，猛地抬头）走？师父！您……您要赶我走？弟子离家二十年，把这里当成唯一的家！师恩未报，您教我往哪里去？'}, {'角色': '须菩提祖师', '内容': '你从哪里来，便回哪里去。'}, {'角色': '孙悟空', '内容': '（哭求）不！师父，我不能走！您是我唯一的亲人，除了您，我谁的话也不听！求您别赶我走！'}, {'角色': '须菩提祖师', '内容': '（声音冷硬如铁，不带一丝情感）不必多言。我与你之间，师徒情分已尽，再无恩义！你此去，不管惹出什么滔天大祸，都不准说出是我的徒弟。'}, {'角色': '孙悟空', '内容': '（绝望）师父……'}, {'角色': '须菩提祖师', '内容': '（一字一顿，带着森然杀意）若敢提我半个字，我便知晓。定将你这猢狲剥皮锉骨，神魂贬入九幽之地，让你万劫不得翻身！滚！'}, {'角色': '旁白', '内容': '悟空含泪叩别，不敢再言。他捻起诀，纵身一跃，一个筋斗，便是十万八千里。身后，灵台方寸山瞬间化为尘埃，前方，是茫茫云海。他得了长生，得了神通，却也……成了一个真正的孤家寡人。'}]}]}
    # script_conflict_escalation_gemini = {'剧本': [{'场景': 1, '场景剧本': [{'角色': '旁白', '内容': '混沌未分之前，宇宙只是一片虚无。直至盘古开天，清浊始判。东胜神洲之上，有一仙石，暗合周天之数，上有九窍八卦之形。它吸食日月精华，孕育着一个撼动天地的生命。这一日，仙石轰然迸裂，石卵迎风而化，一个石猴就此诞生。他初睁的双目中，射出两道金光，撕裂云海，直冲斗府，惊动了九重天上的凌霄宝殿。'}, {'角色': '玉皇大帝', '内容': '何事惊动凌霄？'}, {'角色': '千里眼', '内容': '启禀陛下，非兵戈，非妖祸。'}, {'角色': '顺风耳', '内容': '臣所闻，也非雷鸣，而是一声金石碎裂之音，清越异常。'}, {'角色': '玉皇大帝', '内容': '又是哪个山头的法宝，按捺不住寂寞了？讲。'}, {'角色': '千里眼', '内容': '陛下，那两道金光，并非源自任何法宝。它来自下界东胜神洲，一处凡间山脉。光芒之盛，竟能直刺牛斗星宫，臣险些灼伤仙目！'}, {'角色': '玉皇大帝', '内容': '有趣。能伤到你的眼睛，倒是个稀罕事。那金光的源头，究竟为何物？'}, {'角色': '旁白', '内容': '千里眼微微一顿，仙目中似乎还残留着那两道金光的余威。他抬起头，神色中混杂着惊异与一丝不甘。'}, {'角色': '千里眼', '内容': '陛下，臣穷尽目力看去，那金光，源自一只刚从仙石中迸裂而出的石猴，是它的双眼！'}, {'角色': '顺风耳', '内容': '正是。一声石裂之后，万籁俱寂，仿佛天地都为它屏息。但此刻金光已敛，那猴物正在山涧饮水，与其他野兽无异。'}, {'角色': '玉皇大帝', '内容': '石猴？呵呵……'}, {'角色': '旁白', '内容': '宝座之上，玉帝发出一声轻笑，指尖轻敲着龙椅扶手，语气里是俯瞰万古的倦怠与傲慢。'}, {'角色': '玉皇大帝', '内容': '你们两个，跟了朕多少万年了？天地精华，日月灵气，偶尔造出个有些灵性的东西，有什么值得大惊小怪的？不过是块顽石，做了个不安分的梦罢了。'}, {'角色': '玉皇大帝', '内容': '它既生于凡尘，便由它自生自灭。天庭的威仪，不是用来关注一只野猴子的。退下吧。'}, {'角色': '旁白', '内容': '天庭的威严，在此刻化为一种轻慢的漠然。对于这桩日后将颠覆三界的大事，此刻的定义，不过是一场“不安分的梦”。'}, {'角色': '千里眼', '内容': '……是，陛下。'}]}, {'场景': 2, '场景剧本': [{'角色': '旁白', '内容': '山中无岁月，石猴与群猴为伴，嬉戏山林，自在逍遥。这一日暑气蒸腾，群猴玩耍至一处山涧，只见一道白练从断崖上倾泻而下，水声轰鸣，震彻山谷。'}, {'角色': '众猴', '内容': '这鬼天气，热得皮毛都要烧着了。这瀑布看着凉快，可谁知道里面藏着什么？'}, {'角色': '众猴', '内容': '水声这么响，里面要是住着什么精怪，咱们这点骨头还不够它塞牙缝的。'}, {'角色': '众猴', '内容': '说的也是，安稳日子过一天是一天，何必去招惹那未知的凶险。'}, {'角色': '众猴', '内容': '安稳？日晒雨淋，东躲西藏，这也叫安稳？我们当中，难道就没有一个有胆量的，敢进去为我们探出一条生路？'}, {'角色': '众猴', '内容': '谁有这本事？谁又能担得起这个风险？除非……谁能毫发无伤地进去再出来，我等就奉他为王，从此听他号令！'}, {'角色': '孙悟空', '内容': '我去。'}, {'角色': '众猴', '内容': '石头，你疯了？这不是逞能的时候，这是拿命在赌！'}, {'角色': '孙悟空', '内容': '你们的命是安稳，我的命是探寻。你们的恐惧，恰好是我的机会。等着我回来称王。'}, {'角色': '旁白', '内容': '话音未落，石猴的身影已如离弦之箭，迎着那千钧水势纵身跃入。冰冷的激流瞬间将他吞没，外界的喧嚣顷刻间化为一片沉寂的轰鸣。'}, {'角色': '孙悟空', '内容': '果然，这水帘之后，别有洞天！竟是一座铁板桥，通往未知。'}, {'角色': '孙悟空', '内容': '石锅石灶，石床石凳……竟是天造地设的一座府邸。这哪里是瀑布之后，这分明就是为王准备的宫殿。'}, {'角色': '孙悟空', '内容': '花果山福地，水帘洞洞天……哈哈哈哈！天命！天命如此！此地，此名，皆为我所有！'}, {'角色': '旁白', '内容': '瀑布之外，时间仿佛被拉长。方才还喧闹的猴群渐渐安静下来，只剩下水声依旧。它们焦灼地望着那片白茫茫的水帘，等待着一个它们既期盼又畏惧的结局。'}, {'角色': '众猴', '内容': '他不会……真的死了吧？我们是不是逼得太紧了？'}, {'角色': '旁白', '内容': '就在众猴的希望即将被恐惧吞噬时，那道水帘猛地向外一分，一个湿淋淋的身影破水而出，稳稳落在岸边。他抹去脸上的水珠，眼中闪烁着征服者的光芒。'}, {'角色': '孙悟空', '内容': '孩儿们，你们的王，回来了！'}, {'角色': '众猴', '内容': '你……你真的回来了！里面究竟是什么？是龙潭还是虎穴？'}, {'角色': '孙悟空', '内容': '龙潭虎穴？不！那后面是上天赐予我们的王国！一座天造地设的石屋，宽敞得足以容纳我们整个族群，锅碗瓢盆，一应俱全！'}, {'角色': '孙悟空', '内容': '从此，我们不必再畏惧风霜雨雪，不必再提防虎豹豺狼！那洞口的石碑上，早已为我们刻好了名号：花果山福地，水帘洞洞天！'}, {'角色': '孙悟空', '内容': '你们还在等什么？那是一个承诺，一个没有恐惧的家园！'}, {'角色': '众猴', '内容': '家园……我们愿意跟你进去！'}, {'角色': '众猴', '内容': '你言出必行，神通广大，我等心服口服！请受我们一拜，从今往后，你就是我们的王！'}, {'角色': '众猴', '内容': '拜见千岁大王！拜见千岁大王！'}, {'角色': '旁白', '内容': '“千岁大王”的呼喊声在山谷间回荡。石猴坦然受了这一拜，他站上高处，目光扫过自己的第一批臣民。从混沌中诞生的顽石，此刻用勇气与野心，为自己加冕。'}, {'角色': '孙悟空', '内容': '都起来。记住今日。从今往后，我便是你们的美猴王。'}]}, {'场景': 3, '场景剧本': [{'角色': '众猴', '内容': '大王千岁！大王千岁！'}, {'角色': '旁白', '内容': '水帘洞内，喧嚣的欢宴正酣，猴儿们畅饮着甘醇的椰酒。然而，端坐于石座上的美猴王，却在一片欢呼声中，发出一声沉重而压抑的悲泣，瞬间将所有的热闹凝固。'}, {'角色': '孙悟空', '内容': '都停下。'}, {'角色': '众猴', '内容': '大王？您怎么哭了？是谁惹您不快了？'}, {'角色': '孙悟空', '内容': '不快？不。我只是……忽然觉得这一切都没什么意思。'}, {'角色': '众猴', '内容': '没意思？大王，我们今日有酒有果，自由自在，这可是天大的快活！您为何要为那些看不见的明天烦恼？'}, {'角色': '孙悟空', '内容': '快活？这快活能有多久？你们以为这‘自由’是真的吗？我们不过是阎王老子生死簿上，还没被勾掉的名字罢了。'}, {'角色': '众猴', '内容': '大王，您别说笑了。我们占山为王，谁敢管我们？'}, {'角色': '孙悟空', '内容': '我没说笑！你们看这花开花谢，可曾想过，我等的性命，亦不过如此？今日我虽为王，可百年之后，还不是一抔黄土，一身枯骨？这‘王’位，这‘千岁’的呼喊，在阎王面前，不过是个天大的笑话！'}, {'角色': '众猴', '内容': '阎王……大王，别说了……我们会死……都会死……'}, {'角色': '旁白', '内容': '死亡的恐惧如冰冷的潮水，瞬间淹没了整个水帘洞。群猴的哭号混杂着绝望。就在此时，一只通背老猿分开哀嚎的猴群，他苍老的眼中没有恐惧，只有洞悉一切的平静。'}, {'角色': '博学的猿猴', '内容': '都安静。大王，您能为此而悲，才是真正的道心萌发。'}, {'角色': '孙悟空', '内容': '道心？我只看到绝路一条！难道这生死，还有什么破解之法不成？'}, {'角色': '博学的猿猴', '内容': '天地万物，皆有定数。唯三者，能超脱轮回，与天地同寿。'}, {'角色': '孙悟空', '内容': '哪三者？！快说！'}, {'角色': '博学的猿猴', '内容': '佛，仙，与神圣。此三者，早已跳出三界，不入轮回，无生无灭。'}, {'角色': '旁白', '内容': '佛、仙、神圣。这三个字，像一道劈开黑暗的光，照进了美猴王被死亡阴影笼罩的内心。他眼中熄灭的火焰，重新燃起了焚尽一切的渴望。'}, {'角色': '孙悟空', '内容': '他们在哪？'}, {'角色': '博学的猿猴', '内容': '他们不在此山，亦不离此世。只在尘世的古洞仙山之中，等待有缘之人。'}, {'角色': '孙悟空', '内容': '好！明日我就下山，踏遍天涯海角，也要找到他们！我偏要学一个长生不老之法，把我们所有人的名字，都从那阎王老子的破本子上，一笔勾销！'}]}, {'场景': 4, '场景剧本': [{'角色': '旁白', '内容': '决心一定，猴王告别了涕泣的群猴，独自驾一叶扁舟，飘入了茫茫大海。岁月在风浪间流逝，当他踏上南赡部洲的陆地，山野的自由已被市井的烟火彻底隔绝。他褪下顽石般的野性，笨拙地裹上名为“体面”的布料，学着人的模样，将自己投入这片追逐名利的人间浊流。'}, {'角色': '货郎', '内容': '上好的绫罗，上好的绸缎！客官，瞧瞧吧。人活一世，不就图个体面？穿上它，你就是个人物。'}, {'角色': '孙悟空', '内容': '人物？我问你，这布料能挡住阎王的笔，还是能缝补被岁月撕烂的皮肉？'}, {'角色': '货郎', '内容': '你这人说话真是不中听。没有这身皮，谁认你是个东西？有了钱，有了地位，自然就活得久，活得值！你连这个道理都不懂，还谈什么生死？'}, {'角色': '孙悟空', '内容': '用钱买来的‘值得’，真是廉价得可怜。'}, {'角色': '货郎', '内容': '神经病！滚开，别在这里挡我财路，一身穷酸气！'}, {'角色': '旁白', '内容': '商贩的唾骂，像一盆冰水，浇灭了他对人世最后一丝温情的幻想。他沉默地穿行，发现那些被称作“礼义”的规矩，比藤蔓更缠人，每一步都像在别人的骨架上行走，别扭，且孤独。'}, {'角色': '书生甲', '内容': '大丈夫立于世，当求不朽盛名！待我金榜题名，这名字便刻入青史，与日月同辉！'}, {'角色': '书生乙', '内容': '正是！皮囊终将腐朽，唯功业文章可传千古。这才是真正的长生！'}, {'角色': '孙悟空', '内容': '请教二位，史书上那一个个名字，可曾有一个能从坟墓里爬出来，再看一眼太阳？你们所说的长生，不过是活在别人的嘴里，真够可悲的。'}, {'角色': '书生甲', '内容': '放肆！你这满身腥臊的野人，懂什么叫精神不灭？肉体不过是囚笼，我辈追求的是灵魂的永恒！'}, {'角色': '书生乙', '内容': '与这等只知食色的畜生何必多言？他连做人的资格都未必有，又怎会理解人的追求？走，污了你我的耳朵。'}, {'角色': '旁白', '内容': '年复一年，相似的场景，不同的面孔。他看到的，听到的，尽是些用虚名和财富堆砌起来的华美坟墓。人们在坟墓里弹唱、欢宴，对头顶那片永恒的虚无，默契地视而不见。'}, {'角色': '路人甲', '内容': '总算买下城东那座大宅子了，这辈子，就算扎下根了，再不用担惊受怕了。'}, {'角色': '路人乙', '内容': '是啊，守着一砖一瓦，心里才踏实。这就是家，死了也能埋在自家的地里。'}, {'角色': '孙悟空', '内容': '根？你们的根就在土里，可魂魄呢？宅子再大，是能锁住无常，还是能买通鬼差？不过是给自己造了个更气派的囚笼。'}, {'角色': '路人甲', '内容': '你这人！我们辛辛苦苦一辈子，图个安稳，你在这里胡言乱语，是何居心？咒我们死吗？'}, {'角色': '路人乙', '内容': '离他远点，真是晦气！我看他才是孤魂野鬼，见不得别人好！'}, {'角色': '旁白', '内容': '疯癫的，究竟是谁？喧嚣的人声终于在他耳边彻底退潮，留下宇宙洪荒般的寂静。九年的光阴，像一场拙劣的模仿秀。他低头扯了扯身上这件人的衣袍，再抬头望向那被屋檐切割得支离破碎的天空，一种源自骨血的暴怒与孤独，让他几乎要对天狂啸。'}, {'角色': '孙悟空', '内容': '呵……这就是人。把丝线叫作脸面，把谎言叫作不朽，把泥土和木头叫作根基。我学他们走路，学他们说话，学他们把头低下，把腰弯成一道懦弱的弧线。可笑！'}, {'角色': '孙悟空', '内容': '他们给这身臭皮囊套上一层又一层的壳，把蝇营狗苟称之为生活，却对头顶那真正的大恐怖，连看都不敢看一眼！'}, {'角色': '孙悟空', '内容': '九年！我像个傻子一样，在这片大地上寻找。我看到他们为了指甲盖大小的土地打得头破血流，为了一个虚无缥缈的赞美沾沾自喜。他们争抢的，不过是粪土；他们夸耀的，不过是泡影。'}, {'角色': '孙悟空', '内容': '没有一个人，肯指着自己的鼻子问，我这口气，到底能喘到几时？'}, {'角色': '孙悟空', '内容': '道，不在此处！这片被名利腌透的土地，长不出我要的果子。我得走！到那西洋大海的另一边，再找！'}]}, {'场景': 5, '场景剧本': [{'角色': '旁白', '内容': '石猴登上高山，只见林海茫茫，前路难觅。正当他心中怅惘之际，一阵歌声自幽深的谷底传来，清越悠扬，仿佛不属于这凡尘俗世。'}, {'角色': '樵夫', '内容': '观棋柯烂，伐木丁丁，云边谷口徐行。卖薪沽酒，狂笑自陶情。苍径秋高，对月枕松根，一觉天明。认旧林，登崖过岭，持斧断枯藤。收来成一担，行歌市上，易米三升。更无些子争竞，时价平平。不会机谋巧算，没荣辱，恬淡延生。相逢处，非仙即道，静坐讲《黄庭》。'}, {'角色': '旁白', '内容': '歌声一歇，石猴循声拨开藤蔓，终于在林中见到了歌者。他见这樵夫一身布衣，满手老茧，却能唱出如此超脱的词句，心中的寻仙执念化作了一股尖锐的质问。'}, {'角色': '孙悟空', '内容': '你就是唱那《黄庭》的神仙？既然懂得长生大道，为何要藏在这深山老林，扮作一个凡夫俗子？'}, {'角色': '樵夫', '内容': '神仙？朋友，我若真是神仙，这斧子劈开的就该是天门，而不是这几根烂木头了。你这猴头，认错人了。'}, {'角色': '孙悟空', '内容': '休想骗我！《黄庭》乃道家真言，岂是凡夫俗子能够领悟的？你这歌里字字句句都是清净无为，你却在这里为了几升米弄得一身臭汗！你到底是谁？是谁教你的这首歌？'}, {'角色': '樵夫', '内容': '唉，你这猴子真是多心。这曲子叫《满庭芳》，是我邻居教的。他见我终日劳苦，愁烦太多，才传了这曲子让我解闷。唱一唱，心里的石头也能轻几分。'}, {'角色': '孙悟空', '内容': '你的邻居是神仙？他既是真神仙，为何不干脆传你长生之法，给你一个解脱？难道你甘心这日复一日的辛劳，最后化为一抔黄土？'}, {'角色': '樵夫', '内容': '解脱？我为什么要解脱？长生不老，然后眼睁睁看着我那老母亲化为尘土，独留我一个在这世上？朋友，有些道，不是一个人的道。我的老母亲还在家里等我这三升米下锅，这比什么长生都重要。'}, {'角色': '孙悟空', '内容': '……你的道，是你的。但我的道，是寻一个不死。求你，为我指个方向。'}, {'角色': '旁白', '内容': '石猴眼中的狂热与偏执，在樵夫质朴的话语中渐渐褪去，化为一种纯粹的恳求。樵夫看他这般模样，也不再打趣，神情变得庄重起来。'}, {'角色': '樵夫', '内容': '也罢，你这猴子，眼里有火，不像我们这些土里刨食的。听好了，从此向南，是灵台方寸山，山中有斜月三星洞。你要找的须菩提祖师，就在那里。'}, {'角色': '孙悟空', '内容': '灵台方寸山，斜月三星洞……须菩提祖师……'}, {'角色': '樵夫', '内容': '对。不过我劝你一句，那地方，山门好进，心门难入。祖师的道，可不是唱唱曲子就能悟的。'}, {'角色': '孙悟空', '内容': '多谢！此恩没齿不忘！'}, {'角色': '旁白', '内容': '话音未落，石猴已急不可耐地转身向南，身影瞬间没入林中。樵夫望着他消失的方向，扛起斧头，轻轻叹了口气。'}, {'角色': '樵夫', '内容': '去吧，求你自己的道去吧。唉，他或许是对的，我这俗人，有娘在，便是最大的圆满，哪还有多余的心去求什么大道呢。'}]}, {'场景': 6, '场景剧本': [{'角色': '旁白', '内容': '穿过层层叠叠的琼楼玉宇，石猴终于得见瑶台之上的菩提祖师。四周仙众肃立，大殿之内，时间仿佛静止。那是一种混元之初的寂静，足以荡涤尽两重大海的风浪与一座大陆的尘埃。他漫长的、漂泊的追寻，在此刻抵达了终点。'}, {'角色': '孙悟空', '内容': '师父！弟子……弟子终于找到您了！'}, {'角色': '须菩提祖师', '内容': '你这满身尘嚣的妖猴，从何处来，又为何在此喧哗，扰我清净？'}, {'角色': '孙悟空', '内容': '弟子来自东胜神洲，傲来国，花果山水帘洞。'}, {'角色': '须菩提祖师', '内容': '一派胡言。你可知东胜神洲与此地相隔几重汪洋，几多险恶？你一介妖物，凭何渡海越洲，来到此处？你求的究竟是道，还是又一处可以让你放肆撒野的山头？'}, {'角色': '孙悟空', '内容': '弟子不敢说谎！弟子飘洋过海，走了十数年，并非为了寻一处山头！弟子是为……是为求解脱，求一个不死之法！'}, {'角色': '须菩提祖师', '内容': '不死？生死轮回，乃天道之常。你一介生灵，竟妄图与天道为敌？这非向道之心，而是无边之野心。'}, {'角色': '孙悟空', '内容': '若天道便是眼睁睁看着一切化为尘土，那这道，不求也罢！弟子只知，若不能长生，今日之乐，便是明日之哀！请师父教我！'}, {'角色': '须菩提祖师', '内容': '好一个‘不求也罢’。你既无视天道，想必也无父无母，孑然一身了？'}, {'角色': '孙悟空', '内容': '弟子……确实没有父母，是从山顶一块仙石中迸出来的。'}, {'角色': '旁白', '内容': '祖师眼中那审视的锋芒悄然敛去，转为一种深长的探究。这不是勘破谎言的释然，而是面对一桩天地异数时的静默。他终于明白，眼前这个生物的野心，与其来历一样，生于混沌，不服规训。'}, {'角色': '须菩提祖师', '内容': '天生地养，难怪……难怪敢与天道叫板。你起来，让我看看你这天生的异类，究竟是何模样。'}, {'角色': '旁白', '内容': '石猴应声跳起，绕着殿中走了两圈。那步态带着未经雕琢的、源自天地鸿蒙的野性与灵气。祖师的目光随着他移动，唇边第一次浮现出一丝难以捉摸的笑意。'}, {'角色': '须菩提祖师', '内容': '你形似猢狲，天性顽劣，若不给你个姓氏管束，怕是要翻天。猢字去了兽旁，是个古月。古者老，月者阴，老阴不能化生，与你的生机不符。不若就姓‘孙’吧。孙字是子系，子者儿男，系者婴细，正合你婴儿之本论。让你入个人伦，接上地气。'}, {'角色': '孙悟空', '内容': '孙……弟子有姓了！谢师父，谢师父！'}, {'角色': '须菩提祖师', '内容': '别急着谢。你既妄图勘破生死，我便给你个法名，时时警醒。我门中排到你，正是‘悟’字辈。你就叫‘悟空’。你可能领悟，这‘空’字，对你意味着什么？'}, {'角色': '旁白', '内容': '一个姓氏，是将其拖入红尘；一个法名，却是为其戴上枷锁。这是身份的重塑，也是一场与天性的漫长博弈的开端。'}, {'角色': '孙悟空', '内容': '孙悟空……弟子孙悟空，叩谢师父赐名。'}]}, {'场景': 7, '场景剧本': [{'角色': '须菩提祖师', '内容': '悟空。道有三百六十旁门，门门皆有正果。今日，我便传你“术”字门，请仙问卜，可知趋吉避凶，如何？'}, {'角色': '孙悟空', '内容': '趋吉避凶……然后呢？终究还是难逃一死。师父，此法可得长生否？'}, {'角色': '须菩提祖师', '内容': '不能。'}, {'角色': '孙悟空', '内容': '那便不学。如同给将倾的大厦裱一层新纸，有何用处。'}, {'角色': '须菩提祖师', '内容': '那“静”字门，参禅打坐，入定坐关，又如何？'}, {'角色': '孙悟空', '内容': '坐着等死，和躺着等死，有区别么？可得长生否？'}, {'角色': '须菩提祖师', '内容': '不过是延年益寿，谈不上长生。'}, {'角色': '孙悟空', '内容': '那也不学。我不求苟延残喘，我要求的是永恒。'}, {'角色': '须菩提祖师', '内容': '……好大的口气。那么，“动”字门，采阴补阳，炼丹服药，吞霞服气，你可中意？'}, {'角色': '孙悟空', '内容': '这些，听起来更像是饮鸩止渴的把戏。敢问师父，这般折腾，可得长生么？'}, {'角色': '须菩提祖师', '内容': '犹如镜里观花，水中捞月。'}, {'角色': '孙悟空', '内容': '师父，我漂洋过海，不是来学这些空花幻影的。不学。'}, {'角色': '旁白', '内容': '祖师的声音沉了下去，高台之上的气氛仿佛凝结成冰。他死死盯着悟空，眼神里再无半分温和。'}, {'角色': '须菩提祖师', '内容': '你这泼猴！这道，是水中月，那法，是镜中花。如此说来，我座下竟无一物能入你的法眼？你究竟，待要怎的！'}, {'角色': '孙悟空', '内容': '弟子不敢。但求一条真正能跳出轮回，躲过阎君的……真道！'}, {'角色': '旁白', '内容': '祖师闻言，勃然大怒，跳下高台，手持戒尺指着悟空。'}, {'角色': '须菩提祖师', '内容': '好个不知天高地厚的畜生！给我过来！'}, {'角色': '旁白', '内容': '悟空毫无惧色，坦然上前，跪在祖师面前。祖师举起戒尺，在众人惊恐的倒吸气声中，对着悟空的头，不轻不重，敲了三下。'}, {'角色': '须菩提祖师', '内容': '哼。'}, {'角色': '旁白', '内容': '祖师扔下戒尺，拂袖而去，倒背着手，走入中门，将两扇门“砰”地一声，狠狠关上了。'}, {'角色': '众仙', '内容': '你这泼猴！你毁了我们所有人的机缘！'}, {'角色': '众仙', '内容': '师父何曾如此动怒？今日被你当众顶撞，怕是十年八年都不会再开坛讲法了！'}, {'角色': '众仙', '内容': '你这无法无天的东西，师父的道法也是你能挑三拣四的？你以为你是谁！'}, {'角色': '旁白', '内容': '悟空面对潮水般的斥责，一言不发。他非但没有恼怒，反而对着那扇紧闭的中门，深深叩首。别人看到的是惩罚与决裂，他听到的，却是心有灵犀的暗号。'}, {'角色': '孙悟空', '内容': '三下，是叫我三更时分留意。从后门走，是示意我从后门进入，秘传大道。师父啊师父，您的哑谜，弟子…悟了。'}, {'角色': '众仙', '内容': '你还跪着做什么？等死吗？'}, {'角色': '孙悟空', '内容': '是，是，师兄们教训的是。师父的教诲，弟子一定牢记在心。天色不早了，各位师兄也早些安歇吧，免得误了明早的修行。'}]}, {'场景': 8, '场景剧本': [{'角色': '旁白', '内容': '那一夜，万籁俱寂，唯有同门的鼾声在暗中起伏。悟空躺在铺上，假寐于榻，心却如一团烧红的炭火，在等待一场泼天大雨的考验。子时已至，夜色最浓。他悄然起身，如一道没有重量的影子，滑过沉睡的众人，来到后门。门，虚掩着，仿佛一个等待了他七年的陷阱。他侧身而入，来到祖师榻前，见师父面朝内而卧，身形不动。悟空不敢惊扰，双膝跪倒，将自己的一切都押在了这场无声的豪赌上。'}, {'角色': '须菩提祖师', '内容': '你终究还是来了。'}, {'角色': '孙悟空', '内容': '弟子不敢不来。七年光阴，只为今夜。'}, {'角色': '须菩提祖师', '内容': '做什么？你以为我当众打你三下，是孩童间的游戏吗？你求的，是逆天改命。你知道这四个字，要用什么来换吗？'}, {'角色': '孙悟空', '内容': '弟子不知价码，只知生死。我生于顽石，无父无母，若不能求得真我，与那山间枯木何异？这长生，就是我唯一的根。'}, {'角色': '须菩提祖师', '内容': '根……呵呵，你这根，是要扎进天庭的基石里。你不是在求道，你是在向这天道宣战。我传你此法，便是将这天地的因果，与你我二人绑在了一起。你可想好了？'}, {'角色': '孙悟空', '内容': '弟子一人做事一人当。若有灾祸，弟子愿以魂飞魄散为代价，绝不牵连师父分毫。'}, {'角色': '须菩提祖师', '内容': '罢了。天意让你这块石头开了窍，我若不成全，反倒是逆了更大的天意。附耳过来，听好了。此法一出，再无回头路。'}, {'角色': '旁白', '内容': '悟空膝行至榻前，侧过头颅。那将要降临的，不是甘露，而是一场雷霆，一场足以将他粉身碎骨，也能让他重获新生的雷霆。'}, {'角色': '孙悟空', '内容': '弟子洗耳恭听。'}, {'角色': '须菩提祖师', '内容': '显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄。休漏泄，体中藏，汝受吾传道自昌。口诀记来多有益，屏除邪欲得清凉。得清凉，光皎洁，好向丹台赏明月。月藏玉兔日藏乌，自有龟蛇相盘结。相盘结，性命坚，却能火里种金莲。攒簇五行颠倒用，功完随作佛和仙。'}, {'角色': '旁白', '内容': '那口诀如烙铁，字字滚烫，句句锥心，在他灵魂深处烙下永不磨灭的印记。一条崭新的、充满荆棘与火焰的道路，在他眼前轰然洞开。'}, {'角色': '孙悟空', '内容': '这……这便是夺天地之造化，侵日月之玄机……原来道，不在蒲团，不在经文，在这逆转乾坤的胆魄里！弟子…明白了。'}, {'角色': '须菩提祖师', '内容': '记住，你明白的不是道，是劫。从今往后，你修的每一个神通，都会成为天上众神指向你的刀。出了这个门，你我再无师徒之分，你的来路，你的师承，永远是个秘密。滚吧。'}, {'角色': '旁白', '内容': '悟空重重叩首，再起身时，已不见半分顽劣，唯有无尽的决绝。他悄然退出，身后，门扉无声合拢，隔断了过往。东方天际已泛起一线惨白，众生仍在沉睡。唯有悟空，睁着双眼，从此，再也无法安眠。'}]}, {'场景': 9, '场景剧本': [{'角色': '旁白', '内容': '三年光阴弹指而过。这一日，祖师重登宝座，开讲大道，目光扫过堂下众弟子，最终落在了悟空身上。'}, {'角色': '须菩提祖师', '内容': '悟空何在？'}, {'角色': '孙悟空', '内容': '弟子在此。'}, {'角色': '须菩提祖师', '内容': '你自以为道法如何了？'}, {'角色': '孙悟空', '内容': '托师父洪福，弟子根基稳固，法性贯通。'}, {'角色': '须菩提祖师', '内容': '贯通？你可知，你修的这长生之道，本身就是逆天而行，天地不容。既已通法，便要准备迎接你的‘三灾利害’。'}, {'角色': '孙悟空', '内容': '弟子不解。既已得道，不就该与天同寿，万劫不侵么？何来灾害之说？'}, {'角色': '须菩提祖师', '内容': '天真。此法夺天地造化，侵日月玄机，鬼神都容你不得。五百年后，天会降下雷灾打你。那雷，藏在你元神之中，避无可避。躲不过，你便形神俱灭。'}, {'角色': '孙悟空', '内容': '元神中的雷？'}, {'角色': '须菩提祖师', '内容': '若侥幸躲过，再过五百年，天又降火灾烧你。那火，不是凡火，是阴火。从你脚底涌泉穴烧起，穿过五脏六腑，直透天灵。你千年的修行，顷刻间化为飞灰。'}, {'角色': '孙悟空', '内容': '师父……这火也躲不过吗？'}, {'角色': '须菩提祖师', '内容': '若你再侥幸，又过五百年，还有风灾。那风，不从口鼻入，而是从你顶门囟户吹进，穿过丹田，过九窍。你的骨肉会被吹得消疏，身体自内而外分崩离析。悟空，这三灾，你拿什么去躲？'}, {'角色': '孙悟空', '内容': '弟子……弟子不知……万望师父慈悲，传我躲避之法！弟子粉身碎骨，不敢忘恩！'}, {'角色': '旁白', '内容': '那三灾之说，如三座大山压在悟空心头，长生的喜悦荡然无存，只剩下对死亡的恐惧。祖师遂将地煞七十二变与筋斗云的口诀倾囊相授。这猴王本是天生灵物，一点便透，不消时日，便已尽数学会。又一日，春夏之交，众师兄弟在松荫下闲谈，话锋一转，便刺向了悟空。'}, {'角色': '众仙', '内容': '悟空师弟，听说师父给你开了小灶，传了躲三灾的真本事？'}, {'角色': '孙悟空', '内容': '不敢，不过是师父慈悲，弟子侥幸学了些皮毛。'}, {'角色': '众仙', '内容': '皮毛？师父可从未私下传过我们什么。你这皮毛，恐怕比我们的真传还厉害吧？还是说，你只是得了几句口诀，其实根本没学会？'}, {'角色': '孙悟空', '内容': '师兄何出此言？师父所传，我早已烂熟于心。'}, {'角色': '众仙', '内容': '烂熟于心？那你倒是变个我们看看。我们这些凡夫俗子，也想开开眼，见识一下真正的仙法是什么模样。你若是不敢，就是欺师灭祖，凭空捏造！'}, {'角色': '孙悟空', '内容': '谁说我不敢！你们想看什么？'}, {'角色': '众仙', '内容': '就变作那棵松树。我们倒要看看，能有多真！'}, {'角色': '孙悟空', '内容': '看好了！变！'}, {'角色': '旁白', '内容': '他迎风一晃，身形暴长，原地哪还有什么猴王，分明是一株挺拔的苍松，枝叶繁茂，带着凌霜傲雪之姿，在风中发出阵阵松涛。'}, {'角色': '众仙', '内容': '好！好啊！简直天衣无缝！真神仙手段！'}, {'角色': '旁白', '内容': '一片喝彩与奉承声中，一个冰冷的声音穿透了所有喧嚣。'}, {'角色': '须菩提祖师', '内容': '成何体统！'}, {'角色': '旁白', '内容': '众弟子回头，只见祖师拄杖而立，面沉似水。悟空赶忙收了神通，变回原形，躬身侍立。'}, {'角色': '须菩提祖师', '内容': '刚才是什么人在此喧哗？'}, {'角色': '众仙', '内容': '回禀尊师，是孙悟空演变神通，我等见他变得逼真，忍不住喝彩，惊动了师父。'}, {'角色': '须菩提祖师', '内容': '悟空，你过来。我问你，这是什么？是让你在人前炫耀的戏法吗？道，是拿来卖弄的吗？'}, {'角色': '孙悟空', '内容': '弟子不敢……是师兄们定要看，弟子一时兴起……'}, {'角色': '须菩提祖师', '内容': '别人要看，你就给？别人若要你的命，你也给吗？你今日显露神通，他日若有人见你身怀绝技，逼你传授，你传是不传？若不传，他便要加害于你，你这性命，还保得住吗？'}, {'角色': '孙悟空', '内容': '弟子知错了！只望师父恕罪！'}, {'角色': '须菩提祖师', '内容': '我教你神通，是让你求生，不是让你寻死。你这卖弄的心性不改，迟早会惹下杀身大祸。我这里，再也容不下你了。'}, {'角色': '孙悟空', '内容': '师父！'}, {'角色': '须菩提祖师', '内容': '你走吧。从哪里来，回哪里去。从今以后，不许你说是我的徒弟。你惹下的任何祸事，都与我无关。'}]}, {'场景': 10, '场景剧本': [{'角色': '旁白', '内容': '夏日午后，松荫匝地。三星洞前的弟子们闲坐论道，言语间，不约而同地，都转向了那个天资绝伦却又野性难驯的师弟，孙悟空。'}, {'角色': '众仙', '内容': '悟空，师父私传你的长生妙法，你如今算是登堂入室了？光说可不算数。'}, {'角色': '孙悟空', '内容': '师父点拨，弟子勤修，不敢说登堂入室，但那些变化之术，早已烂熟于心。'}, {'角色': '众仙', '内容': '既如此，何不展示一番，也好让我等凡夫俗子开开眼界，见识一下真正的仙家手段？'}, {'角色': '孙悟空', '内容': '这有何难？众位师兄想看什么，只管说。'}, {'角色': '众仙', '内容': '那就变棵松树吧。此地松柏常见，最能看出真假，也最考验功力。'}, {'角色': '孙悟空', '内容': '好！看我神通！'}, {'角色': '旁白', '内容': '悟空捻起法诀，口中念念有词，身子一纵，原地便化作一棵苍劲古松。树皮皲裂，松针如戟，盘根错节，竟与真树无异，引得众人抚掌大笑，喝彩连连。'}, {'角色': '众仙', '内容': '妙啊！妙啊！这猴子真有通天彻地之能！'}, {'角色': '众仙', '内容': '真乃天纵奇才！我等望尘莫及，望尘莫及啊！'}, {'角色': '旁白', '内容': '喧哗声中，须菩提祖师手持藜杖，悄然现身。他面沉似水，眼神里没有一丝波澜，周遭的笑语瞬间凝固。'}, {'角色': '须菩提祖师', '内容': '悟空，过来。你在这里卖弄的是什么精神？'}, {'角色': '众仙', '内容': '师父息怒，我等在此论道，是孙悟空演练变化，弟子们一时喝彩，惊扰了师父清修。'}, {'角色': '须菩提祖师', '内容': '我问的是他。你变的这棵松树，是想证明什么？证明道法，还是证明你自己？'}, {'角色': '孙悟空', '内容': '禀师父，弟子不敢……只是师兄们好奇，弟子便……'}, {'角色': '须菩提祖师', '内容': '你以为这是什么？街头卖艺的杂耍吗？道，是天地间的隐秘；法，是护持己身的利器！不是让你拿来换几声廉价喝彩的玩物！'}, {'角色': '孙悟空', '内容': '弟子知错了……'}, {'角色': '须菩提祖师', '内容': '你错在哪里，根本就不知道！今日你在此炫耀，明日便会有人因觊觎你的神通而害你性命！他若求你，你传是不传？若不传，他必害你；若传了，你又如何保证他不用这神通为祸世间？到那时，你的性命，这山门的清净，又在何处！'}, {'角色': '孙悟空', '内容': '师父！弟子再也不敢了！求师父宽恕！'}, {'角色': '须菩提祖师', '内容': '你的本性如此，宽恕又有何用。这里，已经容不下你了。'}, {'角色': '旁白', '内容': '悟空如遭雷击，他从未想过，自己引以为傲的神通，换来的竟是逐客之令。'}, {'角色': '孙悟空', '内容': '师父……您这是要赶我走？弟子该去哪里？'}, {'角色': '须菩提祖师', '内容': '你从哪里来，便回哪里去。'}, {'角色': '孙悟空', '内容': '不！师父！弟子离家二十年，寻仙问道，师恩未报万一，怎敢离去！'}, {'角色': '须菩提祖师', '内容': '不必再提师恩。从你走出这个门开始，我与你之间，再无半分恩义。'}, {'角色': '孙悟空', '内容': '师父……'}, {'角色': '须菩提祖师', '内容': '你此去，无论惹出什么滔天大祸，闯下什么灭顶之灾，都不准说出你是我的徒弟。若敢提我半个字，我便知晓。届时，定将你这猢狲神魂贬入九幽，让你永世不得超生！去吧！'}, {'角色': '旁白', '内容': '悟空含泪叩别，不敢再多言。他捻起诀，纵身一跃，一个筋斗，便是十万八千里。身后，那座学道的灵台方寸山，连同二十年的岁月，都在云海中瞬间化为乌有。他得了长生，得了神通，却也从这一刻起，成了天地间一个真正的孤家寡人。'}]}]}
    script_conflict_escalation_gemini = {
    "剧本": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "宇宙洪荒，混沌未开。直至盘古开天，清浊始分，万物皆在十二万九千六百年的轮回中生灭。东胜神洲，花果山之巅，立着一块仙石。它暗合周天之数，上有九窍八卦之形，日日夜夜，贪婪地吮吸着日月精华。这一日，只听一声巨响，仙石迸裂，一个石猴自卵中化出。他双目睁开，两道金光竟如利剑般刺破云霄，直冲天庭斗牛宫！"
                },
                {
                    "角色": "千里眼",
                    "内容": "陛下，斗牛宫被下界妖光冲撞，天庭秩序微乱！"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "何事惊慌，乱了凌霄宝殿的法度？"
                },
                {
                    "角色": "千里眼",
                    "内容": "臣奉旨巡视，忽见两道金光自下界凡尘，破云而出，直射斗牛宫，所到之处仙气激荡，非同小可！"
                },
                {
                    "角色": "顺风耳",
                    "内容": "臣亦听得那金光之中，隐有风雷之声，似山崩石裂，其势惊人。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "立刻给朕查明，是何方孽障，竟敢窥探天威！"
                },
                {
                    "角色": "千里眼",
                    "内容": "遵旨！"
                },
                {
                    "角色": "旁白",
                    "内容": "凌霄殿上鸦雀无声，片刻之后，二将便已洞悉了下界的一切。"
                },
                {
                    "角色": "千里眼",
                    "内容": "启禀陛下，那金光乃自东胜神洲花果山巅的一块仙石，今日迸裂，产一石猴。"
                },
                {
                    "角色": "顺风耳",
                    "内容": "方才那惊扰天庭的金光，正是那石猴双目初开时所发。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "你的意思是，搅动我天庭秩序的，就是一个刚从石头里蹦出来的猢狲？"
                },
                {
                    "角色": "千里眼",
                    "内容": "陛下……正是。但此猴并非凡物，乃是天地精华所生。那金光中蕴含的灵力，前所未见。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "天地精华？呵，天地间失控的精华还少吗？盘古开天辟地，清气上升，浊气下沉，这秩序便是宇宙的铁律。偶尔有些渣滓，得了些机缘，自以为能撼动乾坤，不过是蜉蝣撼树罢了。"
                },
                {
                    "角色": "旁白",
                    "内容": "天庭的威严，建立在对一切秩序的绝对掌控之上。任何意外，要么被收编，要么被抹杀。而此刻，这石猴甚至不配拥有这两种待遇。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "传朕旨意。下界妖猴，不过是山野顽石成精，由他自生自灭。天庭的威严，不会因一只蝼蚁的窥探而动摇。散了吧。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这石猴混入猴群，倒也自在。每日里追逐打闹，攀藤戏水，浑然不知岁月。直到一个酷暑，山涧干涸，猴群被烈日驱赶，沿着最后一丝水汽溯流而上，寻找生命的源头。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "这瀑布是此行的终点了。水声如雷，撕裂天地，凡胎肉骨，谁敢近前？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "终点？我看是起点。越是这样的地方，越藏着我们要找的东西。一个真正的家，一个不用再四处躲藏的家。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "家？哼，天真的石猴。这后面可能是万丈深渊，可能是妖魔的血盆大口。你的好奇，只会带我们走向灭亡。我们猴族的生存之道是顺应，不是征服。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "顺应？顺应就是被晒死，被饿死，被猛兽吃掉？我生来就不是为了顺应这一切的。你们不敢，我敢。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "好一个‘我敢’！你这天生地养的异类，既然口出狂言，那就立个赌注。你若能进去，并活着出来，证明那后面不是坟墓而是福地，我们这合族老小，就尊你为王！奉你号令！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "王？我不在乎。但如果你们的服从，能换来整个族群的安宁，这个王，我当了。"
                },
                {
                    "角色": "旁白",
                    "内容": "他话音未落，已如离弦之箭，纵身跃入那咆哮的白练之中。水声吞噬了他的身影，也吞噬了岸上所有的议论与质疑。冰冷的激流砸在他身上，却未能阻挡他分毫。仅仅一瞬，喧嚣尽去，眼前豁然开朗。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "水幕是假的……后面竟然是空的。脚下是桥，是铁桥。这天地间竟有如此鬼斧神工。石床石凳，石锅石灶，这里不是洞穴，这是一个早已准备好的王国。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "花果山福地，水帘洞洞天……原来，我们的家，早就刻在了这石碑上，只等一个敢推开门的人。今天，我就是这个人。"
                },
                {
                    "角色": "旁白",
                    "内容": "瀑布之外，猴群已陷入绝望的寂静。就在通背猿猴准备宣布石猴已死之时，水帘被一道金光破开，那石猴逆着激流跃出，站在岩石之巅，目光如炬。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你……你还活着？里面，到底是什么？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "里面没有妖魔，也没有深渊。里面是我们一直渴求，却从未敢奢望的一切。是一个不用再畏惧风雨雷电的家，一个能容纳我们所有子孙的国！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "从今天起，我们不必再把命运交给天气，不必再把生命寄托于侥幸！跟我进去，那里，叫水帘洞！"
                },
                {
                    "角色": "旁白",
                    "内容": "他的声音盖过了瀑布的轰鸣，每一个字都砸在猴群的心上。恐惧被狂喜取代，怀疑被敬畏融化。通背猿猴看着他，眼神复杂，最终深深地俯下了身子。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你说得对，生存不是顺应，是开拓。你为我们寻来了未来。从今往后，你就是我们的王。拜见千岁大王！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "水帘洞内，石锅里炖着山果，藤蔓上挂着佳酿。群猴的喧哗像不息的潮水，拍打着洞府的每一个角落。而美猴王，这片喧嚣的中心，却像潮水中的礁石，沉默着，任由欢声笑语冲刷而过。"
                },
                {
                    "角色": "美猴王",
                    "内容": "三百多年……三百多年的欢宴，不过是一场漫长的告别。你们看看自己，再看看我，这满洞的喧嚣，不过是给死亡唱的赞歌。"
                },
                {
                    "角色": "旁白",
                    "内容": "喧闹声低了下去，猴子们面面相觑，不明白他们那位永远快活的大王，为何说出如此败兴的话。"
                },
                {
                    "角色": "美猴王",
                    "内容": "怎么不说话了？你们是不是想说，大王，你想多了？今天有酒今天醉，管他明天是死是活？死了，就烂在土里，化作春泥，再长出新的果子，不是很好吗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "我告诉你们，不好！我见过！我见过那些老死的猴子，他们的皮毛不再光滑，眼神浑浊，最后就那么悄无声息地倒在角落里，身体一点点变冷。这就是你们的归宿！你们所谓的快活，就是闭着眼睛，排着队，走向那个冰冷的角落！"
                },
                {
                    "角色": "旁白",
                    "内容": "喧闹声彻底消失了。一滴眼泪，从美猴王的眼角滚落，滴入酒杯。杯中酒水漾开的，不是悲哀，而是一种被欺骗了三百年的愤怒与恐惧。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我们自以为跳出红尘，不归人王管束。好一个自由！可笑的自由！我们不过是阎王老子圈养的牲口，等我们老了，血气衰了，他的催命帖一到，谁敢不从？这三百年的称王称霸，到头来，不过是为他的生死簿，添上一笔油墨罢了！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王的话语像淬了冰，让洞内的狂热瞬间冷却。群猴的嬉笑凝固在脸上，面面相觑，第一次在王的眼中看到了与自己截然不同的东西——恐惧。就在这片死寂中，一个苍老的声音从猴群的角落里响起。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王能有此畏，已是心窍开，近乎于道了。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老人家，你有办法？你一定有办法，对不对？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "天地万物，芸芸众生，唯三者可避此劫。"
                },
                {
                    "角色": "美猴王",
                    "内容": "是哪三者？快说！他们现在何处？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "乃是佛、仙、与神圣。此三者，已脱轮回，与天地同寿，不归幽冥所管。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "就在这尘世之中，古洞仙山之内，只看缘法。"
                },
                {
                    "角色": "旁白",
                    "内容": "佛、仙、神圣。三个字，像三道劈开混沌的闪电，瞬间照亮了美猴王被死亡阴影笼罩的内心。那双曾射出金光的眼眸里，重新燃起了火焰，不是为了王权，而是为了向命运宣战。"
                },
                {
                    "角色": "美猴王",
                    "内容": "好！原来路在前方！明日我就出发，踏遍四海，访尽千山，我偏要看看，是我的决心硬，还是那阎王老子的笔硬！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "九年。他告别了喧嚣的王国，独自驶向未知。第一个年头，巨浪教会他敬畏。第三个年头，他登上南赡部洲，披上人的衣冠，将野性锁进一副温顺的皮囊。第五年，他已能在市井中用谎言换取食物，但无人知晓，这人模人样的躯壳下，是一颗拒绝腐烂的猴心。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学会了他们的语言，那种把欲望和恐惧藏在礼貌之下的腔调。我学会了他们的营生，用今天去赌一个虚无缥缈的明天。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他们膜拜黄金，敬畏权力，却对头顶的星辰和脚下的轮回视而不见。他们称之为‘活着’。在我看来，这不过是一场漫长而精致的腐烂。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学的究竟是成仙的法门，还是做人的悲哀？不，道不在此处。真正的答案，一定在海的那一边。"
                },
                {
                    "角色": "旁白",
                    "内容": "他再次扎筏，漂过西海，踏上了西牛贺洲。山林幽深，云锁峰顶，他心中笃定，这一次，他来对了。他无惧豺狼，不畏虎豹，径直向那最深处走去。"
                },
                {
                    "角色": "樵夫",
                    "内容": "观棋柯烂，伐木丁丁，云边谷口徐行……"
                },
                {
                    "角色": "美猴王",
                    "内容": "这歌……"
                },
                {
                    "角色": "樵夫",
                    "内容": "相逢处非仙即道，静坐讲《黄庭》。"
                },
                {
                    "角色": "旁白",
                    "内容": "歌声如同一把钥匙，瞬间开启了猴王心中紧锁近十年的门。他拨开荆棘，看见一个挥斧的凡人，却认定，这就是他追寻的终点。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老神仙！我找了你十年！"
                },
                {
                    "角色": "樵夫",
                    "内容": "你……你认错人了。我不是神仙，只是个砍柴的，当不起这个称呼。"
                },
                {
                    "角色": "美猴王",
                    "内容": "你还敢骗我？《黄庭》是道家真言，‘非仙即道’，这不是你一个凡夫俗子能唱出来的！说，你到底是谁？"
                },
                {
                    "角色": "樵夫",
                    "内容": "客官，你真是误会了。这歌是一个神仙邻居教我的。他看我活得辛苦，教我烦心时唱一唱，能解愁。"
                },
                {
                    "角色": "美猴王",
                    "内容": "神仙邻居？长生不老的机缘就在你隔壁，你却在这里……砍柴？"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，我这苦命人，哪有那个福分。家里还有老娘要养，我若去修仙，谁给她饭吃？"
                },
                {
                    "角色": "美猴王",
                    "内容": "给她饭吃，让她多活几年，然后眼睁睁看着她老死病死，这就是你的孝顺？我所求之道，是让万物跳出生死，你守着门口，却只看到一碗饭？"
                },
                {
                    "角色": "樵夫",
                    "内容": "我不知道什么万物，也不懂什么生死。我只知道，我娘今天不能挨饿。你说的那些大道，太大，太远了。我够不着。"
                },
                {
                    "角色": "美猴王",
                    "内容": "……"
                },
                {
                    "角色": "樵夫",
                    "内容": "你若真想寻仙，就顺着这条路往南走七八里。那山叫灵台方寸山，洞叫斜月三星洞。里面的须菩提祖师，才是真神仙。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山……斜月三星洞……"
                },
                {
                    "角色": "旁白",
                    "内容": "近十年的漂泊，在这一刻，有了清晰的终点。他看着眼前的樵夫，这个守着宝山却甘愿忍受贫穷的凡人，忽然明白了些什么。"
                },
                {
                    "角色": "美猴王",
                    "内容": "多谢指路。这份人情，我不会忘。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "樵夫的身影彻底融入林间。猴王孑然一身，面对着愈发幽深的寂静。光线被层层叠叠的树冠切割成锋利的碎片，空气中满是腐殖土和将死的野花气息。他拨开蛛网般的藤蔓，踏上了一条几乎被遗忘的小径。"
                },
                {
                    "角色": "美猴王",
                    "内容": "守着一个凡人，唱着一首凡歌，就心满意足了？用一条会腐烂的命，去陪另一条即将腐烂的命，这就是他所谓的孝道？"
                },
                {
                    "角色": "美猴王",
                    "内容": "真是……可悲的清醒。他看透了生死，却选择跪在生死面前。而我，是要踩在它的头上。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我的道，不在柴米油盐，不在病榻之前。若不成仙，皆为泡影。"
                },
                {
                    "角色": "旁白",
                    "内容": "他将那个凡人的抉择从脑中驱逐，如掸去肩头的尘土。山势愈发险峻，所谓的“路”，不过是尖利碎石与盘结树根的纠缠。他的呼吸开始灼烧喉咙，汗水黏住了额前的毛发，每一步都像在与整座山角力。"
                },
                {
                    "角色": "美猴王",
                    "内容": "七八里……凡人的一里路，难道比我这筋斗云还远？他莫不是在消遣我？"
                },
                {
                    "角色": "美猴王",
                    "内容": "不对。他眼神里的坦然，不像作伪。那么这山，就是在考验我？考验我这颗求道之心，是否会被凡俗的距离所磨灭？"
                },
                {
                    "角色": "旁白",
                    "内容": "他停步，靠在一棵扭曲的老松上，胸膛剧烈起伏。四周只有风的嘶吼，像无数亡魂在耳边低语。他抬起头，视线穿过交错的枯枝，那几个字，在他疲惫的脑中反复冲撞，带着樵夫平和的音调，显得格外刺耳。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山……斜月三星洞……这到底是什么玄虚……"
                },
                {
                    "角色": "美猴王",
                    "内容": "等等。灵台、方寸……山不在外，而在心头。"
                },
                {
                    "角色": "美猴王",
                    "内容": "斜月、三星……洞非石窟，亦在心间。"
                },
                {
                    "角色": "美猴王",
                    "内容": "原来如此！那樵夫不是在给我指路，他是在问我的心！"
                },
                {
                    "角色": "美猴王",
                    "内容": "哈哈！妙啊！求仙问道，原来是向内求索！这才是神仙的手笔！"
                },
                {
                    "角色": "旁白",
                    "内容": "一道明悟如闪电劈开混沌，疲惫与疑虑瞬间烟消云散。他的身体变得轻盈，不再被脚下的崎岖所累，几个纵跃，便翻上了一处陡峭的山脊。眼前的景象，豁然开朗。"
                },
                {
                    "角色": "美猴王",
                    "内容": "这股清气……不会错了！就是这里！"
                },
                {
                    "角色": "旁白",
                    "内容": "洞门紧闭，万籁无声。崖头立着一块巨大的石碑，青苔遍布，仿佛从亘古便立于此地。石碑上十个大字，笔力穿透岁月，带着一股不容置疑的威严，直刺他的眼底。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山，斜月三星洞……一字不差。我，孙悟空，找到了！"
                }
            ]
        },
        {
            "场景": 6,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "是谁在此喧哗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "仙童！是我，一个寻仙问道的弟子！不敢叨扰。"
                },
                {
                    "角色": "仙童",
                    "内容": "寻道的？我家师父正在讲法，却忽然让我出来开门，说是有个修行的到了。想来就是你了？"
                },
                {
                    "角色": "美猴王",
                    "内容": "是我，是我！"
                },
                {
                    "角色": "仙童",
                    "内容": "随我进来吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王随仙童深入洞府，只见琼楼玉宇，竟是别有洞天。行至瑶台之下，菩提祖师高坐台上，周遭侍立着三十余位仙人。猴王不敢抬头，俯身便拜，额头重重叩在冰冷的石地上，在空旷的殿中发出沉闷的回响。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "台下跪着的，是何方妖物？报上你的来历。"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子非是妖物！弟子是东胜神洲傲来国花果山水帘洞人氏，一心拜师，求个长生不老之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "一派胡言。你我之间，隔着两重汪洋，一整片南赡部洲。你这山野猢狲，凭什么渡那无边苦海，到我这灵台山前？休要在我面前搬弄是非！"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子说的句句是真！弟子乘木筏，飘洋过海，任风刮送，历经十数年，方才寻到此地！这十几年，弟子日日面对的，不是死亡，就是虚无！若无求道之心，早已是一具枯骨！求师父明察！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哦？你倒说说，你既非天地人神鬼，也无父母血脉，你从何而来？"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子……弟子无父无母，乃是花果山顶一块仙石迸裂而出。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "天地所生……原来如此。你这身形，倒像个食松果的猢狲。也罢，我便给你去脱了这身兽骨，换个人名。"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子……不敢奢求！谢师父！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你那“猢”字，去了兽旁，是个“古月”。古者，老也；月者，阴也。老阴不能化生，是条死路。我今赐你姓“孙”，这“孙”字去了兽旁，是个“子系”。子者，儿男；系者，婴细。正合婴儿之本论。从今日起，你便姓孙。"
                },
                {
                    "角色": "美猴王",
                    "内容": "姓孙……姓孙……我……我有姓了。不再是那石猴了……"
                },
                {
                    "角色": "旁白",
                    "内容": "孙，一个脱离了兽类，归于人形的姓氏。猴王反复咀嚼着这个字，仿佛生平第一次拥有了根。他叩首下去，这一次，不再是单纯的恳求，而是带着新生的颤栗与归属。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我门中有十二字，排到你，正当‘悟’字。我再与你起个法名，叫做‘孙悟空’。"
                },
                {
                    "角色": "美猴王",
                    "内容": "孙……悟……空……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你因何出海，又为何寻我？不就是因为那无边无际的“空”吗？如今，我把这“空”字赐给你。你……可悟了？"
                },
                {
                    "角色": "旁白",
                    "内容": "空，是万法皆空，亦是万法之始。这个字如同一道惊雷，劈开了他混沌的识海。从一块顽石的虚无，到啸聚山林的喧嚣，再到此刻跪地求道的虔诚，一切过往皆是这“空”字的注脚。从今往后，他不再是那个无名无姓的石猴，而是孙悟空。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "悟了！弟子悟了！哈哈！我有名字了！我叫孙悟空！弟子孙悟空，拜见师父！"
                }
            ]
        },
        {
            "场景": 7,
            "场景剧本": [
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，七年了。你根性已定，今日，我便传你大道。说吧，你想从我这里学走什么？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不求神通，不求富贵，只求一个长生不死的法门。其余皆是虚妄，还请师父指点。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好个只求长生的猢狲。我这有道三百六十旁门，‘术’字门，可知趋吉避凶。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是躲灾避祸，与长生何干？不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘流’字门，可参儒释道家，坐禅谈玄。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是画中之饼，纸上谈兵。不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘静’字门，可休粮守谷，清净无为。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是苟延残喘，与梁上之柱何异？不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘动’字门，采阴补阳，烧茅打鼎。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是水中之月，镜中之花。捞不得，也摘不下！不学！"
                },
                {
                    "角色": "旁白",
                    "内容": "讲坛之上，祖师的脸色彻底沉了下来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "泼猴！我将大道摆在你面前，你竟百般挑剔！这也不行，那也不要，莫非你万里迢迢而来，就是为了消遣我的吗！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师怒喝一声，从高台走下，手中戒尺带着风声，对着悟空的头，不偏不倚，不轻不重，敲了三下。而后，他竟一言不发，倒背双手，径直走入内堂，将中门砰然关闭，只留下一众弟子满堂惊愕。"
                },
                {
                    "角色": "旁白",
                    "内容": "弟子们顿时炸开了锅，惊惧与鄙夷的目光齐齐射向悟空。斥责他不知好歹的低语，嘲笑他自寻死路的窃笑，混杂成一片嗡鸣。他们看他，就像看一个已经断了仙缘的废物。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "多谢师父传我大道。"
                },
                {
                    "角色": "旁白",
                    "内容": "他竟在笑。众弟子见他非但不惧，反而面露喜色，只当他被师父打傻了，纷纷摇头散去，唯恐沾染了他的晦气。"
                },
                {
                    "角色": "旁白",
                    "内容": "讲堂内空无一人，只剩悟空。他望着那扇紧闭的门，心中一片澄明。三下，是三更时分。背手入内，是从后门进去。这盘中之谜，是师父单独为他设下的考题。"
                }
            ]
        },
        {
            "场景": 8,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "夜色如墨，月光滤过洞府的石窗，在地上投下斑驳的冷辉。祖师的卧房内一片死寂，他并未入睡，只是盘坐在榻上，身影仿佛与黑暗融为一体。悟空蹑足潜行，如一缕幽魂，悄然跪倒在榻前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你来了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子在此，不敢惊扰。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你不是来惊扰我，你是来惊扰天地的。你可知你深夜求的，不是长生，而是一份与天地为敌的契约？一旦签下，再无回头之路。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子漂洋过海，历经十数年，求的就是一条回头无岸的路。若不能跳出生死，我来此何干？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好一个回头无岸。你记住，道不是赠予，是交换。你用与生俱来的逍遥，来换一副挣脱不了的枷锁。近前来，听清这每一个字，它们将成为刻在你魂魄上的烙印。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子，洗耳恭听。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄……休漏泄，体中藏，汝受吾传道自昌……"
                },
                {
                    "角色": "旁白",
                    "内容": "长生之诀，如同一根毒刺，扎进悟空的命脉，开出妖异的花。转眼，又是三年。他将一身野性尽数收敛，炼化成深不见底的沉静。这一日，祖师于高台讲法，话音戛然而止，冰冷的目光锁定了他。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子在。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你自觉根基已固，法力已通，是否觉得天地之大，皆可去得？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "回禀师父，弟子不敢自满，但自觉根源坚固，已窥大道门径。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "窥得门径？你可知门后是什么？你以为长生是赏赐，是安逸？错！那是你偷来的东西，贼就要有被追杀的觉悟。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父何出此言？道高德隆，与天同寿，难道不是修行正果？"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师发出一声冷笑，那笑声里没有半分暖意，只有对天真者的嘲弄与怜悯。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "正果？你所学的法，是夺天地造化，侵日月玄机，本身就是逆天而行！丹成之后，鬼神不容。五百年后，天会降下第一笔债，雷灾打你！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "雷灾……弟子能躲吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "躲？你一身的法力就是引雷的信标！躲不过，就是飞灰烟灭。你若侥幸不死，再过五百年，第二笔债就来了，火灾烧你。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "凡火奈何不了弟子。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "天真！此火唤作‘阴火’，不从天降，不从地起，偏从你自己的涌泉穴下烧将上来，燃尽你的五脏，烧干你的骨髓，你千年苦功，不过是为它备下的一把好柴！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "……还有？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "还有！再五百年，风灾吹你！那风无孔不入，从你顶门灌入，直吹丹田，你的骨肉会被吹得像沙子一样散开，身体自解！悟空，你现在还觉得，长生是一件美事吗？"
                },
                {
                    "角色": "旁白",
                    "内容": "长生的美梦，被现实的酷刑彻底击碎。悟空通体冰凉，那不是恐惧，而是被欺骗后的愤怒与绝望。他以为自己追逐的是永恒，原来只是奔赴一场精心设计的漫长处决。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！你为何要传我这绝路之法！既是死路一条，又何必给我希望！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "路是你自己选的。我只负责告诉你路上有什么。现在，是你求我给你一件能在这条绝路上挣扎求生的兵器。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "求师父垂怜！传我躲灾之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我凭什么传你？你虽有人形，却无资格。你看看你自己，尖嘴缩腮，不过是个成了精的畜类。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我的样貌是天地所生，非我所愿！难道大道也以貌取人？若这天道如此狭隘，那我今日便要看看，是我这猴相碍了道，还是这道，容不下一个我！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好。有这股不认命的狠劲，你才配学。我有天罡三十六变，地煞七十二变。前者是顺天应命，后者是逆天改命。你要学哪一种？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我从不信命！弟子愿学地煞数！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师的眼神里第一次流露出一丝赞许，但稍纵即逝，恢复了古井无波的深邃。他的声音再次压低，仿佛在与另一个世界的存在低语。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "附耳过来。这七十二条活命的法子，也是七十二条通往更大灾祸的路……你听好了。"
                }
            ]
        },
        {
            "场景": 9,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "灵台方寸山的一个夏日午后，光影在松针间筛落成斑驳的碎金。几位师兄弟在树下闲谈，话锋一转，便带着几分无法掩饰的嫉妒与挑衅，飘向了那个新来的石猴。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "悟空，我们都在这苦熬岁月，你却得了师父的私传。那七十二变，可是无上大道？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父慈悲，见我顽劣，才多教了几句保命的法子，算不得什么大道。"
                },
                {
                    "角色": "师兄乙",
                    "内容": "保命的法子？我们穷尽一生也未必能窥得一二。你倒说得轻巧。莫不是……师父教的只是口诀，你根本还没练成？"
                },
                {
                    "角色": "师兄甲",
                    "内容": "空谈大道谁都会。我等修行，求的是一个“真”字。你若真有本事，何必藏着掖着？还是说，你怕了？怕在众师兄弟面前，丢了师父给你挣来的脸面？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父有戒，神通不可轻易示人。"
                },
                {
                    "角色": "师兄乙",
                    "内容": "你看，他果然是心虚了。什么戒律，不过是无能的借口。我们自家兄弟，又不是外人，不过是想开开眼，见识一下真传妙法，这也不行？"
                },
                {
                    "角色": "旁白",
                    "内容": "那一句“无能的借口”像一簇火苗，瞬间点燃了孙悟空骨子里的骄傲。师父的告诫，在虚荣与好胜的妖性面前，被焚烧殆尽。他笑了，那笑容里带着一丝轻蔑。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "也罢。既然师兄们如此盛情，我便献丑了。说吧，想看我变成什么？"
                },
                {
                    "角色": "师兄甲",
                    "内容": "就变作眼前这棵苍松。此树最见风骨，也最难摹仿其神韵，最是考验功力。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！都看清楚了！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空身形一晃，并非消失，而是溶解。他的血肉筋骨在一瞬间失去了固有的形态，化作一道青烟，随即又重新凝聚。骨骼是虬结的树干，经脉是盘错的根须，根根毫毛都化作了青翠的松针。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "不见了！悟空……他不见了！"
                },
                {
                    "角色": "师兄乙",
                    "内容": "不对！看！那棵松树！纹理、色泽、连松针上的露水都一般无二！天啊，这就是真传！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师兄们，我这松树可还挺拔？"
                },
                {
                    "角色": "旁白",
                    "内容": "声音从树干深处传来，带着木质的共鸣，戏谑而又得意。众师兄弟爆发出惊叹与喝彩，掌声与笑声在宁静的山林中回荡，也惊动了那个最不该被惊动的人。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "神乎其技！真是神乎其技！"
                },
                {
                    "角色": "师兄乙",
                    "内容": "好猴子！当真学到了真本事！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好一个热闹的戏班子。你们……在为什么喝彩？"
                },
                {
                    "角色": "旁白",
                    "内容": "声音平淡，却如寒冰冻结了空气。须菩提祖师不知何时已站在众人身后，面无表情。所有的喧哗戛然而止，师兄弟们瞬间噤若寒蝉，纷纷退散，只留下那棵突兀的松树。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，还要我请你现出原形吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你错在哪里？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不该……不该在人前卖弄神通。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "卖弄？我传你躲避三灾之法，是让你藏身、保命，不是让你拿来换几声廉价的叫好！你把大道当成了什么？街头杂耍的把戏？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不敢……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你敢得很！你渴望被看见，享受被吹捧，这便是你的心魔，是改不掉的妖性！别人看见的是一棵松树，我看见的，是你亲手为自己立下的墓碑！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "没有下次了。记住我的话，神通显露之日，便是灾祸上门之时。今日你为了一声喝彩变棵松树，他日，你就会为了一个虚名，去捅破这天！你这孽畜，与我无缘了。"
                }
            ]
        },
        {
            "场景": 10,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "松树变回了猴王，喧闹的喝彩声却在祖师冰冷的目光下凝结成一片死寂。悟空脸上的得意还未褪去，就已被一种不祥的预感攫住，他跪倒在地，声音里带着不解与抗辩。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子知错。可……炫耀神通，罪至于此吗？您传我大道，不就是为了让我脱胎换骨，不再是那个蒙昧石猴吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我渡你，是让你看清自己，不是让你成为众人的幻影。你渴求的不是大道，是喝彩。那喝彩声，就是催你走向毁灭的丧钟。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "喝彩又如何？难道身怀利器，就该藏于鞘中，直至锈蚀？难道这通天的本事，就只配在无人处孤芳自赏？这是什么道理！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "道理？你这猢狲，什么时候问过道理？你只问‘能不能’，从不问‘该不该’。我教你七十二变，是让你躲避三灾，你却拿来变成一棵松树取乐。我错了，我错在以为能将一把绝世凶器，磨成一尊护法神像。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不明白……我究竟做错了什么，要您说出如此绝情的话？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你没错。是你的天性没错。你的心太大了，大到这方寸山容不下，这清规戒律缚不住。它只容得下四个字——齐天大圣。"
                },
                {
                    "角色": "旁白",
                    "内容": "“齐天大圣”。四个字，如同一道惊雷，劈开了时空的迷雾，让祖师瞥见了未来的血海与烽烟。而此刻的悟空，只能感到这四个字滚烫的重量，却无法洞悉其中蕴含的，究竟是荣耀，还是宿命的枷锁。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你此去，定生祸端。记住，不许对任何人说，你是我的徒弟。我教不了你收敛心性，只能教你如何独自面对。这，是我能给你的最后一课。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……若我此去，再不见您。那我这一身本事，究竟算什么？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是你自己的造化，也是你自己的罪业。与我无关。还有，你若对任何人泄露此地，哪怕只说出半个字，我便将你这猢狲神魂贬入九幽，叫你万劫不得翻身！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "……弟子明白了。从此，世上再无师承。这一身本事，是我孙悟空，天生就会的。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "去吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "他磕了最后一个头，再无言语。一个筋斗，翻出了十万八千里，也翻出了此生的师徒缘分。身后，是再也回不去的斜月三星洞；眼前，是阔别二十年的花果山。他学成了长生，却被逐出了道法之门；他炼就了通天本领，却成了天地间最孤独的一个。那个寻仙问道的美猴王走了，此刻归来的，是孙悟空。"
                }
            ]
        }
    ]
}
    script_conflict_escalation_gemini = remove_parentheses_in_script(script_conflict_escalation_gemini)

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
            "审查结果": "需修改",
            "问题清单": [
                {
                    "维度": "角色一致性",
                    "问题描述": "在当前场景，主角尚未拜师学艺，其身份应为“石猴”，剧本中使用了其后来的名字“孙悟空”，不符合角色在故事当前阶段的身份设定，造成了时序和角色发展上的矛盾。",
                    "修改建议": "请将剧本中所有“角色”字段为“孙悟空”的条目，统一修改为“石猴”，以确保角色称谓与故事发展阶段保持一致。例如，将‘{\"角色\": \"孙悟空\", \"内容\": \"...\"}’修改为‘{\"角色\": \"石猴\", \"内容\": \"...\"}’。"
                }
            ]
        },
        {
            "场景": 3,
            "审查结果": "通过",
            "问题清单": []
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
        },
        {
            "场景": 6,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 7,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 8,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 9,
            "审查结果": "通过",
            "问题清单": []
        },
        {
            "场景": 10,
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
                    "内容": "宇宙洪荒，混沌未开。直至盘古开天，清浊始分，万物皆在十二万九千六百年的轮回中生灭。东胜神洲，花果山之巅，立着一块仙石。它暗合周天之数，上有九窍八卦之形，日日夜夜，贪婪地吮吸着日月精华。这一日，只听一声巨响，仙石迸裂，一个石猴自卵中化出。他双目睁开，两道金光竟如利剑般刺破云霄，直冲天庭斗牛宫！"
                },
                {
                    "角色": "千里眼",
                    "内容": "陛下，斗牛宫被下界妖光冲撞，天庭秩序微乱！"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "何事惊慌，乱了凌霄宝殿的法度？"
                },
                {
                    "角色": "千里眼",
                    "内容": "臣奉旨巡视，忽见两道金光自下界凡尘，破云而出，直射斗牛宫，所到之处仙气激荡，非同小可！"
                },
                {
                    "角色": "顺风耳",
                    "内容": "臣亦听得那金光之中，隐有风雷之声，似山崩石裂，其势惊人。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "立刻给朕查明，是何方孽障，竟敢窥探天威！"
                },
                {
                    "角色": "千里眼",
                    "内容": "遵旨！"
                },
                {
                    "角色": "旁白",
                    "内容": "凌霄殿上鸦雀无声，片刻之后，二将便已洞悉了下界的一切。"
                },
                {
                    "角色": "千里眼",
                    "内容": "启禀陛下，那金光乃自东胜神洲花果山巅的一块仙石，今日迸裂，产一石猴。"
                },
                {
                    "角色": "顺风耳",
                    "内容": "方才那惊扰天庭的金光，正是那石猴双目初开时所发。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "你的意思是，搅动我天庭秩序的，就是一个刚从石头里蹦出来的猢狲？"
                },
                {
                    "角色": "千里眼",
                    "内容": "陛下……正是。但此猴并非凡物，乃是天地精华所生。那金光中蕴含的灵力，前所未见。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "天地精华？呵，天地间失控的精华还少吗？盘古开天辟地，清气上升，浊气下沉，这秩序便是宇宙的铁律。偶尔有些渣滓，得了些机缘，自以为能撼动乾坤，不过是蜉蝣撼树罢了。"
                },
                {
                    "角色": "旁白",
                    "内容": "天庭的威严，建立在对一切秩序的绝对掌控之上。任何意外，要么被收编，要么被抹杀。而此刻，这石猴甚至不配拥有这两种待遇。"
                },
                {
                    "角色": "玉皇大帝",
                    "内容": "传朕旨意。下界妖猴，不过是山野顽石成精，由他自生自灭。天庭的威严，不会因一只蝼蚁的窥探而动摇。散了吧。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "这石猴混入猴群，倒也自在。每日里追逐打闹，攀藤戏水，浑然不知岁月。直到一个酷暑，山涧干涸，猴群被烈日驱赶，沿着最后一丝水汽溯流而上，寻找生命的源头。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "这瀑布是此行的终点了。水声如雷，撕裂天地，凡胎肉骨，谁敢近前？"
                },
                {
                    "角色": "石猴",
                    "内容": "终点？我看是起点。越是这样的地方，越藏着我们要找的东西。一个真正的家，一个不用再四处躲藏的家。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "家？哼，天真的石猴。这后面可能是万丈深渊，可能是妖魔的血盆大口。你的好奇，只会带我们走向灭亡。我们猴族的生存之道是顺应，不是征服。"
                },
                {
                    "角色": "石猴",
                    "内容": "顺应？顺应就是被晒死，被饿死，被猛兽吃掉？我生来就不是为了顺应这一切的。你们不敢，我敢。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "好一个‘我敢’！你这天生地养的异类，既然口出狂言，那就立个赌注。你若能进去，并活着出来，证明那后面不是坟墓而是福地，我们这合族老小，就尊你为王！奉你号令！"
                },
                {
                    "角色": "石猴",
                    "内容": "王？我不在乎。但如果你们的服从，能换来整个族群的安宁，这个王，我当了。"
                },
                {
                    "角色": "旁白",
                    "内容": "他话音未落，已如离弦之箭，纵身跃入那咆哮的白练之中。水声吞噬了他的身影，也吞噬了岸上所有的议论与质疑。冰冷的激流砸在他身上，却未能阻挡他分毫。仅仅一瞬，喧嚣尽去，眼前豁然开朗。"
                },
                {
                    "角色": "石猴",
                    "内容": "水幕是假的……后面竟然是空的。脚下是桥，是铁桥。这天地间竟有如此鬼斧神工。石床石凳，石锅石灶，这里不是洞穴，这是一个早已准备好的王国。"
                },
                {
                    "角色": "石猴",
                    "内容": "花果山福地，水帘洞洞天……原来，我们的家，早就刻在了这石碑上，只等一个敢推开门的人。今天，我就是这个人。"
                },
                {
                    "角色": "旁白",
                    "内容": "瀑布之外，猴群已陷入绝望的寂静。就在通背猿猴准备宣布石猴已死之时，水帘被一道金光破开，那石猴逆着激流跃出，站在岩石之巅，目光如炬。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你……你还活着？里面，到底是什么？"
                },
                {
                    "角色": "石猴",
                    "内容": "里面没有妖魔，也没有深渊。里面是我们一直渴求，却从未敢奢望的一切。是一个不用再畏惧风雨雷电的家，一个能容纳我们所有子孙的国！"
                },
                {
                    "角色": "石猴",
                    "内容": "从今天起，我们不必再把命运交给天气，不必再把生命寄托于侥幸！跟我进去，那里，叫水帘洞！"
                },
                {
                    "角色": "旁白",
                    "内容": "他的声音盖过了瀑布的轰鸣，每一个字都砸在猴群的心上。恐惧被狂喜取代，怀疑被敬畏融化。通背猿猴看着他，眼神复杂，最终深深地俯下了身子。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "你说得对，生存不是顺应，是开拓。你为我们寻来了未来。从今往后，你就是我们的王。拜见千岁大王！"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "水帘洞内，石锅里炖着山果，藤蔓上挂着佳酿。群猴的喧哗像不息的潮水，拍打着洞府的每一个角落。而美猴王，这片喧嚣的中心，却像潮水中的礁石，沉默着，任由欢声笑语冲刷而过。"
                },
                {
                    "角色": "美猴王",
                    "内容": "三百多年……三百多年的欢宴，不过是一场漫长的告别。你们看看自己，再看看我，这满洞的喧嚣，不过是给死亡唱的赞歌。"
                },
                {
                    "角色": "旁白",
                    "内容": "喧闹声低了下去，猴子们面面相觑，不明白他们那位永远快活的大王，为何说出如此败兴的话。"
                },
                {
                    "角色": "美猴王",
                    "内容": "怎么不说话了？你们是不是想说，大王，你想多了？今天有酒今天醉，管他明天是死是活？死了，就烂在土里，化作春泥，再长出新的果子，不是很好吗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "我告诉你们，不好！我见过！我见过那些老死的猴子，他们的皮毛不再光滑，眼神浑浊，最后就那么悄无声息地倒在角落里，身体一点点变冷。这就是你们的归宿！你们所谓的快活，就是闭着眼睛，排着队，走向那个冰冷的角落！"
                },
                {
                    "角色": "旁白",
                    "内容": "喧闹声彻底消失了。一滴眼泪，从美猴王的眼角滚落，滴入酒杯。杯中酒水漾开的，不是悲哀，而是一种被欺骗了三百年的愤怒与恐惧。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我们自以为跳出红尘，不归人王管束。好一个自由！可笑的自由！我们不过是阎王老子圈养的牲口，等我们老了，血气衰了，他的催命帖一到，谁敢不从？这三百年的称王称霸，到头来，不过是为他的生死簿，添上一笔油墨罢了！"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王的话语像淬了冰，让洞内的狂热瞬间冷却。群猴的嬉笑凝固在脸上，面面相觑，第一次在王的眼中看到了与自己截然不同的东西——恐惧。就在这片死寂中，一个苍老的声音从猴群的角落里响起。"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "大王能有此畏，已是心窍开，近乎于道了。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老人家，你有办法？你一定有办法，对不对？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "天地万物，芸芸众生，唯三者可避此劫。"
                },
                {
                    "角色": "美猴王",
                    "内容": "是哪三者？快说！他们现在何处？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "乃是佛、仙、与神圣。此三者，已脱轮回，与天地同寿，不归幽冥所管。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他们住在哪儿？"
                },
                {
                    "角色": "通背猿猴",
                    "内容": "就在这尘世之中，古洞仙山之内，只看缘法。"
                },
                {
                    "角色": "旁白",
                    "内容": "佛、仙、神圣。三个字，像三道劈开混沌的闪电，瞬间照亮了美猴王被死亡阴影笼罩的内心。那双曾射出金光的眼眸里，重新燃起了火焰，不是为了王权，而是为了向命运宣战。"
                },
                {
                    "角色": "美猴王",
                    "内容": "好！原来路在前方！明日我就出发，踏遍四海，访尽千山，我偏要看看，是我的决心硬，还是那阎王老子的笔硬！"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "九年。他告别了喧嚣的王国，独自驶向未知。第一个年头，巨浪教会他敬畏。第三个年头，他登上南赡部洲，披上人的衣冠，将野性锁进一副温顺的皮囊。第五年，他已能在市井中用谎言换取食物，但无人知晓，这人模人样的躯壳下，是一颗拒绝腐烂的猴心。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学会了他们的语言，那种把欲望和恐惧藏在礼貌之下的腔调。我学会了他们的营生，用今天去赌一个虚无缥缈的明天。"
                },
                {
                    "角色": "美猴王",
                    "内容": "他们膜拜黄金，敬畏权力，却对头顶的星辰和脚下的轮回视而不见。他们称之为‘活着’。在我看来，这不过是一场漫长而精致的腐烂。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我学的究竟是成仙的法门，还是做人的悲哀？不，道不在此处。真正的答案，一定在海的那一边。"
                },
                {
                    "角色": "旁白",
                    "内容": "他再次扎筏，漂过西海，踏上了西牛贺洲。山林幽深，云锁峰顶，他心中笃定，这一次，他来对了。他无惧豺狼，不畏虎豹，径直向那最深处走去。"
                },
                {
                    "角色": "樵夫",
                    "内容": "观棋柯烂，伐木丁丁，云边谷口徐行……"
                },
                {
                    "角色": "美猴王",
                    "内容": "这歌……"
                },
                {
                    "角色": "樵夫",
                    "内容": "相逢处非仙即道，静坐讲《黄庭》。"
                },
                {
                    "角色": "旁白",
                    "内容": "歌声如同一把钥匙，瞬间开启了猴王心中紧锁近十年的门。他拨开荆棘，看见一个挥斧的凡人，却认定，这就是他追寻的终点。"
                },
                {
                    "角色": "美猴王",
                    "内容": "老神仙！我找了你十年！"
                },
                {
                    "角色": "樵夫",
                    "内容": "你……你认错人了。我不是神仙，只是个砍柴的，当不起这个称呼。"
                },
                {
                    "角色": "美猴王",
                    "内容": "你还敢骗我？《黄庭》是道家真言，‘非仙即道’，这不是你一个凡夫俗子能唱出来的！说，你到底是谁？"
                },
                {
                    "角色": "樵夫",
                    "内容": "客官，你真是误会了。这歌是一个神仙邻居教我的。他看我活得辛苦，教我烦心时唱一唱，能解愁。"
                },
                {
                    "角色": "美猴王",
                    "内容": "神仙邻居？长生不老的机缘就在你隔壁，你却在这里……砍柴？"
                },
                {
                    "角色": "樵夫",
                    "内容": "唉，我这苦命人，哪有那个福分。家里还有老娘要养，我若去修仙，谁给她饭吃？"
                },
                {
                    "角色": "美猴王",
                    "内容": "给她饭吃，让她多活几年，然后眼睁睁看着她老死病死，这就是你的孝顺？我所求之道，是让万物跳出生死，你守着门口，却只看到一碗饭？"
                },
                {
                    "角色": "樵夫",
                    "内容": "我不知道什么万物，也不懂什么生死。我只知道，我娘今天不能挨饿。你说的那些大道，太大，太远了。我够不着。"
                },
                {
                    "角色": "美猴王",
                    "内容": "……"
                },
                {
                    "角色": "樵夫",
                    "内容": "你若真想寻仙，就顺着这条路往南走七八里。那山叫灵台方寸山，洞叫斜月三星洞。里面的须菩提祖师，才是真神仙。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山……斜月三星洞……"
                },
                {
                    "角色": "旁白",
                    "内容": "近十年的漂泊，在这一刻，有了清晰的终点。他看着眼前的樵夫，这个守着宝山却甘愿忍受贫穷的凡人，忽然明白了些什么。"
                },
                {
                    "角色": "美猴王",
                    "内容": "多谢指路。这份人情，我不会忘。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "樵夫的身影彻底融入林间。猴王孑然一身，面对着愈发幽深的寂静。光线被层层叠叠的树冠切割成锋利的碎片，空气中满是腐殖土和将死的野花气息。他拨开蛛网般的藤蔓，踏上了一条几乎被遗忘的小径。"
                },
                {
                    "角色": "美猴王",
                    "内容": "守着一个凡人，唱着一首凡歌，就心满意足了？用一条会腐烂的命，去陪另一条即将腐烂的命，这就是他所谓的孝道？"
                },
                {
                    "角色": "美猴王",
                    "内容": "真是……可悲的清醒。他看透了生死，却选择跪在生死面前。而我，是要踩在它的头上。"
                },
                {
                    "角色": "美猴王",
                    "内容": "我的道，不在柴米油盐，不在病榻之前。若不成仙，皆为泡影。"
                },
                {
                    "角色": "旁白",
                    "内容": "他将那个凡人的抉择从脑中驱逐，如掸去肩头的尘土。山势愈发险峻，所谓的“路”，不过是尖利碎石与盘结树根的纠缠。他的呼吸开始灼烧喉咙，汗水黏住了额前的毛发，每一步都像在与整座山角力。"
                },
                {
                    "角色": "美猴王",
                    "内容": "七八里……凡人的一里路，难道比我这筋斗云还远？他莫不是在消遣我？"
                },
                {
                    "角色": "美猴王",
                    "内容": "不对。他眼神里的坦然，不像作伪。那么这山，就是在考验我？考验我这颗求道之心，是否会被凡俗的距离所磨灭？"
                },
                {
                    "角色": "旁白",
                    "内容": "他停步，靠在一棵扭曲的老松上，胸膛剧烈起伏。四周只有风的嘶吼，像无数亡魂在耳边低语。他抬起头，视线穿过交错的枯枝，那几个字，在他疲惫的脑中反复冲撞，带着樵夫平和的音调，显得格外刺耳。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山……斜月三星洞……这到底是什么玄虚……"
                },
                {
                    "角色": "美猴王",
                    "内容": "等等。灵台、方寸……山不在外，而在心头。"
                },
                {
                    "角色": "美猴王",
                    "内容": "斜月、三星……洞非石窟，亦在心间。"
                },
                {
                    "角色": "美猴王",
                    "内容": "原来如此！那樵夫不是在给我指路，他是在问我的心！"
                },
                {
                    "角色": "美猴王",
                    "内容": "哈哈！妙啊！求仙问道，原来是向内求索！这才是神仙的手笔！"
                },
                {
                    "角色": "旁白",
                    "内容": "一道明悟如闪电劈开混沌，疲惫与疑虑瞬间烟消云散。他的身体变得轻盈，不再被脚下的崎岖所累，几个纵跃，便翻上了一处陡峭的山脊。眼前的景象，豁然开朗。"
                },
                {
                    "角色": "美猴王",
                    "内容": "这股清气……不会错了！就是这里！"
                },
                {
                    "角色": "旁白",
                    "内容": "洞门紧闭，万籁无声。崖头立着一块巨大的石碑，青苔遍布，仿佛从亘古便立于此地。石碑上十个大字，笔力穿透岁月，带着一股不容置疑的威严，直刺他的眼底。"
                },
                {
                    "角色": "美猴王",
                    "内容": "灵台方寸山，斜月三星洞……一字不差。我，孙悟空，找到了！"
                }
            ]
        },
        {
            "场景": 6,
            "场景剧本": [
                {
                    "角色": "仙童",
                    "内容": "是谁在此喧哗？"
                },
                {
                    "角色": "美猴王",
                    "内容": "仙童！是我，一个寻仙问道的弟子！不敢叨扰。"
                },
                {
                    "角色": "仙童",
                    "内容": "寻道的？我家师父正在讲法，却忽然让我出来开门，说是有个修行的到了。想来就是你了？"
                },
                {
                    "角色": "美猴王",
                    "内容": "是我，是我！"
                },
                {
                    "角色": "仙童",
                    "内容": "随我进来吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "猴王随仙童深入洞府，只见琼楼玉宇，竟是别有洞天。行至瑶台之下，菩提祖师高坐台上，周遭侍立着三十余位仙人。猴王不敢抬头，俯身便拜，额头重重叩在冰冷的石地上，在空旷的殿中发出沉闷的回响。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "台下跪着的，是何方妖物？报上你的来历。"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子非是妖物！弟子是东胜神洲傲来国花果山水帘洞人氏，一心拜师，求个长生不老之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "一派胡言。你我之间，隔着两重汪洋，一整片南赡部洲。你这山野猢狲，凭什么渡那无边苦海，到我这灵台山前？休要在我面前搬弄是非！"
                },
                {
                    "角色": "美猴王",
                    "内容": "师父！弟子说的句句是真！弟子乘木筏，飘洋过海，任风刮送，历经十数年，方才寻到此地！这十几年，弟子日日面对的，不是死亡，就是虚无！若无求道之心，早已是一具枯骨！求师父明察！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "哦？你倒说说，你既非天地人神鬼，也无父母血脉，你从何而来？"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子……弟子无父无母，乃是花果山顶一块仙石迸裂而出。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "天地所生……原来如此。你这身形，倒像个食松果的猢狲。也罢，我便给你去脱了这身兽骨，换个人名。"
                },
                {
                    "角色": "美猴王",
                    "内容": "弟子……不敢奢求！谢师父！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你那“猢”字，去了兽旁，是个“古月”。古者，老也；月者，阴也。老阴不能化生，是条死路。我今赐你姓“孙”，这“孙”字去了兽旁，是个“子系”。子者，儿男；系者，婴细。正合婴儿之本论。从今日起，你便姓孙。"
                },
                {
                    "角色": "美猴王",
                    "内容": "姓孙……姓孙……我……我有姓了。不再是那石猴了……"
                },
                {
                    "角色": "旁白",
                    "内容": "孙，一个脱离了兽类，归于人形的姓氏。猴王反复咀嚼着这个字，仿佛生平第一次拥有了根。他叩首下去，这一次，不再是单纯的恳求，而是带着新生的颤栗与归属。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我门中有十二字，排到你，正当‘悟’字。我再与你起个法名，叫做‘孙悟空’。"
                },
                {
                    "角色": "美猴王",
                    "内容": "孙……悟……空……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你因何出海，又为何寻我？不就是因为那无边无际的“空”吗？如今，我把这“空”字赐给你。你……可悟了？"
                },
                {
                    "角色": "旁白",
                    "内容": "空，是万法皆空，亦是万法之始。这个字如同一道惊雷，劈开了他混沌的识海。从一块顽石的虚无，到啸聚山林的喧嚣，再到此刻跪地求道的虔诚，一切过往皆是这“空”字的注脚。从今往后，他不再是那个无名无姓的石猴，而是孙悟空。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "悟了！弟子悟了！哈哈！我有名字了！我叫孙悟空！弟子孙悟空，拜见师父！"
                }
            ]
        },
        {
            "场景": 7,
            "场景剧本": [
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，七年了。你根性已定，今日，我便传你大道。说吧，你想从我这里学走什么？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不求神通，不求富贵，只求一个长生不死的法门。其余皆是虚妄，还请师父指点。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好个只求长生的猢狲。我这有道三百六十旁门，‘术’字门，可知趋吉避凶。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是躲灾避祸，与长生何干？不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘流’字门，可参儒释道家，坐禅谈玄。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是画中之饼，纸上谈兵。不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘静’字门，可休粮守谷，清净无为。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是苟延残喘，与梁上之柱何异？不学！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "‘动’字门，采阴补阳，烧茅打鼎。能长生否？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "不过是水中之月，镜中之花。捞不得，也摘不下！不学！"
                },
                {
                    "角色": "旁白",
                    "内容": "讲坛之上，祖师的脸色彻底沉了下来。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "泼猴！我将大道摆在你面前，你竟百般挑剔！这也不行，那也不要，莫非你万里迢迢而来，就是为了消遣我的吗！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师怒喝一声，从高台走下，手中戒尺带着风声，对着悟空的头，不偏不倚，不轻不重，敲了三下。而后，他竟一言不发，倒背双手，径直走入内堂，将中门砰然关闭，只留下一众弟子满堂惊愕。"
                },
                {
                    "角色": "旁白",
                    "内容": "弟子们顿时炸开了锅，惊惧与鄙夷的目光齐齐射向悟空。斥责他不知好歹的低语，嘲笑他自寻死路的窃笑，混杂成一片嗡鸣。他们看他，就像看一个已经断了仙缘的废物。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "多谢师父传我大道。"
                },
                {
                    "角色": "旁白",
                    "内容": "他竟在笑。众弟子见他非但不惧，反而面露喜色，只当他被师父打傻了，纷纷摇头散去，唯恐沾染了他的晦气。"
                },
                {
                    "角色": "旁白",
                    "内容": "讲堂内空无一人，只剩悟空。他望着那扇紧闭的门，心中一片澄明。三下，是三更时分。背手入内，是从后门进去。这盘中之谜，是师父单独为他设下的考题。"
                }
            ]
        },
        {
            "场景": 8,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "夜色如墨，月光滤过洞府的石窗，在地上投下斑驳的冷辉。祖师的卧房内一片死寂，他并未入睡，只是盘坐在榻上，身影仿佛与黑暗融为一体。悟空蹑足潜行，如一缕幽魂，悄然跪倒在榻前。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你来了。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子在此，不敢惊扰。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你不是来惊扰我，你是来惊扰天地的。你可知你深夜求的，不是长生，而是一份与天地为敌的契约？一旦签下，再无回头之路。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子漂洋过海，历经十数年，求的就是一条回头无岸的路。若不能跳出生死，我来此何干？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好一个回头无岸。你记住，道不是赠予，是交换。你用与生俱来的逍遥，来换一副挣脱不了的枷锁。近前来，听清这每一个字，它们将成为刻在你魂魄上的烙印。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子，洗耳恭听。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "显密圆通真妙诀，惜修生命无他说。都来总是精气神，谨固牢藏休漏泄……休漏泄，体中藏，汝受吾传道自昌……"
                },
                {
                    "角色": "旁白",
                    "内容": "长生之诀，如同一根毒刺，扎进悟空的命脉，开出妖异的花。转眼，又是三年。他将一身野性尽数收敛，炼化成深不见底的沉静。这一日，祖师于高台讲法，话音戛然而止，冰冷的目光锁定了他。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子在。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你自觉根基已固，法力已通，是否觉得天地之大，皆可去得？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "回禀师父，弟子不敢自满，但自觉根源坚固，已窥大道门径。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "窥得门径？你可知门后是什么？你以为长生是赏赐，是安逸？错！那是你偷来的东西，贼就要有被追杀的觉悟。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父何出此言？道高德隆，与天同寿，难道不是修行正果？"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师发出一声冷笑，那笑声里没有半分暖意，只有对天真者的嘲弄与怜悯。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "正果？你所学的法，是夺天地造化，侵日月玄机，本身就是逆天而行！丹成之后，鬼神不容。五百年后，天会降下第一笔债，雷灾打你！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "雷灾……弟子能躲吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "躲？你一身的法力就是引雷的信标！躲不过，就是飞灰烟灭。你若侥幸不死，再过五百年，第二笔债就来了，火灾烧你。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "凡火奈何不了弟子。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "天真！此火唤作‘阴火’，不从天降，不从地起，偏从你自己的涌泉穴下烧将上来，燃尽你的五脏，烧干你的骨髓，你千年苦功，不过是为它备下的一把好柴！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "……还有？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "还有！再五百年，风灾吹你！那风无孔不入，从你顶门灌入，直吹丹田，你的骨肉会被吹得像沙子一样散开，身体自解！悟空，你现在还觉得，长生是一件美事吗？"
                },
                {
                    "角色": "旁白",
                    "内容": "长生的美梦，被现实的酷刑彻底击碎。悟空通体冰凉，那不是恐惧，而是被欺骗后的愤怒与绝望。他以为自己追逐的是永恒，原来只是奔赴一场精心设计的漫长处决。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！你为何要传我这绝路之法！既是死路一条，又何必给我希望！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "路是你自己选的。我只负责告诉你路上有什么。现在，是你求我给你一件能在这条绝路上挣扎求生的兵器。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "求师父垂怜！传我躲灾之法！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我凭什么传你？你虽有人形，却无资格。你看看你自己，尖嘴缩腮，不过是个成了精的畜类。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我的样貌是天地所生，非我所愿！难道大道也以貌取人？若这天道如此狭隘，那我今日便要看看，是我这猴相碍了道，还是这道，容不下一个我！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好。有这股不认命的狠劲，你才配学。我有天罡三十六变，地煞七十二变。前者是顺天应命，后者是逆天改命。你要学哪一种？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "我从不信命！弟子愿学地煞数！"
                },
                {
                    "角色": "旁白",
                    "内容": "祖师的眼神里第一次流露出一丝赞许，但稍纵即逝，恢复了古井无波的深邃。他的声音再次压低，仿佛在与另一个世界的存在低语。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "附耳过来。这七十二条活命的法子，也是七十二条通往更大灾祸的路……你听好了。"
                }
            ]
        },
        {
            "场景": 9,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "灵台方寸山的一个夏日午后，光影在松针间筛落成斑驳的碎金。几位师兄弟在树下闲谈，话锋一转，便带着几分无法掩饰的嫉妒与挑衅，飘向了那个新来的石猴。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "悟空，我们都在这苦熬岁月，你却得了师父的私传。那七十二变，可是无上大道？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父慈悲，见我顽劣，才多教了几句保命的法子，算不得什么大道。"
                },
                {
                    "角色": "师兄乙",
                    "内容": "保命的法子？我们穷尽一生也未必能窥得一二。你倒说得轻巧。莫不是……师父教的只是口诀，你根本还没练成？"
                },
                {
                    "角色": "师兄甲",
                    "内容": "空谈大道谁都会。我等修行，求的是一个“真”字。你若真有本事，何必藏着掖着？还是说，你怕了？怕在众师兄弟面前，丢了师父给你挣来的脸面？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父有戒，神通不可轻易示人。"
                },
                {
                    "角色": "师兄乙",
                    "内容": "你看，他果然是心虚了。什么戒律，不过是无能的借口。我们自家兄弟，又不是外人，不过是想开开眼，见识一下真传妙法，这也不行？"
                },
                {
                    "角色": "旁白",
                    "内容": "那一句“无能的借口”像一簇火苗，瞬间点燃了孙悟空骨子里的骄傲。师父的告诫，在虚荣与好胜的妖性面前，被焚烧殆尽。他笑了，那笑容里带着一丝轻蔑。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "也罢。既然师兄们如此盛情，我便献丑了。说吧，想看我变成什么？"
                },
                {
                    "角色": "师兄甲",
                    "内容": "就变作眼前这棵苍松。此树最见风骨，也最难摹仿其神韵，最是考验功力。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "好！都看清楚了！"
                },
                {
                    "角色": "旁白",
                    "内容": "孙悟空身形一晃，并非消失，而是溶解。他的血肉筋骨在一瞬间失去了固有的形态，化作一道青烟，随即又重新凝聚。骨骼是虬结的树干，经脉是盘错的根须，根根毫毛都化作了青翠的松针。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "不见了！悟空……他不见了！"
                },
                {
                    "角色": "师兄乙",
                    "内容": "不对！看！那棵松树！纹理、色泽、连松针上的露水都一般无二！天啊，这就是真传！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师兄们，我这松树可还挺拔？"
                },
                {
                    "角色": "旁白",
                    "内容": "声音从树干深处传来，带着木质的共鸣，戏谑而又得意。众师兄弟爆发出惊叹与喝彩，掌声与笑声在宁静的山林中回荡，也惊动了那个最不该被惊动的人。"
                },
                {
                    "角色": "师兄甲",
                    "内容": "神乎其技！真是神乎其技！"
                },
                {
                    "角色": "师兄乙",
                    "内容": "好猴子！当真学到了真本事！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "好一个热闹的戏班子。你们……在为什么喝彩？"
                },
                {
                    "角色": "旁白",
                    "内容": "声音平淡，却如寒冰冻结了空气。须菩提祖师不知何时已站在众人身后，面无表情。所有的喧哗戛然而止，师兄弟们瞬间噤若寒蝉，纷纷退散，只留下那棵突兀的松树。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "悟空，还要我请你现出原形吗？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……弟子知错了。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你错在哪里？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不该……不该在人前卖弄神通。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "卖弄？我传你躲避三灾之法，是让你藏身、保命，不是让你拿来换几声廉价的叫好！你把大道当成了什么？街头杂耍的把戏？"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不敢……"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你敢得很！你渴望被看见，享受被吹捧，这便是你的心魔，是改不掉的妖性！别人看见的是一棵松树，我看见的，是你亲手为自己立下的墓碑！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父！弟子再也不敢了！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "没有下次了。记住我的话，神通显露之日，便是灾祸上门之时。今日你为了一声喝彩变棵松树，他日，你就会为了一个虚名，去捅破这天！你这孽畜，与我无缘了。"
                }
            ]
        },
        {
            "场景": 10,
            "场景剧本": [
                {
                    "角色": "旁白",
                    "内容": "松树变回了猴王，喧闹的喝彩声却在祖师冰冷的目光下凝结成一片死寂。悟空脸上的得意还未褪去，就已被一种不祥的预感攫住，他跪倒在地，声音里带着不解与抗辩。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父，弟子知错。可……炫耀神通，罪至于此吗？您传我大道，不就是为了让我脱胎换骨，不再是那个蒙昧石猴吗？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "我渡你，是让你看清自己，不是让你成为众人的幻影。你渴求的不是大道，是喝彩。那喝彩声，就是催你走向毁灭的丧钟。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "喝彩又如何？难道身怀利器，就该藏于鞘中，直至锈蚀？难道这通天的本事，就只配在无人处孤芳自赏？这是什么道理！"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "道理？你这猢狲，什么时候问过道理？你只问‘能不能’，从不问‘该不该’。我教你七十二变，是让你躲避三灾，你却拿来变成一棵松树取乐。我错了，我错在以为能将一把绝世凶器，磨成一尊护法神像。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "弟子不明白……我究竟做错了什么，要您说出如此绝情的话？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你没错。是你的天性没错。你的心太大了，大到这方寸山容不下，这清规戒律缚不住。它只容得下四个字——齐天大圣。"
                },
                {
                    "角色": "旁白",
                    "内容": "“齐天大圣”。四个字，如同一道惊雷，劈开了时空的迷雾，让祖师瞥见了未来的血海与烽烟。而此刻的悟空，只能感到这四个字滚烫的重量，却无法洞悉其中蕴含的，究竟是荣耀，还是宿命的枷锁。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "你此去，定生祸端。记住，不许对任何人说，你是我的徒弟。我教不了你收敛心性，只能教你如何独自面对。这，是我能给你的最后一课。"
                },
                {
                    "角色": "孙悟空",
                    "内容": "师父……若我此去，再不见您。那我这一身本事，究竟算什么？"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "是你自己的造化，也是你自己的罪业。与我无关。还有，你若对任何人泄露此地，哪怕只说出半个字，我便将你这猢狲神魂贬入九幽，叫你万劫不得翻身！"
                },
                {
                    "角色": "孙悟空",
                    "内容": "……弟子明白了。从此，世上再无师承。这一身本事，是我孙悟空，天生就会的。"
                },
                {
                    "角色": "须菩提祖师",
                    "内容": "去吧。"
                },
                {
                    "角色": "旁白",
                    "内容": "他磕了最后一个头，再无言语。一个筋斗，翻出了十万八千里，也翻出了此生的师徒缘分。身后，是再也回不去的斜月三星洞；眼前，是阔别二十年的花果山。他学成了长生，却被逐出了道法之门；他炼就了通天本领，却成了天地间最孤独的一个。那个寻仙问道的美猴王走了，此刻归来的，是孙悟空。"
                }
            ]
        }
    ]
}
    refine_script = remove_parentheses_in_script(refine_script)  # 去除语气标注等
    refine_script = normalize_script_characters(refine_script, character_list)
    print(refine_script)
    #tmp_script = json.dumps(refine_script, indent=2, ensure_ascii=False)
    #Final_Proofreader(tmp_script)

    # TODO 过渡
    #tmp_script = json.dumps(refine_script, indent=2, ensure_ascii=False)
    # trans = Transition_Generation(ori,tmp_script)
    # trans = Script_Transition_Generation(ori,tmp_script)
    # print(trans)
    # trans = {'场景过渡': [{'场景': 1, '过渡语句': '凌霄殿上的轻描淡写，并未阻碍花果山中生命力的野蛮生长。岁月流转，那只天生地养的石猴，早已将一身灵气化作了山林间的无尽顽劣。'}, {'场景': 2, '过渡语句': '王座初登，万猴朝拜，这看似圆满的开端，却在他心中投下了一道前所未有的阴影——权柄与领地，是否真能抵御那无形中悄然流逝的时光？'}, {'场景': 3, '过渡语句': '花果山的欢宴犹在耳畔，求道的孤舟已载着他驶向未知的尘世。他告别了山林的纯粹，一头扎进了名为‘人间’的巨大迷局，试图在这片追名逐利的浊流中，打捞出一线长生的微光。'}, {'场景': 4, '过渡语句': '南赡部洲的九年红尘，终究只是一场格格不入的幻梦。他再次登筏，将人间的喧嚣与虚妄抛在身后，任凭西海的风浪将他带向一片更为古老、也更接近‘道’的土地。'}, {'场景': 5, '过渡语句': '樵夫的指引，如同一道破开迷雾的符咒。他沿着那条通往‘心’的小径，穿过七里山路，终于在斜月三星的洞府前停下了脚步。洞门紧闭，万籁俱寂，仿佛隔绝了尘世的一切纷扰，只为等待一个叩门求道之人。'}, {'场景': 6, '过渡语句': '名姓一定，尘缘便了。七年时光在晨钟暮鼓间悄然流逝，扫地、应对、进退、礼仪……他学尽了仙家弟子的一切规矩，唯独那颗寻访长生的初心，在日复一日的等待中，愈发焦灼。'}, {'场景': 7, '过渡语句': '师兄弟们的斥责，于他不过是耳边清风。因为在那三下戒尺的敲击声中，他已听到了通往长生之门的唯一回响。此刻，他只需静待夜色降临，去赴一场独属于他的、关乎生死的约会。'}, {'场景': 8, '过渡语句': '长生之诀已入心海，从此，白日的寻常应对成了他最好的伪装，而每一个寂静的夜晚，都化作他参悟玄机的道场。如此又过了三年，那颗脱胎于顽石的道心，终于在秘法浇灌下，结出了初步的果实。'}, {'场景': 9, '过渡语句': '逐客之令，如晴天霹雳，将他所有关于师门的归属感击得粉碎。而这一切的缘起，不过是那个夏日午后，松荫之下，一场按捺不住的少年意气。'}, {'场景': 10, '过渡语句': ''}]}
    # trans= {'剧本':[]}
    # for index,script in enumerate(refine_script['剧本']):
    #     if index == len(refine_script['剧本'])-1:
    #         break
    #     tmp_script1 = json.dumps(script, indent=4, ensure_ascii=False)
    #     tmp_script2 = json.dumps(refine_script['剧本'][index+1], indent=4, ensure_ascii=False)
    #     tmp_script = tmp_script1+',\n'+tmp_script2
    #     result = Script_Transition_Generation(ori,tmp_script)
    #     trans['剧本'].extend(result['修改后的剧本'])
    #     if index == 0:
    #         continue
    #     else:
    #         trans['剧本'].pop(-2)
    # print(trans)
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
    # print(Emotion)
    Emotion = {
    "语气标注": [
        {
            "场景": 1,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "语速平稳，音调深沉。用讲述古老神话的史诗感和宿命感开场，营造宇宙的宏大与苍凉。说到“金光竟如利剑般刺破云霄”时，语调微扬，带出一丝惊奇和戏剧性的张力，为天庭的反应做铺垫。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "语气急切但受控，体现其作为“工具”的高效与忠诚。声音清晰有力，重点在“妖光冲撞”和“秩序微乱”上，表达出事态的严重性，但没有个人情绪的恐慌。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "语气沉稳而威严，带着被打断议程的轻微不悦。语速稍慢，每个字都带着不容置疑的权威感。重点在“惊慌”和“法度”上，是上级对下属失态的轻微斥责，而非对事件本身的担忧。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "语气恭敬，条理清晰地汇报。在描述“金光”、“破云而出”、“仙气激荡”时，语调中要带上一种亲眼目睹奇观的凝重感，向玉帝证明此事非同寻常，自己的“惊慌”事出有因。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "声音清晰敏锐，作为补充报告，印证同伴的观察。语气同样恭敬而严肃，重点在“风雷之声”、“山崩石裂”，用听觉的细节来佐证事件的惊人声势，强调其并非幻象。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "语气果断，不容置疑的命令。语调略微提高，语速加快，展现出作为最高统治者处理“异常”时的绝对控制力。“立刻”和“查明”要发得短促有力，不带情绪，只是启动一个程序。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "简短、有力、果决。没有任何犹豫，是绝对服从和高效执行力的声音体现。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "语速放缓，声音平稳客观，营造出一种时间凝滞、气氛森严的紧张感。描述二将神通时，带一丝旁观者的惊叹，突出天庭的效率。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "恢复平稳的汇报语气，声音清晰，不带感情色彩，客观陈述调查结果，像在宣读一份档案。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "语气同样客观冷静，作为补充，点明金光的来源，将整个事件的起因逻辑闭环。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "语速变慢，语调中充满难以置信和一丝荒谬的讥讽。重音落在“石头里蹦出来的猢狲”上，带着一种看透万物的、居高临下的轻蔑。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "声线略带迟疑，先是确认这个听起来荒谬的答案（“正是”）。随即迅速转为严肃，补充说明“天地精华”，试图用专业的术语来解释现象的合理性，挽回事件的严肃性。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "以一声轻蔑的冷笑“呵”开头。接下来的话语调平稳，却带着居高临下的说教感和彻底的漠然，仿佛在阐述一个不证自明的宇宙真理。将石猴比作“渣滓”和“蜉蝣”，语气极度轻描淡写，体现出对这种“意外”的司空见惯和绝对自信。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "声音冷静、客观，像是在剖析一个冷酷的权力法则。语调平直，不带感情色彩，以一种抽离的视角，揭示天庭权力运作的冰冷本质，为玉帝接下来的决定提供注解。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "恢复了作为统治者的威严，但语调中充满了处理琐事的倦怠和不耐烦。将石猴定义为“山野顽石”，是对此事最终的、不容置喙的裁定。最后的“散了吧”三个字，说得轻缓而随意，仿佛挥走一只苍蝇，彻底将此事从议程中抹去，尽显其神性的傲慢与漠然。"
                }
            ]
        },
        {
            "场景": 2,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "讲述者口吻，语速平稳。前半句带一丝田园牧歌式的悠然，后半句随着“酷暑”出现，转为沉重和紧迫，为接下来的戏剧冲突铺垫。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "年长者的审慎与敬畏。声音苍老，语调低沉，带着对自然伟力的无奈和宿命感。仿佛在陈述一个不可逾越的真理，也隐隐带着对猴群未来的担忧。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "年轻、充满野心和挑战欲。对“终点”一词带着轻微的嗤笑和不屑。语气坚定、锐利，充满对未知的渴望和领袖般的洞察力，最后一句语调稍缓，流露出对“家”的深切渴望，使其动机更具说服力。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "长者的说教与被冒犯的冷哼。开头的“哼”短促有力，充满不悦。“天真的石猴”带着一丝居高临下的嘲讽和惋惜。整段话是理性的、基于过往经验的警告，语重心长但缺乏变通。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "压抑的怒火和存在主义式的反抗。对“顺应”的反问充满力量，语调上扬。列举死亡时，语速加快，情绪层层递进。最后一句“你们不敢，我敢”语速放慢，声音压低，不是单纯的叫嚣，而是对自己本质的深刻断言，冷静而决绝。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "被激怒后的将计就计。带有被挑衅后的怒气和一丝狠辣的决断。语调变得尖锐、公开化，像是在众人面前立下不可更改的契约。说到“尊你为王”时，带有孤注一掷的意味，既是赌注，也是一种考验。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "超然物外的冷静和目标导向。对“王”这个头衔表现出不屑一顾的淡然。语气平静，显示出他所求的并非个人权位，而是族群的存续。这是一种更高级的领袖气质，沉稳且有担当。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "紧张感与史诗感并存。描述跳入瀑布时，节奏加快，充满动感。随后转为描绘水下的冲击感和压迫感。最后一句“豁然开朗”时，语调舒展，带给听众一种释放和豁然开朗的听觉感受。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "从震惊到狂喜的低语。初见的几句是气声，带着劫后余生的喘息和不敢置信的喃喃自语。随着发现的深入，声音逐渐由虚转实，充满了发现新大陆的震撼与喜悦，仿佛在亲吻一件神迹。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "找到归宿的宿命感和自我加冕。念出石碑上的字时，语速放慢，庄重而神圣，仿佛在宣读神谕。最后一句“我就是这个人”，语气无比坚定，充满了天命所归的自信和力量，完成了从“石猴”到“王”的心理蜕变。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "戏剧性的转折。前半段描述猴群的绝望时，语调低沉、滞重。随着金光破开，语调瞬间提振，充满英雄归来的画面感和冲击力，“目光如炬”四个字要说得掷地有声。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "世界观被颠覆的震惊与急切。声音带着颤抖和沙哑，之前的威严荡然无存。问题问得非常急切，甚至有些语无伦次，充满了对未知的好奇与恐惧。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "宣告福音的领袖。声音洪亮、充满喜悦和安抚人心的力量。他没有夸耀自己的英勇，而是直接呈现了所有猴子最渴望的结果。语气中充满了对未来的承诺和希望，温暖而坚定。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "极具煽动性的号令。声音拔高，盖过想象中的瀑布轰鸣。这是成为“王”之后的第一道命令，充满了不容置疑的权威和感染力。每一个字都像锤子一样，砸向旧有的懦弱和彷徨，宣告新时代的来临。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "见证历史的旁观者。描述猴群的反应时，语调昂扬，充满激情。在描述通背猿猴时，语调转为复杂和意味深长，最后“俯下了身子”时，声音低沉下来，带着一种尘埃落定的庄重感。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "彻底的臣服与新生。声音里带着大彻大悟后的释然和由衷的敬佩。他坦然承认了自己的局限，语气诚恳。最后一句“拜见千岁大王！”声音洪亮，发自肺腑，完成了权力的交接，也代表旧时代智慧向新时代力量的低头。"
                }
            ]
        },
        {
            "场景": 3,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "语调平稳，略带一丝疏离的观察感，仿佛镜头缓缓推近。描述喧哗时语速正常，在描绘美猴王时语速放缓，用声音的质感营造出喧嚣与孤独的鲜明对比，为后续的情绪爆发铺垫。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "语调低沉，充满深刻的厌倦与顿悟后的悲凉。'三百多年'要说得缓慢而沉重，仿佛每个字都压着三百年的时光。后半句转为一种冰冷的自嘲和对周围麻木同伴的讽刺，不是激昂的控诉，而是看透一切后的、发自肺腑的低语。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "语气随场景变化，从之前的平稳转为略带悬念和凝重。语速放慢，营造出空气突然凝固的感觉，引导听众感受那份突如其来的尴尬和不解。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "语气转为尖锐的、带有挑衅意味的质问。'怎么不说话了？'带着一丝冷笑。模仿猴子们可能的想法时，语调变得轻佻、满不在乎，形成一种刻意的反差，以此来凸显他内心的痛苦和对这种“快活”哲学的极度鄙夷。'不是很好吗？'这句要说得像一个冰冷的反问。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "情绪彻底爆发，但不是失控的嘶吼，而是压抑已久的恐惧与愤怒的喷涌。'不好！'要说得斩钉截铁。描述老死猴子时，语速加快，声音里带着因回忆而产生的微颤，仿佛那冰冷的画面就在眼前。最后一句，声音提高，语调充满悲凉和绝望的控诉，是对所有同类、也是对自己命运的审判。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "语速再次放缓，语调变得深沉而富有洞察力。在寂静中，这一滴泪要被描述得极具分量。重点在于揭示情绪的本质——'不是悲哀，而是一种被欺骗了三百年的愤怒与恐惧'。语气要沉静而肯定，引导听众理解猴王内心更深层的动因。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "声音从之前的激动中沉淀下来，但更加冰冷、锐利。'好一个自由！可笑的自由！'充满了刻骨的讽刺，可以带上一点咬牙切齿的感觉。'阎王老子圈养的牲口'这句话要说得充满屈辱和不甘。结尾部分，语调里是彻底的、冰冷的醒悟，带着一种看透了宏大骗局的绝望。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "语气肃穆，营造出一种冰点般的氛围。'淬了冰'是关键词，整个语调都要有这种冷感。描述群猴的'恐惧'时，要强调这是他们'第一次'看到。在引出通背猿猴时，语调稍稍回暖，带上一丝神秘和期待，为新角色的出场铺垫。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "声音苍老，但不虚弱，充满了一种历经世事后的平和与通透。语速非常缓慢，一字一句都带着分量。语气是赞许的，但不是奉承，而是一种长者对后辈开悟的欣慰。'近乎于道了'要说得意味深长，仿佛点破天机。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "急切，充满了抓住救命稻草的渴望。之前所有的愤怒和绝望瞬间转化为恳求。'老人家'的称呼要充满敬意，'你一定有办法，对不对？'带着确认和催促，声音可以略微颤抖，表现出极度渴望的情绪。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "保持缓慢、沉稳的节奏，不被孙悟空的急切所影响。语气平淡，像是在陈述一个亘古不变的事实，这种从容与孙悟空的焦灼形成强烈对比，更显其智慧和高深莫测。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "语气更加急切，甚至有些命令的口吻，体现出他'猴王'的本性和急躁。'快说！'是脱口而出的，几乎没有思考。这句要短促有力。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "语调不变，依旧是古井无波的沉稳。但在念出'佛、仙、与神圣'时，每个词之间可以有微小的停顿，赋予这三个词神圣感和庄重感。声音里带着对这些存在的敬畏。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "问题简短直接，语气质朴，完全是一个求道者的姿态。没有了之前的王霸之气，只有纯粹的追问。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "语气依旧平和，但带有一丝禅意和玄机。'就在这尘世之中'给人以希望，但'只看缘法'又把主动权交了出去，话说得不透，留有余韵，引人深思。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "语调上扬，变得激昂、充满力量，像史诗的序章。'三道劈开混沌的闪电'要说得有画面感和冲击力。描述猴王眼中的'火焰'时，语气要充满赞叹和对这份生命力的肯定。'向命运宣战'是核心，要说得铿锵有力，奠定全剧的基调。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "声音洪亮，充满了重获新生的力量和无所畏惧的豪情。'好！'字要短促有力，充满喜悦。'明日我就出发'没有丝毫犹豫。最后一句，'我偏要看看，是我的决心硬，还是那阎王老子的笔硬！'充满了挑战和野性未驯的霸气，是对命运的正式宣战，语调高亢，充满决心。"
                }
            ]
        },
        {
            "场景": 4,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "（旁白）语速平稳，带有一种史诗般的沉重感和时间流逝的沧桑。讲述猴王九年的心路历程，情感基调是客观中带着一丝悲悯。结尾“猴心”二字，语调可略微上扬，强调其未被磨灭的本性。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "（内心独白）冷静、抽离的自述，带着深刻的洞察和一丝不易察觉的轻蔑。说到“腔调”时，可以带一点模仿的讽刺感。整体是压抑在人性皮囊下的野性在冷眼旁观。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "（内心独白）情绪递进，从冷静的鄙夷转为一种哲学层面的沉痛。语气中透露出对这种“活法”的彻底否定。“漫长而精致的腐烂”一句，语速放慢，带着一种近乎宣判的冷酷和悲哀。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "（内心独白）从自我怀疑的迷茫，迅速转为孤注一掷的坚定。“不”字要短促有力，是一个清晰的转折。后半句的语气重新燃起希望，笃定而决绝，充满了对未知彼岸的向往。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "（旁白）氛围由压抑转向开阔。语气变得明朗，带有期待感和宿命感，为即将到来的相遇铺垫。“这一次，他来对了”一句，语调肯定，仿佛是命运的旁注。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "（歌声）朴实、悠远、自得其乐的歌声，不追求技巧，而是传达一种与自然融为一体的宁静心境。声音清朗，回荡在山林间，有一种超然物外的感觉。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "（惊疑/自语）被歌声攫住心神，声音微弱，仿佛怕惊扰了什么。气息中带着长久寻觅后终于发现线索的震惊和不敢置信。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "（歌声）继续吟唱，未受打扰。语气依然平静、安然，仿佛歌词中的境界就是他生活的常态。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "（旁白）语气中带着一种“谜底揭晓”的激动和感慨，强调这一刻对猴王的决定性意义。语速可以稍快，推动情节，将猴王的急切心情外化。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "（急切/激动）压抑了十年的期盼在瞬间爆发，声音洪亮但因激动而略带颤抖。不是简单的呼喊，而是将全部希望寄托于此的呐喊，甚至带点哽咽。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "（受惊/朴实）被突然出现的猴王吓了一跳，但语气依然温和、谦逊。声音里带着乡野之人的淳朴和一点不知所措，真诚地否认。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "（急躁/多疑）希望被否定的瞬间，野性和不信任感立刻占据上风。语气质问，充满压迫感，声调变硬，显示出他绝不容许再次被欺骗的决心。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "（耐心/诚恳）面对质问，没有慌乱，而是不急不躁地解释。语气平和，像在安抚一个焦躁的陌生人，试图用最朴素的语言化解误会。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "（荒谬/质问）听到解释后，感到极度的不可思议和荒唐。语气中充满了尖锐的嘲讽和对这种“不求上进”的全然不解。“砍柴？”二字要拖长音，强调那种匪夷所思的感觉。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "（叹息/无奈）一声沉重的叹息，道尽了凡人的身不由己。语气平静，没有抱怨，只是在陈述一个无法改变的事实。声音里有生活的重压，但也有一种认命的坦然。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "（失望/痛心）价值观受到巨大冲击后的激烈反应。语气中混杂着愤怒、失望和一种“恨铁不成钢”的痛心。他不是在争论，而是在用自己的世界观审判对方的“短视”。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "（平静/坚定）面对宏大的质问，他的回答却无比踏实。语气不卑不亢，平静地阐述自己的局限和选择。最后一句“我够不着”要轻而坚定，充满了知天命的安然和力量。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "（沉默）这是被另一种截然不同却同样坚固的价值观击中后的沉默。需要用气息表达出内心的震动、思考和哑口无言的状态。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "（坦然/指引）没有因为刚才的争论而生气，语气恢复了之前的平和与友善。像一个普通乡人一样，热心地为问路者指明方向。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "（低语/神圣）轻声重复地名，仿佛在念诵神圣的咒语。声音里充满了敬畏和即将得道的虔诚，之前的焦躁和轻蔑已荡然无存。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "（旁白）语气变得深沉而富有哲理，为这段相遇做一个总结。点明猴王的顿悟，语调中带着一种智慧的启迪感。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "（郑重/诚恳）语气沉稳，带有一种前所未有的成熟和尊重。他不再是那个野性难驯的石猴，而是一个懂得了人情的求道者。这句话是一个庄重的承诺。"
                }
            ]
        },
        {
            "场景": 5,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "沉稳而富有画面感。语速稍缓，营造出孤寂、幽深且略带压迫感的氛围。声音中带着一丝神秘，引导听众进入猴王独自求索的内心与外部环境。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "自语，带着一种理性的、近乎冷酷的审视和不解。语调平直，情感克制，透露出对凡俗价值观的疏离感和一丝不易察觉的轻蔑。仿佛一个高维生物在观察低维生物的逻辑。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "前半句“真是……”带一声极轻的嗤笑，是对那种“凡人智慧”的怜悯式嘲讽。后半句“而我，是要踩在它的头上”语调陡然坚定，充满野心和不容置疑的决绝，是与其野性未驯的本能和目标导向的性格完全契合的宣言。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "语气决绝，如同对自己立下誓言。声音沉稳，每个字都带着重量，尤其在“皆为泡影”四个字上，可以感受到他背后那股对虚无和死亡的深层恐惧，以及由此产生的强大驱动力。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "客观冷静的叙述，但通过对“尖利”“盘结”“灼烧”“角力”等词的强调，传递出强烈的身体上的疲惫感和挣扎感。语速平稳，但节奏上可以模拟出攀登的艰难，为后续的情绪爆发做铺垫。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "压抑着喘息，声音中带着明显的疲惫和焦躁。前半句是咬着牙的自语，后半句“他莫不是在消遣我？”则是一种被愚弄后的恼怒和怀疑，带有一丝凶性，但又强行克制着。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "“不对”两个字要说得短促有力，是他聪慧天性下的快速自我纠正。随即转为冷静的内省和分析，语速放慢，带着思索的停顿。最后一句是向内的、严肃的质问，怀疑的对象从樵夫转向了这座山，甚至是“道”本身。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "语调低沉，营造出一种身心俱疲、孤立无援的氛围。通过声音描绘出风声的凄厉和环境的压迫感，最后一句“显得格外刺耳”要带有一种精神被反复折磨的烦躁感。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "声音嘶哑，充满极限状态下的迷茫和困惑。语速缓慢，像是从牙缝里挤出来的字句，每个词之间都有微小的停顿，体现出精神上的巨大压力。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "“等等”是一个顿悟的瞬间，语气由之前的疲惫困惑猛然转为清醒和专注。后面的话语速不快，但充满了恍然大悟的惊喜感，仿佛在黑暗中看到第一缕光，带着一丝不确定但又无比兴奋的探索意味。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "承接上一句的情绪，但更加确定和激动。语调上扬，节奏加快，像是在脑中迅速地将线索串联起来，声音中带着一种解开谜题的智性上的愉悦。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "“原来如此！”要说得酣畅淋漓，是彻底想通后的释然和惊叹。后半句的语气中充满了对这种“神仙手笔”的赞赏和敬畏，之前对樵夫的怀疑一扫而空，取而代之的是一种棋逢对手般的兴奋。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "笑声要发自内心，是智识突破后的狂喜，而非简单的开心。笑声中带着他的野性和不羁。“妙啊！”要充满赞叹。整句话的情感是通透、畅快，充满了对更高智慧的向往和认同。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "语调一扫之前的沉重，变得轻快、昂扬。语速加快，与角色的心境和行动同步，传递出一种拨云见日、豁然开朗的解放感。声音里要有光。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "带着一点急促的喘息，但这是兴奋的喘息，而非疲惫。声音里充满了压抑不住的激动和百分之百的肯定，目标就在眼前的渴望和喜悦喷薄而出。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "语调庄重、肃穆，语速放缓。声音要沉稳有力，描绘出石碑历经岁月的沧桑感和文字中蕴含的无上威严，营造出一种神圣而不可侵犯的强大气场。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "前半句是低声的、带着敬畏的确认，仿佛在与心中的答案进行最后的印证。稍作停顿后，“我，孙悟空，找到了！”的情感要猛然爆发，这不是简单的呐喊，而是混杂着长途跋涉的艰辛、得偿所愿的狂喜、以及对自己身份和命运的确认，声音可以带一丝激动的颤抖。"
                }
            ]
        },
        {
            "场景": 6,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "平静中带着一丝被打扰的质询，语调清冷，恪尽职守，不带个人情绪。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "急切但努力压抑着，充满希望和敬畏。声音里带着长途跋涉后的风尘和见到希望的微颤。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "平铺直叙，略带一丝超然的好奇。仿佛在确认一件早已预知的事情，语气沉静，没有波澜。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "喜出望外，毫不掩饰的激动和确认，声音瞬间明亮起来。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "淡然，引路人的姿态，语调平稳无变化。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "旁白：语速平缓，营造出庄严肃穆、深远空旷的氛围。描述叩首时，声音可略微加重，强调猴王此刻的虔诚与渺小。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "威严，洞悉一切，带着审视的意味。声音沉稳而有穿透力，语调平缓却自带压力，称其为“妖物”是刻意的试探，语气中不带贬损，而是近乎冷酷的客观。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "恳切，急于辩解又满怀赤诚。语速稍快，带着激动的情绪，但努力保持着对师父的恭敬。提到“长生不老”时，充满了对死亡的恐惧和对希望的渴望。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "严厉，带着不容置疑的驳斥。语气陡然转冷，像是高高在上的智者对谎言的蔑视，实则是进一步的施压与考验。每个字都清晰有力，不怒自威。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "悲怆而决绝，声音因激动而颤抖。这是将内心最深处的痛苦和执念剖白出来，语调中充满着回忆的苦涩、与虚无对抗的疲惫，以及不容置疑的真诚。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "语气由严厉转为探寻，带着一丝高深莫测的兴趣。“哦？”字可拖长，表示考验通过，开始真正的好奇。问题看似平淡，实则直指其存在的根源。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "迟疑，坦诚中带着一丝无根的脆弱。说到自己的来历，声音不自觉地放轻，仿佛在诉说一个连自己都觉得奇异的秘密。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "了然于心，带着一丝悲悯和最终的接纳。语调转为温和，仿佛一切尘埃落定。“也罢”二字，有种超然的宽容。话语间是从容不迫的赐予和决定。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "难以置信的狂喜，声音哽咽，激动得有些语无伦次。从巨大的压力中瞬间解脱，充满了劫后余生的感激。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "如智者讲经，语调平稳，充满哲理和仪式感。在拆解字义时，不疾不徐，仿佛在进行一场神圣的命名仪式，每个字都蕴含着深刻的道理和期望。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "喃喃自语，充满了初获身份的迷惘和珍重。反复念着“姓孙”，是从懵懂到了然，再到内心被巨大喜悦充满的过程。最后一句“不再是那石猴了”是如释重负的轻语。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "旁白：语调深沉而富有哲思，带着共情。为听众解读这份“归属感”的重量，声音温暖而有力，强调“根”、“新生”、“颤栗”等词，引发听众对存在意义的思考。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "庄重，赐予法名。语气平淡却有分量，如同在宣布一件影响深远的大事，不容置疑。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "缓慢，带着咀嚼和思索的意味。将三个字分开念，充满了对“空”字的好奇与不解，是发自内心的疑问。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "一语道破天机，带着洞穿一切的智慧。语气平静，却如洪钟大吕，直击悟空内心最深的恐惧。最后的“可悟了？”语调放轻，却蕴含着千钧之力，是点化，也是叩问。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "旁白：语调上扬，带着一种豁然开朗的通透感。将悟空的过去与“空”字相连，声音中应有宿命感和史诗感。最后一句“而是孙悟空”，语调坚定，充满力量，宣告一个全新生命体的诞生。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "从顿悟的狂喜到虔诚的叩拜。第一句“悟了”是醍醐灌顶的呐喊，笑声是发自内心的解脱与喜悦。喊出自己名字时充满自豪和力量，最后一句“拜见师父”则回归了弟子的身份，真诚而坚定。"
                }
            ]
        },
        {
            "场景": 7,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "庄重沉稳，带着智者洞察一切的平静。说“七年了”时，语调略沉，有时间的厚重感。提问时，语气平淡但有穿透力，仿佛是在开启一场早已预知的、至关重要的仪式。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "坚定恳切，不卑不亢。说“不求”时果断，表明早已想通。在“只求一个长生不死的法门”上，语速放慢，字句清晰，充满压抑已久的渴望和决心，这是他唯一的执念。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "带一丝考究和轻微的玩味。说“好个…”时，像是在审视一件璞玉，既有欣赏也有考验。介绍“旁门”时，语气平淡如念清单，最后的“能长生否？”语调略扬，是明知故问的钩子。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "果决，毫不犹豫，带着看穿本质的通透。反问时有轻微的不屑，但并非无礼。“不学！”二字短促有力，斩钉截铁。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "波澜不惊，保持着古井无波的平静。继续以同样的平淡语气介绍下一个选项，用这种不变来施加压力，考验悟空的耐心和心性。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "比之前更显不耐，但仍克制在尊敬的范围内。用“画中之饼”的比喻时，带着一丝对虚浮理论的轻蔑。“不学！”依旧坚决。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "语气依旧平稳，仿佛对悟空的拒绝无动于衷。这种重复的、毫无情绪的试探，本身就是一种高深的禅机和考验。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "失望和鄙夷感加重。“苟延残喘”四字要说出极度的不屑，反问句中蕴含着对生命意义的深刻诘问，而不仅仅是求生。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "语气依旧平淡，但这是暴风雨前的最后平静。可以想象他内心已有定论，这只是走完最后一道程序，为接下来的“表演”做铺垫。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "彻底的醒悟和决绝。说“水中之月，镜中之花”时，带有一种对虚妄法门的诗意否定。“捞不得，也摘不下！”是充满力量的结论。最后的“不学！”是盖棺定论，再无转圜余地。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "旁白：语速平稳，但声音略沉，渲染出山雨欲来的紧张感。“彻底”二字可稍作强调，暗示事态升级，气氛凝固。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "压抑的怒火，是师长恨铁不成钢式的威严喝斥，一场演给所有人的戏。声音有爆发力但收放自如，每个字都清晰有力，看似盛怒，实则每一个词都在掌控之中。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "旁白：语速从容，富有节奏感和画面感。强调动作的精准，“不偏不倚，不轻不重”，暗示其中另有玄机。“敲了三下”是重音。“砰然”二字要有力度，最后一句则描绘出静止的惊愕画面。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "旁白：语速稍快，营造众人惊扰、嘈杂的氛围。用一种抽离、冷峻的语调描述他们的惊惧、鄙夷与嘲笑，最后一句“就像看一个…废物”语调转为冰冷的陈述，凸显悟空被孤立的处境。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "极轻声的，压抑着巨大喜悦的内心独白。声音里是劫后余生般的释然，和领悟天机后的狂喜与感激。这句是风暴中心的宁静，要与周围的嘈杂形成鲜明对比。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "旁白：语气中带着一丝洞悉全局的了然和淡淡的讽刺。“他竟在笑”要说出一种意料之外的惊奇感，而后半段描述众人反应时，语调可以更轻，像在讲述一件无关紧要的趣闻。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "旁白：语速放缓，回归平静、清晰的解谜感。逐一揭示谜底时，节奏分明，笃定而有力。最后一句“是师父单独为他设下的考题”要带有尘埃落定的总结意味，以及一丝对这对师徒心意相通的欣赏。"
                }
            ]
        },
        {
            "场景": 8,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "旁白。沉静、神秘，带有宿命感。语速平稳，如同在讲述一个古老而沉重的秘密，为深夜密会奠定庄重而压抑的基调。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "平静，意料之中。仿佛不是在提问，而是在陈述一个既定事实。声音低沉，不带任何情绪波澜，体现出洞悉一切的智慧。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "恭敬，压抑着内心的急切与忐忑。语速稍快，声音放低，既是尊敬，也怕惊扰了这份来之不易的机会。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "严肃，带着审视与警告。语气平铺直叙，但每个字都充满分量，尤其在“与天地为敌的契约”上加重，像是在宣告一桩不可逆转的交易的残酷条款。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "决绝，甚至带有一丝悲壮。声音坚定，充满力量，将十数年的孤注一掷和存在主义的焦虑感融入其中。这不是冲动，而是深思熟虑后的宣言。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "冷酷的赞许。对悟空的决绝给予肯定，但语气依旧冰冷，如同在阐述一条冰冷的宇宙法则。话语重心落在“交换”和“枷锁”上，最后一句命令式的“近前来”，带着不容置疑的威严。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "虔诚，全神贯注。声音压得更低，充满了即将接受神启般的郑重，气息平稳，显示出内心的专注。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "低沉的秘语。如同古老的咒文，语速缓慢，节奏分明，不带感情色彩，但每个字都清晰有力，仿佛直接刻入听者的灵魂。声音里带着非人间的神秘感。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "旁白。语调一转，从神秘转向凌厉。前段描述悟空的变化，声音沉稳；后段描述祖师的目光，语调变得尖锐、冰冷，营造出山雨欲来的紧张感。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "冷峻，不容置疑。一声呼唤，如同利剑出鞘，打破了讲法的平和氛围，带着审判般的严厉。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "沉稳，平静。与三年前的忐忑不同，此时的声音充满底气，简短的回答中透出根基已固的自信。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "审视，略带讽刺。问题看似平常，实则暗藏机锋，语气中带着一丝不易察觉的嘲弄，仿佛在考验他的心性。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "自信而不自傲。回答得体，语气谦逊，但内在的底气和对“道”的信心无法掩饰。声音平稳，不卑不亢。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "严厉，带着残酷的现实感。彻底打破对方的幻想，语气变得尖锐而充满压迫感。“错！”字短促有力，后面的话如同冰水浇头，特别是“贼”字，充满了鄙夷和警告。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "震惊，难以置信。长久以来的信念被颠覆，声音中带着一丝颤抖和急切的辩解，充满困惑。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "旁白。配合描述，声音中应带有一丝寒意，描绘出那声冷笑的“嘲弄与怜悯”，让听众切身感受到其中的冰冷。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "揭示真相的冷酷。语气变得更加严峻，像是在宣读一份天道的判决书。“逆天而行”四字掷地有声，提及“雷灾”时，语调加重，充满了宿命的沉重感。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "本能的恐惧。第一次显露出真正的惊慌，声音发紧，问题问得短促，暴露出内心深处的求生欲。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "轻蔑，不屑。对悟空的天真嗤之以鼻，语气中的轻视感毫不掩饰。描述灾难时，语调平直，仿佛在陈述一件微不足道但又无可避免的琐事。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "挣扎的自负。试图用自己已有的认知来对抗未知的恐惧，语气中带着一丝强撑的骄傲，但底气已明显不足。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "残忍的教诲。用一种近乎享受的、冰冷的语调，详细描绘“阴火”的恐怖，最后一句“一把好柴”带着极致的嘲讽，将悟空的千年修行贬低到尘埃里。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "濒临崩溃的绝望。声音虚弱，沙哑，几乎是气音。在巨大的恐惧面前，只剩下最无力的疑问。"
                },
                {
                    "台词位置": 22,
                    "语气指导": "不带感情的宣判。以一种毫无波澜的语调，陈述第三重灾难，这种平静反而比咆哮更令人恐惧。最后的反问，语调微微上扬，带着一种冷漠的、看透一切的质问。"
                },
                {
                    "台词位置": 23,
                    "语气指导": "旁白。语调充满同情下的冷峻，既描述悟空的内心崩塌，也揭示这残酷真相的本质。声音中带着对这种“精心设计的漫长处决”的敬畏与悲哀。"
                },
                {
                    "台词位置": 24,
                    "语气指导": "被背叛的愤怒质问。压抑不住的咆哮，声音中充满了被欺骗的痛苦和绝望，不是求饶，而是对师父、对命运发出的控诉。"
                },
                {
                    "台词位置": 25,
                    "语气指导": "绝对的冷静与抽离。完全不受悟空情绪的影响，语气冰冷得像一块玄铁。他将一切归于悟空自己的选择，话语间带着一种“我只是规则的阐述者”的漠然。"
                },
                {
                    "台词位置": 26,
                    "语气指导": "彻底的屈服与哀求。所有的骄傲和愤怒都被求生欲击垮，声音嘶哑，充满了最原始的、毫无尊严的乞求。"
                },
                {
                    "台词位置": 27,
                    "语气指导": "刻意的羞辱与刺激。用最轻蔑、最伤人的言语进行人格上的打击，语气中充满了鄙夷，仿佛在看一件不值一提的玩物，以此来试探其最后的底线。"
                },
                {
                    "台词位置": 28,
                    "语气指导": "触底反弹的冲天之怒。从被羞辱的低吼开始，声音逐渐拔高，充满了不屈的野性和对不公天道的极致蔑视。这不是求饶，而是以自身存在为赌注的宣战。"
                },
                {
                    "台词位置": 29,
                    "语气指导": "隐晦的赞许与最终的考验。一声“好”，低沉而有力，是对他狠劲的认可。随即语气恢复平静，用一种交易般的口吻给出选择，将顺从与反抗两条路清晰地摆在面前。"
                },
                {
                    "台词位置": 30,
                    "语气指导": "毫不犹豫的抉择。声音果断、坚定，充满了逆天而行的决心。这是他本性的呐喊，也是他命运的宣言。"
                },
                {
                    "台词位置": 31,
                    "语气指导": "旁白。语调变得深邃，捕捉到祖师那稍纵即逝的赞许，随后压低声音，营造出一种更加隐秘、更加危险的氛围。"
                },
                {
                    "台词位置": 32,
                    "语气指导": "最终的密传。声音压成一道几乎听不见的耳语，充满了警告和诅咒的意味。这不是恩赐，而是递给他一把双刃剑，语气中混合着传道的责任和对未来的冷酷预见。"
                }
            ]
        },
        {
            "场景": 9,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "旁白：语速平缓，沉静中带着一丝山雨欲来的预兆。描述午后景象时是客观的，但提及“嫉妒与挑衅”时，语调可略微压低，暗示平静下的暗流。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "师兄甲：皮笑肉不笑，语气里带着酸味。看似是请教，实则是质问和试探，每个字都像包裹着糖衣的针，带着刺探的意味。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "孙悟空：谦逊而疏离。他洞悉对方的意图，因此用一种四两拨千斤的客气来回应，刻意放低姿态，语气平和，试图化解对方的敌意。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "师兄乙：轻蔑的嗤笑，语调上扬，充满不屑和怀疑。后半句的“莫不是…”带着明显的激将法，试图用羞辱来逼他就范。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "师兄甲：站在道德高地上进行人格攻击。语气变得冠冕堂皇，充满“说教”感，但底层的挑衅意味更浓，尤其是“怕了？”二字，要说得又轻又重，直刺内心。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "孙悟空：克制而坚定。这是他最后的防线，搬出师父作为挡箭牌。语气比之前要硬，但仍保持着表面的平静，能听出压抑着的不耐烦。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "师兄乙：洋洋得意，抓住了话柄。语气轻浮，带着胜利者的姿态，将悟空的原则曲解为“无能”，最后用“自家兄弟”来道德绑架，显得虚伪又煽动。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "旁白：语调一转，从外部的言语交锋转向悟空的内心。语气低沉而有力，带着一丝叹息，点明那份被点燃的、无法抑制的“妖性”与骄傲。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "孙悟空：压抑后的释放，带着一丝冷笑和骨子里的狂傲。语调从容不迫，甚至有些慵懒，仿佛接受挑战是件无所谓的小事，充满了对挑衅者的轻蔑。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "师兄甲：故作高深，提出一个看似刁钻的难题。语气中带着一丝考验的傲慢，仿佛自己是出题的考官。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "孙悟空：意气风发，充满了少年得志的张扬。声音洪亮，自信满满，享受成为众人焦点的时刻，带着一种“看我手段”的炫耀感。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "旁白：语速放缓，用一种充满画面感、略带敬畏的语调来描述这神奇的变化，仿佛亲眼见证一个奇迹的诞生。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "师兄甲：发自内心的惊骇，声音带着一丝颤抖和不敢置信，是纯粹的、被震撼到的表现。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "师兄乙：从震惊转为狂热的赞叹。语速加快，情绪激动，声音里充满了羡慕和拜服，最后的“天啊”是情绪的顶点。"
                },
                {
                    "台词位置": 14,
                    "语气指导": "孙悟空：（需要做一些后期效果，模拟从树干中发出的声音，带点混响和木质感）语气得意洋洋，充满了戏谑和满足感，享受着师兄弟们的顶礼膜拜。"
                },
                {
                    "台词位置": 15,
                    "语气指导": "旁白：前半句语调轻松，呼应现场的热烈气氛。到“也惊动了…”时，语调骤然冷却、压低，带来一种不祥的预感，仿佛欢乐乐章中一个刺耳的休止符。"
                },
                {
                    "台词位置": 16,
                    "语气指导": "师兄甲：发自肺腑的吹捧，语气夸张，充满了惊叹。"
                },
                {
                    "台词位置": 17,
                    "语气指导": "师兄乙：热络地称赞，带着几分讨好和亲近，与之前的挑衅判若两人。"
                },
                {
                    "台词位置": 18,
                    "语气指导": "须菩提祖师：平静得可怕。声音不大，但极具穿透力，不带任何情绪起伏，像一块寒冰，瞬间冻结全场。问句是反问，充满了不容置疑的威严。"
                },
                {
                    "台词位置": 19,
                    "语气指导": "旁白：语速变慢，语气紧张、凝重，描述一种绝对的寂静和恐惧，每一个字都透着寒气。"
                },
                {
                    "台词位置": 20,
                    "语气指导": "须菩提祖师：冷漠的命令。语气依旧平淡，但其中蕴含的压力令人窒息。这不是询问，而是最后的通牒。"
                },
                {
                    "台词位置": 21,
                    "语气指导": "孙悟空：（恢复原形）声音微弱，充满了恐惧和悔恨，带着明显的颤音，像一个做错了事的孩子面对严厉的家长。"
                },
                {
                    "台词位置": 22,
                    "语气指导": "须菩提祖师：冰冷的质询。语调没有丝毫变化，如同手术刀一般精准而冷酷，目的是剖开问题，而不是给予安慰。"
                },
                {
                    "台词位置": 23,
                    "语气指导": "孙悟空：囁嚅着回答，声音断断续续，充满了不确定和害怕，他只知道自己犯了戒，但尚未理解错误的根本。"
                },
                {
                    "台词位置": 24,
                    "语气指导": "须菩提祖师：失望透顶的怒火，但并非咆哮，而是压抑后的爆发。语调陡然严厉，字字千钧，充满了痛心疾首的斥责。“街头杂耍的把戏”几个字要说得极具分量，充满鄙夷。"
                },
                {
                    "台词位置": 25,
                    "语气指导": "孙悟空：被师父的怒火彻底击溃，声音只剩下本能的、微弱的辩解，气若游丝。"
                },
                {
                    "台词位置": 26,
                    "语气指导": "须菩提祖师：洞悉一切的冷酷。愤怒已经转化为一种深刻的、悲哀的断言。语气沉重，带着预言般的宿命感。“墓碑”二字要说得极其缓慢而清晰，直击人心。"
                },
                {
                    "台词位置": 27,
                    "语气指导": "孙悟空：绝望的哀求。声音嘶哑，带着哭腔，是发自内心的恐惧和乞求，想要抓住最后一根稻草。"
                },
                {
                    "台词位置": 28,
                    "语气指导": "须菩提祖师：彻底的决绝。所有的情绪都已收回，只剩下绝对的、不容转圜的冰冷。语气平淡如水，却比任何愤怒都更具毁灭性。说出“与我无缘了”时，就像在陈述一个与己无关的事实，彻底斩断了所有情分。"
                }
            ]
        },
        {
            "场景": 10,
            "场景剧本": [
                {
                    "台词位置": 0,
                    "语气指导": "语速平稳，基调沉重。前半句营造喧闹后的寂静，在“祖师冰冷的目光下”开始放慢语速，声音压低，传递气氛凝固的窒息感。后半句转向悟空的内心，带出他从得意到惊惧的戏剧性转变，为角色出场铺垫好情绪。"
                },
                {
                    "台词位置": 1,
                    "语气指导": "急切、困惑，并带着一丝本能的委屈和抗辩。开头的“弟子知错”是下意识的求饶，但紧接着的反问，底气回升，充满了不解和理直气壮。他此刻无法理解师父的怒火，认为自己只是展示所学，罪不至此。"
                },
                {
                    "台词位置": 2,
                    "语气指导": "冰冷、沉重，不带个人情绪的审判感。语速放慢，字字清晰，仿佛在阐述一个冷酷的真理。这不是愤怒的斥责，而是一种洞悉一切后的失望与警示。“丧钟”二字，要带着预言般的终极警告意味。"
                },
                {
                    "台词位置": 3,
                    "语气指导": "被误解后的愤懑和压抑不住的野性。情绪被激发，语速加快，声调提高。这是他天性的直接反抗，充满了对“锦衣夜行”式道理的挑战和不服。“这是什么道理！”带着被压抑后的爆发力，但并非失控的嘶吼。"
                },
                {
                    "台词位置": 4,
                    "语气指导": "压抑着怒火的痛心疾首。以一声充满讽刺的冷笑“道理？”开场。语气中交织着对牛弹琴的疲惫、深刻的失望和沉痛的自责。说到“我错了”时，语调转为低沉，充满了无力回天的决绝。"
                },
                {
                    "台词位置": 5,
                    "语气指导": "被最敬重的人用最重的话刺伤后的迷茫与痛苦。之前的气焰完全消失，声音颤抖，甚至可以带一丝不易察觉的哭腔。语速放缓，充满了无助感，像一个无法理解惩罚的孩童。"
                },
                {
                    "台词位置": 6,
                    "语气指导": "从个人情绪中抽离，转为一种陈述宿命的平静与深远。语调低沉、悠远，仿佛在揭示一个与自己无关但早已注定的未来。“你没错”三个字，带着卸下教导重担的叹息。最后念出“齐天大圣”时，一字一顿，极慢，每个字都灌注着洞悉未来的沉重分量。"
                },
                {
                    "台词位置": 7,
                    "语气指导": "宏大而充满宿命感的史诗旁白。配合“惊雷”二字，语调上扬，营造出命运被揭示的震撼感。随即转为低沉，描述悟空当下的茫然，将未来的“血海烽烟”与此刻的“滚烫重量”进行对比，突出悲剧的张力。"
                },
                {
                    "台词位置": 8,
                    "语气指导": "彻底的决绝与不容置疑的命令。语气恢复冰冷，像是在交待后事，不带任何情感温度。话语简洁、有力。“这，是我能给你的最后一课”，可带入一丝微不可察的、深埋的悲悯，但立刻被冷硬的表象覆盖。"
                },
                {
                    "台词位置": 9,
                    "语气指导": "近乎哀求的最后追问，充满了存在主义的迷惘。声音虚弱，带着颤音，失去了所有方向感。这不是在求情，而是在师徒缘分断绝的边缘，对自己一身本领的意义发出的、最根本的疑问。"
                },
                {
                    "台词位置": 10,
                    "语气指导": "冷酷到极点的切割，不留任何余地。声音压得极低，语调平直，毫无情感波动。“与我无关”四个字要轻而决绝。最后的威胁，语速放慢，每个字都像冰锥，带着不容置疑的威严和杀伐之气，彻底斩断悟空最后的念想。"
                },
                {
                    "台词位置": 11,
                    "语气指导": "心如死灰后的悲壮与傲气。在短暂的停顿和吸气后，声音变得低沉沙哑，是接受现实的麻木。但说到后半句“是我孙悟空，天生就会的”时，语调中重新燃起一丝倔强和傲骨，一种被逼上绝路的、悲剧性的自我确立。"
                },
                {
                    "台词位置": 12,
                    "语气指导": "轻声，但无比沉重。这两个字里包含了所有未说出口的叹息、不舍与无奈，但最终都化为这最后、最平静的两个音节。它代表着一个时代的彻底终结。"
                },
                {
                    "台词位置": 13,
                    "语气指导": "恢弘、悲凉，带着历史的沧桑感。语速平缓，如同一位站在时间长河尽头的讲述者。通过“学成”与“被逐”、“通天本领”与“最孤独的一个”的强烈对比，渲染出宿命的讽刺与悲剧性。最后一句“此刻归来的，是孙悟空”，语调变得坚定、有力，为这个传奇英雄的真正诞生，落下沉重的一笔。"
                }
            ]
        }
    ]
}

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
    #Role_Voice_Map(character_gemini, script_with_emotion)