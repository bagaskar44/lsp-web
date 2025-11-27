from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secret_key_admin_216' 
app.permanent_session_lifetime = timedelta(minutes=3)

# Konfigurasi Database
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER') 
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')     
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Hasil query bisa diakses sbg dictionary
mysql = MySQL(app)

# Routes Auth Admin
@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('dashboard_admin'))
    return redirect(url_for('login_admin'))

@app.route('/login', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE user_admin = %s", (username,))
        admin = cur.fetchone()
        cur.close()

        if admin:
            if check_password_hash(admin['pass_admin'], password):
                session['admin_id'] = admin['id_admin']
                session['nama_admin'] = admin['nama_admin']
                return redirect(url_for('dashboard_admin'))
            else:
                flash('Password salah!', 'danger')
        else:
            flash('Username admin tidak ditemukan!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_admin'))

# Helper: Register Admin Baru
'''
@app.route('/setup_admin')
def setup_admin():
    # Jalankan url ini sekali untuk membuat akun admin: user=admin, pass=admin123
    pass_hash = generate_password_hash('admin123')
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO admin (nama_admin, user_admin, pass_admin) VALUES ('Super Admin', 'admin', %s)", (pass_hash,))
        mysql.connection.commit()
        return "Admin berhasil dibuat. User: admin, Pass: admin123"
    except:
        return "Admin sudah ada."
    finally:
        cur.close()     
'''

# Routes Utama Admin
@app.route('/dashboard')
def dashboard_admin():
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    # Menampilkan pesanan yang statusnya masih DIPROSES
    cur = mysql.connection.cursor()
    query = """
        SELECT p.kode_pinjam, p.tgl_pesan, pm.nama_peminjam, p.status, count(dp.id_detail) as jumlah_buku
        FROM peminjaman p
        JOIN peminjam pm ON p.id_peminjam = pm.id_peminjam
        JOIN detail_peminjaman dp ON p.kode_pinjam = dp.kode_pinjam
        WHERE p.status = 'DIPROSES'
        GROUP BY p.kode_pinjam
        ORDER BY p.tgl_pesan ASC
    """
    cur.execute(query)
    pesanan_masuk = cur.fetchall()
    cur.close()
    
    return render_template('dashboard.html', pesanan=pesanan_masuk)

@app.route('/detail_pesanan/<int:kode_pinjam>')
def detail_pesanan(kode_pinjam):
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    cur = mysql.connection.cursor()
    
    # Ambil Info Peminjam
    cur.execute("""
        SELECT p.kode_pinjam, pm.nama_peminjam, p.tgl_pesan, p.status 
        FROM peminjaman p
        JOIN peminjam pm ON p.id_peminjam = pm.id_peminjam
        WHERE p.kode_pinjam = %s
    """, (kode_pinjam,))
    info_pinjam = cur.fetchone()
    
    # Ambil Detail Buku
    cur.execute("""
        SELECT dp.id_detail, b.judul_buku, b.nama_pengarang
        FROM detail_peminjaman dp
        JOIN buku b ON dp.id_buku = b.id_buku
        WHERE dp.kode_pinjam = %s
    """, (kode_pinjam,))
    detail_buku = cur.fetchall()
    cur.close()
    
    return render_template('detail_pesanan.html', info=info_pinjam, buku=detail_buku)

@app.route('/hapus_item/<int:kode_pinjam>/<int:id_detail>')
def hapus_item(kode_pinjam, id_detail):
    # Fitur: Admin mengurangi buku dari daftar jika tidak tersedia
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM detail_peminjaman WHERE id_detail = %s", (id_detail,))
    mysql.connection.commit()
    cur.close()
    
    flash('Satu buku berhasil dihapus dari pesanan.', 'warning')
    return redirect(url_for('detail_pesanan', kode_pinjam=kode_pinjam))

@app.route('/aksi_pesanan/<int:kode_pinjam>/<string:aksi>')
def aksi_pesanan(kode_pinjam, aksi):
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    admin_id = session['admin_id']
    status_baru = ''
    
    if aksi == 'setuju':
        status_baru = 'DISETUJUI'
    elif aksi == 'tolak':
        status_baru = 'DITOLAK'
    else:
        return redirect(url_for('dashboard_admin'))
        
    cur = mysql.connection.cursor()
    # Update status dan catat siapa admin yang memproses, set tgl_ambil jika disetujui
    if status_baru == 'DISETUJUI':
        cur.execute("""
            UPDATE peminjaman 
            SET status = %s, id_admin = %s, tgl_ambil = NOW() 
            WHERE kode_pinjam = %s
        """, (status_baru, admin_id, kode_pinjam))
    else:
        cur.execute("""
            UPDATE peminjaman 
            SET status = %s, id_admin = %s 
            WHERE kode_pinjam = %s
        """, (status_baru, admin_id, kode_pinjam))
        
    mysql.connection.commit()
    cur.close()
    
    flash(f'Pesanan berhasil {status_baru}.', 'success')
    return redirect(url_for('dashboard_admin'))

# Route Pengembalian
@app.route('/pengembalian')
def pengembalian():
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    # Menampilkan pesanan yang statusnya DISETUJUI (Sedang dipinjam)
    cur = mysql.connection.cursor()
    query = """
        SELECT p.kode_pinjam, pm.nama_peminjam, p.tgl_ambil, p.tgl_wajibkembali
        FROM peminjaman p
        JOIN peminjam pm ON p.id_peminjam = pm.id_peminjam
        WHERE p.status = 'DISETUJUI'
        ORDER BY p.tgl_wajibkembali ASC
    """
    cur.execute(query)
    list_kembali = cur.fetchall()
    cur.close()
    
    return render_template('pengembalian.html', list_kembali=list_kembali)

@app.route('/konfirmasi_kembali/<int:kode_pinjam>')
def konfirmasi_kembali(kode_pinjam):
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
        
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE peminjaman 
        SET status = 'SELESAI', tgl_kembali = NOW() 
        WHERE kode_pinjam = %s
    """, (kode_pinjam,))
    mysql.connection.commit()
    cur.close()
    
    flash('Pengembalian berhasil dikonfirmasi. Transaksi Selesai.', 'success')
    return redirect(url_for('pengembalian'))

# Kelola Buku
@app.route('/buku', methods=['GET', 'POST'])
def kelola_buku():
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))
    
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        judul = request.form['judul']
        pengarang = request.form['pengarang']
        penerbit = request.form['penerbit']
        tgl_terbit = request.form['tgl_terbit'] # Format YYYY-MM-DD
        
        cur.execute("""
            INSERT INTO buku (judul_buku, nama_pengarang, nama_penerbit, tgl_terbit)
            VALUES (%s, %s, %s, %s)
        """, (judul, pengarang, penerbit, tgl_terbit))
        mysql.connection.commit()
        flash('Buku berhasil ditambahkan', 'success')
    
    cur.execute("SELECT * FROM buku ORDER BY id_buku DESC")
    buku_list = cur.fetchall()
    cur.close()
    
    return render_template('kelola_buku.html', buku=buku_list)

if __name__ == '__main__':
    app.run(debug=True, port=5002) # Port 5002 untuk Admin