"""
Polygon.io S3 Bulk Downloader for Historical Options Data

Uses S3-compatible endpoints to download bulk historical data from Polygon.io.
This bypasses the REST API rate limits and provides access to larger datasets.

S3 Credentials Required:
- POLYGON_ACCESS_KEY_ID
- POLYGON_SECRET_ACCESS_KEY  
- POLYGON_S3_ENDPOINT
- POLYGON_BUCKET
"""

import os
import boto3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
import structlog
from dotenv import load_dotenv
import gzip
import io

load_dotenv()
logger = structlog.get_logger()


class PolygonS3BulkDownloader:
    """Downloads bulk historical data from Polygon.io S3 endpoints."""
    
    def __init__(self):
        """Initialize S3 client for Polygon.io."""
        self.access_key_id = os.getenv('POLYGON_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('POLYGON_SECRET_ACCESS_KEY')
        self.endpoint_url = os.getenv('POLYGON_S3_ENDPOINT')
        self.bucket_name = os.getenv('POLYGON_BUCKET')
        
        if not all([self.access_key_id, self.secret_access_key, self.endpoint_url, self.bucket_name]):
            raise ValueError("Missing S3 credentials in environment variables")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        )
        
        logger.info("polygon_s3_client_initialized", 
                   endpoint=self.endpoint_url,
                   bucket=self.bucket_name)
    
    def list_available_data(self, prefix: str = "") -> List[str]:
        """
        List available data files in the S3 bucket.
        
        Args:
            prefix: S3 prefix to filter files (e.g., "options/", "stocks/")
            
        Returns:
            List of available file paths
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append(obj['Key'])
            
            logger.info("s3_files_listed", count=len(files), prefix=prefix)
            return files
            
        except Exception as e:
            logger.error("s3_list_failed", error=str(e), prefix=prefix)
            return []
    
    def get_options_data_structure(self) -> Dict[str, Any]:
        """
        Explore the options data directory structure.
        
        Returns:
            Dictionary with available options data paths
        """
        try:
            # Actual options data paths in Polygon S3
            options_prefixes = [
                "us_options_opra/",  # US options OPRA data
                "us_options_sip/",   # US options SIP data
                "options/",
                "us_options/",
                "options_data/",
                "derivatives/",
                "options_contracts/",
                "options_quotes/",
                "options_trades/"
            ]
            
            structure = {}
            for prefix in options_prefixes:
                files = self.list_available_data(prefix)
                if files:
                    structure[prefix] = files[:10]  # First 10 files as sample
            
            logger.info("options_data_structure_explored", 
                       prefixes_found=list(structure.keys()))
            return structure
            
        except Exception as e:
            logger.error("options_structure_exploration_failed", error=str(e))
            return {}
    
    def download_options_file(self, file_path: str, local_path: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Download and parse a single options data file.
        
        Args:
            file_path: S3 path to the file
            local_path: Local path to save the file (optional)
            
        Returns:
            DataFrame with the data or None if failed
        """
        try:
            # Download file
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            # Read file content
            content = response['Body'].read()
            
            # Handle gzipped files
            if file_path.endswith('.gz'):
                content = gzip.decompress(content)
            
            # Parse CSV data
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            
            # Save locally if requested
            if local_path:
                df.to_csv(local_path, index=False)
                logger.info("options_file_saved", local_path=local_path)
            
            logger.info("options_file_downloaded", 
                       file_path=file_path,
                       rows=len(df),
                       columns=list(df.columns))
            
            return df
            
        except Exception as e:
            logger.error("options_file_download_failed", 
                        error=str(e), 
                        file_path=file_path)
            return None
    
    def download_options_by_date_range(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        option_type: str = "all"
    ) -> pd.DataFrame:
        """
        Download options data for a specific ticker and date range.
        
        Args:
            ticker: Stock ticker (e.g., "QQQ")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            option_type: "call", "put", or "all"
            
        Returns:
            Combined DataFrame with all options data
        """
        try:
            # Generate date range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            all_data = []
            current_date = start_dt
            
            while current_date <= end_dt:
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Try different file naming patterns (based on actual S3 structure)
                possible_paths = [
                    f"us_options_opra/day_aggs_v1/{current_date.year}/{current_date.month:02d}/{date_str}.csv.gz",
                    f"us_options_sip/day_aggs_v1/{current_date.year}/{current_date.month:02d}/{date_str}.csv.gz",
                    f"options/{ticker}/{date_str}.csv",
                    f"options/{ticker}/{date_str}.csv.gz",
                    f"us_options/{ticker}/{date_str}.csv",
                    f"us_options/{ticker}/{date_str}.csv.gz",
                    f"options_data/{ticker}/{date_str}.csv",
                    f"options_data/{ticker}/{date_str}.csv.gz",
                    f"options/{date_str}/{ticker}.csv",
                    f"options/{date_str}/{ticker}.csv.gz",
                ]
                
                for path in possible_paths:
                    df = self.download_options_file(path)
                    if df is not None and not df.empty:
                        # Filter by option type if specified
                        if option_type != "all":
                            df = df[df['option_type'].str.lower() == option_type.lower()]
                        
                        all_data.append(df)
                        logger.info("options_data_downloaded", 
                                   ticker=ticker,
                                   date=date_str,
                                   rows=len(df))
                        break
                
                current_date += timedelta(days=1)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info("options_bulk_download_complete",
                           ticker=ticker,
                           start_date=start_date,
                           end_date=end_date,
                           total_rows=len(combined_df))
                return combined_df
            else:
                logger.warning("no_options_data_found", 
                              ticker=ticker,
                              start_date=start_date,
                              end_date=end_date)
                return pd.DataFrame()
                
        except Exception as e:
            logger.error("options_bulk_download_failed",
                        error=str(e),
                        ticker=ticker,
                        start_date=start_date,
                        end_date=end_date)
            return pd.DataFrame()
    
    def test_s3_connection(self) -> bool:
        """
        Test S3 connection and permissions.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list objects in the bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1
            )
            
            logger.info("s3_connection_test_successful")
            return True
            
        except Exception as e:
            logger.error("s3_connection_test_failed", error=str(e))
            return False


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download bulk options data from Polygon.io S3")
    parser.add_argument("--ticker", default="QQQ", help="Ticker symbol")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--test", action="store_true", help="Test S3 connection")
    parser.add_argument("--explore", action="store_true", help="Explore available data structure")
    parser.add_argument("--option-type", choices=["call", "put", "all"], default="all", help="Option type")
    
    args = parser.parse_args()
    
    try:
        downloader = PolygonS3BulkDownloader()
        
        if args.test:
            print("="*60)
            print("POLYGON.IO S3 CONNECTION TEST")
            print("="*60)
            
            if downloader.test_s3_connection():
                print("✅ S3 connection successful!")
                print(f"Endpoint: {downloader.endpoint_url}")
                print(f"Bucket: {downloader.bucket_name}")
                print(f"Access Key: {downloader.access_key_id[:10]}...")
            else:
                print("❌ S3 connection failed!")
            print("="*60)
            
        elif args.explore:
            print("="*60)
            print("EXPLORING POLYGON.IO S3 DATA STRUCTURE")
            print("="*60)
            
            structure = downloader.get_options_data_structure()
            if structure:
                for prefix, files in structure.items():
                    print(f"\n📁 {prefix}")
                    for file in files:
                        print(f"  📄 {file}")
            else:
                print("❌ No options data structure found")
            print("="*60)
            
        else:
            if not args.start_date or not args.end_date:
                print("❌ Error: --start-date and --end-date required")
                exit(1)
            
            print(f"Downloading {args.ticker} options data from {args.start_date} to {args.end_date}...")
            df = downloader.download_options_by_date_range(
                ticker=args.ticker,
                start_date=args.start_date,
                end_date=args.end_date,
                option_type=args.option_type
            )
            
            if not df.empty:
                print(f"✅ Downloaded {len(df)} rows")
                print(df.head())
                
                # Save to CSV
                filename = f"polygon_s3_{args.ticker}_{args.start_date}_to_{args.end_date}.csv"
                df.to_csv(filename, index=False)
                print(f"💾 Saved to {filename}")
            else:
                print("❌ No data found")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
