"""
Utility functions for portfolio calculations and data processing.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple


def calculate_portfolio_metrics(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Calculate key portfolio metrics.
    
    Args:
        df: Portfolio DataFrame
        
    Returns:
        Tuple of (total_value, total_current_weight, total_target_weight)
    """
    # Calculate current values
    df["Current Value"] = df["Shares Held"] * df["Current Price (per share)"]
    total_value = df["Current Value"].sum()
    
    # Calculate current weights
    if total_value > 0:
        df["Current Weight (%)"] = (df["Current Value"] / total_value * 100).round(2)
    else:
        df["Current Weight (%)"] = 0.0
    
    # Calculate totals
    total_current_weight = round(df["Current Weight (%)"].sum(), 2)
    total_target_weight = round(df["Target Weight (%)"].sum(), 2)
    
    return total_value, total_current_weight, total_target_weight


def optimize_shares(prices: pd.Series, target_values: pd.Series) -> List[int]:
    """
    Optimize share quantities to match target values as closely as possible.
    
    Args:
        prices: Series of current prices
        target_values: Series of target values
        
    Returns:
        List of optimized share quantities
    """
    shares = []
    for price, target in zip(prices, target_values):
        if price > 0:
            shares.append(int(round(target / price)))
        else:
            shares.append(0)
    return shares


def validate_portfolio_data(df: pd.DataFrame) -> List[str]:
    """
    Validate portfolio data for common issues.
    
    Args:
        df: Portfolio DataFrame
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Check for required columns
    required_columns = ["Ticker", "Shares Held", "Target Weight (%)"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    # Check for negative values
    if "Shares Held" in df.columns:
        if (df["Shares Held"] < 0).any():
            errors.append("Shares held cannot be negative")
    
    if "Target Weight (%)" in df.columns:
        if (df["Target Weight (%)"] < 0).any():
            errors.append("Target weights cannot be negative")
    
    # Check for empty tickers
    if "Ticker" in df.columns:
        if df["Ticker"].isna().any() or (df["Ticker"] == "").any():
            errors.append("Ticker symbols cannot be empty")
    
    return errors


def format_currency(value: float) -> str:
    """
    Format value as Indian currency.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted currency string
    """
    return f"₹{value:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.2f}%"


def reorder_rebalanced_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reorder columns in the rebalanced portfolio DataFrame to a specified order.
    
    Args:
        df: DataFrame to reorder
        
    Returns:
        DataFrame with reordered columns
    """
    column_order = [
        "Ticker",
        "Shares Held",
        "Current Price (per share)",
        "Current Weight (%)",
        "Current Value",
        "Target Weight (%)",
        "Target Value",
        "Target Shares",
        "Target Value (Actual)",
        "Difference",
        "Action",
        "Shares to Buy/Sell",
        "Real Weight (%)"
    ]
    
    available_columns = [col for col in column_order if col in df.columns]
    remaining_columns = [col for col in df.columns if col not in available_columns]
    final_column_order = available_columns + remaining_columns
    
    return df[final_column_order]


def calculate_rebalancing_metrics(df: pd.DataFrame, additional_capital: float = 0.0) -> pd.DataFrame:
    """
    Calculate rebalancing metrics for a portfolio.
    
    Args:
        df: Portfolio DataFrame
        additional_capital: Additional capital to invest
        
    Returns:
        DataFrame with rebalancing calculations
    """
    # Calculate total value including additional capital
    total_current_value = df["Current Value"].sum()
    new_total_value = total_current_value + additional_capital
    
    # Calculate target values
    df["Target Value"] = (df["Target Weight (%)"] / 100.0 * new_total_value)
    
    # Optimize shares
    df["Target Shares"] = optimize_shares(
        df["Current Price (per share)"],
        df["Target Value"]
    )
    
    # Calculate actual target values and differences
    df["Target Value (Actual)"] = df["Target Shares"] * df["Current Price (per share)"]
    df["Difference"] = df["Target Value (Actual)"] - df["Current Value"]
    
    # Determine actions
    df["Action"] = df["Difference"].apply(
        lambda x: "Buy" if x > 0 else ("Sell" if x < 0 else "Hold")
    )
    
    # Calculate shares to trade
    df["Shares to Buy/Sell"] = df["Target Shares"] - df["Shares Held"]
    
    # Calculate real weights
    total_rebalanced_value = df["Target Value (Actual)"].sum()
    if total_rebalanced_value > 0:
        df["Real Weight (%)"] = (df["Target Value (Actual)"] / total_rebalanced_value * 100).round(2)
    else:
        df["Real Weight (%)"] = 0.0
    
    return reorder_rebalanced_columns(df) 