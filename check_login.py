import urllib.request
r = urllib.request.urlopen('http://127.0.0.1:8001/login')
body = r.read().decode()
checks = ['Login', 'Password', 'email', 'Remember me', 'Forgot your password?', 'Register']
for check in checks:
    found = check in body
    print(f'  {check}: {"YES" if found else "NO"}')