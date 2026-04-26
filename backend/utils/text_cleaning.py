import re
import html
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# stopword
factory = StopWordRemoverFactory()
stopwords = set(factory.get_stop_words())

# tambahan stopword manual (SLANG / NOISE)
custom_stopwords = {
    "tuh", "nih", "dong", "deh", "lah", "kok", "sih",
    "git", "gitu", "gt", "aja", "doang", "banget",
    "amp", "ampamp", "nya", "yah"
}

# normalisasi kata (slang & english -> indonesia baku)
normalisasi = {
    "yg": "yang",
    "dgn": "dengan",
    "tdk": "tidak",
    "gk": "tidak",
    "gak": "tidak",
    "ga": "tidak",
    "kalo": "kalau",
    "utk": "untuk",
    "org": "orang",
    "rp": "rupiah",
    "t": "triliun",
    "jt": "juta",
    "m": "miliar",
    "dr": "dari",
    "pd": "pada",
    "krn": "karena",
    "smpe": "sampai",
    "sampe": "sampai",
    "blm": "belum",
    "udah": "sudah",
    "aja": "saja",
    "bgt": "banget",
    "and": "dan",
    "the": "itu",
    "is": "adalah",
    "are": "adalah",
    "in": "di",
    "on": "pada",
    "with": "dengan",
    "for": "untuk",
    "from": "dari",
    "not": "tidak",
    "no": "tidak",
    "yes": "ya",
    "good": "bagus",
    "bad": "buruk",
}

def clean_text(text):
    text = str(text)

    # fix encoding
    text = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')

    # lowercase
    text = text.lower()

    # hapus HTML entity
    text = html.unescape(text)

    # hapus URL
    text = re.sub(r'https?://\S+', '', text)

    # hapus mention @user
    text = re.sub(r'@\w+', '', text)

    # hapus hashtag #contoh
    text = re.sub(r'#\w+', '', text)

    # hapus angka
    text = re.sub(r'\d+', ' ', text)

    # hapus semua karakter selain huruf dan spasi (termasuk tanda baca, simbol)
    text = re.sub(r'[^a-z\s]', ' ', text)

    # hapus spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    # tokenisasi & normalisasi kata
    tokens = text.split()
    tokens = [normalisasi[word] if word in normalisasi else word for word in tokens]

    # hapus stopword
    tokens = [word for word in tokens if word not in stopwords]

    return ' '.join(tokens)