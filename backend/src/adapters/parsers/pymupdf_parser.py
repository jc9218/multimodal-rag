import logging

import os

import time

from typing import Callable, List, Optional, Tuple

try:
    import pymupdf as fitz

except ImportError:
    import fitz

from src.domain.models import BoundingBox, Chunk, ExtractedImage

from src.ports.document_parser_port import DocumentParserPort

from src.ports.storage_port import StoragePort

from src.infrastructure.config import settings

from src.infrastructure.memory import release_memory

logger = logging.getLogger(__name__)

# Class: PyMuPDFParser.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class PyMuPDFParser(DocumentParserPort):
    def __init__(
        self,
        storage: StoragePort,
        proximity_threshold: float = 450.0,
        ocr_dpi: int = 96,
    ):
        """init.

        Args:

            storage: StoragePort, proximity_threshold: float, ocr_dpi: int.

        Returns:

            unspecified..

        """

        self.storage = storage

        self.proximity_threshold = proximity_threshold

        self.ocr_dpi = ocr_dpi

    # Purpose: Extract PDF text, tables, and images and correlate them by page.

    # Inputs: file_path, document_id, progress_callback, page_callback.

    # Output: Tuple containing text chunks and extracted images.

    def parse_pdf(
        self,
        file_path: str,
        document_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        page_callback: Optional[
            Callable[[int, int, List[Chunk], List[ExtractedImage]], None]
        ] = None,
    ) -> Tuple[List[Chunk], List[ExtractedImage]]:
        """Parse pdf.

        Args:

            file_path: str, document_id: str, progress_callback: Optional[Callable[[float, str], None]], page_callback: Optional[Callable[[int, int, List[Chunk], List[ExtractedImage]], None]].

        Returns:

            Tuple[List[Chunk], List[ExtractedImage]]..

        """

        logger.info(
            f"Parsing PDF document '{file_path}' (doc_id={document_id}) with PyMuPDF"
        )

        fitz.TOOLS.store_shrink(100)

        release_memory()

        doc = fitz.open(file_path)

        page_count = len(doc)

        try:
            # Extract human-readable document filename safely with os imported

            raw_fname = os.path.basename(file_path)

            if raw_fname.startswith(f"{document_id}_"):
                doc_name = raw_fname[len(document_id) + 1 :]

            elif "_" in raw_fname:
                doc_name = raw_fname.split("_", 1)[1]

            else:
                doc_name = raw_fname

            all_images: List[ExtractedImage] = []

            page_images_map: dict[int, List[ExtractedImage]] = {}

            max_image_bytes = settings.MAX_EXTRACTED_IMAGE_MB * 1024 * 1024

            embedded_resources_detected = 0

            embedded_occurrences_detected = 0

            embedded_resources_decoded = 0

            embedded_occurrences_saved = 0

            skipped_oversized_resources = 0

            skipped_oversized_occurrences = 0

            skipped_limit_resources = 0

            skipped_limit_occurrences = 0

            failed_resources = 0

            failed_occurrences = 0

            scanned_pages_saved = 0

            scanned_pages_skipped_oversized = 0

            scanned_pages_failed = 0

            # Pass 1: Extract all embedded images (handling multiple occurrences / all rects per xref)

            for page_idx in range(page_count):
                page_num = page_idx + 1

                page = doc[page_idx]

                page_images_map[page_num] = []

                image_started = time.perf_counter()

                usable_image_count = 0

                extracted_image_count = 0

                saved_image_count = 0

                if progress_callback:
                    progress_callback(
                        (page_num - 1) / page_count * 0.5,
                        f"Página {page_num}/{page_count}: extrayendo imágenes y recursos visuales...",
                    )

                image_list = page.get_images(full=True)

                embedded_resources_detected += len(image_list)

                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]

                    rects = page.get_image_rects(xref)

                    usable_rects = [
                        rect for rect in rects if rect.width >= 15 and rect.height >= 15
                    ]

                    if not usable_rects:
                        try:
                            single_bbox = page.get_image_bbox(img_info)

                            if (
                                single_bbox
                                and not single_bbox.is_empty
                                and not single_bbox.is_infinite
                            ):
                                usable_rects = [single_bbox]

                            else:
                                usable_rects = [
                                    fitz.Rect(0, 0, page.rect.width, page.rect.height)
                                ]

                        except Exception:
                            usable_rects = [
                                fitz.Rect(0, 0, page.rect.width, page.rect.height)
                            ]

                    usable_image_count += len(usable_rects)

                    embedded_occurrences_detected += len(usable_rects)

                    try:
                        extract_started = time.perf_counter()

                        extracted = doc.extract_image(xref)

                        extract_elapsed = time.perf_counter() - extract_started

                        image_bytes = extracted.get("image")

                        image_ext = extracted.get("ext", "png")

                        extracted_image_count += 1

                        embedded_resources_decoded += 1

                        if len(image_bytes or b"") > max_image_bytes:
                            skipped_oversized_resources += 1

                            skipped_oversized_occurrences += len(usable_rects)

                            logger.warning(
                                "Skipping oversized image page=%s xref=%s bytes=%s limit=%s",
                                page_num,
                                xref,
                                len(image_bytes or b""),
                                max_image_bytes,
                            )

                            continue

                        if len(all_images) >= settings.MAX_IMAGES_PER_DOCUMENT:
                            skipped_limit_resources += len(image_list) - img_idx

                            skipped_limit_occurrences += len(usable_rects) + sum(
                                len(page.get_image_rects(remaining[0]))
                                for remaining in image_list[img_idx + 1 :]
                            )

                            logger.warning(
                                "Skipping remaining images document_id=%s limit=%s",
                                document_id,
                                settings.MAX_IMAGES_PER_DOCUMENT,
                            )

                            break

                        if extract_elapsed >= 0.5:
                            logger.info(
                                "Slow image extraction page=%s xref=%s duration=%.2fs bytes=%s",
                                page_num,
                                xref,
                                extract_elapsed,
                                len(image_bytes or b""),
                            )

                        # Handle all occurrences/positions where this image appears on the page

                        for rect_idx, rect in enumerate(usable_rects):
                            image_id = (
                                f"img_{document_id}_p{page_num}_{img_idx}_{rect_idx}"
                            )

                            image_filename = f"{image_id}.{image_ext}"

                            save_started = time.perf_counter()

                            dest_path = self.storage.save_image(
                                document_id=document_id,
                                image_filename=image_filename,
                                image_bytes=image_bytes,
                            )

                            saved_image_count += 1

                            save_elapsed = time.perf_counter() - save_started

                            if save_elapsed >= 0.5:
                                logger.info(
                                    "Slow image save page=%s xref=%s duration=%.2fs bytes=%s",
                                    page_num,
                                    xref,
                                    save_elapsed,
                                    len(image_bytes or b""),
                                )

                            bbox = BoundingBox(
                                page=page_num,
                                x0=round(rect.x0, 2),
                                y0=round(rect.y0, 2),
                                x1=round(rect.x1, 2),
                                y1=round(rect.y1, 2),
                            )

                            img_obj = ExtractedImage(
                                id=image_id,
                                document_id=document_id,
                                filename=image_filename,
                                page=page_num,
                                bbox=bbox,
                                file_path=dest_path,
                                url=f"/api/v1/images/{document_id}/{image_filename}",
                                format=image_ext,
                                width_px=extracted.get("width", int(rect.width)),
                                height_px=extracted.get("height", int(rect.height)),
                            )

                            all_images.append(img_obj)

                            page_images_map[page_num].append(img_obj)

                            embedded_occurrences_saved += 1

                        del image_bytes

                        del extracted

                    except Exception as exc:
                        failed_resources += 1

                        failed_occurrences += len(usable_rects)

                        logger.warning(
                            f"Failed to extract image xref={xref} on page {page_num}: {exc}"
                        )

                logger.info(
                    "Visual extraction page=%s/%s duration=%.2fs resources=%s occurrences=%s "
                    "decoded=%s saved=%s",
                    page_num,
                    page_count,
                    time.perf_counter() - image_started,
                    len(image_list),
                    usable_image_count,
                    extracted_image_count,
                    saved_image_count,
                )

                if progress_callback:
                    progress_callback(
                        (page_num / page_count) * 0.5,
                        f"Página {page_num}/{page_count}: recursos visuales extraídos "
                        f"({saved_image_count} imágenes).",
                    )

                fitz.TOOLS.store_shrink(100)

                release_memory()

            # Pass 2: Extract text blocks, tables, and perform spatial correlation

            all_chunks: List[Chunk] = []

            for page_idx in range(page_count):
                page_num = page_idx + 1

                page = doc[page_idx]

                page_chunk_start = len(all_chunks)

                page_imgs = page_images_map.get(page_num, [])

                logger.info("Extracting page %s/%s", page_num, page_count)

                page_started = time.perf_counter()

                if progress_callback:
                    progress_callback(
                        0.5 + ((page_num - 1) / page_count * 0.5),
                        f"Página {page_num}/{page_count}: extrayendo texto y tablas...",
                    )

                # --- 2.1 Structured Table Extraction via page.find_tables() ---

                text_started = time.perf_counter()

                text_blocks = page.get_text("blocks")

                native_text_len = sum(
                    len(b[4].strip()) for b in text_blocks if b[6] == 0
                )

                text_elapsed = time.perf_counter() - text_started

                table_started = time.perf_counter()

                table_count = 0

                try:
                    tables = page.find_tables() if native_text_len >= 25 else []

                    table_count = len(tables.tables) if hasattr(tables, "tables") else 0

                    for tbl_idx, tab in enumerate(tables):
                        table_data = tab.extract()

                        if table_data and len(table_data) > 1:
                            headers = [str(c or "").strip() for c in table_data[0]]

                            header_line = "| " + " | ".join(headers) + " |"

                            sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"

                            rows = []

                            for r in table_data[1:]:
                                rows.append(
                                    "| "
                                    + " | ".join([str(c or "").strip() for c in r])
                                    + " |"
                                )

                            md_table = "\n".join([header_line, sep_line] + rows)

                            t_rect = tab.bbox

                            tbl_bbox = BoundingBox(
                                page=page_num,
                                x0=round(t_rect[0], 2),
                                y0=round(t_rect[1], 2),
                                x1=round(t_rect[2], 2),
                                y1=round(t_rect[3], 2),
                            )

                            # Find nearest image to table on the same page

                            tbl_img_candidates = [
                                (img, tbl_bbox.distance_to(img.bbox))
                                for img in page_imgs
                            ]

                            tbl_img_candidates.sort(key=lambda x: x[1])

                            associated_tbl_imgs = [
                                img.id for img, _ in tbl_img_candidates[:1]
                            ]

                            tbl_chunk_id = (
                                f"chunk_{document_id}_p{page_num}_tbl_{tbl_idx}"
                            )

                            all_chunks.append(
                                Chunk(
                                    id=tbl_chunk_id,
                                    document_id=document_id,
                                    text=f"### [Tabla Página {page_num}]\n{md_table}",
                                    page=page_num,
                                    bbox=tbl_bbox,
                                    associated_images=associated_tbl_imgs,
                                    metadata={
                                        "page": page_num,
                                        "document_id": document_id,
                                        "document_name": doc_name,
                                        "type": "table",
                                    },
                                )
                            )

                except Exception as tbl_err:
                    logger.debug(f"Table extraction on page {page_num}: {tbl_err}")

                table_elapsed = time.perf_counter() - table_started

                # --- 2.2 Text extraction with OCR fallback ---

                ocr_elapsed = 0.0

                render_elapsed = 0.0

                if native_text_len < 25:
                    logger.info(
                        f"Page {page_num} has minimal/no native text ({native_text_len} chars). "
                        "Running OCR textpage extraction for scanned document..."
                    )

                    if progress_callback:
                        progress_callback(
                            0.5 + ((page_num - 1) / page_count * 0.5),
                            f"Página {page_num}/{page_count}: ejecutando OCR "
                            f"({self.ocr_dpi} DPI)...",
                        )

                    try:
                        ocr_started = time.perf_counter()

                        logger.info("Running OCR for page %s/%s", page_num, page_count)

                        tp = page.get_textpage_ocr(
                            language="spa+eng", dpi=self.ocr_dpi, full=True
                        )

                        ocr_blocks = page.get_text("blocks", textpage=tp)

                        if ocr_blocks:
                            text_blocks = ocr_blocks

                        del tp

                        ocr_elapsed = time.perf_counter() - ocr_started

                        logger.info(
                            "OCR completed page=%s/%s duration=%.2fs blocks=%s dpi=%s",
                            page_num,
                            page_count,
                            ocr_elapsed,
                            len(text_blocks),
                            self.ocr_dpi,
                        )

                    except Exception as ocr_err:
                        logger.warning(
                            f"OCR extraction bypassed or unavailable on page {page_num}: {ocr_err}"
                        )

                    if not page_imgs:
                        scan_skipped_for_size = False

                        try:
                            render_started = time.perf_counter()

                            # Use grayscale without alpha channel to cut pixmap memory consumption by 75%

                            pix = page.get_pixmap(
                                dpi=self.ocr_dpi, colorspace=fitz.csGRAY, alpha=False
                            )

                            img_bytes = pix.tobytes("png")

                            img_len = len(img_bytes)

                            if img_len > max_image_bytes:
                                scan_skipped_for_size = True

                                scanned_pages_skipped_oversized += 1

                                logger.warning(
                                    "Skipping oversized scanned page image page=%s bytes=%s limit=%s",
                                    page_num,
                                    img_len,
                                    max_image_bytes,
                                )

                                del img_bytes

                                del pix

                                raise ValueError(
                                    "Scanned page image exceeds configured limit"
                                )

                            image_id = f"img_{document_id}_p{page_num}_scan"

                            image_filename = f"{image_id}.png"

                            dest_path = self.storage.save_image(
                                document_id=document_id,
                                image_filename=image_filename,
                                image_bytes=img_bytes,
                            )

                            scan_bbox = BoundingBox(
                                page=page_num,
                                x0=0,
                                y0=0,
                                x1=round(page.rect.width, 2),
                                y1=round(page.rect.height, 2),
                            )

                            scan_img = ExtractedImage(
                                id=image_id,
                                document_id=document_id,
                                filename=image_filename,
                                page=page_num,
                                bbox=scan_bbox,
                                file_path=dest_path,
                                url=f"/api/v1/images/{document_id}/{image_filename}",
                                format="png",
                                width_px=pix.width,
                                height_px=pix.height,
                            )

                            all_images.append(scan_img)

                            page_imgs.append(scan_img)

                            scanned_pages_saved += 1

                            del img_bytes

                            del pix

                            render_elapsed = time.perf_counter() - render_started

                            logger.info(
                                "Scanned page render completed page=%s/%s duration=%.2fs bytes=%s",
                                page_num,
                                page_count,
                                render_elapsed,
                                img_len,
                            )

                        except Exception as render_err:
                            if not scan_skipped_for_size:
                                scanned_pages_failed += 1

                            logger.warning(
                                f"Could not render scanned page snapshot on page {page_num}: {render_err}"
                            )

                # --- 2.3 Semantic Hierarchical Chunking (Preserve Headings and Sections with Paragraph Merging) ---

                current_section_title = ""

                current_group: List[dict] = []

                TARGET_CHUNK_CHARS = 650

                def flush_group(group: List[dict], sec_title: str) -> None:
                    """Flush group.

                    Args:

                        group: List[dict], sec_title: str.

                    Returns:

                        None..

                    """

                    if not group:
                        return

                    combined_texts = [b["text"] for b in group]

                    body_text = "\n\n".join(combined_texts).strip()

                    if not body_text:
                        return

                    # Prepend section context if available and not redundant

                    enriched_text = body_text

                    if sec_title and not enriched_text.startswith(sec_title):
                        enriched_text = f"[{sec_title}]\n{body_text}"

                    min_x0 = min(b["x0"] for b in group)

                    min_y0 = min(b["y0"] for b in group)

                    max_x1 = max(b["x1"] for b in group)

                    max_y1 = max(b["y1"] for b in group)

                    chunk_bbox = BoundingBox(
                        page=page_num,
                        x0=round(min_x0, 2),
                        y0=round(min_y0, 2),
                        x1=round(max_x1, 2),
                        y1=round(max_y1, 2),
                    )

                    # Spatial correlation: Rank images on the same page by proximity

                    # Every diagram on the same page is relevant context to that page's text;

                    # sorting by Euclidean distance ensures the closest diagram is prioritized.

                    img_candidates = [
                        (img, chunk_bbox.distance_to(img.bbox)) for img in page_imgs
                    ]

                    img_candidates.sort(key=lambda pair: pair[1])

                    associated_images = [img.id for img, _ in img_candidates[:2]]

                    # If no images on the current page, check if text explicitly references a figure

                    # and link the image from the subsequent or preceding page

                    if not associated_images and any(
                        k in enriched_text.lower()
                        for k in (
                            "figura",
                            "diagrama",
                            "esquema",
                            "ver fig",
                            "ilustración",
                            "plano",
                        )
                    ):
                        adjacent_imgs = page_images_map.get(
                            page_num + 1, []
                        ) or page_images_map.get(page_num - 1, [])

                        if adjacent_imgs:
                            associated_images = [adjacent_imgs[0].id]

                    first_block_no = group[0]["block_no"]

                    chunk_id = f"chunk_{document_id}_p{page_num}_{first_block_no}"

                    chunk = Chunk(
                        id=chunk_id,
                        document_id=document_id,
                        text=enriched_text,
                        page=page_num,
                        bbox=chunk_bbox,
                        associated_images=associated_images,
                        metadata={
                            "page": page_num,
                            "document_id": document_id,
                            "document_name": doc_name,
                            "block_no": first_block_no,
                            "section": sec_title,
                        },
                    )

                    all_chunks.append(chunk)

                for block_idx, block in enumerate(text_blocks):
                    x0, y0, x1, y1, text, block_no, block_type = block

                    if block_type != 0:
                        continue

                    cleaned_text = text.strip()

                    if not cleaned_text:
                        continue

                    # Filter out isolated page numbering / footer artifacts (e.g. "Page 12", "12", "- 12 -")

                    if len(cleaned_text) < 15 and (
                        cleaned_text.isdigit()
                        or cleaned_text.lower().startswith("pág")
                        or cleaned_text.lower().startswith("page")
                    ):
                        continue

                    # Detect headings/titles (short lines, section numbers, e.g. "3.2 Torque", "1. INTRODUCCIÓN")

                    lines = [l.strip() for l in cleaned_text.splitlines() if l.strip()]

                    is_heading = (
                        len(cleaned_text) < 60
                        and (len(lines) == 1)
                        and (
                            cleaned_text.isupper()
                            or any(
                                cleaned_text.startswith(f"{i}.") for i in range(1, 20)
                            )
                        )
                    )

                    if is_heading:
                        # Flush previous group before starting new section

                        if current_group:
                            flush_group(current_group, current_section_title)

                            current_group = []

                        current_section_title = cleaned_text

                        if len(cleaned_text) < 15:
                            continue

                    block_item = {
                        "text": cleaned_text,
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "block_no": block_no,
                    }

                    # Check if adding this block exceeds target chunk size

                    current_chars = sum(len(b["text"]) for b in current_group)

                    if (
                        current_chars + len(cleaned_text) > TARGET_CHUNK_CHARS
                        and current_group
                    ):
                        flush_group(current_group, current_section_title)

                        current_group = [block_item]

                    else:
                        current_group.append(block_item)

                # Flush any remaining blocks on this page

                if current_group:
                    flush_group(current_group, current_section_title)

                    current_group = []

                if page_callback:
                    page_callback(
                        page_num,
                        page_count,
                        all_chunks[page_chunk_start:],
                        page_imgs,
                    )

                    del all_chunks[page_chunk_start:]

                if progress_callback:
                    progress_callback(
                        0.5 + (page_num / page_count) * 0.5,
                        f"Página {page_num}/{page_count} completada: "
                        f"{len(all_chunks)} fragmentos acumulados.",
                    )

                fitz.TOOLS.store_shrink(100)

                release_memory()

                logger.info(
                    "Page extraction summary page=%s/%s duration=%.2fs text_blocks=%s "
                    "native_chars=%s tables=%s text=%.2fs tables_time=%.2fs ocr=%.2fs "
                    "render=%.2fs chunks_total=%s",
                    page_num,
                    page_count,
                    time.perf_counter() - page_started,
                    len(text_blocks),
                    native_text_len,
                    table_count,
                    text_elapsed,
                    table_elapsed,
                    ocr_elapsed,
                    render_elapsed,
                    len(all_chunks),
                )

        finally:
            try:
                doc.close()

            except Exception:
                pass

            fitz.TOOLS.store_shrink(100)

            release_memory()

        logger.info(
            "Document processing summary document_id=%s document_name=%s pages=%s "
            "chunks_saved=%s images_saved=%s "
            "embedded_resources_detected=%s embedded_occurrences_detected=%s "
            "embedded_resources_decoded=%s embedded_occurrences_saved=%s "
            "skipped_oversized_resources=%s skipped_oversized_occurrences=%s "
            "skipped_limit_resources=%s skipped_limit_occurrences=%s "
            "failed_resources=%s failed_occurrences=%s "
            "scanned_pages_saved=%s scanned_pages_skipped_oversized=%s "
            "scanned_pages_failed=%s limits={max_image_mb:%s,max_images:%s}",
            document_id,
            doc_name,
            page_count,
            len(all_chunks),
            len(all_images),
            embedded_resources_detected,
            embedded_occurrences_detected,
            embedded_resources_decoded,
            embedded_occurrences_saved,
            skipped_oversized_resources,
            skipped_oversized_occurrences,
            skipped_limit_resources,
            skipped_limit_occurrences,
            failed_resources,
            failed_occurrences,
            scanned_pages_saved,
            scanned_pages_skipped_oversized,
            scanned_pages_failed,
            settings.MAX_EXTRACTED_IMAGE_MB,
            settings.MAX_IMAGES_PER_DOCUMENT,
        )

        return all_chunks, all_images
