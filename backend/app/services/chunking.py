def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """
    Splits text into chunks of roughly `chunk_size` characters, with `chunk_overlap`
    characters of overlap. Tries to split on sentence or word boundaries to preserve semantic cohesion.
    """
    if not text:
        return []
    
    chunks = []
    text_len = len(text)
    start = 0
    
    while start < text_len:
        end = start + chunk_size
        
        # If we aren't at the end of the text, try to find a natural boundary to split on
        if end < text_len:
            boundary = -1
            # Check for sentence endings (. ? ! or newline) within the last 50 characters of the chunk
            for i in range(end, max(start, end - 50), -1):
                if text[i] in {'.', '!', '?', '\n'}:
                    boundary = i
                    break
            
            if boundary != -1:
                end = boundary + 1
            else:
                # If no sentence boundary, check for space to avoid cutting words
                for i in range(end, max(start, end - 20), -1):
                    if text[i] == ' ':
                        boundary = i
                        break
                if boundary != -1:
                    end = boundary + 1
                    
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # Move forward by size minus overlap
        next_start = end - chunk_overlap
        if next_start >= text_len:
            break
        
        # Ensure we always move forward to avoid infinite loop
        if next_start <= start:
            start = end
        else:
            start = next_start
            
    return chunks
