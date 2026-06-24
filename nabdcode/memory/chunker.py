import os
import re

class SmartCodeChunker:
    """وحدة التقطيع الذكي لفصل ملفات الكود والنصوص بناءً على دلالة البنية وليس فقط حجم الحروف"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.MAX_FILE_SIZE = 5 * 1024 * 1024
        
        self.boundary_pattern = re.compile(
            r'''
            (def\s+\w+)
            |(class\s+\w+)
            |(func\s+\w+)
            |(\bfunction\b)
            |(fun\s+\w+)
            |(struct\s+\w+)
            |(interface\s+\w+)
            |(namespace\s+\w+)
            |(export\s+class\s+\w+)
            ''',
            re.MULTILINE | re.VERBOSE
        )

    def _apply_overlap(self, lines, overlap_chars):
        result = []
        size = 0
        for line in reversed(lines):
            size += len(line) + 1
            result.insert(0, line)
            if size >= overlap_chars:
                break
        return result

    def chunk_file(self, file_path: str, content: str) -> list:
        """تحديد نوع الملف وتقطيعه بالأسلوب الأنسب (كود برمجي أم نص عادي)"""
        if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
            raise ValueError(f"File {file_path} exceeds maximum supported size")
            
        _, ext = os.path.splitext(file_path.lower())
        
        # إذا كان ملف كود مصدري
        if ext in ['.py', '.go', '.java', '.js', '.cpp', '.h', '.ts', '.c', '.rs', '.php', '.rb', '.swift']:
            return self._chunk_source_code(content, file_path, ext)
        else:
            return self._chunk_text(content, file_path, ext)

    def _chunk_source_code(self, content: str, file_path: str, ext: str) -> list:
        """تقطيع الأكواد البرمجية بمراعاة حدود الدوال والفئات"""
        lines = content.splitlines()
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1
            if self.boundary_pattern.search(line) and current_size > (self.chunk_size // 2):
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = self._apply_overlap(current_chunk, self.chunk_overlap)
                    current_size = sum(len(l) + 1 for l in current_chunk)

            current_chunk.append(line)
            current_size += line_size

            if current_size >= self.chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = self._apply_overlap(current_chunk, self.chunk_overlap)
                current_size = sum(len(l) + 1 for l in current_chunk)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        result = []
        for i, chk in enumerate(chunks):
            if chk.strip():
                result.append({
                    "text": chk,
                    "metadata": {
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "chunk_index": i,
                        "chunk_type": "code",
                        "language": ext.lstrip(".")
                    }
                })
        return result

    def _chunk_text(self, content: str, file_path: str, ext: str) -> list:
        """تقطيع النصوص العامة والـ Markdown بناءً على الفقرات"""
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para) + 2
            if current_size + para_size > self.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        result = []
        for i, chk in enumerate(chunks):
            if chk.strip():
                result.append({
                    "text": chk,
                    "metadata": {
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "chunk_index": i,
                        "chunk_type": "text",
                        "language": ext.lstrip(".") if ext else "text"
                    }
                })
        return result
