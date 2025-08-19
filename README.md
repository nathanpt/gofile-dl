# Gofile Downloader

A command-line tool to download files from Gofile.io to a network mount on Ubuntu.

## Features

- Download files from Gofile.io using file codes or URLs
- Save files to a specified directory (including network mounts)
- Progress bar for download tracking
- Custom filename support
- Verbose logging option
- Support for premium users with API token
- Support for password-protected files
- Download all files from a folder

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/gofile-dl.git
   cd gofile-dl
   ```

2. Install dependencies using one of these methods:

   **Option A: Using a virtual environment (recommended)**
   ```bash
   # Make sure you have python3-venv installed
   sudo apt install python3-venv
   
   # Create a virtual environment
   python3 -m venv venv
   
   # Activate the virtual environment
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

   **Option B: Using system packages**
   ```bash
   sudo apt install python3-requests python3-click python3-tqdm
   ```

   **Option C: Using pipx for isolated installation**
   ```bash
   # Install pipx if not already installed
   sudo apt install pipx
   pipx ensurepath
   
   # Install the application
   pipx install --spec . gofile-dl
   ```

3. Make the script executable (if using Option A or B):
   ```
   chmod +x gofile_dl.py
   ```

## Usage

Basic usage:
```
./gofile_dl.py FILE_CODE
```

You can also use a full Gofile URL:
```
./gofile_dl.py https://gofile.io/d/abc123
```

With options:
```
./gofile_dl.py FILE_CODE --output /path/to/network/mount/ --filename custom_name.ext --verbose
```

For premium users:
```
./gofile_dl.py FILE_CODE --token YOUR_API_TOKEN
```

### Options

- `FILE_CODE`: The unique identifier for the file on Gofile.io
- `--output, -o`: Output directory or file path
- `--filename, -f`: Custom filename for the downloaded file
- `--verbose, -v`: Enable verbose logging
- `--token, -t`: API token for premium users (get from your Gofile.io account)
- `--password, -p`: Password for protected content
- `--all, -a`: Download all files if the content is a folder

## Examples

Download a file to the current directory:
```
./gofile_dl.py abc123
```

Download to a network mount with a custom filename:
```
./gofile_dl.py abc123 --output /mnt/network_share/ --filename important_document.pdf
```

Download as a premium user to a network mount:
```
./gofile_dl.py abc123 --output /mnt/network_share/ --token YOUR_API_TOKEN
```

Download a password-protected file:
```
./gofile_dl.py abc123 --password YOUR_PASSWORD
```

Download all files from a folder:
```
./gofile_dl.py abc123 --all
```

Download all files from a folder to a specific directory with a custom folder name:
```
./gofile_dl.py abc123 --all --output /mnt/network_share/ --filename custom_folder_name
```

## Notes

- This tool requires an active internet connection
- Network mounts should be properly configured and accessible before using this tool
