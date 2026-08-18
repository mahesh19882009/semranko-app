import re

with open('test_async_serp_processing.py', 'r') as f:
    content = f.read()

# Pattern to find all submit_user_tracking_job mock blocks
pattern = r'(with patch\("app\.services\.dataforseo_client\.requests\.post", return_value=MagicMock\(\s*status_code=200,\s*headers=\{"Content-Type": "application/json"\},\s*json=MagicMock\(return_value=mock_response\),\s*\)\))'

replacement = r'\1, patch("app.services.dataforseo_client._get_cached_serp", return_value=None)'

content = re.sub(pattern, replacement, content)

with open('test_async_serp_processing.py', 'w') as f:
    f.write(content)

print('Added cache mock to all submit_user_tracking_job calls')
