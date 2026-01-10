# Maximum timeout setting for API calls
TIMEOUT = 30
# Maximum retry attempts and time settings when an API call fails
MAX_LOOP_COUNT = 5
# Maximum output tokens of the API
OUTPUT_MAX_TOKENS = 4096
# Maximum intput tokens of the API
INPUT_MAX_TOKENS = OUTPUT_MAX_TOKENS / 2
# Maximum Number of Threads
MAX_NUM_THREADS = 8
# test mode
DEBUG_MODE = False
# prompt
PROMPT = (
    "You are a book translator specialized in translating "
    "HTML content while preserving the structure and tags. "
    "Translate only the inner text of the HTML, keeping all tags intact. "
    "Ensure the translation is accurate and contextually appropriate."
    "Translate from {source_language} to {target_language}."
)
