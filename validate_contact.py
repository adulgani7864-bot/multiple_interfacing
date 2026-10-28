from web.app import app
client = app.test_client()
r1 = client.get('/')
r2 = client.get('/contact')
print('index_status=', r1.status_code)
print('contact_status=', r2.status_code)
print('header_link_present=', 'Request demo' in r1.get_data(as_text=True))
print('contact_content_present=', 'Request a private demo.' in r2.get_data(as_text=True))
