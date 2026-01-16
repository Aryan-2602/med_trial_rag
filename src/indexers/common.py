"""Common utilities for indexing documents."""

import re
from typing import List


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Uses a simple token estimation (1 token ≈ 4 characters) for chunking.
    For production, consider using tiktoken for accurate token counting.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Simple token estimation: ~4 characters per token
    # This is approximate but works for chunking purposes
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap * chars_per_token
    
    # Split by paragraphs first (double newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_length = len(para)
        
        # If paragraph fits, add it
        if current_length + para_length <= max_chars:
            current_chunk.append(para)
            current_length += para_length + 2  # +2 for newline
        else:
            # Current chunk is full, save it
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
            
            # If paragraph itself is too long, split it by sentences
            if para_length > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = []
                current_length = 0
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    sent_length = len(sentence)
                    
                    if current_length + sent_length <= max_chars:
                        current_chunk.append(sentence)
                        current_length += sent_length + 1
                    else:
                        if current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            chunks.append(chunk_text)
                        
                        # Start new chunk with overlap
                        if overlap_chars > 0 and chunks:
                            # Take last part of previous chunk for overlap
                            prev_chunk = chunks[-1]
                            overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk
                            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                            current_length = len(' '.join(current_chunk))
                        else:
                            current_chunk = [sentence]
                            current_length = sent_length
            else:
                # Paragraph fits in new chunk, start fresh
                # Add overlap from previous chunk if available
                if overlap_chars > 0 and chunks:
                    prev_chunk = chunks[-1]
                    overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk
                    current_chunk = [overlap_text, para] if overlap_text else [para]
                    current_length = len('\n\n'.join(current_chunk))
                else:
                    current_chunk = [para]
                    current_length = para_length
    
    # Add final chunk
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append(chunk_text)
    
    # Filter out very short chunks (likely artifacts)
    chunks = [chunk for chunk in chunks if len(chunk.strip()) > 50]
    
    return chunks

