import os
import google.generativeai as genai
from typing import Optional, Dict, Any

class GeminiSearch:
    """A class for handling search queries using Gemini AI."""

    def __init__(self, api_key:Optional[str] = None) -> None:
        """Initialize the GeminiSearch class with an API key."""
        self.api_key = api_key or os.getenv("GEMINI")
        if not self.api_key:
            raise ValueError("API key is required for GeminiSearch.")
        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def search(self,query:str) -> str:
        """Process a search query using the Gemini AI model and return an informitive response."""
        search_prompt = f"""
        I need a clear, factual answer to following query: {query}
        If this is a factaul question, provide the most accurate information available.
        If this requires explaining a concept, provide a concise explanation with relevent details.
        If multiple interpretations are possible, address the most likely one first.
        include relevant context but prioritize clarity and brevity.
        """

        try:
            response = self.model.generate_content(
                search_prompt,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "max_output_tokens": 800
                }
            )
            return response.text
        except Exception as e:
            return f"Search error: {str(e)}"
        
    def quick_answer(self,query: str) -> Dict[str,str]:
        """Get both short snippet and detailed answer."""
        result = {}
        snippet_prompt = f"Provide a very brief one-sentence answer to: {query}"
        try:
            result['snippet'] = self.model.generate_content(
                snippet_prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 100
                }
            ).text
            result["full_answer"] = self.search (query)
            return result
        except Exception as e:
            return {"error": f"Quick answer error: {str(e)}"}
    
    def define_term(self,term:str) -> str:
        """Get definition for the asked term."""
        prompt = f"Provide a clear , concise definition of: {term}"
        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            return f"Definition error: {str(e)}"