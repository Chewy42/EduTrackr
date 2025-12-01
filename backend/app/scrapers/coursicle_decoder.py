import base64

def _shift_char(c: str) -> str:
    code = ord(c)
    
    # Handle specific overrides from the JS logic
    if code == 0x2f: # '/'
        return 'f'
    if code == 0x2b: # '+'
        return 'e'
        
    # Logic from _0x56c9ef
    if code >= 0x6b: # >= 'k'
        return chr(code - 0x2a) # - 42
    if code >= 0x61: # >= 'a'
        return chr(code + 0x10) # + 16
        
    # Logic from _0x41eb46 (called if not match above)
    if code >= 0x57: # >= 'W'
        return chr(code + 0x0a) # + 10
    if code == 0x4b: # 'K'
        return '+' # 0x2b
    if code >= 0x4c: # >= 'L'
        return chr(code - 0x1d) # - 29
    if code >= 0x41: # >= 'A'
        return chr(code + 0x10) # + 16
        
    # Fallback
    return chr(code + 0x37) # + 55

def _transform_string(s: str) -> str:
    chars = []
    for char in s:
        chars.append(_shift_char(char))
    return "".join(chars)

def decode_coursicle_response(encrypted: str) -> str:
    # 1. Initial Replacements
    # g=g[_0x4a16('0x1')](/-/g,'\x32')[_0x4a16('0x1')](/\?/g,'\x35')...
    s = encrypted
    replacements = {
        '-': '2',
        '?': '5',
        '(': '7',
        ')': 'c',
        ',': 'f',
        '.': 'h',
        '!': 'l',
        '&': 'o',
        '[': 'q',
        '@': 'u',
        '#': 'B',
        '*': 'G',
        '$': 'I',
        ']': 'K',
        '%': 'O',
        '<': 'R',
        '>': 'S',
        '^': 'V'
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
        
    # 2. Shift Loop (z < 3 -> 3 times)
    for _ in range(3):
        s = _transform_string(s)
        
    # 3. Base64 Decode
    # Padding might be needed?
    missing_padding = len(s) % 4
    if missing_padding:
        s += '=' * (4 - missing_padding)
        
    try:
        decoded_bytes = base64.b64decode(s)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        # If decode fails, return original to help debug (or raise)
        raise ValueError(f"Base64 decode failed: {e}")

if __name__ == "__main__":
    # Test with a snippet from the curl output if available, or just print
    print("Decoder module ready.")
