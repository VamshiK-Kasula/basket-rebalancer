"""
Data service for managing portfolio data persistence and loading.
"""
import os
import pandas as pd
import numpy as np
import logging
from typing import Union, IO

logger = logging.getLogger(__name__)


class DataService:
    """Service for managing portfolio data persistence."""
    
    def __init__(self, save_file: str = "data/tornado.csv"):

        self.save_file = save_file
        self._ensure_data_directory()
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        dir_path = os.path.dirname(self.save_file)
        if dir_path:  # Only create directory if there's a path
            os.makedirs(dir_path, exist_ok=True)

    def load_portfolio_data(self) -> pd.DataFrame:
        """
        Load portfolio data from CSV file or return default data.
        
        Returns:
            DataFrame with portfolio data
        """
        if os.path.exists(self.save_file):
            try:
                df = self.read_portfolio_csv(self.save_file)
                logger.info(f"Loaded portfolio data from {self.save_file}")
                return df
            except Exception as e:
                logger.error(f"Error loading portfolio data: {e}")
                return self._get_default_data()
        else:
            logger.info("No saved data found, using default portfolio")
            return self._get_default_data()
    
    def save_portfolio_data(self, df: pd.DataFrame) -> None:
        """
        Save portfolio data to CSV file (only core columns).
        
        Args:
            df: DataFrame to save
        """
        try:
            core_columns = ["Ticker", "Shares Held", "Target Weight (%)"]
            # Ensure all required columns exist
            for col in core_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Select only core columns and save as CSV
            df_to_save = df[core_columns].copy()
            df_to_save.to_csv(self.save_file, index=False)
            logger.info(f"Saved portfolio data to {self.save_file}")
        except Exception as e:
            logger.error(f"Error saving portfolio data: {e}")
            raise
    
    def _get_default_data(self) -> pd.DataFrame:
        """
        Get default portfolio data.
        
        Returns:
            DataFrame with default portfolio holdings
        """
        data = {
            "Ticker": ["TCS.NS", "INFY.NS", "HDFC.NS"],
            "Shares Held": [10, 20, 12],
            "Target Weight (%)": [25.0, 50.0, 25.0]
        }
        return pd.DataFrame(data)
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = "rebalanced_portfolio.csv") -> bytes:
        """
        Export DataFrame to CSV format.
        
        Args:
            df: DataFrame to export
            filename: Name of the CSV file
            
        Returns:
            CSV data as bytes
        """
        return df.to_csv(index=False).encode('utf-8')

    def _validate_csv_columns(self, df: pd.DataFrame) -> None:
        """Validate that CSV has exactly the expected columns in the expected order."""
        expected_columns = ["Ticker", "Shares Held", "Target Weight (%)"]
        incoming_columns = [col.strip() for col in df.columns.tolist()]
        if incoming_columns != expected_columns:
            raise ValueError(
                "CSV schema mismatch. Expected columns exactly: "
                f"{expected_columns} but got {incoming_columns}."
            )

    def read_portfolio_csv(self, input_source: Union[str, IO[str], IO[bytes]]) -> pd.DataFrame:
        """
        Read a portfolio CSV and validate it matches the export schema exactly.

        The CSV must contain exactly these columns in this order:
        ["Ticker", "Shares Held", "Target Weight (%)"].
        """
        try:
            df = pd.read_csv(input_source)
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            raise
        
        # Validate schema strictly
        self._validate_csv_columns(df)

        # Coerce types and clean values
        df["Ticker"] = df["Ticker"].astype(str).str.strip()
        df["Shares Held"] = pd.to_numeric(df["Shares Held"], errors="raise").astype(int)
        df["Target Weight (%)"] = pd.to_numeric(df["Target Weight (%)"], errors="raise").astype(float)

        logger.info(f"Successfully loaded portfolio CSV with {len(df)} rows")
        return df
    
    
    def get_suggested_additional_amount(self, target_values: pd.Series, current_value: float) -> float:
        """
        Calculate suggested additional amount for perfect rebalancing.
        
        Args:
            target_values: Series of target values
            current_value: Current total portfolio value
            
        Returns:
            Suggested additional amount
        """
        return target_values.sum() - current_value
