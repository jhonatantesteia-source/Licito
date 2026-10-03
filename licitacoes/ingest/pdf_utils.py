import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageDraw

class PDFHighlighter:
    """Handles PDF to Image conversion and highlighting of evidence."""

    @staticmethod
    def highlight_text(pdf_path: Path, text_snippet: str, page_num: int, output_path: Path):
        """
        Searches for text in a PDF page, draws a yellow rectangle, and saves as PNG.
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1] if page_num else doc[0]

        # Search for the text snippet
        text_instances = page.search_for(text_snippet)

        # Convert page to image (pixmap)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Scale up for quality
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)

        # Draw yellow rectangles over matches
        for inst in text_instances:
            # Scale coordinates to match the pixmap scale (Matrix 2,2)
            rect = [inst.x0 * 2, inst.y0 * 2, inst.x1 * 2, inst.y1 * 2]
            draw.rectangle(rect, fill=(255, 255, 0, 128), outline=(255, 255, 0))

        img.save(output_path)
        doc.close()
