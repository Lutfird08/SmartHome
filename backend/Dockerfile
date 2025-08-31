# Gunakan base image Python yang lebih kecil
FROM python:3.11-slim-bullseye

# !! BARIS BARU DITAMBAHKAN DI SINI !!
# Install build tools dan library yang dibutuhkan oleh PyAudio
RUN apt-get update && apt-get install -y gcc portaudio19-dev

# Tetapkan direktori kerja di dalam container
WORKDIR /app

# Salin file requirements terlebih dahulu untuk caching
COPY requirements.txt requirements.txt

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Unduh HANYA paket NLTK yang dibutuhkan, bukan semuanya
RUN python3 -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('omw-1.4')"

# Salin sisa kode aplikasi ke dalam container
COPY . .

# Beritahu Docker port mana yang akan diekspos
EXPOSE 8080

# Perintah untuk menjalankan aplikasi saat container dimulai
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
