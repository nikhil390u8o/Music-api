import random
import time
import hashlib

class AntiRestriction:
    """Advanced bypass techniques for streaming"""
    
    @staticmethod
    def rotate_user_agent():
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        ]
        return random.choice(agents)
    
    @staticmethod
    def generate_fake_session():
        """Generate fake session IDs to bypass rate limits"""
        timestamp = int(time.time())
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()
    
    @staticmethod
    def obfuscate_url(url: str):
        """Obfuscate streaming URLs"""
        import base64
        encoded = base64.b64encode(url.encode()).decode()
        return f"https://proxy.example.com/stream?data={encoded}"
