from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secret_key_216' 

app.config['SESSION_COOKIE_NAME'] = 'session_peminjam'
app.permanent_session_lifetime = timedelta(minutes=3)

# Konfigurasi Database
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER') 
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')     
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Hasil query bisa diakses sbg dictionary
mysql = MySQL(app)

# Routes Auth
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.jinja')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM peminjam WHERE user_peminjam = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user:
            if check_password_hash(user['pass_peminjam'], password):
                session['user_id'] = user['id_peminjam']
                session['nama'] = user['nama_peminjam']
                session['keranjang'] = [] # Inisialisasi keranjang kosong
                return redirect(url_for('dashboard'))
            else:
                flash('Password salah!', 'danger')
        else:
            flash('Username tidak ditemukan!', 'danger')

    return render_template('login.jinja')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO peminjam (nama_peminjam, user_peminjam, pass_peminjam, status_peminjam) 
                VALUES (%s, %s, %s, 'AKTIF')
            """, (nama, username, hashed_password)) # Otomatis aktif setelah register
            mysql.connection.commit()
            flash('Pendaftaran berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Username sudah digunakan atau error lain: {e}', 'danger')
        finally:
            cur.close()

    return render_template('register.jinja')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Routes Utama Peminjam
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM buku")
    buku_list = cur.fetchall()
    cur.close()
    
    return render_template('dashboard.jinja', buku=buku_list)

@app.route('/tambah_keranjang/<int:id_buku>')
def tambah_keranjang(id_buku):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    keranjang = session.get('keranjang', [])
    
    # Masukkan ID buku ke session list    
    # Cek agar tidak meminjam buku yang sama 2 kali dalam 1 sesi
    if id_buku not in keranjang:
        keranjang.append(id_buku)
        session['keranjang'] = keranjang
        flash('Buku dimasukkan ke keranjang peminjaman.', 'success')
    else:
        flash('Buku sudah ada di keranjang.', 'warning')
        
    return redirect(url_for('dashboard'))

@app.route('/keranjang')
def keranjang():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    id_buku_list = session.get('keranjang', [])
    
    buku_di_keranjang = []
    if id_buku_list:
        # Ambil detail buku berdasarkan ID yang ada di session
        format_strings = ','.join(['%s'] * len(id_buku_list))
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT * FROM buku WHERE id_buku IN ({format_strings})", tuple(id_buku_list))
        buku_di_keranjang = cur.fetchall()
        cur.close()
        
    return render_template('keranjang.jinja', buku=buku_di_keranjang)

@app.route('/hapus_keranjang/<int:id_buku>')
def hapus_keranjang(id_buku):
    keranjang = session.get('keranjang', [])
    if id_buku in keranjang:
        keranjang.remove(id_buku)
        session['keranjang'] = keranjang
    return redirect(url_for('keranjang'))

@app.route('/proses_pinjam', methods=['POST'])
def proses_pinjam():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    keranjang = session.get('keranjang', [])
    if not keranjang:
        flash('Keranjang kosong!', 'warning')
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    tgl_pesan = datetime.now()
    # Wajib kembalikan 7 hari setelah pemesanan
    tgl_wajibkembali = tgl_pesan + timedelta(days=7)
    
    cur = mysql.connection.cursor()
    try:
        # Buat record di tabel peminjaman
        cur.execute("""
            INSERT INTO peminjaman (id_peminjam, tgl_pesan, tgl_wajibkembali, status)
            VALUES (%s, %s, %s, 'DIPROSES')
        """, (user_id, tgl_pesan, tgl_wajibkembali))
        
        # Ambil kode_pinjam yang baru saja dibuat (Mabil primary key terakhir insert)
        kode_pinjam = cur.lastrowid
        
        # Masukkan detail buku ke tabel detail_peminjaman
        for id_buku in keranjang:
            cur.execute("""
                INSERT INTO detail_peminjaman (kode_pinjam, id_buku)
                VALUES (%s, %s)
            """, (kode_pinjam, id_buku))
            
        mysql.connection.commit()
        
        # Kosongkan keranjang setelah sukses
        session['keranjang'] = []
        flash('Peminjaman berhasil diajukan! Silakan ambil melalui Drive-Thru.', 'success')
        return redirect(url_for('riwayat'))
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Gagal memproses peminjaman: {e}', 'danger')
        return redirect(url_for('keranjang'))
    finally:
        cur.close()

@app.route('/riwayat')
def riwayat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Query join untuk mengambil data peminjaman beserta detail bukunya
    # Pakai GROUP_CONCAT agar buku tampil dalam satu baris per kode pinjam
    query = """
        SELECT p.kode_pinjam, p.tgl_pesan, p.tgl_wajibkembali, p.status, 
               GROUP_CONCAT(b.judul_buku SEPARATOR ', ') as daftar_buku
        FROM peminjaman p
        JOIN detail_peminjaman dp ON p.kode_pinjam = dp.kode_pinjam
        JOIN buku b ON dp.id_buku = b.id_buku
        WHERE p.id_peminjam = %s
        GROUP BY p.kode_pinjam
        ORDER BY p.tgl_pesan DESC
    """
    cur.execute(query, (user_id,))
    data_riwayat = cur.fetchall()
    cur.close()
    
    return render_template('riwayat.jinja', riwayat=data_riwayat)

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Port 5001 biar ga bentrok kalau admin jalan juga
