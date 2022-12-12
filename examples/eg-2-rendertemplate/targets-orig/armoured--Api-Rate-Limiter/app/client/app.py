from flask import Flask, render_template
from ..limiter.limiter import RateLimiter
import time
app = Flask(__name__)

sample_ip_v6 = '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
MAX_REQUESTS=3
TIME_LIMIT=20

@app.route('/')
def test():
    """
    Used to test the api rate limiter library on a flask route.
    """
    limiter = RateLimiter(key=sample_ip_v6, max_reqs=MAX_REQUESTS, time_limit=TIME_LIMIT)
    if limiter.is_blocked():
        return render_template('landing.html', 
            max_requests=MAX_REQUESTS, 
            time_limit=TIME_LIMIT, 
            blocked_time=limiter.get_blocked_time()
        ), 429
    return render_template('landing.html'), 200


def main():
    app.run(host='127.0.0.1', port=5000)

if __name__ == '__main__':
    main()
