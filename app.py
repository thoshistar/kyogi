from flask import Flask, render_template, request, redirect, url_for
import os
import openai
import ctypes
import ctypes.util
import docx

# Windows環境でのlibcの設定
if os.name == 'nt':
    libc_name = ctypes.util.find_library("msvcrt")
    if libc_name:
        libc = ctypes.CDLL(libc_name)
    else:
        raise RuntimeError("Cannot find msvcrt.dll")

app = Flask(__name__, template_folder='.')

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# .docxファイルを読み込む関数
def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    # 音声ファイルを保存
    filepath = os.path.join("uploads", file.filename)
    file.save(filepath)

    # テキストを取得
    if filepath.endswith('.m4a') or filepath.endswith('.mp3') or filepath.endswith('.wav'):
        # Whisper-1を使って音声ファイルをテキストに変換
        with open(filepath, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1", 
                file=audio_file
            )
        text = transcript['text']
    elif filepath.endswith('.docx'):
        # .docxファイルを読み込んでテキストを取得
        text = read_docx(filepath)
    else:
        return "Unsupported file format", 400

    # GPT-4で要点整理
    doc_text = read_docx("example/稟議書の記載例.docx")  # 参照用のdocxファイルを読み込む
    prompt = f"""次の「」内のテキストを、{doc_text}のサンプル１、サンプル２を参考に、指定された８つの観点に沿って簡潔に要点整理してください。「」内のテキストを文字化する必要はありません。
「{text}」
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    summary = response.choices[0].message['content']

    # 要約をリスト形式に変換し、空の項目をフィルタリング
    summary_items = [item for item in summary.split('\n') if item.strip()]

    # 要約をテンプレートに渡す
    return render_template('result.html', summary_items=summary_items)

if __name__ == '__main__':
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)
