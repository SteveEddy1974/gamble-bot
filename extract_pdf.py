#!/usr/bin/env python3
"""Extract text from the Betfair Games API PDF guide."""
import PyPDF2
import sys

pdf_path = "Betfair-Exchange-Games-API-User-Guide.pdf"

try:
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        print(f"Total pages: {len(reader.pages)}")
        print("\n" + "="*80)
        print("EXTRACTING TEXT FROM PDF")
        print("="*80 + "\n")
        
        full_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            full_text.append(f"\n--- PAGE {i+1} ---\n{text}")
        
        combined = "\n".join(full_text)
        
        # Save to file
        with open("pdf_extracted_text.txt", "w", encoding="utf-8") as out:
            out.write(combined)
        
        print(f"Extracted {len(combined)} characters")
        print("Saved to: pdf_extracted_text.txt")
        
        # Print first 5000 chars to see what we have
        print("\n" + "="*80)
        print("FIRST 5000 CHARACTERS:")
        print("="*80)
        print(combined[:5000])
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
