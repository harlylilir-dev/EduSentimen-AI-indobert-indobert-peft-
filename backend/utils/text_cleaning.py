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

# normalisasi kata
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
    "bgt": "banget"
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

    # hapus mention
    text = re.sub(r'@\w+', '', text)

    # HASHTAG -> jadi kata (dipisah)
    text = re.sub(r'#\w+', '', text)

    # pisahkan huruf kapital (camel case hashtag)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # hapus angka (opsional, tapi kita ubah dulu)
    text = re.sub(r'\d+', ' ', text)

    # hapus simbol
    text = re.sub(r'[^a-z\s]', ' ', text)

    # hapus spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    # tokenisasi
    tokens = text.split()

    # NORMALISASI KATA
    tokens = [normalisasi[word] if word in normalisasi else word for word in tokens]

    # hapus stopword
    tokens = [word for word in tokens if word not in stopwords]

    # join
    return ' '.join(tokens)