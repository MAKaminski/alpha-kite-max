#!/usr/bin/env python3
"""
Health check script for streaming service.
Can be run locally or on the Lightsail instance.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import structlog
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from supabase_client import SupabaseClient

load_dotenv()
logger = structlog.get_logger()

class HealthChecker:
    """Check health of streaming service and database."""
    
    def __init__(self):
        """Initialize health checker."""
        try:
            self.supabase = SupabaseClient()
            self.ticker = os.getenv('STREAM_TICKER', 'QQQ')
        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            sys.exit(1)
    
    def check_database_connection(self) -> Dict[str, Any]:
        """Check if database is accessible."""
        try:
            result = self.supabase.test_connection()
            return {
                'status': 'healthy' if result else 'error',
                'message': 'Database connection successful' if result else 'Connection failed'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Database connection error: {str(e)}'
            }
    
    def check_recent_data(self) -> Dict[str, Any]:
        """Check if recent data exists in the database."""
        try:
            # Query for data from the last 5 minutes
            response = self.supabase.client.table("equity_data")\
                .select("*")\
                .eq("ticker", self.ticker)\
                .gte("timestamp", (datetime.now() - timedelta(minutes=5)).isoformat())\
                .execute()
            
            count = len(response.data) if response.data else 0
            
            if count > 0:
                latest = response.data[0]
                latest_time = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00'))
                age = datetime.now(latest_time.tzinfo) - latest_time
                
                return {
                    'status': 'healthy',
                    'message': f'Found {count} records in last 5 minutes',
                    'latest_timestamp': latest['timestamp'],
                    'age_seconds': age.total_seconds(),
                    'latest_price': latest['price']
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'No data in last 5 minutes',
                    'count': 0
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Data check error: {str(e)}'
            }
    
    def check_streaming_metrics(self) -> Dict[str, Any]:
        """Check streaming service metrics."""
        try:
            response = self.supabase.client.table("streaming_metrics")\
                .select("*")\
                .eq("ticker", self.ticker)\
                .gte("timestamp", (datetime.now() - timedelta(hours=1)).isoformat())\
                .execute()
            
            if not response.data:
                return {
                    'status': 'warning',
                    'message': 'No streaming metrics found in last hour'
                }
            
            metrics = response.data
            total_records = sum(m['records_processed'] for m in metrics)
            total_errors = sum(m['error_count'] for m in metrics)
            avg_batch_size = sum(m['batch_size'] for m in metrics if m['batch_size']) / len(metrics)
            
            error_rate = (total_errors / total_records * 100) if total_records > 0 else 0
            
            status = 'healthy'
            if error_rate > 5:
                status = 'warning'
            if error_rate > 10:
                status = 'error'
            
            return {
                'status': status,
                'message': f'Processed {total_records} records in last hour',
                'total_records': total_records,
                'total_errors': total_errors,
                'error_rate': round(error_rate, 2),
                'avg_batch_size': round(avg_batch_size, 2),
                'batch_count': len(metrics)
            }
            
        except Exception as e:
            # Metrics table might not exist or no data yet
            return {
                'status': 'info',
                'message': 'Streaming metrics not available (this is OK for new deployments)'
            }
    
    def check_data_freshness(self) -> Dict[str, Any]:
        """Check how fresh the data is."""
        try:
            response = self.supabase.client.table("equity_data")\
                .select("timestamp")\
                .eq("ticker", self.ticker)\
                .order("timestamp", desc=True)\
                .limit(1)\
                .execute()
            
            if not response.data:
                return {
                    'status': 'warning',
                    'message': 'No data found for ticker'
                }
            
            latest_timestamp = datetime.fromisoformat(response.data[0]['timestamp'].replace('Z', '+00:00'))
            age = datetime.now(latest_timestamp.tzinfo) - latest_timestamp
            age_minutes = age.total_seconds() / 60
            
            status = 'healthy'
            if age_minutes > 5:
                status = 'warning'
            if age_minutes > 15:
                status = 'error'
            
            return {
                'status': status,
                'message': f'Latest data is {round(age_minutes, 1)} minutes old',
                'latest_timestamp': latest_timestamp.isoformat(),
                'age_minutes': round(age_minutes, 1)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Freshness check error: {str(e)}'
            }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        logger.info("health_check_starting", ticker=self.ticker)
        
        checks = {
            'timestamp': datetime.now().isoformat(),
            'ticker': self.ticker,
            'database_connection': self.check_database_connection(),
            'recent_data': self.check_recent_data(),
            'data_freshness': self.check_data_freshness(),
            'streaming_metrics': self.check_streaming_metrics()
        }
        
        # Determine overall status
        statuses = [check['status'] for check in checks.values() if isinstance(check, dict) and 'status' in check]
        
        if 'error' in statuses:
            overall_status = 'error'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        checks['overall_status'] = overall_status
        
        return checks
    
    def print_report(self, checks: Dict[str, Any]):
        """Print a human-readable health report."""
        status_icons = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌',
            'info': 'ℹ️'
        }
        
        print("\n" + "="*60)
        print(f"🏥 STREAMING SERVICE HEALTH CHECK")
        print("="*60)
        print(f"Timestamp: {checks['timestamp']}")
        print(f"Ticker: {checks['ticker']}")
        print(f"Overall Status: {status_icons.get(checks['overall_status'], '❓')} {checks['overall_status'].upper()}")
        print("="*60)
        
        for check_name, check_data in checks.items():
            if check_name in ['timestamp', 'ticker', 'overall_status']:
                continue
            
            if isinstance(check_data, dict) and 'status' in check_data:
                icon = status_icons.get(check_data['status'], '❓')
                print(f"\n{icon} {check_name.replace('_', ' ').title()}")
                print(f"   Status: {check_data['status'].upper()}")
                print(f"   {check_data['message']}")
                
                # Print additional details
                for key, value in check_data.items():
                    if key not in ['status', 'message']:
                        print(f"   {key}: {value}")
        
        print("\n" + "="*60 + "\n")


def main():
    """Main entry point."""
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    checker = HealthChecker()
    checks = checker.run_all_checks()
    checker.print_report(checks)
    
    # Exit with appropriate code
    if checks['overall_status'] == 'error':
        sys.exit(1)
    elif checks['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

