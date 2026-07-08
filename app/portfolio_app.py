"""
Main application class for portfolio rebalancing.
"""
import pandas as pd
import logging
import numpy as np
import streamlit as st
from typing import Optional, Dict

from services.price_service import PriceService
from services.data_service import DataService
from services.image_service import ImageService
from ui.components import PortfolioUIComponents
from utils.portfolio_utils import calculate_portfolio_metrics, calculate_rebalancing_metrics, validate_portfolio_data
from config.settings import app_config

logger = logging.getLogger(__name__)


class PortfolioRebalancerApp:
    """Main application class for portfolio rebalancing."""
    
    def __init__(self):
        """Initialize the application with all required services."""
        self.price_service = PriceService()
        self.image_service = ImageService()
        self._price_cache: Dict[str, float] = {}
        self.data_service = DataService(app_config.SAVE_FILE)
        self.ui = PortfolioUIComponents()
        
        # Load from session state if available to keep user-specific state isolated,
        # otherwise load from default file.
        if 'portfolio_df' in st.session_state:
            self._portfolio_df = st.session_state['portfolio_df']
        else:
            self._portfolio_df = self.data_service.load_portfolio_data()
    
    def run(self) -> None:
        try:
            print("Running application")

            # 0. Let user choose data input method
            mode, uploaded, api_key = self.ui.render_data_input_selector()

            # 1. If CSV mode and a file is uploaded, read it
            if mode == "Upload CSV" and uploaded is not None:
                try:
                    csv_df = self.data_service.read_portfolio_csv(uploaded)
                    self._portfolio_df = csv_df
                    st.session_state['portfolio_df'] = csv_df
                    st.success("✅ CSV loaded successfully!")
                except Exception as e:
                    self.ui.render_error_message(str(e))
                    # Fall back to existing data
            
            # 1b. If Image mode and a file is uploaded, read it using Gemini
            elif mode == "Upload Image Table" and uploaded is not None:
                if not api_key:
                    st.warning("⚠️ Please enter a Gemini API Key to parse the image.")
                else:
                    if st.button("🔮 Extract Portfolio from Image", type="primary"):
                        try:
                            with st.spinner("Analyzing image layout and extracting stocks/weights using Gemini..."):
                                image_bytes = uploaded.read()
                                mime_type = uploaded.type
                                
                                # Call Gemini to parse the image
                                extracted_stocks = self.image_service.parse_portfolio_image(
                                    image_bytes=image_bytes,
                                    mime_type=mime_type,
                                    api_key=api_key
                                )
                                
                            if not extracted_stocks:
                                st.warning("⚠️ No stocks could be extracted from this image. Please check the image layout.")
                            else:
                                resolved_list = []
                                progress_text = "Resolving stock names to tickers on Yahoo Finance..."
                                progress_bar = st.progress(0, text=progress_text)
                                
                                for i, stock in enumerate(extracted_stocks):
                                    name = stock.get("stock_name", "")
                                    weight = float(stock.get("weight", 0.0))
                                    
                                    # Resolve ticker symbol using yfinance search
                                    progress_bar.progress((i + 1) / len(extracted_stocks), text=f"Resolving ticker for {name}...")
                                    ticker = self.image_service.resolve_ticker_symbol(name)
                                    
                                    resolved_list.append({
                                        "Stock Name": name,
                                        "Ticker": ticker,
                                        "Shares Held": 0,  # Default since weightage doesn't tell us shares held
                                        "Target Weight (%)": weight
                                    })
                                    
                                progress_bar.empty()
                                
                                # Build dataframe and store in session
                                image_df = pd.DataFrame(resolved_list)
                                self._portfolio_df = image_df
                                st.session_state['portfolio_df'] = image_df
                                st.success("✅ Portfolio successfully extracted from image!")
                                st.rerun()
                                
                        except Exception as e:
                            self.ui.render_error_message(str(e))

            # 2. Show editable table (user_df is always the user's last edit)
            self._portfolio_df = self.ui.render_portfolio_table(self._portfolio_df)

            # 3. If user made changes, update session state
            # if not edited_df.equals(user_df):
            st.session_state['portfolio_df'] = self._portfolio_df
            st.success("✅ Changes saved to session!")

            # 4. For calculations and display, create a copy and update prices
            display_df = self.update_portfolio_prices(self._portfolio_df.copy())

            # 5. Show metrics, charts, etc. using display_df
            self._display_portfolio_metrics(display_df)
            self._handle_rebalancing(display_df)
            self.ui.render_footer()

        except Exception as e:
            logger.error(f"Application error: {e}")
            self.ui.render_error_message(str(e))

    def update_portfolio_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Update current prices for all tickers in the portfolio.
        """
        tickers = df["Ticker"].tolist()
        if not self._price_cache:
            self._price_cache = self.price_service.get_portfolio_prices(tickers)
        df["Current Price (per share)"] = df["Ticker"].apply(lambda ticker: self._price_cache.get(ticker, np.nan))
        return df
    
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Update prices and calculate metrics.
        
        Args:
            df: DataFrame to process
            
        Returns:
            Processed DataFrame with current prices and metrics
        """
        # Update prices
        df = self.price_service.update_portfolio_prices(df)
        
        # Calculate metrics
        total_value, _, _ = calculate_portfolio_metrics(df)
        
        return df
    
    def _save_user_data_to_file(self, df: pd.DataFrame) -> None:
        """
        Save user data to session state (only user-editable columns).
        
        Args:
            df: DataFrame with user edits
        """
        try:
            # Only save user-editable columns
            user_columns = ["Stock Name", "Ticker", "Shares Held", "Target Weight (%)"]
            user_data = df[user_columns].copy()
            
            st.session_state['portfolio_df'] = user_data
            st.success("💾 Changes saved to session!")
            
        except Exception as e:
            st.error(f"❌ Error saving: {e}")
            logger.error(f"Error saving user data to session: {e}")
    
    def _display_portfolio_metrics(self, df: pd.DataFrame) -> None:
        """
        Display portfolio metrics and summary.
        
        Args:
            df: Portfolio DataFrame
        """
        # Calculate metrics
        total_value, total_current_weight, total_target_weight = calculate_portfolio_metrics(df)
        
        # Display weight summary
        self.ui.render_weight_summary(df)
        
        # Display total value
        self.ui.render_total_value(total_value)
    
    def _handle_rebalancing(self, df: pd.DataFrame) -> None:
        """
        Handle the rebalancing process.
        
        Args:
            df: Portfolio DataFrame
        """
        # Get additional capital input
        additional_amount = self.ui.render_additional_capital_input()
        
        # Check if rebalance button is clicked
        if self.ui.render_rebalance_button():
            self._perform_rebalancing(df, additional_amount)
    
    def _perform_rebalancing(self, df: pd.DataFrame, additional_amount: float) -> None:
        """
        Perform the rebalancing calculations and display results.
        
        Args:
            df: Portfolio DataFrame
            additional_amount: Additional capital to invest
        """
        try:
            # Validate data
            errors = validate_portfolio_data(df)
            if errors:
                for error in errors:
                    self.ui.render_error_message(error)
                return
            
            # Save current user data to session state (only user-editable columns)
            user_columns = ["Stock Name", "Ticker", "Shares Held", "Target Weight (%)"]
            user_data = df[user_columns].copy()
            
            st.session_state['portfolio_df'] = user_data
            st.success("💾 Portfolio data saved to session!")
            
            # Calculate rebalancing metrics
            rebalanced_df = calculate_rebalancing_metrics(df, additional_amount)
            
            # Display results
            self.ui.render_rebalanced_portfolio(rebalanced_df)
            
            # Provide download option
            self.ui.render_download_button(rebalanced_df)
            
            # Show suggestion for additional investment
            suggested_amount = self.data_service.get_suggested_additional_amount(
                rebalanced_df["Target Value (Actual)"], 
                df["Current Value"].sum()
            )
            self.ui.render_suggestion_message(suggested_amount, additional_amount)
            
        except Exception as e:
            logger.error(f"Rebalancing error: {e}")
            self.ui.render_error_message(str(e))
    
    def get_portfolio_summary(self, df: pd.DataFrame) -> dict:
        """
        Get a summary of portfolio metrics.
        
        Args:
            df: Portfolio DataFrame
            
        Returns:
            Dictionary with portfolio summary
        """
        total_value, total_current_weight, total_target_weight = calculate_portfolio_metrics(df)
        
        return {
            "total_value": total_value,
            "total_current_weight": total_current_weight,
            "total_target_weight": total_target_weight,
            "holdings_count": len(df),
            "additional_capital": 0.0  # This would be set by the UI
        } 