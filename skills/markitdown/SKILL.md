---
name: markitdown
description: Convert documents and media files to Markdown using Microsoft's official markitdown tool. Use when the user asks to extract, inspect, summarize, or convert PDFs, DOCX, PPTX, XLSX, HTML, images, audio, or other supported files into Markdown/text, especially before analysis by an agent.
license: MIT
metadata:
  version: "0.1.6"
  category: document-processing
  sources:
    - https://github.com/microsoft/markitdown
    - https://pypi.org/project/markitdown/
---

# MarkItDown

Use Microsoft's `markitdown` package for lightweight file-to-Markdown conversion.

## Setup Check

Before first use in a session, check the active Python environment:

```bash
python -m markitdown --version
```

If missing, install the official package:

```bash
python -m pip install markitdown
```

## Basic Usage

Convert a file and print Markdown to stdout:

```bash
python -m markitdown input.pdf
```

Convert a file and save output:

```bash
python -m markitdown input.docx -o output.md
```

Use extension hints when reading from stdin or when the file has no reliable extension:

```bash
python -m markitdown -x pdf < input.bin > output.md
```

## Workflow

1. Prefer `markitdown` for fast text extraction from common office, web, and media formats.
2. Write extracted Markdown to a temporary or requested `.md` file when downstream analysis needs stable line references.
3. Inspect the converted Markdown before relying on it; complex layouts, scanned PDFs, tables, and slide decks may need a specialized document, spreadsheet, PDF, or presentation skill after extraction.
4. Do not overwrite the original file. Save conversion output beside the source only when the user asks for a deliverable or when a stable intermediate artifact is useful.

## Azure Options

Offline conversion is the default. Use Azure Document Intelligence or Azure Content Understanding only when the user asks for it or when offline extraction is insufficient and the required endpoint is available:

```bash
python -m markitdown input.pdf --use-docintel --endpoint "$AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
python -m markitdown input.pdf --use-cu --cu-endpoint "$AZURE_CONTENT_UNDERSTANDING_ENDPOINT"
```
