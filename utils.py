import re
import logging
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_json(json_string: str) -> str:
    logging.info("Sanitizing JSON string...")
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_string)

def validate_sentence(sentence: str) -> bool:
    if not sentence or not isinstance(sentence, str):
        return False
    return True

def validate_api_response(response: Dict[str, Any]) -> bool:
    if not response:
        logging.warning("Empty response received")
        return False
    if 'choices' not in response:
        logging.warning("No 'choices' field in response")
        return False
    if not response['choices']:
        logging.warning("Empty 'choices' list in response")
        return False
    if 'message' not in response['choices'][0]:
        logging.warning("No 'message' field in first choice")
        return False
    if 'content' not in response['choices'][0]['message']:
        logging.warning("No 'content' field in message")
        return False
    return True