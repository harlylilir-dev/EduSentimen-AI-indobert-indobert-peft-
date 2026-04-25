import pandas as pd
import io
import html  # 🔥 TAMBAHAN
from backend.utils.text_cleaning import clean_text

def process_file(file):
    content = file.stream.read().decode("utf-8", errors="ignore")
    stream = io.StringIO(content)

    # 🔥 FIX 1: jangan hardcode separator
    try:
        df = pd.read_csv(
            stream,
            sep=",",
            engine="python",
            on_bad_lines="skip"
        )
    except:
        stream.seek(0)
        df = pd.read_csv(
            stream,
            sep=";",
            engine="python",
            on_bad_lines="skip"
        )

    if df.empty:
        return None, "CSV kosong"

    df.columns = df.columns.str.strip()

    # 🔥 HANDLE kalau cuma 1 kolom
    if len(df.columns) == 1:
        df.columns = ['teks']
    else:
        df.rename(columns={df.columns[0]: 'teks'}, inplace=True)

    hasil = []

    for _, row in df.iterrows():
        teks = str(row['teks'])

        # 🔥 FIX 2: decode HTML (ini penting banget untuk kasus kamu)
        teks = html.unescape(teks)

        cleaned = clean_text(teks)

        hasil.append({
            "teks": teks,
            "cleaned": cleaned
        })

    return hasil, None