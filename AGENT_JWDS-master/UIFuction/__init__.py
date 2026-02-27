import re
import os
import time
import json
from collections import defaultdict

import gradio as gr
import fitz
#import Prompt
from Prompt.Children import *
from Prompt import Adult, Teenager, Children

# 全局变量存储当前使用的Prompt模块
current_prompt_module = Children

"""
切换Prompt模块
"""
def switch_prompt_module(mode):
    global current_prompt_module
    mode_map = {
        "成年版": Adult,
        "青年版": Teenager,
        "儿童版": Children
    }
    current_prompt_module = mode_map.get(mode, Children)
    print(f"[INFO] Prompt模块已切换到: {mode} - {current_prompt_module.__name__}")
    return current_prompt_module

"""
重新格式化文本中的换行符：
- 将段落内的单个换行符替换为空格。
- 保留（或规范化为单个）段落间的多个换行符。
"""
def reformat_text_newlines(text):
    if not text:
        return ""
    # 1. 规范化所有类型的换行符为 \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 2. 将三个或更多连续的 \n 替换为两个 \n，以简化后续处理
    #    这样 \n\n, \n\n\n, \n\n\n\n 等都会变成 \n\n
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 3. 将双换行符 (段落分隔) 替换为特殊占位符
    paragraph_placeholder = "__PARAGRAPH_BREAK_PLACEHOLDER__"
    text_with_placeholders = text.replace('\n\n', paragraph_placeholder)
    # 4. 将剩余的单换行符 (段内换行) 替换为空格
    text_single_newlines_removed = text_with_placeholders.replace('\n', '')
    # 5. 将占位符替换回单个换行符 (作为段落分隔)
    final_text = text_single_newlines_removed.replace(paragraph_placeholder, '\n')

    return final_text

