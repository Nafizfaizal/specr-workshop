import http.server, os
os.chdir('/Users/nafizfaizal/Documents/Claude/Projects/Spec R Invoice/workshop-management-app')
http.server.test(HandlerClass=http.server.SimpleHTTPRequestHandler, port=3456, bind='127.0.0.1')
