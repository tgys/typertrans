"""
Wasabi S3-compatible failed titles cache implementation

This module provides caching functionality to track titles that failed to download
or extract, preventing repeated attempts on subsequent runs.
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Set, Dict, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    import wasabi
    WASABI_AVAILABLE = True
except ImportError:
    WASABI_AVAILABLE = False


class WasabiFailedTitlesCache:
    """
    Cache for tracking titles that failed to download/extract using Wasabi S3 storage
    with local backup functionality
    """
    
    def __init__(self, access_key="O9YRIDWGSOTFW07SB6AK", bucket_name="typertrs", 
                 cache_key="failed_titles.json", local_backup="failed_titles_backup.json"):
        self.access_key = access_key
        self.bucket_name = bucket_name
        self.cache_key = cache_key
        self.local_backup = Path(local_backup)
        
        # Initialize wasabi logger if available
        if WASABI_AVAILABLE:
            self.msg = wasabi.Printer()
        else:
            # Fallback to simple print-based logger
            self.msg = self._create_fallback_logger()
        
        # Initialize S3 client and load cache
        self.s3_client = None
        self.failed_titles: Set[str] = set()
        self._init_s3_client()
        self._load_cache()
    
    def _create_fallback_logger(self):
        """Create a simple fallback logger when wasabi is not available"""
        class FallbackLogger:
            def good(self, msg): print(f"✅ {msg}")
            def info(self, msg): print(f"ℹ️  {msg}")
            def warn(self, msg): print(f"⚠️  {msg}")
            def fail(self, msg): print(f"❌ {msg}")
        return FallbackLogger()
    
    def _init_s3_client(self):
        """Initialize the S3 client for Wasabi storage"""
        if not BOTO3_AVAILABLE:
            self.msg.warn("boto3 not available, using local cache only")
            return
            
        try:
            # Get secret key from environment
            secret_key = os.getenv('WASABI_SECRET_KEY')
            if not secret_key:
                self.msg.fail("WASABI_SECRET_KEY environment variable not set")
                return
                
            self.s3_client = boto3.client(
                's3',
                endpoint_url='https://s3.wasabisys.com',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=secret_key,
                region_name='us-east-1',
                config=boto3.session.Config(
                    s3={'addressing_style': 'path'},
                    signature_version='s3v4'
                )
            )
            
            # Test connection by listing buckets and checking if our bucket exists
            response = self.s3_client.list_buckets()
            bucket_names = [bucket['Name'] for bucket in response.get('Buckets', [])]
            if self.bucket_name not in bucket_names:
                self.msg.fail(f"Bucket '{self.bucket_name}' not found in available buckets: {bucket_names}")
                self.s3_client = None
                return
            self.msg.good("Connected to Wasabi storage")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.msg.fail(f"Bucket '{self.bucket_name}' not found")
            else:
                self.msg.fail(f"Failed to connect to Wasabi: {e}")
            self.s3_client = None
        except Exception as e:
            self.msg.fail(f"Failed to initialize Wasabi client: {e}")
            self.s3_client = None
    
    def _load_cache(self):
        """Load failed titles cache from Wasabi or local backup"""
        # Try loading from Wasabi first
        if self.s3_client:
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.cache_key)
                cache_data = json.loads(response['Body'].read().decode('utf-8'))
                
                # Handle both old format (list) and new format (dict with metadata)
                if isinstance(cache_data, list):
                    self.failed_titles = set(cache_data)
                elif isinstance(cache_data, dict) and 'failed_titles' in cache_data:
                    self.failed_titles = set(cache_data['failed_titles'])
                else:
                    self.failed_titles = set()
                
                self.msg.good(f"Loaded {len(self.failed_titles)} failed titles from Wasabi")
                
                # Save local backup
                self._save_local_backup()
                return
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NoSuchKey':
                    # Silently handle missing cache file
                    logging.getLogger('wasabi_cache').debug("No cache file found in Wasabi, starting fresh")
                elif error_code == 'AuthorizationHeaderMalformed':
                    # Silently log authorization issues (common with region mismatches)
                    logging.getLogger('wasabi_cache').debug(f"Authorization header issue (logged): {e}")
                else:
                    self.msg.warn(f"Failed to load from Wasabi: {e}")
            except Exception as e:
                self.msg.warn(f"Error loading from Wasabi: {e}")
        
        # Fallback to local backup
        if self.local_backup.exists():
            try:
                with open(self.local_backup, 'r') as f:
                    cache_data = json.load(f)
                    
                # Handle both old format (list) and new format (dict with metadata)
                if isinstance(cache_data, list):
                    self.failed_titles = set(cache_data)
                elif isinstance(cache_data, dict) and 'failed_titles' in cache_data:
                    self.failed_titles = set(cache_data['failed_titles'])
                else:
                    self.failed_titles = set()
                    
                # Silently load from local backup
                logging.getLogger('wasabi_cache').debug(f"Loaded {len(self.failed_titles)} failed titles from local backup")
            except Exception as e:
                self.msg.warn(f"Failed to load local backup: {e}")
                self.failed_titles = set()
        else:
            self.failed_titles = set()
            # Silently start with empty cache
            logging.getLogger('wasabi_cache').debug("Starting with empty failed titles cache")
    
    def _save_cache(self):
        """Save failed titles cache to Wasabi and local backup"""
        # Create cache data with metadata
        cache_data = {
            'failed_titles': list(self.failed_titles),
            'last_updated': time.time(),
            'total_count': len(self.failed_titles)
        }
        
        # Save to Wasabi
        if self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self.cache_key,
                    Body=json.dumps(cache_data, indent=2),
                    ContentType='application/json'
                )
                self.msg.good("Saved cache to Wasabi")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'AuthorizationHeaderMalformed':
                    # Silently log authorization issues (common with region mismatches)
                    logging.getLogger('wasabi_cache').debug(f"Authorization header issue during save (logged): {e}")
                else:
                    # Silently log save failures
                    logging.getLogger('wasabi_cache').debug(f"Failed to save to Wasabi: {e}")
            except Exception as e:
                # Silently log save failures
                logging.getLogger('wasabi_cache').debug(f"Failed to save to Wasabi: {e}")
        
        # Always save local backup
        self._save_local_backup(cache_data)
    
    def _save_local_backup(self, cache_data=None):
        """Save local backup of the cache"""
        if cache_data is None:
            cache_data = {
                'failed_titles': list(self.failed_titles),
                'last_updated': time.time(),
                'total_count': len(self.failed_titles)
            }
        
        try:
            with open(self.local_backup, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            # Silently log local backup failures
            logging.getLogger('wasabi_cache').debug(f"Failed to save local backup: {e}")
    
    def add_failed(self, title: str, reason: str = "unknown"):
        """Add a title to the failed cache"""
        if not title or not title.strip():
            return
            
        title = title.strip()
        self.failed_titles.add(title)
        self._save_cache()
        # Silently add to failed cache
        logging.getLogger('wasabi_cache').debug(f"Added to failed cache: {title} (reason: {reason})")
    
    def is_failed(self, title: str) -> bool:
        """Check if a title is in the failed cache"""
        if not title:
            return False
        return title.strip() in self.failed_titles
    
    def should_skip(self, title: str) -> bool:
        """Check if a title should be skipped due to previous failure"""
        if self.is_failed(title):
            # Silently skip previously failed title
            logging.getLogger('wasabi_cache').debug(f"Skipping previously failed title: {title}")
            return True
        return False
    
    def remove_failed(self, title: str):
        """Remove a title from failed cache if you want to retry it"""
        if not title:
            return
            
        title = title.strip()
        if title in self.failed_titles:
            self.failed_titles.remove(title)
            self._save_cache()
            self.msg.good(f"Removed from failed cache: {title}")
    
    def clear_cache(self):
        """Clear all failed titles"""
        self.failed_titles.clear()
        self._save_cache()
        self.msg.good("Cleared failed titles cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_failed': len(self.failed_titles),
            'failed_titles': list(self.failed_titles),
            'wasabi_connected': self.s3_client is not None,
            'local_backup_exists': self.local_backup.exists()
        }
    
    def bulk_add_failed(self, titles: list, reason: str = "bulk_add"):
        """Add multiple titles to failed cache efficiently"""
        if not titles:
            return
            
        added_count = 0
        for title in titles:
            if title and title.strip() and title.strip() not in self.failed_titles:
                self.failed_titles.add(title.strip())
                added_count += 1
        
        if added_count > 0:
            self._save_cache()
            # Silently bulk add to failed cache
            logging.getLogger('wasabi_cache').debug(f"Bulk added {added_count} titles to failed cache (reason: {reason})")
    
    def export_failed_list(self, file_path: str):
        """Export failed titles list to a text file"""
        try:
            with open(file_path, 'w') as f:
                for title in sorted(self.failed_titles):
                    f.write(f"{title}\n")
            self.msg.good(f"Exported {len(self.failed_titles)} failed titles to {file_path}")
        except Exception as e:
            self.msg.fail(f"Failed to export failed titles: {e}")


# Convenience function for easy import
def create_cache(access_key="O9YRIDWGSOTFW07SB6AK", bucket_name="typertrs") -> WasabiFailedTitlesCache:
    """Create and return a WasabiFailedTitlesCache instance"""
    return WasabiFailedTitlesCache(access_key=access_key, bucket_name=bucket_name)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Wasabi Failed Titles Cache...")
    
    cache = create_cache()
    
    # Test adding and checking failed titles
    test_titles = ["Test Title 1", "Test Title 2", "Test Title 3"]
    
    print(f"\nInitial stats: {cache.get_stats()}")
    
    # Add some test failures
    cache.add_failed(test_titles[0], "download_failed")
    cache.add_failed(test_titles[1], "extraction_failed")
    
    # Test bulk add
    cache.bulk_add_failed([test_titles[2]], "test_bulk_add")
    
    print(f"After adding failures: {cache.get_stats()}")
    
    # Test should_skip
    for title in test_titles:
        print(f"Should skip '{title}': {cache.should_skip(title)}")
    
    # Test with a new title
    print(f"Should skip 'New Title': {cache.should_skip('New Title')}")
    
    # Remove one and test again
    cache.remove_failed(test_titles[0])
    print(f"After removing '{test_titles[0]}': {cache.should_skip(test_titles[0])}")
    
    print(f"\nFinal stats: {cache.get_stats()}")