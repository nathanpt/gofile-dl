#!/usr/bin/env python3
"""
Gofile Downloader - A CLI tool to download files from Gofile.io to a network mount
"""

import os
import sys
import json
import logging
import requests
from tqdm import tqdm
import click

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('gofile-dl')

class GofileDownloader:
    """Class to handle downloading files from Gofile.io"""
    
    BASE_URL = "https://api.gofile.io"
    
    def __init__(self, output_dir=None, verbose=False, token=None):
        """Initialize the downloader with optional output directory and token"""
        self.output_dir = output_dir or os.getcwd()
        self.verbose = verbose
        self.token = token  # API token for premium users
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                logger.debug(f"Created output directory: {self.output_dir}")
            except OSError as e:
                logger.error(f"Failed to create output directory: {e}")
                sys.exit(1)
    
    def get_server(self):
        """Get the best server for API operations"""
        url = f"{self.BASE_URL}/getServer"
        
        try:
            logger.debug("Getting best server for operations")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                error_msg = data.get('data', {}).get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return None
            
            return data.get('data', {}).get('server')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get server: {e}")
            return None
    
    def get_file_info(self, file_code):
        """Get information about a file using its code"""
        url = f"{self.BASE_URL}/getContent"
        
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        params = {'contentId': file_code}
        
        try:
            logger.debug(f"Getting file info for code: {file_code}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                error_msg = data.get('data', {}).get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return None
            
            return data.get('data', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    def download_file(self, file_code, custom_filename=None):
        """Download a file from Gofile using its code"""
        # Get file information first
        file_info = self.get_file_info(file_code)
        
        if not file_info:
            logger.error(f"Could not retrieve information for file code: {file_code}")
            return False
        
        # Extract file information from the response
        content_data = file_info.get('contents', {})
        
        if not content_data:
            logger.error("No file content information available")
            return False
        
        # Find the file in the contents
        file_data = None
        for content_id, content in content_data.items():
            if content.get('type') == 'file':
                file_data = content
                break
        
        if not file_data:
            logger.error("No file found in the content data")
            return False
        
        # Get download link
        download_url = file_data.get('link')
        if not download_url:
            logger.error("No download link available")
            return False
        
        # Determine filename
        if custom_filename:
            filename = custom_filename
        else:
            filename = file_data.get('name', f"gofile_{file_code}")
        
        output_path = os.path.join(self.output_dir, filename)
        
        # Download the file with progress bar
        try:
            logger.info(f"Downloading {filename} to {self.output_dir}")
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                with open(output_path, 'wb') as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as progress_bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress_bar.update(len(chunk))
            
            logger.info(f"Successfully downloaded {filename}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed: {e}")
            # Clean up partial download if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
        except IOError as e:
            logger.error(f"Failed to write file: {e}")
            return False


@click.command()
@click.argument('file_code')
@click.option('--output', '-o', help='Output directory or file path')
@click.option('--filename', '-f', help='Custom filename for the downloaded file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--token', '-t', help='API token for premium users')
def main(file_code, output, filename, verbose, token):
    """
    Download files from Gofile.io using their file codes.
    
    FILE_CODE is the unique identifier for the file on Gofile.io
    """
    # Determine if output is a directory or a specific file path
    output_dir = None
    custom_filename = filename
    
    if output:
        if os.path.isdir(output) or output.endswith('/') or output.endswith('\\'):
            output_dir = output
        else:
            # If output doesn't exist or doesn't end with / or \, assume it's a file path
            output_dir = os.path.dirname(output)
            if not custom_filename:
                custom_filename = os.path.basename(output)
    
    downloader = GofileDownloader(output_dir=output_dir, verbose=verbose, token=token)
    success = downloader.download_file(file_code, custom_filename=custom_filename)
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
