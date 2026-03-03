This repo is the implementation of "NovelCast: Transforming Diegetic Novels into Mimetic Audio Dramas via Multi-Agent Collaboration".

## Introduction

The Novel-to-Podcast Framework is a multi-agent collaboration system designed to transform raw novel texts into structured, engaging audio dramas and high-quality podcast outputs tailored to specific audiences (e.g., children, teenagers, or adults). By simulating the workflow of human screenwriters and directors, this framework automates complex processes such as global plot analysis, iterative scene creation, script revision, and audio preparation. Specialized agents—including Plot Analysts, Character Consultants, Dialogue Writers, Script Proofreaders, and Dubbing Directors—are employed to address specific challenges at each stage, ensuring narrative tension, structural coherence, and age-appropriate engagement in the final script. Additionally, a multidimensional timbre library and cutting-edge Text-to-Speech (TTS) engine further enhance the auditory experience by assigning and synthesizing expressive character voices.

![Agent Framework](https://github.com/9085929/NovelCast/raw/main/pic/agent_framework.png)

## Installation

Install the required dependencies:

```bash
conda create -n <your env name> python=3.10
conda activate <your env name>
pip install -r requirement.txt
```

## Quickstart

- For Ollama users, you need to download the corresponding model and change the model in `ollama.generate` in the `utils.chat` file. Here is an example:

```python
ollama.generate(model="qwen2.5:72b-instruct", prompt=prompt_text, options={"num_ctx": 30720,"num_predict":-1})
```

- For users of other api services, you need to fill in the `api_key` and `base_url` in `utils.chat`.

```python
client = OpenAI(api_key="", base_url="")
```

- Then run the script:
  Ensure your raw novel content is saved in `.txt` format and placed within the respective chapter folder (e.g., `1-第一章/原著-白话.txt`).
  Use the `-c` argument to specify the chapter number(s) you want to process.

```bash
python getScriptRes.py -c 1
# To process multiple chapters simultaneously: python getScriptRes.py -c 1 2 3
```

You'll get the generated manuscript files (including the structured script, emotional annotations, and role-voice mapping) in your corresponding output directory (e.g., `gen_teenagers`).

For the audio generation section, this project utilizes CosyVoice 2 in zero-shot mode for multi-character speech synthesis based on extracted voice references. After the script is successfully generated, run the audio synthesis script:

```bash
python getAudio.py
```

The final synthesized audio files will be saved in the same output directory as your generated scripts.

## Limitations

The current Text-to-Speech engine is limited in handling extreme vocal performances (e.g., intense shouting, crying, or subtle whispering), and the system lacks ambient sound effects. Future work will focus on enhancing the synthesis engine’s performative extremes and integrating automated Foley generation to realize a fully autonomous, highly immersive audio production pipeline.

## Appreciation

- [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) for the core text-to-speech synthesis and zero-shot voice cloning capabilities.
- [MetaGPT](https://github.com/geekan/MetaGPT) for inspiring the Multi-Agent collaboration workflow.
- Thanks to the LLM API providers (e.g., Alibaba Qwen, Google Gemini, DeepSeek) for powering the complex reasoning and script generation backbone.
