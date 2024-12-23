# TCTMD PDF Downloader

This script automates the process of downloading all slide PDFs from the TCTMD website.

---

## Features
- Logs into the TCTMD website using provided credentials.
- Uses the TCTMD API to fetch presentation data and locate downloadable PDFs.
- Downloads PDFs to a specified directory.
- Includes a test mode to limit downloads to 2 PDFs for testing purposes.

---

## Prerequisites

### 1. Install Python
Make sure Python 3.x is installed on your system:
- **Windows**:
  - Download the installer from [python.org](https://www.python.org/downloads/).
  - During installation, check the box to "Add Python to PATH".
- **Mac/Linux**:
  - Open a terminal and type:
    ```bash
    python3 --version
    ```
  - If Python is not installed, refer to [python.org](https://www.python.org/downloads/) for installation instructions.

### 2. Verify Python Installation
Run the following command in your terminal to confirm Python is installed:
```bash
python --version
```
(or `python3 --version` on some systems).

---

## Installation

1. Clone this repository from GitHub:
```bash
git clone https://github.com/<your-github-username>/tctmd-downloader.git
```

2. Navigate to the project directory:
```bash
cd tctmd-downloader
```

3. Install the required Python libraries:
```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Set Your TCTMD Login Credentials
Open the script file (`tctmd_downloader.py`) in a text editor. Locate the following lines near the bottom of the script:
```python
USERNAME = "your_email@example.com"
PASSWORD = "your_password"
```
Replace `your_email@example.com` and `your_password` with your TCTMD username and password.

### 2. Enable or Disable Test Mode
- **Test Mode (default)**: The script will download only 2 PDFs for testing.
- To disable test mode (download all PDFs):
  - Locate this line in the script:
    ```python
    downloader = TCTMDDownloader(USERNAME, PASSWORD, test_mode=True)
    ```
  - Change `test_mode=True` to `test_mode=False`.

---

## Usage

1. Open a terminal and navigate to the directory containing the script:
```bash
cd tctmd-downloader
```

2. Run the script:
```bash
python tctmd_downloader.py
```

3. Monitor progress:
- The script logs detailed progress and errors in a file called `pdf_downloader.log`.
- Check the `downloads` directory for the downloaded PDFs.

---

## Troubleshooting

### 1. Common Issues
- **Python not found**: Ensure Python is installed and added to your system PATH.
- **Login failure**: Double-check your TCTMD username and password.
- **Missing dependencies**: Run `pip install -r requirements.txt` to ensure all libraries are installed.

### 2. Debugging
Check the log file (`pdf_downloader.log`) for detailed error messages.

---

## Notes
- Ensure your TCTMD account has access to the slides.
- Large downloads may take time depending on the number of slides and your internet speed.

---

## License
This script is provided as-is for educational and personal use. Use responsibly.
