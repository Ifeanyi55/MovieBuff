from CyVer.validators import SyntaxValidator,PropertiesValidator
from fastrtc import (ReplyOnPause,WebRTC)
from neo4j_assistant import neo4jVoice
import gradio as gr

with gr.Blocks(
    theme =  "upsatwal/mlsc_tiet",
    fill_height=True,
    css="footer {display: none !important;}"
) as demo:
    gr.HTML(
    """
    <h1 style='text-align: center'>
    🎥 Movie Buff 🎬
    </h1>
    """
    )
    with gr.Column():
        with gr.Group():
            audio = WebRTC(
                mode="send-receive",
                modality="audio",
            )
        audio.stream(fn=ReplyOnPause(neo4jVoice),
                    inputs=[audio], outputs=[audio],
                    time_limit=60)

if __name__=="__main__":
    demo.launch()

