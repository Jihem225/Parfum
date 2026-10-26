import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import AppError

MAX_BYTES = 5 * 1024 * 1024
MAX_SIDE = 2000
ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP")
Image.MAX_IMAGE_PIXELS = 40_000_000  # au-delà : refus (protection contre les « bombes » d'images)


def to_webp(data: bytes) -> bytes:
    """Contrôle le contenu réel (pas l'extension) puis ré-encode en WebP ≤ 2000 px.
    Le ré-encodage supprime les métadonnées (GPS, appareil) et neutralise les fichiers piégés."""
    if len(data) > MAX_BYTES:
        raise AppError(413, "IMAGE_TOO_LARGE", "Image trop lourde : 5 Mo maximum.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            # formats= : les autres décodeurs (TIFF, GIF, EPS…) ne voient jamais le fichier.
            with Image.open(io.BytesIO(data), formats=ACCEPTED_FORMATS) as probe:
                probe.verify()
            with Image.open(io.BytesIO(data), formats=ACCEPTED_FORMATS) as source:
                image = ImageOps.exif_transpose(source)
                has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
                image = image.convert("RGBA" if has_alpha else "RGB")
                image.thumbnail((MAX_SIDE, MAX_SIDE))
                out = io.BytesIO()
                image.save(out, "WEBP", quality=82)
                return out.getvalue()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
    ) as exc:
        raise AppError(
            422, "INVALID_IMAGE", "Image illisible. Formats acceptés : JPG, PNG ou WebP."
        ) from exc
