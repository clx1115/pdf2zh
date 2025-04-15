import os
import shutil
from pathlib import Path
from pdf2zh.high_level import translate
from pdf2zh.translator import (
    BaseTranslator,
    GoogleTranslator,
    ZhipuTranslator,
    GeminiTranslator,
)

import gradio as gr
from gradio_pdf import PDF
import tqdm
import requests
from pycparser.ply.yacc import default_lr

service_map: dict[str, BaseTranslator] = {
    "Google": GoogleTranslator,
   # "Zhipu": ZhipuTranslator,
   # "Gemini": GeminiTranslator,
}
lang_map = {
    "Chinese": "zh",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Spanish": "es",
    "Italian": "it",
}

page_map = {
    "All": None,
    "First": [0],
    "First 5 pages": list(range(0, 5)),
}

client_key = os.getenv("PDF2ZH_CLIENT_KEY")
server_key = os.getenv("PDF2ZH_SERVER_KEY")
os.environ['GEMINI_API_KEY'] = 'AIzaSyAmyjKvA7gamr6Xoq5W2VSmzx-YEVqTLrk'
os.environ['ZHIPU_API_KEY'] = 'f1279541e4773773a8a973391eba4f0f.aTjDpieDy6DdWO92'

def verify_recaptcha(response):
    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    print("reCAPTCHA", server_key, response)
    data = {"secret": server_key, "response": response}
    result = requests.post(recaptcha_url, data=data).json()
    print("reCAPTCHA", result.get("success"))
    return result.get("success")


def download_with_limit():
    pass


def on_select_service(service, evt: gr.EventData):
    translator = service_map[service]
    _envs = []
    for i in range(3):
        _envs.append(gr.update(visible=False, value=""))
    for i, env in enumerate(translator.envs.items()):
        print(env[0], env[1])
        _envs[i] = gr.update(
            visible=False if "API_KEY" in env[0] else True, label=env[0],
            value=os.getenv(env[0], env[1])
        )
    return _envs
def translate_file(
        file_input,
        service,
        lang_from,
        lang_to,
        page_range,
        progress=gr.Progress(),
        *envs,
):
    """Translate PDF content using selected service."""
    progress(0, desc="Starting translation...")

    output = Path("pdf2zh_files")
    output.mkdir(parents=True, exist_ok=True)
    if not file_input:
        raise gr.Error("No input")
    file_path = shutil.copy(file_input, output)
    filename = os.path.splitext(os.path.basename(file_path))[0]
    file_raw = output / f"{filename}.pdf"
    file_mono = output / f"{filename}-mono.pdf"
    file_dual = output / f"{filename}-dual.pdf"

    translator = service_map[service]
    selected_page = page_map[page_range]
    lang_from = lang_map[lang_from]
    lang_to = lang_map[lang_to]

    for i, env in enumerate(translator.envs.items()):
        os.environ[env[0]] = envs[i]

    print(f"Files before translation: {os.listdir(output)}")
    def progress_bar(t: tqdm.tqdm):
        progress(t.n / t.total, desc="Translating...")
    param = {
        "files": [str(file_raw)],
        "pages": selected_page,
        "lang_in": lang_from,
        "lang_out": lang_to,
        "service": f"{translator.name}",
        "output": output,
        "thread": 4,
        "callback": progress_bar,
    }
    print(param)
    translate(**param)
    print(f"Files after translation: {os.listdir(output)}")

    if not file_mono.exists() or not file_dual.exists():
        raise gr.Error("No output")

    progress(1.0, desc="Translation complete!")

    return (
        str(file_mono),
        str(file_mono),
        str(file_dual),
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(visible=True),
    )

custom_blue = gr.themes.Color(
    c50="#E8F3FF",
    c100="#BEDAFF",
    c200="#94BFFF",
    c300="#6AA1FF",
    c400="#4080FF",
    c500="#165DFF",  # Primary color
    c600="#0E42D2",
    c700="#0A2BA6",
    c800="#061D79",
    c900="#03114D",
    c950="#020B33",
)

with gr.Blocks(
        title="PDF翻译助手",
        theme=gr.themes.Default(
            primary_hue=custom_blue, spacing_size="md", radius_size="lg"
        ),
) as app:
    gr.Markdown(
        "# PDF翻译助手"
    )
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## File")
            file_input = gr.File(
                label="File",
                file_count="single",
                file_types=[".pdf"],
                type="filepath",
                elem_classes=["input-file"],
            )
            gr.Markdown("## Option")
            service = gr.Dropdown(
                label="Service",
                choices=service_map.keys(),
                value="Google",
            )

            envs = []
            # 初始化环境变量输入框
            #translator_init = service_map["Zhipu"]
            for i in range(3):
                envs.append(
                    gr.Textbox(
                        visible=False,
                        interactive=True,
                    )
                )
            
            # 设置初始状态
            #for i, env in enumerate(translator_init.envs.items()):
            #    if "API_KEY" not in env[0]:
            #        envs[i].visible = True
            #        envs[i].label = env[0]
            #        envs[i].value = os.getenv(env[0], env[1])
            with gr.Row():
                lang_from = gr.Dropdown(
                    label="Translate from",
                    choices=lang_map.keys(),
                    value="English",
                )
                lang_to = gr.Dropdown(
                    label="Translate to",
                    choices=lang_map.keys(),
                    value="Chinese",
                )
            with gr.Row():
                page_range = gr.Radio(
                    choices=page_map.keys(),
                    label="Pages",
                    value=list(page_map.keys())[0],
                )
                service.select(
                    on_select_service,
                    service,
                    envs,
                )
            with gr.Row():
                output_title = gr.Markdown("## Translated", visible=False)
            with gr.Row():
                output_file_mono = gr.File(
                    label="Download Translation (Mono)", visible=False
                )
                output_file_dual = gr.File(
                    label="Download Translation (Dual)", visible=False
                )
            with gr.Row():
                translate_btn = gr.Button("Translate", variant="primary")
        with gr.Column(scale=2):
            gr.Markdown("## Preview")
            preview = PDF(label="Document Preview", visible=True)
    file_input.upload(
        lambda x: x,
        inputs=file_input,
        outputs=preview,
    )
    translate_btn.click(
        translate_file,
        inputs=[
            file_input,
            service,
            lang_from,
            lang_to,
            page_range,
            *envs,
        ],
        outputs=[
            output_file_mono,
            preview,
            output_file_dual,
            output_file_mono,
            output_file_dual,
            output_title,
        ],
    )

def setup_gui(share=False):
    try:
        app.launch(
            server_name="0.0.0.0",
            server_port=9870,
            debug=True,
            inbrowser=True,
            share=share,
            auth=('admin', 'ai@topskyrealty.com'),
        )
    except Exception:
        print(
            "Error launching GUI using 0.0.0.0.\nThis may be caused by global mode of proxy software."
        )
        try:
            app.launch(
                server_name="127.0.0.1", debug=True, inbrowser=True, share=share
            )
        except Exception:
            print(
                "Error launching GUI using 127.0.0.1.\nThis may be caused by global mode of proxy software."
            )
            app.launch(debug=True, inbrowser=True, share=True)


# For auto-reloading while developing
if __name__ == "__main__":
    setup_gui()
