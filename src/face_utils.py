"""
face_utils.py — Utilitas pemrosesan wajah menggunakan FaceNet via DeepFace.

Fungsi utama:
  - extract_embedding(base64_image) : Decode gambar base64 → ekstrak embedding 128-dim
  - compare_embeddings(emb1, emb2)  : Hitung cosine similarity antara dua embedding
"""

import base64
import io
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Model yang digunakan: "Facenet" (128-dim) atau "Facenet512" (512-dim)
FACENET_MODEL = "Facenet"

# Ambang batas cosine distance untuk dianggap cocok
# DeepFace menggunakan cosine distance (0 = identik, 2 = berbeda total)
# Threshold 0.40 berarti ~wajah yang sama
COSINE_THRESHOLD = 0.50


def extract_embedding(base64_image: str) -> list:
    """
    Decode gambar base64 dan ekstrak embedding wajah menggunakan FaceNet via DeepFace.

    Args:
        base64_image (str): String base64 dari gambar wajah (JPG/PNG).
                            Bisa dengan atau tanpa prefix "data:image/...;base64,"

    Returns:
        list: Embedding wajah sebagai list float (128-dimensi untuk FaceNet).

    Raises:
        ValueError: Jika tidak ada wajah yang terdeteksi pada gambar.
        Exception: Jika terjadi error lain saat pemrosesan.
    """
    try:
        from deepface import DeepFace

        # Hapus prefix data URI jika ada (misal: "data:image/jpeg;base64,...")
        if "," in base64_image:
            base64_image = base64_image.split(",", 1)[1]

        # Decode base64 → bytes → numpy array (via PIL/OpenCV)
        image_bytes = base64.b64decode(base64_image)

        # Simpan sementara ke file (deepface bekerja lebih stabil dengan path file)
        import tempfile
        import cv2

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            # Ekstrak representasi embedding wajah menggunakan FaceNet
            embedding_objs = DeepFace.represent(
                img_path=tmp_path,
                model_name=FACENET_MODEL,
                enforce_detection=False,   # Ignore error jika wajah tidak terdeteksi (karena di frontend ML Kit sudah memastikan ada wajah)
                detector_backend="opencv" # Backend deteksi wajah: cepat dan ringan
            )

            if not embedding_objs:
                raise ValueError("Tidak ada wajah yang terdeteksi pada gambar.")

            # Ambil embedding dari wajah pertama yang terdeteksi
            embedding = embedding_objs[0]["embedding"]
            logger.info(f"Embedding berhasil diekstrak: {len(embedding)} dimensi")
            return embedding

        finally:
            # Hapus file sementara
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.error(f"Error ekstrak embedding: {e}")
        raise


def compare_embeddings(embedding1: list, embedding2: list) -> dict:
    """
    Bandingkan dua embedding wajah menggunakan cosine similarity.

    Args:
        embedding1 (list): Embedding wajah pertama (dari DB / registrasi)
        embedding2 (list): Embedding wajah kedua (dari gambar baru / verifikasi)

    Returns:
        dict: {
            "verified": bool,       # True jika wajah cocok
            "confidence": float,    # Skor kepercayaan 0.0–1.0 (1.0 = identik)
            "distance": float,      # Cosine distance (lebih kecil = lebih mirip)
            "threshold": float      # Threshold yang digunakan
        }
    """
    try:
        emb1 = np.array(embedding1, dtype=np.float64)
        emb2 = np.array(embedding2, dtype=np.float64)

        # Hitung cosine distance
        # cosine_similarity = dot(A, B) / (||A|| * ||B||)
        # cosine_distance = 1 - cosine_similarity (deepface convention: 1-cos)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            raise ValueError("Embedding tidak valid (norm = 0)")

        cosine_similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        cosine_distance = 1 - cosine_similarity  # range: 0 (identik) ~ 2 (berbeda)

        # Confidence score: konversi distance ke skor 0-1
        # Jika distance=0 → confidence=1.0, jika distance=threshold → confidence=0.5
        confidence = float(max(0.0, 1.0 - (cosine_distance / (COSINE_THRESHOLD * 2))))
        confidence = round(min(confidence, 1.0), 4)

        is_verified = bool(cosine_distance <= COSINE_THRESHOLD)

        logger.info(
            f"Perbandingan wajah — distance: {cosine_distance:.4f}, "
            f"threshold: {COSINE_THRESHOLD}, verified: {is_verified}, "
            f"confidence: {confidence}"
        )

        return {
            "verified": is_verified,
            "confidence": confidence,
            "distance": round(float(cosine_distance), 4),
            "threshold": COSINE_THRESHOLD
        }

    except Exception as e:
        logger.error(f"Error compare embeddings: {e}")
        raise


def is_deepface_available() -> bool:
    """Cek apakah DeepFace berhasil diimport (untuk fallback graceful)."""
    try:
        import deepface
        return True
    except ImportError:
        return False
