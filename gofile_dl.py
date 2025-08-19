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
    
    def get_file_info(self, file_code, password=None):
        """Get information about a file using its code
        
        Args:
            file_code (str): The Gofile content ID
            password (str, optional): Password for protected content
            
        Returns:
            dict: File information or None if an error occurred
                 Returns {'password_required': True} if password is needed
        """
        url = f"{self.BASE_URL}/contents/{file_code}"
        
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            logger.debug("Using premium token for authentication")
        
        # Add query parameters similar to what the gofile-downloader uses
        params = {
            'wt': '4fd6sg89d7s6',  # This seems to be a required parameter
            'cache': 'true',
            'sortField': 'createTime',
            'sortDirection': '1'
        }
        
        # Add password if provided
        if password:
            import hashlib
            # Hash the password with SHA-256 as seen in the gofile-downloader
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            params['password'] = hashed_password
            logger.debug("Password provided and hashed for authentication")
        
        try:
            logger.debug(f"Getting file info for code: {file_code}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                error_msg = data.get('data', {}).get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return None
            
            # Check if password is required but not provided or incorrect
            data_content = data.get('data', {})
            if 'password' in data_content and data_content.get('passwordStatus') != 'passwordOk':
                logger.error("Password required or incorrect password provided")
                return {'password_required': True}
            
            return data_content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    def download_file(self, file_code, custom_filename=None, password=None, download_all=False):
        """Download a file from Gofile using its code
        
        Args:
            file_code (str): The Gofile content ID or URL
            custom_filename (str, optional): Custom filename for the downloaded file
            password (str, optional): Password for protected content
            download_all (bool, optional): Download all files if content is a folder
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        # Get file information first
        logger.info(f"Retrieving information for content: {file_code}")
        file_info = self.get_file_info(file_code, password)
        
        if not file_info:
            logger.error(f"Could not retrieve information for file code: {file_code}")
            logger.error("Please check if the file code is correct and the content still exists")
            return False
        
        # Check if password is required
        if file_info.get('password_required'):
            logger.error("This content is password protected. Please provide a password using the --password option.")
            return False
        
        # Check if this is a folder or a file
        content_type = file_info.get('type')
        
        if content_type == 'file':
            # Direct file download
            download_url = file_info.get('link')
            if not download_url:
                logger.error("No download link available")
                return False
                
            # Determine filename
            if custom_filename:
                filename = custom_filename
            else:
                filename = file_info.get('name', f"gofile_{file_code}")
                
            # Download the single file
            return self._download_single_file(download_url, filename)
                
        elif content_type == 'folder':
            # Handle folder with children
            children = file_info.get('children', {})
            
            if not children:
                logger.error("Folder is empty")
                return False
            
            # If download_all is True, download all files in the folder
            if download_all:
                return self._download_folder_contents(children, custom_filename)
            else:
                # Find the first file in the folder
                file_data = None
                for child_id, child in children.items():
                    if child.get('type') == 'file':
                        file_data = child
                        break
                        
                if not file_data:
                    logger.error("No file found in the folder")
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
                    
                # Download the single file
                return self._download_single_file(download_url, filename)
        else:
            logger.error(f"Unknown content type: {content_type}")
            return False
        
    def _download_single_file(self, download_url, filename):
        """Download a single file from the given URL"""
        output_path = os.path.join(self.output_dir, filename)
        
        # Download the file with progress bar
        try:
            logger.info(f"Downloading {filename} to {self.output_dir}")
            
            # Set stream=True to download in chunks and verify=True for SSL verification
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            with requests.get(download_url, stream=True, headers=headers, verify=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                # Verify we got a content-length header
                if total_size == 0:
                    logger.warning(f"Content-Length header missing or zero for {filename}. Download may be incomplete.")
                
                # Open file in binary write mode
                with open(output_path, 'wb') as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    disable=total_size == 0,  # Disable progress bar if size unknown
                ) as progress_bar:
                    downloaded_size = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            progress_bar.update(len(chunk))
            
            # Verify file size after download
            actual_size = os.path.getsize(output_path)
            if total_size > 0 and actual_size < total_size:
                logger.error(f"Downloaded file size ({actual_size} bytes) is smaller than expected ({total_size} bytes). File may be corrupt.")
                return False
                
            logger.info(f"Successfully downloaded {filename} ({actual_size} bytes)")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed: {e}")
            # Clean up partial download if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
        except IOError as e:
            logger.error(f"Failed to write file: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    def _download_folder_contents(self, children, custom_folder_name=None):
        """Download all files in a folder"""
        if custom_folder_name:
            # Create a subfolder with the custom name if specified
            folder_path = os.path.join(self.output_dir, custom_folder_name)
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                    logger.debug(f"Created folder: {folder_path}")
                except OSError as e:
                    logger.error(f"Failed to create folder: {e}")
                    return False
            # Update output_dir temporarily for this download
            original_output_dir = self.output_dir
            self.output_dir = folder_path
        
        success_count = 0
        total_files = 0
        
        # Count total files first
        for child_id, child in children.items():
            if child.get('type') == 'file':
                total_files += 1
        
        if total_files == 0:
            logger.error("No files found in the folder")
            # Restore original output directory if it was changed
            if custom_folder_name:
                self.output_dir = original_output_dir
            return False
        
        logger.info(f"Found {total_files} files to download")
        
        # Download each file
        for child_id, child in children.items():
            if child.get('type') == 'file':
                download_url = child.get('link')
                filename = child.get('name')
                
                if not download_url or not filename:
                    logger.warning(f"Skipping file with missing information: {child_id}")
                    continue
                
                if self._download_single_file(download_url, filename):
                    success_count += 1
        
        # Restore original output directory if it was changed
        if custom_folder_name:
            self.output_dir = original_output_dir
        
        logger.info(f"Downloaded {success_count} of {total_files} files")
        return success_count > 0


@click.command()
@click.argument('file_code')
@click.option('--output', '-o', help='Output directory or file path')
@click.option('--filename', '-f', help='Custom filename for the downloaded file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--token', '-t', help='API token for premium users')
@click.option('--password', '-p', help='Password for protected content')
@click.option('--all', '-a', is_flag=True, help='Download all files if the content is a folder')
def main(file_code, output, filename, verbose, token, password, all):
    """
    Download files from Gofile.io using their file codes.
    
    FILE_CODE is the unique identifier for the file on Gofile.io
    """
    # Extract file code from URL if a full URL was provided
    extracted_code = extract_file_code(file_code)
    if extracted_code:
        if verbose:
            logger.info(f"Extracted file code '{extracted_code}' from URL")
        file_code = extracted_code
    
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
    success = downloader.download_file(file_code, custom_filename=custom_filename, password=password, download_all=all)
    
    if not success:
        sys.exit(1)


def extract_file_code(input_string):
    """
    Extract the file code from various formats of Gofile URLs or direct codes.
    
    Args:
        input_string (str): The input string which could be a URL or file code
        
    Returns:
        str or None: Extracted file code or None if extraction failed
        
    Handles formats like:
    - https://gofile.io/d/abc123
    - gofile.io/d/abc123
    - abc123 (direct code)
    """
    import re
    
    # If it's already just a code (no slashes or dots), return as is
    if '/' not in input_string and '.' not in input_string:
        return input_string
    
    # Try to extract from URL format
    url_pattern = r'(?:https?://)?(?:www\.)?gofile\.io/d/([a-zA-Z0-9]+)'
    match = re.search(url_pattern, input_string)
    
    if match:
        return match.group(1)
    
    # If no match found, return None
    logger.warning(f"Could not extract a valid file code from: {input_string}")
    logger.warning("Please provide a valid Gofile URL (https://gofile.io/d/CODE) or just the file code")
    return None


if __name__ == '__main__':
    main()
