# econai-layoutdetection

A Python project for detecting and analyzing document layouts using deep learning.

## Features

- It uses Layout Parser (https://layout-parser.github.io/) to find the internal structure of documents 
- Generates layouts in COCO JSON format
- Genrates PDFs with overlaid layouts

## Repository Structure

```
econai-layoutdetection/
├── tools/               # tools to preprocess, convert between formats, manipulate etc.
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
parse_pdf_layouts.py  # Runs layout detection model; input argument: single JSON config file
```

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/econai-layoutdetection.git
    cd econai-layoutdetection
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## License

MIT License

## Contact

For questions or contributions, open an issue or pull request.