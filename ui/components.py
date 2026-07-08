"""
UI components for the portfolio rebalancing application.
"""
import streamlit as st
import pandas as pd
from typing import Optional


class PortfolioUIComponents:
    """UI components for portfolio rebalancing interface."""

    def __init__(self):
        """Initialize the UI components."""
        st.set_page_config(page_title="Basket Rebalancer", layout="wide")
        st.title("📊 Basket Portfolio Rebalancer")
        
        st.markdown("""
        This tool helps you rebalance your custom Basket by comparing current allocations with your target weights.
        Fill out the table below with your current holdings and desired target allocation.
        """)
        st.markdown("---")
    
    @staticmethod
    def render_data_input_selector():
        """Render a selector for data input method and optionally a CSV/Image uploader.

        Returns:
            Tuple[str, Optional[Any], Optional[str]]: selected mode, uploaded file, and API key
        """
        mode = st.radio(
            "Choose how to provide portfolio data",
            options=["Manual Entry", "Upload CSV", "Upload Image Table"],
            horizontal=True,
        )
        uploaded = None
        api_key = None
        
        if mode == "Upload CSV":
            with st.expander("CSV requirements (exact columns)", expanded=False):
                st.code("Stock Name,Ticker,Shares Held,Target Weight (%)")
            uploaded = st.file_uploader("Upload CSV", type=["csv"], accept_multiple_files=False)
            
        elif mode == "Upload Image Table":
            uploaded = st.file_uploader("Upload portfolio screenshot", type=["png", "jpg", "jpeg"], accept_multiple_files=False)
            
            # Look for Gemini API Key in environment first
            import os
            env_key = os.environ.get("GEMINI_API_KEY", "")
            
            st.markdown("### 🔑 Gemini API Credentials")
            api_key = st.text_input(
                "Enter Gemini API Key (obtain from Google AI Studio)",
                value=st.session_state.get("gemini_api_key", env_key),
                type="password",
                placeholder="AIzaSy..."
            )
            if api_key:
                st.session_state["gemini_api_key"] = api_key
                
        return mode, uploaded, api_key

    @staticmethod
    def render_portfolio_table(df: pd.DataFrame) -> pd.DataFrame:
        """
        Render the editable portfolio table.
        
        Args:
            df: DataFrame to display
            
        Returns:
            Edited DataFrame
        """
        # Rearrange columns in the desired order
        column_order = [
            "Stock Name",
            "Ticker", 
            "Shares Held", 
            "Current Price (per share)", 
            "Current Value", 
            "Current Weight (%)", 
            "Target Weight (%)"
        ]
        
        # Only include columns that exist in the DataFrame
        available_columns = [col for col in column_order if col in df.columns]
        df_reordered = df[available_columns].copy()
        
        # Add 1-based serial numbers as the index
        df_reordered.index = range(1, len(df_reordered) + 1)
        df_reordered.index.name = "#"
        
        st.markdown("### 📊 Portfolio Holdings")
        st.markdown("Edit the values below to update your portfolio. Changes are automatically saved to session.")
        
        # Render the data editor with a stable key
        edited_df = st.data_editor(
            df_reordered, 
            num_rows="dynamic", 
            width="stretch",
            hide_index=False,
        )
        
        return edited_df
    
    @staticmethod
    def render_weight_summary(df: pd.DataFrame) -> None:
        """
        Render weight summary metrics.
        
        Args:
            df: Portfolio DataFrame
        """
        col1, col2 = st.columns(2)
        
        with col1:
            total_current_weight = round(df["Current Weight (%)"].sum(), 2)
            st.metric("🔢 Total Current Weight (%)", f"{total_current_weight}%")
        
        with col2:
            total_target_weight = round(df["Target Weight (%)"].sum(), 2)
            st.metric("🎯 Total Target Weight (%)", f"{total_target_weight}%")
    
    @staticmethod
    def render_total_value(total_value: float) -> None:
        """
        Render total portfolio value.
        
        Args:
            total_value: Total portfolio value
        """
        st.markdown(f"**💰 Total Current Value: ₹{total_value:,.2f}**")
    
    @staticmethod
    def render_additional_capital_input() -> float:
        """
        Render additional capital input.
        
        Returns:
            Additional capital amount
        """
        return st.number_input(
            "💸 Optional: Enter additional amount to invest (₹)", 
            min_value=0, 
            value=0
        )
    
    @staticmethod
    def render_rebalance_button() -> bool:
        """
        Render rebalance button.
        
        Returns:
            True if button is clicked
        """
        return st.button("🔄 Rebalance Portfolio")
    
    @staticmethod
    def render_rebalanced_portfolio(df: pd.DataFrame) -> None:
        """
        Render the rebalanced portfolio results.
        
        Args:
            df: Rebalanced portfolio DataFrame
        """
        st.markdown("### 🧾 Rebalanced Portfolio")
        st.dataframe(
            PortfolioUIComponents.style_output(df), 
            width="stretch", 
            height=500
        )
    
    @staticmethod
    def render_download_button(df: pd.DataFrame) -> None:
        """
        Render download button to save current basket state.
        
        Args:
            df: Rebalanced portfolio DataFrame
        """
        state_df = pd.DataFrame({
            "Stock Name": df["Stock Name"],
            "Ticker": df["Ticker"],
            "Shares Held": df["Target Shares"],
            "Target Weight (%)": df["Target Weight (%)"]
        })
        
        csv = state_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "💾 Save Current Basket State", 
            csv, 
            "rebalanced_portfolio.csv", 
            "text/csv"
        )
    
    @staticmethod
    def render_suggestion_message(suggested_amount: float, additional_amount: float) -> None:
        """
        Render suggestion message for additional investment.
        
        Args:
            suggested_amount: Suggested additional amount
            additional_amount: Current additional amount
        """
        if additional_amount == 0 and suggested_amount > 0:
            st.markdown(
                f"💡 To reach target weights exactly, consider adding "
                f"**₹{suggested_amount:,.2f}** more to the portfolio."
            )
    
    @staticmethod
    def render_error_message(error: str) -> None:
        """
        Render error message.
        
        Args:
            error: Error message to display
        """
        st.error(f"Something went wrong: {error}")
    
    @staticmethod
    def render_footer() -> None:
        """Render the application footer."""
        st.markdown("---")
        st.info("Tip: Modify tickers (e.g., add '.NS'), and prices will be fetched automatically.")
    
    @staticmethod
    def style_output(df: pd.DataFrame):
        """
        Apply styling to the output DataFrame.
        
        Args:
            df: DataFrame to style
            
        Returns:
            Styled DataFrame
        """
        def highlight_action(val):
            color = "lightgray"
            if val == "Buy":
                color = "#d4f4dd"
            elif val == "Sell":
                color = "#fddede"
            return f"background-color: {color}"

        return df.style \
            .map(highlight_action, subset=["Action"]) \
            .set_properties(
                **{
                    "background-color": "#e8f4fd",
                    "font-weight": "bold"
                },
                subset=["Stock Name", "Ticker", "Shares Held", "Target Weight (%)", "Target Shares", "Current Price (per share)"]
            ) \
            .set_properties(
                **{
                    "background-color": "#f4f9f4"
                },
                subset=["Current Value", "Current Weight (%)", "Target Value", "Shares to Buy/Sell", "Real Weight (%)"]
            ) \
            .format({
                "Current Price (per share)": "₹{:.2f}",
                "Current Value": "₹{:.2f}",
                "Target Value": "₹{:.2f}",
                "Target Value (Actual)": "₹{:.2f}",
                "Difference": "₹{:.2f}",
                "Real Weight (%)": "{:.2f}%"
            }) 