"""
输入:
- pdf_upload: 用户通过“上传文档”组件上传的文件对象。
输出:
- pdf_content_display: 更新“PDF内容显示区域”，显示从文件中提取的文本。
- process_status_display: 更新“处理状态显示”，反馈文件上传成功等状态信息。
- btn_generate: 激活“分析内容/重新分析”按钮，使其变为可点击。
- filename_state: 将上传的文件名存入一个不可见的状态组件，供后续步骤使用。
"""
def display_uploaded_file_content(file_obj):

    if file_obj is None:
        return "请先上传文件。", "请先上传文件。", gr.update(interactive=False)

    file_path = file_obj.name  # 这是上传后Gradio保存的临时文件路径
    file_name = os.path.basename(file_path)  # 获取原始文件名
    content = ""
    try:
        if file_path.lower().endswith(".txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            status_message = f"文件 '{file_name}' 解析成功。"
            return content, status_message, gr.update(interactive=True), file_name  # 返回内容和状态消息
        elif file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                content += page.get_text("text")
                content += "\n"
            content = reformat_text_newlines(content)  # 调用文本格式化函数
            status_message = f"文件 '{file_name}'  解析成功，共 {len(doc)} 页。"
            doc.close()
            return content, status_message, gr.update(interactive=True), file_name  # 返回内容和状态消息
        else:
            content = "错误：不支持的文件类型。请上传 PDF 或 TXT 文件。"
            status_message = "文件类型不支持。"
        if not content.strip():  # 如果提取内容为空
            content = "(文件内容为空或无法解析)"
            status_message = f"文件 '{file_name}' 内容为空或无法提取文本。"
        return content, status_message, gr.update(interactive=False), "error"  # 返回内容和状态消息

    except Exception as e:
        error_msg = f"解析文件 '{file_name}' 时出错: {str(e)}"
        print(error_msg)
        return "解析文件时发生错误，请检查文件格式或内容。", error_msg, gr.update(interactive=False), "error"


"""
    输出 (outputs):
    - pdf_content_display, process_status_display, storyline_content_display, character_content_display, generated_script_display:
      清空所有文本显示区域，并将其重置为初始的占位符或提示文本。
    - tts_audio_output:
      清除“生成的语音”播放器中任何已存在的音频。
    - btn_generate, btn_generate_script, btn_generate_voiceMatch, btn_generate_tts:
      禁用（设置为不可交互）所有主要的功能按钮。
    - Accordion_Storyline, Accordion_Role, Accordion_Script, Accordion_TTS:
      折叠所有分析结果相关的Accordion区块，恢复UI的初始布局。
"""
def clear_all_related_outputs():
    """
    当用户清除上传的文件时,重置所有相关的输出组件到其初始状态。
    """
    print("[INFO] File cleared by user, resetting outputs to their initial/default states.")

    reset_pdf_content = "请先上传并解析文件。"
    reset_process_status = "请先上传文件。"
    reset_storyline_content = "请先分析内容。"
    reset_character_content = "请先分析内容。"
    reset_generated_script = None
    reset_tts_audio = None
    return (
        reset_pdf_content,
        reset_process_status,
        reset_storyline_content,
        reset_character_content,
        reset_generated_script,
        reset_tts_audio,
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(open=False),
        gr.update(open=False),
        gr.update(open=False),
        gr.update(open=False),
        gr.update(interactive=True),  # 重新启用模式选择器
    )



"""
按钮：分析内容/重新分析
    输入 (inputs):
    - pdf_content_display: “PDF内容显示区域”中的文本内容，作为内容分析的源数据。

    输出 (outputs):
    - storyline_content_display: 更新“故事线内容显示区域”，展示分析出的故事线。
    - character_content_display: 更新“角色内容显示区域”，展示提取出的角色信息。
    - btn_generate_script: 激活“生成剧本”按钮，允许用户进行下一步操作。
    - Accordion_Storyline: 展开“故事主线 Section”以显示结果。
    - Accordion_Role: 展开“角色 Section”以显示结果。
    - process_status_display: 更新“处理状态显示”，反馈分析进度或完成信息。
    - storyline_json_state: 将分析出的故事线数据（通常为JSON格式）存入不可见的状态组件中。
    - character_json_state: 将分析出的角色信息数据（通常为JSON格式）存入不可见的状态组件中。
"""
def analyze_content_process(current_pdf_content):
    # 使用当前选中的Prompt模块
    # print("[INFO] Starting content analysis...")
    # try:
    #     analyzed_storyline = current_prompt_module.Extraction_Summary(current_pdf_content)
    #     analyzed_characters = current_prompt_module.Extraction_Characters(current_pdf_content)
    #     character_display_text = ""
    #     characters_list = analyzed_characters['全部角色']
    #     for i, character in enumerate(characters_list, 1):
    #         # 格式化角色基本信息
    #         name = character.get('规范化名称', '未知')
    #         aliases = character.get('别名', [])
    #         traits = character.get('性格特征', [])
    #         biography = character.get('人物生平', '')
    #
    #         # 构建显示文本
    #         character_display_text += f"{i}. {name}"
    #
    #         # 添加别名（如果有的话）
    #         if aliases:
    #             aliases_str = "、".join(aliases)
    #             character_display_text += f" ({aliases_str})"
    #
    #         # 添加性格特征
    #         if traits:
    #             traits_str = "、".join(traits[:3])  # 只显示前3个特征，避免太长
    #             character_display_text += f" | 性格：{traits_str}"
    #             if len(traits) > 3:
    #                 character_display_text += "等"
    #
    #         # 添加人物生平
    #         if biography:
    #             character_display_text += f" | 生平：{biography} "
    #         character_display_text += "\n"
    #
    #     print("[INFO] Content analysis finished.")
    #     # 分析成功后，解锁剧本生成按钮
    #     return (
    #         analyzed_storyline['章节核心概要'],
    #         character_display_text,
    #         gr.update(interactive=True),
    #         gr.update(open=True),
    #         gr.update(open=True),
    #         "内容分析成功。请继续生成剧本。",
    #         analyzed_storyline,
    #         analyzed_characters
    #     )
    # except Exception as e:
    #     error_msg = f"内容分析过程中发生错误: {str(e)}"
    #     print("[ERROR]", error_msg)
    #     return (
    #         "内容分析失败，请检查文件内容或重新分析。",
    #         {},
    #         gr.update(interactive=False),
    #         gr.update(open=False),
    #         gr.update(open=False),
    #         error_msg,
    #         None,
    #         None
    #     )
    # 测试
    # time.sleep(5)
    result = {"章节核心概要":"一个从魔法石头里蹦出来的小石猴，因为勇敢地找到了一个叫做“水帘洞”的神秘山洞，成为了猴子们的猴王。但是，他担心快乐的日子会结束，于是他离开家，去很远很远的地方寻找一位神奇的老师。老师给了他一个新名字叫“孙悟空”，并教会了他七十二变和翻筋斗云等很多厉害的魔法。最后，孙悟空学成本领，告别老师，开心地飞回了家乡花果山。","故事线框架":[{"场景":1,"情节节点":"在一座美丽的花果山上，一块魔法石头裂开，蹦出了一只石猴。他和许多小猴子一起玩耍。有一天，他们发现了一道大瀑布，大家都不敢进去。石猴非常勇敢，第一个跳了进去，发现瀑布后面藏着一个又大又漂亮的山洞，叫做“水帘洞”。因为他的勇敢，猴子们都推选他当大王。","核心冲突":"猴子们对瀑布后面的世界感到好奇又害怕，没有人敢去一探究竟。","关键转折":"石猴自告奋勇，第一个跳进瀑布，为大家发现了一个可以安全居住的完美新家。"},{"场景":2,"情节节点":"当了猴王后，石猴过得很开心，但他突然开始担心，怕有一天这种快乐的生活会结束。一只年纪大的猴子告诉他，世界上有会魔法的仙人，他们知道永远快乐的秘密。于是，猴王决定离开花果山，去寻找这位仙人，学习长生不老的本领。","核心冲突":"猴王意识到快乐的时光是有限的，他渴望找到一种方法能让快乐和冒险永远持续下去。","关键转折":"猴王下定决心，告别了他的猴子朋友们，独自一人踏上了寻找仙人的旅程。"},{"场景":3,"情节节点":"猴王坐着自己做的小木筏，漂洋过海，走了很多年。他遇到了一个正在砍柴的好心樵夫。樵夫告诉他，附近的山上就住着一位叫菩提祖师的神仙，并为他指明了方向。","核心冲突":"世界那么大，猴王不知道去哪里才能找到传说中的神仙。","关键转折":"遇到善良的樵夫，他不仅证实了神仙的存在，还给了猴王明确的地址，让猴王找到了希望。"},{"场景":4,"情节节点":"猴王找到了菩提祖师，并拜他为师。祖师给他取了一个新名字叫“孙悟空”。孙悟空非常聪明，领悟了祖师给他的一个秘密暗示（在他头上敲三下），在半夜得到了祖师的秘密教导，学会了七十二变等神奇的法术。","核心冲突":"孙悟空需要向祖师证明自己有足够的智慧和耐心，才能学到真正的魔法。","关键转折":"孙悟空成功解开了祖师的“谜题”，得到了在夜里单独学习最厉害法术的机会。"},{"场景":5,"情节节点":"孙悟空又学会了能一下飞很远的“筋斗云”。一天，他在师兄们面前炫耀，把自己变成了一棵松树，结果被祖师看到了。祖师告诉他，真正的本领不是用来炫耀的，他的学习已经结束，是时候回家了。祖师让他保证，永远不能告诉别人是谁教他的法术。孙悟空告别了大家，一个筋斗云就飞回了花果山。","核心冲突":"孙悟空因为忍不住炫耀自己的新本领，让祖师觉得他不适合再留下来继续学习。","关键转折":"祖师决定让孙悟空毕业回家，并让他带着一身本领去开始自己的冒险，这是一个成长的结束，也是新旅程的开始。"}]}
    result2 = {"全部角色":[{"规范化名称":"盘古","别名":[],"性别":"男","人物生平":"在很久很久以前，世界还是一片黑乎乎的时候，是盘古用一把巨大的斧头，一下子把天地分开了。清亮的东西变成了蓝天，重重的东西变成了大地。是他让我们的世界变得这么美丽。","性格特征":["强大","有创造力","勇敢","开天辟地"],"说话语气":"充满力量和智慧"},{"规范化名称":"玉皇大帝","别名":["玉帝"],"性别":"男","人物生平":"他是天上的大王，住在美丽的云朵宫殿里，关心着世界上发生的一切事情。当他发现石猴出生时，就派人去看看发生了什么。他知道石猴是天地间自然诞生的宝贝，所以并不觉得奇怪。","性格特征":["有权威","冷静","见多识广","有智慧"],"说话语气":"平静而有威严"},{"规范化名称":"千里眼","别名":[],"性别":"男","人物生平":"他是玉皇大帝的好帮手，有一双特别厉害的眼睛，可以看到非常非常远的地方发生的事情。玉皇大帝让他去看石猴，他很快就看清楚了情况并回来报告。","性格特征":["忠诚","服从命令","视力超群","认真负责"],"说话语气":"恭敬且清晰"},{"规范化名称":"顺风耳","别名":[],"性别":"男","人物生平":"他也是玉皇大帝的好帮手，有一双神奇的耳朵，可以听到很远地方的声音。他和千里眼一起合作，帮助玉皇大帝了解远方发生的事情。","性格特征":["忠诚","服从命令","听力灵敏","认真负责"],"说话语气":"恭敬且清晰"},{"规范化名称":"孙悟空","别名":["石猴","猴王","千岁大王","美猴王","猢狲"],"性别":"男","人物生平":"他是一只从花果山上的神奇石头里蹦出来的猴子。他非常勇敢，带领猴子们找到了“水帘洞”这个美丽的家，成为了猴王。为了学习长生不老的本领，他不怕困难，一个人划着木筏出海寻找神仙，最后拜了一位很厉害的老师，学会了七十二变和筋斗云。","性格特征":["勇敢","好奇心强","有追求","聪明","坚持不懈","有领导力"],"说话语气":"活泼、直接、对老师很尊敬"},{"规范化名称":"猴子们","别名":["群猴","小猴子们"],"性别":"男/女","人物生平":"他们是住在花果山的一群快乐的小猴子，是孙悟空最好的朋友和家人。他们每天一起玩耍，后来在孙悟空的带领下住进了水帘洞。他们非常尊敬和爱戴他们的猴王，是孙悟空最温暖的伙伴。","性格特征":["活泼","爱玩","团结","尊敬领袖","天真快乐"],"说话语气":"热闹、愉快、叽叽喳喳"},{"规范化名称":"老猿猴","别名":["一只会说话的猿猴"],"性别":"男","人物生平":"他是猴群里一只非常有智慧的老猴子。当猴王因为担心会变老而难过时，是他告诉猴王，世界上有可以长生不老的仙人，并且鼓励猴王去寻找他们，给了猴王很大的启发。","性格特征":["有智慧","见多识广","善于引导","考虑长远"],"说话语气":"充满智慧、沉稳"},{"规范化名称":"樵夫","别名":[],"性别":"男","人物生平":"孙悟空在寻找神仙的路上遇到的一个善良的人。他一边砍柴一边唱着神仙教给他的歌。他很孝顺，要照顾年迈的妈妈。他热情地为孙悟空指明了去神仙家的路，是一个乐于助人的好心人。","性格特征":["善良","孝顺","热心","朴实","乐于助人"],"说话语气":"谦虚、友好、朴实"},{"规范化名称":"菩提祖师","别名":["祖师","师父","须菩提祖师"],"性别":"男","人物生平":"他是一位住在“灵台方寸山”的法力高强的神仙老师。他看出了孙悟空的不平凡，给他取名“孙悟空”，并用独特的方式考验他，最后在半夜悄悄地教会了他长生不老的方法、七十二变和筋斗云。他是一位严格又充满智慧的好老师。","性格特征":["智慧高深","严格","善于教导","外冷内热","有远见"],"说话语气":"威严而充满智慧，有时会生气，但都是为了教导学生"},{"规范化名称":"仙童","别名":["道童"],"性别":"男","人物生平":"他是菩提祖师的小徒弟，负责开门迎接客人。是他在门口迎接了前来拜师的孙悟空，并把他带到了老师面前。他是一个很有礼貌的小神仙。","性格特征":["有礼貌","听从师命","友好","认真"],"说话语气":"友好且有礼貌"},{"规范化名称":"众师兄","别名":["众仙","众人","诸位师兄","诸位长者"],"性别":"男/女","人物生平":"他们是和孙悟空一起在菩提祖师门下学习的同学们。他们一起学习、生活。他们一开始觉得孙悟空很顽皮，但后来又对孙悟空学会的本领感到好奇和羡慕，是一群一起成长的伙伴。","性格特征":["好奇","遵守规矩","爱热闹","团结"],"说话语气":"正常交谈，有时会责备，有时会羡慕地笑"}]}

    # 创建适合页面显示的角色信息字符串
    character_display_text = ""
    characters_list = result2['全部角色']

    for i, character in enumerate(characters_list, 1):
        # 格式化角色基本信息
        name = character.get('规范化名称', '未知')
        aliases = character.get('别名', [])
        traits = character.get('性格特征', [])
        biography = character.get('人物生平', '')

        # 构建显示文本
        character_display_text += f"{i}. {name}"

        # 添加别名（如果有的话）
        if aliases:
            aliases_str = "、".join(aliases)
            character_display_text += f" ({aliases_str})"

        # 添加性格特征
        if traits:
            traits_str = "、".join(traits[:3])  # 只显示前3个特征，避免太长
            character_display_text += f" | 性格：{traits_str}"
            if len(traits) > 3:
                character_display_text += "等"

        # 添加人物生平
        if biography:
            character_display_text += f" | 生平：{biography} "
        character_display_text += "\n"


    return result['章节核心概要'], character_display_text, gr.update(interactive=True), gr.update(open=True), gr.update(
        open=True), "内容分析成功，请继续生成剧本。", result, result2
"""
   输入 (inputs):
   - pdf_content_display: “PDF内容显示区域”中的完整原文，提供剧本生成的详细上下文。
   - storyline_content_display: “故事线内容显示区域”的文本，作为生成剧本的核心大纲。
   - character_json_state: 存储有角色信息的不可见状态组件，用于在剧本中正确分配角色对话。

   输出 (outputs):
   - generated_script_display: 更新“剧本内容显示区域”，展示AI生成的对话式剧本。
   - btn_generate_voiceMatch: 激活“角色声音配对”按钮，解锁下一步工作流。
   - Accordion_Script: 展开“剧本 Section”以方便用户查看新生成的剧本。
   - process_status_display: 更新“处理状态显示”，反馈剧本生成完成的状态。
   - generated_script_json_state: 将生成的剧本数据（通常为JSON格式）存入不可见的状态组件，供后续TTS生成步骤使用。
"""
def generate_script_process(pdf_content, current_storyline, current_characters):
    # 使用当前选中的Prompt模块
    # print("[INFO] 改编大纲生成...")
    # script_structure_gemini = current_prompt_module.Script_Structure_Planning(pdf_content,current_storyline)
    #
    # character_list = [
    #     {
    #         "规范化名称": char.get("规范化名称", ""),
    #         "别名": char.get("别名", []),
    #         "性格特征": char.get("性格特征", [])
    #         # "说话语气": char.get("说话语气", "")
    #     }
    #     for char in current_characters.get("全部角色", [])
    # ]
    # character_list_str = json.dumps(character_list, indent=4, ensure_ascii=False)
    #
    # print("[INFO] 对白生成...")
    # # 对白生成
    # dialogue_gemini = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     result = current_prompt_module.Dialogue_Generation(pdf_content,character_list_str,tmp_structure)
    #     dialogue_gemini['剧本'].append(result)
    #
    # print("[INFO] 旁白生成...")
    # narration_gemini = {'剧本':[]}
    # for index,structure in enumerate(script_structure_gemini['改编大纲']):
    #     tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
    #     tmp_dialogue = dialogue_to_annotated_string_by_scene(dialogue_gemini['剧本'][index])
    #     result = current_prompt_module.Narration_Generation(pdf_content,tmp_structure,tmp_dialogue)
    #     narration_gemini['剧本'].append(result)
    #
    # print("[INFO] 合并剧本与旁白...")
    # pre_script_gemini = combine_dialogue_and_narration(dialogue_gemini, narration_gemini)
    #
    # print("[INFO] 剧本冲突增强...")
    # script_conflict_escalation_gemini = {'剧本':[]}
    # for index,script in enumerate(pre_script_gemini['剧本']):
    #     tmp_script_structure =json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #     tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
    #     tmp_script_escalation = current_prompt_module.Conflict_Escalation(tmp_script_structure, character_list_str,tmp_script)
    #     script_conflict_escalation_gemini['剧本'].append(tmp_script_escalation)
    #
    # print("[INFO] 开始迭代式剧本审查与修正...")
    # # 1. 初始化
    # MAX_ITERATIONS = 3
    # current_iteration = 0
    # # 使用 list() 来创建一个浅拷贝，防止修改原始数据
    # scripts_to_refine = list(script_conflict_escalation_gemini['剧本'])
    # num_scenes = len(scripts_to_refine)
    # # 创建一个状态列表，追踪每个场景是否已通过审查
    # # 初始状态下，所有场景都未通过
    # scene_pass_status = [False] * num_scenes
    #
    # # 2. 开始主循环，直到所有场景通过或达到最大迭代次数
    # while not all(scene_pass_status) and current_iteration < MAX_ITERATIONS:
    #     current_iteration += 1
    #     print(f"\n[INFO] --- 开始第 {current_iteration}/{MAX_ITERATIONS} 轮迭代 ---")
    #     # 3. 遍历每一个场景
    #     for index in range(num_scenes):
    #         # 如果当前场景已经通过，则跳过，不再进行审查和修改
    #         if scene_pass_status[index]:
    #             continue
    #
    #         print(f"[INFO] 正在审查场景 {index + 1}...")
    #
    #         # 准备审查所需的数据
    #         tmp_script_structure = json.dumps(script_structure_gemini['改编大纲'][index], indent=4, ensure_ascii=False)
    #         # 注意：这里我们使用 scripts_to_refine[index]，即当前最新版本的剧本
    #         tmp_script = json.dumps(scripts_to_refine[index], indent=4, ensure_ascii=False)
    #         # a. 剧本审查
    #         proofread_result = current_prompt_module.Proofreader(pdf_content, tmp_script_structure, tmp_script)
    #
    #         # b. 判断审查结果
    #         if proofread_result.get('审查结果', '').strip() == '通过':
    #             print(f"[SUCCESS] 场景 {index + 1} 在第 {current_iteration} 轮审查通过！")
    #             scene_pass_status[index] = True
    #         else:
    #             print(f"[WARN] 场景 {index + 1} 未通过，问题：{proofread_result.get('问题清单')}")
    #             print(f"[INFO] 正在修正场景 {index + 1}...")
    #
    #             # 准备修正所需的数据
    #             tmp_feedback = json.dumps(proofread_result, indent=4, ensure_ascii=False)
    #
    #             # c. 迭代修正
    #             revised_script = current_prompt_module.Script_Revision(pdf_content, tmp_script_structure, tmp_script,
    #                                                                    tmp_feedback)
    #
    #             # d. 更新剧本列表为修正后的版本
    #             scripts_to_refine[index] = revised_script
    #             print(f"[INFO] 场景 {index + 1} 已修正。")
    #
    # # 4. 循环结束后的最终处理
    # print("\n[INFO] 迭代修正流程结束。")
    #
    # # 检查结束原因
    # if all(scene_pass_status):
    #     print("[SUCCESS] 所有场景均已通过审查！")
    # else:
    #     failed_scenes = [i + 1 for i, status in enumerate(scene_pass_status) if not status]
    #     print(f"[WARN] 已达到最大迭代次数 ({MAX_ITERATIONS}次)。")
    #     print(f"[WARN] 以下场景仍未通过审查: {failed_scenes}")
    #
    # # 5. 整理最终结果
    # refine_script = {'剧本': scripts_to_refine}
    # refine_script = remove_parentheses_in_script(refine_script)
    #
    # print("[INFO] 情感与表演指导...")
    # Emotion = {'语气标注': []}
    # for index,script in enumerate(refine_script['剧本']):
    #     str_script = script_to_annotated_string_by_scene(script)
    #     tmp_character = []
    #     character_profiles_in_script = extract_character_profiles(script, current_characters)
    #     for value in character_profiles_in_script.values():
    #         tmp_character.append({
    #         "规范化名称": value.get("规范化名称", ""),
    #         "别名": value.get("别名", []),
    #         "性格特征": value.get("性格特征", []),
    #         "性别":value.get("性别","")
    #     })
    #     tmp_character2 = json.dumps(tmp_character, indent=4, ensure_ascii=False)
    #     result = current_prompt_module.Emotional_Guidance(tmp_character2,str_script)
    #     Emotion['语气标注'].append(result)
    # print("[INFO] Script generation finished.")
    # script_with_emotion = combine_script_and_emotion(refine_script, Emotion)
    # output_lines = []
    # for scene in script_with_emotion['剧本']:
    #     output_lines.append(f"场景：{scene['场景']}")
    #     for line in scene['场景剧本']:
    #         role = line['角色']
    #         content = line['内容']
    #         output_lines.append(f"{role}：{content}")
    #     output_lines.append("---" * 70)
    # str_script = "\n".join(output_lines)
    # return str_script, gr.update(interactive=True), gr.update(
    #     open=True), "剧本生成成功，请继续进行角色声音配对。", script_with_emotion

    # 测试
    script_structure_gemini = {
        "改编大纲": [
            {
                "场景": 1,
                "改编目标": "快速建立石猴勇敢、爱探索的形象，突出“发现水帘洞”这一核心事件，强化故事的趣味性和动作感，让儿童听众迅速代入角色。",
                "节奏调整": [
                    {
                        "部分": "原文开头关于宇宙形成、天地计数、十二时辰等过于宏大和抽象的背景介绍。",
                        "调整方式": "全部删除。故事直接从“东胜神洲花果山顶上有一块神奇的仙石”开始，用简洁的旁白（如“这块石头每天晒太阳、吹风，变得越来越有灵气”）引出石猴的诞生，加快故事进入正题的速度。"
                    },
                    {
                        "部分": "猴群玩耍的详细描写（如扯葛藤、编草绳、捉虱子等）。",
                        "调整方式": "简化为更具动感的描述，用音效配合旁白。例如：“小猴子们在林子里荡秋千、捉迷藏，传来一片叽叽喳喳的欢笑声。”，重点突出它们的快乐，而非具体行为。"
                    },
                    {
                        "部分": "原文中发现瀑布后，猴子们的讨论和约定过程较为平淡。",
                        "调整方式": "增强冲突。将猴子们的反应改为对话形式，增加戏剧性。例如，一只小猴说：“哇，好大的瀑布，里面会不会有妖怪呀？”另一只胆小的猴子说：“我可不敢进去！”通过对话凸显石猴的勇敢，让他主动站出来说：“别怕，我去看看到底有什么！”"
                    }
                ],
                "转化困难的部分": [
                    {
                        "部分": "水帘洞内部景色的纯视觉描写（如翠藓堆蓝、白云浮玉、石碣文字等）。",
                        "调整方式": "通过石猴的惊叹和发现来转化为听觉内容。例如，旁白：“石猴一进去，哇！里面好大好亮啊！”，石猴的台词：“这里有石头的桌子和凳子，还有软软的石床！看，墙上还刻着字呢，叫‘水帘洞’！这简直就是为我们准备的家呀！”用角色的兴奋情绪和简单的描述替代复杂的景物描写。"
                    }
                ]
            },
            {
                "场景": 2,
                "改编目标": "将猴王对“死亡”的抽象恐惧，转化为儿童能够理解的“对快乐时光结束的担忧”，明确他外出求仙的动机，使其行为更具逻辑性和情感共鸣。",
                "节奏调整": [
                    {
                        "部分": "猴王突然感到忧虑并流泪的心理活动。",
                        "调整方式": "通过简单的对话来外化情感。猴王可以叹气说：“虽然我们每天都很快乐，但如果有一天我们老了，跳不动了，那该怎么办呢？我希望能永远和大家这样开心地玩下去。”"
                    },
                    {
                        "部分": "通臂猿猴关于“佛、仙、神圣”三者的分类解释。",
                        "调整方式": "简化并合并。直接让老猴子说：“大王，听说很远的地方有一位神仙，他有长生不老的魔法，能让快乐永远不结束！只要找到他，学习他的本领，我们就再也不用担心了。”将复杂的概念简化为“有魔法的神仙”和“让快乐永不结束的本领”。"
                    }
                ],
                "转化困难的部分": [
                    {
                        "部分": "原文中对死亡和阎王的哲学探讨。",
                        "调整方式": "完全删除。将核心冲突简化为“希望快乐永恒”VS“时光流逝”，这是一个儿童更能理解和共情的主题。重点放在猴王为了保护大家的快乐而踏上旅程的决心上，强调其责任感和勇气。"
                    }
                ]
            },
            {
                "场景": 3,
                "改编目标": "缩短漫长的寻仙旅程，让猴王与樵夫的相遇成为关键节点，快速引出菩提祖师的所在地，保持故事的推进感。",
                "节奏调整": [
                    {
                        "部分": "猴王漂洋过海、游历人间的八九年时间。",
                        "调整方式": "用一段简短的旁白和音效（如海浪声、风声）快速带过。例如：“猴王坐着小木筏，漂过了一个又一个大海，走过了一座又一座高山，他找啊找啊，找了很久很久。”"
                    },
                    {
                        "部分": "樵夫所唱的充满道家哲理的歌曲。",
                        "调整方式": "将歌词内容改为简单直白、充满童趣的语言，核心只保留“神仙”的线索。例如，樵夫可以唱：“砍柴呀，真快乐，山里住着老神仙，教会我呀唱新歌，烦恼见了都躲着。”"
                    },
                    {
                        "部分": "樵夫解释自己因母亲无法修仙的详细对话。",
                        "调整方式": "简化对话。猴王问：“你为什么不跟神仙学长生不老的本领呢？”樵夫回答：“我要照顾我年迈的妈妈呀。”一两句对话即可体现樵夫的孝心，并迅速将话题转到“神仙在哪里”。"
                    }
                ],
                "转化困难的部分": [
                    {
                        "部分": "灵台方寸山、斜月三星洞的景色描写。",
                        "调整方式": "通过猴王的视角和感受来描述。例如，旁白：“按照樵夫指的方向，猴王果然看到了一座云雾缭绕的大山，空气里都是香香甜甜的味道。他心里想：神仙一定就住在这里！”用感官和情绪来替代视觉描写。"
                    }
                ]
            },
            {
                "场景": 4,
                "改编目标": "将拜师学艺的过程趣味化，把祖师的考验设计成一个“秘密暗号”游戏，突出孙悟空的聪明机灵，让学艺过程充满神秘感和期待感。",
                "节奏调整": [
                    {
                        "部分": "祖师盘问悟空来历和身世的冗长对话。",
                        "调整方式": "大幅缩减。祖师问：“你从哪里来？”悟空答：“花果山水帘洞。”祖师再根据他活泼的样子，直接赐姓为“孙”，取名“悟空”，让节奏更明快。"
                    },
                    {
                        "部分": "祖师向悟空传授“术”、“流”、“静”、“动”四门道法并被悟空一一拒绝的重复情节。",
                        "调整方式": "完全删除。改为祖师考验悟空的耐心和智慧。祖师可以直接说：“想学我的真本领可不容易，你得有耐心才行。”然后直接引出“敲三下头”的考验情节，让冲突更集中。"
                    },
                    {
                        "部分": "祖师传授长生妙诀的诗歌。",
                        "调整方式": "删除诗歌。改为旁白描述：“祖师在悟空耳边悄悄说出了神奇的咒语，那咒语像唱歌一样好听。悟空一下子就记住了，他感觉身体里充满了力量！”用神秘感和效果描述来替代难懂的口诀。"
                    }
                ],
                "转化困难的部分": [
                    {
                        "部分": "祖师用戒尺打悟空三下，然后背手关门的无声动作。",
                        "调整方式": "通过孙悟空的内心独白和旁白解释清楚。旁白：“大家都被吓坏了，以为悟空惹恼了师父。但聪明的悟空却明白了！”悟空内心独白：“师父打我三下，是让我在三更半夜去找他！从后门进去，是教我悄悄地去！这一定是师父给我的秘密暗号！”这样可以让儿童听众清晰地理解这个关键转折。"
                    }
                ]
            },
            {
                "场景": 5,
                "改编目标": "展示孙悟空学成的神奇本领，并通过“炫耀被罚”的情节，传递“真正的本领不是用来炫耀”的正面价值观，为孙悟空的成长画上句号，并开启新的旅程。",
                "节奏调整": [
                    {
                        "部分": "祖师解释“三灾利害”和天罡地煞变化的复杂概念。",
                        "调整方式": "合并简化。祖师可以在传授完72变后直接教筋斗云，作为最后的礼物。将复杂的灾难理论去掉，让学习过程更纯粹、更神奇。"
                    },
                    {
                        "部分": "悟空和师兄们关于是否学会法术的对话。",
                        "调整方式": "直接进入动作场面。师兄们可以好奇地问：“悟空，听说你学了新魔法，变一个给我们看看吧！”直接触发悟空的炫耀行为，让情节更紧凑。"
                    },
                    {
                        "部分": "祖师严厉斥责并解释赶走悟空的原因。",
                        "调整方式": "将斥责的语气调整为语重心长的教导。祖师可以说：“悟空，你的本领学成了。但记住，真正的强大不是向别人炫耀，而是用它来做对的事情。你已经长大了，是时候回家了。”这样更符合儿童教育的温和方式。"
                    }
                ],
                "转化困难的部分": [
                    {
                        "部分": "悟空变成松树的纯视觉变化。",
                        "调整方式": "用音效和师兄们的惊叹来表现。旁白：“悟空念动咒语，只听‘砰’的一声，他原地消失了，变成了一棵高大的松树！”然后加入其他猴子（仙童）的惊呼：“哇！真的变成松树了！”“太厉害了！”来烘托变化的神奇效果。"
                    },
                    {
                        "部分": "筋斗云“十万八千里”的距离概念。",
                        "调整方式": "用比喻来让儿童理解。旁白可以描述：“悟空翻了一个跟斗，‘嗖’的一下，就像坐上了最快的火箭，眨眼间，家乡花果山就出现在眼前了！”用熟悉的事物来类比，增强听觉画面的生动性。"
                    }
                ]
            }
        ]
    }
    script_structure_gemini_str = json.dumps(script_structure_gemini, indent=4, ensure_ascii=False)
    dialogue_gemini = {
        "剧本": [
            {
                "场景": 1,
                "场景剧本": [
                    {
                        "角色": "猴子们",
                        "对白": "哗啦啦！好大的瀑布啊！声音真响！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "水这么急，里面会不会有大妖怪？我好害怕！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "怕什么！我们猴子天不怕地不怕！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "可是……可是万一回不来了怎么办？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "别担心，我去看看到底有什么！要是有好玩的地方，我就叫你们！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "你真的敢进去吗？太危险了！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "看我的！我跳进去啦！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "啊！他真的跳进去了！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "（从瀑布后传来）哇！快来呀！这里面是个大宝贝！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "里面是什么？你还好吗？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "好得很！这里有石头的桌子和凳子，还有软软的石床！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "真的吗？还有什么？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "哈哈，墙上还写着字呢，叫‘水帘洞’！这简直就是为我们准备的家呀！大家快进来！"
                    }
                ]
            },
            {
                "场景": 2,
                "场景剧本": [
                    {
                        "角色": "猴子们",
                        "对白": "大王，今天的水果真甜！我们来玩捉迷藏吧！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "（叹气）唉……"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "大王，你怎么了？为什么不开心呀？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "我们每天都很快乐，可是……如果有一天我们老了，跳不动了，那该怎么办呢？"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "老了？那我们就不能一起玩了吗？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "是啊，我希望能永远和大家这样开心地玩下去。"
                    },
                    {
                        "角色": "老猿猴",
                        "对白": "大王，您能想到这么远，真是了不起。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "老人家，难道你有什么好办法吗？"
                    },
                    {
                        "角色": "老猿猴",
                        "对白": "我听说，在很远很远的地方，住着一位神仙。他有长生不老的魔法，能让快乐永远不结束！"
                    },
                    {
                        "角色": "猴子们",
                        "对白": "真的吗？长生不老的魔法？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "神仙在哪里？我一定要找到他！"
                    },
                    {
                        "角色": "老猿猴",
                        "对白": "只要您去寻找，就一定能找到。学习他的本领，我们就再也不用担心了。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "好！为了大家，我明天就出发！"
                    }
                ]
            },
            {
                "场景": 3,
                "场景剧本": [
                    {
                        "角色": "樵夫",
                        "对白": "（唱歌）砍柴呀，真快乐，山里住着老神仙，教会我呀唱新歌，烦恼见了都躲着。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "（跳出来）老神仙，你好呀！"
                    },
                    {
                        "角色": "樵夫",
                        "对白": "哎呀！吓我一跳！我不是神仙，我只是个砍柴的。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "你刚才唱的歌里不是有神仙吗？"
                    },
                    {
                        "角色": "樵夫",
                        "对白": "哦，那首歌是住在这山里的神仙爷爷教我的，他说我一唱歌，烦恼就没了。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "那你为什么不跟他学长生不老的本领呢？"
                    },
                    {
                        "角色": "樵夫",
                        "对白": "唉，我要照顾我年迈的妈妈呀，没时间去学习。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "你真是个孝顺的好孩子！快告诉我，神仙爷爷住在哪里？我想去拜访他！"
                    },
                    {
                        "角色": "樵夫",
                        "对白": "不远不远，你顺着这条小路一直往南走，就能看到一个山洞，那就是神仙的家了。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "太好了！谢谢你，好心的樵夫！"
                    },
                    {
                        "角色": "樵夫",
                        "对白": "不用谢，快去吧！"
                    }
                ]
            },
            {
                "场景": 4,
                "场景剧本": [
                    {
                        "角色": "菩提祖师",
                        "对白": "你这猴头，从哪里来的？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "师父，我从东胜神洲花果山水帘洞来，想跟您学习长生不老的本领！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "嗯……看你这么活泼，就给你取个名字，叫‘孙悟空’吧。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "孙悟空？太好了！谢谢师父赐名！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "你这猢狲！这也不学，那也不学，到底想怎样！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "师父，我……"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "（用戒尺在悟空头上敲了三下）哼！"
                    },
                    {
                        "角色": "众师兄",
                        "对白": "哎呀！你这猴子，怎么把师父给气走了！"
                    },
                    {
                        "角色": "众师兄",
                        "对白": "这下完了，师父肯定不会再教我们了！都怪你！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "（小声对自己说）嘿嘿，我明白了！师父打我三下，是让我在三更半夜去找他！从后门进去，是教我悄悄地去！这是师父给我的秘密暗号！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "（夜里，在房间里）你这猢狲，不在前面睡觉，跑来这里做什么？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "师父，我明白您的暗号了，特地来请师父教我真本领！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "呵呵，果然是个聪明的猴头。你过来，我便将那长生妙法，悄悄说与你听。"
                    }
                ]
            },
            {
                "场景": 5,
                "场景剧本": [
                    {
                        "角色": "众师兄",
                        "对白": "悟空，听说你学了新魔法，快变一个给我们看看吧！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "好嘞！看我七十二变！你们想让我变成什么？"
                    },
                    {
                        "角色": "众师兄",
                        "对白": "变成一棵大松树！"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "没问题！变！"
                    },
                    {
                        "角色": "众师兄",
                        "对白": "哇！真的变成一棵松树了！一模一样！"
                    },
                    {
                        "角色": "众师兄",
                        "对白": "太厉害了！好猴子！好猴子！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "是谁在这里大声喧哗？"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "（变回原形）师父……"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "悟空，你的本领学成了。但记住，真正的强大不是向别人炫耀，而是用它来做对的事情。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "师父，我错了。"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "你已经长大了，是时候回家了。去吧，回到你的花果山去。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "师父……我舍不得您！"
                    },
                    {
                        "角色": "菩提祖师",
                        "对白": "去吧。但是记住，以后无论惹出什么祸事，都不能说我是你的师父。"
                    },
                    {
                        "角色": "孙悟空",
                        "对白": "弟子明白！师父保重！我走啦！筋斗云，起！"
                    }
                ]
            }
        ]
    }
    narration_gemini = {
        "剧本": [
            {
                "场景": 1,
                "旁白内容": [
                    {
                        "插入位置": 0,
                        "旁白": "在遥远的东胜神洲，有一座美丽的花果山。山上住着一群快乐的小猴子，还有一只从石头里蹦出来的石猴。这天，大家在小溪边玩耍，忽然听到一阵巨大的响声，他们顺着声音找了过去。"
                    },
                    {
                        "插入位置": 6,
                        "旁白": "石猴说完，深吸一口气，闭上眼睛，向着白茫茫的水帘猛地跳了过去！"
                    },
                    {
                        "插入位置": 8,
                        "旁白": "石猴穿过凉凉的水帘，睁开眼睛一看，瀑布后面竟然别有洞天，根本没有水，而是一个亮晶晶的大山洞！"
                    },
                    {
                        "插入位置": 13,
                        "旁白": "听到石猴的呼唤，小猴子们一个接一个，勇敢地跳进了瀑布。大家在新家里欢呼雀跃，把又聪明又勇敢的石猴，推选为他们的大王——美猴王！"
                    }
                ]
            },
            {
                "场景": 2,
                "旁白内容": [
                    {
                        "插入位置": 0,
                        "旁白": "自从住进了水帘洞，美猴王和猴子们每天都过得特别开心。可是有一天，当大家正在草地上追逐打闹时，美猴王却自己坐在一块大石头上，好像有心事。"
                    },
                    {
                        "插入位置": 6,
                        "旁白": "就在大家不知道该怎么办的时候，猴群里一位年纪最大的老猴子走了过来。"
                    },
                    {
                        "插入位置": 12,
                        "旁白": "听到有这样的神仙，美猴王一下子站了起来，眼睛里闪着希望的光芒。"
                    },
                    {
                        "插入位置": 13,
                        "旁白": "为了守护大家的快乐，勇敢的美猴王决定独自出海，去寻找那位能教他长生不老魔法的神仙。"
                    }
                ]
            },
            {
                "场景": 3,
                "旁白内容": [
                    {
                        "插入位置": 0,
                        "旁白": "美猴王坐着自己做的小木筏，漂过了一个又一个大海，走过了一座又一座高山。他找啊找啊，找了很久很久。这一天，他来到一座云雾缭绕的大山里，正走着，忽然听到一阵清脆的歌声。"
                    },
                    {
                        "插入位置": 1,
                        "旁白": "美猴王心里一喜，顺着歌声悄悄地拨开树丛一看，发现唱歌的原来是一个正在砍柴的小哥哥。"
                    },
                    {
                        "插入位置": 9,
                        "旁白": "美猴王向樵夫道了谢，就立刻顺着小路跑了过去。很快，他看到了一座云雾缭绕的山洞，空气里都是香香甜甜的味道。他知道，自己终于找到了！"
                    }
                ]
            },
            {
                "场景": 4,
                "旁白内容": [
                    {
                        "插入位置": 0,
                        "旁白": "孙悟空跟着仙童走进洞府深处，看见一位白胡子老爷爷正坐在高台上讲课，他知道，这位一定就是菩提祖师了。他赶紧跑上前去，恭恭敬敬地跪下磕头。"
                    },
                    {
                        "插入位置": 4,
                        "旁白": "就这样，孙悟空在洞里住了下来，每天跟着师兄们学习本领。可是师父教的，都只是些普通的法术。这一天，师父又问大家想学什么，孙悟空还是说只想学长生不老的真本领，这下，师父好像生气了。"
                    },
                    {
                        "插入位置": 7,
                        "旁白": "祖师说完，真的走下台，拿起戒尺在悟空头上不轻不重地敲了三下，然后背着手，自己走进里屋，还把门关上了。其他的师兄们都吓坏了，纷纷指责悟空。"
                    },
                    {
                        "插入位置": 10,
                        "旁白": "到了晚上，悟空假装睡着了，等到半夜三更，他悄悄地爬起来，溜到后门一看，门果然留着一条缝。他蹑手蹑脚地走了进去，跪在了师父的床边。"
                    },
                    {
                        "插入位置": 13,
                        "旁白": "于是，菩提祖师在悟空耳边悄悄说出了神奇的咒语，那咒语像唱歌一样好听。聪明的悟空一下子就记住了，他感觉身体里充满了暖洋洋的力量！"
                    }
                ]
            },
            {
                "场景": 5,
                "旁白内容": [
                    {
                        "插入位置": 0,
                        "旁白": "学会了七十二变和筋斗云之后，孙悟空开心极了。这天，他和师兄们在松树下聊天，大家早就听说他学了新本领，都好奇地围了上来。"
                    },
                    {
                        "插入位置": 3,
                        "旁白": "悟空念动咒语，用手一指，只听“砰”的一声，他原地消失了，地上真的出现了一棵高大挺拔的松树！"
                    },
                    {
                        "插入位置": 6,
                        "旁白": "大家的欢笑声和鼓掌声太大了，把正在房间里休息的菩提祖师给吵醒了。祖师拄着拐杖走了出来，看到大家闹哄哄的样子，脸上露出了严肃的表情。"
                    },
                    {
                        "插入位置": 13,
                        "旁白": "孙悟空向师父拜了三拜，忍着眼泪，转身念动咒语。"
                    },
                    {
                        "插入位置": 14,
                        "旁白": "这筋斗云可真快呀，嗖的一下，就像坐上了最快的火箭，眨眼间，他就飞得无影无踪了。孙悟空终于学成本领，要回到他日思夜想的花果山啦！"
                    }
                ]
            }
        ]
    }
    pre_script_gemini = {
        '剧本': [{
            '场景': 1,
            '场景剧本': [{
                '角色': '旁白',
                '内容': '在遥远的东胜神洲，有一座美丽的花果山。山上住着一群快乐的小猴子，还有一只从石头里蹦出来的石猴。这天，大家在小溪边玩耍，忽然听到一阵巨大的响声，他们顺着声音找了过去。'
            },
                {
                    '角色': '猴子们',
                    '内容': '哗啦啦！好大的瀑布啊！声音真响！'
                },
                {
                    '角色': '猴子们',
                    '内容': '水这么急，里面会不会有大妖怪？我好害怕！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '怕什么！我们猴子天不怕地不怕！'
                },
                {
                    '角色': '猴子们',
                    '内容': '可是……可是万一回不来了怎么办？'
                },
                {
                    '角色': '孙悟空',
                    '内容': '别担心，我去看看到底有什么！要是有好玩的地方，我就叫你们！'
                },
                {
                    '角色': '猴子们',
                    '内容': '你真的敢进去吗？太危险了！'
                },
                {
                    '角色': '旁白',
                    '内容': '石猴说完，深吸一口气，闭上眼睛，向着白茫茫的水帘猛地跳了过去！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '看我的！我跳进去啦！'
                },
                {
                    '角色': '猴子们',
                    '内容': '啊！他真的跳进去了！'
                },
                {
                    '角色': '旁白',
                    '内容': '石猴穿过凉凉的水帘，睁开眼睛一看，瀑布后面竟然别有洞天，根本没有水，而是一个亮晶晶的大山洞！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '（从瀑布后传来）哇！快来呀！这里面是个大宝贝！'
                },
                {
                    '角色': '猴子们',
                    '内容': '里面是什么？你还好吗？'
                },
                {
                    '角色': '孙悟空',
                    '内容': '好得很！这里有石头的桌子和凳子，还有软软的石床！'
                },
                {
                    '角色': '猴子们',
                    '内容': '真的吗？还有什么？'
                },
                {
                    '角色': '孙悟空',
                    '内容': '哈哈，墙上还写着字呢，叫‘水帘洞’！这简直就是为我们准备的家呀！大家快进来！'
                },
                {
                    '类型': '旁白',
                    '内容': '听到石猴的呼唤，小猴子们一个接一个，勇敢地跳进了瀑布。大家在新家里欢呼雀跃，把又聪明又勇敢的石猴，推选为他们的大王——美猴王！'
                }]
        },
            {
                '场景': 2,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '自从住进了水帘洞，美猴王和猴子们每天都过得特别开心。可是有一天，当大家正在草地上追逐打闹时，美猴王却自己坐在一块大石头上，好像有心事。'
                },
                    {
                        '角色': '猴子们',
                        '内容': '大王，今天的水果真甜！我们来玩捉迷藏吧！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（叹气）唉……'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '大王，你怎么了？为什么不开心呀？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '我们每天都很快乐，可是……如果有一天我们老了，跳不动了，那该怎么办呢？'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '老了？那我们就不能一起玩了吗？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '是啊，我希望能永远和大家这样开心地玩下去。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '就在大家不知道该怎么办的时候，猴群里一位年纪最大的老猴子走了过来。'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '大王，您能想到这么远，真是了不起。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '老人家，难道你有什么好办法吗？'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '我听说，在很远很远的地方，住着一位神仙。他有长生不老的魔法，能让快乐永远不结束！'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '真的吗？长生不老的魔法？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '神仙在哪里？我一定要找到他！'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '只要您去寻找，就一定能找到。学习他的本领，我们就再也不用担心了。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '听到有这样的神仙，美猴王一下子站了起来，眼睛里闪着希望的光芒。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '好！为了大家，我明天就出发！'
                    },
                    {
                        '类型': '旁白',
                        '内容': '为了守护大家的快乐，勇敢的美猴王决定独自出海，去寻找那位能教他长生不老魔法的神仙。'
                    }]
            },
            {
                '场景': 3,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '美猴王坐着自己做的小木筏，漂过了一个又一个大海，走过了一座又一座高山。他找啊找啊，找了很久很久。这一天，他来到一座云雾缭绕的大山里，正走着，忽然听到一阵清脆的歌声。'
                },
                    {
                        '角色': '樵夫',
                        '内容': '（唱歌）砍柴呀，真快乐，山里住着老神仙，教会我呀唱新歌，烦恼见了都躲着。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '美猴王心里一喜，顺着歌声悄悄地拨开树丛一看，发现唱歌的原来是一个正在砍柴的小哥哥。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（跳出来）老神仙，你好呀！'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '哎呀！吓我一跳！我不是神仙，我只是个砍柴的。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '你刚才唱的歌里不是有神仙吗？'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '哦，那首歌是住在这山里的神仙爷爷教我的，他说我一唱歌，烦恼就没了。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '那你为什么不跟他学长生不老的本领呢？'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '唉，我要照顾我年迈的妈妈呀，没时间去学习。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '你真是个孝顺的好孩子！快告诉我，神仙爷爷住在哪里？我想去拜访他！'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '不远不远，你顺着这条小路一直往南走，就能看到一个山洞，那就是神仙的家了。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '美猴王向樵夫道了谢，就立刻顺着小路跑了过去。很快，他看到了一座云雾缭绕的山洞，空气里都是香香甜甜的味道。他知道，自己终于找到了！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '太好了！谢谢你，好心的樵夫！'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '不用谢，快去吧！'
                    }]
            },
            {
                '场景': 4,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '孙悟空跟着仙童走进洞府深处，看见一位白胡子老爷爷正坐在高台上讲课，他知道，这位一定就是菩提祖师了。他赶紧跑上前去，恭恭敬敬地跪下磕头。'
                },
                    {
                        '角色': '菩提祖师',
                        '内容': '你这猴头，从哪里来的？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父，我从东胜神洲花果山水帘洞来，想跟您学习长生不老的本领！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '嗯……看你这么活泼，就给你取个名字，叫‘孙悟空’吧。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '孙悟空？太好了！谢谢师父赐名！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '就这样，孙悟空在洞里住了下来，每天跟着师兄们学习本领。可是师父教的，都只是些普通的法术。这一天，师父又问大家想学什么，孙悟空还是说只想学长生不老的真本领，这下，师父好像生气了。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '你这猢狲！这也不学，那也不学，到底想怎样！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父，我……'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（用戒尺在悟空头上敲了三下）哼！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '祖师说完，真的走下台，拿起戒尺在悟空头上不轻不重地敲了三下，然后背着手，自己走进里屋，还把门关上了。其他的师兄们都吓坏了，纷纷指责悟空。'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '哎呀！你这猴子，怎么把师父给气走了！'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '这下完了，师父肯定不会再教我们了！都怪你！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（小声对自己说）嘿嘿，我明白了！师父打我三下，是让我在三更半夜去找他！从后门进去，是教我悄悄地去！这是师父给我的秘密暗号！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '到了晚上，悟空假装睡着了，等到半夜三更，他悄悄地爬起来，溜到后门一看，门果然留着一条缝。他蹑手蹑脚地走了进去，跪在了师父的床边。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（夜里，在房间里）你这猢狲，不在前面睡觉，跑来这里做什么？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父，我明白您的暗号了，特地来请师父教我真本领！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '呵呵，果然是个聪明的猴头。你过来，我便将那长生妙法，悄悄说与你听。'
                    },
                    {
                        '类型': '旁白',
                        '内容': '于是，菩提祖师在悟空耳边悄悄说出了神奇的咒语，那咒语像唱歌一样好听。聪明的悟空一下子就记住了，他感觉身体里充满了暖洋洋的力量！'
                    }]
            },
            {
                '场景': 5,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '学会了七十二变和筋斗云之后，孙悟空开心极了。这天，他和师兄们在松树下聊天，大家早就听说他学了新本领，都好奇地围了上来。'
                },
                    {
                        '角色': '众师兄',
                        '内容': '悟空，听说你学了新魔法，快变一个给我们看看吧！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '好嘞！看我七十二变！你们想让我变成什么？'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '变成一棵大松树！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '悟空念动咒语，用手一指，只听“砰”的一声，他原地消失了，地上真的出现了一棵高大挺拔的松树！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '没问题！变！'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '哇！真的变成一棵松树了！一模一样！'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '太厉害了！好猴子！好猴子！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '大家的欢笑声和鼓掌声太大了，把正在房间里休息的菩提祖师给吵醒了。祖师拄着拐杖走了出来，看到大家闹哄哄的样子，脸上露出了严肃的表情。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '是谁在这里大声喧哗？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（变回原形）师父……'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '悟空，你的本领学成了。但记住，真正的强大不是向别人炫耀，而是用它来做对的事情。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父，我错了。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '你已经长大了，是时候回家了。去吧，回到你的花果山去。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父……我舍不得您！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '去吧。但是记住，以后无论惹出什么祸事，都不能说我是你的师父。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '孙悟空向师父拜了三拜，忍着眼泪，转身念动咒语。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '弟子明白！师父保重！我走啦！筋斗云，起！'
                    },
                    {
                        '类型': '旁白',
                        '内容': '这筋斗云可真快呀，嗖的一下，就像坐上了最快的火箭，眨眼间，他就飞得无影无踪了。孙悟空终于学成本领，要回到他日思夜想的花果山啦！'
                    }]
            }]
    }
    script_conflict_escalation_gemini = {
	'剧本': [{
		'场景': 1,
		'场景剧本': [{
			'角色': '旁白',
			'内容': '在遥远的东胜神洲，有一座美丽的花果山。山上住着一群快乐的小猴子，还有一只从石头里蹦出来的石猴。这天，大家在小溪边玩耍，忽然听到一阵巨大的响声，他们顺着声音找了过去。'
		},
		{
			'角色': '猴子们',
			'内容': '（惊叹）哗啦啦！好大的瀑布啊！声音真响！'
		},
		{
			'角色': '老猿猴',
			'内容': '孩子们，我们祖祖辈辈都说，谁有本事跳过这瀑布，找到水的源头，还能平安回来，我们就拜他当大王！'
		},
		{
			'角色': '猴子们',
			'内容': '（害怕）当大王？不行不行，太危险了！水这么急，里面肯定有妖怪！'
		},
		{
			'角色': '猴子们',
			'内容': '是啊，万一被大水冲走了怎么办？我可不敢去！'
		},
		{
			'角色': '孙悟空',
			'内容': '（不服气地）哼，真没出息！连试一试的胆子都没有吗？'
		},
		{
			'角色': '猴子们',
			'内容': '（被激将）你……你敢说我们没出息？那你去啊！'
		},
		{
			'角色': '孙悟空',
			'内容': '（坚定地）去就去！我今天就跳进去看看！要是我在里面找到了一个能挡风躲雨的好地方，你们就都要拜我做大王，听我的话！'
		},
		{
			'角色': '猴子们',
			'内容': '（犹豫但又期待）好……好吧！你要是真能找到一个家，我们就认你当大王！'
		},
		{
			'角色': '旁白',
			'内容': '石猴说完，深吸一口气，闭上眼睛，向着白茫茫的水帘猛地跳了过去！'
		},
		{
			'角色': '孙悟空',
			'内容': '看我的！我跳进去啦！'
		},
		{
			'角色': '猴子们',
			'内容': '（紧张地大喊）啊！他真的跳进去了！'
		},
		{
			'角色': '旁白',
			'内容': '石猴穿过凉凉的水帘，睁开眼睛一看，瀑布后面竟然别有洞天，根本没有水，而是一个亮晶晶的大山洞！'
		},
		{
			'角色': '孙悟空',
			'内容': '（声音从瀑布后传来，充满兴奋）哇！快来呀！这里面是个大宝贝！一个不用怕下雨的家！'
		},
		{
			'角色': '猴子们',
			'内容': '（焦急地问）里面是什么？你还好吗？没有妖怪吧？'
		},
		{
			'角色': '孙悟空',
			'内容': '好得很！这里有石头的桌子和凳子，还有软软的石床！'
		},
		{
			'角色': '猴子们',
			'内容': '真的吗？还有什么？'
		},
		{
			'角色': '孙悟空',
			'内容': '哈哈，墙上还写着字呢，叫‘水帘洞’！这简直就是为我们准备的家呀！大家快进来！'
		},
		{
			'角色': '旁白',
			'内容': '听到石猴的呼唤，小猴子们又惊喜又佩服，一个接一个，勇敢地跳进了瀑布。大家看到这么好的新家，都开心地欢呼起来，一起遵守约定，拜又聪明又勇敢的石猴为大王，还给他取了个威风的名字——美猴王！'
		}]
	},
	{
		'场景': 2,
		'场景剧本': [{
			'角色': '旁白',
			'内容': '自从住进了水帘洞，美猴王和猴子们每天都过得特别开心。可是有一天，当大家正在草地上追逐打闹时，美猴王却自己坐在一块大石头上，长长地叹了一口气。'
		},
		{
			'角色': '猴子们',
			'内容': '大王，快来呀！我们来玩捉迷藏吧！'
		},
		{
			'角色': '孙悟空',
			'内容': '（看着大家，小声地）唉……真希望这样的日子永远不要结束。'
		},
		{
			'角色': '猴子们',
			'内容': '（跑过来）大王，你怎么了？为什么不开心呀？我们不是玩得好好的吗？'
		},
		{
			'角色': '孙悟空',
			'内容': '我们每天都很快乐，可是……我在担心，如果有一天我们都老了，跳不动了，那该怎么办呢？'
		},
		{
			'角色': '猴子们',
			'内容': '（不服气地）才不会呢！我们永远都会这么开心的！老了也可以一起玩呀！'
		},
		{
			'角色': '孙悟空',
			'内容': '（摇摇头，很坚定地）不行！我不能让这种事情发生。我希望大家的快乐永远不会变老，永远不会消失！'
		},
		{
			'角色': '旁白',
			'内容': '就在大家不知道该怎么安慰大王时，猴群里一位年纪最大的老猴子走了过来。'
		},
		{
			'角色': '老猿猴',
			'内容': '大王，您是在为大家的快乐担心啊。我听说，有一个办法，能让快乐永远不结束！'
		},
		{
			'角色': '孙悟空',
			'内容': '（立刻站起来）什么办法？快告诉我！'
		},
		{
			'角色': '老猿猴',
			'内容': '我听说，在很远很远的地方，住着一位有魔法的神仙。他有长生不老的本领！'
		},
		{
			'角色': '猴子们',
			'内容': '哇！长生不老？那是不是就意味着可以永远玩下去了？'
		},
		{
			'角色': '老猿猴',
			'内容': '没错！只要大王能找到他，学习他的本领，我们就再也不用担心快乐会消失了。'
		},
		{
			'角色': '孙悟空',
			'内容': '（眼睛里闪着光）好！不管有多远，多困难，我一定要找到这位神仙！'
		},
		{
			'角色': '猴子们',
			'内容': '大王，我们跟你一起去！'
		},
		{
			'角色': '孙悟空',
			'内容': '（拍拍胸脯）不，路途太危险了。你们在家里等我，我一定会把‘永远的快乐’带回来！我明天就出发！'
		},
		{
			'角色': '旁白',
			'内容': '为了守护大家的快乐，勇敢的美猴王下定决心，要独自出海，去寻找那位能教他长生不老魔法的神仙。'
		}]
	},
	{
		'场景': 3,
		'场景剧本': [{
			'角色': '旁白',
			'内容': '美猴王坐着自己做的小木筏，漂过了一个又一个大海，走过了一座又一座高山。他找啊找啊，找了很久很久。这一天，他来到一座云雾缭绕的大山里，正走着，忽然听到一阵清脆的歌声。'
		},
		{
			'角色': '樵夫',
			'内容': '（唱歌）砍柴呀，真快乐，山里住着老神仙，教会我呀唱新歌，烦恼见了都躲着。'
		},
		{
			'角色': '旁白',
			'内容': '美猴王心里一喜，以为终于找到了神仙。他悄悄拨开树丛，发现唱歌的原来是一个正在砍柴的小哥哥。'
		},
		{
			'角色': '孙悟空',
			'内容': '（激动地跳出来）老神仙！我可找到你了！'
		},
		{
			'角色': '樵夫',
			'内容': '（吓了一大跳，后退一步）哎呀！你……你是谁？你吓死我了！我不是神仙！'
		},
		{
			'角色': '孙悟空',
			'内容': '（有些失望）你不是？可你唱的歌里明明有神仙呀！你一定认识他，对不对？'
		},
		{
			'角色': '樵夫',
			'内容': '（警惕地看着他）我……我为什么要告诉你？神仙爷爷不喜欢陌生人来打扰他。你快走吧。'
		},
		{
			'角色': '旁白',
			'内容': '孙悟空心里咯噔一下，他找了那么久，难道就要在这里失败了吗？他心里又着急又委屈。'
		},
		{
			'角色': '孙悟空',
			'内容': '（恳切地）求求你了！我叫孙悟空，是从很远很远的花果山来的。我漂洋过海，走了好久好久的路，就是想拜神仙为师，学长生不老的本领，好回去保护我的猴子猴孙们！'
		},
		{
			'角色': '樵夫',
			'内容': '（被孙悟空的真诚打动了）原来……你是为了保护大家才来学本领的。唉，你这份心意真了不起。不像我，还得照顾年迈的妈妈，没法去学仙法。'
		},
		{
			'角色': '孙悟空',
			'内容': '你真是个孝顺的好孩子！那你愿意告诉我神仙爷爷住在哪里了吗？'
		},
		{
			'角色': '樵夫',
			'内容': '（笑着点头）当然！你顺着这条小路一直往南走，就能看到一个亮晶晶的山洞，那就是神仙的家了。记住，见到神仙一定要有礼貌哦！'
		},
		{
			'角色': '孙悟空',
			'内容': '太好了！谢谢你，好心的樵夫！'
		},
		{
			'角色': '旁白',
			'内容': '美猴王向樵夫道了谢，就立刻顺着小路跑了过去。很快，他看到了一座云雾缭绕的山洞，空气里都是香香甜甜的味道。他知道，自己终于找到了！'
		}]
	},
	{
		'场景': 4,
		'场景剧本': [{
			'角色': '旁白',
			'内容': '孙悟空跟着仙童走进洞府深处，看见一位白胡子老爷爷正坐在高台上讲课，他知道，这位一定就是菩提祖师了。他赶紧跑上前去，恭恭敬敬地跪下磕头。'
		},
		{
			'角色': '菩提祖师',
			'内容': '你这猴头，从哪里来的？'
		},
		{
			'角色': '孙悟空',
			'内容': '师父，我从东胜神洲花果山水帘洞来，想跟您学习长生不老的本领！'
		},
		{
			'角色': '菩提祖师',
			'内容': '嗯……看你这么活泼，就给你取个名字，叫‘孙悟空’吧。'
		},
		{
			'角色': '孙悟空',
			'内容': '孙悟空？太好了！谢谢师父赐名！'
		},
		{
			'角色': '旁白',
			'内容': '就这样，孙悟空在洞里住了下来。可是师父教的，都只是些普通的法术。这一天，师父讲完课，故意大声问大家。'
		},
		{
			'角色': '菩提祖师',
			'内容': '悟空，你到底想学点什么？怎么教你什么，你都摇头？'
		},
		{
			'角色': '孙悟空',
			'内容': '（坚定地）师父，我只想学那个最厉害的，能长生不老的真本领！'
		},
		{
			'角色': '菩提祖师',
			'内容': '（突然变了脸色，大声呵斥）你这猢狲！这也不学，那也不学，真是太不听话了！'
		},
		{
			'角色': '孙悟空',
			'内容': '（有些委屈但依然坚持）师父，我不是不听话，我是真的……只想学那个本领！'
		},
		{
			'角色': '旁白',
			'内容': '菩提祖师拿起戒尺，走下高台。众师兄都以为孙悟空要挨打了，吓得不敢出声。祖师在悟空头上不轻不重地敲了三下，然后背着手，自己走进里屋，还把门关上了。'
		},
		{
			'角色': '众师兄',
			'内容': '哎呀！你这猴子，看你干的好事，把师父给气走了！'
		},
		{
			'角色': '众师兄',
			'内容': '这下完了，师父肯定不会再教我们了！都怪你！'
		},
		{
			'角色': '孙悟空',
			'内容': '（小声反驳）不是的！师父……师父他不是真的生气！'
		},
		{
			'角色': '旁白',
			'内容': '师兄们还在埋怨他，可聪明的悟空心里却明白了什么。他心想：'
		},
		{
			'角色': '孙悟空',
			'内容': '（内心独白）嘿嘿，我懂了！师父打我三下，是让我在三更半夜去找他！他背着手从后门进去，是教我悄悄地从后门进去！这一定是师父给我的秘密暗号！'
		},
		{
			'角色': '旁白',
			'内容': '到了晚上，悟空假装睡着了，等到半夜三更，他悄悄地爬起来，溜到后门一看，门果然留着一条缝。他蹑手蹑脚地走了进去，跪在了师父的床边。'
		},
		{
			'角色': '菩提祖师',
			'内容': '（故意用严肃的语气）谁在外面？三更半夜不睡觉，是想挨罚吗？'
		},
		{
			'角色': '孙悟空',
			'内容': '（小声又激动地）师父，是我，孙悟空！我遵守了我们的秘密约定，来向您学习真本领了！'
		},
		{
			'角色': '菩提祖师',
			'内容': '（温和地笑起来）呵呵，我就知道你会懂。快起来吧，聪明的猴头。你过来，我便将那长生妙法，悄悄说与你听。'
		},
		{
			'角色': '旁白',
			'内容': '于是，菩提祖师在悟空耳边悄悄说出了神奇的咒语，那咒语像唱歌一样好听。聪明的悟空一下子就记住了，他感觉身体里充满了暖洋洋的力量！'
		}]
	},
	{
		'场景': 5,
		'场景剧本': [{
			'角色': '旁白',
			'内容': '学会了七十二变和筋斗云之后，孙悟空开心极了。这天，他和师兄们在松树下玩耍，大家早就听说他学了新本领，都好奇地围了上来。'
		},
		{
			'角色': '众师兄',
			'内容': '悟空，听说你学了不得了的魔法，是真的吗？快变一个给我们看看，我们才信呢！'
		},
		{
			'角色': '孙悟空',
			'内容': '（挺起胸膛，有些得意）当然是真的！看我七十二变！你们说，想让我变成什么？'
		},
		{
			'角色': '众师兄',
			'内容': '就变成这棵大松树！'
		},
		{
			'角色': '孙悟空',
			'内容': '没问题！瞧好了！变！'
		},
		{
			'角色': '旁白',
			'内容': '悟空念动咒语，用手一指，只听“砰”的一声，他原地消失了，地上真的出现了一棵高大挺拔的松树！'
		},
		{
			'角色': '众师兄',
			'内容': '哇！真的变成一棵松树了！一模一样！'
		},
		{
			'角色': '众师兄',
			'内容': '太厉害了！好猴子！好猴子！大家快来拍手！'
		},
		{
			'角色': '旁白',
			'内容': '大家的欢笑声和鼓掌声太大了，惊动了正在房间里静修的菩提祖师。祖师拄着拐杖走了出来，看到大家闹哄哄的样子，脸色立刻严肃起来。'
		},
		{
			'角色': '菩提祖师',
			'内容': '（声音严肃）孙悟空！我教你的本领，是让你拿来当众炫耀的戏法吗？'
		},
		{
			'角色': '孙悟空',
			'内容': '（立刻变回原形，有点慌张和委屈）师父……我……我不是那个意思，我只是想让师兄们看看我的新本领，大家一起高兴高兴。'
		},
		{
			'角色': '菩提祖师',
			'内容': '（叹了口气）糊涂！真正的强大，不是为了赢得别人的掌声，而是用它来做对的事情。你今天为了炫耀而变，明天就可能为了炫耀去闯祸！'
		},
		{
			'角色': '孙悟空',
			'内容': '（低下头，真心知错）师父，我错了。我不该这么轻浮，不该炫耀的。'
		},
		{
			'角色': '菩提祖师',
			'内容': '你明白了就好。你的本领已经学成，是时候回家了。'
		},
		{
			'角色': '孙悟空',
			'内容': '（急忙抬头）师父，不要赶我走！我再也不敢了！求您留下我吧！'
		},
		{
			'角色': '菩提祖师',
			'内容': '（摇了摇头，语气坚定但温和）你必须走。你天性活泼，留在这里，早晚会给师门惹来大祸。去吧，回到你的花果山去。'
		},
		{
			'角色': '菩提祖师',
			'内容': '但是记住，以后无论惹出什么祸事，都不能说我是你的师父。这是我对你最后的保护。'
		},
		{
			'角色': '旁白',
			'内容': '孙悟空知道师父的心意已决，他含着眼泪，向师父重重地磕了三个头。'
		},
		{
			'角色': '孙悟空',
			'内容': '（声音哽咽）弟子明白！师父保重！我走啦！筋斗云，起！'
		},
		{
			'角色': '旁白',
			'内容': '这筋斗云可真快呀，嗖的一下，就像坐上了最快的火箭，眨眼间，孙悟空就飞得无影无踪了。他终于学成本领，要回到他日思夜想的花果山啦！'
		}]
	}]
}
    script_proofreader = {
        '剧本审查': [{
            '场景': 1,
            '审查结果': '通过',
            '问题清单': [{
                '维度': '综合评价',
                '问题描述': '剧本在目标一致性、信息平衡、角色一致性和受众适宜性四个维度上均表现出色，完全符合儿童剧本的审查标准。',
                '修改建议': '剧本审查通过，可移交下一环节进行配音和制作。'
            }]
        },
            {
                '场景': 2,
                '审查结果': '通过',
                '问题清单': [{
                    '维度': '整体评估',
                    '问题描述': '剧本完全符合改编大纲的要求，且满足所有审查清单标准。',
                    '修改建议': '无需修改，准予通过。可移交下一环节（如配音、动画制作等）。'
                }]
            },
            {
                '场景': 3,
                '审查结果': '需修改',
                '问题清单': [{
                    '维度': '角色一致性',
                    '问题描述': '在此场景中，美猴王自我介绍为“孙悟空”。根据原著情节，“孙悟空”这个名字是由菩提祖师在下一场景中赐予的。在本场景中提前使用该名字，造成了情节与角色身份的前后矛盾。',
                    '修改建议': '建议将孙悟空的自我介绍修改为符合其当前身份的称呼。例如，将“我叫孙悟空”改为“我还没有名字，大家都叫我美猴王”或直接说“我是从花果山来的美猴王”。这样既能保持角色身份的连贯性，也能为下一场景祖师赐名埋下伏笔。'
                }]
            },
            {
                '场景': 4,
                '审查结果': '需修改',
                '问题清单': [{
                    '维度': '受众适宜性',
                    '问题描述': '众师兄的对白使用了直接的指责性语言（“都怪你！”），虽然其作用是反衬悟空的聪明，但对于儿童受众，这种直接的同伴指责可能会传递负面情绪，与剧本整体积极、合作的风格略有偏差。',
                    '修改建议': '建议将众师兄的台词从直接指责改为表达担忧和不解。例如，可以将“这下完了，师父肯定不会再教我们了！都怪你！”修改为“这可怎么办呀？师父真的生气了，以后我们该怎么学本领呢？”。这样既能表现出他们的误解和紧张气氛，又能避免直接的负面指责，使情节冲突更温和。'
                },
                    {
                        '维度': '角色一致性',
                        '问题描述': '菩提祖师在深夜考验孙悟空时，台词“谁在外面？三更半夜不睡觉，是想挨罚吗？”略显严厉，与其内心已经认可悟空智慧的状态稍有不符，可能会让儿童观众感到困惑。',
                        '修改建议': '建议调整菩提祖师的语气和台词，使其更符合“考验”而非“真生气”的状态。可修改为：“（故意装作严肃）是谁呀？这么晚了还不睡，难道是想来偷学我的本领？”这样既保持了考验的神秘感，又带有一丝不易察觉的 playful（顽皮）感，更符合祖师的智者形象。'
                    }]
            },
            {
                '场景': 5,
                '审查结果': '通过',
                '问题清单': []
            }]
    }
    refine_script = {
        '剧本': [{
            '场景': 1,
            '场景剧本': [{
                '角色': '旁白',
                '内容': '在遥远的东胜神洲，有一座美丽的花果山。山上住着一群快乐的小猴子，还有一只从石头里蹦出来的石猴。这天，大家在小溪边玩耍，忽然听到一阵巨大的响声，他们顺着声音找了过去。'
            },
                {
                    '角色': '猴子们',
                    '内容': '（惊叹）哗啦啦！好大的瀑布啊！声音真响！'
                },
                {
                    '角色': '老猿猴',
                    '内容': '孩子们，我们祖祖辈辈都说，谁有本事跳过这瀑布，找到水的源头，还能平安回来，我们就拜他当大王！'
                },
                {
                    '角色': '猴子们',
                    '内容': '（害怕）当大王？不行不行，太危险了！水这么急，里面肯定有妖怪！'
                },
                {
                    '角色': '猴子们',
                    '内容': '是啊，万一被大水冲走了怎么办？我可不敢去！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '（不服气地）哼，真没出息！连试一试的胆子都没有吗？'
                },
                {
                    '角色': '猴子们',
                    '内容': '（被激将）你……你敢说我们没出息？那你去啊！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '（坚定地）去就去！我今天就跳进去看看！要是我在里面找到了一个能挡风躲雨的好地方，你们就都要拜我做大王，听我的话！'
                },
                {
                    '角色': '猴子们',
                    '内容': '（犹豫但又期待）好……好吧！你要是真能找到一个家，我们就认你当大王！'
                },
                {
                    '角色': '旁白',
                    '内容': '石猴说完，深吸一口气，闭上眼睛，向着白茫茫的水帘猛地跳了过去！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '看我的！我跳进去啦！'
                },
                {
                    '角色': '猴子们',
                    '内容': '（紧张地大喊）啊！他真的跳进去了！'
                },
                {
                    '角色': '旁白',
                    '内容': '石猴穿过凉凉的水帘，睁开眼睛一看，瀑布后面竟然别有洞天，根本没有水，而是一个亮晶晶的大山洞！'
                },
                {
                    '角色': '孙悟空',
                    '内容': '（声音从瀑布后传来，充满兴奋）哇！快来呀！这里面是个大宝贝！一个不用怕下雨的家！'
                },
                {
                    '角色': '猴子们',
                    '内容': '（焦急地问）里面是什么？你还好吗？没有妖怪吧？'
                },
                {
                    '角色': '孙悟空',
                    '内容': '好得很！这里有石头的桌子和凳子，还有软软的石床！'
                },
                {
                    '角色': '猴子们',
                    '内容': '真的吗？还有什么？'
                },
                {
                    '角色': '孙悟空',
                    '内容': '哈哈，墙上还写着字呢，叫‘水帘洞’！这简直就是为我们准备的家呀！大家快进来！'
                },
                {
                    '角色': '旁白',
                    '内容': '听到石猴的呼唤，小猴子们又惊喜又佩服，一个接一个，勇敢地跳进了瀑布。大家看到这么好的新家，都开心地欢呼起来，一起遵守约定，拜又聪明又勇敢的石猴为大王，还给他取了个威风的名字——美猴王！'
                }]
        },
            {
                '场景': 2,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '自从住进了水帘洞，美猴王和猴子们每天都过得特别开心。可是有一天，当大家正在草地上追逐打闹时，美猴王却自己坐在一块大石头上，长长地叹了一口气。'
                },
                    {
                        '角色': '猴子们',
                        '内容': '大王，快来呀！我们来玩捉迷藏吧！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（看着大家，小声地）唉……真希望这样的日子永远不要结束。'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '（跑过来）大王，你怎么了？为什么不开心呀？我们不是玩得好好的吗？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '我们每天都很快乐，可是……我在担心，如果有一天我们都老了，跳不动了，那该怎么办呢？'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '（不服气地）才不会呢！我们永远都会这么开心的！老了也可以一起玩呀！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（摇摇头，很坚定地）不行！我不能让这种事情发生。我希望大家的快乐永远不会变老，永远不会消失！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '就在大家不知道该怎么安慰大王时，猴群里一位年纪最大的老猴子走了过来。'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '大王，您是在为大家的快乐担心啊。我听说，有一个办法，能让快乐永远不结束！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（立刻站起来）什么办法？快告诉我！'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '我听说，在很远很远的地方，住着一位有魔法的神仙。他有长生不老的本领！'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '哇！长生不老？那是不是就意味着可以永远玩下去了？'
                    },
                    {
                        '角色': '老猿猴',
                        '内容': '没错！只要大王能找到他，学习他的本领，我们就再也不用担心快乐会消失了。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（眼睛里闪着光）好！不管有多远，多困难，我一定要找到这位神仙！'
                    },
                    {
                        '角色': '猴子们',
                        '内容': '大王，我们跟你一起去！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（拍拍胸脯）不，路途太危险了。你们在家里等我，我一定会把‘永远的快乐’带回来！我明天就出发！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '为了守护大家的快乐，勇敢的美猴王下定决心，要独自出海，去寻找那位能教他长生不老魔法的神仙。'
                    }]
            },
            {
                '场景': 3,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '美猴王坐着自己做的小木筏，漂过了一个又一个大海，走过了一座又一座高山。他找啊找啊，找了很久很久。这一天，他来到一座云雾缭绕的大山里，正走着，忽然听到一阵清脆的歌声。'
                },
                    {
                        '角色': '樵夫',
                        '内容': '（唱歌）砍柴呀，真快乐，山里住着老神仙，教会我呀唱新歌，烦恼见了都躲着。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '美猴王心里一喜，以为终于找到了神仙。他悄悄拨开树丛，发现唱歌的原来是一个正在砍柴的小哥哥。'
                    },
                    {
                        '角色': '美猴王',
                        '内容': '（激动地跳出来）老神仙！我可找到你了！'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '（吓了一大跳，后退一步）哎呀！你……你是谁？你吓死我了！我不是神仙！'
                    },
                    {
                        '角色': '美猴王',
                        '内容': '（有些失望）你不是？可你唱的歌里明明有神仙呀！你一定认识他，对不对？'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '（警惕地看着他）我……我为什么要告诉你？神仙爷爷不喜欢陌生人来打扰他。你快走吧。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '孙悟空心里咯噔一下，他找了那么久，难道就要在这里失败了吗？他心里又着急又委屈。'
                    },
                    {
                        '角色': '美猴王',
                        '内容': '（恳切地）求求你了！我是从很远很远的花果山来的美猴王。我漂洋过海，走了好久好久的路，就是想拜神仙为师，学长生不老的本领，好回去保护我的猴子猴孙们！'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '（被孙悟空的真诚打动了）原来……你是为了保护大家才来学本领的。唉，你这份心意真了不起。不像我，还得照顾年迈的妈妈，没法去学仙法。'
                    },
                    {
                        '角色': '美猴王',
                        '内容': '你真是个孝顺的好孩子！那你愿意告诉我神仙爷爷住在哪里了吗？'
                    },
                    {
                        '角色': '樵夫',
                        '内容': '（笑着点头）当然！你顺着这条小路一直往南走，就能看到一个亮晶晶的山洞，那就是神仙的家了。记住，见到神仙一定要有礼貌哦！'
                    },
                    {
                        '角色': '美猴王',
                        '内容': '太好了！谢谢你，好心的樵夫！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '美猴王向樵夫道了谢，就立刻顺着小路跑了过去。很快，他看到了一座云雾缭绕的山洞，空气里都是香香甜甜的味道。他知道，自己终于找到了！'
                    }]
            },
            {
                '场景': 4,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '孙悟空跟着仙童走进洞府深处，看见一位白胡子老爷爷正坐在高台上讲课，他知道，这位一定就是菩提祖师了。他赶紧跑上前去，恭恭敬敬地跪下磕头。'
                },
                    {
                        '角色': '菩提祖师',
                        '内容': '你这猴头，从哪里来的？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '师父，我从东胜神洲花果山水帘洞来，想跟您学习长生不老的本领！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '嗯……看你这么活泼，就给你取个名字，叫‘孙悟空’吧。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '孙悟空？太好了！谢谢师父赐名！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '就这样，孙悟空在洞里住了下来。可是师父教的，都只是些普通的法术。这一天，师父讲完课，故意大声问大家。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '悟空，你到底想学点什么？怎么教你什么，你都摇头？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（坚定地）师父，我只想学那个最厉害的，能长生不老的真本领！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（突然变了脸色，大声呵斥）你这猢狲！这也不学，那也不学，真是太不听话了！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（有些委屈但依然坚持）师父，我不是不听话，我是真的……只想学那个本领！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '菩提祖师拿起戒尺，走下高台。众师兄都以为孙悟空要挨打了，吓得不敢出声。祖师在悟空头上不轻不重地敲了三下，然后背着手，自己走进里屋，还把门关上了。'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '哎呀！你把师父气走了！这可怎么办呀？'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '师父真的生气了，以后我们该怎么学本领呢？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（小声反驳）不是的！师父……师父他不是真的生气！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '师兄们还在埋怨他，可聪明的悟空心里却明白了什么。他心想：'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（内心独白）嘿嘿，我懂了！师父打我三下，是让我在三更半夜去找他！他背着手从后门进去，是教我悄悄地从后门进去！这一定是师父给我的秘密暗号！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '到了晚上，悟空假装睡着了，等到半夜三更，他悄悄地爬起来，溜到后门一看，门果然留着一条缝。他蹑手蹑脚地走了进去，跪在了师父的床边。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（故意装作严肃）是谁呀？这么晚了还不睡，难道是想来偷学我的本领？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（小声又激动地）师父，是我，孙悟空！我遵守了我们的秘密约定，来向您学习真本领了！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（温和地笑起来）呵呵，我就知道你会懂。快起来吧，聪明的猴头。你过来，我便将那长生妙法，悄悄说与你听。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '于是，菩提祖师在悟空耳边悄悄说出了神奇的咒语，那咒语像唱歌一样好听。聪明的悟空一下子就记住了，他感觉身体里充满了暖洋洋的力量！'
                    }]
            },
            {
                '场景': 5,
                '场景剧本': [{
                    '角色': '旁白',
                    '内容': '学会了七十二变和筋斗云之后，孙悟空开心极了。这天，他和师兄们在松树下玩耍，大家早就听说他学了新本领，都好奇地围了上来。'
                },
                    {
                        '角色': '众师兄',
                        '内容': '悟空，听说你学了不得了的魔法，是真的吗？快变一个给我们看看，我们才信呢！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（挺起胸膛，有些得意）当然是真的！看我七十二变！你们说，想让我变成什么？'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '就变成这棵大松树！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '没问题！瞧好了！变！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '悟空念动咒语，用手一指，只听“砰”的一声，他原地消失了，地上真的出现了一棵高大挺拔的松树！'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '哇！真的变成一棵松树了！一模一样！'
                    },
                    {
                        '角色': '众师兄',
                        '内容': '太厉害了！好猴子！好猴子！大家快来拍手！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '大家的欢笑声和鼓掌声太大了，惊动了正在房间里静修的菩提祖师。祖师拄着拐杖走了出来，看到大家闹哄哄的样子，脸色立刻严肃起来。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（声音严肃）孙悟空！我教你的本领，是让你拿来当众炫耀的戏法吗？'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（立刻变回原形，有点慌张和委屈）师父……我……我不是那个意思，我只是想让师兄们看看我的新本领，大家一起高兴高兴。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（叹了口气）糊涂！真正的强大，不是为了赢得别人的掌声，而是用它来做对的事情。你今天为了炫耀而变，明天就可能为了炫耀去闯祸！'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（低下头，真心知错）师父，我错了。我不该这么轻浮，不该炫耀的。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '你明白了就好。你的本领已经学成，是时候回家了。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（急忙抬头）师父，不要赶我走！我再也不敢了！求您留下我吧！'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '（摇了摇头，语气坚定但温和）你必须走。你天性活泼，留在这里，早晚会给师门惹来大祸。去吧，回到你的花果山去。'
                    },
                    {
                        '角色': '菩提祖师',
                        '内容': '但是记住，以后无论惹出什么祸事，都不能说我是你的师父。这是我对你最后的保护。'
                    },
                    {
                        '角色': '旁白',
                        '内容': '孙悟空知道师父的心意已决，他含着眼泪，向师父重重地磕了三个头。'
                    },
                    {
                        '角色': '孙悟空',
                        '内容': '（声音哽咽）弟子明白！师父保重！我走啦！筋斗云，起！'
                    },
                    {
                        '角色': '旁白',
                        '内容': '这筋斗云可真快呀，嗖的一下，就像坐上了最快的火箭，眨眼间，孙悟空就飞得无影无踪了。他终于学成本领，要回到他日思夜想的花果山啦！'
                    }]
            }]
    }
    refine_script = remove_parentheses_in_script(refine_script)
    Emotion = {
        '语气标注': [{
            '场景': 1,
            '场景剧本': [{
                '台词位置': 0,
                '语气指导': '（温和、亲切地讲故事）语速平稳，像在讲一个神奇的童话故事。说到“巨大的响声”时，语气略带悬念，引导听众的好奇心。'
            },
                {
                    '台词位置': 1,
                    '语气指导': '（七嘴八舌，充满惊奇和兴奋）声音响亮，语调上扬，带着发现新大陆般的惊喜感。可以想象小猴子们指着瀑布，大声感叹的样子。'
                },
                {
                    '台词位置': 2,
                    '语气指导': '（沉稳、庄重地宣布）语速放慢，声音浑厚有力，像在讲述一个古老的传说，带着引导和激励的意味。'
                },
                {
                    '台词位置': 3,
                    '语气指导': '（害怕、退缩地议论）声音变小，语速加快，带着明显的胆怯和担忧。七嘴八舌地表达“不行不行”，充满对未知的恐惧。'
                },
                {
                    '台词位置': 4,
                    '语气指导': '（附和，害怕得发抖）语气非常肯定自己的“不敢”，声音可以带一点点颤抖，强调对危险的恐惧。'
                },
                {
                    '台词位置': 5,
                    '语气指导': '（不屑、骄傲地）一声轻哼，带着明显的瞧不起。语调上扬，充满挑战和自信，与小猴子们的胆小形成鲜明对比。'
                },
                {
                    '台词位置': 6,
                    '语气指导': '（被激怒，不服气地反驳）一开始有点结巴，表示被说中了心事，接着转为理直气壮的激将法，声音提高，带着“你行你上”的挑衅。'
                },
                {
                    '台词位置': 7,
                    '语气指导': '（豪情万丈，信心十足）毫不犹豫，声音洪亮，充满英雄气概。说“去就去”时干脆利落，说到“拜我做大王”时，带着不容置疑的霸气。'
                },
                {
                    '台词位置': 8,
                    '语气指导': '（半信半疑，勉强地答应）开头有些犹豫，但还是被石猴的气势镇住，最终带着一点点期待和看好戏的心情答应下来。'
                },
                {
                    '台词位置': 9,
                    '语气指导': '（紧张、激动地描述）语速加快，语气中带着紧张感和期待感，强调“猛地”这个词，营造出惊险刺激的氛围。'
                },
                {
                    '台词位置': 10,
                    '语气指导': '（大喊，兴奋又勇敢）声音响亮，充满力量和冲劲，可以带一点回声的感觉，表现出他正向瀑布冲去。'
                },
                {
                    '台词位置': 11,
                    '语气指导': '（集体发出惊呼）声音充满震惊和不敢相信，语调急促，大家的声音要重叠在一起，形成惊呼的效果。'
                },
                {
                    '台词位置': 12,
                    '语气指导': '（充满惊喜和神奇感）语气从紧张转为豁然开朗的惊喜。描述山洞时，语调要轻快、明亮，带着发现新世界的奇妙感觉。'
                },
                {
                    '台词位置': 13,
                    '语气指导': '（欣喜若狂，大声呼喊）声音带着发现宝藏的巨大喜悦和激动。语气热情，语速快，像是在向外面的伙伴们炫耀和分享。可以带一点点洞穴里的回音效果。'
                },
                {
                    '台词位置': 14,
                    '语气指导': '（急切、担忧地追问）七嘴八舌地提问，语气中既有好奇，又有挥之不去的担心。问题一个接一个，显得非常急切。'
                },
                {
                    '台词位置': 15,
                    '语气指导': '（得意、兴奋地介绍）语气非常肯定，充满自豪感。描述石床石凳时，带着分享的快乐，好像在展示自己的新家。'
                },
                {
                    '台词位置': 16,
                    '语气指导': '（好奇心被点燃，充满期待）担忧减少，好奇和兴奋的情绪占了上风。声音变得雀跃，追问的语气充满渴望。'
                },
                {
                    '台词位置': 17,
                    '语气指导': '（开怀大笑，热情地邀请）开头是爽朗的大笑。语气自豪又热情，充满归属感。“快进来”三个字要特别有号召力，像一个真正的领袖在召唤他的子民。'
                },
                {
                    '台词位置': 18,
                    '语气指导': '（温和、欣慰地总结）语速平稳，语气中带着喜悦和满足感。描述猴子们欢呼时，语气要上扬，充满感染力。最后说出“美猴王”时，语调要稍微加重，带着赞叹和一点点威风的感觉，为故事画上圆满的句号。'
                }]
        },
            {
                '场景': 2,
                '场景剧本': [{
                    '台词位置': 0,
                    '语气指导': '【旁白，亲切温和，带转折】语速平稳，带着微笑讲述开心的生活。到“可是有一天”时，语速放慢，语气转为轻柔，带一点悬念，引出美猴王的反常。'
                },
                    {
                        '台词位置': 1,
                        '语气指导': '【猴群，活泼响亮】非常开心的呼喊，声音清脆，充满活力和热情，像一群无忧无虑的孩子在邀请伙伴玩耍。'
                    },
                    {
                        '台词位置': 2,
                        '语气指导': '【孙悟空，忧愁感伤】声音低沉，语速慢。开头的“唉”要叹得长一些，充满孩子气的烦恼。整句话带着对美好时光可能流逝的担心。'
                    },
                    {
                        '台词位置': 3,
                        '语气指导': '【猴群，困惑关心】从刚才的活泼转为不解和关切，语速放慢，带着真诚的疑问，想知道大王为什么不开心。'
                    },
                    {
                        '台词位置': 4,
                        '语气指导': '【孙悟空，认真忧虑】语气真诚，坦白自己的烦恼。“可是”之后，语调更沉重，语速变慢，表达出对“变老”这个未知问题的深切担忧。'
                    },
                    {
                        '台词位置': 5,
                        '语气指导': '【猴群，天真乐观】语气轻松、肯定，带着孩子气的反驳和安慰。他们无法理解深层的烦恼，只是单纯地相信快乐会永远持续。'
                    },
                    {
                        '台词位置': 6,
                        '语气指导': '【孙悟空，坚定果断】情绪突然激昂起来，音量提高，语速加快。“不行！”两个字要短促有力，展现出他作为猴王不愿屈服的决心和担当。'
                    },
                    {
                        '台词位置': 7,
                        '语气指导': '【旁白，平缓铺垫】语气平缓，营造出一种“解围者即将登场”的氛围，为老猴子的出场做好铺垫。'
                    },
                    {
                        '台词位置': 8,
                        '语气指导': '【老猿猴，沉稳智慧】声音苍老但清晰有力，语速不疾不徐。语气中带着对猴王的理解和赞许，像一位看透一切的长者。'
                    },
                    {
                        '台词位置': 9,
                        '语气指导': '【孙悟空，急切渴望】情绪由忧愁转为惊喜，像抓住了救命稻草。音调立刻抬高，语速非常快，充满了希望和期待。'
                    },
                    {
                        '台词位置': 10,
                        '语气指导': '【老猿猴，神秘向往】像在讲述一个古老的传说，语速放慢，语气带着一丝神秘感。说到“神仙”和“长生不老”时，语调中要充满敬畏。'
                    },
                    {
                        '台词位置': 11,
                        '语气指导': '【猴群，惊喜兴奋】齐声发出惊叹，“哇！”可以拖长一点。语气非常兴奋，充满了孩子对“永远玩耍”这个美好前景的无限向往。'
                    },
                    {
                        '台词位置': 12,
                        '语气指导': '【老猿猴，肯定鼓励】语气非常确定，声音沉稳。“没错！”说得很有力，给猴子们信心。后半句带着对孙悟空的期许和信任，引导他做出决定。'
                    },
                    {
                        '台词位置': 13,
                        '语气指导': '【孙悟空，决心万丈】声音洪亮，充满力量，掷地有声。“好！”字要短促有力。整句话语调激昂，表达出他排除万难、一往无前的英雄气概。'
                    },
                    {
                        '台词位置': 14,
                        '语气指导': '【猴群，团结拥护】异口同声，语气急切而真诚，表达对大王的忠诚和想要同甘共苦的决心。'
                    },
                    {
                        '台词位置': 15,
                        '语气指导': '【孙悟空，果断且有担当】先用“不”坚决地拒绝，展现领袖的决断力。随后语气变得温和而坚定，充满对同伴的爱护。最后一句是对大家的郑重承诺，充满自信。'
                    },
                    {
                        '台词位置': 16,
                        '语气指导': '【旁白，赞扬肯定】语气温和而庄重，带着对美猴王勇气的赞许。语速平稳，为本场景收尾，并预告新征程的开始。'
                    }]
            },
            {
                '场景': 3,
                '场景剧本': [{
                    '台词位置': 0,
                    '语气指导': '亲切平稳的讲述感。语速稍慢，强调“很久很久”来表现旅途的漫长。说到“忽然听到”时，语调略微上扬，带出神秘和期待感。'
                },
                    {
                        '台词位置': 1,
                        '语气指导': '语调轻快，充满天真烂漫的快乐。声音清亮，带着歌唱的韵律感，像是在自得其乐地哼唱，悠闲自在。'
                    },
                    {
                        '台词位置': 2,
                        '语气指导': '语气中带着美猴王的喜悦和激动。说到“心里一喜”时，声音上扬。在“原来是”之后，语速放慢，带有一种恍然大悟和略带一点小失望的感觉。'
                    },
                    {
                        '台词位置': 3,
                        '语气指导': '声音响亮，充满极度的兴奋和急切！像是找到了救星一样，语速快，语调高昂，带着孩子气的冒失和天真。'
                    },
                    {
                        '台词位置': 4,
                        '语气指导': '惊慌失措。第一声“哎呀”要短促有力，表现出被吓了一大跳。后面的话语速快，带点结巴，声音发抖，极力撇清关系。'
                    },
                    {
                        '台词位置': 5,
                        '语气指导': '从惊讶转为急切的追问。第一句带着大大的疑惑，后面语速变快，像连珠炮一样发问，充满了不放弃的劲头，句末“对不对”要重读，带着强烈的期盼。'
                    },
                    {
                        '台词位置': 6,
                        '语气指导': '语气带着防备和犹豫。开头“我……”要拖长一点。后面说话的语气有点强硬，但不是真的凶，更像是一个善良的人在努力保护自己尊敬的人。'
                    },
                    {
                        '台词位置': 7,
                        '语气指导': '语调低沉下来，语速放慢，营造出紧张和失落的气氛。要清晰地传达出孙悟空内心的“咯噔”感，以及那种“又着急又委屈”的复杂情绪。'
                    },
                    {
                        '台词位置': 8,
                        '语气指导': '真诚、恳切，带着哭腔和哀求。开头“求求你了”非常急切，后面讲述来历时语速放缓，充满感情，最后说到“保护我的猴子猴孙们”时，语气变得坚定而充满责任感。'
                    },
                    {
                        '台词位置': 9,
                        '语气指导': '从恍然大悟转为感动和敬佩。叹息声“唉”要真诚，带有一丝羡慕和对自己情况的无奈。夸赞孙悟空时要发自内心，语气温和而充满赞许。'
                    },
                    {
                        '台词位置': 10,
                        '语气指导': '真诚地赞美，带着同理心。然后话锋一转，带着小心翼翼的期待和希望再次提问，声音放轻，充满渴望。'
                    },
                    {
                        '台词位置': 11,
                        '语气指导': '热情、爽朗。“当然！”要干脆有力。指路时语速清晰，充满善意。最后一句叮嘱要像个大哥哥一样，亲切又认真。'
                    },
                    {
                        '台词位置': 12,
                        '语气指导': '声音里充满了压抑不住的喜悦和感激！语调高昂，语速快，充满活力和兴奋感。“太好了”要喊出来，充满力量。'
                    },
                    {
                        '台词位置': 13,
                        '语气指导': '语气轻快，带着故事即将进入高潮的激动感。描述山洞时，语速放慢，营造一种神奇、梦幻的氛围。最后一句“自己终于找到了！”语调要上扬、肯定，为美猴王感到由衷的高兴。'
                    }]
            },
            {
                '场景': 4,
                '场景剧本': [{
                    '台词位置': 0,
                    '语气指导': '（旁白）语速平缓，声音亲切温暖，带着一点点神秘感，引导小朋友进入故事。描述祖师时，语气略带崇敬。'
                },
                    {
                        '台词位置': 1,
                        '语气指导': '（菩提祖师）语气威严，语速稍慢，带着长者的审视感，声音沉稳有力，但不是真的在生气。'
                    },
                    {
                        '台词位置': 2,
                        '语气指导': '（孙悟空）充满期待和尊敬，语速稍快，声音响亮而真诚，把自己的来历和目的说得清清楚楚。'
                    },
                    {
                        '台词位置': 3,
                        '语气指导': '（菩提祖师）声音放缓，带一点沉吟和思考的感觉（“嗯……”），后面变得温和，带着一丝对悟空灵性的赞许。'
                    },
                    {
                        '台词位置': 4,
                        '语气指导': '（孙悟空）惊喜地重复名字，然后语调上扬，充满孩子气的开心和激动，声音响亮，充满感激。'
                    },
                    {
                        '台词位置': 5,
                        '语气指导': '（旁白）语气平稳，讲述故事的口吻。说到“故意大声问大家”时，可以稍微加重语气，为接下来的情节做铺垫。'
                    },
                    {
                        '台词位置': 6,
                        '语气指导': '（菩提祖师）声音洪亮，带着公开质问的意味，语气显得有些不耐烦和严厉，但这是演给其他弟子看的。'
                    },
                    {
                        '台词位置': 7,
                        '语气指导': '（孙悟空）语气坚定执着，充满渴望，声音响亮，强调“最厉害的”和“真本领”。'
                    },
                    {
                        '台词位置': 8,
                        '语气指导': '（菩提祖师）语气严厉，大声呵斥，听起来像是真的生气了，但要控制好力度，是“演”出来的愤怒。'
                    },
                    {
                        '台词位置': 9,
                        '语气指导': '（孙悟空）语气急切，带一点委屈和辩解，但目标非常明确，说到最后一句时又变得很坚定。'
                    },
                    {
                        '台词位置': 10,
                        '语气指导': '（旁白）语速放慢，语气变得紧张起来，营造出一种“大事不妙”的氛围。描述敲头的动作要清晰。'
                    },
                    {
                        '台词位置': 11,
                        '语气指导': '（众师兄）声音惊慌，带着埋怨和不知所措的语气，语速快，像是在七嘴八舌地议论。'
                    },
                    {
                        '台词位置': 12,
                        '语气指导': '（众师兄）语气发愁，带着哭腔，充满了对未来的担忧，有点孩子气的抱怨。'
                    },
                    {
                        '台词位置': 13,
                        '语气指导': '（孙悟空）急切地反驳，但声音不大，更像是在自言自语，带着思考和不确定，但又有一丝肯定。'
                    },
                    {
                        '台词位置': 14,
                        '语气指导': '（旁白）语气一转，从紧张的氛围中跳出，带上一点赞许和神秘感，暗示悟空的聪明，引导听众进入悟空的内心。'
                    },
                    {
                        '台词位置': 15,
                        '语气指导': '（孙悟空-内心独白）压低声音，带着点小得意和狡黠的笑声（“嘿嘿”），语速轻快，像是发现了一个大秘密一样兴奋。'
                    },
                    {
                        '台词位置': 16,
                        '语气指导': '（旁白）声音放轻，语速放缓，营造出夜晚的安静和悟空行动的鬼祟感，带着点小悬念。'
                    },
                    {
                        '台词位置': 17,
                        '语气指导': '（菩提祖师）声音压低，像是刚被吵醒，但语气里没有真的责备，反而带着一丝不易察觉的笑意和考验的意味。'
                    },
                    {
                        '台词位置': 18,
                        '语气指导': '（孙悟空）压低声音但难掩兴奋，语气里充满了“我答对啦”的小骄傲，同时又非常尊敬。'
                    },
                    {
                        '台词位置': 19,
                        '语气指导': '（菩提祖师）温和慈爱的笑声（“呵呵”），语气里满是欣慰和赞许，声音亲切又带着传授秘法的神秘感。'
                    },
                    {
                        '台词位置': 20,
                        '语气指导': '（旁白）声音轻柔，充满神奇色彩，像是在分享一个美妙的秘密。结尾要给人一种充满希望和力量的感觉。'
                    }]
            },
            {
                '场景': 5,
                '场景剧本': [{
                    '台词位置': 0,
                    '语气指导': '（语速平稳，语气亲切，带着讲故事的微笑）介绍一个开心的场景，为接下来的热闹氛围做铺垫。'
                },
                    {
                        '台词位置': 1,
                        '语气指导': '（好奇又兴奋，七嘴八舌地）带着孩子们特有的、天真的挑衅感，语速可以稍快，催促悟空表演。'
                    },
                    {
                        '台词位置': 2,
                        '语气指导': '（得意洋洋，拍着胸脯）声音响亮自信，充满表现欲，甚至有点小小的炫耀。'
                    },
                    {
                        '台词位置': 3,
                        '语气指导': '（异口同声，充满期待）大家一起大声喊出来，好像在玩一个有趣的游戏。'
                    },
                    {
                        '台词位置': 4,
                        '语气指导': '（充满自信，干脆利落）“变”字要短促有力，像一个神奇的魔法口令。'
                    },
                    {
                        '台词位置': 5,
                        '语气指导': '（语速稍放慢，营造神秘感）“砰”的一声后稍作停顿，再用惊喜、赞叹的语气描述松树的出现。'
                    },
                    {
                        '台词位置': 6,
                        '语气指导': '（惊叹，不敢相信）“哇”要拖长音，声音高昂，充满发现新大陆一样的喜悦。'
                    },
                    {
                        '台词位置': 7,
                        '语气指导': '（欢呼雀跃，真心赞美）语气非常热烈，可以加上拍手的声音，把快乐的气氛推向高潮。'
                    },
                    {
                        '台词位置': 8,
                        '语气指导': '（语气由轻松转为严肃）语速放慢，为祖师的出场铺垫紧张感，暗示快乐的时光被打断了。'
                    },
                    {
                        '台词位置': 9,
                        '语气指导': '（严厉，声音低沉）语速不快，但字字清晰，带着压迫感和不悦，充满了长辈的责备和失望。'
                    },
                    {
                        '台词位置': 10,
                        '语气指导': '（吓了一跳，声音立刻变小）有点结巴，语气慌乱又委屈，像做错事被抓包的孩子一样试图解释。'
                    },
                    {
                        '台词位置': 11,
                        '语气指导': '（痛心疾首，恨铁不成钢）“糊涂”二字要严厉，后面的话语重心长，是在教导一个重要的人生道理。'
                    },
                    {
                        '台词位置': 12,
                        '语气指导': '（低着头，声音充满悔意）小声地，诚恳地认错，已经完全认识到自己的错误。'
                    },
                    {
                        '台词位置': 13,
                        '语气指导': '（语气稍微缓和但依然严肃）带着一种不容置疑的决绝，平静地宣布一个重大决定。'
                    },
                    {
                        '台词位置': 14,
                        '语气指导': '（急切，带着哭腔）声音里充满了恳求和慌张，害怕被师父赶走。'
                    },
                    {
                        '台词位置': 15,
                        '语气指导': '（语气坚定，不带情绪）像在陈述一个无法改变的事实，但深处藏着一丝对悟空未来的担忧和无奈。'
                    },
                    {
                        '台词位置': 16,
                        '语气指导': '（语气极其严肃郑重）语速放慢，一字一顿，强调这是最后的忠告，话语中透露出一种深沉的、不舍的保护。'
                    },
                    {
                        '台词位置': 17,
                        '语气指导': '（语气沉重，充满同情和伤感）描述悟空的动作时要放慢语速，营造离别的悲伤氛围。'
                    },
                    {
                        '台词位置': 18,
                        '语气指导': '（强忍着泪水，声音哽咽但努力保持坚定）“筋斗云，起！”要大声喊出来，既是告别，也是给自己打气。'
                    },
                    {
                        '台词位置': 19,
                        '语气指导': '（语气由伤感立刻转为惊叹和轻快）用活泼的语气描述筋斗云的速度，最后一句充满期待和喜悦，开启新篇章。'
                    }]
            }]
    }
    script_with_emotion = combine_script_and_emotion(refine_script, Emotion)
    output_lines = []
    for scene in script_with_emotion['剧本']:
        output_lines.append(f"场景：{scene['场景']}")
        for line in scene['场景剧本']:
            role = line['角色']
            content = line['内容']
            output_lines.append(f"{role}：{content}")
        output_lines.append("---"*70)
    str_script =  "\n".join(output_lines)
    return str_script, gr.update(interactive=True), gr.update(
            open=True), "剧本生成成功，请继续进行角色声音配对。", script_with_emotion
