"""
Configuration settings for the portfolio rebalancing application.
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class AppConfig:
    """Application configuration settings."""
    
    # File paths
    SAVE_FILE: str = "data/tornado.csv"
    
    # Default portfolio data
    DEFAULT_TICKERS: List[str] = None
    DEFAULT_SHARES: List[int] = None
    DEFAULT_WEIGHTS: List[float] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.DEFAULT_TICKERS is None:
            self.DEFAULT_TICKERS = ["TCS.NS", "INFY.NS", "HDFC.NS"]
        if self.DEFAULT_SHARES is None:
            self.DEFAULT_SHARES = [10, 20, 12]
        if self.DEFAULT_WEIGHTS is None:
            self.DEFAULT_WEIGHTS = [25.0, 50.0, 25.0]
    
    @property
    def data_directory(self) -> str:
        """Get the data directory path."""
        dir_path = os.path.dirname(self.SAVE_FILE)
        return dir_path if dir_path else "data"
    
    def ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        os.makedirs(self.data_directory, exist_ok=True)


# Global configuration instance
app_config = AppConfig() 