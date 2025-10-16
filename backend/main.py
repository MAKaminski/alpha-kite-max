#!/usr/bin/env python3
"""Main entry point for ETL pipeline."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from etl_pipeline import ETLPipeline


# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download equity data from Schwab and load into Supabase"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="QQQ",
        help="Stock ticker symbol (default: QQQ)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Number of days of historical data to fetch (default: 5)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for data download (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--test-connections",
        action="store_true",
        help="Test connections to Schwab and Supabase only"
    )
    
    args = parser.parse_args()
    
    logger.info("starting_application", ticker=args.ticker, days=args.days)
    
    # Initialize pipeline
    pipeline = ETLPipeline()
    
    if args.test_connections:
        logger.info("testing_connections")
        results = pipeline.test_connections()
        
        print(f"\nConnection Test Results:")
        print(f"  Supabase: {'✓ Connected' if results['supabase'] else '✗ Failed'}")
        print(f"  Schwab:   {'✓ Connected' if results['schwab'] else '✗ Failed'}")
        
        if all(results.values()):
            logger.info("all_connections_successful")
            return 0
        else:
            logger.error("connection_tests_failed", results=results)
            return 1
    
    # Run ETL pipeline
    logger.info("running_etl_pipeline")
    result = pipeline.run(ticker=args.ticker, days=args.days, start_date=args.start_date)
    
    if result["success"]:
        print(f"\n✓ ETL Pipeline completed successfully!")
        print(f"  Ticker:         {result['ticker']}")
        print(f"  Equity rows:    {result['equity_rows']}")
        print(f"  Indicator rows: {result['indicator_rows']}")
        if "date_range" in result:
            print(f"  Date range:     {result['date_range']['start']} to {result['date_range']['end']}")
        logger.info("etl_completed_successfully", result=result)
        return 0
    else:
        print(f"\n✗ ETL Pipeline failed!")
        print(f"  Error: {result.get('error', result.get('message', 'Unknown error'))}")
        logger.error("etl_failed", result=result)
        return 1


if __name__ == "__main__":
    sys.exit(main())

