# Gunakan base image Python yang lebih kecil (slim version)
FROM python:3.9-slim-buster

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
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
