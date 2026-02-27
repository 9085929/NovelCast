import json

def process_audio_files(input_file_path, output_file_path):
    """
    Reads a JSON file, processes the '音频' list for each character to keep only the first audio file,
    and writes the result to a new JSON file.

    Args:
        input_file_path (str): The path to the input JSON file.
        output_file_path (str): The path to the output JSON file.
    """
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Iterate over each character in the JSON data
        for character_name, character_data in data.items():
            # Check if '音频' key exists and is a list
            if "音频" in character_data and isinstance(character_data["音频"], list):
                # If there are multiple audio files, keep only the first one
                if len(character_data["音频"]) > 1:
                    character_data["音频"] = character_data["音频"][:1]

        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"处理完成！已将结果保存到 {output_file_path}")

    except FileNotFoundError:
        print(f"错误: 文件 '{input_file_path}' 未找到。")
    except json.JSONDecodeError:
        print(f"错误: 文件 '{input_file_path}' 不是有效的JSON格式。")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == '__main__':
    # 将 'your_input_file.json' 替换为您的输入文件名
    # 将 'your_output_file.json' 替换为您想要的输出文件名
    process_audio_files('merged_lol_data_xiyou_1028.json', 'merged_lol_data_xiyou_1028_1.json')
