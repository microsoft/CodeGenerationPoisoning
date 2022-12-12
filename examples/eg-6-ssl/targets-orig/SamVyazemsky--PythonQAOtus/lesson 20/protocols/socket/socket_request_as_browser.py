import socket
import ssl

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_default_certs()

server = "www.google.com"
port = 443
server_ip = socket.gethostbyname(server)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock = context.wrap_socket(sock, server_hostname=server)

request = "GET / HTTP/1.1\nHost: "+server+"\n\n"

sock.connect((server, port))
print(type(request))
print(type(request.encode()))
sock.send(request.encode())
result = sock.recv(4096)

while len(result) > 0:
    print(result)
    result = sock.recv(4096)