"""
输入 (inputs):
    - character_json_state: 存储有角色信息的不可见状态组件。
    - generated_script_json_state: 存储有已生成剧本的不可见状态组件。
    输出 (outputs):
    - btn_generate_tts: 激活“生成TTS”按钮，以进行最终的音频合成。
    - Accordion_Role: 确保“角色 Section”展开，以显示即将更新的配音建议。
    - process_status_display: 更新“处理状态显示”，反馈声音配对完成的状态。
    - character_voice_json_state: 将AI分析出的角色与推荐声音的配对结果（及理由）存入此不可见状态组件，以传递给下一步。
"""
def voice_match_process(current_characters, current_script):  # 简化输入
    # 原有逻辑
    # print("[INFO] Starting role-voice matching...")
    # role_voice_json = current_prompt_module.Role_Voice_Map(current_characters, current_script)  # 调用角色声音配对函数
    # print("[INFO] Role-voice matching finished.")
    # return gr.update(interactive=True), gr.update(open=True), "角色声音配对成功，请继续生成TTS。",role_voice_json

    # 测试
    tmp_voice_match_json = {'角色声音配对': [{'角色名称': '旁白', '配对声音': '巴德', '理由': '该音色原型为“吟游诗人”与“守护者”，是一位超凡的星界存在，负责照料并协调宇宙的和谐。这与旁白温和、亲切且带有神秘色彩的叙事者身份完美契合，能够以一种充满关怀和智慧的口吻，引导听众进入神奇的故事世界。'}, {'角色名称': '孙悟空', '配对声音': '伊泽瑞尔', '理由': '该音色属于一位天赋异禀、自信勇敢且不守规矩的年轻探险家。这非常符合孙悟空早期作为美猴王时那种骄傲自信、敢作敢为、充满英雄气概和冒险精神的形象，声音中充满了年轻的活力与闯劲。'}, {'角色名称': '老猿猴', '配对声音': '贾克斯', '理由': '该音色是一位经验丰富的战斗大师，是“艾卡西亚最后的光”的守护者，身上肩负着沉重的责任感。这种坚毅、孤独且充满使命感的特质，非常适合为老猿猴配音，能够表现出其作为族群长者的沉稳、智慧以及对传统的守护。'}, {'角色名称': '樵夫', '配对声音': '艾翁', '理由': '该音色曾是一位无情的战士，后幡然醒悟，转变为与自然和谐共处的生命保护者。这种转变赋予了声音一种历经沧桑后的温和与悲悯，非常适合演绎心地善良、生活朴素、对自然和亲人怀有深厚感情的樵夫形象。'}, {'角色名称': '菩提祖师', '配对声音': '内瑟斯', '理由': '该音色是一位聪颖、求知若渴的学者与守护者，是智慧与力量的化身。其“智者”与“守护者”的原型，完美匹配了菩提祖师作为一位法力高深、智慧超群、同时又肩负着教导与守护责任的世外高人形象，声音沉稳而富有权威感。'}, {'角色名称': '盘古', '配对声音': '亚索', '理由': '角色 盘古 在语音库中未找到合适的配对声音，请手动选择。'}, {'角色名称': '玉皇大帝', '配对声音': '亚索', '理由': '角色 玉皇大帝 在语音库中未找到合适的配对声音，请手动选择。'}, {'角色名称': '千里眼', '配对声音': '亚索', '理由': '角色 千里眼 在语音库中未找到合适的配对声音，请手动选择。'}, {'角色名称': '顺风耳', '配对声音': '亚索', '理由': '角色 顺风耳 在语音库中未找到合适的配对声音，请手动选择。'}, {'角色名称': '仙童', '配对声音': '亚索', '理由': '角色 仙童 在语音库中未找到合适的配对声音，请手动选择。'}, {'角色名称': '猴子们', '配对声音': '璐璐', '理由': '该音色的人物原型是‘顽童’，性格中古怪、爱玩、无忧无虑的特质，与猴群活泼、好奇、七嘴八舌、时而胆怯时而兴奋的情绪状态高度吻合，能完美演绎出那份天真烂漫的群体感。'}, {'角色名称': '众师兄', '配对声音': '斯莫德', '理由': '该音色的人物原型是‘成长中的英雄’，性格中带着好奇心与学习成长的特质，这很符合众师兄作为学徒的身份，他们尚未成熟，对悟空的本领充满好奇，又会在师父发怒时表现出普通弟子的担忧和不知所措。'}]}

    return gr.update(interactive=True), gr.update(
        open=True), "角色声音配对成功，请继续生成TTS。", tmp_voice_match_json







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
