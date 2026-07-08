"""
Image service for extracting stock data from uploaded screenshots/images using Gemini API
and resolving stock names to Yahoo Finance tickers.
"""
import base64
import json
import logging
import requests
import yfinance as yf
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ImageService:
    """Service for parsing portfolio images and resolving stock tickers."""

    def parse_portfolio_image(self, image_bytes: bytes, mime_type: str, api_key: str) -> List[Dict[str, Any]]:
        """
        Send the portfolio screenshot/image to the Gemini API to extract stock data.
        
        Args:
            image_bytes: Raw bytes of the uploaded image
            mime_type: MIME type of the image (e.g. 'image/png', 'image/jpeg')
            api_key: User's Gemini API Key
            
        Returns:
            List of dicts containing 'segment', 'stock_name', and 'weight'.
        """
        # Ensure we use the latest gemini model (gemini-1.5-flash is stable and fast for multimodal)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"        
        # Base64 encode the image
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Formulate a structured system instruction and request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You are an expert financial OCR assistant. Analyze the uploaded image, which contains a table/list of stocks and their weightages. "
                                "Extract all individual stocks listed in the table. Note the following structure:\n"
                                "1. Segment/Category rows are in bold (e.g. 'Auto Parts', 'Software Services') and have an aggregated weight next to them.\n"
                                "2. Under each segment, individual stocks are listed (e.g. 'Wheels India Ltd', 'Sandhar Technologies Ltd') with their respective weights.\n\n"
                                "Your goal is to extract only the actual stocks (NOT the segment summary rows). For each stock, return:\n"
                                "- 'segment': The name of the segment the stock belongs to.\n"
                                "- 'stock_name': The exact text name of the stock.\n"
                                "- 'weight': The weightage percentage as a float number (e.g., 10.00).\n\n"
                                "Return the data strictly as a raw JSON array of objects. Do not include any markdown styling like ```json or wrappers."
                            )
                        },
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": encoded_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info("Sending request to Gemini API for image parsing...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.text}")
            raise Exception(f"Gemini API returned error {response.status_code}: {response.text}")
            
        try:
            response_json = response.json()
            text_content = response_json['candidates'][0]['content']['parts'][0]['text']
            parsed_data = json.loads(text_content)
            
            if not isinstance(parsed_data, list):
                if isinstance(parsed_data, dict) and "stocks" in parsed_data:
                    parsed_data = parsed_data["stocks"]
                elif isinstance(parsed_data, dict) and "holdings" in parsed_data:
                    parsed_data = parsed_data["holdings"]
                else:
                    raise ValueError("Extracted JSON is not a list structure.")
            
            logger.info(f"Successfully extracted {len(parsed_data)} stocks from image.")
            return parsed_data
            
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Gemini JSON output: {e}. Raw response: {response.text}")
            raise Exception(f"Failed to parse Gemini response: {e}")

    def resolve_ticker_symbol(self, stock_name: str) -> str:
        """
        Query Yahoo Finance Search to resolve the correct ticker for a stock name.
        Prefer NSE (.NS) and BSE (.BO) tickers.
        
        Args:
            stock_name: Name of the stock to search for
            
        Returns:
            Resolved ticker string (e.g., 'WHEELS.NS'). If not found, falls back to a guess.
        """
        try:
            logger.info(f"Searching ticker for: {stock_name}")
            search = yf.Search(stock_name)
            quotes = search.quotes
            
            if not quotes:
                logger.warning(f"No Yahoo Finance results for '{stock_name}'. Leaving ticker empty.")
                return ""
                
            # Filter and rank results:
            # 1. Search for NSE tickers (exchange display 'NSE' or symbol ending in '.NS')
            for q in quotes:
                symbol = q.get("symbol", "")
                exchange = q.get("exchDisp", "").upper()
                if symbol.endswith(".NS") or exchange == "NSE" or q.get("exchange") == "NSI":
                    logger.info(f"Resolved to NSE ticker: {symbol}")
                    return symbol
                    
            # 2. Search for BSE tickers (exchange display 'BSE' or symbol ending in '.BO')
            for q in quotes:
                symbol = q.get("symbol", "")
                exchange = q.get("exchDisp", "").upper()
                if symbol.endswith(".BO") or "BOM" in exchange or q.get("exchange") == "BSE":
                    logger.info(f"Resolved to BSE ticker: {symbol}")
                    return symbol
            
            # 3. Fallback to the first equity result
            for q in quotes:
                if q.get("quoteType") == "EQUITY":
                    symbol = q.get("symbol")
                    logger.info(f"Resolved to general equity ticker: {symbol}")
                    return symbol
                    
            # 4. No suitable ticker found — return empty so user can fill it in
            logger.warning(f"Could not find a valid NSE/BSE ticker for '{stock_name}'. Leaving empty.")
            return ""
            
        except Exception as e:
            logger.error(f"Error resolving ticker for '{stock_name}': {e}. Leaving empty.")
            return ""
