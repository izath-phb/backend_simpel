import os
import sys
from datetime import datetime
from mongoengine import connect
from werkzeug.security import generate_password_hash

# Pastikan path folder backend terbaca agar bisa import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import User, Report, ReportLog, Project, Announcement, AuditLog

def seed_db():
    print("=== Memulai Seeding Database SIMPEL ===")
    
    # Hubungkan ke MongoDB
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/simpel_db')
    print(f"Menghubungkan ke MongoDB: {mongo_uri}")
    connect(host=mongo_uri)
    
    # 1. Bersihkan Koleksi Lama
    print("Membersihkan koleksi database lama...")
    User.objects.delete()
    Report.objects.delete()
    Project.objects.delete()
    Announcement.objects.delete()
    AuditLog.objects.delete()
    
    # 2. Buat Pengguna (Admin & Warga)
    print("Membuat pengguna default...")
    
    admin = User(
        name="Admin Desa Bongkok",
        email="admin@desa.go.id",
        role="admin",
        rt="00",
        rw="00",
        photo_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=150",
        is_verified=True,
        is_email_verified=True
    )
    admin.set_password("admin123")
    admin.save()
    
    warga = User(
        name="Budi Santoso",
        email="warga@desa.go.id",
        role="warga",
        rt="003",
        rw="002",
        photo_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=150",
        is_verified=True,
        is_email_verified=True
    )
    warga.set_password("warga123")
    warga.save()
    
    print(f"-> Sukses membuat Admin: {admin.email}")
    print(f"-> Sukses membuat Warga: {warga.email}")
    
    # 3. Buat Pengumuman
    print("Membuat pengumuman desa...")
    
    announcements_data = [
        {
            "title": "Kerja Bakti Akbar Desa Bongkok",
            "content": "Menyambut musim hujan, seluruh warga diimbau untuk berpartisipasi dalam kerja bakti membersihkan saluran air dan drainase pada hari Minggu besok mulai pukul 07:00 WIB di lingkungan RT masing-masing.",
            "imageUrl": "https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?q=80&w=600",
            "authorName": "Kepala Desa Bongkok",
            "is_carousel": True
        },
        {
            "title": "Penyaluran BLT Dana Desa Tahap II",
            "content": "Penyaluran Bantuan Langsung Tunai (BLT) Tahap II akan diselenggarakan di Balai Desa mulai Senin depan pukul 08:30 WIB. Warga penerima manfaat harap membawa KTP dan Kartu Keluarga asli.",
            "imageUrl": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?q=80&w=600",
            "authorName": "Sekretaris Desa",
            "is_carousel": True
        },
        {
            "title": "Posyandu Balita & Lansia Rutin",
            "content": "Pemeriksaan kesehatan rutin bulanan gratis untuk balita (timbang berat badan & vitamin) dan lansia (cek tensi & gula darah) akan dilaksanakan di Poskesdes hari Rabu depan pukul 09:00 WIB.",
            "imageUrl": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=600",
            "authorName": "Kader Posyandu",
            "is_carousel": False
        }
    ]
    
    for a_data in announcements_data:
        ann = Announcement(**a_data)
        ann.save()
        
    print(f"-> Sukses membuat {len(announcements_data)} pengumuman.")
    
    # 4. Buat Proyek Pembangunan
    print("Membuat proyek pembangunan desa...")
    
    projects_data = [
        {
            "title": "Pengecoran Jalan RT 03 / RW 02",
            "description": "Pekerjaan pengaspalan dan pengecoran jalan utama sepanjang 300 meter untuk mempermudah akses transportasi dan ekonomi warga.",
            "budget": 75000000.0,
            "progress": 80,
            "status": "On Progress",
            "coordinates": [-6.2012, 106.8175],
            "imageUrl": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=600",
            "startDate": datetime(2026, 4, 1),
            "endDate": datetime(2026, 6, 1)
        },
        {
            "title": "Pembangunan Drainase Irigasi Beton",
            "description": "Pembuatan saluran irigasi air beton di pinggir jalan utama guna mengantisipasi luapan banjir musiman di pemukiman warga.",
            "budget": 120000000.0,
            "progress": 100,
            "status": "Completed",
            "coordinates": [-6.1985, 106.8123],
            "imageUrl": "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?q=80&w=600",
            "startDate": datetime(2026, 2, 10),
            "endDate": datetime(2026, 4, 15)
        },
        {
            "title": "Pemasangan Lampu Penerangan Jalan Umum",
            "description": "Instalasi 15 titik tiang lampu jalan LED hemat energi bertenaga surya di titik-titik gang desa yang rawan gelap.",
            "budget": 35000000.0,
            "progress": 25,
            "status": "Planning",
            "coordinates": [-6.2045, 106.8198],
            "imageUrl": "https://images.unsplash.com/photo-1507608869274-d3177c8bb4c7?q=80&w=600",
            "startDate": datetime(2026, 5, 15),
            "endDate": datetime(2026, 6, 15)
        }
    ]
    
    for p_data in projects_data:
        p = Project(**p_data)
        p.save()
        
    print(f"-> Sukses membuat {len(projects_data)} proyek pembangunan.")
    
    # 5. Buat Laporan Warga
    print("Membuat contoh laporan warga...")
    
    reports_data = [
        {
            "user_id": warga,
            "title": "Kebersihan Lingkungan - Sampah Menumpuk Dekat Pasar",
            "description": "Sampah domestik meluap di pinggir jalan pasar desa Bongkok, baunya sangat menyengat dan mulai mengundang banyak lalat. Mengganggu sekali bagi pejalan kaki.",
            "category": "Kebersihan Lingkungan",
            "coordinates": [-6.1995, 106.8142],
            "status": "on_progress",
            "imageUrl": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?q=80&w=600",
            "logs": [
                ReportLog(status="pending", note="Laporan berhasil dikirim oleh warga.", timestamp=datetime(2026, 5, 14, 8, 30)),
                ReportLog(status="verified", note="Laporan diverifikasi. Petugas kebersihan akan segera dikerahkan ke lokasi pasar.", timestamp=datetime(2026, 5, 14, 10, 15)),
                ReportLog(status="on_progress", note="Petugas kebersihan beserta truk pengangkut sampah sedang memuat sampah di lokasi.", timestamp=datetime(2026, 5, 15, 9, 0))
            ]
        },
        {
            "user_id": warga,
            "title": "Infrastruktur Desa - Jalan Berlubang Besar RT 04",
            "description": "Jalan utama RT 04 berlubang cukup dalam (sekitar 15cm), sangat membahayakan bagi pengendara motor terutama saat malam hari karena kurang penerangan.",
            "category": "Infrastruktur Desa",
            "coordinates": [-6.2025, 106.8188],
            "status": "resolved",
            "imageUrl": "https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=600",
            "afterImageUrl": "https://images.unsplash.com/photo-1599740831146-80a6b7bd06c2?q=80&w=600",
            "adminNote": "Lubang jalan telah ditambal dengan material semen aspal dingin oleh tim sarana prasarana desa dan sekarang jalan aman dilewati.",
            "rating": 5,
            "logs": [
                ReportLog(status="pending", note="Laporan berhasil dikirim oleh warga.", timestamp=datetime(2026, 5, 10, 14, 20)),
                ReportLog(status="verified", note="Laporan diverifikasi. Penambalan lubang jalan dijadwalkan minggu ini.", timestamp=datetime(2026, 5, 11, 8, 0)),
                ReportLog(status="on_progress", note="Tim konstruksi desa sedang melakukan penambalan aspal di lokasi jalan berlubang.", timestamp=datetime(2026, 5, 12, 13, 0)),
                ReportLog(status="resolved", note="Penambalan lubang selesai 100%. Jalan sudah kembali mulus.", timestamp=datetime(2026, 5, 13, 16, 30))
            ]
        },
        {
            "user_id": warga,
            "title": "Keamanan & Ketertiban - Lampu Jalan Gang Flamboyan Mati",
            "description": "Lampu penerangan jalan utama di gang Flamboyan padam selama 3 malam berturut-turut. Kondisi gang sangat gelap di malam hari, warga khawatir rawan tindakan kriminal.",
            "category": "Keamanan & Ketertiban",
            "coordinates": [-6.2008, 106.8160],
            "status": "pending",
            "imageUrl": "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?q=80&w=600",
            "logs": [
                ReportLog(status="pending", note="Laporan berhasil dikirim oleh warga. Menunggu verifikasi petugas.", timestamp=datetime(2026, 5, 16, 20, 45))
            ]
        }
    ]
    
    for r_data in reports_data:
        r = Report(**r_data)
        r.save()
        
    print(f"-> Sukses membuat {len(reports_data)} laporan warga.")
    
    # 6. Buat Audit Log
    print("Membuat contoh audit log...")
    AuditLog(
        admin_id=admin,
        action="CREATE_PROJECT",
        target="Pengecoran Jalan RT 03 / RW 02",
        timestamp=datetime(2026, 4, 1, 9, 30)
    ).save()
    AuditLog(
        admin_id=admin,
        action="UPDATE_REPORT_STATUS",
        target="Infrastruktur Desa - Jalan Berlubang Besar RT 04",
        timestamp=datetime(2026, 5, 13, 16, 30)
    ).save()
    
    print("=== Seeding Selesai dengan Sukses! ===")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    seed_db()
