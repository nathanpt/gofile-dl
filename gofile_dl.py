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
                
            # Ensure we're using the direct download URL
            # Sometimes Gofile returns a URL that needs to be modified for direct download
            if 'gofile.io' in download_url and '/download/' not in download_url:
                # Convert from /d/ format to /download/ format if needed
                download_url = download_url.replace('/d/', '/download/')
                logger.debug(f"Modified download URL: {download_url}")
                
            # Use custom filename if provided, otherwise use the original filename
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
                    
                # Ensure we're using the direct download URL
                if 'gofile.io' in download_url and '/download/' not in download_url:
                    # Convert from /d/ format to /download/ format if needed
                    download_url = download_url.replace('/d/', '/download/')
                    logger.debug(f"Modified download URL: {download_url}")
                    
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
        
        # Try different approaches to download the file
        approaches = [
            self._download_with_requests,
            self._download_with_urllib,
            self._download_with_requests_session,
            self._download_with_browser_simulation
        ]
        
        for i, download_approach in enumerate(approaches):
            try:
                logger.info(f"Downloading {filename} to {self.output_dir} (attempt {i+1})")
                success = download_approach(download_url, output_path, filename)
                if success:
                    return True
                logger.warning(f"Download attempt {i+1} failed, trying next approach...")
            except Exception as e:
                logger.error(f"Error in download attempt {i+1}: {e}")
                # Continue to next approach
        
        logger.error(f"All download attempts failed for {filename}")
        return False
        
    def _download_with_requests(self, download_url, output_path, filename):
        """Download a file using the requests library"""
        # Set comprehensive headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://gofile.io/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
        
        # First make a HEAD request to get the content length
        try:
            head_response = requests.head(download_url, headers=headers, timeout=10)
            head_response.raise_for_status()
            total_size = int(head_response.headers.get('content-length', 0))
            logger.debug(f"HEAD request content-length: {total_size}")
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.warning(f"Failed to get content length with HEAD request: {e}")
            total_size = 0
        
        # Now make the actual GET request to download the file
        with requests.get(download_url, stream=True, headers=headers, verify=True, timeout=30) as r:
            r.raise_for_status()
            
            # If we didn't get content length from HEAD, try from GET
            if total_size == 0:
                total_size = int(r.headers.get('content-length', 0))
                logger.debug(f"GET request content-length: {total_size}")
            
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
        logger.info(f"Downloaded file size: {actual_size} bytes")
        
        if total_size > 0 and actual_size < total_size:
            logger.error(f"Downloaded file size ({actual_size} bytes) is smaller than expected ({total_size} bytes). File may be corrupt.")
            return False
            
        logger.info(f"Successfully downloaded {filename} ({actual_size} bytes)")
        return True
        
    def _download_with_urllib(self, download_url, output_path, filename):
        """Download a file using urllib"""
        import urllib.request
        
        logger.info(f"Trying urllib download approach for {filename}")
        
        # Create a Request object with headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://gofile.io/'
        }
        
        req = urllib.request.Request(download_url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response, open(output_path, 'wb') as out_file:
                # Get content length if available
                content_length = response.getheader('Content-Length')
                total_size = int(content_length) if content_length else 0
                
                if total_size == 0:
                    logger.warning(f"Content-Length header missing in urllib approach")
                
                # Setup progress bar
                with tqdm(
                    desc=filename,
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    disable=total_size == 0,
                ) as progress_bar:
                    downloaded_size = 0
                    while True:
                        buffer = response.read(8192)
                        if not buffer:
                            break
                        out_file.write(buffer)
                        downloaded_size += len(buffer)
                        progress_bar.update(len(buffer))
            
            actual_size = os.path.getsize(output_path)
            logger.info(f"Downloaded file size with urllib: {actual_size} bytes")
            
            if total_size > 0 and actual_size < total_size:
                logger.error(f"Downloaded file size ({actual_size} bytes) is smaller than expected ({total_size} bytes)")
                return False
                
            return True
        except Exception as e:
            logger.error(f"urllib download failed: {e}")
            return False
            
    def _download_with_requests_session(self, download_url, output_path, filename):
        """Download a file using a requests session with different parameters"""
        logger.info(f"Trying requests session download approach for {filename}")
        
        session = requests.Session()
        
        # Set different headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            # Try to download with a session
            response = session.get(download_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f, tqdm(
                desc=filename,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                disable=total_size == 0,
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
            
            actual_size = os.path.getsize(output_path)
            logger.info(f"Downloaded file size with session: {actual_size} bytes")
            
            if actual_size > 0:
                return True
            return False
        except Exception as e:
            logger.error(f"Session download failed: {e}")
            return False
            
    def _download_with_browser_simulation(self, download_url, output_path, filename):
        """Download a file by simulating a browser more closely"""
        logger.info(f"Trying browser simulation download approach for {filename}")
        
        # Create a session that will persist cookies and follow redirects
        session = requests.Session()
        
        # Set very browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://gofile.io/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        
        try:
            # First visit the main gofile.io site to get cookies
            logger.debug("Visiting gofile.io to establish session")
            session.get('https://gofile.io/', headers=headers, timeout=10)
            
            # If we have a /d/ URL, first visit the page to get any necessary cookies/tokens
            if '/d/' in download_url:
                logger.debug("Visiting download page to get necessary cookies/tokens")
                page_url = download_url
                session.get(page_url, headers=headers, timeout=10)
                
                # Convert to direct download URL if needed
                if '/download/' not in download_url:
                    download_url = download_url.replace('/d/', '/download/')
                    logger.debug(f"Modified to direct download URL: {download_url}")
            
            # Try a different URL format if it's a gofile.io URL
            if 'gofile.io' in download_url:
                # Extract the file code from the URL
                file_code = None
                if '/d/' in download_url:
                    file_code = download_url.split('/d/')[1].split('/')[0]
                elif '/download/' in download_url:
                    file_code = download_url.split('/download/')[1].split('/')[0]
                
                if file_code:
                    # Try the direct API download URL format
                    api_download_url = f"https://api.gofile.io/contents/{file_code}/download"
                    logger.debug(f"Trying API download URL: {api_download_url}")
                    
                    # Add the token if available
                    if self.api_token:
                        api_download_url += f"?token={self.api_token}"
                    
                    # Try this URL first
                    try:
                        response = session.get(api_download_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
                        if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 0:
                            download_url = api_download_url
                            logger.debug("Using API download URL")
                    except Exception:
                        logger.debug("API download URL failed, falling back to original URL")
            
            # Now try to download the file
            logger.debug(f"Downloading from URL: {download_url}")
            response = session.get(download_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Check if we got redirected and log the final URL
            if response.url != download_url:
                logger.debug(f"Redirected to: {response.url}")
            
            # Get content length if available
            total_size = int(response.headers.get('content-length', 0))
            logger.debug(f"Content-Length from response: {total_size}")
            
            # Log all headers for debugging
            logger.debug("Response headers:")
            for header, value in response.headers.items():
                logger.debug(f"  {header}: {value}")
            
            # Download the file with progress bar
            with open(output_path, 'wb') as f, tqdm(
                desc=filename,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                disable=total_size == 0,
            ) as progress_bar:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress_bar.update(len(chunk))
            
            # Verify file size
            actual_size = os.path.getsize(output_path)
            logger.info(f"Downloaded file size with browser simulation: {actual_size} bytes")
            
            # Check if the file seems too small (less than 10KB)
            if actual_size < 10240 and '.jpg' in filename.lower():
                # For images, this is suspiciously small
                with open(output_path, 'rb') as f:
                    content = f.read(100)  # Read first 100 bytes
                    # Check if it's HTML instead of binary data
                    if b'<!DOCTYPE html>' in content or b'<html' in content:
                        logger.error("Downloaded content appears to be HTML, not the expected file")
                        return False
            
            if actual_size > 0:
                return True
            return False
        except Exception as e:
            logger.error(f"Browser simulation download failed: {e}")
            return False
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
                    
                # Ensure we're using the direct download URL
                if 'gofile.io' in download_url and '/download/' not in download_url:
                    # Convert from /d/ format to /download/ format if needed
                    download_url = download_url.replace('/d/', '/download/')
                    logger.debug(f"Modified download URL: {download_url}")
                
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
