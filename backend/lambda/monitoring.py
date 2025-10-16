"""Monitoring and logging utilities for Lambda function."""

import boto3
from datetime import datetime
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

# Initialize CloudWatch client
cloudwatch = boto3.client('cloudwatch')


def log_streaming_metrics(
    ticker: str,
    data_points_fetched: int,
    supabase_success: bool,
    latency_ms: float,
    token_refreshed: bool = False
):
    """Log metrics to CloudWatch.
    
    Args:
        ticker: Stock ticker symbol
        data_points_fetched: Number of data points fetched
        supabase_success: Whether Supabase upload succeeded
        latency_ms: Latency in milliseconds
        token_refreshed: Whether token was refreshed
    """
    try:
        namespace = 'AlphaKiteMax/RealTimeStreaming'
        timestamp = datetime.utcnow()
        
        metrics = []
        
        # Data points fetched
        metrics.append({
            'MetricName': 'DataPointsFetched',
            'Value': data_points_fetched,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Ticker', 'Value': ticker}
            ]
        })
        
        # Supabase upload success
        metrics.append({
            'MetricName': 'SupabaseUploadSuccess',
            'Value': 1 if supabase_success else 0,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Ticker', 'Value': ticker}
            ]
        })
        
        # Latency
        metrics.append({
            'MetricName': 'LatencyMilliseconds',
            'Value': latency_ms,
            'Unit': 'Milliseconds',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Ticker', 'Value': ticker}
            ]
        })
        
        # Token refresh events
        if token_refreshed:
            metrics.append({
                'MetricName': 'TokenRefreshEvents',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': timestamp,
                'Dimensions': [
                    {'Name': 'Ticker', 'Value': ticker}
                ]
            })
        
        # Put metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=metrics
        )
        
        logger.info(
            "metrics_logged",
            ticker=ticker,
            data_points=data_points_fetched,
            supabase_success=supabase_success,
            latency_ms=latency_ms,
            token_refreshed=token_refreshed
        )
        
    except Exception as e:
        logger.error("metrics_logging_error", error=str(e))


def create_cloudwatch_alarm(
    alarm_name: str,
    metric_name: str,
    threshold: float,
    comparison_operator: str = 'LessThanThreshold',
    evaluation_periods: int = 3,
    sns_topic_arn: str = None
):
    """Create CloudWatch alarm for monitoring.
    
    Args:
        alarm_name: Name of the alarm
        metric_name: Metric to monitor
        threshold: Threshold value
        comparison_operator: Comparison operator
        evaluation_periods: Number of periods to evaluate
        sns_topic_arn: SNS topic ARN for notifications
    """
    try:
        alarm_config = {
            'AlarmName': alarm_name,
            'ComparisonOperator': comparison_operator,
            'EvaluationPeriods': evaluation_periods,
            'MetricName': metric_name,
            'Namespace': 'AlphaKiteMax/RealTimeStreaming',
            'Period': 300,  # 5 minutes
            'Statistic': 'Average',
            'Threshold': threshold,
            'ActionsEnabled': bool(sns_topic_arn),
            'AlarmDescription': f'Alert when {metric_name} crosses threshold',
            'Dimensions': [
                {
                    'Name': 'Ticker',
                    'Value': 'QQQ'
                }
            ]
        }
        
        if sns_topic_arn:
            alarm_config['AlarmActions'] = [sns_topic_arn]
        
        cloudwatch.put_metric_alarm(**alarm_config)
        
        logger.info("alarm_created", alarm_name=alarm_name, metric_name=metric_name)
        
    except Exception as e:
        logger.error("alarm_creation_error", error=str(e), alarm_name=alarm_name)


def log_error_to_cloudwatch(error: Exception, context: Dict[str, Any]):
    """Log error details to CloudWatch Logs.
    
    Args:
        error: Exception that occurred
        context: Additional context information
    """
    try:
        logger.error(
            "streaming_error",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )
        
        # Also log as a metric for alerting
        cloudwatch.put_metric_data(
            Namespace='AlphaKiteMax/RealTimeStreaming',
            MetricData=[
                {
                    'MetricName': 'Errors',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {
                            'Name': 'ErrorType',
                            'Value': type(error).__name__
                        }
                    ]
                }
            ]
        )
        
    except Exception as e:
        logger.error("error_logging_failed", error=str(e))

