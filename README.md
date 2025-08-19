# Gofile Downloader

A command-line tool to download files from Gofile.io to a network mount on Ubuntu.

## Features

- Download files from Gofile.io using file codes
- Save files to a specified directory (including network mounts)
- Progress bar for download tracking
- Custom filename support
- Verbose logging option
- Support for premium users with API token

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/gofile-dl.git
   cd gofile-dl
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make the script executable:
   ```
   chmod +x gofile_dl.py
   ```

## Usage

Basic usage:
```
./gofile_dl.py FILE_CODE
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

## Notes

- This tool requires an active internet connection
- Network mounts should be properly configured and accessible before using this tool
