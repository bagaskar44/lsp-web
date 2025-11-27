Sistem Informasi Perpustakaan Arcadia (Drive-Thru)Aplikasi web berbasis Flask untuk manajemen peminjaman buku dengan sistem Drive-Thru. Terdiri dari dua modul: Peminjam (Member) dan Admin.Fitur UtamaPeminjam: Landing page, Registrasi/Login, Katalog Buku, Keranjang, dan Tiket Kode Pinjam (untuk ditunjukkan di Drive-Thru).Admin: Dashboard Pesanan, Manajemen Stok (Edit Pesanan), Persetujuan (Approval), dan Konfirmasi Pengembalian.TeknologiBackend: Python FlaskDatabase: MySQL (flask_mysqldb)Frontend: HTML5, Bootstrap 5Struktur Folder/arcadia_library
│
├── app.py                # Aplikasi Peminjam (Port 5001)
├── app_admin.py          # Aplikasi Admin (Port 5002)
├── /templates            # Folder HTML (User & Admin)
└── README.md
Instalasi & KonfigurasiInstall Library:pip install flask flask-mysqldb
Database:Buat database arcadia_db dan buat tabel (peminjam, admin, buku, peminjaman, detail_peminjaman) sesuai skema rancangan.Konfigurasi:Sesuaikan MYSQL_USER dan MYSQL_PASSWORD di file app.py dan app_admin.py.Cara MenjalankanBuka dua terminal berbeda untuk menjalankan sistem secara paralel:Aplikasi Peminjam (User):python app.py
Akses: http://127.0.0.1:5001Aplikasi Admin (Staff):python app_admin.py
Akses: http://127.0.0.1:5002Alur SingkatSetup: Jalankan app_admin.py, akses /setup_admin untuk buat akun admin awal.User: Daftar -> Pilih Buku -> Checkout -> Dapat Kode "DIPROSES".Admin: Cek Dashboard -> Setujui Pesanan.Pickup: User cek status "SIAP DIAMBIL" -> Tunjukkan Kode di Drive-Thru.Return: Admin konfirmasi di menu Pengembalian saat buku dikembalikan.
